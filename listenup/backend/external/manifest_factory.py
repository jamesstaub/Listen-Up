from typing import Optional
from .base_manifest import BaseManifest
from .flucoma_manifest import FlucomaManifest
from .librosa_manifest import LibrosaManifest


class ManifestFactory:
    """
    Factory class for creating appropriate manifest instances based on service names.
    """
    
    _manifests = {
        "flucoma_service": FlucomaManifest,
        "librosa_service": LibrosaManifest
    }
    
    @classmethod
    def create_manifest(cls, service_name: str) -> BaseManifest:
        """
        Create a manifest instance for the specified service.
        
        Args:
            service_name: Name of the microservice
            
        Returns:
            BaseManifest: Appropriate manifest instance
            
        Raises:
            ValueError: If service is not supported
        """
        if service_name not in cls._manifests:
            raise ValueError(f"No manifest available for service: {service_name}")
        
        manifest_class = cls._manifests[service_name]
        return manifest_class()
    
    @classmethod
    def get_supported_services(cls) -> list:
        """
        Get list of supported service names.
        
        Returns:
            list: List of supported service names
        """
        return list(cls._manifests.keys())
    
    @classmethod
    def register_manifest(cls, service_name: str, manifest_class: type):
        """
        Register a new manifest class for a service.
        
        Args:
            service_name: Name of the microservice
            manifest_class: Manifest class to register
        """
        cls._manifests[service_name] = manifest_class
