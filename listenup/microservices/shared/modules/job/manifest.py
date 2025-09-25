# Manifest loading and validation utilities

import json
import os


class Manifest:
	"""
	Generic manifest base class. Subclasses must implement validation methods.
	"""
	def __init__(self, manifest_path=None):
		self.manifest_path = manifest_path
		self.manifest = None

	def validate_action(self, action_name):
		raise NotImplementedError("Subclasses must implement validate_action.")

	def validate_parameters(self, action_name, parameters):
		raise NotImplementedError("Subclasses must implement validate_parameters.")

	def validate_job(self, action_name, parameters):
		raise NotImplementedError("Subclasses must implement validate_job.")

	def parse_input_files(self, command: str) -> list:
		"""
		Parse the command string and return a list of input files.
		Subclasses should implement specific logic.
		"""
		raise NotImplementedError("Subclasses must implement parse_input_files.")

	def parse_output_files(self, command: str) -> list:
		"""
		Parse the command string and return a list of output files.
		Subclasses should implement specific logic.
		"""
		raise NotImplementedError("Subclasses must implement parse_output_files.")
