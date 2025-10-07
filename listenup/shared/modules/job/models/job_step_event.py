from pydantic import BaseModel
from typing import Dict, Any
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

    def resolve_and_prepare(self, previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use CommandResolver to replace placeholders in command_spec
        based on resolved inputs and outputs.
        """
        resolved_inputs = self._resolve_inputs(previous_outputs)
        spec = CommandSpec(**self.command_spec)
        resolved_spec = CommandResolver.resolve(spec, resolved_inputs, self.outputs)

        payload = self.model_dump()
        payload["inputs"] = resolved_inputs
        payload["command_spec"] = resolved_spec.dict()
        return payload

    def _resolve_inputs(self, previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve placeholders in the inputs section using outputs from previous steps.
        """
        resolved_inputs = self.inputs.copy()
        for key, value in resolved_inputs.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                placeholder = value.strip("{}")
                if placeholder in previous_outputs:
                    resolved_inputs[key] = previous_outputs[placeholder]
        return resolved_inputs
