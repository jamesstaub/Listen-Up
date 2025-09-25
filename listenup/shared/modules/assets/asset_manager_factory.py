"""
Asset Manager Factory

This module provides a factory function to create the correct AssetManager
implementation based on environment variables. This decouples the main
application from the concrete storage provider.
"""
import os
from asset_manager_base import AssetManager
from local_asset_manager import LocalAssetManager
from s3_asset_manager import S3AssetManager

def create_asset_manager() -> AssetManager:
    """
    Factory function to create the appropriate AssetManager instance.

    It determines the implementation based on the `ASSET_STORAGE_PROVIDER`
    environment variable.

    Returns:
        AssetManager: A concrete implementation of the AssetManager.
    """
    provider = os.environ.get("ASSET_STORAGE_PROVIDER", "local").lower()
    
    if provider == "s3":
        bucket_name = os.environ.get("S3_BUCKET_NAME", "your-prod-bucket")
        region = os.environ.get("S3_REGION", "us-east-1")
        return S3AssetManager(bucket_name=bucket_name, region=region)
    else:
        # Default to local for development
        return LocalAssetManager()
