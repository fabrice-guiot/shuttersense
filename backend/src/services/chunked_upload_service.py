"""
Chunked upload service for large job results.

Handles chunked upload protocol for results that exceed inline size limits:
- JSON results > 1MB: Use chunked upload
- HTML reports: Always use chunked upload

Protocol:
1. Job completion request with upload_required=True
2. Server returns upload_id, chunk_size, total_chunks
3. Agent uploads chunks via PUT /uploads/{uploadId}/{chunkIndex}
4. Agent finalizes via POST /uploads/{uploadId}/finalize with checksum
5. Server verifies checksum and processes results

Security:
- Upload sessions scoped to job and agent
- SHA-256 checksum verification at finalization
- HTML reports validated for no external scripts
- Sessions expire after 1 hour

Issue #90 - Distributed Agent Architecture (Phase 15)
Tasks: T204, T209
"""

import hashlib
import json
import re
import secrets
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from backend.src.services.exceptions import ValidationError, NotFoundError
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")

# Configuration constants
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB default chunk size
MAX_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB max chunk size
INLINE_JSON_THRESHOLD = 1 * 1024 * 1024  # 1MB - above this use chunked upload
SESSION_TTL_HOURS = 1  # Sessions expire after 1 hour
UPLOAD_ID_LENGTH = 32  # 256-bit random upload ID

# Module-level storage (shared across all service instances)
# This is necessary because each API request creates a new service instance
_sessions: Dict[str, "UploadSession"] = {}
_finalized_content: Dict[str, Tuple[bytes, int, int, datetime]] = {}  # upload_id -> (content, agent_id, team_id, finalized_at)


class UploadType(str, Enum):
    """Type of content being uploaded."""
    RESULTS_JSON = "results_json"
    REPORT_HTML = "report_html"
    FILE_INFO = "file_info"  # Issue #107: Inventory FileInfo for collections
    DELTA = "delta"  # Issue #107 Phase 8: Inventory delta results


@dataclass
class ChunkInfo:
    """Information about an uploaded chunk."""
    index: int
    size: int
    checksum: str  # SHA-256 of individual chunk
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UploadSession:
    """
    Upload session tracking.

    Attributes:
        upload_id: Unique upload ID (returned to client)
        job_guid: Associated job GUID
        agent_id: Agent internal ID (for validation)
        team_id: Team internal ID (for validation)
        upload_type: Type of content being uploaded
        expected_size: Total expected bytes
        expected_checksum: Expected SHA-256 checksum
        chunk_size: Size of each chunk (except last)
        total_chunks: Expected number of chunks
        chunks: Received chunk information
        temp_dir: Temporary directory for chunk storage
        created_at: Session creation timestamp
        expires_at: Session expiration timestamp
    """
    upload_id: str
    job_guid: str
    agent_id: int
    team_id: int
    upload_type: UploadType
    expected_size: int
    expected_checksum: Optional[str] = None  # Set at finalization
    chunk_size: int = DEFAULT_CHUNK_SIZE
    total_chunks: int = 0
    chunks: Dict[int, ChunkInfo] = field(default_factory=dict)
    temp_dir: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS))

    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_complete(self) -> bool:
        """Check if all chunks have been received."""
        return len(self.chunks) == self.total_chunks

    @property
    def received_size(self) -> int:
        """Get total bytes received so far."""
        return sum(chunk.size for chunk in self.chunks.values())


@dataclass
class InitiateUploadResult:
    """Result of initiating a chunked upload."""
    upload_id: str
    chunk_size: int
    total_chunks: int


@dataclass
class FinalizeUploadResult:
    """Result of finalizing an upload."""
    success: bool
    content: Optional[bytes] = None
    content_type: UploadType = UploadType.RESULTS_JSON
    error: Optional[str] = None


