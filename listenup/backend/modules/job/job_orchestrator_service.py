from shared.modules.job.models.step_transition import StepTransition
from shared.modules.job.models.command_spec import CommandSpec
from shared.modules.job.models.job import Job, JobStatus, JobStep
from shared.modules.job.enums.job_step_state_enum import JobStepState
from shared.modules.job.models.job_step_event import JobStepEvent
from shared.modules.job.command_resolver import CommandResolver
from shared.modules.queue.redis_client import RedisQueueClient
from backend.modules.job.models.job_model import JobModel
from typing import Dict, Any
import uuid
import os
from datetime import datetime

# Environment-configurable storage root
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/app/storage")


class JobOrchestratorService:
    """
    Orchestrates multi-step jobs via async event-driven queue.
    Dispatches steps to microservices and listens for completion events.
    """

    def __init__(self, mongo_db):
        self.job_model = JobModel(mongo_db)
        self.queue_clients = {}  # cache service queues
        self.resolver = CommandResolver()

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
        step_name_to_composite = {s.name: s.get_composite_name() for s in job_steps}
        
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
        self._prepare_job_directory_structure(job)

        # Dispatch first steps that have no dependencies
        for step in job.steps:
            if not any(t.to_step_id == step.step_id for t in job.step_transitions):
                self._dispatch_step(job, step)

        return job.dict()

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
            if step.state != JobStepState.COMPLETE:
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
    def _prepare_job_directory_structure(self, job: Job) -> None:
        """
        Pre-create all directory structures needed for this job's workflow.
        All outputs now go to job-step directories regardless of storage policy.
        Storage policy determines cleanup behavior, not directory structure.
        """
        if not job.user_id:
            print("⚠️ No user_id provided, skipping directory structure creation")
            return
            
        # Create job-step directory for each step
        for step in job.steps:
            # Create job-step directory using composite name
            composite_name = step.get_composite_name()
            job_step_dir = f"{STORAGE_ROOT}/users/{job.user_id}/jobs/{job.job_id}/{composite_name}"
            self._ensure_directory_exists(job_step_dir, f"job step: {step.name}")
            
            # Pre-create directories for all output paths of this step
            for output_key, output_path in step.outputs.items():
                # Resolve template variables in output paths
                resolved_path = output_path.replace("{{job_id}}", job.job_id)
                if job.user_id:
                    resolved_path = resolved_path.replace("{{user_id}}", job.user_id)
                resolved_path = resolved_path.replace("{{step_id}}", step.step_id)
                resolved_path = resolved_path.replace("{{composite_name}}", composite_name)
                
                # Convert relative path to absolute using STORAGE_ROOT
                if not resolved_path.startswith("/"):
                    resolved_path = os.path.join(STORAGE_ROOT, resolved_path)
                
                # Ensure this is within the storage root
                if not resolved_path.startswith(STORAGE_ROOT):
                    continue  # Skip non-storage paths
                
                # Extract directory path from file path
                output_dir = os.path.dirname(resolved_path)
                self._ensure_directory_exists(output_dir, f"output: {output_key}")
        
        print(f"✅ Pre-created job-step directories for job {job.job_id}")
        print(f"📁 All outputs will be written to job-step directories")
        print(f"🧹 Storage policy will determine cleanup behavior, not directory location")
    
    def _ensure_directory_exists(self, directory_path: str, description: str) -> None:
        """Ensure a directory exists using direct filesystem operations."""
        try:
            os.makedirs(directory_path, exist_ok=True)
            print(f"📁 Created directory: {directory_path} ({description})")
        except Exception as e:
            print(f"⚠️ Failed to create directory {directory_path} ({description}): {e}")

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
        
        self.job_model.update_job_step_status(job.job_id, step.step_id, JobStepState.PROCESSING)

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
        status = event.get("status")
        outputs = event.get("outputs", {})

        if not job_id or not step_id or not status:
            print(f"❌ Invalid status event: missing required fields {job_id=} {step_id=} {status=}")
            return

        print(f"⚙️ Handling status event: {job_id=} {step_id=} {status=}")

        job = self.job_model.get_job(job_id)
        if not job:
            print(f"❌ Job {job_id} not found in DB")
            return

        # Update job step status in DB
        self.job_model.update_job_step_status(job_id, step_id, status, outputs=outputs)

        # Handle status types
        if status == JobStepState.COMPLETE:
            next_step = self._get_next_step(job, step_id)
            if next_step:
                print(f"➡️ Dispatching next step: {next_step.name}")
                self._dispatch_step(job, next_step)
            else:
                print(f"✅ Job {job_id} fully completed")
                self.job_model.update_job_status(job_id, JobStatus.COMPLETE)

        elif status == JobStepState.FAILED:
            print(f"💥 Step {step_id} failed; marking job {job_id} as FAILED")
            self.job_model.update_job_status(job_id, JobStatus.FAILED)

        elif status == JobStepState.PROCESSING:
            print(f"🛠 Step {step_id} is processing... (no action needed)")

    # -------------------------------------------------------------------------
    # Step progression logic
    # -------------------------------------------------------------------------
    def _get_next_step(self, job: Job, completed_step_id: str):
        """Return the next step in the workflow based on transitions."""
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
                        return step
        return None
