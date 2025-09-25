import os
from microservices_shared.modules.job.manifest import Manifest

class FlucomaManifest(Manifest):
	# TODO: maybe it would be better off instead to ensure that input files always are prepended with input_* and output files with output_*?
	def parse_input_files(self, command: str) -> list:
		"""
		For FluCoMa, assume the first argument with a file extension is the input file.
		"""
		args = command.split()
		for arg in args:
			if "." in arg and not arg.startswith("-"):
				return [arg]
		return []

	def parse_output_files(self, command: str) -> list:
		"""
		For FluCoMa, assume all subsequent arguments with file extensions are output files.
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
	"""
	Manifest for Flucoma microservice. Uses ENV for allowed commands.
	"""
	def __init__(self, manifest_path=None, bin_dir=None):
		super().__init__(manifest_path)
		self.bin_dir = bin_dir or os.environ.get("FLUCOMA_BIN_DIR", "/opt/flucoma-cli/FluidCorpusManipulation/bin")
		self.allowed_commands = self._load_bin_commands()

	def _load_bin_commands(self):
		"""
		Load available commands from the FluCoMa CLI bin directory into a dict.
		"""
		try:
			if not os.path.isdir(self.bin_dir):
				print(f"Warning: FluCoMa bin directory not found: {self.bin_dir}")
				return {}
			commands = {}
			for fname in os.listdir(self.bin_dir):
				fpath = os.path.join(self.bin_dir, fname)
				if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
					commands[fname] = fpath
			return commands
		except Exception as e:
			print(f"Error loading FluCoMa commands: {e}")
			return {}

	def validate_action(self, action_name):
		if action_name in self.allowed_commands:
			return {"name": action_name, "path": self.allowed_commands[action_name]}
		raise ValueError(f"Action '{action_name}' is not allowed for Flucoma.")

	def validate_parameters(self, action_name, parameters):
		# For quick start, accept any parameters
		return True

	def validate_job(self, action_name, parameters):
		self.validate_action(action_name)
		self.validate_parameters(action_name, parameters)
		return {"name": action_name, "parameters": parameters}
