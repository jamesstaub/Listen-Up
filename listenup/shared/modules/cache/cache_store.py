# Abstract cache interface (to be implemented for Firestore, MongoDB, etc.)
class CacheStore:
    def get(self, cache_key):
        raise NotImplementedError
    def set(self, cache_key, value, ttl_minutes):
        raise NotImplementedError
