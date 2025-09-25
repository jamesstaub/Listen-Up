from microservices_shared.modules.microservice_base import MicroserviceBase

SERVICE_NAME = "flucoma_service"


class FlucomaMicroservice(MicroserviceBase):
    def __init__(self, service_name):
        super().__init__(service_name)

    def get_queue_service_class(self):
        from microservices_shared.modules.queue.microservice_queue_service import MicroserviceQueueService
        return MicroserviceQueueService

    def get_manifest(self):
        from microservices.flucoma_service.manifest import FlucomaManifest

        return FlucomaManifest()


if __name__ == "__main__":
    print("Flucoma microservice starting...")
    service = FlucomaMicroservice(service_name=SERVICE_NAME)
    service.run()
