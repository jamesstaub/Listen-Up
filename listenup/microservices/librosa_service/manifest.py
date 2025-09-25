import os
from microservices_shared.modules.job.manifest import Manifest

class LibrosaManifest(Manifest):
    def parse_input_files(self, command: str) -> list:
        """
        For Librosa, assume the first argument with a file extension is the input file.
        """
        args = command.split()
        for arg in args:
            if "." in arg and not arg.startswith("-"):
                return [arg]
        return []

    def parse_output_files(self, command: str) -> list:
        """
        For Librosa, assume all subsequent arguments with file extensions are output files.
        """
        args = command.split()
        found_input = False
        outputs = []
        for arg in args:
            if "." in arg and not arg.startswith("-"):
                if not found_input:
                    found_input = True
                else:
                    outputs.append(arg)
        return outputs
