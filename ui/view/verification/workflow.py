"""
Module verification_workflow.py

This module contains the high-level verification workflow generator
that creates verification graphs from data.

"""

from .model import VerificationScene
from ..graphics_scene import GraphicsScene
from ..component.block_graphics import BlockGraphics
from ..component.socket_graphics import SocketGraphics
from ..component.edge_graphics import BezierEdgeGraphics
from ..base_types import SocketType
import ui.view.styling.dimension as dim


class VerificationWorkflowGenerator:
    """High-level generator for verification workflows"""
    
    def __init__(self, graphics_scene):
        self.scene = VerificationScene()
        self.graphics_scene = graphics_scene
    
    def create_example_workflow(self):
        """Create an example verification workflow for testing"""
        # For-all property workflow
        property1 = self.scene.add_property_block("for_all", "∀x (speed(x) ≤ max_speed)", -200, -100)
        query1 = self.scene.add_query_block(1, "speed(x1) > max_speed", True, 0, 0)
        query2 = self.scene.add_query_block(2, "speed(x2) > max_speed", True, 150, 0)
        
        # Exists property workflow  
        property2 = self.scene.add_property_block("exists", "∃x (brake_response(x) < 0.5s)", -200, 200)
        query3 = self.scene.add_query_block(3, "brake_response(x3) < 0.5s", False, 0, 300)
        
        # Witnesses
        counterexample = self.scene.add_witness_block(True, {"speed": 85}, 150, 120)
        witness = self.scene.add_witness_block(False, {"brake_response": 0.3}, 0, 420)
        
        # Create graphics for all blocks
        for block in [property1, query1, query2, property2, query3, counterexample, witness]:
            self._create_graphics_block(block)
        
        # Connect blocks
        connections = [
            (property1, query1), (property1, query2), (query1, counterexample),
            (property2, query3), (query3, witness)
        ]
        for source, target in connections:
            self._connect_blocks(source, target)
    
    def create_workflow_from_data(self, verification_data):
        """Create a verification workflow from structured data"""
        # This method would parse real verification data
        # For now, it creates the example workflow
        self.create_example_workflow()
    
    def _create_graphics_block(self, block):
        """Create graphics representation for a block"""
        graphics_block = BlockGraphics(block)
        graphics_block.setPos(block.x, block.y)
        block.block_graphics = graphics_block
        self.graphics_scene.addItem(graphics_block)
        
        # Create graphics for sockets
        for socket in block.sockets:
            graphics_socket = SocketGraphics(socket)
            if socket.s_type == SocketType.INPUT:
                socket_x = dim.SOCKET_RADIUS
            else:
                socket_x = graphics_block.width - dim.SOCKET_RADIUS
            socket_y = graphics_block.height // 2
            graphics_socket.setPos(socket_x, socket_y)
            graphics_socket.setParentItem(graphics_block)
            socket.socket_graphics = graphics_socket
    
    def _connect_blocks(self, source_block, target_block):
        """Create a connection between two blocks"""
        edge = self.scene.connect_blocks(source_block, target_block)
        if edge:
            graphics_edge = BezierEdgeGraphics(edge)
            
            # Calculate initial positions
            start_pos = source_block.block_graphics.pos()
            end_pos = target_block.block_graphics.pos()
            graphics_edge.src_pos = [
                start_pos.x() + source_block.block_graphics.width - dim.SOCKET_RADIUS,
                start_pos.y() + source_block.block_graphics.height // 2
            ]
            graphics_edge.dest_pos = [
                end_pos.x() + dim.SOCKET_RADIUS,
                end_pos.y() + target_block.block_graphics.height // 2
            ]
            graphics_edge.update_path()
            
            self.graphics_scene.addItem(graphics_edge)
            edge.edge_graphics = graphics_edge
