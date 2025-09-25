"""
Redis Client

This module provides a dedicated client class for handling all Redis interactions,
separating the queue logic from the core business logic.
"""
import redis
import json
import os

class RedisClient:
    """
    A client for connecting to Redis and performing queue-related operations.
    """

    def __init__(self, host: str, port: int, queue_name: str):
        """
        Initializes the Redis client and establishes a connection.

        Args:
            host (str): The Redis server hostname.
            port (int): The Redis server port.
            queue_name (str): The name of the Redis list to use as a queue.
        """
        self.queue_name = queue_name
        self.redis_client = redis.StrictRedis(
            host=host,
            port=port,
            db=0,
            decode_responses=True
        )
        print(f"Redis client initialized for queue '{self.queue_name}'.")

    def listen_for_job(self, timeout: int = 60):
        """
        Performs a blocking pop operation to retrieve the next job from the queue.

        Args:
            timeout (int): The maximum time in seconds to wait for a job.

        Returns:
            dict or None: The deserialized job payload if a job is found, otherwise None.
        """
        try:
            # blpop is a blocking call that waits for an item on the list.
            # It's an efficient way to listen for new jobs.
            queue_name, job_payload_json = self.redis_client.blpop(self.queue_name, timeout=timeout)
            
            if job_payload_json:
                print(f"Found a new job on queue '{self.queue_name}'.")
                return json.loads(job_payload_json)
            else:
                return None

        except redis.exceptions.ConnectionError as e:
            print(f"Error: Could not connect to Redis. Please check server status. Error: {e}")
            raise
        except json.JSONDecodeError as e:
            print(f"Error: Could not decode JSON from queue. Error: {e}")
            return None

    def publish_job(self, job_payload: dict):
        """
        Adds a new job to the end of the queue.

        Args:
            job_payload (dict): The job data to be processed by a worker.
        """
        try:
            self.redis_client.rpush(self.queue_name, json.dumps(job_payload))
            print(f"Job published to Redis queue '{self.queue_name}'.")
        except redis.exceptions.ConnectionError as e:
            print(f"Error: Could not publish job to Redis. Error: {e}")
            raise
