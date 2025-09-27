import logging
import time
import os
from abc import ABC, abstractmethod
from typing import Any

from ..job.events import JobEvent


class QueueService(ABC):
    """
    Generic base class for a queue event listener/consumer.
    Subclass this in microservices and backend to implement handle_event.
    """

    def __init__(self, queue_client, poll_timeout=60, logger=None):
        self.queue_client = queue_client
        self.poll_timeout = poll_timeout
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def run(self):
        self.logger.info(f"{self.__class__.__name__} starting event loop...")
        while True:
            try:
                raw = self.queue_client.listen_for_event(timeout=self.poll_timeout)
                if raw:
                    try:
                        event = JobEvent.parse_obj(raw)
                    except Exception as e:
                        self.logger.error(f"Invalid event dropped: {e}")
                        continue
                    self.handle_event(event)
                else:
                    self.logger.info("No events found. Still listening...")
            except Exception as e:
                self.logger.exception(f"An error occurred in the listening loop: {e}")
                time.sleep(10)

    @abstractmethod
    def handle_event(self, event: JobEvent):
        """
        Handle a single validated JobEvent from the queue.
        """
        pass
