from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from ..enums.job_status_enum import JobStatus
from .job_step import JobStep
from .step_transition import StepTransition

class Job(BaseModel):
    job_id: str
    status: str = JobStatus.PENDING
    steps: List[JobStep] = Field(default_factory=list)
    step_transitions: List[StepTransition] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True  # Store enums as plain strings for Mongo/Redis
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    # --- Convenience methods ---
    def is_pending(self) -> bool:
        return self.status == JobStatus.PENDING

    def is_processing(self) -> bool:
        return self.status == JobStatus.PROCESSING

    def is_complete(self) -> bool:
        return self.status == JobStatus.COMPLETE

    def is_failed(self) -> bool:
        return self.status == JobStatus.FAILED

    def get_current_step(self) -> Optional[JobStep]:
        """Return the first non-complete step, or None if all are done."""
        for step in self.steps:
            if not step.is_complete():
                return step
        return None
    
    def get_transition_for_steps(self, from_step_id: str, to_step_id: str) -> Optional[StepTransition]:
        """Find the transition mapping between two specific steps."""
        for transition in self.step_transitions:
            if transition.from_step_id == from_step_id and transition.to_step_id == to_step_id:
                return transition
        return None
    
    def get_mapped_inputs_for_next_step(self, completed_step_id: str, completed_outputs: List[str]) -> List[str]:
        """
        Get the mapped inputs for the next step based on completed step outputs.
        
        Args:
            completed_step_id: ID of the step that just completed
            completed_outputs: Output URIs from the completed step
            
        Returns:
            List of URIs mapped for the next step's inputs
        """
        # Find the completed step and next step
        completed_step_index = None
        for i, step in enumerate(self.steps):
            if step.step_id == completed_step_id:
                completed_step_index = i
                break
                
        if completed_step_index is None or completed_step_index >= len(self.steps) - 1:
            return []  # No next step or step not found
            
        next_step = self.steps[completed_step_index + 1]
        
        # Find transition mapping
        transition = self.get_transition_for_steps(completed_step_id, next_step.step_id)
        
        if transition:
            mapped_outputs = transition.apply_mapping(completed_outputs)
            print(f"🗺️ Applied mapping {completed_step_id}→{next_step.step_id}: {len(completed_outputs)} → {len(mapped_outputs)}")
            return mapped_outputs
        else:
            # No explicit mapping - pass all outputs
            print(f"📋 No mapping configured - passing all {len(completed_outputs)} outputs as inputs")
            return completed_outputs