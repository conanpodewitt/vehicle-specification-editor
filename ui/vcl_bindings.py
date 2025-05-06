import os
import subprocess
import vehicle_lang as vcl
import json

from vehicle_lang import VehicleError


def execute_vcl_command(command, *args, **kwargs):
	"""Execute a command and return the output"""
	cmd = ["vehicle", command]

	# Add the positional arguments
	for command_arg in args:
		cmd.append(command_arg)

	# Add the optional
	for option, value in kwargs.items():
		option = option.replace("_", "-")
		cmd.append(f"--{option}")
		cmd.append(value)

	result = subprocess.run(cmd, capture_output=True, text=True, check=True)
	if result.returncode == 0:
		return result.stdout
	else:
		error_msg = f"{command} failed (exit code {result.code}):\n\n"
		if result.stderr:
			error_msg += f"Error output:\n{result.stderr}\n\n"
		if result.stdout:
			error_msg += f"Standard output:\n{result.stdout}"
		return error_msg


class VCLBindings:
	"""Python bindings for the Vehicle command-line tool"""

	def __init__(self, vcl_path = None):
		"""Initialize the VCLBindings class"""
		self._vcl_path = vcl_path
		self._verifier_path = None
		self._networks = {}
		self._datasets = {}
		self._parameters= {}


	def compile(self):
		"""Compile a VCL specification"""
		return vcl.compile_to_query(self._vcl_path, 
							  vcl.QueryFormat.Marabou,
							  networks=self._networks,
							  datasets=self._datasets,
							  parameters=self._parameters)
	

	def verify(self):
		"""Verify a VCL specification"""
		return vcl.verify(self._vcl_path,
						  properties=self._parameters,
						  networks=self._networks,
						  datasets=self._datasets,
						  parameters=self._parameters,
						  verifier_location=self._verifier_path)
		
	
	def resources(self):
		"""Get the resources used by the VCLBindings"""
		# Original form of resources: [ @network classifier Image -> Vector Rat 10 ]
		vcl_output = vcl.list_resources(self._vcl_path)
		if not vcl_output:
			raise VehicleError("No resources found in VCL file. Something is wrong.")
		return json.loads(vcl_output)
		

	@property
	def vcl_path(self):
		"""Get the VCL path"""
		return self._vcl_path
	

	@vcl_path.setter
	def vcl_path(self, value):
		"""Set the VCL path"""
		# Check if the file exists
		if os.path.isfile(value):
			self._vcl_path = value
		else:
			raise FileNotFoundError(f"VCL file not found: {value}")
	
	
	@property
	def verifier_path(self):
		"""Get the VCL path"""
		return self._verifier_path
	

	@verifier_path.setter
	def verifier_path(self, value):
		"""Set the Marabou Verifier path"""
		# Check if the file exists
		if os.path.isfile(value):
			self._verifier_path = value
		else:
			raise FileNotFoundError(f"Verifier binary not found: {value}")
		

	def set_network(self, name, path):
		"""Add a network to the VCLBindings"""
		if not os.path.isfile(path):
			raise FileNotFoundError(f"Network file not found: {path}")
		self._networks[name] = path


	def set_dataset(self, name, path):
		"""Add a dataset to the VCLBindings"""
		if not os.path.isfile(path):
			raise FileNotFoundError(f"Dataset file not found: {path}")
		self._datasets[name] = path


	def set_parameter(self, name, value):
		"""Add a property to the VCLBindings"""
		self._parameters[name] = value


	def clear(self):
		"""Clear all networks, datasets, and properties"""
		self._networks.clear()
		self._datasets.clear()
		self._parameters.clear()
		self._vcl_path = None

	