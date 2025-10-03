import sys
import json
from vehicle_lang.error import VehicleError
from vehicle_lang.list import list
from typing import Union
from pathlib import Path

def list_resources(specification: Union[str, Path]) -> str:
    """
    List all networks, datasets, and non-inferable parameters in the specification.
    :param specification: The path to the Vehicle specification file to list resources for.
    :return: list of entities as JSON.
    """
    try:
        result = json.loads(list(specification))
        filtered_items = []
        for item in result:
            item_tag = item["tag"]            
            if item_tag == "Network" or item_tag == "Dataset" or (item_tag == "Parameter" and item["contents"]["inferable"] == False):
                filtered_items.append(item)
        return json.dumps(filtered_items, indent=2)
    except VehicleError as e:
        raise VehicleError(f"Error listing resources: {e}")

def list_properties(specification: Union[str, Path]) -> str:
    """
    List all properties in specification.
    :param specification: The path to the Vehicle specification file to list resources for.
    :return: list of entities as JSON.
    """
    try:
        result = json.loads(list(specification))
        filtered_items = []
        for item in result:
            item_tag = item["tag"]            
            if item_tag == "Property":
                filtered_items.append(item)
        return json.dumps(filtered_items, indent=2)
    except VehicleError as e:
        raise VehicleError(f"Error listing resources: {e}")

def get_resources_info(specification: Union[str, Path]) -> str:
    """
    Get resources info from the specification.
    :param specification: The path to the Vehicle specification file to get resources info for.
    :return: resources info.
    """
    try:
        resources_json = json.loads(list_resources(specification))
        resources_info = []
        for item in resources_json:
            resources_info.append({"tag": item["tag"], "name": item["contents"]["sharedData"]["name"], "typeText": item["contents"]["sharedData"]["typeText"]})
        return json.dumps(resources_info, indent=2)
    except VehicleError as e:
        raise VehicleError(f"Error getting resources info: {e}")

def get_properties_info(specification: Union[str, Path]) -> str:
    """
    Get properties info from the specification.
    :param specification: The path to the Vehicle specification file to get properties info for.
    :return: properties info.
    """
    try:
        properties_json = json.loads(list_properties(specification))
        properties_info = []
        for item in properties_json:
            quantified_var_names = [var["sharedData"]["name"] for var in item["contents"]["quantifiedVariables"]]
            properties_info.append({"name": item["contents"]["sharedData"]["name"], 
                                    "quantifiedVariablesInfo": quantified_var_names,
                                    "type": item["contents"]["sharedData"]["typeText"]})
        return json.dumps(properties_info, indent=2)
    except VehicleError as e:
        raise VehicleError(f"Error getting properties info: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = Path(__file__).parent.parent / "temp" / "temp.vcl"
    results = get_resources_info(file_path)
    print("--------------Resources---------------")
    print(results)
    print("--------------Properties---------------")
    results = get_properties_info(file_path)
    print(results)