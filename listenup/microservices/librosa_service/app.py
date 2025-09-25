
import os
from microservices_shared.modules.microservice_base import MicroserviceBase

SERVICE_NAME = "librosa_service"

class LibrosaMicroservice(MicroserviceBase):
    def get_queue_service_class(self):
        from microservices_shared.modules.queue.microservice_queue_service import MicroserviceQueueService
        return MicroserviceQueueService
    
    def get_manifest(self):
        from microservices.librosa_service.manifest import LibrosaManifest
        return LibrosaManifest()


if __name__ == "__main__":
    print("Librosa microservice starting...")
    service = LibrosaMicroservice(
        service_name=SERVICE_NAME
    )
    service.run()

