import os
import subprocess
from typing import List, Dict, Any, Tuple
from microservices_shared.modules.job.manifest import Manifest

class FlucomaManifest(Manifest):
    
    def __init__(self, manifest_path=None, bin_dir=None):
        super().__init__(manifest_path)
        self.service_name = "flucoma_service"
        self.bin_dir = bin_dir or os.environ.get("FLUCOMA_BIN_DIR", "/opt/flucoma-cli/FluidCorpusManipulation/bin")
        self.allowed_operations = self._load_available_operations()

    def validate_operation(self, operation_name: str) -> bool:
        """
        Validate that the operation is supported by FluCoMa.
        
        Args:
            operation_name: The FluCoMa operation to validate
            
        Returns:
            bool: True if operation is valid
        """
        return operation_name in self.allowed_operations

    def construct_command(
        self, 
        operation: str, 
        inputs: List[str], 
        parameters: Dict[str, Any],
        temp_output_dir: str
    ) -> Tuple[str, List[str]]:
        """
        Construct FluCoMa command and expected output files.
        
        Args:
            operation: FluCoMa operation (e.g., "ampslice", "mfcc", etc.)
            inputs: List of local input file paths
            parameters: Operation parameters
            temp_output_dir: Directory for temporary output files
            
        Returns:
            tuple: (command_string, expected_output_files)
        """
        if not self.validate_operation(operation):
            raise ValueError(f"Unsupported FluCoMa operation: {operation}")

        # Get the executable path
        executable = self.allowed_operations[operation]
        
        # Create output file paths based on operation
        output_files = self._create_output_files(operation, temp_output_dir)
        
        # Build command arguments
        cmd_parts = [executable]
        
        # Add input files
        for input_file in inputs:
            cmd_parts.extend(["-source", input_file])
        
        # Add output files
        if operation == "ampslice":
            cmd_parts.extend(["-indices", output_files[0]])
            if len(output_files) > 1:
                cmd_parts.extend(["-slices", output_files[1]])
        elif operation == "mfcc":
            cmd_parts.extend(["-features", output_files[0]])
        elif operation == "hpss":
            # HPSS requires harmonic and percussive output buffers
            cmd_parts.extend(["-harmonic", output_files[0]])      # harmonic component
            cmd_parts.extend(["-percussive", output_files[1]])    # percussive component
            if len(output_files) > 2:
                cmd_parts.extend(["-residual", output_files[2]])  # residual (optional)
        elif operation == "pitch":
            # Pitch analysis outputs features to CSV
            cmd_parts.extend(["-features", output_files[0]])
        else:
            # Generic output
            cmd_parts.extend(["-destination", output_files[0]])
        
        # Add parameters
        for key, value in parameters.items():
            if isinstance(value, list):
                # For list parameters like fftsettings, join with spaces
                cmd_parts.extend([f"-{key}", " ".join(map(str, value))])
            else:
                cmd_parts.extend([f"-{key}", str(value)])
        
        command = " ".join(cmd_parts)
        
        print(f"🔨 Constructed FluCoMa command: {command}")
        return command, output_files

    def _load_available_operations(self) -> Dict[str, str]:
        """
        Load available FluCoMa operations from the bin directory.
        
        Returns:
            Dict mapping operation names to executable paths
        """
        operations = {}
        
        if not os.path.isdir(self.bin_dir):
            raise RuntimeError(f"FluCoMa bin directory not found: {self.bin_dir}")
        
        for filename in os.listdir(self.bin_dir):
            if filename.startswith('fluid-'):
                operation_name = filename.replace('fluid-', '').lower()
                full_path = os.path.join(self.bin_dir, filename)
                if os.access(full_path, os.X_OK):
                    operations[operation_name] = full_path
        
        if not operations:
            raise RuntimeError(f"No executable FluCoMa operations found in {self.bin_dir}")
            
        print(f"📋 Loaded {len(operations)} FluCoMa operations")
        return operations

    def _create_output_files(self, operation: str, temp_output_dir: str) -> List[str]:
        """
        Create expected output file paths for a given operation.
        
        Args:
            operation: The FluCoMa operation
            temp_output_dir: Directory for temporary files
            
        Returns:
            List of expected output file paths
        """
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        if operation == "ampslice":
            return [
                os.path.join(temp_output_dir, f"ampslice_indices_{unique_id}.txt"),
                os.path.join(temp_output_dir, f"ampslice_slices_{unique_id}.wav")
            ]
        elif operation == "mfcc":
            return [
                os.path.join(temp_output_dir, f"mfcc_features_{unique_id}.csv")
            ]
        elif operation == "spectralshape":
            return [
                os.path.join(temp_output_dir, f"spectralshape_features_{unique_id}.csv")
            ]
        elif operation == "hpss":
            # HPSS produces harmonic, percussive, and optionally residual components
            return [
                os.path.join(temp_output_dir, f"hpss_harmonic_{unique_id}.wav"),      # Index 0: harmonic component
                os.path.join(temp_output_dir, f"hpss_percussive_{unique_id}.wav"),   # Index 1: percussive component  
                os.path.join(temp_output_dir, f"hpss_residual_{unique_id}.wav")      # Index 2: residual (if maskingmode=2)
            ]
        elif operation == "pitch":
            # Pitch analysis produces features as CSV
            return [
                os.path.join(temp_output_dir, f"pitch_features_{unique_id}.csv")
            ]
        else:
            # Generic output
            return [
                os.path.join(temp_output_dir, f"{operation}_output_{unique_id}.dat")
            ]

    # Legacy methods for backward compatibility
    def validate_action(self, action_name):
        return self.validate_operation(action_name)

    def validate_parameters(self, action_name, parameters):
        # For now, accept any parameters
        return True

    def validate_job(self, action_name, parameters):
        return self.validate_operation(action_name) and self.validate_parameters(action_name, parameters)
