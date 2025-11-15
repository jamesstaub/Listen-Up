from multiprocessing import get_logger
import os
from backend.modules import job
from shared.modules.job.models.job import Job
from shared.modules.job.models.job_step import JobStep
from shared.modules.job.services.path_template_resolver import PathTemplateResolver
from shared.modules.storage.storage_manager import StorageManager


class JobStepStorageService():
    
    def __init__(self, path_template_resolver: PathTemplateResolver, storage_manager: StorageManager):
        self.path_template_resolver = path_template_resolver
        self.storage_manager = storage_manager

    def _prepare_job_directory_structure(self, job: Job) -> None:
        """
        Pre-create all directory structures needed for this job's workflow.
        All outputs now go to job-step directories regardless of storage policy.
        Storage policy determines cleanup behavior, not directory structure.
        """
        if not job.user_id:
            get_logger().warning(f"Cannot prepare job directories: missing user_id for job {job.job_id}")
            return
            
        # Create job-step directory for each step
        for step in job.steps:
            job_step_dir_path = self.create_job_step_storage_path(job.user_id, job.job_id, step)
            self.storage_manager.exists(job_step_dir_path)
            # Pre-create directories for all output paths of this step
            for output_key, output_path in step.outputs.items():
                # Resolve template variables in output paths using PathTemplateResolver
                resolved_path = self.path_template_resolver.resolve(output_path, job=job, step=step)
                
                if not resolved_path.startswith("/"):
                    resolved_path = os.path.join(self.storage_manager.storage_root(), resolved_path)
                
                # Ensure this is within the storage root
                if not resolved_path.startswith(self.storage_manager.storage_root()):
                    continue  # Skip non-storage paths
                
                # Extract directory path from file path
                output_dir = os.path.dirname(resolved_path)
                
                self.storage_manager.exists(output_dir)


    def create_job_step_storage_path(self, user_id: str, job_id, step: JobStep) -> str:
        """
        Get the storage path for a given job step.
        """
        composite_name = step.get_composite_name()
        job_step_dir_path = f"{StorageManager.storage_root}/users/{user_id}/jobs/{job_id}/{composite_name}"
        
        return job_step_dir_path