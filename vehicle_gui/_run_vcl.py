"""
This is a CLI for running Vehicle commands in a separate process. 
It is used to run the VCL commands in a separate process to avoid blocking the main thread.
It is also used to stream the output of the VCL commands to the main thread using asyncio.
This is a stop-gap until we develop a threaded solution inside of the Vehicle codebase.
"""

from vehicle_lang.session import Session
from vehicle_gui.vcl_bindings import CACHE_DIR
import sys
import os

if __name__ == "__main__":
	# Get the command line arguments
	args = sys.argv[1:]

	# Create a new session
	s = Session().__enter__()

	# Run the command and get the output
	log_path = os.path.join(os.path.dirname(__file__), CACHE_DIR, "log.txt")
	try:
		s.check_call(
			[
				f"--redirect-logs={log_path}",
				*args,
			]
		)
	finally:
		if os.path.exists(log_path):
			os.remove(log_path)
