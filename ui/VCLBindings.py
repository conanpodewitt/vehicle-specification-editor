import os
import subprocess


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
		self._properties = {}


	def compile(self):
		"""Compile a VCL specification"""
		network_args = {"network": f"{name}:{path}" for name, path in self._networks.items()}
		dataset_args = {"dataset": f"{name}:{path}" for name, path in self._datasets.items()}
		parameter_args = {"parameter": f"{name}:{value}" for name, value in self._properties.items()}
		# Combine all arguments
		args = {**network_args, **dataset_args, **parameter_args}
		return execute_vcl_command("compile", target="MarabouQueries", specification=self._vcl_path, **args)
	

	def verify(self):
		"""Verify a VCL specification"""
		network_args = {"network": f"{name}:{path}" for name, path in self._networks.items()}
		dataset_args = {"dataset": f"{name}:{path}" for name, path in self._datasets.items()}
		parameter_args = {"parameter": f"{name}:{value}" for name, value in self._properties.items()}
		# Combine all arguments
		args = {**network_args, **dataset_args, **parameter_args}
		return execute_vcl_command("verify", 
							   specification=self._vcl_path, 
							   verifier="Marabou", 
							   verifier_location=self._verifier_path, **args)
		
	
	def resources(self):
		"""Get the resources used by the VCLBindings"""
		# Original form of resources: [ @network classifier Image -> Vector Rat 10 ]
		vcl_output = execute_vcl_command("list", "resources", specification=self._vcl_path)
		vcl_output = vcl_output.strip()[1:-1]
		vcl_output = vcl_output.split(",")

		for resource in vcl_output:
			json_resource = {}
			resource = resource.strip().split(" ")
			json_resource["type"] = resource[0].lstrip("@")
			json_resource["name"] = resource[1]

			if json_resource["type"] == "parameter":
				json_resource["data_type"] = resource[2]
			
			yield json_resource
		

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


	def set_property(self, name, value):
		"""Add a property to the VCLBindings"""
		self._properties[name] = value


	def clear(self):
		"""Clear all networks, datasets, and properties"""
		self._networks.clear()
		self._datasets.clear()
		self._properties.clear()
		self._vcl_path = None

	