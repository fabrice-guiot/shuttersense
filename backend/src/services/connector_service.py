"""
Connector service for managing remote storage connectors.

Provides business logic for creating, reading, updating, and deleting
remote storage connectors with credential encryption/decryption.

Design:
- Encrypts credentials before storing in database
- Decrypts credentials when retrieving
- Validates connector can be deleted (no collections reference it)
- Tests connections using appropriate storage adapter
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.src.models import Connector, ConnectorType
from backend.src.utils.crypto import CredentialEncryptor
from backend.src.utils.logging_config import get_logger
from backend.src.services.remote import S3Adapter, GCSAdapter, SMBAdapter


logger = get_logger("services")


class ConnectorService:
    """
    Service for managing remote storage connectors.

    Handles CRUD operations for connectors with automatic credential encryption/decryption.
    Validates connectors can connect before creation and provides connection testing.

    Usage:
        >>> service = ConnectorService(db_session, credential_encryptor)
        >>> connector = service.create_connector(
        ...     name="My AWS Account",
        ...     type=ConnectorType.S3,
        ...     credentials={"aws_access_key_id": "...", "aws_secret_access_key": "..."},
        ...     metadata={"team": "engineering"}
        ... )
    """

    def __init__(self, db: Session, encryptor: CredentialEncryptor):
        """
        Initialize connector service.

        Args:
            db: SQLAlchemy database session
            encryptor: Credential encryptor for encrypting/decrypting credentials
        """
        self.db = db
        self.encryptor = encryptor

    def create_connector(
        self,
        name: str,
        type: ConnectorType,
        credentials: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Connector:
        """
        Create a new connector with encrypted credentials.

        Args:
            name: User-friendly connector name (must be unique)
            type: Connector type (S3, GCS, SMB)
            credentials: Decrypted credentials dictionary
            metadata: Optional user-defined metadata

        Returns:
            Created Connector instance

        Raises:
            ValueError: If name already exists or credentials invalid
            Exception: If database operation fails

        Example:
            >>> credentials = {"aws_access_key_id": "...", "aws_secret_access_key": "..."}
            >>> connector = service.create_connector("My AWS", ConnectorType.S3, credentials)
        """
        try:
            # Encrypt credentials
            credentials_json = json.dumps(credentials)
            encrypted_credentials = self.encryptor.encrypt(credentials_json)

            # Convert metadata to JSON string if provided
            metadata_json = json.dumps(metadata) if metadata else None

            # Create connector
            connector = Connector(
                name=name,
                type=type,
                credentials=encrypted_credentials,
                metadata_json=metadata_json,
                is_active=True
            )

            self.db.add(connector)
            self.db.commit()
            self.db.refresh(connector)

            logger.info(
                f"Created connector: {name}",
                extra={"connector_id": connector.id, "type": type.value}
            )

            return connector

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Connector name already exists: {name}")
            raise ValueError(f"Connector with name '{name}' already exists")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create connector: {str(e)}", extra={"connector_name": name})
            raise

    def get_connector(self, connector_id: int, decrypt_credentials: bool = False) -> Optional[Connector]:
        """
        Get connector by ID.

        Args:
            connector_id: Connector ID
            decrypt_credentials: If True, decrypt and attach credentials to connector object

        Returns:
            Connector instance or None if not found

        Note:
            If decrypt_credentials=True, decrypted credentials are added as
            connector.decrypted_credentials (not persisted to database)

        Example:
            >>> connector = service.get_connector(1, decrypt_credentials=True)
            >>> print(connector.decrypted_credentials)
            {'aws_access_key_id': '...', 'aws_secret_access_key': '...'}
        """
        connector = self.db.query(Connector).filter(Connector.id == connector_id).first()

        if connector and decrypt_credentials:
            # Decrypt credentials and attach to connector object
            decrypted_json = self.encryptor.decrypt(connector.credentials)
            connector.decrypted_credentials = json.loads(decrypted_json)

        return connector

    def list_connectors(
        self,
        type_filter: Optional[ConnectorType] = None,
        active_only: bool = False
    ) -> List[Connector]:
        """
        List connectors with optional filtering.

        Args:
            type_filter: Filter by connector type (S3, GCS, SMB)
            active_only: If True, only return active connectors

        Returns:
            List of Connector instances

        Example:
            >>> connectors = service.list_connectors(type_filter=ConnectorType.S3, active_only=True)
            >>> for conn in connectors:
            ...     print(f"{conn.name} ({conn.type.value})")
        """
        query = self.db.query(Connector)

        if type_filter:
            query = query.filter(Connector.type == type_filter)

        if active_only:
            query = query.filter(Connector.is_active == True)

        connectors = query.order_by(Connector.name).all()

        logger.info(
            f"Listed {len(connectors)} connectors",
            extra={"type_filter": type_filter.value if type_filter else None, "active_only": active_only}
        )

        return connectors

    def update_connector(
        self,
        connector_id: int,
        name: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ) -> Connector:
        """
        Update connector properties.

        Re-encrypts credentials if provided. Only updates fields that are not None.

        Args:
            connector_id: Connector ID to update
            name: New name (must be unique if changed)
            credentials: New credentials (will be re-encrypted)
            metadata: New metadata
            is_active: New active status

        Returns:
            Updated Connector instance

        Raises:
            ValueError: If connector not found or name conflicts
            Exception: If database operation fails

        Example:
            >>> new_creds = {"aws_access_key_id": "...", "aws_secret_access_key": "..."}
            >>> connector = service.update_connector(1, credentials=new_creds)
        """
        connector = self.db.query(Connector).filter(Connector.id == connector_id).first()

        if not connector:
            raise ValueError(f"Connector with ID {connector_id} not found")

        try:
            # Update fields
            if name is not None:
                connector.name = name

            if credentials is not None:
                # Re-encrypt credentials
                credentials_json = json.dumps(credentials)
                connector.credentials = self.encryptor.encrypt(credentials_json)

            if metadata is not None:
                connector.metadata_json = json.dumps(metadata)

            if is_active is not None:
                connector.is_active = is_active

            self.db.commit()
            self.db.refresh(connector)

            logger.info(
                f"Updated connector: {connector.name}",
                extra={"connector_id": connector_id}
            )

            return connector

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Connector name conflict: {name}")
            raise ValueError(f"Connector with name '{name}' already exists")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update connector: {str(e)}", extra={"connector_id": connector_id})
            raise

    def delete_connector(self, connector_id: int) -> None:
        """
        Delete connector.

        Enforces RESTRICT constraint - cannot delete if collections reference this connector.

        Args:
            connector_id: Connector ID to delete

        Raises:
            ValueError: If connector not found or collections reference it
            Exception: If database operation fails

        Example:
            >>> service.delete_connector(1)  # Raises ValueError if collections exist
        """
        connector = self.db.query(Connector).filter(Connector.id == connector_id).first()

        if not connector:
            raise ValueError(f"Connector with ID {connector_id} not found")

        # Check for referenced collections (RESTRICT constraint)
        collection_count = connector.collections.count()
        if collection_count > 0:
            logger.warning(
                f"Cannot delete connector with referenced collections",
                extra={"connector_id": connector_id, "collection_count": collection_count}
            )
            raise ValueError(
                f"Cannot delete connector '{connector.name}' because {collection_count} "
                f"collection(s) reference it. Delete or reassign collections first."
            )

        try:
            self.db.delete(connector)
            self.db.commit()

            logger.info(f"Deleted connector: {connector.name}", extra={"connector_id": connector_id})

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete connector: {str(e)}", extra={"connector_id": connector_id})
            raise

    def test_connector(self, connector_id: int) -> tuple[bool, str]:
        """
        Test connector connection using appropriate storage adapter.

        Updates connector's last_validated and last_error fields based on test result.

        Args:
            connector_id: Connector ID to test

        Returns:
            Tuple of (success: bool, message: str)

        Raises:
            ValueError: If connector not found or type not supported

        Example:
            >>> success, message = service.test_connector(1)
            >>> if success:
            ...     print(f"Connected: {message}")
            >>> else:
            ...     print(f"Failed: {message}")
        """
        connector = self.get_connector(connector_id, decrypt_credentials=True)

        if not connector:
            raise ValueError(f"Connector with ID {connector_id} not found")

        try:
            # Create appropriate adapter based on type
            if connector.type == ConnectorType.S3:
                adapter = S3Adapter(connector.decrypted_credentials)
            elif connector.type == ConnectorType.GCS:
                adapter = GCSAdapter(connector.decrypted_credentials)
            elif connector.type == ConnectorType.SMB:
                adapter = SMBAdapter(connector.decrypted_credentials)
            else:
                raise ValueError(f"Unsupported connector type: {connector.type}")

            # Test connection
            success, message = adapter.test_connection()

            # Update connector fields based on test result
            if success:
                connector.last_validated = datetime.utcnow()
                connector.last_error = None
            else:
                connector.last_error = message

            self.db.commit()

            logger.info(
                f"Tested connector: {connector.name}",
                extra={"connector_id": connector_id, "success": success, "test_message": message}
            )

            return success, message

        except Exception as e:
            # Update last_error on exception
            connector.last_error = f"Test failed with exception: {str(e)}"
            self.db.commit()

            logger.error(
                f"Connector test exception: {str(e)}",
                extra={"connector_id": connector_id}
            )

            return False, f"Test failed: {str(e)}"
