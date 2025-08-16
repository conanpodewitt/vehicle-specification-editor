"""
Module blocks.py

This module contains verification-specific block types for the node editor.

"""

from ..base_types import Block, Status


class PropertyBlock(Block):
    """Block representing a high-level verification property"""
    def __init__(self, property_type="for_all", formula="", title="Property"):
        super().__init__()
        self.title = title
        self.property_type = property_type  # "for_all" or "exists"
        self.formula = formula
        self.verification_status = "unknown"  # "verified", "disproven", "unknown"
        self.queries = []  # List of associated queries
    
    def get_color_scheme(self):
        """Return color scheme based on verification status"""
        if self.verification_status == "verified":
            return ["#1E8449", "#27AE60", "#27AE60", "#1E8449", "#2c2c2c"]  # Green
        elif self.verification_status == "disproven":
            return ["#C0392B", "#E74C3C", "#E74C3C", "#C0392B", "#2c2c2c"]  # Red
        else:  # unknown
            return ["#304153", "#34475b", "#34475b", "#304153", "#2c2c2c"]  # Blue
    
    def get_socket_colors(self):
        """Return socket colors for property blocks"""
        return {"bg_color": "#FF8800", "outline_color": "#FF8800"}  # Orange
    
    def get_block_width(self):
        """Return width for property blocks"""
        return 220  # Property blocks are wider to show formulas


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
    
    def get_color_scheme(self):
        """Return color scheme based on verification status"""
        if self.verification_status == "verified":
            return ["#1E8449", "#27AE60", "#27AE60", "#1E8449", "#2c2c2c"]  # Green
        elif self.verification_status == "disproven":
            return ["#C0392B", "#E74C3C", "#E74C3C", "#C0392B", "#2c2c2c"]  # Red
        else:  # unknown
            return ["#808080", "#CCCCCC", "#CCCCCC", "#808080", "#2c2c2c"]  # Grey
    
    def get_socket_colors(self):
        """Return socket colors for query blocks"""
        return {"bg_color": "#CCCCCC", "outline_color": "#808080"}  # Grey


class WitnessBlock(Block):
    """Block representing verification results (witness/counterexample)"""
    def __init__(self, is_counterexample=False, witness_data=None, title=None):
        super().__init__()
        self.is_counterexample = is_counterexample
        self.witness_data = witness_data or {}
        self.title = title or ("Counter Example" if is_counterexample else "Witness")
        self.query_ref = None  # Reference to associated query
    
    def get_color_scheme(self):
        """Return color scheme based on counterexample vs witness"""
        if self.is_counterexample:
            return ["#D35400", "#E67E22", "#E67E22", "#D35400", "#2c2c2c"]  # Orange
        else:
            return ["#105555", "#157172", "#157172", "#105555", "#2c2c2c"]  # Teal
    
    def get_socket_colors(self):
        """Return socket colors for witness blocks"""
        if self.is_counterexample:
            return {"bg_color": "#E67E22", "outline_color": "#D35400"}  # Orange
        else:
            return {"bg_color": "#157172", "outline_color": "#105555"}  # Teal
