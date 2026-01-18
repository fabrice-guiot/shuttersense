"""
Utility modules for ShutterSense backend.

This package contains shared utilities used across the application:
- crypto: Credential encryption/decryption (Fernet)
- cache: File listing cache with collection-aware TTL
- job_queue: Job queue for sequential analysis execution
- logging_config: Structured logging setup with JSON format
"""

from backend.src.utils.crypto import (
    CredentialEncryptor,
    get_credential_encryptor,
    init_credential_encryptor,
)
from backend.src.utils.cache import (
    CachedFileListing,
    FileListingCache,
    get_file_listing_cache,
    init_file_listing_cache,
    get_ttl_for_state,
    COLLECTION_STATE_TTL,
)
from backend.src.utils.job_queue import (
    JobStatus,
    AnalysisJob,
    JobQueue,
    get_job_queue,
    init_job_queue,
    create_job_id,
)
from backend.src.utils.logging_config import (
    configure_logging,
    get_logger,
    init_logging,
    JSONFormatter,
    ConsoleFormatter,
)

__all__ = [
    # Crypto
    "CredentialEncryptor",
    "get_credential_encryptor",
    "init_credential_encryptor",
    # Cache
    "CachedFileListing",
    "FileListingCache",
    "get_file_listing_cache",
    "init_file_listing_cache",
    "get_ttl_for_state",
    "COLLECTION_STATE_TTL",
    # Job Queue
    "JobStatus",
    "AnalysisJob",
    "JobQueue",
    "get_job_queue",
    "init_job_queue",
    "create_job_id",
    # Logging
    "configure_logging",
    "get_logger",
    "init_logging",
    "JSONFormatter",
    "ConsoleFormatter",
]
