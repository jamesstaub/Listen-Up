from pydantic import BaseModel
from typing import Dict, Any, Optional
from shared.modules.job.models.command_spec import CommandSpec
from shared.modules.job.services.command_resolver import CommandResolver
from shared.modules.job.services.path_template_resolver import PathTemplateResolver


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
        
        # Use PathTemplateResolver for basic template resolution
        path_resolver = PathTemplateResolver()
        
        # Create minimal objects for PathTemplateResolver
        from types import SimpleNamespace
        
        # Create a simple job object with the necessary attributes
        job_obj = SimpleNamespace()
        job_obj.job_id = self.job_id
        job_obj.user_id = user_id
        job_obj.steps = []  # Not needed for basic template resolution
        
        # Create a simple step object with the necessary attributes  
        step_obj = SimpleNamespace()
        step_obj.step_id = self.step_id
        step_obj.get_composite_name = lambda: self.composite_name or self.step_id
        
        # Use PathTemplateResolver for basic template variable resolution
        resolved_value = path_resolver.resolve(value, job=job_obj, step=step_obj)
        
        # Convert relative storage paths to absolute paths
        if "/" in resolved_value and not resolved_value.startswith("/"):
            import os
            storage_root = os.getenv("STORAGE_ROOT", "/app/storage")
            resolved_value = os.path.join(storage_root, resolved_value)
        
        return resolved_value
