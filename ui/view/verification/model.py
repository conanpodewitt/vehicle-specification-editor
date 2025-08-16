"""
Module verification_model.py

This module contains the verification-specific scene, socket, and edge classes
for managing verification workflows in the node editor.

"""

from ..base_types import Scene, Socket, Edge, SocketType
from .blocks import PropertyBlock, QueryBlock, WitnessBlock
import ui.view.styling.dimension as dim


class VerificationScene(Scene):
    """Scene class specifically for verification workflows"""
    
    def add_property_block(self, property_type, formula, x=0, y=0):
        """Add a property block to the verification scene"""
        block = PropertyBlock(property_type, formula, f"Property ({property_type})")
        return self._setup_block(block, x, y, [SocketType.OUTPUT])
    
    def add_query_block(self, query_id, query_text, is_negated=False, x=0, y=0):
        """Add a query block to the verification scene"""
        title = f"{'¬' if is_negated else ''}Query {query_id}"
        block = QueryBlock(query_id, query_text, is_negated, title)
        return self._setup_block(block, x, y, [SocketType.INPUT, SocketType.OUTPUT])
    
    def add_witness_block(self, is_counterexample=False, witness_data=None, x=0, y=0):
        """Add a witness/counterexample block to the verification scene"""
        title = "Counter Example" if is_counterexample else "Witness"
        block = WitnessBlock(is_counterexample, witness_data, title)
        return self._setup_block(block, x, y, [SocketType.INPUT])
    
    def _setup_block(self, block, x, y, socket_types):
        """Setup a block with position, sockets, and scene reference"""
        block.x, block.y = x, y
        block.attr_dict = {'parameters': {}}
        block.sockets = [VerificationSocket(st, block) for st in socket_types]
        block.has_parameters = lambda: False
        
        def update_edges():
            if block.scene_ref:
                for edge in block.scene_ref.edges.values():
                    if (edge.start_skt.block_ref == block or edge.end_skt.block_ref == block):
                        edge.update_graphics_position()
        
        block.update_edges = update_edges
        return self.add_block(block)
    
    def connect_blocks(self, source_block, target_block):
        """Connect two blocks in the verification workflow"""
        source_socket = next((s for s in source_block.sockets if s.s_type == SocketType.OUTPUT), None)
        target_socket = next((s for s in target_block.sockets if s.s_type == SocketType.INPUT), None)
        
        if source_socket and target_socket:
            edge = VerificationEdge(source_socket, target_socket)
            self.edges[edge.id] = edge
            return edge
        return None


class VerificationSocket(Socket):
    """Socket class specifically for verification blocks"""
    
    def __init__(self, socket_type, block):
        super().__init__(socket_type, block)


class VerificationEdge(Edge):
    """Edge class specifically for verification workflows"""
    
    def update_graphics_position(self):
        """Update the graphics position of this verification edge"""
        if self.edge_graphics and self.start_skt.block_ref.block_graphics and self.end_skt.block_ref.block_graphics:
            start_pos = self.start_skt.block_ref.block_graphics.pos()
            end_pos = self.end_skt.block_ref.block_graphics.pos()
            
            start_x = start_pos.x() + self.start_skt.block_ref.block_graphics.width - dim.SOCKET_RADIUS
            start_y = start_pos.y() + self.start_skt.block_ref.block_graphics.height // 2
            end_x = end_pos.x() + dim.SOCKET_RADIUS
            end_y = end_pos.y() + self.end_skt.block_ref.block_graphics.height // 2
            
            self.edge_graphics.src_pos = [start_x, start_y]
            self.edge_graphics.dest_pos = [end_x, end_y]
            self.edge_graphics.update_path()
