"""
Chunked upload client for large job results.

Provides client-side implementation of the chunked upload protocol:
- Automatic detection of when chunked upload is needed
- Session management and chunk upload
- Checksum calculation and verification
- Retry logic for failed chunks

Issue #90 - Distributed Agent Architecture (Phase 15)
Task: T207
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from src.api_client import (
    AgentApiClient,
    ApiError,
    AuthenticationError,
    ConnectionError,
    API_BASE_PATH,
)


logger = logging.getLogger("agent.chunked_upload")

# Configuration constants
INLINE_JSON_THRESHOLD = 1 * 1024 * 1024  # 1MB - above this use chunked upload
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB default chunk size
MAX_RETRIES = 3  # Max retries per chunk


class ChunkedUploadError(ApiError):
    """Raised when chunked upload fails."""
    pass


@dataclass
class UploadSession:
    """
    Tracks an upload session.

    Attributes:
        upload_id: Server-assigned upload ID
        chunk_size: Size of each chunk
        total_chunks: Total number of chunks
        upload_type: Type of content (results_json or report_html)
    """
    upload_id: str
    chunk_size: int
    total_chunks: int
    upload_type: str


@dataclass
class ChunkedUploadResult:
    """
    Result of a chunked upload operation.

    Attributes:
        success: Whether upload completed successfully
        upload_id: Server-assigned upload ID (for use with job completion)
        content_size: Size of the uploaded content
        checksum: SHA-256 checksum of the content
        error: Error message if upload failed
    """
    success: bool
    upload_id: Optional[str] = None
    content_size: int = 0
    checksum: Optional[str] = None
    error: Optional[str] = None


def should_use_chunked_upload(
    results: Optional[dict[str, Any]] = None,
    report_html: Optional[str] = None,
) -> tuple[bool, bool]:
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


class ChunkedUploadClient:
    """
    Client for chunked uploads.

    Handles the chunked upload protocol:
    1. Initiate upload session
    2. Upload chunks with retry logic
    3. Finalize upload with checksum verification

    Usage:
        >>> client = ChunkedUploadClient(api_client)
        >>> result = await client.upload_results(job_guid, results_dict)
        >>> if result.success:
        ...     # Use result.upload_id in job completion
    """

    def __init__(
        self,
        api_client: AgentApiClient,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        max_retries: int = MAX_RETRIES,
    ):
        """
        Initialize the chunked upload client.

        Args:
            api_client: Agent API client for server communication
            chunk_size: Size of each chunk in bytes
            max_retries: Maximum retries per chunk
        """
        self._api_client = api_client
        self._chunk_size = chunk_size
        self._max_retries = max_retries

    async def upload_results(
        self,
        job_guid: str,
        results: dict[str, Any],
    ) -> ChunkedUploadResult:
        """
        Upload results JSON using chunked upload.

        Args:
            job_guid: GUID of the job
            results: Results dictionary

        Returns:
            ChunkedUploadResult with upload details
        """
        # Serialize results to JSON bytes
        results_json = json.dumps(results, sort_keys=True, separators=(',', ':'))
        content = results_json.encode('utf-8')

        return await self._upload_content(
            job_guid=job_guid,
            content=content,
            upload_type="results_json",
        )

    async def upload_report_html(
        self,
        job_guid: str,
        report_html: str,
    ) -> ChunkedUploadResult:
        """
        Upload HTML report using chunked upload.

        Args:
            job_guid: GUID of the job
            report_html: HTML report string

        Returns:
            ChunkedUploadResult with upload details
        """
        content = report_html.encode('utf-8')

        return await self._upload_content(
            job_guid=job_guid,
            content=content,
            upload_type="report_html",
        )

    async def _upload_content(
        self,
        job_guid: str,
        content: bytes,
        upload_type: str,
    ) -> ChunkedUploadResult:
        """
        Upload content using chunked upload protocol.

        Args:
            job_guid: GUID of the job
            content: Content bytes to upload
            upload_type: Type of content (results_json or report_html)

        Returns:
            ChunkedUploadResult with upload details
        """
        content_size = len(content)
        checksum = hashlib.sha256(content).hexdigest()

        logger.info(
            f"Starting chunked upload: type={upload_type}, size={content_size}, chunks={self._calculate_total_chunks(content_size)}"
        )

        try:
            # Step 1: Initiate upload session
            session = await self._initiate_upload(
                job_guid=job_guid,
                upload_type=upload_type,
                expected_size=content_size,
            )

            # Step 2: Upload chunks
            await self._upload_chunks(session, content)

            # Step 3: Finalize upload
            await self._finalize_upload(session.upload_id, checksum)

            logger.info(f"Chunked upload completed: upload_id={session.upload_id}")

            return ChunkedUploadResult(
                success=True,
                upload_id=session.upload_id,
                content_size=content_size,
                checksum=checksum,
            )

        except Exception as e:
            logger.error(f"Chunked upload failed: {e}")
            return ChunkedUploadResult(
                success=False,
                error=str(e),
            )

    def _calculate_total_chunks(self, content_size: int) -> int:
        """Calculate total number of chunks needed."""
        return (content_size + self._chunk_size - 1) // self._chunk_size

    async def _initiate_upload(
        self,
        job_guid: str,
        upload_type: str,
        expected_size: int,
    ) -> UploadSession:
        """
        Initiate a chunked upload session.

        Args:
            job_guid: GUID of the job
            upload_type: Type of content
            expected_size: Total expected bytes

        Returns:
            UploadSession with server-assigned upload ID

        Raises:
            ChunkedUploadError: If initiation fails
        """
        payload = {
            "upload_type": upload_type,
            "expected_size": expected_size,
            "chunk_size": self._chunk_size,
        }

        try:
            response = await self._api_client._client.post(
                f"{API_BASE_PATH}/jobs/{job_guid}/uploads/initiate",
                json=payload,
            )
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to server: {e}")
        except httpx.TimeoutException as e:
            raise ConnectionError(f"Connection timed out: {e}")

        if response.status_code == 201:
            data = response.json()
            return UploadSession(
                upload_id=data["upload_id"],
                chunk_size=data["chunk_size"],
                total_chunks=data["total_chunks"],
                upload_type=upload_type,
            )
        elif response.status_code == 401:
            raise AuthenticationError("Invalid API key", status_code=401)
        elif response.status_code == 404:
            raise ChunkedUploadError("Job not found", status_code=404)
        elif response.status_code == 403:
            raise ChunkedUploadError("Job not assigned to this agent", status_code=403)
        elif response.status_code == 400:
            detail = response.json().get("detail", "Invalid request")
            raise ChunkedUploadError(detail, status_code=400)
        else:
            raise ChunkedUploadError(
                f"Failed to initiate upload: status {response.status_code}",
                status_code=response.status_code,
            )

    async def _upload_chunks(
        self,
        session: UploadSession,
        content: bytes,
    ) -> None:
        """
        Upload all chunks for a session.

        Args:
            session: Upload session
            content: Content bytes to upload

        Raises:
            ChunkedUploadError: If chunk upload fails after retries
        """
        total_chunks = session.total_chunks
        chunk_size = session.chunk_size

        for chunk_index in range(total_chunks):
            # Extract chunk
            start = chunk_index * chunk_size
            end = min(start + chunk_size, len(content))
            chunk_data = content[start:end]

            # Upload with retry
            await self._upload_chunk_with_retry(
                session.upload_id,
                chunk_index,
                chunk_data,
            )

            logger.debug(
                f"Uploaded chunk {chunk_index + 1}/{total_chunks} "
                f"({len(chunk_data)} bytes)"
            )

    async def _upload_chunk_with_retry(
        self,
        upload_id: str,
        chunk_index: int,
        chunk_data: bytes,
    ) -> None:
        """
        Upload a single chunk with retry logic.

        Args:
            upload_id: Upload session ID
            chunk_index: Zero-based chunk index
            chunk_data: Chunk bytes

        Raises:
            ChunkedUploadError: If upload fails after max retries
        """
        last_error = None

        for attempt in range(self._max_retries):
            try:
                await self._upload_chunk(upload_id, chunk_index, chunk_data)
                return  # Success
            except ConnectionError as e:
                last_error = e
                logger.warning(
                    f"Chunk {chunk_index} upload failed (attempt {attempt + 1}/{self._max_retries}): {e}"
                )
                if attempt < self._max_retries - 1:
                    # Wait before retry (exponential backoff)
                    import asyncio
                    await asyncio.sleep(2 ** attempt)

        raise ChunkedUploadError(
            f"Failed to upload chunk {chunk_index} after {self._max_retries} attempts: {last_error}"
        )

    async def _upload_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        chunk_data: bytes,
    ) -> bool:
        """
        Upload a single chunk.

        Args:
            upload_id: Upload session ID
            chunk_index: Zero-based chunk index
            chunk_data: Chunk bytes

        Returns:
            True if new chunk, False if duplicate (idempotent)

        Raises:
            ChunkedUploadError: If upload fails
        """
        # Use raw bytes content type for chunk upload
        headers = {
            "Content-Type": "application/octet-stream",
        }

        try:
            response = await self._api_client._client.put(
                f"{API_BASE_PATH}/uploads/{upload_id}/{chunk_index}",
                content=chunk_data,
                headers=headers,
            )
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to server: {e}")
        except httpx.TimeoutException as e:
            raise ConnectionError(f"Connection timed out: {e}")

        if response.status_code == 200:
            data = response.json()
            return data.get("received", True)
        elif response.status_code == 401:
            raise AuthenticationError("Invalid API key", status_code=401)
        elif response.status_code == 404:
            raise ChunkedUploadError("Upload session not found", status_code=404)
        elif response.status_code == 400:
            detail = response.json().get("detail", "Invalid chunk")
            raise ChunkedUploadError(detail, status_code=400)
        elif response.status_code == 409:
            # Duplicate chunk - this is OK (idempotent)
            logger.debug(f"Chunk {chunk_index} already uploaded (idempotent)")
            return False
        else:
            raise ChunkedUploadError(
                f"Failed to upload chunk: status {response.status_code}",
                status_code=response.status_code,
            )

    async def _finalize_upload(
        self,
        upload_id: str,
        checksum: str,
    ) -> None:
        """
        Finalize an upload with checksum verification.

        Args:
            upload_id: Upload session ID
            checksum: SHA-256 checksum of complete content

        Raises:
            ChunkedUploadError: If finalization fails
        """
        payload = {"checksum": checksum}

        try:
            response = await self._api_client._client.post(
                f"{API_BASE_PATH}/uploads/{upload_id}/finalize",
                json=payload,
            )
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to server: {e}")
        except httpx.TimeoutException as e:
            raise ConnectionError(f"Connection timed out: {e}")

        if response.status_code == 200:
            data = response.json()
            if not data.get("success"):
                raise ChunkedUploadError(
                    f"Upload finalization reported failure: {data.get('error')}"
                )
            return
        elif response.status_code == 401:
            raise AuthenticationError("Invalid API key", status_code=401)
        elif response.status_code == 404:
            raise ChunkedUploadError("Upload session not found", status_code=404)
        elif response.status_code == 400:
            detail = response.json().get("detail", "Finalization failed")
            raise ChunkedUploadError(detail, status_code=400)
        else:
            raise ChunkedUploadError(
                f"Failed to finalize upload: status {response.status_code}",
                status_code=response.status_code,
            )

    async def cancel_upload(self, upload_id: str) -> bool:
        """
        Cancel an in-progress upload.

        Args:
            upload_id: Upload session ID

        Returns:
            True if cancelled, False if not found
        """
        try:
            response = await self._api_client._client.delete(
                f"{API_BASE_PATH}/uploads/{upload_id}"
            )
            return response.status_code == 204
        except Exception as e:
            logger.warning(f"Failed to cancel upload {upload_id}: {e}")
            return False
