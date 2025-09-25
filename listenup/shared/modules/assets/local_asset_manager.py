"""
Local Asset Manager

This is a concrete implementation of the AssetManager for a local
development environment. It reads and writes files from the local
filesystem instead of a remote filestore.
"""
import os
import shutil
import time
from asset_manager import AssetManager

class LocalAssetManager(AssetManager):
    """
    Manages assets on the local filesystem. Ideal for development and testing.
    """
    def __init__(self, base_dir: str = "local_filestore"):
        """
        Initializes the LocalAssetManager.

        Args:
            base_dir (str): The root directory for storing assets.
        """
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        print(f"LocalAssetManager initialized. Files will be stored in: {self.base_dir}")

    def download_file(self, file_url: str, filename: str, job_step_name: str, file_type: str = "input") -> str:
        """
        Simulates downloading a file by creating an empty mock file at a constructed tmp path.
        """
        output_path = self.construct_tmp_path(filename, job_step_name, file_type)
        print(f"  LocalAssetManager: Simulating download from {file_url}...")
        time.sleep(1) # Simulate network delay
        with open(output_path, 'w') as f:
            f.write("This is a mock downloaded file.")
        print(f"  LocalAssetManager: Mock download complete. File saved to {output_path}")
        return output_path

    def upload_file(self, local_path: str, job_id: str, file_type: str) -> str:
        """
        "Uploads" a file by moving it to the local filestore directory
        and returning a local path as the "URL".
        """
        # Create an organized subdirectory for the job
        job_dir = os.path.join(self.base_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        # Determine the destination path based on file_type
        filename = os.path.basename(local_path)
        destination_path = os.path.join(job_dir, f"{file_type}_{filename}")

        print(f"  LocalAssetManager: 'Uploading' file {local_path} to {destination_path}...")
        shutil.copyfile(local_path, destination_path)
        print(f"  LocalAssetManager: 'Upload' complete.")
        
        # Return the local path, which serves as the "upload URL" in dev
        return os.path.abspath(destination_path)
