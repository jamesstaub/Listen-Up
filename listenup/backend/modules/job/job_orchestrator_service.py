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
from datetime import datetime


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

        # Build StepTransitions
        transitions_data = job_payload.get("step_transitions", [])
        step_transitions = []
        step_name_to_id = {s.name: s.step_id for s in job_steps}
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
            steps=job_steps,
            step_transitions=step_transitions,
            status=JobStatus.PENDING,
            created_at=created_at
        )
        self.job_model.create_job(job)

        # Dispatch first steps that have no dependencies
        for step in job_steps:
            if not any(t.to_step_id == step.step_id for t in step_transitions):
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
    
        self.job_model.update_job_step_status(job.job_id, step.step_id, JobStepState.PROCESSING)

        # Gather previous outputs via StepTransition
        previous_outputs = {}
        for transition in job.step_transitions:
            if transition.to_step_id == step.step_id:
                previous_outputs.update(self.job_model.get_step_outputs(job.job_id, transition.from_step_id))

        # Build the event and resolve it
        step_event = JobStepEvent(
            job_id=job.job_id,
            step_id=step.step_id,
            step_name=step.name,
            microservice=step.microservice,
            command_spec=step.command_spec.dict() if step.command_spec else {},
            inputs=step.inputs,
            outputs=step.outputs
        )

        resolved_payload = step_event.resolve_and_prepare(previous_outputs)

        # Push to queue
        queue = self._get_service_queue(step.microservice)
        queue.push_event(resolved_payload)
        print(f"📤 Dispatched step {step.name} -> {step.microservice}")

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
