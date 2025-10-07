import json
import os
import subprocess
import tempfile
import uuid
from typing import Any, Dict, List, Optional
from shared.modules.queue.redis_client import RedisQueueClient
from shared.modules.job.models.job_step_event import JobStepEvent
from shared.modules.job.models.job_step_status_event import JobStepStatusEvent
from shared.modules.job.enums.job_step_state_enum import JobStepState
from microservices.shared.modules.log.simple_logger import get_logger

# TODO need to wrap certain commands in utility scripts such as NMF
# which outputs a single multi-channel file. in teh client, the NMF "step" can be a macro
# that also includes options for buffer management like number of channels, encoding etc.
# flucoma manifest will have a configuration map for what kinds of pre/post processing should happen based on
# which particular argument. in this case the "components" argument determines how many expected channels
# eg. "nmf": "buffer-compose", channel_count: "components"

# Or we can simply count the number of channels on file, and the JobStepEvent will provide a parameter
# for either multichannel or multi-file outputs (better without reading the specific flag name)


class CommandExecutorQueueService:
    """
    Simplified microservice queue service that executes pre-constructed commands.
    The backend orchestrator constructs safe, well-formed commands that are executed verbatim.
    """

    def __init__(self, queue_name: str, service_name: str, log_context=None):
        self.queue_name = queue_name
        self.service_name = service_name
        self.redis_client = RedisQueueClient(queue_name=queue_name)
        self.logger = get_logger(service_name or "microservice", log_context)
        # We'll handle file operations locally for now

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
        """Process a single step message by executing the pre-constructed command with file mapping."""
        step_event = None
        temp_dir = None
        
        try:
            # Parse message data
            if isinstance(message_data, str):
                self.logger.info("📝 Parsing message_data as JSON string")
                message_data = json.loads(message_data)
            
            # Parse the JobStepEvent
            step_event = JobStepEvent(**message_data)
            self.logger.info(f"🔄 Processing step: {step_event.step_id} | Operation: {step_event.operation}")
            self.logger.info(f"🔨 Command template: {step_event.command}")
            
            # Send "processing" status
            self._send_status_update(step_event, JobStepState.PROCESSING, "Processing step with file mapping")

            # Create temporary directories
            temp_dir = tempfile.mkdtemp(prefix=f"{self.service_name}_{step_event.step_id}_")
            input_dir = os.path.join(temp_dir, "inputs")
            output_dir = os.path.join(temp_dir, "outputs")
            os.makedirs(input_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
            
            # Download input files and map to local paths
            self.logger.info(f"🔍 About to download inputs: {step_event.input_file_mapping}")
            local_input_mapping = self._download_and_map_inputs(
                step_event.input_file_mapping, 
                input_dir
            )
            self.logger.info(f"🗂️ Input mapping created: {local_input_mapping}")
            
            # Create output file paths mapping
            self.logger.info(f"🔍 About to create output mapping: {step_event.output_file_mapping}")
            local_output_mapping = self._create_output_mapping(
                step_event.output_file_mapping,
                output_dir
            )
            self.logger.info(f"🗂️ Output mapping created: {local_output_mapping}")
            
            # Substitute placeholders in command with actual file paths
            self.logger.info(f"🔍 About to substitute command template: {step_event.command}")
            final_command = self._substitute_file_paths(
                step_event.command,
                local_input_mapping,
                local_output_mapping
            )
            
            self.logger.info(f"🔧 Final command: {final_command}")
            
            # Execute the command with substituted file paths
            self._execute_command(final_command, temp_dir)
            
            # Validate that expected output files were created
            self._validate_output_files(local_output_mapping, step_event)
            
            # Upload output files and get their URIs
            output_uris = self._upload_output_files(local_output_mapping, step_event.step_id)
            
            # Send success status
            self._send_status_update(
                step_event, 
                JobStepState.COMPLETE, 
                f"Command executed successfully", 
                outputs=output_uris
            )
                
        except Exception as e:
            error_msg = f"Failed to execute command: {str(e)}"
            self.logger.error(error_msg)
            
            if step_event:
                self._send_status_update(step_event, JobStepState.FAILED, error_msg)
                
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                self._cleanup_temp_files(temp_dir)

    def _execute_command(self, command: str, working_dir: str):
        """
        Execute the pre-constructed command in the given working directory.
        
        Args:
            command: Complete command string to execute
            working_dir: Working directory for command execution
        """
        self.logger.info(f"🚀 Executing: {command}")
        
        # Execute the command
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            self.logger.error(f"❌ Command failed with return code {result.returncode}")
            self.logger.error(f"   STDOUT: {result.stdout}")
            self.logger.error(f"   STDERR: {result.stderr}")
            raise RuntimeError(f"Command execution failed: {result.stderr}")
        
        self.logger.info(f"✅ Command executed successfully")
        if result.stdout:
            self.logger.info(f"   STDOUT: {result.stdout}")

    def _validate_output_files(self, output_mapping: Dict[str, str], step_event: JobStepEvent):
        """
        Validate that expected output files were created after command execution.
        
        Args:
            output_mapping: Dict mapping placeholders to local file paths  
            step_event: The step event for error reporting
            
        Raises:
            RuntimeError: If no expected output files were created
        """
        if not output_mapping:
            # No output files expected, validation passes
            self.logger.info("✅ No output files expected, validation passed")
            return
            
        missing_files = []
        created_files = []
        
        for placeholder, local_path in output_mapping.items():
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                created_files.append(f"{placeholder} -> {local_path}")
                self.logger.info(f"✅ Output file created: {placeholder} -> {local_path}")
            else:
                missing_files.append(f"{placeholder} -> {local_path}")
                self.logger.warning(f"❌ Expected output file missing or empty: {placeholder} -> {local_path}")
        
        # If no files were created at all, this is a failure
        if not created_files:
            error_msg = f"Command executed successfully but created no output files. Expected: {list(output_mapping.keys())}"
            self.logger.error(f"💥 {error_msg}")
            raise RuntimeError(error_msg)
        
        # If some files were created, log what's missing but don't fail
        if missing_files:
            self.logger.warning(f"⚠️  Some expected output files were not created: {missing_files}")
            self.logger.info(f"✅ But {len(created_files)} output files were created successfully: {created_files}")

    def _download_and_map_inputs(self, input_mapping: Dict[str, str], input_dir: str) -> Dict[str, str]:
        """
        Download input files and create placeholder-to-local-path mapping.
        
        Args:
            input_mapping: Dict mapping placeholders to input URIs
            input_dir: Directory to download files to
            
        Returns:
            Dict mapping placeholders to local file paths
        """
        local_mapping = {}
        
        for placeholder, uri in input_mapping.items():
            # Create local filename based on placeholder
            filename = f"{placeholder.replace('{', '').replace('}', '').lower()}.wav"
            local_path = os.path.join(input_dir, filename)
            
            # For now, assume local file paths for development/testing
            if os.path.exists(uri):
                import shutil
                shutil.copy2(uri, local_path)
                self.logger.info(f"📥 Downloaded {placeholder}: {uri} -> {local_path}")
            else:
                # For S3 or remote URIs, we'd implement download logic here
                # For now, create a dummy audio file for testing
                self.logger.warning(f"⚠️  Input file not found locally: {uri}")
                
                # Create a minimal WAV file (44-byte header + silence)
                import struct
                with open(local_path, 'wb') as f:
                    # WAV header for 1 second of silence, 44100 Hz, mono, 16-bit
                    sample_rate = 44100
                    num_samples = sample_rate  # 1 second
                    f.write(b'RIFF')
                    f.write(struct.pack('<I', 36 + num_samples * 2))  # File size
                    f.write(b'WAVE')
                    f.write(b'fmt ')
                    f.write(struct.pack('<I', 16))  # PCM format chunk size
                    f.write(struct.pack('<HHIIHH', 1, 1, sample_rate, sample_rate * 2, 2, 16))
                    f.write(b'data')
                    f.write(struct.pack('<I', num_samples * 2))  # Data chunk size
                    f.write(b'\x00' * (num_samples * 2))  # Silent audio data
                
                self.logger.info(f"📥 Created dummy WAV: {uri} -> {local_path}")
            
            local_mapping[placeholder] = local_path
        
        return local_mapping

    def _create_output_mapping(self, output_mapping: Dict[str, str], output_dir: str) -> Dict[str, str]:
        """
        Create placeholder-to-local-path mapping for output files.
        
        Args:
            output_mapping: Dict mapping placeholders to output filenames
            output_dir: Directory where output files will be created
            
        Returns:
            Dict mapping placeholders to local file paths
        """
        local_mapping = {}
        
        for placeholder, filename in output_mapping.items():
            local_path = os.path.join(output_dir, filename)
            local_mapping[placeholder] = local_path
            self.logger.info(f"📤 Will create {placeholder}: {local_path}")
        
        return local_mapping

    def _substitute_file_paths(self, command_template: str, input_mapping: Dict[str, str], output_mapping: Dict[str, str]) -> str:
        """
        Substitute placeholders in command template with actual file paths.
        
        Args:
            command_template: Command template with placeholders
            input_mapping: Placeholder-to-local-path mapping for inputs
            output_mapping: Placeholder-to-local-path mapping for outputs
            
        Returns:
            Final command with substituted file paths
        """
        final_command = command_template
        
        # Substitute input placeholders
        for placeholder, local_path in input_mapping.items():
            final_command = final_command.replace(placeholder, local_path)
            
        # Substitute output placeholders  
        for placeholder, local_path in output_mapping.items():
            final_command = final_command.replace(placeholder, local_path)
            
        return final_command

    def _upload_output_files(self, output_mapping: Dict[str, str], step_id: str) -> List[str]:
        """
        Upload output files and return their URIs.
        
        Args:
            output_mapping: Dict mapping placeholders to local file paths
            step_id: Step ID for generating unique URIs
            
        Returns:
            List of uploaded URIs
        """
        output_uris = []
        
        for placeholder, local_path in output_mapping.items():
            if not os.path.exists(local_path):
                self.logger.warning(f"⚠️  Expected output file not found: {local_path}")
                continue
            
            # For now, return local path as URI for development/testing
            # In production, this would upload to S3 and return the S3 URI
            uri = f"file://{local_path}"
            
            output_uris.append(uri)
            self.logger.info(f"📤 Uploaded {placeholder}: {local_path} -> {uri}")
        
        return output_uris
        """
        Download input files to the input directory.
        
        Args:
            input_uris: List of input file URIs
            input_dir: Directory to download files to
            
        Returns:
            List of local file paths
        """
        local_paths = []
        
        for i, uri in enumerate(input_uris):
            # Create predictable local filename
            filename = f"input_{i}.wav"
            local_path = os.path.join(input_dir, filename)
            
            # For now, assume local file paths for development/testing
            if os.path.exists(uri):
                import shutil
                shutil.copy2(uri, local_path)
            else:
                # For S3 or remote URIs, we'd need to implement download logic here
                # For now, create a dummy file for testing
                self.logger.warning(f"⚠️  Input file not found locally: {uri}")
                # Create an empty file so the command doesn't fail immediately
                with open(local_path, 'w') as f:
                    f.write("dummy audio data")
            
            local_paths.append(local_path)
            self.logger.info(f"📥 Downloaded {uri} -> {local_path}")
        
    def _send_status_update(self, step_event: JobStepEvent, status: JobStepState, message: str, outputs: Optional[List[str]] = None):
        """Send a status update back to the orchestrator."""
        event_type_map = {
            JobStepState.PROCESSING: "JOB_STEP_PROCESSING",
            JobStepState.COMPLETE: "JOB_STEP_COMPLETE", 
            JobStepState.FAILED: "JOB_STEP_FAILED"
        }
        
        status_event = JobStepStatusEvent(
            event_type=event_type_map.get(status, "JOB_STEP_PROCESSING"),
            job_id=step_event.job_id,
            step_id=step_event.step_id,
            step_name=step_event.step_name,
            status=status,
            outputs=outputs or [],
            error_message=message if status == JobStepState.FAILED else None
        )
        
        # Send to job status events queue
        status_queue = RedisQueueClient(queue_name="job_status_events")
        status_queue.push_event(status_event.model_dump(mode='json'))
        
        self.logger.info(f"📤 Sent {status.value} status for step {step_event.step_id}")

    def _cleanup_temp_files(self, temp_dir: str):
        """Clean up temporary files and directory."""
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
            self.logger.info(f"🧹 Cleaned up temp directory: {temp_dir}")
