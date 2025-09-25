"""
Asset Manager Interface

This module defines the abstract base class for all Asset Manager implementations.
This ensures that any concrete class (e.g., S3, Local) provides the same
interface for downloading and uploading files.
"""
from abc import ABC, abstractmethod

class AssetManager(ABC):
    # TODO: we may want to include normalized parameters in the filepath
    # job_stesp should be determinisitic so the normalized job name + parameters should be enough to uniquely identify it.
    def construct_tmp_path(self, filename: str, job_step_name: str, file_type: str = "output") -> str:
        """
        Construct a tmp file path for input/output files.
        """
        import os
        tmp_dir = f"/tmp/{job_step_name}_{file_type}s"
        os.makedirs(tmp_dir, exist_ok=True)
        return os.path.join(tmp_dir, filename)
    """
    Abstract base class for managing asset downloads and uploads.
    """
    @abstractmethod
    def download_file(self, file_url: str, output_path: str) -> str:
        """
        Downloads a file from a remote URL to a specified local path.

        Args:
            file_url (str): The URL of the file to download.
            output_path (str): The local path where the file should be saved.

        Returns:
            str: The local path of the downloaded file.
        """
        pass

    @abstractmethod
    def upload_file(self, local_path: str, job_id: str, file_type: str) -> str:
        """
        Uploads a local file to the filestore.

        The method must generate a unique and organized path based on the job ID
        and file type.

        Args:
            local_path (str): The local path of the file to upload.
            job_id (str): The unique ID of the job.
            file_type (str): A string describing the type of file (e.g., 'audio_output').

        Returns:
            str: The public URL of the uploaded file.
        """
        pass
