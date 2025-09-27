# Manifest loading and validation utilities

import json
import os
import tempfile
import uuid
from typing import List, Dict, Any, Tuple
from abc import ABC, abstractmethod


class Manifest(ABC):
    """
    Base class for microservice manifests. Handles command validation,
    construction, and execution coordination for specific microservice types.
    """
    
    def __init__(self, manifest_path=None):
        self.manifest_path = manifest_path
        self.manifest = None
        self.service_name = getattr(self, 'service_name', 'unknown')

    @abstractmethod
    def validate_operation(self, operation_name: str) -> bool:
        """
        Validate that the operation is supported by this microservice.
        
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
        temp_output_dir: str
    ) -> Tuple[str, List[str]]:
        """
        Construct the command to execute and expected output files.
        
        Args:
            operation: The operation to perform
            inputs: List of input file URIs
            parameters: Operation parameters
            temp_output_dir: Directory for temporary output files
            
        Returns:
            tuple: (command_string, expected_output_files)
        """
        pass

    def create_temp_output_dir(self) -> str:
        """Create a temporary directory for output files."""
        temp_dir = tempfile.mkdtemp(prefix=f"{self.service_name}_")
        print(f"📁 Created temp output directory: {temp_dir}")
        return temp_dir

    def download_inputs(self, input_uris: List[str], temp_dir: str) -> List[str]:
        """
        Download input files from URIs to local temporary files.
        
        Args:
            input_uris: List of input URIs (s3://, file://, etc.)
            temp_dir: Local directory for temporary files
            
        Returns:
            List of local file paths
        """
        local_files = []
        for i, uri in enumerate(input_uris):
            # For now, just create placeholder paths
            # TODO: Implement actual download logic based on URI scheme
            if uri.startswith('s3://'):
                filename = os.path.basename(uri)
                local_path = os.path.join(temp_dir, f"input_{i}_{filename}")
                print(f"📥 Would download {uri} to {local_path}")
                # Create empty file for testing
                with open(local_path, 'w') as f:
                    f.write(f"Mock content from {uri}")
                local_files.append(local_path)
            elif uri.startswith('file://'):
                local_path = uri[7:]  # Remove file:// prefix
                local_files.append(local_path)
            else:
                # Assume it's already a local path
                local_files.append(uri)
        
        return local_files

    def upload_outputs(self, local_files: List[str], job_id: str, step_name: str) -> List[str]:
        """
        Upload output files to storage and return URIs.
        
        Args:
            local_files: List of local file paths to upload
            job_id: Job identifier for organizing uploads
            step_name: Step name for organizing uploads
            
        Returns:
            List of uploaded file URIs
        """
        uploaded_uris = []
        for local_file in local_files:
            if os.path.exists(local_file):
                filename = os.path.basename(local_file)
                # TODO: Implement actual upload logic
                # For now, create mock URIs
                uri = f"s3://outputs/{job_id}/{step_name}/{filename}"
                print(f"📤 Would upload {local_file} to {uri}")
                uploaded_uris.append(uri)
            else:
                print(f"⚠️ Output file not found: {local_file}")
        
        return uploaded_uris

    def cleanup_temp_files(self, temp_dir: str):
        """Clean up temporary files and directory."""
        import shutil
        try:
            shutil.rmtree(temp_dir)
            print(f"🗑️ Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            print(f"⚠️ Failed to cleanup {temp_dir}: {str(e)}")

    # Legacy methods - kept for backward compatibility
    def parse_input_files(self, command: str) -> list:
        """Legacy method - use construct_command instead."""
        return []

    def parse_output_files(self, command: str) -> list:
        """Legacy method - use construct_command instead."""
        return []
