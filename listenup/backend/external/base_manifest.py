# Backend manifest base class for command construction

from typing import List, Dict, Any, Tuple
from abc import ABC, abstractmethod


class BaseManifest(ABC):
    """
    Base class for backend manifests. Responsible for constructing 
    safe, well-formed commands that will be sent to microservices.
    """
    
    def __init__(self):
        self.service_name = getattr(self, 'service_name', 'unknown')

    @abstractmethod
    def validate_operation(self, operation_name: str) -> bool:
        """
        Validate that the operation is supported by this service.
        
        Args:
            operation_name: The operation to validate
            
        Returns:
            bool: True if operation is valid
        """
        pass

    @abstractmethod
    def construct_command(
        self, 
        operation: str, 
        inputs: List[str], 
        parameters: Dict[str, Any],
        output_directory: str = "/tmp/outputs"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Construct the complete command template and file mappings.
        
        Args:
            operation: The operation to perform
            inputs: List of input file URIs (will be downloaded by microservice)
            parameters: Operation parameters
            output_directory: Directory for output files (microservice will create)
            
        Returns:
            tuple: (command_template_with_placeholders, file_mappings_dict)
        """
        pass

    def get_expected_outputs_count(self, operation: str) -> int:
        """
        Get the expected number of output files for an operation.
        Override in subclasses if needed.
        
        Args:
            operation: The operation name
            
        Returns:
            int: Expected number of output files
        """
        return 1
