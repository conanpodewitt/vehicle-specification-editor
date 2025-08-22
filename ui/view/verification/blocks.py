"""
Module blocks.py

This module contains verification-specific block types for the node editor.

"""

from enum import Enum
from ..base_types import Block


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


class PropertyQuantifier(Enum):
    """Property quantifier enumeration"""
    FOR_ALL = 0
    EXISTS = 1


class PropertyBlock(Block):
    """Block representing a high-level verification property"""
    def __init__(self, property_type=PropertyQuantifier.FOR_ALL, title="Property"):
        super().__init__()
        self.title = title
        self.property_type = property_type  # FOR_ALL or EXISTS
        self.verification_status = Status.UNKNOWN  
        self.queries = []  # List of associated queries
    
    def get_color_scheme(self):
        """Return color scheme based on verification status"""
        if self.verification_status == Status.VERIFIED:
            return ["#1E8449", "#27AE60", "#27AE60", "#1E8449", "#2c2c2c"]  # Green
        elif self.verification_status == Status.DISPROVEN:
            return ["#C0392B", "#E74C3C", "#E74C3C", "#C0392B", "#2c2c2c"]  # Red
        else:  # unknown
            return ["#B7950B", "#D4AC0D", "#D4AC0D", "#B7950B", "#2c2c2c"]  # Dull Yellow
    
    def get_socket_colors(self):
        """Return socket colors for property blocks"""
        return {"bg_color": "#D4AC0D", "outline_color": "#B7950B"}  # Dull Yellow


class QueryBlock(Block):
    """Block representing a verification query"""
    def __init__(self, id, property_block, path, is_negated=False):
        super().__init__()
        self.id = id
        self.property_ref = property_block  # Reference to parent property
        self.path = path
        self.title = f"Query {id}" if not is_negated else f"¬Query {id}"
        self.is_negated = is_negated  # True for 'for all' properties
        self.verification_status = Status.UNKNOWN
    
    def get_color_scheme(self):
        """Return color scheme based on verification status"""
        if self.verification_status == Status.VERIFIED:
            return ["#1E8449", "#27AE60", "#27AE60", "#1E8449", "#2c2c2c"]  # Green
        elif self.verification_status == Status.DISPROVEN:
            return ["#C0392B", "#E74C3C", "#E74C3C", "#C0392B", "#2c2c2c"]  # Red
        else:  # unknown
            return ["#B7950B", "#D4AC0D", "#D4AC0D", "#B7950B", "#2c2c2c"]  # Dull Yellow
    
    def get_socket_colors(self):
        """Return socket colors for query blocks"""
        return {"bg_color": "#D4AC0D", "outline_color": "#B7950B"}  # Dull Yellow


class WitnessBlock(Block):
    """Block representing verification results (witness/counterexample)"""
    def __init__(self, query_block, title=None):
        super().__init__()
        self.is_counterexample = query_block.is_negated
        self.title = title or ("Counter Example" if self.is_counterexample else "Witness")
        self.query_ref = query_block  # Reference to associated query

    def get_color_scheme(self):
        """Return color scheme based on counterexample vs witness"""
        if self.is_counterexample:
            return ["#C0392B", "#E74C3C", "#E74C3C", "#C0392B", "#2c2c2c"]  # Red
        else:
            return ["#105555", "#157172", "#157172", "#105555", "#2c2c2c"]  # Teal
    
    def get_socket_colors(self):
        """Return socket colors for witness blocks"""
        if self.is_counterexample:
            return {"bg_color": "#E74C3C", "outline_color": "#C0392B"}  # Red
        else:
            return {"bg_color": "#157172", "outline_color": "#105555"}  # Teal
