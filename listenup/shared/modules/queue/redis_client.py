import redis
import os
import json

class RedisQueueClient:
    def __init__(self, host=None, port=None, queue_name=None):
        self.host = host or os.environ.get("REDIS_HOST", "localhost")
        self.port = port or int(os.environ.get("REDIS_PORT", 6379))
        self.queue_name = queue_name
        self.redis = redis.StrictRedis(
            host=self.host,
            port=self.port,
            decode_responses=True
        )

    def push_event(self, event: dict):
        """
        Push a JSON event to the Redis queue.
        """
        self.redis.rpush(self.queue_name, json.dumps(event))

    def listen_for_event(self, timeout=60):
        """
        Block until an event is available on the Redis queue.
        Returns the deserialized JSON dict, or None on timeout.
        """
        result = self.redis.blpop(self.queue_name, timeout=timeout)
        if result:
            return json.loads(result[1])
        return None
