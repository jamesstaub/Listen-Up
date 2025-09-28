"""
Shared logging utilities for microservices.
"""

def get_logger(service_name, context=None):
    """
    Get a simple logger instance for microservices.
    
    Args:
        service_name: Name of the service for log prefixing
        context: Optional context for additional log information
        
    Returns:
        SimpleLogger: Logger instance
    """
    class SimpleLogger:
        def __init__(self, name):
            self.name = name
        
        def info(self, msg):
            print(f"[{self.name}] INFO: {msg}")
        
        def error(self, msg):
            print(f"[{self.name}] ERROR: {msg}")
        
        def warning(self, msg):
            print(f"[{self.name}] WARNING: {msg}")
        
        def debug(self, msg):
            print(f"[{self.name}] DEBUG: {msg}")
    
    return SimpleLogger(service_name)
