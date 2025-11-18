import uuid
from datetime import datetime
import json
import hashlib
from typing import Optional, Dict, Any, List
from shared.modules.job.models.command_spec import CommandSpec
from pydantic import BaseModel, Field
from shared.modules.job.enums.job_step_status_enum import JobStepStatus

class JobStep(BaseModel):
    """
    Represents a single step in a Job.
    Shared between backend, microservice, and orchestration layers.
    """
    name: str
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order: Optional[int] = None 
    command_spec: Optional[CommandSpec] = None
    status: JobStepStatus = JobStepStatus.PENDING
    inputs: Dict[str, Any] = Field(default_factory=dict)    # Cloud URIs or job outputs
    outputs: Dict[str, Any] = Field(default_factory=dict)   # Output artifacts (URIs or local paths)
    log_tail: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    microservice: Optional[str] = None                      # Which service should run it

    # --- Business logic queries (no persistence) ---
    def is_complete(self) -> bool:
        return self.status == JobStepStatus.COMPLETE

    def is_failed(self) -> bool:
        return self.status == JobStepStatus.FAILED
    
    def is_running(self) -> bool:
        return self.status == JobStepStatus.RUNNING

    @staticmethod
    def params_hash(params: Dict[str, Any]) -> str:
        """
        Create a stable MD5 hash for a step's parameters.

        This is useful for deduplication/caching across runs. It sorts the
        parameters to produce a consistent digest regardless of key order.
        """
        try:
            sorted_params = json.dumps(params or {}, sort_keys=True, separators=(',', ':'))
        except Exception:
            # Fallback to string conversion if params can't be JSON serialized
            sorted_params = str(params or "")
        return hashlib.md5(sorted_params.encode('utf-8')).hexdigest()

    def get_composite_name(self) -> str:
        """
        Generate a composite directory name: <order>_<service>_<program>_<param_hash>
        
        This creates semantic, readable, and cacheable directory names that include:
        - Step order for sorting
        - Service name for identification
        - Program name for the specific operation
        - Parameter hash for caching/deduplication
        
        Example: "000_flucoma_service_fluid-hpss_a1b2c3d4"
        """
        # Get order with zero-padding
        order_str = f"{self.order:03d}" if self.order is not None else "000"
        
        # Get service name (fallback to 'unknown')
        service_name = self.microservice or "unknown"
        
        # Get program name from command spec (fallback to 'unknown')
        program_name = "unknown"
        if self.command_spec and self.command_spec.program:
            program_name = self.command_spec.program
        
        # Create parameter hash from command spec flags
        params_to_hash = {}
        if self.command_spec and self.command_spec.flags:
            params_to_hash = self.command_spec.flags
        param_hash = self.params_hash(params_to_hash)[:8]  # Use first 8 chars for readability
        
        return f"{order_str}_{service_name}_{program_name}_{param_hash}"
