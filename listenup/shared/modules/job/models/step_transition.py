from pydantic import BaseModel, Field
from typing import Dict, Any

class StepTransition(BaseModel):
    """
    Defines how outputs from one step map to inputs of the next step.
    Allows flexible pipeline configuration where steps can have
    different input/output names.
    """
    from_step_id: str = Field(..., description="Source step ID")
    to_step_id: str = Field(..., description="Target step ID")
    output_to_input_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of source output key -> target input key"
    )

    def apply_mapping(self, source_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply the mapping to transform source outputs to target inputs.

        Args:
            source_outputs: Dict of outputs from the source step {key: value}

        Returns:
            Dict of mapped inputs for the target step {target_input_key: value}
        """
        mapped_inputs = {}
        for src_key, tgt_key in self.output_to_input_mapping.items():
            if src_key in source_outputs:
                mapped_inputs[tgt_key] = source_outputs[src_key]
            else:
                # Log warning if the expected output key is missing
                print(f"⚠️ Warning: Source output '{src_key}' not found in step {self.from_step_id}")
        return mapped_inputs
