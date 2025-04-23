import os
import subprocess


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
		try:
			# Add required --target parameter with a valid value (VehicleLoss)
			cmd = ["vehicle", "compile", "--target", "VehicleLoss", "--specification", self._vcl_path]
			result = subprocess.run(cmd, capture_output=True, text=True, check=True)
			return result.stdout
		except subprocess.CalledProcessError as e:
			return e.stderr
		except Exception as e:
			return str(e)
	

	def verify(self, output_json=False):
		"""Verify a VCL specification"""
		try:
			# Directly use the filename as network name
			filename = os.path.basename(self._vcl_path)
			network_name = os.path.splitext(filename)[0]
			
			# Build command
			cmd = ["vehicle", "verify", "--specification", self._vcl_path]
			
			# Add network
			print(f"Using network argument: {self._networks}")
			cmd.extend(["--network", self._networks])
			
			# Add verifier
			cmd.extend(["--verifier", "Marabou", "--verifier-location", self._verifier_path])
			
			# If JSON output is needed
			if output_json:
				cmd.append("--json")
			
			# Print full command for debugging
			print(f"Executing command: {' '.join(cmd)}")
			
			# Execute command
			result = subprocess.run(cmd, capture_output=True, text=True)
			
			# Return result with debug info
			if result.returncode == 0:
				return "Verification successful:\n\n" + result.stdout
			else:
				error_msg = f"Verification failed (exit code {result.returncode}):\n\n"
				if result.stderr:
					error_msg += f"Error output:\n{result.stderr}\n\n"
				if result.stdout:
					error_msg += f"Standard output:\n{result.stdout}"
				return error_msg
		except Exception as e:
			import traceback
			return f"Exception during verification:\n{str(e)}\n\n{traceback.format_exc()}"
		

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

	