class ChunkedUploadService:
    """
    Service for managing chunked uploads.

    Stores upload sessions in memory and chunks on disk.
    Sessions and temp files are cleaned up on expiration.

    Usage:
        >>> service = ChunkedUploadService()
        >>> result = service.initiate_upload(
        ...     job_guid="job_xxx",
        ...     agent_id=1,
        ...     team_id=1,
        ...     upload_type=UploadType.RESULTS_JSON,
        ...     expected_size=5_000_000
        ... )
        >>> service.upload_chunk(result.upload_id, 0, chunk_data)
        >>> final = service.finalize_upload(result.upload_id, checksum)
    """

    def __init__(self, temp_base: Optional[str] = None):
        """
        Initialize the chunked upload service.

        Note: Sessions and finalized content are stored in module-level
        dictionaries to persist across service instances (each API request
        creates a new service instance).

        Args:
            temp_base: Base directory for temp files (uses system temp if None)
        """
        self._temp_base = temp_base or tempfile.gettempdir()
        self._uploads_dir = Path(self._temp_base) / "shuttersense_uploads"
        self._uploads_dir.mkdir(parents=True, exist_ok=True)

    def _validate_path_containment(self, path: Path) -> Path:
        """
        Validate that a path is contained within the uploads directory.

        Resolves symlinks and relative path components (like ..) to ensure
        the path cannot escape the uploads directory (path traversal prevention).

        Args:
            path: Path to validate

        Returns:
            Resolved absolute path

        Raises:
            ValidationError: If path would escape uploads directory
        """
        resolved_path = path.resolve()
        uploads_resolved = self._uploads_dir.resolve()

        # Check that the resolved path starts with the uploads directory
        try:
            resolved_path.relative_to(uploads_resolved)
        except ValueError:
            logger.warning(
                "Path traversal attempt detected",
                extra={"attempted_path": str(path), "resolved_to": str(resolved_path)}
            )
            raise ValidationError("Invalid path: path traversal detected")

        return resolved_path

    # =========================================================================
    # Upload Session Management
    # =========================================================================

    def initiate_upload(
        self,
        job_guid: str,
        agent_id: int,
        team_id: int,
        upload_type: UploadType,
        expected_size: int,
        chunk_size: Optional[int] = None,
    ) -> InitiateUploadResult:
        """
        Initiate a new chunked upload session.

        Args:
            job_guid: GUID of the job this upload is for
            agent_id: Internal ID of the uploading agent
            team_id: Team internal ID
            upload_type: Type of content being uploaded
            expected_size: Total expected bytes
            chunk_size: Optional custom chunk size (default 5MB, max 10MB)

        Returns:
            InitiateUploadResult with upload_id and chunk info

        Raises:
            ValidationError: If parameters are invalid
        """
        # Validate chunk size
        if chunk_size is None:
            chunk_size = DEFAULT_CHUNK_SIZE
        elif chunk_size > MAX_CHUNK_SIZE:
            raise ValidationError(f"Chunk size cannot exceed {MAX_CHUNK_SIZE} bytes")
        elif chunk_size <= 0:
            raise ValidationError("Chunk size must be positive")

        # Validate expected size
        if expected_size <= 0:
            raise ValidationError("Expected size must be positive")

        # Generate unique upload ID
        upload_id = secrets.token_urlsafe(UPLOAD_ID_LENGTH)

        # Calculate total chunks
        total_chunks = (expected_size + chunk_size - 1) // chunk_size

        # Create temp directory for this upload
        temp_dir = self._uploads_dir / upload_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Create session
        session = UploadSession(
            upload_id=upload_id,
            job_guid=job_guid,
            agent_id=agent_id,
            team_id=team_id,
            upload_type=upload_type,
            expected_size=expected_size,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            temp_dir=str(temp_dir),
        )

        _sessions[upload_id] = session

        logger.info(
            "Initiated chunked upload",
            extra={
                "upload_id": upload_id,
                "job_guid": job_guid,
                "upload_type": upload_type.value,
                "expected_size": expected_size,
                "chunk_size": chunk_size,
                "total_chunks": total_chunks,
            }
        )

        return InitiateUploadResult(
            upload_id=upload_id,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
        )

    def get_session(self, upload_id: str) -> Optional[UploadSession]:
        """
        Get an upload session by ID.

        Args:
            upload_id: Upload session ID

        Returns:
            UploadSession or None if not found/expired
        """
        session = _sessions.get(upload_id)
        if session and session.is_expired:
            self._cleanup_session(upload_id)
            return None
        return session

    def validate_session(
        self,
        upload_id: str,
        agent_id: int,
        team_id: int,
    ) -> UploadSession:
        """
        Validate and retrieve an upload session.

        Args:
            upload_id: Upload session ID
            agent_id: Agent internal ID (must match session)
            team_id: Team internal ID (must match session)

        Returns:
            Validated UploadSession

        Raises:
            NotFoundError: If session not found
            ValidationError: If session expired or agent mismatch
        """
        session = _sessions.get(upload_id)

        if not session:
            raise NotFoundError("Upload session", upload_id)

        if session.is_expired:
            self._cleanup_session(upload_id)
            raise ValidationError("Upload session has expired")

        if session.agent_id != agent_id:
            raise ValidationError("Upload session belongs to a different agent")

        if session.team_id != team_id:
            raise ValidationError("Upload session belongs to a different team")

        return session

    # =========================================================================
    # Chunk Upload
    # =========================================================================

    def upload_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        chunk_data: bytes,
        agent_id: int,
        team_id: int,
    ) -> bool:
        """
        Upload a chunk for an existing session.

        Chunks are stored on disk to avoid memory pressure for large uploads.

        Args:
            upload_id: Upload session ID
            chunk_index: Zero-based chunk index
            chunk_data: Chunk bytes
            agent_id: Agent internal ID (for validation)
            team_id: Team internal ID (for validation)

        Returns:
            True if this is a new chunk, False if duplicate (idempotent)

        Raises:
            NotFoundError: If session not found
            ValidationError: If session expired, agent mismatch, or invalid chunk
        """
        session = self.validate_session(upload_id, agent_id, team_id)

        # Validate chunk index
        if chunk_index < 0 or chunk_index >= session.total_chunks:
            raise ValidationError(
                f"Invalid chunk index {chunk_index}, expected 0-{session.total_chunks - 1}"
            )

        # Check if chunk already received (idempotent)
        if chunk_index in session.chunks:
            existing_chunk = session.chunks[chunk_index]
            # Verify checksum matches (detect corruption/tampering)
            incoming_checksum = hashlib.sha256(chunk_data).hexdigest()
            if existing_chunk.checksum != incoming_checksum:
                raise ValidationError(
                    f"Chunk {chunk_index} already received with different content"
                )
            logger.debug(
                "Duplicate chunk upload (idempotent)",
                extra={"upload_id": upload_id, "chunk_index": chunk_index}
            )
            return False

        # Validate chunk size
        is_last_chunk = chunk_index == session.total_chunks - 1
        if is_last_chunk:
            # Last chunk can be smaller
            expected_last_size = session.expected_size - (session.chunk_size * chunk_index)
            if len(chunk_data) != expected_last_size:
                raise ValidationError(
                    f"Last chunk size mismatch: expected {expected_last_size}, got {len(chunk_data)}"
                )
        else:
            # Non-last chunks must be full size
            if len(chunk_data) != session.chunk_size:
                raise ValidationError(
                    f"Chunk size mismatch: expected {session.chunk_size}, got {len(chunk_data)}"
                )

        # Compute chunk checksum
        chunk_checksum = hashlib.sha256(chunk_data).hexdigest()

        # Store chunk on disk
        if not session.temp_dir:
            raise ValidationError("Upload session has no temp directory")
        chunk_path = Path(session.temp_dir) / f"chunk_{chunk_index:06d}"
        # Validate path is within uploads directory (path traversal prevention)
        validated_path = self._validate_path_containment(chunk_path)
        with open(validated_path, 'wb') as f:
            f.write(chunk_data)

        # Record chunk info
        session.chunks[chunk_index] = ChunkInfo(
            index=chunk_index,
            size=len(chunk_data),
            checksum=chunk_checksum,
        )

        logger.debug(
            "Chunk uploaded",
            extra={
                "upload_id": upload_id,
                "chunk_index": chunk_index,
                "chunk_size": len(chunk_data),
                "chunks_received": len(session.chunks),
                "total_chunks": session.total_chunks,
            }
        )

        return True

    def get_upload_status(
        self,
        upload_id: str,
        agent_id: int,
        team_id: int,
    ) -> Dict[str, Any]:
        """
        Get current upload status.

        Args:
            upload_id: Upload session ID
            agent_id: Agent internal ID (for validation)
            team_id: Team internal ID (for validation)

        Returns:
            Status dictionary with progress info

        Raises:
            NotFoundError: If session not found
            ValidationError: If session expired or agent mismatch
        """
        session = self.validate_session(upload_id, agent_id, team_id)

        received_chunks = sorted(session.chunks.keys())
        missing_chunks = [i for i in range(session.total_chunks) if i not in session.chunks]

        return {
            "upload_id": upload_id,
            "job_guid": session.job_guid,
            "upload_type": session.upload_type.value,
            "expected_size": session.expected_size,
            "received_size": session.received_size,
            "total_chunks": session.total_chunks,
            "received_chunks": len(session.chunks),
            "received_chunk_indices": received_chunks,
            "missing_chunk_indices": missing_chunks,
            "is_complete": session.is_complete,
            "expires_at": session.expires_at.isoformat(),
        }

    # =========================================================================
    # Finalization
    # =========================================================================

    def finalize_upload(
        self,
        upload_id: str,
        expected_checksum: str,
        agent_id: int,
        team_id: int,
    ) -> FinalizeUploadResult:
        """
        Finalize an upload by verifying checksum and assembling content.

        Args:
            upload_id: Upload session ID
            expected_checksum: Expected SHA-256 checksum of complete content
            agent_id: Agent internal ID (for validation)
            team_id: Team internal ID (for validation)

        Returns:
            FinalizeUploadResult with assembled content or error

        Raises:
            NotFoundError: If session not found
            ValidationError: If validation fails
        """
        session = self.validate_session(upload_id, agent_id, team_id)

        # Check all chunks received
        if not session.is_complete:
            missing = [i for i in range(session.total_chunks) if i not in session.chunks]
            raise ValidationError(
                f"Upload incomplete, missing chunks: {missing[:10]}{'...' if len(missing) > 10 else ''}"
            )

        # Assemble chunks and compute checksum
        assembled_content = self._assemble_chunks(session)
        actual_checksum = hashlib.sha256(assembled_content).hexdigest()

        # Verify checksum
        if actual_checksum != expected_checksum:
            logger.warning(
                "Checksum verification failed",
                extra={
                    "upload_id": upload_id,
                    "expected": expected_checksum,
                    "actual": actual_checksum,
                }
            )
            raise ValidationError(
                f"Checksum verification failed: expected {expected_checksum[:16]}..., "
                f"got {actual_checksum[:16]}..."
            )

        # Validate content based on type
        validation_error = self._validate_content(session.upload_type, assembled_content)
        if validation_error:
            logger.warning(
                "Content validation failed",
                extra={
                    "upload_id": upload_id,
                    "upload_type": session.upload_type.value,
                    "error": validation_error,
                }
            )
            raise ValidationError(f"Content validation failed: {validation_error}")

        logger.info(
            "Upload finalized successfully",
            extra={
                "upload_id": upload_id,
                "job_guid": session.job_guid,
                "upload_type": session.upload_type.value,
                "content_size": len(assembled_content),
            }
        )

        # Store finalized content for retrieval during job completion
        _finalized_content[upload_id] = (
            assembled_content,
            agent_id,
            team_id,
            datetime.utcnow(),
        )

        # Cleanup session temp files but keep content in memory
        self._cleanup_session(upload_id)

        return FinalizeUploadResult(
            success=True,
            content=assembled_content,
            content_type=session.upload_type,
        )

    def get_finalized_content(
        self,
        upload_id: str,
        agent_id: int,
        team_id: int,
    ) -> Optional[bytes]:
        """
        Retrieve finalized content from a completed upload.

        Content is removed from storage after retrieval (one-time access).

        Args:
            upload_id: Upload session ID
            agent_id: Agent internal ID (must match upload owner)
            team_id: Team internal ID (must match upload owner)

        Returns:
            Content bytes if found and owned by agent, None otherwise
        """
        if upload_id not in _finalized_content:
            logger.debug(
                "Finalized content not found",
                extra={"upload_id": upload_id}
            )
            return None

        content, stored_agent_id, stored_team_id, finalized_at = _finalized_content[upload_id]

        # Verify ownership
        if stored_agent_id != agent_id or stored_team_id != team_id:
            logger.warning(
                "Finalized content ownership mismatch",
                extra={
                    "upload_id": upload_id,
                    "stored_agent_id": stored_agent_id,
                    "agent_id": agent_id,
                }
            )
            return None

        # Remove from storage (one-time access)
        del _finalized_content[upload_id]

        logger.debug(
            "Finalized content retrieved",
            extra={
                "upload_id": upload_id,
                "content_size": len(content),
            }
        )

        return content

    def _assemble_chunks(self, session: UploadSession) -> bytes:
        """
        Assemble all chunks into complete content.

        Args:
            session: Upload session with complete chunks

        Returns:
            Assembled bytes
        """
        if not session.temp_dir:
            raise ValidationError("Upload session has no temp directory")

        temp_dir = Path(session.temp_dir)
        chunks = []
        for i in range(session.total_chunks):
            chunk_path = temp_dir / f"chunk_{i:06d}"
            # Validate path is within uploads directory (path traversal prevention)
            validated_path = self._validate_path_containment(chunk_path)
            with open(validated_path, 'rb') as f:
                chunks.append(f.read())

        return b''.join(chunks)

    # =========================================================================
    # Content Validation
    # =========================================================================

    def _validate_content(
        self,
        upload_type: UploadType,
        content: bytes,
    ) -> Optional[str]:
        """
        Validate uploaded content based on type.

        Args:
            upload_type: Type of content
            content: Content bytes

        Returns:
            Error message if validation fails, None if valid
        """
        if upload_type == UploadType.RESULTS_JSON:
            return self._validate_json_results(content)
        elif upload_type == UploadType.REPORT_HTML:
            return self._validate_html_report(content)
        elif upload_type == UploadType.FILE_INFO:
            return self._validate_file_info(content)
        elif upload_type == UploadType.DELTA:
            return self._validate_delta(content)
        return None

    def _validate_json_results(self, content: bytes) -> Optional[str]:
        """
        Validate JSON results content.

        Args:
            content: JSON bytes

        Returns:
            Error message if invalid, None if valid
        """
        try:
            # Parse JSON
            decoded = content.decode('utf-8')
            data = json.loads(decoded)

            # Must be a dictionary
            if not isinstance(data, dict):
                return "Results must be a JSON object"

            return None

        except UnicodeDecodeError as e:
            return f"Invalid UTF-8 encoding: {e}"
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"

    def _validate_file_info(self, content: bytes) -> Optional[str]:
        """
        Validate FileInfo content from inventory import.

        FileInfo is a JSON object with:
        - connector_guid: str (con_xxx format)
        - collections: list of {collection_guid, file_info}

        Issue #107: Chunked upload support for large FileInfo

        Args:
            content: JSON bytes

        Returns:
            Error message if invalid, None if valid
        """
        try:
            # Parse JSON
            decoded = content.decode('utf-8')
            data = json.loads(decoded)

            # Must be a dictionary
            if not isinstance(data, dict):
                return "FileInfo must be a JSON object"

            # Must have connector_guid
            if "connector_guid" not in data:
                return "FileInfo missing 'connector_guid' field"

            # Must have collections array
            if "collections" not in data:
                return "FileInfo missing 'collections' field"

            if not isinstance(data["collections"], list):
                return "FileInfo 'collections' must be an array"

            # Validate each collection entry has required fields
            for i, entry in enumerate(data["collections"]):
                if not isinstance(entry, dict):
                    return f"FileInfo collections[{i}] must be an object"
                if "collection_guid" not in entry:
                    return f"FileInfo collections[{i}] missing 'collection_guid'"
                if "file_info" not in entry:
                    return f"FileInfo collections[{i}] missing 'file_info'"
                if not isinstance(entry["file_info"], list):
                    return f"FileInfo collections[{i}].file_info must be an array"

            return None

        except UnicodeDecodeError as e:
            return f"Invalid UTF-8 encoding: {e}"
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"

    def _validate_delta(self, content: bytes) -> Optional[str]:
        """
        Validate delta content from inventory import Phase C.

        Delta is a JSON object with:
        - connector_guid: str (con_xxx format)
        - deltas: list of {collection_guid, summary, is_first_import, changes}

        Issue #107 Phase 8: Chunked upload support for large deltas

        Args:
            content: JSON bytes

        Returns:
            Error message if invalid, None if valid
        """
        try:
            # Parse JSON
            decoded = content.decode('utf-8')
            data = json.loads(decoded)

            # Must be a dictionary
            if not isinstance(data, dict):
                return "Delta must be a JSON object"

            # Must have connector_guid
            if "connector_guid" not in data:
                return "Delta missing 'connector_guid' field"

            # Must have deltas array
            if "deltas" not in data:
                return "Delta missing 'deltas' field"

            if not isinstance(data["deltas"], list):
                return "Delta 'deltas' must be an array"

            # Validate each delta entry has required fields
            for i, entry in enumerate(data["deltas"]):
                if not isinstance(entry, dict):
                    return f"Delta deltas[{i}] must be an object"
                if "collection_guid" not in entry:
                    return f"Delta deltas[{i}] missing 'collection_guid'"
                if "summary" not in entry:
                    return f"Delta deltas[{i}] missing 'summary'"
                if not isinstance(entry["summary"], dict):
                    return f"Delta deltas[{i}].summary must be an object"

            return None

        except UnicodeDecodeError as e:
            return f"Invalid UTF-8 encoding: {e}"
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"

    # Trusted CDN domains for external scripts/stylesheets
    TRUSTED_CDNS = [
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "unpkg.com",
    ]

    def _validate_html_report(self, content: bytes) -> Optional[str]:
        """
        Validate HTML report for security.

        Security checks:
        - No external scripts except from trusted CDNs
        - No javascript: URLs
        - No data: URLs with script content
        - No inline event handlers that could execute external code

        Trusted CDNs (allowed):
        - cdn.jsdelivr.net (Chart.js, etc.)
        - cdnjs.cloudflare.com
        - unpkg.com

        Args:
            content: HTML bytes

        Returns:
            Error message if validation fails, None if valid
        """
        try:
            html = content.decode('utf-8')
        except UnicodeDecodeError as e:
            return f"Invalid UTF-8 encoding: {e}"

        # Check for external script sources (except trusted CDNs)
        # Find all script src URLs
        script_src_pattern = re.compile(
            r'''<script[^>]*\ssrc\s*=\s*["']?(https?://[^"'\s>]+)["']?''',
            re.IGNORECASE
        )
        for match in script_src_pattern.finditer(html):
            url = match.group(1)
            # Check if URL is from a trusted CDN
            if not any(cdn in url for cdn in self.TRUSTED_CDNS):
                return f"External script sources are not allowed (untrusted: {url[:50]}...)"

        # Check for javascript: URLs
        javascript_url_pattern = re.compile(
            r'''["']\s*javascript:''',
            re.IGNORECASE
        )
        if javascript_url_pattern.search(html):
            return "javascript: URLs are not allowed"

        # Check for potentially dangerous data: URLs
        # Allow data:image/* but block data:text/html or data:application/javascript
        dangerous_data_pattern = re.compile(
            r'''["']\s*data:(text/html|application/javascript|text/javascript)''',
            re.IGNORECASE
        )
        if dangerous_data_pattern.search(html):
            return "Dangerous data: URLs are not allowed"

        # Check for external stylesheet links (except trusted CDNs)
        css_href_pattern = re.compile(
            r'''<link[^>]*\shref\s*=\s*["']?(https?://[^"'\s>]+)["']?''',
            re.IGNORECASE
        )
        for match in css_href_pattern.finditer(html):
            url = match.group(1)
            # Check if URL is from a trusted CDN
            if not any(cdn in url for cdn in self.TRUSTED_CDNS):
                return f"External stylesheets are not allowed (untrusted: {url[:50]}...)"

        # Check for external image sources that could track users
        # This is optional/configurable - commenting out for now as it may be too restrictive
        # external_img_pattern = re.compile(
        #     r'''<img[^>]*\ssrc\s*=\s*["']?https?://''',
        #     re.IGNORECASE
        # )

        return None

    # =========================================================================
    # Session Cleanup
    # =========================================================================

    def _cleanup_session(self, upload_id: str) -> None:
        """
        Clean up a session and its temp files.

        Args:
            upload_id: Upload session ID to clean up
        """
        session = _sessions.pop(upload_id, None)
        if session and session.temp_dir:
            try:
                shutil.rmtree(session.temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(
                    "Failed to cleanup temp directory",
                    extra={"upload_id": upload_id, "temp_dir": session.temp_dir, "error": str(e)}
                )

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up all expired sessions.

        Should be called periodically (e.g., every 15 minutes).

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow()
        expired = [
            upload_id for upload_id, session in _sessions.items()
            if session.expires_at < now
        ]

        for upload_id in expired:
            self._cleanup_session(upload_id)

        if expired:
            logger.info(
                "Cleaned up expired upload sessions",
                extra={"count": len(expired)}
            )

        return len(expired)

    def cancel_upload(
        self,
        upload_id: str,
        agent_id: int,
        team_id: int,
    ) -> bool:
        """
        Cancel an in-progress upload.

        Args:
            upload_id: Upload session ID
            agent_id: Agent internal ID (for validation)
            team_id: Team internal ID (for validation)

        Returns:
            True if cancelled, False if not found

        Raises:
            ValidationError: If agent mismatch
        """
        session = _sessions.get(upload_id)
        if not session:
            return False

        if session.agent_id != agent_id:
            raise ValidationError("Upload session belongs to a different agent")

        if session.team_id != team_id:
            raise ValidationError("Upload session belongs to a different team")

        self._cleanup_session(upload_id)
        logger.info("Upload cancelled", extra={"upload_id": upload_id})
        return True


# ============================================================================
# Helper Functions
# ============================================================================

def should_use_chunked_upload(
    results: Optional[Dict[str, Any]] = None,
    report_html: Optional[str] = None,
) -> Tuple[bool, bool]:
    """
    Determine if chunked upload should be used.

    Args:
        results: Results dictionary (will be JSON-encoded)
        report_html: HTML report string

    Returns:
        Tuple of (results_needs_chunked, html_needs_chunked)
    """
    results_needs_chunked = False
    html_needs_chunked = False

    if results:
        results_json = json.dumps(results, sort_keys=True, separators=(',', ':'))
        results_needs_chunked = len(results_json.encode('utf-8')) > INLINE_JSON_THRESHOLD

    if report_html:
        # HTML reports always use chunked upload for security validation
        html_needs_chunked = True

    return results_needs_chunked, html_needs_chunked
