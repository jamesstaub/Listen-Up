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
from shared.modules.log.simple_logger import get_logger

# Storage root configuration
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/app/storage")

# Get storage root from environment, default to Docker volume path
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/app/storage")

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
            self.logger.info("🔍 About to create JobStepEvent")
            step_event = JobStepEvent(**message_data)
            self.logger.info(f"✅ JobStepEvent created successfully")
            self.logger.info(f"🔄 Processing step: {step_event.step_id} | Service: {step_event.microservice}")
            self.logger.info(f"🔨 Command spec: {step_event.command_spec}")
            self.logger.info(f"🔍 Step event attributes: {list(step_event.__dict__.keys())}")
            
            # Send "processing" status
            self._send_status_update(step_event, JobStepState.PROCESSING, "Processing step with file mapping")

            # Create temporary directories
            temp_dir = tempfile.mkdtemp(prefix=f"{self.service_name}_{step_event.step_id}_")
            input_dir = os.path.join(temp_dir, "inputs")
            output_dir = os.path.join(temp_dir, "outputs")
            os.makedirs(input_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
            
            # Download input files and map to local paths
            self.logger.info(f"🔍 About to download inputs: {step_event.inputs}")
            local_input_mapping = self._download_and_map_inputs(
                step_event.inputs, 
                input_dir
            )
            self.logger.info(f"🗂️ Input mapping created: {local_input_mapping}")
            
            # Create output file paths mapping
            self.logger.info(f"🔍 About to create output mapping: {step_event.outputs}")
            local_output_mapping = self._create_output_mapping(
                step_event.outputs,
                output_dir
            )
            self.logger.info(f"🗂️ Output mapping created: {local_output_mapping}")
            
            # Build command from resolved command_spec and substitute local file paths
            self.logger.info(f"🔍 Building command from resolved spec: {step_event.command_spec}")
            command_from_spec = self._build_command_from_spec(step_event.command_spec)
            self.logger.info(f"🔧 Built command: {command_from_spec}")
            final_command = self._substitute_file_paths(
                command_from_spec,
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
            import traceback
            error_msg = f"Failed to execute command: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            
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
        Map input files to local paths, using shared storage directly when possible.
        
        Args:
            input_mapping: Dict mapping placeholders to relative storage paths
            input_dir: Directory to download remote files to (unused for local storage)
            
        Returns:
            Dict mapping placeholders to absolute file paths
        """
        local_mapping = {}
        
        for placeholder, relative_path in input_mapping.items():
            # Convert relative path to absolute path within shared storage
            if relative_path.startswith(STORAGE_ROOT):
                # Already absolute path - use directly
                absolute_path = relative_path
            else:
                # Relative path - prepend storage root
                absolute_path = os.path.join(STORAGE_ROOT, relative_path)
            
            # Use the file directly from shared storage - no copying needed!
            if os.path.exists(absolute_path):
                local_mapping[placeholder] = absolute_path
                self.logger.info(f"📂 Using shared storage file directly: {placeholder} -> {absolute_path}")
            else:
                # File doesn't exist - this is an error in the pipeline
                self.logger.error(f"❌ Input file not found in shared storage: {absolute_path}")
                raise FileNotFoundError(f"Input file not found: {absolute_path}")
        
        return local_mapping

    def _create_output_mapping(self, output_mapping: Dict[str, str], output_dir: str) -> Dict[str, str]:
        """
        Create placeholder-to-absolute-path mapping for output files in shared storage.
        
        Args:
            output_mapping: Dict mapping placeholders to relative storage paths
            output_dir: Temp directory (unused - we write directly to shared storage)
            
        Returns:
            Dict mapping placeholders to absolute file paths in shared storage
        """
        local_mapping = {}
        
        for placeholder, relative_path in output_mapping.items():
            # Convert relative path to absolute path within shared storage
            if relative_path.startswith(STORAGE_ROOT):
                # Already absolute path - use directly
                absolute_path = relative_path
            else:
                # Relative path - prepend storage root
                absolute_path = os.path.join(STORAGE_ROOT, relative_path)
            
            # Ensure output directory exists
            output_dir_path = os.path.dirname(absolute_path)
            os.makedirs(output_dir_path, exist_ok=True)
            
            local_mapping[placeholder] = absolute_path
            self.logger.info(f"📤 Will create {placeholder}: {absolute_path}")
        
        return local_mapping

    def _build_command_from_spec(self, command_spec: Dict[str, Any]) -> str:
        """Build a command string from a resolved CommandSpec dictionary."""
        program = command_spec.get("program", "")
        flags = command_spec.get("flags", {})
        args = command_spec.get("args", [])
        
        # Start with the program
        command_parts = [program]
        
        # Add flags (format: -flag value1 value2 ...)
        for flag, value in flags.items():
            command_parts.append(flag)
            
            # Handle multi-value arguments (like -fftsettings "1024 512 1024")
            if isinstance(value, str) and ' ' in value:
                # Split space-separated values into individual arguments
                command_parts.extend(value.split())
            else:
                # Single value - convert relative paths to absolute if needed
                str_value = str(value)
                
                # Convert relative storage paths to absolute using STORAGE_ROOT
                if not str_value.startswith("/") and "/" in str_value:
                    # This is a relative path - make it absolute
                    str_value = os.path.join(STORAGE_ROOT, str_value)
                
                command_parts.append(str_value)
        
        # Add positional args
        command_parts.extend([str(arg) for arg in args])
        
        return " ".join(command_parts)

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

    def _upload_output_files(self, output_mapping: Dict[str, str], step_id: str) -> Dict[str, str]:
        """
        Return relative storage paths for output files (already written to shared storage).
        
        Args:
            output_mapping: Dict mapping placeholders to absolute storage paths
            step_id: Step ID (unused - paths already determined)
            
        Returns:
            Dict mapping output names to relative storage paths
        """
        output_paths = {}
        
        for placeholder, absolute_path in output_mapping.items():
            if not os.path.exists(absolute_path):
                self.logger.warning(f"⚠️  Expected output file not found: {absolute_path}")
                continue
            
            # Convert absolute path to relative storage path
            relative_path = absolute_path.replace(STORAGE_ROOT + "/", "")
            
            # Remove curly braces from placeholder to get clean output name
            output_name = placeholder.replace('{', '').replace('}', '')
            output_paths[output_name] = relative_path
            
            self.logger.info(f"📤 Output stored: {placeholder} -> {relative_path}")
        
        return output_paths
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
        
    def _send_status_update(self, step_event: JobStepEvent, status: JobStepState, message: str, outputs: Optional[Dict[str, str]] = None):
        """Send a status update back to the orchestrator."""
        event_type_map = {
            JobStepState.PROCESSING: "JOB_STEP_PROCESSING",
            JobStepState.COMPLETE: "JOB_STEP_COMPLETE", 
            JobStepState.FAILED: "JOB_STEP_FAILED"
        }
        
        # Only include outputs for successful completion or when explicitly provided
        # Don't clear outputs on failure or processing unless explicitly requested
        event_outputs = outputs if outputs is not None else {}
        if (status in [JobStepState.FAILED, JobStepState.PROCESSING]) and outputs is None:
            # For failures and processing, don't send outputs at all to avoid clearing existing outputs
            event_outputs = None
        
        status_event = JobStepStatusEvent(
            event_type=event_type_map.get(status, "JOB_STEP_PROCESSING"),
            job_id=step_event.job_id,
            step_id=step_event.step_id,
            step_name=step_event.step_name,
            status=status,
            outputs=event_outputs,
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
