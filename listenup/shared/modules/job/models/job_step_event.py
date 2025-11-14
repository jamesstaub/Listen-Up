from pydantic import BaseModel
from typing import Dict, Any, Optional
from shared.modules.job.models.command_spec import CommandSpec
from shared.modules.job.command_resolver import CommandResolver


class JobStepEvent(BaseModel):
    job_id: str
    step_id: str
    step_name: str
    microservice: str
    command_spec: Dict[str, Any]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    composite_name: Optional[str] = None  # Add composite name for template resolution

    def resolve_and_prepare(self, previous_outputs: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Use CommandResolver to replace placeholders in command_spec
        based on resolved inputs and outputs.
        """
        resolved_inputs = self._resolve_inputs(previous_outputs, user_id)
        resolved_outputs = self._resolve_outputs(user_id)
        
        spec = CommandSpec(**self.command_spec)
        resolved_spec = CommandResolver.resolve(spec, resolved_inputs, resolved_outputs)

        payload = self.model_dump()
        payload["inputs"] = resolved_inputs
        payload["outputs"] = resolved_outputs
        payload["command_spec"] = resolved_spec.dict()
        return payload

    def _resolve_inputs(self, previous_outputs: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Resolve placeholders in the inputs section using outputs from previous steps.
        """
        resolved_inputs = self.inputs.copy()
        for key, value in resolved_inputs.items():
            if isinstance(value, str):
                value = self._resolve_template_variables(value, user_id)
                if value.startswith("{{") and value.endswith("}}"):
                    placeholder = value.strip("{}")
                    if placeholder in previous_outputs:
                        resolved_inputs[key] = previous_outputs[placeholder]
                else:
                    resolved_inputs[key] = value
        return resolved_inputs

    def _resolve_outputs(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Resolve template variables in outputs section.
        """
        resolved_outputs = {}
        for key, value in self.outputs.items():
            if isinstance(value, str):
                resolved_outputs[key] = self._resolve_template_variables(value, user_id)
            else:
                resolved_outputs[key] = value
        return resolved_outputs

    def _resolve_template_variables(self, value: str, user_id: Optional[str] = None) -> str:
        """
        Resolve job-level template variables like {{job_id}}, {{user_id}}, {{step_id}}, and {{composite_name}}.
        Convert relative storage paths to absolute paths.
        """
        if not isinstance(value, str):
            return value
        
        # Replace job_id template variable
        value = value.replace("{{job_id}}", self.job_id)
        
        # Replace step_id template variable
        value = value.replace("{{step_id}}", self.step_id)
        
        # Replace composite_name template variable if available
        if self.composite_name:
            value = value.replace("{{composite_name}}", self.composite_name)
        
        # Replace user_id template variable if provided
        if user_id:
            value = value.replace("{{user_id}}", user_id)
        
        # Convert relative storage paths to absolute paths
        if "/" in value and not value.startswith("/"):
            import os
            storage_root = os.getenv("STORAGE_ROOT", "/app/storage")
            value = os.path.join(storage_root, value)
        
        return value
