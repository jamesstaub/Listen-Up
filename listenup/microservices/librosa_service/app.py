
import os
from microservices_shared.modules.queue.command_executor_queue_service import CommandExecutorQueueService

SERVICE_NAME = "librosa_service"
QUEUE_NAME = f"{SERVICE_NAME}_queue"


def main():
    """Main entry point for Librosa microservice."""
    print(f"🎵 Starting {SERVICE_NAME}...")
    
    try:
        # Initialize command executor queue service  
        queue_service = CommandExecutorQueueService(
            queue_name=QUEUE_NAME,
            service_name=SERVICE_NAME
        )
        
        print(f"🚀 {SERVICE_NAME} ready to process messages from {QUEUE_NAME}")
        
        # Start processing messages
        queue_service.process_messages()
        
    except KeyboardInterrupt:
        print(f"\n👋 Shutting down {SERVICE_NAME}...")
    except Exception as e:
        print(f"❌ Error in {SERVICE_NAME}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

