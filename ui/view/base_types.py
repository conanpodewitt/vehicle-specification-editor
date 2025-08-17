"""
Module base_types.py

This module contains the base classes for the node editor framework:
- Base block, socket, edge, and scene classes
- Core enumerations
- Utility functions

"""

from typing import Any
from enum import Enum
from .styling import dimension as dim


# Core enumerations
class SocketType(Enum):
    """Socket type enumeration"""
    INPUT = 0
    OUTPUT = 1


class BlockType(Enum):
    """Block type enumeration"""
    PROPERTY = 0
    QUERY = 1
    WITNESS = 2


class Status(Enum):
    """Verification status enumeration"""
    VERIFIED = 0
    DISPROVEN = 1
    UNKNOWN = 2


# Base classes
class Block:
    """Base block class for all node types"""
    def __init__(self):
        self.id = None
        self.title = "Block"
        self.scene_ref = None
        self.graphics = None  # Reference to BlockGraphics instance
        self.block_graphics = None  # Legacy reference to BlockGraphics instance
        self.sockets = []
        self.inputs = []   # Input sockets
        self.outputs = []  # Output sockets
        self.attr_dict = {'parameters': {}}
        self.x = 0
        self.y = 0
    
    def has_parameters(self):
        """Required method for GraphicsBlock"""
        return False
    
    def get_color_scheme(self):
        """Return the color scheme for this block type"""
        # Default color scheme - subclasses should override
        return ["#304153", "#34475b", "#34475b", "#304153", "#2c2c2c"]
    
    def get_socket_colors(self):
        """Return the socket colors for this block type"""
        # Default socket colors - subclasses should override  
        return {"bg_color": "#FFFFFF", "outline_color": "#FFFFFF"}
    
    def get_block_width(self):
        """Return the width for this block type"""
        # Default width - subclasses can override
        return dim.BLOCK_BASE_WIDTH
    
    def update_edges(self):
        """Update connected edges when block moves"""
        for socket in self.sockets:
            for edge in socket.edges:   
                edge.update_graphics_position()
        
        # Also update any edges in the scene that involve this block
        if self.scene_ref:
            for edge in self.scene_ref.edges.values():
                if (edge.start_skt.block_ref == self or edge.end_skt.block_ref == self):
                    edge.update_graphics_position()


class Socket:
    """Base socket class for block connections"""
    def __init__(self, socket_type, block):
        self.s_type = socket_type
        self.block_ref = block
        self.graphics = None  # Reference to SocketGraphics instance
        self.socket_graphics = None  # Legacy reference to SocketGraphics instance
        self.edges = []  # List of connected edges


class Edge:
    """Base edge class for connecting blocks"""
    def __init__(self, start_socket, end_socket):
        self.id = id(self)
        self.start_skt = start_socket
        self.end_skt = end_socket
        self.view_dim = True
        self.graphics = None  # Reference to EdgeGraphics instance
        self.edge_graphics = None  # Legacy reference to EdgeGraphics instance
        
        # Add this edge to the sockets
        start_socket.edges.append(self)
        end_socket.edges.append(self)
    
    def update_graphics_position(self):
        """Update the graphics position of this edge"""
        raise NotImplementedError("Subclasses must implement update_graphics_position")


class Scene:
    """Base scene class for managing blocks and edges"""
    def __init__(self):
        self.blocks = {}
        self.edges = {}
        self.counter = 0
    
    def add_block(self, block):
        """Add a block to the scene"""
        block.id = self.counter
        block.scene_ref = self
        self.blocks[self.counter] = block
        self.counter += 1
        return block
    
    def connect_blocks(self, source_block, target_block):
        """Connect two blocks with an edge"""
        raise NotImplementedError("Subclasses must implement connect_blocks")


# Utility functions
def get_classname(obj: Any) -> str:
    """Get the class name of an object"""
    return obj.__class__.__name__
