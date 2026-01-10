"""
Custom exceptions for service layer.

Provides specific exception types for business logic errors
that can be translated to appropriate HTTP responses.
"""

from typing import Optional


class ServiceError(Exception):
    """Base exception for service layer errors."""
    pass


class NotFoundError(ServiceError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, identifier: any):
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} {identifier} not found")


class ConflictError(ServiceError):
    """Raised when an operation conflicts with existing state."""

    def __init__(
        self,
        message: str,
        existing_job_id: Optional[str] = None,
        position: Optional[int] = None
    ):
        self.message = message
        self.existing_job_id = existing_job_id  # GUID format: job_xxx
        self.position = position
        super().__init__(message)


class ValidationError(ServiceError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class CollectionNotAccessibleError(ServiceError):
    """Raised when attempting an operation on an inaccessible collection."""

    def __init__(self, collection_id: int, collection_name: str):
        self.collection_id = collection_id
        self.collection_name = collection_name
        self.message = (
            f"Collection '{collection_name}' (ID: {collection_id}) is not accessible. "
            "Please verify the collection path exists and is readable, then use the "
            "'Test Connection' action to update its accessibility status."
        )
        super().__init__(self.message)
