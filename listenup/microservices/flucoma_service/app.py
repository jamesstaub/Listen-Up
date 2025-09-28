import traceback
from microservices_shared.modules.queue.command_executor_queue_service import CommandExecutorQueueService

    
SERVICE_NAME = "flucoma_service"
QUEUE_NAME = f"{SERVICE_NAME}_queue"


def main():
    """Main entry point for FluCoMa microservice."""
    print(f"🎵 Starting {SERVICE_NAME}...")
    
    try:
        # Initialize command executor queue service (no manifest needed!)
        queue_service = CommandExecutorQueueService(
            queue_name=QUEUE_NAME,
            service_name=SERVICE_NAME
        )
        
        print(f"🚀 {SERVICE_NAME} ready to process messages from {QUEUE_NAME}")
        
        # Start processing messages
        queue_service.process_messages()
        
    except KeyboardInterrupt:
        print(f"\n👋 Shutting down {SERVICE_NAME} gracefully...")
    except Exception as e:
        print(f"❌ Fatal error in {SERVICE_NAME}: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
