import idx2numpy
import os
import json
import sys

def get_vehicle_type(dtype: str) -> str:
    """
    Get the vehicle type based on the dtype.
    :param dtype: Data type of the numpy array.
    :return: Vehicle type as a string.
    """
    if dtype == 'ubyte':
        return "NatTensor"
    elif dtype == 'byte' or dtype == '>i2' or dtype == '>i4':
        return "IntTensor"
    elif dtype == '>f4' or dtype == '>f8':
        return "RatTensor"
    else:
        raise ValueError(f"Unsupported data type: {dtype}")
    

# Convert to tensor and provide as JSON
def convert_to_tensor(ndarr) -> dict:
    """
    Returns the numpy array as a tensor in JSON format.
    :param ndarr: Numpy array to be converted.
    :return: JSON representation of the tensor.
    The JSON format is:
    {
        "type": "NatTensor" | "IntTensor" | "RatTensor",
        "shape": [dim1, dim2, ...],
        "data": ndarr
    }
    """
    return {
        "type": get_vehicle_type(ndarr.dtype),
        "shape": ndarr.shape,
        "data": ndarr
    }
    

# Using the idx2numpy library to decode IDX files which follows the IDX file format.
# https://www.fon.hum.uva.nl/praat/manual/IDX_file_format.html
def decode_idx(filename : str) -> dict:
    """
    Decode IDX file and convert it to numpy array.
    :param filename: Path to the IDX file."""
    ndarr = idx2numpy.convert_from_file(filename)

    tensor_json = convert_to_tensor(ndarr)
    # print(tensor_json)
    
    return tensor_json

def decode_counter_examples(cache_dir: str = "../temp") -> dict:
    """
    Decode counterexamples for tensor assignments stored in IDX files in the specified cache directory.
    :param cache_dir: Directory containing IDX files."""
    # All subdirectories with counterexamples is the ending with '-assignments'
    subdirs = [
        d for d in os.listdir(cache_dir)
        if os.path.isdir(os.path.join(cache_dir, d)) and d.endswith("-assignments")
    ]

    print("Subdirectories ending with '-assignments':", subdirs)

    counter_examples = {}

    for subdir in subdirs:
        print(f"Decoding IDX files in subdirectory: {subdir}")
        subdir_path = os.path.join(cache_dir, subdir)
        for filename in os.listdir(subdir_path):
            full_path = os.path.join(subdir_path, filename)
            print(f"Decoding file: {full_path}")
            tensor_json = decode_idx(full_path)
            counter_examples[filename] = tensor_json
    
    return counter_examples

# Testing from command line
if __name__ == "__main__":
    if len(sys.argv) > 1:
        cache_location = sys.argv[1]
    else:
        raise ValueError("Cache directory argument missing. Please provide the cache directory as a command-line argument.")
    result = decode_counter_examples(cache_location)
    print(json.dumps(result, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o), indent=2))