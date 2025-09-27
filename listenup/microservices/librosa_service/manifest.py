import os
from typing import List, Dict, Any, Tuple
from microservices_shared.modules.job.manifest import Manifest

class LibrosaManifest(Manifest):
    
    def __init__(self, manifest_path=None):
        super().__init__(manifest_path)
        self.service_name = "librosa_service"
        # Basic librosa operations that we support
        self.supported_operations = {
            "spectral_features": "Extract spectral features (mfcc, chroma, spectral_centroid)",
            "tempo_beat": "Extract tempo and beat tracking information",
            "onset_detection": "Detect onset times in audio",
            "harmonic_percussive": "Separate harmonic and percussive components"
        }

    def validate_operation(self, operation_name: str) -> bool:
        """
        Validate that the operation is supported by Librosa.
        
        Args:
            operation_name: The librosa operation to validate
            
        Returns:
            bool: True if operation is valid
        """
        return operation_name in self.supported_operations

    def construct_command(
        self, 
        operation: str, 
        inputs: List[str], 
        parameters: Dict[str, Any],
        temp_output_dir: str
    ) -> Tuple[str, List[str]]:
        """
        Construct librosa processing command and expected output files.
        
        Args:
            operation: Librosa operation (e.g., "spectral_features", "tempo_beat", etc.)
            inputs: List of local input file paths
            parameters: Operation parameters
            temp_output_dir: Directory for temporary output files
            
        Returns:
            tuple: (command_string, expected_output_files)
        """
        if not self.validate_operation(operation):
            raise ValueError(f"Unsupported Librosa operation: {operation}")

        if not inputs:
            raise ValueError("No input files provided for librosa operation")

        # Create output file paths
        output_files = self._create_output_files(operation, inputs[0], temp_output_dir)
        
        # Build Python command to execute librosa operations
        cmd_parts = [
            "python", "-c",
            f"\"import librosa; import numpy as np; import json; "
            f"from librosa_processor import process_{operation}; "
            f"result = process_{operation}('{inputs[0]}', {repr(parameters)}); "
            f"with open('{output_files[0]}', 'w') as f: json.dump(result, f)\""
        ]
        
        command = " ".join(cmd_parts)
        print(f"🔨 Constructed Librosa command: {command}")
        return command, output_files

    def _create_output_files(self, operation: str, input_file: str, temp_output_dir: str) -> List[str]:
        """Create output file paths based on operation and input."""
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        
        if operation == "spectral_features":
            return [os.path.join(temp_output_dir, f"{base_name}_spectral_features.json")]
        elif operation == "tempo_beat":
            return [os.path.join(temp_output_dir, f"{base_name}_tempo_beat.json")]
        elif operation == "onset_detection":
            return [os.path.join(temp_output_dir, f"{base_name}_onsets.json")]
        elif operation == "harmonic_percussive":
            return [
                os.path.join(temp_output_dir, f"{base_name}_harmonic.wav"),
                os.path.join(temp_output_dir, f"{base_name}_percussive.wav")
            ]
        else:
            return [os.path.join(temp_output_dir, f"{base_name}_{operation}.json")]

    def parse_input_files(self, command: str) -> list:
        """
        For Librosa, assume the first argument with a file extension is the input file.
        """
        args = command.split()
        for arg in args:
            if "." in arg and not arg.startswith("-"):
                return [arg]
        return []

    def parse_output_files(self, command: str) -> list:
        """
        For Librosa, assume all subsequent arguments with file extensions are output files.
        """
        args = command.split()
        found_input = False
        outputs = []
        for arg in args:
            if "." in arg and not arg.startswith("-"):
                if not found_input:
                    found_input = True
                else:
                    outputs.append(arg)
        return outputs
