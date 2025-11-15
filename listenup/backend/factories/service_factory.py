"""
Service Factory for creating business service instances with proper dependencies.
"""
from typing import Optional
from backend.modules.job.services.job_orchestrator_service import JobOrchestratorService
from backend.factories.storage_factory import StorageFactory
from backend.database.context import DatabaseContext
from backend.modules.job.services.job_step_storage_service import JobStepStorageService
from shared.modules.job.services.path_template_resolver import PathTemplateResolver


class ServiceFactory:
    """
    Factory for creating service instances with injected dependencies.
    Automatically handles Flask request context and application context.
    """

    @staticmethod
    def create_job_step_storage_service(user_id: Optional[str] = None):
        storage_manager = StorageFactory.create_storage_manager(user_id)
        path_template_resolver = PathTemplateResolver()
        return JobStepStorageService(path_template_resolver, storage_manager)

    @staticmethod
    def create_job_orchestrator(user_id: Optional[str] = None) -> JobOrchestratorService:
        """
        Create a JobOrchestratorService with properly configured dependencies.
        
        Works in both:
        - Request context (controllers)  
        - Application context (background threads like BackendQueueService)
        
        Args:
            user_id: Optional user ID for user-specific storage configuration
            
        Returns:
            JobOrchestratorService: Configured orchestrator service
        """
        # Get database from Flask context (works in both request and app context)
        mongo_db = DatabaseContext.get_mongo_db()
        
        # Create storage manager with user context
        storage_manager = StorageFactory.create_storage_manager(user_id)
        
        # Create job step storage service
        job_step_storage_service = ServiceFactory.create_job_step_storage_service(user_id)
        
        return JobOrchestratorService(mongo_db, storage_manager, job_step_storage_service)
    
