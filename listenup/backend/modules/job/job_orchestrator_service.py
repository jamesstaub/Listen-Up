"""
The Job Orchestrator Service is responsible for managing and orchestrating jobs across various mic            # Start execution
            if steps:
                self._start_job_execution(saved_job)

            # ✅ Use model_dump_json_json() for proper JSON serialization of datetime objects
            return job.model_dump_json_json()

        except Exception as e:es.
This is the business logic of interpreting the job data and deciding what happens next.

- handles writing the Job record to mongodb
- called by BackendQueueService when new JobEvents are received
- calls BackendQueueService to create JobStep events for microservices to pick up

"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from .models.job_model import JobModel  # Relative import
from shared.modules.job.models.job import Job
from shared.modules.job.models.job_step import JobStep
from shared.modules.job.models.step_transition import StepTransition
from shared.modules.job.events import JobStepEvent, JobStepStatusEvent
from shared.modules.job.enums.job_status_enum import JobStatus
from shared.modules.job.enums.job_step_state_enum import JobStepState

from shared.modules.queue.redis_client import RedisQueueClient

class JobOrchestratorService:
    """
    Main business logic for job orchestration.
    Handles job creation, step execution coordination, and status updates.
    """
    
    def __init__(self, mongo_db):
        self.mongo_db = mongo_db
        self.job_model = JobModel(mongo_db)
        # We'll create service-specific queues dynamically
        self.status_queue = RedisQueueClient(queue_name="job_status_events")
    
    def _get_service_queue(self, service_name: str) -> RedisQueueClient:
        """
        Get a Redis queue client for the specific microservice.
        
        Args:
            service_name: Name of the microservice (e.g., "flucoma_service")
            
        Returns:
            RedisQueueClient configured for the service's queue
        """
        if not service_name:
            raise ValueError("Service name is required to get queue")
        
        queue_name = f"{service_name}_queue"
        return RedisQueueClient(queue_name=queue_name)
    
    def create_job(self, steps_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a new job from step definitions and start execution.

        Args:
            steps_data: List of step definitions from the API request
                        Can include 'step_transitions' for output→input mapping

        Returns:
            Dict containing job creation response (JSON-safe)
        """
        try:
            # Generate job ID
            job_id = str(uuid.uuid4())
            created_at = datetime.utcnow()
            
            # Extract step transitions if provided
            step_transitions_data = steps_data.get('step_transitions', []) if isinstance(steps_data, dict) else []
            actual_steps_data = steps_data.get('steps', steps_data) if isinstance(steps_data, dict) else steps_data

            # Build JobStep objects
            steps = []
            for i, step_data in enumerate(actual_steps_data):
                step = JobStep(
                    name=step_data.get("name"),
                    order=i,
                    service=step_data.get("service"),
                    operation=step_data.get("operation"),
                    parameters=step_data.get("parameters", {}),
                    inputs=step_data.get("inputs", [])
                )
                steps.append(step)
            
            # Build StepTransition objects
            step_transitions = []
            step_name_to_id = {step.name: step.step_id for step in steps}

            for transition_data in step_transitions_data:
                from_step_name = transition_data.get("from_step_name")
                to_step_name = transition_data.get("to_step_name")

                from_step_id = step_name_to_id.get(from_step_name)
                to_step_id = step_name_to_id.get(to_step_name)

                if from_step_id and to_step_id:
                    transition = StepTransition(
                        from_step_id=from_step_id,
                        to_step_id=to_step_id,
                        output_to_input_mapping=transition_data.get("output_to_input_mapping", [])
                    )
                    step_transitions.append(transition)
                    print(f"🗺️ Added transition: {from_step_name} → {to_step_name}")
                else:
                    print(f"⚠️ Warning: Could not resolve step names for transition: {from_step_name} → {to_step_name}")

            # Create Job object
            job = Job(
                job_id=job_id,
                steps=steps,
                step_transitions=step_transitions,
                status=JobStatus.PENDING,
                created_at=created_at
            )

            # Persist to MongoDB
            saved_job = self.job_model.create_job(job)

            # Start execution
            if steps:
                self._start_job_execution(saved_job)

            # ✅ Use Pydantic’s JSON-safe dict
            return job.dict()

        except Exception as e:
            raise Exception(f"Job creation failed: {str(e)}")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve job details by ID.
        
        Args:
            job_id: The job identifier
            
        Returns:
            Job data or None if not found
        """
        return self.job_model.get_job(job_id)
    
    def retry_job(self, job_id: str) -> Dict[str, Any]:
        """
        Retry a failed or incomplete job by starting from the first non-complete step.
        
        Args:
            job_id: The job identifier to retry
            
        Returns:
            Dict containing retry response
        """
        try:
            # Get the current job from database
            job_data = self.job_model.get_job(job_id)
            if not job_data:
                raise ValueError(f"Job not found: {job_id}")
            
            # Check if job can be retried
            if job_data['status'] == JobStatus.COMPLETE.value:
                raise ValueError(f"Job {job_id} is already complete")
            
            if job_data['status'] == JobStatus.PROCESSING.value:
                raise ValueError(f"Job {job_id} is currently processing")
            
            # Find the first incomplete step
            resume_step = self._find_resume_step(job_data)
            if not resume_step:
                raise ValueError(f"No incomplete steps found in job {job_id}")
            
            resume_step_index = resume_step['order']
            print(f"🔄 Retrying job {job_id} from step {resume_step_index + 1}: {resume_step['name']}")
            
            # Show which steps are already complete
            completed_steps = [step['name'] for step in job_data['steps'] 
                             if step.get('status') == JobStepState.COMPLETE.value]
            if completed_steps:
                print(f"   ✅ Skipping {len(completed_steps)} completed steps: {', '.join(completed_steps)}")
            else:
                print(f"   ⚠️  No previously completed steps found")
            
            # Reset job status to processing
            self.job_model.update_job_status(job_id, JobStatus.PROCESSING)
            
            # Reset the resume step to pending (clear any error state)
            self.job_model.update_job_step_status(
                job_id=job_id,
                step_id=resume_step['step_id'],
                status=JobStepState.PENDING,
                clear_error=True  # Clear previous error
            )
            
            # Start execution from the resume step
            self._start_specific_step(job_data, resume_step)
            
            return {
                "status": "retrying",
                "job_id": job_id,
                "resume_step": resume_step['name'],
                "step_index": resume_step['order']
            }
            
        except Exception as e:
            raise Exception(f"Job retry failed: {str(e)}")

    def _find_resume_step(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find the first step that needs to be executed (failed or pending).
        
        Args:
            job_data: Job document from MongoDB
            
        Returns:
            Step dictionary or None if all steps are complete
        """
        for step in job_data['steps']:
            step_status = step.get('status', JobStepState.PENDING.value)
            
            # Skip completed steps
            if step_status == JobStepState.COMPLETE.value:
                continue
                
            # Found a step that needs execution
            return step
        
        return None

    def _start_specific_step(self, job_data: Dict[str, Any], step_data: Dict[str, Any]) -> None:
        """
        Start execution of a specific step with proper input chaining (used for retries).
        Only gets outputs from the immediate previous completed step.
        
        Args:
            job_data: Full job data
            step_data: The specific step to start
        """
        step_index = step_data['order']
        
        # Get outputs from the immediately previous completed step (not all previous steps)
        previous_outputs = self._collect_previous_outputs(job_data, step_index)
        
        # Update step status to processing
        self.job_model.update_job_step_status(
            job_data['job_id'],
            step_data['step_id'],
            JobStepState.PROCESSING
        )
        
        # Create step event with chained inputs
        step_event = JobStepEvent(
            job_id=job_data['job_id'],
            step_id=step_data['step_id'],
            step_name=step_data['name'],
            service=step_data['service'],
            operation=step_data['operation'],
            parameters=step_data.get('parameters', {}),
            inputs=self._merge_inputs(step_data.get('inputs', []), previous_outputs)
        )
        
        # Use model_dump_json() instead of dict() for proper JSON serialization of datetime objects
        # Send to service-specific queue
        service_queue = self._get_service_queue(step_data['service'])
        service_queue.push_event(step_event.model_dump_json())
        print(f"📤 Resumed execution at step: {step_data['name']} -> {step_data['service']}")
        print(f"   Retry step {step_index + 1} with {len(previous_outputs)} inputs from previous step")

    def _collect_previous_outputs(self, job_data: Dict[str, Any], current_step_index: int) -> List[str]:
        """
        Collect output URIs from the immediately previous completed step (for retry scenarios).
        
        Args:
            job_data: Full job data from MongoDB
            current_step_index: Index of the current step being started
            
        Returns:
            List of absolute URIs from the immediately previous completed step
        """
        # Look backwards from current step to find the most recent completed step
        for i in range(current_step_index - 1, -1, -1):
            step = job_data['steps'][i]
            step_status = step.get('status', JobStepState.PENDING.value)
            
            if step_status == JobStepState.COMPLETE.value:
                step_outputs = step.get('outputs', [])
                step_name = step.get('name', f'step_{i}')
                
                print(f"📋 Found previous completed step: {step_name} with {len(step_outputs)} outputs")
                if step_outputs:
                    print(f"   Previous outputs: {step_outputs}")
                
                return step_outputs if isinstance(step_outputs, list) else []
        
        print(f"📋 No previous completed steps found for retry")
        return []
    
    def handle_step_status_event(self, status_event_data: Dict[str, Any]) -> None:
        """
        Process a step status event from a microservice.
        
        Args:
            status_event_data: Status event payload from microservice
        """
        try:
            # Parse the status event
            status_event = JobStepStatusEvent(**status_event_data)
            
            print(f"🔄 Processing step status: {status_event.step_name} -> {status_event.status}")
            
            # Update the step in MongoDB
            self._update_step_status(status_event)
            
            # Determine next action based on step result
            if status_event.status == JobStepState.COMPLETE.value:
                self._handle_step_success(status_event)
            else:
                self._handle_step_failure(status_event)
                
        except Exception as e:
            print(f"❌ Error handling step status event: {str(e)}")
    
    def _start_job_execution(self, job: Job) -> None:
        """
        Start job execution by sending the first step to the queue.
        """
        if not job.steps:
            return
            
        first_step = job.steps[0]

        # Update job status to processing
        self.job_model.update_job_status(job.job_id, JobStatus.PROCESSING)

        # Update first step to processing
        self.job_model.update_job_step_status(
            job.job_id,
            first_step.step_id,
            JobStepState.PROCESSING
        )

        # Create and send step execution event
        step_event = JobStepEvent(
            job_id=job.job_id,
            step_id=first_step.step_id,
            step_name=first_step.name,
            service=first_step.service,
            operation=first_step.operation,
            parameters=first_step.parameters,
            inputs=first_step.inputs
        )

        # Use model_dump_json() instead of dict() for proper JSON serialization of datetime objects
        # Send to service-specific queue
        if not first_step.service:
            raise ValueError("Service name is required for step execution")
        service_queue = self._get_service_queue(first_step.service)
        service_queue.push_event(step_event.model_dump_json())
        print(f"📤 Sent step to queue: {first_step.name} -> {first_step.service}")
    
    def _update_step_status(self, status_event: JobStepStatusEvent) -> None:
        """
        Update step status and outputs in MongoDB.
        """
        # Map status event status to JobStepState
        step_state = JobStepState.COMPLETE if status_event.status == "SUCCESS" else JobStepState.FAILED
        
        # Update step in database
        self.job_model.update_job_step_status(
            job_id=status_event.job_id,
            step_id=status_event.step_id,
            status=step_state,
            outputs=status_event.outputs,
            error_message=status_event.error_message
        )
    
    def _handle_step_success(self, status_event: JobStepStatusEvent) -> None:
        """
        Handle successful step completion - trigger next step or complete job.
        """
        job = self.job_model.get_job(status_event.job_id)
        if not job:
            print(f"❌ Job not found: {status_event.job_id}")
            return
        
        # Find current step index
        current_step_index = None
        for i, step in enumerate(job['steps']):
            if step['step_id'] == status_event.step_id:
                current_step_index = i
                break
        
        if current_step_index is None:
            print(f"❌ Step not found in job: {status_event.step_id}")
            return
        
        # Check if there's a next step
        next_step_index = current_step_index + 1
        if next_step_index < len(job['steps']):
            # Start next step with mapping
            self._start_next_step(job, next_step_index, status_event.step_id, status_event.outputs)
        else:
            # Job is complete
            self._complete_job(status_event.job_id)
    
    def _handle_step_failure(self, status_event: JobStepStatusEvent) -> None:
        """
        Handle step failure - mark job as failed.
        """
        self.job_model.update_job_status(status_event.job_id, JobStatus.FAILED)
        print(f"💥 Job failed: {status_event.job_id} - {status_event.error_message}")
    
    def _start_next_step(self, job_dict: Dict[str, Any], step_index: int, previous_step_id: str, previous_outputs: List[str]) -> None:
        """
        Start the next step in the job pipeline with proper input chaining and mapping.
        Uses the Job model's transition mapping logic.
        
        Args:
            job_dict: Full job data from MongoDB
            step_index: Index of the next step to start
            previous_step_id: ID of the step that just completed
            previous_outputs: Output URIs from the just-completed step
        """
        next_step_data = job_dict['steps'][step_index]
        
        # Create a Job object from the dict to use mapping logic
        job = Job(**job_dict)
        
        # Get mapped inputs using the Job model's logic
        mapped_previous_outputs = job.get_mapped_inputs_for_next_step(previous_step_id, previous_outputs)
        
        # Update step status to processing
        self.job_model.update_job_step_status(
            job_dict['job_id'],
            next_step_data['step_id'],
            JobStepState.PROCESSING
        )
        
        # Create step event with original inputs + mapped previous outputs
        step_event = JobStepEvent(
            job_id=job_dict['job_id'],
            step_id=next_step_data['step_id'],
            step_name=next_step_data['name'],
            service=next_step_data['service'],
            operation=next_step_data['operation'],
            parameters=next_step_data.get('parameters', {}),
            inputs=self._merge_inputs(next_step_data.get('inputs', []), mapped_previous_outputs)
        )
        
        # Use model_dump_json() instead of dict() for proper JSON serialization of datetime objects
        # Send to service-specific queue
        service_queue = self._get_service_queue(next_step_data['service'])
        service_queue.push_event(step_event.model_dump_json())
        print(f"📤 Started next step: {next_step_data['name']} -> {next_step_data['service']}")
        print(f"   Step {step_index + 1} of {len(job_dict['steps'])}")
        print(f"   Inputs: {len(next_step_data.get('inputs', []))} original + {len(mapped_previous_outputs)} mapped from previous step")
    
    def _complete_job(self, job_id: str) -> None:
        """
        Mark job as complete.
        """
        self.job_model.update_job_status(job_id, JobStatus.COMPLETE)
        print(f"🎉 Job completed: {job_id}")
    
    def _merge_inputs(self, original_inputs: List[str], previous_outputs: List[str]) -> List[str]:
        """
        Merge original step inputs with outputs from the immediate previous step.
        This creates a simple pipeline: previous step outputs become current step inputs.
        
        Args:
            original_inputs: List of absolute URIs defined for this step
            previous_outputs: List of absolute URIs from the previous completed step
            
        Returns:
            Combined list: original inputs + previous step outputs
        """
        merged_inputs = original_inputs.copy()
        merged_inputs.extend(previous_outputs)
        
        print(f"🔗 Input chaining: {len(original_inputs)} original + {len(previous_outputs)} from previous = {len(merged_inputs)} total")
        return merged_inputs

