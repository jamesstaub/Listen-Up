import json
import os
import subprocess
from typing import Any, Dict
from shared.modules.queue.redis_client import RedisQueueClient
from shared.modules.job.models.job_step_event import JobStepEvent
from shared.modules.job.models.job_step_status_event import JobStepStatusEvent
from shared.modules.job.enums.job_step_status_enum import JobStepStatus
from shared.modules.log.simple_logger import get_logger

# DEPRECATED
class MicroserviceQueueService:
    """
    Generic microservice queue service that delegates command construction 
    and file handling to service-specific manifest classes.
    """

    def __init__(self, queue_name: str, service_name: str, manifest, log_context=None):
        self.queue_name = queue_name
        self.service_name = service_name
        self.manifest = manifest
        self.redis_client = RedisQueueClient(queue_name=queue_name)
        self.logger = get_logger(service_name or "microservice", log_context)

    def process_messages(self):
        """Process messages from the Redis queue."""
        self.logger.info(f"🎧 Starting to process messages from queue: {self.queue_name}")
        
        while True:
            try:
                # Blocking pop from Redis queue
                message_data = self.redis_client.listen_for_event(timeout=10)
                
                if message_data:
                    self.logger.info(f"📨 Received message: {message_data}")
                    try:
                        self._process_step_message(message_data)
                    except Exception as e:
                        self.logger.error(f"❌ Failed to process message: {e}")
                        
            except Exception as e:
                self.logger.error(f"❌ Error in message processing loop: {e}")

    def _process_step_message(self, message_data: Dict[str, Any]):
        """Process a single step message using the manifest."""
        step_event = None
        try:
            # Debug: Check the type and content of message_data
            self.logger.info(f"🔍 Message data type: {type(message_data)}")
            self.logger.info(f"🔍 Message data content: {message_data}")
            
            # If message_data is a string, parse it as JSON
            if isinstance(message_data, str):
                self.logger.info("📝 Parsing message_data as JSON string")
                message_data = json.loads(message_data)
            
            # Parse the JobStepEvent
            step_event = JobStepEvent(**message_data)
            self.logger.info(f"🔄 Processing step: {step_event.step_id} | Operation: {step_event.operation}")
            
            # Send "processing" status
            self._send_status_update(step_event, JobStepStatus.PROCESSING, "Step started")

            # Validate operation with manifest
            if not self.manifest.validate_operation(step_event.operation):
                raise ValueError(f"Operation '{step_event.operation}' not supported by {self.service_name}")
            
            # Create temporary directory
            temp_dir = self.manifest.create_temp_directory(step_event.step_id)
            
            try:
                # Download input files
                local_inputs = self.manifest.download_inputs(step_event.inputs, temp_dir)
                self.logger.info(f"📥 Downloaded {len(local_inputs)} input files")
                
                # Construct command using manifest
                command, expected_outputs = self.manifest.construct_command(
                    step_event.operation,
                    local_inputs,
                    step_event.parameters or {},
                    temp_dir
                )
                
                # Execute command
                self.logger.info(f"🚀 Executing: {command}")
                result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=temp_dir)
                
                if result.returncode != 0:
                    raise RuntimeError(f"Command failed with return code {result.returncode}: {result.stderr}")
                
                self.logger.info(f"✅ Command completed successfully")
                if result.stdout:
                    self.logger.debug(f"Command output: {result.stdout}")
                
                # Verify expected outputs exist
                existing_outputs = []
                for output_path in expected_outputs:
                    if os.path.exists(output_path):
                        existing_outputs.append(output_path)
                    else:
                        self.logger.warning(f"Expected output file not found: {output_path}")
                
                if not existing_outputs:
                    raise RuntimeError("No output files were generated")
                
                # Upload output files
                # Upload outputs to storage
                output_uris = self.manifest.upload_outputs(existing_outputs, step_event.job_id, step_event.step_name)
                self.logger.info(f"📤 Uploaded {len(output_uris)} output files")
                
                # Send "completed" status with outputs
                self._send_status_update(step_event, JobStepStatus.COMPLETE, "Step completed successfully", output_uris)

            finally:
                # Always cleanup temporary files
                self.manifest.cleanup_temp_files(temp_dir)
                
        except Exception as e:
            self.logger.error(f"❌ Error processing step message: {e}")
            if step_event:
                self._send_status_update(step_event, JobStepStatus.FAILED, str(e))
            else:
                self.logger.error(f"❌ Failed to parse step event from message")

    def _send_status_update(self, step_event: JobStepEvent, status: JobStepStatus, message: str, outputs=None):
        """Send status update back to orchestrator."""
        try:
            # Determine event_type based on status
            if status == JobStepStatus.COMPLETE:
                event_type = "JOB_STEP_COMPLETE"
            elif status == JobStepStatus.FAILED:
                event_type = "JOB_STEP_FAILED"
            else:
                event_type = "JOB_STEP_UPDATE"
            
            status_event = JobStepStatusEvent(
                event_type=event_type,
                job_id=step_event.job_id,
                step_id=step_event.step_id,
                step_name=step_event.step_name,
                status=status,
                outputs=outputs or {},
                error_message=message if status == JobStepStatus.FAILED else None
            )
            
            # Send to orchestrator queue
            orchestrator_queue = RedisQueueClient(queue_name="orchestrator_updates")
            message_data = status_event.model_dump_json()  # Use JSON serialization mode
            orchestrator_queue.push_event(message_data)
            
            self.logger.info(f"📤 Sent status update: {status} for step {step_event.step_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send status update: {e}")

    # Legacy compatibility methods
    def handle_event(self, event_data: Dict[str, Any]):
        """Legacy compatibility method."""
        self._process_step_message(event_data)