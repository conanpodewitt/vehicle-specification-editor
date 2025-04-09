from vehicle_lang.ast import *

import json
import os
import sys
import argparse
from typing import List, Dict, Any, Optional


def parse_node(node, elements_found, property_name) -> None:
    if isinstance(node, Lam):
        binder = node.binder

        # Extract information from the binder
        item_name: Optional[Name] = binder.name
        item_cls: Union[Expression, BuiltinType] = binder.type

        # Only process if the binder has a name
        if item_name:
            element_info = {
                "name": item_name,
                "type_name": item_cls.__class__.__name__,
                "property_name": property_name,
            }
			
            if type(item_cls) == Pi:
                element_info["element_type"] = "network"
            elif type(item_cls) == TensorType:
                element_info["element_type"] = "parameter"
            #### NEED TO ADD DATASET TYPE HERE
			
            elements_found[item_name] = element_info
			
        lam_function = node.body
        parse_node(lam_function, elements_found, property_name)
    
    elif isinstance(node, BuiltinFunction):
        if type(node.body) == list:
            for arg in node.body:
                parse_node(arg, elements_found, property_name)
        else:
            parse_node(node.body, elements_found, property_name)
			
	
def extract_elements(ast: Program) -> List[Dict[str, Any]]:
    """
    Extract network, dataset, and parameter information from a Vehicle AST Program object.

    Identifies elements based on the pattern: A DefFunction where the
    body is a Lam, taking the Lam's binder as the network definition.

    Args:
        ast: The parsed Program AST object.

    Returns:
        A dictionary containing the extracted elements, where each key is the
        element name and the value is a dictionary containing information about the element.
    """
    elements_found: Dict[str, Any] = {}

    # Ensure the root is a Main program node
    if not isinstance(ast, Main):
        print("Warning: AST root is not Main node.", file=sys.stderr)
        return elements_found

    # Iterate through top-level declarations
    for declaration in ast.declarations:
        if isinstance(declaration, DefFunction):
            parse_node(declaration.body, elements_found, declaration.name)

    return elements_found


file_path = os.path.dirname(os.path.abspath(__file__))
spec_path = os.path.join(file_path, "golden_spec.json")


def main():
	parser = argparse.ArgumentParser(description='Extract network definitions from Vehicle AST JSON')
	parser.add_argument('--ast_file', default=spec_path, help='Path to the AST JSON file')
	parser.add_argument('--format', choices=['json', 'minimal'], default='json',
					  help='Output format (json, or minimal)')
	parser.add_argument('--names-only', action='store_true', help='Only output network names')
	args = parser.parse_args()
	
	try:
		with open(args.ast_file, 'r') as f:
			ast = Program.from_json(f.read())
        
		elements = extract_elements(ast)
		
		if not elements:
			print("No elements found in the AST.")
			return
		
		# Handle different output formats
		if args.names_only:
			for network in elements:
				print(network['name'])
				
		elif args.format == 'json':
			print(json.dumps(elements, indent=2))

		elif args.format == 'minimal':
			for network in elements:
				name = network['name']
				defined_in = network['property_name']
				print(f"{name} (defined in {defined_in})")
	
	except FileNotFoundError:
		print(f"Error: File '{args.ast_file}' not found.")
		sys.exit(1)
	except json.JSONDecodeError:
		print(f"Error: File '{args.ast_file}' is not a valid JSON file.")
		sys.exit(1)

if __name__ == "__main__":
	main() 