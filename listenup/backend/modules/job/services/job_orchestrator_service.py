
from shared.modules.storage.backends.LocalFilesystemBackend import LocalFilesystemBackend
from shared.modules.storage.backends.StorageBackend import StorageBackend
from shared.modules.storage.storage_manager import StorageManager
from shared.modules.job.models.step_transition import StepTransition
from shared.modules.job.models.command_spec import CommandSpec
from shared.modules.job.models.job import Job, JobStatus, JobStep
from shared.modules.job.enums.job_step_status_enum import JobStepStatus
from shared.modules.job.models.job_step_event import JobStepEvent
from shared.modules.job.services.command_resolver import CommandResolver
from shared.modules.queue.redis_client import RedisQueueClient
from backend.modules.job.models.job_model import JobModel

from typing import Dict, Any
import uuid
import os
from datetime import datetime

class JobOrchestratorService:
    """
    Orchestrates multi-step jobs via async event-driven queue.
    Dispatches steps to microservices and listens for completion events.
    """

    def __init__(self, mongo_db, storage: StorageManager, job_step_storage_service):
        self.job_model = JobModel(mongo_db)
        self.queue_clients = {}  # cache service queues
        self.resolver = CommandResolver()
        self.storage = storage
        self.job_step_storage_service = job_step_storage_service

    def create_job(self, job_payload: dict) -> dict:
        """
        Create a Job with flat steps (no StepGroups), persist, and dispatch first steps.
        """
        job_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        user_id = job_payload.get("user_id")

        # Build JobSteps
        steps_data = job_payload.get("steps", [])
        job_steps = []
        for order, step_data in enumerate(steps_data):
            step = JobStep(
                name=step_data["name"],
                microservice=step_data["service"],
                command_spec=CommandSpec(**step_data.get("command_spec", {})),
                inputs=step_data.get("inputs", {}),
                outputs=step_data.get("outputs", {}),
                order=order
            )
            job_steps.append(step)

        # Build StepTransitions using composite names instead of step names
        transitions_data = job_payload.get("step_transitions", [])
        step_transitions = []
        step_name_to_id = {s.name: s.step_id for s in job_steps}
        # step_name_to_composite = {s.name: s.get_composite_name() for s in job_steps}
        
        for t in transitions_data:
            from_name, to_name = t["from_step_name"], t["to_step_name"]
            if from_name in step_name_to_id and to_name in step_name_to_id:
                step_transitions.append(
                    StepTransition(
                        from_step_id=step_name_to_id[from_name],
                        to_step_id=step_name_to_id[to_name],
                        output_to_input_mapping=t.get("output_to_input_mapping", {})
                    )
                )

        # Persist job
        job = Job(
            job_id=job_id,
            user_id=user_id,
            steps=job_steps,
            step_transitions=step_transitions,
            status=JobStatus.PENDING,
            created_at=created_at
        )
        self.job_model.create_job(job)

        # Pre-create all directory structure for this job workflow
        self.job_step_storage_service._prepare_job_directory_structure(job)

        # Dispatch first steps that have no dependencies
        for step in job.steps:
            if not any(t.to_step_id == step.step_id for t in job.step_transitions):
                self._dispatch_step(job, step)

        return job.dict()

    # TODO: move these to job model or helper
    def get_job(self, job_id: str) -> dict | None:
        """
        Retrieve a job by ID from the database.
        """
        job = self.job_model.get_job(job_id)
        if job:
            return job.dict()
        return None

    def retry_job(self, job_id: str) -> dict:
        """
        Retry a failed or incomplete job from the first non-complete step.
        """
        job = self.job_model.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Find the first non-complete step
        resume_step = None
        for i, step in enumerate(job.steps):
            if step.status != JobStepStatus.COMPLETE:
                resume_step = step
                break
        
        if not resume_step:
            raise ValueError(f"Job {job_id} is already complete")
        
        # Update job status to processing and dispatch the step
        self.job_model.update_job_status(job_id, JobStatus.PROCESSING)
        self._dispatch_step(job, resume_step)
        
        return {
            "status": "retrying",
            "job_id": job_id,
            "resume_step": resume_step.name,
            "step_index": resume_step.order
        }

    # -------------------------------------------------------------------------
    # Storage management
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Queue utils
    # -------------------------------------------------------------------------
    def _get_service_queue(self, microservice_name: str):
        """Return or create a Redis queue for a given microservice."""
        if microservice_name not in self.queue_clients:
            self.queue_clients[microservice_name] = RedisQueueClient(
                queue_name=f"{microservice_name}_requests"
            )
        return self.queue_clients[microservice_name]

    # -------------------------------------------------------------------------
    # Dispatch logic
    # -------------------------------------------------------------------------
    def _dispatch_step(self, job: Job, step: JobStep) -> None:
        """Send a step to its microservice queue."""

        if not step.microservice:
            print(f"❌ Step {step.name} has no microservice defined!")
            return
    
        # All outputs now go to job-step directories using composite names
        composite_name = step.get_composite_name()
        job_step_path = f"users/{job.user_id}/jobs/{job.job_id}/{composite_name}" if job.user_id else "none"
        
        self.job_model.update_job_step_status(job.job_id, step.step_id, JobStepStatus.PROCESSING)

        # Gather previous outputs via StepTransition
        previous_outputs = {}
        for transition in job.step_transitions:
            if transition.to_step_id == step.step_id:
                previous_outputs.update(self.job_model.get_step_outputs(job.job_id, transition.from_step_id))

        # Build the event and resolve it
        composite_name = step.get_composite_name()
        step_event = JobStepEvent(
            job_id=job.job_id,
            step_id=step.step_id,
            step_name=step.name,
            microservice=step.microservice,
            command_spec=step.command_spec.dict() if step.command_spec else {},
            inputs=step.inputs,
            outputs=step.outputs,
            composite_name=composite_name
        )

        resolved_payload = step_event.resolve_and_prepare(previous_outputs, job.user_id)

        # Push to queue
        queue = self._get_service_queue(step.microservice)
        queue.push_event(resolved_payload)
        print(f"📤 Dispatched step {step.name} -> {step.microservice}")
        print(f"🗂️ Job-step directory: {job_step_path}")
        
        # Log the resolved paths for debugging
        if resolved_payload.get("inputs"):
            print(f"🔗 Resolved inputs: {resolved_payload['inputs']}")
        if resolved_payload.get("outputs"):
            print(f"🎯 Resolved outputs: {resolved_payload['outputs']}")

    # -------------------------------------------------------------------------
    # Step status event handler (called from BackendQueueService)
    # -------------------------------------------------------------------------
    def handle_step_status_event(self, event: Dict[str, Any]):
        """
        Handle step status events from the microservice queue.
        """
        job_id = event.get("job_id")
        step_id = event.get("step_id")
        status_raw = event.get("status")
        outputs = event.get("outputs", {})

        if not job_id or not step_id or not status_raw:
            print(f"❌ Invalid status event: missing required fields {job_id=} {step_id=} {status_raw=}")
            return

        # Convert status string to JobStepStatus enum
        if isinstance(status_raw, str):
            try:
                status = JobStepStatus(status_raw)
            except ValueError:
                print(f"❌ Invalid status value: {status_raw}")
                return
        else:
            status = status_raw

        print(f"⚙️ Handling status event: {job_id=} {step_id=} {status=}")

        job = self.job_model.get_job(job_id)
        if not job:
            print(f"❌ Job {job_id} not found in DB")
            return

        # Update job step status in DB
        self.job_model.update_job_step_status(job_id, step_id, status, outputs=outputs)

        # CRITICAL: Fetch fresh job data after status update to avoid stale data
        job = self.job_model.get_job(job_id)
        if not job:
            print(f"❌ Job {job_id} not found after update")
            return

        # Handle status types
        if status == JobStepStatus.COMPLETE:
            # Find all steps that are now ready to run (have all inputs available)
            ready_steps = self._get_ready_steps(job)
            if ready_steps:
                for ready_step in ready_steps:
                    print(f"➡️ Dispatching ready step: {ready_step.name}")
                    self._dispatch_step(job, ready_step)
            else:
                # No more steps are ready - check if job is complete
                if self._is_job_complete(job):
                    print(f"✅ Job {job_id} fully completed")
                    self.job_model.update_job_status(job_id, JobStatus.COMPLETE)
                else:
                    print(f"⏳ Job {job_id} waiting for more dependencies")

        elif status == JobStepStatus.FAILED:
            print(f"💥 Step {step_id} failed; marking job {job_id} as FAILED")
            self.job_model.update_job_status(job_id, JobStatus.FAILED)

        elif status == JobStepStatus.PROCESSING:
            print(f"🛠 Step {step_id} is processing... (no action needed)")

    # -------------------------------------------------------------------------
    # Step progression logic
    # -------------------------------------------------------------------------
    def _get_ready_steps(self, job: Job):
        """
        Return all steps that are ready to run (have all inputs available and are not already running/complete).
        
        FUTURE EXTENSION NOTES:
        - This method currently handles 1:1 step relationships
        - For fan-out patterns (1 step → N dynamic steps), we'll need to:
          1. Check for steps with 'dynamic_parallelism' configuration
          2. Enumerate outputs from completed dependency steps
          3. Generate multiple step instances dynamically
          4. Each instance gets a subset of the outputs as inputs
        - For now, we maintain simple static step relationships
        """
        ready_steps = []
        
        for step in job.steps:
            # Skip steps that are already running, complete, or failed
            current_status = getattr(step, 'status', JobStepStatus.PENDING)
            
            if current_status in [JobStepStatus.PROCESSING, JobStepStatus.COMPLETE, JobStepStatus.FAILED]:
                print(f"🔄 Skipping step '{step.name}' (current_status={current_status})")
                continue
                
            # Check if all inputs for this step are available
            if self._are_step_inputs_ready(job, step):
                print(f"✅ Step '{step.name}' is ready to run")
                # Resolve inputs from completed dependency steps
                self._resolve_step_inputs(job, step)
                ready_steps.append(step)
            else:
                print(f"⏳ Step '{step.name}' is not ready (dependencies incomplete)")
        
        # TODO: Future extension point for dynamic step generation
        # ready_steps.extend(self._generate_dynamic_steps(job))
        
        return ready_steps
    
    def _are_step_inputs_ready(self, job: Job, step):
        """
        Check if all required inputs for a step are available from completed dependency steps.
        
        This method handles both simple dependencies and fan-in scenarios:
        - Simple: Step A → Step B (1:1)
        - Fan-out: Step A → [Step B1, Step B2, Step B3] (1:N) 
        - Fan-in: [Step B1, Step B2, Step B3] → Step C (N:1) ← THIS IS THE KEY PATTERN
        
        For fan-in, ALL dependency steps must be complete before this step can run.
        """
        # Get all steps that this step depends on
        dependency_step_ids = set()
        for transition in job.step_transitions:
            if transition.to_step_id == step.step_id:
                dependency_step_ids.add(transition.from_step_id)
        
        # If no dependencies, step is ready (probably a starting step)
        if not dependency_step_ids:
            return True
            
        # CRITICAL FOR FAN-IN: Check that ALL dependency steps are complete
        completed_dependencies = 0
        total_dependencies = len(dependency_step_ids)
        
        for dep_step_id in dependency_step_ids:
            dep_step = next((s for s in job.steps if s.step_id == dep_step_id), None)
            if dep_step:
                # Check the step's status
                current_status = getattr(dep_step, 'status', JobStepStatus.PENDING)
                
                if current_status == JobStepStatus.COMPLETE:
                    completed_dependencies += 1
                    print(f"✅ Dependency '{dep_step.name}' is complete (current_status={current_status})")
                else:
                    print(f"⏳ Dependency '{dep_step.name}' is not complete (current_status={current_status})")
                    return False
            else:
                print(f"❌ Dependency step {dep_step_id} not found")
                return False
                
        # All dependencies complete - step is ready for fan-in aggregation
        print(f"🔄 Fan-in ready: Step '{step.name}' has all {total_dependencies} dependencies complete")
        return completed_dependencies == total_dependencies
    
    def _resolve_step_inputs(self, job: Job, step):
        """
        Resolve step inputs by mapping outputs from dependency steps.
        
        Handles multiple input patterns:
        1. Simple 1:1 mapping (Step A output → Step B input)
        2. Fan-in N:1 mapping (Multiple step outputs → Single step input)
        
        FUTURE EXTENSION NOTES:
        - Current implementation assumes simple key-value output mapping
        - For fan-out scenarios, we'll need to handle:
          1. Directory outputs containing multiple files
          2. Dynamic input enumeration (e.g., slice_001.wav, slice_002.wav, ...)
          3. Flexible mapping patterns (not just direct key mapping)
        - For fan-in aggregation, consider adding:
          1. Input aggregation strategies (list, concatenate, merge)
          2. Order-dependent vs order-independent aggregation
        """
        aggregated_inputs = {}
        
        for transition in job.step_transitions:
            if transition.to_step_id == step.step_id:
                # Get outputs from each dependency step
                previous_outputs = self.job_model.get_step_outputs(
                    job.job_id, transition.from_step_id
                )
                
                # TODO: Future extension for dynamic output discovery
                # if self._is_dynamic_output(previous_outputs):
                #     previous_outputs = self._enumerate_dynamic_outputs(previous_outputs)
                
                # Map those outputs to this step's inputs
                mapped_inputs = transition.apply_mapping(previous_outputs)
                
                # For fan-in: Aggregate inputs from multiple sources
                # Current behavior: later mappings override earlier ones (simple case)
                # Future: Support aggregation strategies (list, concat, etc.)
                aggregated_inputs.update(mapped_inputs)
        
        # Apply all aggregated inputs to the step
        step.inputs.update(aggregated_inputs)
    
    def _is_job_complete(self, job: Job):
        """Check if all steps in the job are complete."""
        for step in job.steps:
            # Check the step's status
            current_status = getattr(step, 'status', JobStepStatus.PENDING)
            
            if current_status != JobStepStatus.COMPLETE:
                return False
        return True

    # =============================================================================
    # FUTURE EXTENSION POINTS FOR DYNAMIC PARALLELISM & FAN-IN/FAN-OUT
    # =============================================================================
    # 
    # The following methods are placeholders for implementing advanced workflow patterns:
    # 
    # FAN-OUT PATTERNS (1 → N):
    # - Audio slicer produces N slices → N parallel analysis steps
    # - Batch processing where one step produces multiple outputs
    # 
    # FAN-IN PATTERNS (N → 1): 
    # - N parallel MFCC analyses → 1 concatenation/aggregation step
    # - Map-reduce where N parallel operations → 1 reduce step
    # - Multi-channel processing → single mixed output
    #
    # def _generate_dynamic_steps(self, job: Job):
    #     """Generate step instances dynamically based on fan-out outputs.
    #     
    #     Use cases:
    #     1. Audio slicer produces N slices → N parallel analysis steps
    #     2. Batch processing where one step produces multiple outputs
    #     3. Map-reduce style workflows
    #     
    #     Returns:
    #         List of dynamically generated step instances
    #     """
    #     pass
    #
    # def _is_dynamic_output(self, outputs):
    #     """Check if outputs represent a dynamic collection (directory, pattern, etc.)"""
    #     pass
    #
    # def _enumerate_dynamic_outputs(self, outputs):
    #     """Enumerate individual files from dynamic outputs (e.g., directory listing)"""
    #     pass
    #
    # def _create_step_instance(self, template_step, instance_id, inputs, outputs):
    #     """Create a new step instance with specific inputs/outputs"""
    #     pass
    #
    # def _aggregate_fan_in_inputs(self, inputs, aggregation_strategy):
    #     """Aggregate multiple inputs for fan-in scenarios.
    #     
    #     Strategies:
    #     - 'list': Combine inputs into array [input1, input2, input3]
    #     - 'concat': Concatenate files or data
    #     - 'merge': Merge structured data
    #     - 'first': Use first available input
    #     - 'custom': User-defined aggregation function
    #     """
    #     pass
    # 
    # =============================================================================

    def _get_next_steps(self, job: Job, completed_step_id: str):
        """Return all next steps in the workflow based on transitions."""
        next_steps = []
        
        for transition in job.step_transitions:
            if transition.from_step_id == completed_step_id:
                target_step_id = transition.to_step_id
                for step in job.steps:
                    if step.step_id == target_step_id:
                        # Map outputs from previous step to next step inputs
                        previous_outputs = self.job_model.get_step_outputs(
                            job.job_id, completed_step_id
                        )
                        mapped_inputs = transition.apply_mapping(previous_outputs)
                        step.inputs.update(mapped_inputs)
                        next_steps.append(step)
                        break
        
        return next_steps
