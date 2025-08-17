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
    """High-level generator for verification workflows with hierarchical tree layout"""
    
    def __init__(self, graphics_scene, graphics_view=None):
        self.scene = VerificationScene()
        self.graphics_scene = graphics_scene
        self.graphics_view = graphics_view  # Reference to graphics view for auto-scrolling
        
        # Starting position and counter for layout
        self.property_counter = 0       
        
        # Track positions for hierarchical layout
        self.properties = []  #
        self.property_query_positions = {}    
    
    def add_property(self, property_type, formula, title=None):
        """Add a property block with vertical hierarchical positioning"""
        if title is None:
            title = f"Property ({property_type})"
        
        # Properties are positioned vertically, queries spread horizontally under each
        property_x = dim.PROPERTY_X  # Fixed X position for all properties
        property_y = dim.WORKFLOW_START_Y + (self.property_counter * dim.PROPERTY_SPACING_Y)
        
        # Create the property at the calculated position
        property_block = self.scene.add_property_block(
            property_type, formula, property_x, property_y
        )
        property_block.title = title
        
        # Initialize query tracking for this property  
        self.property_query_positions[property_block.id] = {
            'property_x': property_x,  # Store property position for centering queries
            'query_count': 0,
            'queries': [],
            'witnesses': []
        }
        
        # Track properties and increment counter
        self.properties.append(property_block)
        self.property_counter += 1
        
        # Create graphics
        self._create_graphics_block(property_block)
        
        return property_block
    
    def add_query(self, property_block, query_id, query_text, is_negated=False, title=None):
        """Add a query block connected to a property with hierarchical positioning"""
        if title is None:
            title = f"{'¬' if is_negated else ''}Query {query_id}"
        
        # Get the property's query tracking info
        prop_info = self.property_query_positions[property_block.id]
        current_queries = prop_info['queries']
        center_x = prop_info['property_x']
        
        # New approach: Don't reposition existing queries, just add to the right
        if len(current_queries) == 0:
            # First query: position under the property
            query_x = center_x 
        else:
            # Subsequent queries: position to the right of the rightmost existing query
            rightmost_query = max(current_queries, key=lambda q: q.x)
            query_x = rightmost_query.x + dim.QUERY_SPACING
        
        # Queries are positioned below their property
        query_y = property_block.y + dim.QUERY_Y_OFFSET
        
        # Create the query block
        query_block = self.scene.add_query_block(
            query_id, query_text, is_negated, query_x, query_y
        )
        query_block.title = title
        query_block.property_ref = property_block
        
        # Update tracking
        prop_info['query_count'] += 1
        prop_info['queries'].append(query_block)
        property_block.queries.append(query_block)
        
        # Create graphics and connection
        self._create_graphics_block(query_block)
        self._connect_blocks(property_block, query_block)
        
        # Since we're not repositioning existing queries, we only need to update edges for the new query
        if hasattr(query_block, 'update_edges'):
            query_block.update_edges()
        
        return query_block
    
    def add_witness(self, query_block, is_counterexample=False, witness_data=None, title=None):
        """Add a witness block connected to a query with hierarchical positioning"""
        if title is None:
            title = "Counter Example" if is_counterexample else "Witness"
        
        # Position witness directly below the query (hierarchical tree structure)
        witness_x = query_block.x
        witness_y = query_block.y + dim.WITNESS_Y_OFFSET
        
        # Create the witness block
        witness_block = self.scene.add_witness_block(
            is_counterexample, witness_data, witness_x, witness_y
        )
        witness_block.title = title
        witness_block.query_ref = query_block
        
        # Update tracking
        prop_info = self.property_query_positions[query_block.property_ref.id]
        prop_info['witnesses'].append(witness_block)
        
        # Create graphics and connection
        self._create_graphics_block(witness_block)
        self._connect_blocks(query_block, witness_block)
        
        # Force graphics update to ensure witness is positioned correctly
        if hasattr(witness_block, 'graphics') and witness_block.graphics:
            witness_block.graphics.setPos(witness_x, witness_y)
            witness_block.graphics.update()
        
        # Update connected edges after positioning
        if hasattr(witness_block, 'update_edges'):
            witness_block.update_edges()
        if hasattr(query_block, 'update_edges'):
            query_block.update_edges()
        
        return witness_block
    
    def clear_workflow(self):
        """Clear the current workflow and reset positions"""
        self.graphics_scene.clear()
        self.scene = VerificationScene()
        self.property_counter = 0
        self.properties = []
        self.property_query_positions = {}
    
    def get_workflow_bounds(self):
        """Get the bounding rectangle of the current workflow"""
        if not self.scene.blocks:
            return (0, 0, 0, 0)
        
        import ui.view.styling.dimension as dim
        
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
        property1 = self.add_property("for_all", "∀x (speed(x) ≤ max_speed)", "Speed Limit Property")
        query1 = self.add_query(property1, 1, "speed(x1) > max_speed", True, "¬Query 1")
        _ = self.add_query(property1, 2, "speed(x2) > max_speed", True, "¬Query 2")
        _ = self.add_witness(query1, True, {"speed": 85}, "Counter Example")
        
        # Property 2: Exists property with one query and a witness
        property2 = self.add_property("exists", "∃x (brake_response(x) < 0.5s)", "Brake Response Property")
        query3 = self.add_query(property2, 3, "brake_response(x3) < 0.5s", False, "Query 3")
        _ = self.add_witness(query3, False, {"brake_response": 0.3}, "Witness")
        
        # Property 3: Another for-all property to demonstrate the hierarchical structure
        property3 = self.add_property("for_all", "∀x (fuel_efficiency(x) > 15)", "Fuel Efficiency Property")
        query4 = self.add_query(property3, 4, "fuel_efficiency(x4) <= 15", True, "¬Query 4")
        _ = self.add_query(property3, 5, "fuel_efficiency(x5) <= 15", True, "¬Query 5")
        query6 = self.add_query(property3, 6, "fuel_efficiency(x6) <= 15", True, "¬Query 6")
        _ = self.add_witness(query4, False, {"fuel_efficiency": 18}, "Good Efficiency")
        _ = self.add_witness(query6, True, {"fuel_efficiency": 12}, "Poor Efficiency")
        
        # Force update all edge positions after workflow creation is complete
        self._update_all_edge_positions()
        
        return [property1, property2, property3]
    
    def create_workflow_from_data(self, verification_data):
        """Create a verification workflow from structured data"""
        # This method would parse real verification data
        # For now, it creates the example workflow
        self.create_example_workflow()
    
    def _create_graphics_block(self, block):
        """Create graphics for a block and add to scene"""
        graphics = BlockGraphics(block)  # Pass the block object
        self.graphics_scene.addItem(graphics)
        
        # Position the graphics
        graphics.setPos(block.x, block.y)
        # Create input/output socket graphics
        self._create_socket_graphics(block, graphics)
        # Store reference for edge creation and block updates
        block.graphics = graphics
        
        # TODO: Add auto-scrolling logic here
        return graphics
        
    def _create_socket_graphics(self, block, graphics):
        """Create socket graphics for a block with hierarchical positioning"""
        from ..component.socket_graphics import SocketGraphics
        import ui.view.styling.dimension as dim
        
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
    
    def _connect_blocks(self, source_block, target_block):
        """Create an edge connection between two blocks"""
        # Create the edge in the model using the scene's method
        edge = self.scene.connect_blocks(source_block, target_block)
        
        if edge:
            # Create the graphics using BezierEdgeGraphics
            edge_graphics = BezierEdgeGraphics(edge)
            
            self.graphics_scene.addItem(edge_graphics)
            edge.graphics = edge_graphics
            
            # Use the edge's own positioning logic for consistent vertical anchors
            edge.update_graphics_position()
        
        return edge
    
    def _update_all_edge_positions(self):
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
