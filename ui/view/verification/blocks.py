"""
Module blocks.py

This module contains verification-specific block types for the node editor.

"""

from enum import Enum
from ..base_types import Block
from ..styling.palette import *


PALETTE = {
    # [_pen_default, _pen_hovered, _pen_selected, _brush_title, _brush_background]
    "AND":       ( [BLUE_0, BLUE_1, DARK_BLUE, BLUE_0, DARK_GREY],                  {"bg_color": BLUE_1,    "outline_color": BLUE_0} ),
    "OR":        ( [VIOLET, VIOLET_1, BLUE, VIOLET, DARK_GREY],                     {"bg_color": VIOLET_1,  "outline_color": VIOLET} ),
    "VERIFIED":  ( [DARK_GREEN, LIGHT_GREEN, LIGHT_GREEN, DARK_GREEN, DARK_GREY],   {"bg_color": LIGHT_GREEN, "outline_color": DARK_GREEN} ),
    "DISPROVEN": ( [DARK_RED, LIGHT_RED, LIGHT_RED, DARK_RED, DARK_GREY],           {"bg_color": LIGHT_RED,   "outline_color": DARK_RED} ),
    "UNKNOWN":   ( [DARK_ORANGE, ORANGE_1, ORANGE_0, DARK_ORANGE, DARK_GREY],       {"bg_color": ORANGE_1,    "outline_color": DARK_ORANGE} ),
    "WITNESS":   ( [DARK_TEAL, TEAL, LIGHT_TEAL, DARK_TEAL, DARK_GREY],             {"bg_color": TEAL,        "outline_color": DARK_TEAL} ),
}


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


class OrBlock(Block):
    """Block representing a disjunction (OR) in verification properties"""
    def __init__(self, parent=None):
        super().__init__()
        self.title = "OR"
        self.children = []  # List of child blocks
        self.parent_ref = parent  # Reference to parent block
        self.verification_status = Status.UNKNOWN   # Whether this proves or disproves the original property
    
    def get_color_scheme(self):
        """Return color scheme for OR blocks"""
        return PALETTE["OR"][0]
    
    def get_socket_colors(self):
        """Return socket colors for OR blocks"""
        return PALETTE["OR"][1]


class AndBlock(Block):
    """Block representing a conjunction (AND) in verification properties"""
    def __init__(self, parent=None):
        super().__init__()
        self.title = "AND"
        self.children = []  # List of child blocks
        self.parent_ref = parent  # Reference to parent block
        self.verification_status = Status.UNKNOWN       # Whether this proves or disproves the original property

    def get_color_scheme(self):
        """Return color scheme for AND blocks"""
        # [_pen_default, _pen_hovered , _pen_selected, _brush_title, _brush_background]
        return PALETTE["AND"][0]

    def get_socket_colors(self):
        """Return socket colors for AND blocks"""
        return PALETTE["AND"][1]


class PropertyBlock(Block):
    """Block representing a high-level verification property"""
    def __init__(self, title="Property"):
        super().__init__()
        self.title = title
        self.verification_status = Status.UNKNOWN
        self.children = []  # List of child blocks
        self.queries = []   # List of associated queries

    def get_color_scheme(self):
        """Return color scheme based on verification status"""
        key = "UNKNOWN"
        if self.verification_status == Status.VERIFIED:
            key = "VERIFIED"
        elif self.verification_status == Status.DISPROVEN:
            key = "DISPROVEN"
        return PALETTE[key][0]
    
    def get_socket_colors(self):
        """Return socket colors for property blocks"""
        key = "UNKNOWN"
        if self.verification_status == Status.VERIFIED:
            key = "VERIFIED"
        elif self.verification_status == Status.DISPROVEN:
            key = "DISPROVEN"
        return PALETTE[key][1]


class QueryBlock(Block):
    """Block representing a verification query"""
    def __init__(self, id, parent, path, is_negated=False):
        super().__init__()
        self.id = id
        self.parent_ref = parent
        self.path = path
        self.title = f"Query {id}" if not is_negated else f"¬Query {id}"
        self.is_negated = is_negated 
        self.verification_status = Status.UNKNOWN
    
    def get_color_scheme(self):
        """Return color scheme based on verification status"""
        key = "UNKNOWN"
        if self.verification_status == Status.VERIFIED:
            key = "VERIFIED"
        elif self.verification_status == Status.DISPROVEN:
            key = "DISPROVEN"
        return PALETTE[key][0]
    
    def get_socket_colors(self):
        """Return socket colors for query blocks"""
        key = "UNKNOWN"
        if self.verification_status == Status.VERIFIED:
            key = "VERIFIED"
        elif self.verification_status == Status.DISPROVEN:
            key = "DISPROVEN"
        return PALETTE[key][1]


class WitnessBlock(Block):
    """Block representing verification results (witness/counterexample)"""
    def __init__(self, query_block):
        super().__init__()
        self.is_counterexample = query_block.is_negated
        self.query_ref = query_block  # Reference to associated query
        self.title = "Counter Example" if self.is_counterexample else "Witness"

    def get_color_scheme(self):
        """Return color scheme based on counterexample vs witness"""
        return PALETTE["DISPROVEN"][0] if self.is_counterexample else PALETTE["WITNESS"][0]
    
    def get_socket_colors(self):
        """Return socket colors for witness blocks"""
        return PALETTE["DISPROVEN"][1] if self.is_counterexample else PALETTE["WITNESS"][1]
