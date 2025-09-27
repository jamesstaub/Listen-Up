from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class StepTransition(BaseModel):
    """
    Defines how outputs from one step map to inputs of the next step.
    This allows for flexible pipeline configuration where steps can have
    mismatched input/output cardinalities.
    """
    from_step_id: str = Field(..., description="Source step ID")
    to_step_id: str = Field(..., description="Target step ID")
    output_to_input_mapping: List[int] = Field(
        default_factory=list,
        description="Indices mapping from_step.outputs to to_step.inputs"
    )
    
    class Config:
        json_encoders = {}
        
    def apply_mapping(self, source_outputs: List[str]) -> List[str]:
        """
        Apply the mapping to transform source outputs to target inputs.
        
        Args:
            source_outputs: List of output URIs from the source step
            
        Returns:
            List of URIs mapped according to the transition configuration
        """
        if not self.output_to_input_mapping:
            # If no mapping specified, pass all outputs
            return source_outputs
            
        mapped_outputs = []
        for index in self.output_to_input_mapping:
            if 0 <= index < len(source_outputs):
                mapped_outputs.append(source_outputs[index])
            else:
                # Log warning but don't fail - let the microservice handle missing inputs
                print(f"⚠️ Warning: Mapping index {index} out of range for {len(source_outputs)} outputs")
                
        return mapped_outputs
