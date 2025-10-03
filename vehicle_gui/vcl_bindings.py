import os
import re
import sys
import vehicle_lang as vcl
import json
import asyncio
from vehicle_lang import VehicleError
from typing import Sequence, Optional, Callable
from vehicle_gui.vcl_utils import get_resources_info
from vehicle_gui.vcl_utils import get_properties_info


CACHE_DIR = os.path.join(os.path.expanduser("~"), ".vehicle")

class Runner:
	def __init__(self, command: str,  script: str = "_run_vcl.py", *args: str, **kwargs: str):
		self.script_path = os.path.join(os.path.dirname(__file__), script)
		self.cmd = self.build_command(command, args, kwargs)

	def build_command(self, command: str, args: Sequence[str], kwargs: dict) -> list[str]:
		cmd = [sys.executable, "-u", self.script_path, command]
		cmd.extend(args)

		# Keyword is --option
		for option, value in kwargs.items():
			flag = f"--{option.replace('_', '-')}"
			# Handle networks, datasets, and parameters, which requires flag to be repeated for each name-value pair
			if isinstance(value, dict):
				for name, val in value.items():
					cmd.append(flag)
					cmd.append(f"{name}:{val}")
			# Handle properties, which requires flag to be repeated for each property
			elif isinstance(value, list):
				for item in value:
					cmd.append(flag)
					cmd.append(str(item))
			# Handle other parameters
			else:
				cmd.append(flag)
				cmd.append(str(value))
				
		return cmd

	async def run(self, line_reader: Callable, finish_fn: Callable, stop_event: asyncio.Event) -> str:
		process = await asyncio.create_subprocess_exec(
			*self.cmd,
			stdout=asyncio.subprocess.PIPE,
			stderr=asyncio.subprocess.PIPE
		)

		async def stream_output(stream, tag):
			while True:
				data_chunk = await stream.read(4096)
				if not data_chunk:
					break
				decoded = data_chunk.decode(errors="replace")
				line_reader(tag, decoded)

		async def watch_stop():
			while True:
				await asyncio.sleep(0.1)
				if stop_event.is_set():
					print(f"[DEBUG] Stopping process: {self.cmd}")
					try:
						process.terminate()
					except ProcessLookupError:
						pass

		stdout_task = asyncio.create_task(stream_output(process.stdout, "stdout"))
		stderr_task = asyncio.create_task(stream_output(process.stderr, "stderr"))
		stop_task = asyncio.create_task(watch_stop())

		await asyncio.wait([stdout_task, stderr_task, stop_task], return_when=asyncio.FIRST_COMPLETED)

		exit_code = await process.wait()
		finish_fn(exit_code)

	def run_sync(self, command: str, *args: str, **kwargs: str) -> str:
		return asyncio.run(self.run(command, *args, **kwargs))


class VCLBindings:
	"""Python bindings for the Vehicle command-line tool"""
	def __init__(self, vcl_path = None):
		"""Initialize the VCLBindings class"""
		self._vcl_path = vcl_path
		self._verifier_path = None
		self._networks = {}
		self._datasets = {}
		self._parameters = {}
		self._properties = []

	def compile(self, callback_fn: Callable, finish_fn: Callable, stop_event: asyncio.Event):
		"""Compile a VCL specification"""
		runner = Runner(
			command="compile", 
			specification=self._vcl_path, 
			network=self._networks,
			dataset=self._datasets,
			parameter=self._parameters,
			target="MarabouQueries",
			output=CACHE_DIR,
		)
		asyncio.run(runner.run(
			line_reader=callback_fn, 
			finish_fn=finish_fn,
			stop_event=stop_event,
		))
	
	def verify(self, callback_fn: Callable, finish_fn: Callable, stop_event: asyncio.Event):	
		"""Verify a VCL specification"""	
		runner = Runner(
			command="verify", 
			specification=self._vcl_path, 
			verifier="Marabou", 
			verifier_location=self._verifier_path, 
			network=self._networks,
			dataset=self._datasets,
			parameter=self._parameters,
			cache=CACHE_DIR,
			property=self._properties,
		)
		asyncio.run(runner.run(
			line_reader=callback_fn, 
			finish_fn=finish_fn,
			stop_event=stop_event,
		))

	def type_check(self):
		"""Type check a VCL specification"""
		try:
			# Temporary method until type checking is fixed in vehicle_lang
			vcl.list(self._vcl_path)
		except VehicleError as e:
			error_str = str(e)
			error_json = json.loads(error_str)
			if "provenance" not in error_json:
				# error is not JSON formatted. This is a syntax error caught by BNFC parser
				match = re.search(r"line (\d+), column (\d+)", error_str)
				if match:
					line, column = [int(g) for g in match.groups()]
					start_col = max(1, column - 3)
					end_col = column + 2

					error_json = [{
						"provenance": {
							"tag": "Provenance",
							"contents": [line, start_col, line, end_col]
						},
						"problem": "Syntax Error",
						"fix": f"fix {error_json}"
					}]
			if not isinstance(error_json, list):
				error_json = [error_json]
			return error_json
		return []

	def resources(self):
		"""Get the resources used by the VCLBindings"""
		vcl_output = get_resources_info(self._vcl_path)
		if not vcl_output:
			raise VehicleError("No resources found in VCL file. Something is wrong.")
		return json.loads(vcl_output)

	def properties(self):
		"""Get the properties in the VCL specification"""
		vcl_output = get_properties_info(self._vcl_path)
		if not vcl_output:
			return []
		return json.loads(vcl_output)
	
	def variables(self):
		"""Get the quantified variables listed in the VCL specification"""
		result = get_properties_info(self._vcl_path)
		if not result:
			return []
		result = json.loads(result)
		vars = set()
		for item in result:
			vars = vars.union(set(item["quantifiedVariablesInfo"]))
		return [{"name": var, "tag": "Variable"} for var in vars]

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

	def set_properties(self, properties: list[str]):
		"""Set the list of properties to verify"""
		self._properties = properties

	def clear(self):
		"""Clear all networks, datasets, and properties"""
		self._networks.clear()
		self._datasets.clear()
		self._parameters.clear()
		self._properties.clear()
		self._vcl_path = None