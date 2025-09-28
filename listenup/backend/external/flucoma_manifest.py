import os
from typing import List, Dict, Any, Tuple
from .base_manifest import BaseManifest


class FlucomaManifest(BaseManifest):
    """
    FluCoMa manifest for command construction in the backend.
    Constructs complete, safe commands to be executed by the flucoma_service.
    """
    
    def __init__(self, bin_dir=None):
        super().__init__()
        self.service_name = "flucoma_service"
        self.bin_dir = bin_dir or "/opt/flucoma-cli/FluidCorpusManipulation/bin"
        self.allowed_operations = self._get_allowed_operations()

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
        output_directory: str = "/tmp/outputs"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Construct FluCoMa command template with file placeholders.
        
        Args:
            operation: FluCoMa operation (e.g., "hpss", "pitch", etc.)
            inputs: List of input file URIs
            parameters: Operation parameters
            output_directory: Directory for output files (not used in template)
            
        Returns:
            tuple: (command_template_with_placeholders, file_mappings)
        """
        if not self.validate_operation(operation):
            raise ValueError(f"Unsupported FluCoMa operation: {operation}")

        # Get the executable name
        if operation == "force_error_test":
            # Force a command that doesn't exist to test error handling
            executable = "/nonexistent-flucoma-command"
        else:
            executable = f"{self.bin_dir}/fluid-{operation}"
        
        # Build command template with placeholders
        cmd_parts = [executable]
        input_mapping = {}
        output_mapping = {}
        
        # Add input file placeholders (support multiple inputs)
        input_specs = self._get_input_specification(operation)
        
        if len(input_specs) == 1 and len(inputs) > 1:
            # Operation expects single input flag but we have multiple inputs
            # Use the single flag with multiple sources
            flag = input_specs[0]['flag']
            for i, input_uri in enumerate(inputs):
                placeholder = f"{{INPUT_{i}}}"
                cmd_parts.extend([flag, placeholder])
                input_mapping[placeholder] = input_uri
        elif len(input_specs) > 1 and len(inputs) >= len(input_specs):
            # Operation expects multiple different input types
            for i, input_spec in enumerate(input_specs):
                if i < len(inputs):
                    placeholder = f"{{INPUT_{i}_{input_spec['type'].upper()}}}"
                    cmd_parts.extend([input_spec['flag'], placeholder])
                    input_mapping[placeholder] = inputs[i]
        else:
            # Standard case: single input type, potentially multiple files
            flag = input_specs[0]['flag'] if input_specs else "-source"
            for i, input_uri in enumerate(inputs):
                placeholder = f"{{INPUT_{i}}}"
                cmd_parts.extend([flag, placeholder])
                input_mapping[placeholder] = input_uri
        
        # Add output file placeholders based on operation (dynamic outputs)
        output_specs = self._get_output_specification(operation)
        for output_spec in output_specs:
            placeholder = output_spec['placeholder']
            flag = output_spec['flag']
            filename = output_spec['filename']
            
            cmd_parts.extend([flag, placeholder])
            output_mapping[placeholder] = filename
        
        # Add parameters (no placeholders needed for these)
        for key, value in parameters.items():
            if isinstance(value, list):
                # For list parameters like fftsettings, add each value as separate argument
                cmd_parts.extend([f"-{key}"] + [str(v) for v in value])
            else:
                cmd_parts.extend([f"-{key}", str(value)])
        
        command_template = " ".join(f'"{part}"' if " " in str(part) else str(part) for part in cmd_parts)
        
        print(f"🔨 Backend constructed FluCoMa command template: {command_template}")
        print(f"   Input mappings: {input_mapping}")
        print(f"   Output mappings: {output_mapping}")
        
        # Return command template and mapping dictionaries
        return command_template, {"input_mapping": input_mapping, "output_mapping": output_mapping}

    def _get_output_specification(self, operation: str) -> List[Dict[str, str]]:
        """
        Get the output specification for a given operation.
        
        Args:
            operation: FluCoMa operation name
            
        Returns:
            List of output specifications with placeholder, flag, and filename
        """
        output_specs = {
            "hpss": [
                {"placeholder": "{OUTPUT_HARMONIC}", "flag": "-harmonic", "filename": "hpss_harmonic.wav"},
                {"placeholder": "{OUTPUT_PERCUSSIVE}", "flag": "-percussive", "filename": "hpss_percussive.wav"}
            ],
            "pitch": [
                {"placeholder": "{OUTPUT_FEATURES}", "flag": "-features", "filename": "pitch_features.csv"}
            ],
            "ampslice": [
                {"placeholder": "{OUTPUT_INDICES}", "flag": "-indices", "filename": "ampslice_indices.csv"}
            ],
            "onsetslice": [
                {"placeholder": "{OUTPUT_INDICES}", "flag": "-indices", "filename": "onsetslice_indices.csv"}
            ],
            "noveltyslice": [
                {"placeholder": "{OUTPUT_INDICES}", "flag": "-indices", "filename": "noveltyslice_indices.csv"}
            ],
            "mfcc": [
                {"placeholder": "{OUTPUT_FEATURES}", "flag": "-features", "filename": "mfcc_features.csv"}
            ],
            "spectralshape": [
                {"placeholder": "{OUTPUT_FEATURES}", "flag": "-features", "filename": "spectralshape_features.csv"}
            ],
            "loudness": [
                {"placeholder": "{OUTPUT_FEATURES}", "flag": "-features", "filename": "loudness_features.csv"}
            ],
            "chroma": [
                {"placeholder": "{OUTPUT_FEATURES}", "flag": "-features", "filename": "chroma_features.csv"}
            ],
            "melband": [
                {"placeholder": "{OUTPUT_FEATURES}", "flag": "-features", "filename": "melband_features.csv"}
            ],
            # Operations that can have optional multiple outputs
            "nmf": [
                {"placeholder": "{OUTPUT_BASES}", "flag": "-bases", "filename": "nmf_bases.csv"},
                {"placeholder": "{OUTPUT_ACTIVATIONS}", "flag": "-activations", "filename": "nmf_activations.csv"}
            ],
            # Operations with single generic output
            "normalize": [
                {"placeholder": "{OUTPUT_MAIN}", "flag": "-destination", "filename": f"{operation}_output.wav"}
            ],
            "envelope": [
                {"placeholder": "{OUTPUT_MAIN}", "flag": "-destination", "filename": f"{operation}_output.wav"}
            ]
        }
        
        # Return specification for the operation, or generic single output as fallback
        return output_specs.get(operation, [
            {"placeholder": "{OUTPUT_MAIN}", "flag": "-destination", "filename": f"{operation}_output.wav"}
        ])

    def _get_input_specification(self, operation: str) -> List[Dict[str, str]]:
        """
        Get the input specification for a given operation.
        
        Args:
            operation: FluCoMa operation name
            
        Returns:
            List of input specifications with flag and type information
        """
        input_specs = {
            # Most operations use single -source flag
            "hpss": [{"flag": "-source", "type": "audio"}],
            "pitch": [{"flag": "-source", "type": "audio"}],
            "ampslice": [{"flag": "-source", "type": "audio"}],
            "mfcc": [{"flag": "-source", "type": "audio"}],
            "spectralshape": [{"flag": "-source", "type": "audio"}],
            
            # Operations that might need multiple different input types
            "nmf": [{"flag": "-source", "type": "audio"}],
            
            # Hypothetical operations that could take multiple input types
            # "compare": [
            #     {"flag": "-source1", "type": "audio"},
            #     {"flag": "-source2", "type": "audio"}
            # ],
            
            # Generic operations
            "normalize": [{"flag": "-source", "type": "audio"}],
            "envelope": [{"flag": "-source", "type": "audio"}]
        }
        
        # Return specification for the operation, or generic single source as fallback
        return input_specs.get(operation, [{"flag": "-source", "type": "audio"}])

    def _get_allowed_operations(self) -> Dict[str, str]:
        """
        Get allowed FluCoMa operations.
        
        Returns:
            Dict mapping operation names to their status
        """
        # Core FluCoMa operations that we support
        return {
            "hpss": "supported",
            "pitch": "supported", 
            "ampslice": "supported",
            "mfcc": "supported",
            "onsetslice": "supported",
            "noveltyslice": "supported",
            "transientslice": "supported",
            "spectralshape": "supported",
            "loudness": "supported",
            "chroma": "supported",
            "melband": "supported",
            "bark": "supported",
            "envelope": "supported",
            "stats": "supported",
            "normalize": "supported",
            "standardize": "supported",
            "scale": "supported",
            "umap": "supported",
            "pca": "supported",
            "kmeans": "supported",
            "dbscan": "supported",
            "hdbscan": "supported",
            "nmf": "supported"
        }

    def _create_output_files(self, operation: str, output_dir: str) -> List[str]:
        """
        Create output file paths based on operation type.
        
        Args:
            operation: FluCoMa operation name
            output_dir: Output directory
            
        Returns:
            List of expected output file paths
        """
        if operation == "hpss":
            # HPSS produces harmonic and percussive components
            return [
                f"{output_dir}/{operation}_harmonic.wav",
                f"{output_dir}/{operation}_percussive.wav"
            ]
        elif operation in ["pitch", "mfcc", "spectralshape", "loudness", "chroma", "melband", "bark"]:
            # Feature analysis operations produce CSV files
            return [f"{output_dir}/{operation}_features.csv"]
        elif operation == "ampslice":
            # Amplitude slicing produces indices
            return [f"{output_dir}/{operation}_indices.csv"]
        else:
            # Generic audio output
            return [f"{output_dir}/{operation}_output.wav"]

    def get_expected_outputs_count(self, operation: str) -> int:
        """
        Get the expected number of output files for a FluCoMa operation.
        
        Args:
            operation: The operation name
            
        Returns:
            int: Expected number of output files
        """
        if operation == "hpss":
            return 2  # harmonic + percussive
        else:
            return 1
