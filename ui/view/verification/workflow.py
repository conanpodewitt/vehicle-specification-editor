"""
Module verification_workflow.py

This module contains the high-level verification workflow generator
that creates verification graphs from data.

"""

from .blocks import PropertyBlock, WitnessBlock, QueryBlock, PropertyQuantifier
from ..base_types import Scene, Socket
from ..graphics_view import GraphicsView
from ..component.block_graphics import BlockGraphics
from ..component.socket_graphics import SocketGraphics
from ..component.edge_graphics import BezierEdgeGraphics
from ..base_types import SocketType
import ui.view.styling.dimension as dim


class VerificationWorkflow:
    """High-level manager for verification workflows with hierarchical tree layout"""
    
    def __init__(self, graphics_scene, graphics_view):
        self.graphics_scene = graphics_scene
        self.graphics_view = graphics_view
        self.scene = Scene()

        # Properties  
        self.property_counter = 0
        self.properties = []  
        self.property_info = {}    
    
    def add_property(self, property_type, title=None):
        """Add a property block with vertical hierarchical positioning"""
        if title is None:
            title = f"Property"
        
        # Properties are positioned vertically, queries spread horizontally under each
        property_x = dim.PROPERTY_X
        property_y = dim.WORKFLOW_START_Y + (self.property_counter * dim.PROPERTY_SPACING_Y)
        
        # Create the property at the calculated position
        property_block = PropertyBlock(property_type, title)
        self._setup_block(property_block, property_x, property_y, [SocketType.OUTPUT])
        self.property_info[property_block.title] = {
            'queries': [],
            'witnesses': []
        }
        self.properties.append(property_block)
        self.property_counter += 1

        self._create_block_graphics(property_block)
        self.graphics_view.scroll_item_into_view(property_block.graphics)
        return property_block
    
    def add_query(self, property_block, is_negated=False, title=None):
        """Add a query block connected to a property with hierarchical positioning"""
        if title is None:
            title = f"{'¬' if is_negated else ''}Query"

        # Get the property's query tracking info
        prop_info = self.property_info[property_block.title]
        current_queries = prop_info['queries']

        # Set query (X, Y) coordinates
        query_y = property_block.y + dim.VERTICAL_SPACING
        if len(current_queries) == 0:
            query_x = dim.PROPERTY_X
        else:
            query_x = current_queries[-1].x + dim.HORIZONTAL_SPACING

        # Create the query block
        query_block = QueryBlock(property_block, title, is_negated)
        self._setup_block(query_block, query_x, query_y, [SocketType.INPUT, SocketType.OUTPUT])
        prop_info['queries'].append(query_block)
        property_block.queries.append(query_block)
        
        # Create graphics and connection
        self._create_block_graphics(query_block)
        self._create_edge_graphics(property_block, query_block)
        query_block.update_edges()

        # Update scrollbar
        self.graphics_view.scroll_item_into_view(query_block.graphics)
        return query_block
    
    def add_witness(self, query_block, title=None):
        """Add a witness block connected to a query with hierarchical positioning"""
        if title is None:
            title = "Counter Example" if query_block.is_negated else "Witness"
        
        # Position witness directly below the query (hierarchical tree structure)
        witness_x = query_block.x
        witness_y = query_block.y + dim.VERTICAL_SPACING
        
        # Create the witness block
        witness_block = WitnessBlock(query_block, title)
        self._setup_block(witness_block, witness_x, witness_y, [SocketType.INPUT])
        prop_info = self.property_info[query_block.property_ref.title]
        prop_info['witnesses'].append(witness_block)
        
        # Create graphics and connection
        self._create_block_graphics(witness_block)
        self._create_edge_graphics(query_block, witness_block)
        witness_block.update_edges()
        query_block.update_edges()

        self.graphics_view.scroll_item_into_view(witness_block.graphics)
        return witness_block
    
    def clear_workflow(self):
        """Clear the current workflow and reset positions"""
        self.graphics_scene.clear()
        self.scene = Scene()
        self.property_counter = 0
        self.properties = []
        self.property_info = {}
    
    def get_workflow_bounds(self):
        """Get the bounding rectangle of the current workflow"""
        if not self.scene.blocks:
            return (0, 0, 0, 0)
        
        min_x = min(block.x for block in self.scene.blocks.values())
        max_x = max(block.x + dim.BLOCK_BASE_WIDTH for block in self.scene.blocks.values())
        min_y = min(block.y for block in self.scene.blocks.values())
        max_y = max(block.y + dim.BLOCK_BASE_HEIGHT for block in self.scene.blocks.values())
        
        return (min_x, min_y, max_x - min_x, max_y - min_y)
    
    def create_example_workflow(self):
        """Create an example verification workflow using hierarchical tree layout"""
        # Clear any existing workflow
        self.clear_workflow()
        
        # Property 1: For-all property with two queries and a counterexample
        property1 = self.add_property(PropertyQuantifier.FOR_ALL)
        query1 = self.add_query(property1, True)
        _ = self.add_query(property1, True)
        _ = self.add_witness(query1)
        
        # Property 2: Exists property with one query and a witness
        property2 = self.add_property(PropertyQuantifier.EXISTS)
        query3 = self.add_query(property2, False)
        _ = self.add_witness(query3)
        
        # Property 3: Another for-all property to demonstrate the hierarchical structure
        property3 = self.add_property(PropertyQuantifier.FOR_ALL)
        query4 = self.add_query(property3, True)
        _ = self.add_query(property3, True)
        query6 = self.add_query(property3, True)
        _ = self.add_witness(query4)
        _ = self.add_witness(query6)

        # Force update all edge positions after workflow creation is complete
        self._update_edge_positions()
        
        return [property1, property2, property3]
    
    def _create_block_graphics(self, block):
        """Create graphics for a block and add to scene"""
        graphics = BlockGraphics(block)
        self.graphics_scene.addItem(graphics)
        graphics.setPos(block.x, block.y)
        self._create_socket_graphics(block, graphics)
        block.graphics = graphics
        return graphics
        
    def _create_socket_graphics(self, block, graphics):
        """Create socket graphics for a block with hierarchical positioning"""
        # Create input socket graphics (top center of block)
        for socket in block.inputs:
            socket_graphics = SocketGraphics(socket)
            socket_graphics.setParentItem(graphics)
            # Position at top center of block
            socket_x = graphics.width / 2 - dim.SOCKET_RADIUS
            socket_y = -dim.SOCKET_RADIUS
            socket_graphics.setPos(socket_x, socket_y)
            socket.graphics = socket_graphics
            
        # Create output socket graphics (bottom center of block)
        for socket in block.outputs:
            socket_graphics = SocketGraphics(socket)
            socket_graphics.setParentItem(graphics)
            # Position at bottom center of block
            socket_x = graphics.width / 2 - dim.SOCKET_RADIUS
            socket_y = graphics.height - dim.SOCKET_RADIUS
            socket_graphics.setPos(socket_x, socket_y)
            socket.graphics = socket_graphics
    
    def _create_edge_graphics(self, source_block, target_block):
        """Create an edge connection between two blocks"""
        # Create the edge in the model using the scene's method
        edge = self.scene.connect_blocks(source_block, target_block)
        
        if edge:
            edge_graphics = BezierEdgeGraphics(edge)
            self.graphics_scene.addItem(edge_graphics)
            edge.graphics = edge_graphics
            edge.update_graphics_position()
        
        return edge
    
    def _update_edge_positions(self):
        """Update all edge positions after workflow creation is complete"""
        # Get all edges from the scene
        for edge in self.scene.edges.values():
            if hasattr(edge, 'update_graphics_position'):
                edge.update_graphics_position()
        
        # Force graphics updates for all blocks and edges
        for item in self.graphics_scene.items():
            item.update()
        
        # Force a complete graphics scene update
        self.graphics_scene.update()
        self.graphics_scene.invalidate()

    def _setup_block(self, block, x, y, socket_types):
        """Setup a block with position, sockets, and scene reference"""
        block.x, block.y = x, y
        block.sockets = [Socket(st, block) for st in socket_types]
        
        # Setup input/output socket lists
        block.inputs = [s for s in block.sockets if s.s_type == SocketType.INPUT]
        block.outputs = [s for s in block.sockets if s.s_type == SocketType.OUTPUT]
        return self.scene.add_block(block)
