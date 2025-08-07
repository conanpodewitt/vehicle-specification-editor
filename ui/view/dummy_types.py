"""
Module dummy_types.py

This module contains dummy classes to replace coconet imports during the migration process.
These should be replaced with actual implementations as the integration progresses.

"""

from typing import Any
from enum import Enum

# Enums
class SocketType(Enum):
    """Socket type enumeration"""
    INPUT = "input"
    OUTPUT = "output"

# Core model classes that were imported from coconet
class Block:
    """Dummy Block class"""
    def __init__(self):
        self.title = "Block"
        self.scene_ref = None
        self.graphics_block = None
        self.sockets = []
        self.attr_dict = {'parameters': {}}
    
    def has_parameters(self):
        """Required method for GraphicsBlock"""
        return False
    
    def update_edges(self):
        """Required method for GraphicsBlock - update connected edges when block moves"""
        if hasattr(self, 'sockets'):
            for socket in self.sockets:
                if hasattr(socket, 'edges'):
                    for edge in socket.edges:
                        if hasattr(edge, 'update_graphics_position'):
                            edge.update_graphics_position()
        
        # Also update any edges in the scene that involve this block
        if self.scene_ref and hasattr(self.scene_ref, 'edges'):
            for edge in self.scene_ref.edges.values():
                if (hasattr(edge, 'start_skt') and hasattr(edge.start_skt, 'block_ref') and 
                    edge.start_skt.block_ref == self) or \
                   (hasattr(edge, 'end_skt') and hasattr(edge.end_skt, 'block_ref') and 
                    edge.end_skt.block_ref == self):
                    if hasattr(edge, 'update_graphics_position'):
                        edge.update_graphics_position()

class Edge:
    """Dummy Edge class"""
    def __init__(self, start_socket=None, end_socket=None):
        self.start_skt = start_socket
        self.end_skt = end_socket
        self.view_dim = True
        self.graphics_edge = None
        self.id = id(self)

class Socket:
    """Dummy Socket class"""
    def __init__(self, socket_type=None, block_ref=None):
        self.s_type = socket_type or SocketType.OUTPUT
        self.block_ref = block_ref
        self.graphics_socket = None
        self.edges = []

class Scene:
    """Dummy Scene class"""
    def __init__(self):
        pass

class PropertyBlock(Block):
    """Block representing a high-level verification property"""
    def __init__(self, property_type="for_all", formula="", title="Property"):
        super().__init__()
        self.title = title
        self.property_type = property_type  # "for_all" or "exists"
        self.formula = formula
        self.verification_status = "unknown"  # "verified", "disproven", "unknown"
        self.queries = []  # List of associated queries

class QueryBlock(Block):
    """Block representing a verification query"""
    def __init__(self, query_id=1, query_text="", is_negated=False, title=None):
        super().__init__()
        self.title = title or f"Query {query_id}"
        self.query_id = query_id
        self.query_text = query_text
        self.is_negated = is_negated  # True for 'for all' properties
        self.verification_status = "unknown"  # "verified", "disproven", "unknown"
        self.property_ref = None  # Reference to parent property

class WitnessBlock(Block):
    """Block representing verification results (witness/counterexample)"""
    def __init__(self, is_counterexample=False, witness_data=None, title=None):
        super().__init__()
        self.is_counterexample = is_counterexample
        self.witness_data = witness_data or {}
        self.title = title or ("Counter Example" if is_counterexample else "Witness")
        self.query_ref = None  # Reference to associated query

class LayerBlock(Block):
    """Dummy LayerBlock class"""
    def __init__(self):
        super().__init__()

class Project:
    """Dummy Project class"""
    def __init__(self):
        pass

class CoCoNetWindow:
    """Dummy CoCoNetWindow class"""
    def __init__(self):
        pass

class GraphicsScene:
    """Dummy GraphicsScene class"""
    def __init__(self):
        pass

# Utility classes
class FileFormat:
    """Dummy FileFormat class"""
    pass

class MessageType:
    """Dummy MessageType class"""
    ERROR = "error"
    MESSAGE = "message"

# Functions
def read_properties(path: str) -> list:
    """Dummy function to read properties"""
    return []

def get_classname(obj: Any) -> str:
    """Get the class name of an object"""
    return obj.__class__.__name__

# Constants
RES_DIR = "."
