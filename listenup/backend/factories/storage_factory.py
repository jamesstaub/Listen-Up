"""
Storage Factory for creating environment and user-specific storage managers.
"""
import os
from typing import Optional
from shared.modules.storage.backends.LocalFilesystemBackend import LocalFilesystemBackend
from shared.modules.storage.backends.StorageBackend import StorageBackend
from shared.modules.storage.storage_manager import StorageManager


class StorageFactory:
    """
    Factory for creating StorageManager instances based on environment and user context.
    """
    
    @staticmethod
    # TODO: maybe rename this filestore_manager globally to be more specific
    def create_storage_manager(user_id: Optional[str] = None) -> StorageManager:
        """
        Create a StorageManager instance based on environment and user context.
        
        Args:
            user_id: Optional user ID for user-specific storage configuration
            
        Returns:
            StorageManager: Configured storage manager instance
        """
        environment = os.getenv("ENVIRONMENT", "development")
        storage_root = os.getenv("STORAGE_ROOT", "/app/storage")
        
        if environment == "production":
            # In production, could use user-specific buckets
            backend = StorageFactory._create_production_backend(user_id, storage_root)
        else:
            # Development/testing uses local filesystem
            backend = LocalFilesystemBackend(storage_root)
        
        return StorageManager(backend)
    
    @staticmethod
    def _create_production_backend(user_id: Optional[str] = None, storage_root: str = "/app/storage") -> StorageBackend:
        """
        Create production storage backend (S3, GCS, etc.) with optional user-specific configuration.
        """
        # For now, still use LocalFilesystemBackend
        # Later this could be:
        # if user_id:
        #     bucket_name = f"user-data-{user_id}"
        #     return S3Backend(bucket_name=bucket_name)
        # else:
        #     bucket_name = os.getenv("DEFAULT_S3_BUCKET", "app-storage")
        #     return S3Backend(bucket_name=bucket_name)
        
        return LocalFilesystemBackend(storage_root)