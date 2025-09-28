from typing import List, Dict, Any, Tuple
from .base_manifest import BaseManifest


class LibrosaManifest(BaseManifest):
    """
    Librosa manifest for command construction in the backend.
    Constructs Python commands to be executed by the librosa_service.
    """
    
    def __init__(self):
        super().__init__()
        self.service_name = "librosa_service"
        self.allowed_operations = self._get_allowed_operations()

    def validate_operation(self, operation_name: str) -> bool:
        """
        Validate that the operation is supported by Librosa.
        
        Args:
            operation_name: The Librosa operation to validate
            
        Returns:
            bool: True if operation is valid
        """
        return operation_name in self.allowed_operations

    def construct_command(
        self, 
        operation: str, 
        inputs: List[str], 
        parameters: Dict[str, Any],
        output_directory: str = "/tmp/outputs"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Construct Librosa Python command template with file mappings.
        
        Args:
            operation: Librosa operation (e.g., "stft", "mfcc", etc.)
            inputs: List of input file URIs
            parameters: Operation parameters
            output_directory: Directory for output files
            
        Returns:
            tuple: (python_command_template, file_mappings_dict)
        """
        if not self.validate_operation(operation):
            raise ValueError(f"Unsupported Librosa operation: {operation}")

        # Create input and output mappings
        input_mapping = {}
        output_mapping = {}
        
        # Map input files to placeholders
        for i, input_uri in enumerate(inputs):
            placeholder = f"{{INPUT_{i}}}"
            input_mapping[placeholder] = input_uri
            
        # Get output specifications for this operation
        output_specs = self._get_librosa_output_specs(operation)
        for output_spec in output_specs:
            placeholder = output_spec['placeholder']
            filename = output_spec['filename']
            output_mapping[placeholder] = filename
        
        # Construct Python script template with placeholders
        python_script = self._generate_python_script_template(operation, input_mapping, output_mapping, parameters)
        
        # The command is the Python script itself
        command_template = f"python3 -c \"{python_script}\""
        
        print(f"🔨 Backend constructed Librosa command template: {command_template}")
        print(f"   Input mappings: {input_mapping}")
        print(f"   Output mappings: {output_mapping}")
        
        return command_template, {"input_mapping": input_mapping, "output_mapping": output_mapping}

    def _get_librosa_output_specs(self, operation: str) -> List[Dict[str, str]]:
        """
        Get output specifications for Librosa operations.
        
        Args:
            operation: Librosa operation name
            
        Returns:
            List of output specifications
        """
        output_specs = {
            "stft": [{"placeholder": "{OUTPUT_STFT}", "filename": "stft_result.npy"}],
            "mfcc": [{"placeholder": "{OUTPUT_MFCC}", "filename": "mfcc_features.npy"}],
            "spectral_centroid": [{"placeholder": "{OUTPUT_CENTROID}", "filename": "centroid_features.npy"}],
            "spectral_rolloff": [{"placeholder": "{OUTPUT_ROLLOFF}", "filename": "rolloff_features.npy"}],
            "spectral_bandwidth": [{"placeholder": "{OUTPUT_BANDWIDTH}", "filename": "bandwidth_features.npy"}],
            "chroma_stft": [{"placeholder": "{OUTPUT_CHROMA}", "filename": "chroma_features.npy"}],
            "tempo": [{"placeholder": "{OUTPUT_TEMPO}", "filename": "tempo_result.json"}],
            "beat_track": [{"placeholder": "{OUTPUT_BEATS}", "filename": "beat_result.json"}],
            "onset_detect": [{"placeholder": "{OUTPUT_ONSETS}", "filename": "onset_result.json"}],
            "harmonic": [{"placeholder": "{OUTPUT_HARMONIC}", "filename": "harmonic_component.npy"}],
            "percussive": [{"placeholder": "{OUTPUT_PERCUSSIVE}", "filename": "percussive_component.npy"}],
            "zero_crossing_rate": [{"placeholder": "{OUTPUT_ZCR}", "filename": "zcr_features.npy"}]
        }
        
        return output_specs.get(operation, [{"placeholder": "{OUTPUT_MAIN}", "filename": f"{operation}_output.npy"}])

    def _generate_python_script_template(
        self, 
        operation: str, 
        input_mapping: Dict[str, str], 
        output_mapping: Dict[str, str],
        parameters: Dict[str, Any]
    ) -> str:
        """
        Generate Python script template for the Librosa operation with placeholders.
        
        Args:
            operation: Librosa operation name
            input_mapping: Input placeholder to URI mapping
            output_mapping: Output placeholder to filename mapping
            parameters: Operation parameters
            
        Returns:
            str: Python script template with placeholders
        """
        script_lines = [
            "import librosa",
            "import numpy as np",
            "import json",
            "import os"
        ]
        
        # Load input files using placeholders
        for i, (placeholder, uri) in enumerate(input_mapping.items()):
            script_lines.append(f"y_{i}, sr_{i} = librosa.load('{placeholder}')")
        
        # Execute operation with placeholders for outputs
        if operation == "stft":
            output_placeholder = list(output_mapping.keys())[0]
            script_lines.extend([
                f"stft_result = librosa.stft(y_0)",
                f"np.save('{output_placeholder}', stft_result)"
            ])
        elif operation == "mfcc":
            n_mfcc = parameters.get("n_mfcc", 13)
            output_placeholder = list(output_mapping.keys())[0]
            script_lines.extend([
                f"mfcc_result = librosa.feature.mfcc(y=y_0, sr=sr_0, n_mfcc={n_mfcc})",
                f"np.save('{output_placeholder}', mfcc_result)"
            ])
        elif operation == "spectral_centroid":
            output_placeholder = list(output_mapping.keys())[0]
            script_lines.extend([
                f"centroid = librosa.feature.spectral_centroid(y=y_0, sr=sr_0)",
                f"np.save('{output_placeholder}', centroid)"
            ])
        elif operation == "tempo":
            output_placeholder = list(output_mapping.keys())[0]
            script_lines.extend([
                f"tempo, beats = librosa.beat.beat_track(y=y_0, sr=sr_0)",
                f"result = {{'tempo': float(tempo), 'beats': beats.tolist()}}",
                f"with open('{output_placeholder}', 'w') as f: json.dump(result, f)"
            ])
        # Add more operations as needed...
        
        # Join all lines with semicolons for single-line execution
        return "; ".join(script_lines)

    def _generate_python_script(
        self, 
        operation: str, 
        inputs: List[str], 
        parameters: Dict[str, Any],
        output_files: List[str]
    ) -> str:
        """
        Generate Python script for the Librosa operation.
        
        Args:
            operation: Librosa operation name
            inputs: Input file URIs
            parameters: Operation parameters
            output_files: Expected output file paths
            
        Returns:
            str: Python script as string
        """
        script_lines = [
            "import librosa",
            "import numpy as np",
            "import json",
            "import os"
        ]
        
        # Load input files
        for i, input_uri in enumerate(inputs):
            local_input = f"/tmp/inputs/input_{i}.wav"
            script_lines.append(f"y_{i}, sr_{i} = librosa.load('{local_input}')")
        
        # Execute operation
        if operation == "stft":
            script_lines.extend([
                f"stft_result = librosa.stft(y_0)",
                f"np.save('{output_files[0]}', stft_result)"
            ])
        elif operation == "mfcc":
            n_mfcc = parameters.get("n_mfcc", 13)
            script_lines.extend([
                f"mfcc_result = librosa.feature.mfcc(y=y_0, sr=sr_0, n_mfcc={n_mfcc})",
                f"np.save('{output_files[0]}', mfcc_result)"
            ])
        elif operation == "spectral_centroid":
            script_lines.extend([
                f"centroid = librosa.feature.spectral_centroid(y=y_0, sr=sr_0)",
                f"np.save('{output_files[0]}', centroid)"
            ])
        elif operation == "tempo":
            script_lines.extend([
                f"tempo, beats = librosa.beat.beat_track(y=y_0, sr=sr_0)",
                f"result = {{'tempo': float(tempo), 'beats': beats.tolist()}}",
                f"with open('{output_files[0]}', 'w') as f: json.dump(result, f)"
            ])
        
        # Join all lines with semicolons for single-line execution
        return "; ".join(script_lines)

    def _get_allowed_operations(self) -> Dict[str, str]:
        """
        Get allowed Librosa operations.
        
        Returns:
            Dict mapping operation names to their status
        """
        return {
            "stft": "supported",
            "mfcc": "supported",
            "spectral_centroid": "supported",
            "spectral_rolloff": "supported",
            "spectral_bandwidth": "supported",
            "zero_crossing_rate": "supported",
            "chroma_stft": "supported",
            "tempo": "supported",
            "beat_track": "supported",
            "onset_detect": "supported",
            "harmonic": "supported",
            "percussive": "supported"
        }

    def _create_output_files(self, operation: str, output_dir: str) -> List[str]:
        """
        Create output file paths based on operation type.
        
        Args:
            operation: Librosa operation name
            output_dir: Output directory
            
        Returns:
            List of expected output file paths
        """
        if operation in ["tempo", "beat_track"]:
            # Tempo/beat operations produce JSON files
            return [f"{output_dir}/{operation}_result.json"]
        elif operation in ["stft", "mfcc", "spectral_centroid", "spectral_rolloff", "chroma_stft"]:
            # Feature operations produce numpy arrays
            return [f"{output_dir}/{operation}_features.npy"]
        else:
            # Generic numpy output
            return [f"{output_dir}/{operation}_output.npy"]
