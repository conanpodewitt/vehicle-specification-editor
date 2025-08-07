import os
from PyQt6.QtWidgets import QVBoxLayout, QSizePolicy, QWidget
from PyQt6 import QtGui
from pathlib import Path
import re

# Import node editor components
from ui.view.graphics_scene import GraphicsScene
from ui.view.graphics_view import GraphicsView
from ui.view.component.graphics_block import GraphicsBlock
from ui.view.component.graphics_edge import GraphicsBezierEdge
from ui.view.component.graphics_socket import GraphicsSocket
import ui.view.styling.dimension as dim
from ui.view.dummy_types import SocketType, PropertyBlock, QueryBlock, WitnessBlock

CACHE_LOCATION = os.path.join(os.path.dirname(__file__), "../temp/cache")


# Minimal verification scene and components (copied from test_node_editor.py)
class VerificationScene:
    def __init__(self):
        self.blocks = {}
        self.edges = {}
        self.counter = 0
    
    def add_property_block(self, property_type, formula, x=0, y=0):
        block = PropertyBlock(property_type, formula, f"Property ({property_type})")
        return self._setup_block(block, x, y, [SocketType.OUTPUT])
    
    def add_query_block(self, query_id, query_text, is_negated=False, x=0, y=0):
        title = f"{'¬' if is_negated else ''}Query {query_id}"
        block = QueryBlock(query_id, query_text, is_negated, title)
        return self._setup_block(block, x, y, [SocketType.INPUT, SocketType.OUTPUT])
    
    def add_witness_block(self, is_counterexample=False, witness_data=None, x=0, y=0):
        title = "Counter Example" if is_counterexample else "Witness"
        block = WitnessBlock(is_counterexample, witness_data, title)
        return self._setup_block(block, x, y, [SocketType.INPUT])
    
    def _setup_block(self, block, x, y, socket_types):
        block.id = self.counter
        block.x, block.y = x, y
        block.scene_ref = self
        block.attr_dict = {'parameters': {}}
        block.sockets = [VerificationSocket(st, block) for st in socket_types]
        block.has_parameters = lambda: False
        
        def update_edges():
            if block.scene_ref:
                for edge in block.scene_ref.edges.values():
                    if (edge.start_skt.block_ref == block or edge.end_skt.block_ref == block):
                        edge.update_graphics_position()
        
        block.update_edges = update_edges
        self.blocks[self.counter] = block
        self.counter += 1
        return block
    
    def connect_blocks(self, source_block, target_block):
        source_socket = next((s for s in source_block.sockets if s.s_type == SocketType.OUTPUT), None)
        target_socket = next((s for s in target_block.sockets if s.s_type == SocketType.INPUT), None)
        
        if source_socket and target_socket:
            edge = VerificationEdge(source_socket, target_socket)
            self.edges[edge.id] = edge
            return edge
        return None


class VerificationSocket:
    def __init__(self, socket_type, block):
        self.s_type = socket_type
        self.block_ref = block
        self.graphics_socket = None


class VerificationEdge:
    def __init__(self, start_socket, end_socket):
        self.id = id(self)
        self.start_skt = start_socket
        self.end_skt = end_socket
        self.view_dim = True
        self.graphics_edge = None
    
    def update_graphics_position(self):
        if self.graphics_edge and self.start_skt.block_ref.graphics_block and self.end_skt.block_ref.graphics_block:
            start_pos = self.start_skt.block_ref.graphics_block.pos()
            end_pos = self.end_skt.block_ref.graphics_block.pos()
            
            start_x = start_pos.x() + self.start_skt.block_ref.graphics_block.width - dim.SOCKET_RADIUS
            start_y = start_pos.y() + self.start_skt.block_ref.graphics_block.height // 2
            end_x = end_pos.x() + dim.SOCKET_RADIUS
            end_y = end_pos.y() + self.end_skt.block_ref.graphics_block.height // 2
            
            self.graphics_edge.src_pos = [start_x, start_y]
            self.graphics_edge.dest_pos = [end_x, end_y]
            self.graphics_edge.update_path()


class HeirarchicalOutput(QWidget):
    """Verification node editor widget replacing the tree widget"""
    
    def __init__(self, parent=None, cache_location=CACHE_LOCATION):
        super().__init__(parent)
        self.cache_location = Path(cache_location)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Setup node editor
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.scene = VerificationScene()
        self.graphics_scene = GraphicsScene(self.scene)
        self.graphics_view = GraphicsView(self.graphics_scene)
        layout.addWidget(self.graphics_view)
        
        self.create_verification_workflow()
    
    def clear(self):
        """Clear and recreate the verification workflow"""
        self.scene = VerificationScene()
        self.graphics_scene = GraphicsScene(self.scene)
        self.graphics_view.setScene(self.graphics_scene)
        self.create_verification_workflow()
    
    def create_verification_workflow(self):
        """Create example verification workflow"""
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
        
        # Create graphics
        for block in [property1, query1, query2, property2, query3, counterexample, witness]:
            self._create_graphics_block(block)
        
        # Connect blocks
        for source, target in [(property1, query1), (property1, query2), (query1, counterexample), 
                              (property2, query3), (query3, witness)]:
            self._connect_blocks(source, target)
    
    def _create_graphics_block(self, block):
        graphics_block = GraphicsBlock(block)
        graphics_block.setPos(block.x, block.y)
        block.graphics_block = graphics_block
        self.graphics_scene.addItem(graphics_block)
        
        for socket in block.sockets:
            graphics_socket = GraphicsSocket(socket)
            if socket.s_type == SocketType.INPUT:
                socket_x = dim.SOCKET_RADIUS
            else:
                socket_x = graphics_block.width - dim.SOCKET_RADIUS
            socket_y = graphics_block.height // 2
            graphics_socket.setPos(socket_x, socket_y)
            graphics_socket.setParentItem(graphics_block)
            socket.graphics_socket = graphics_socket
    
    def _connect_blocks(self, source_block, target_block):
        edge = self.scene.connect_blocks(source_block, target_block)
        if edge:
            graphics_edge = GraphicsBezierEdge(edge)
            
            start_pos = source_block.graphics_block.pos()
            end_pos = target_block.graphics_block.pos()
            graphics_edge.src_pos = [
                start_pos.x() + source_block.graphics_block.width - dim.SOCKET_RADIUS,
                start_pos.y() + source_block.graphics_block.height // 2
            ]
            graphics_edge.dest_pos = [
                end_pos.x() + dim.SOCKET_RADIUS,
                end_pos.y() + target_block.graphics_block.height // 2
            ]
            graphics_edge.update_path()
            
            self.graphics_scene.addItem(graphics_edge)
            edge.graphics_edge = graphics_edge

			
		