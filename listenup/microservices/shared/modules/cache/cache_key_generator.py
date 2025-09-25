# Shared cache logic for microservices (cloud-agnostic)

import hashlib
import json

class CacheKeyGenerator:
    @staticmethod
    def generate(job_step_name, parameters, file_checksum):
        key_data = {
            "job_step_name": job_step_name,
            "parameters": parameters,
            "file_checksum": file_checksum
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
