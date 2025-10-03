"""
Module verification_workflow.py

This module contains the high-level verification workflow generator
that creates verification graphs from data.

"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QColor, QBrush

from .blocks import PropertyBlock, WitnessBlock, QueryBlock, PropertyQuantifier, Status, AndBlock, OrBlock
from ..base_types import Scene, Socket
from ..graphics.graphics_view import GraphicsView
from ..graphics.block_graphics import BlockGraphics
from ..graphics.socket_graphics import SocketGraphics
from ..graphics.edge_graphics import BezierEdgeGraphics
from ..base_types import SocketType
import vehicle_gui.query_view.styling.dimension as dim


class VerificationWorkflow:
    """High-level manager for verification workflows with hierarchical tree layout"""
    
    def __init__(self, graphics_scene, graphics_view):
        self.graphics_scene = graphics_scene
        self.graphics_view = graphics_view
        self.scene = Scene()

        # Properties  
        self.property_counter = 0
        self.properties = []    
    
    def add_property(self, title=None):
        """Add a property block with vertical hierarchical positioning"""
        if title is None:
            title = f"Property"
        
        # Properties are positioned vertically, queries spread horizontally under each
        property_x = dim.PROPERTY_X
        property_y = dim.WORKFLOW_START_Y + (self.property_counter * dim.PROPERTY_SPACING_Y)
        
        # Create the property at the calculated position
        property_block = PropertyBlock(title)
        self._setup_block(property_block, property_x, property_y, [SocketType.OUTPUT])
        self.properties.append(property_block)
        self.property_counter += 1

        self._create_block_graphics(property_block)
        return property_block
    
    def add_query(self, id, parent_block, query_path, is_negated=False):
        """Add a query block connected to a property with hierarchical positioning"""
        # Set query Y coordinate (X will be set by centering logic)
        query_y = parent_block.y + dim.VERTICAL_SPACING

        query_block = QueryBlock(id, parent_block, query_path, is_negated)
        self._setup_block(query_block, 0, query_y, [SocketType.INPUT, SocketType.OUTPUT])  # Temporary X=0
        
        # Add to tracking structures
        parent_block.children.append(query_block)  # Use children attribute
        
        # Create graphics and connection
        self._create_block_graphics(query_block)
        self._create_edge_graphics(parent_block, query_block)

        # Position all children centered around the parent
        self._position_children_centered(parent_block)

        query_block.update_edges()
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
        
        # Create graphics and connection
        self._create_block_graphics(witness_block)
        self._create_edge_graphics(query_block, witness_block)
        witness_block.update_edges()
        query_block.update_edges()

        return witness_block
    
    def add_and(self, parent_block):
        """Add an AND block connected to a parent with hierarchical positioning"""
        # Position AND block below the parent
        and_y = parent_block.y + dim.VERTICAL_SPACING
        
        # Create the AND block with parent reference
        and_block = AndBlock(parent_block)
        self._setup_block(and_block, 0, and_y, [SocketType.INPUT, SocketType.OUTPUT])  # Temporary X=0
        
        # Add to parent's children
        parent_block.children.append(and_block)
        
        # Create graphics and connection
        self._create_block_graphics(and_block)
        self._create_edge_graphics(parent_block, and_block)
        
        # Position all children centered around the parent
        self._position_children_centered(parent_block)
        
        and_block.update_edges()
        return and_block
    
    def add_or(self, parent_block):
        """Add an OR block connected to a parent with hierarchical positioning"""
        # Position OR block below the parent
        or_y = parent_block.y + dim.VERTICAL_SPACING
        
        # Create the OR block with parent reference
        or_block = OrBlock(parent_block)
        self._setup_block(or_block, 0, or_y, [SocketType.INPUT, SocketType.OUTPUT])  # Temporary X=0
        
        # Add to parent's children
        parent_block.children.append(or_block)
        
        # Create graphics and connection
        self._create_block_graphics(or_block)
        self._create_edge_graphics(parent_block, or_block)
        
        # Position all children centered around the parent
        self._position_children_centered(parent_block)
        
        or_block.update_edges()
        return or_block
    
    def clear_workflow(self):
        """Clear the current workflow and reset positions"""
        self.graphics_scene.clear()
        self.scene = Scene()
        self.property_counter = 0
        self.properties = []
    
    def get_workflow_bounds(self):
        """Get the bounding rectangle of the current workflow"""
        if not self.scene.blocks:
            return (0, 0, 0, 0)
        
        min_x = min(block.x for block in self.scene.blocks.values())
        max_x = max(block.x + dim.BLOCK_BASE_WIDTH for block in self.scene.blocks.values())
        min_y = min(block.y for block in self.scene.blocks.values())
        max_y = max(block.y + dim.BLOCK_BASE_HEIGHT for block in self.scene.blocks.values())
        
        return (min_x, min_y, max_x - min_x, max_y - min_y)

    def update_status(self, query_block: QueryBlock, status: Status):
        """Update verification status of a query and its parent property, then repaint"""
        pass
    
    def _repaint_block(self, block):
        """Repaint a block's graphics to reflect updated verification status"""
        graphics = block.graphics
        color_scheme = block.get_color_scheme()
        graphics._pen_default = QPen(QColor(color_scheme[0]))
        graphics._pen_default.setWidth(2)
        graphics._pen_hovered = QPen(QColor(color_scheme[1]))
        graphics._pen_hovered.setWidth(2)
        graphics._pen_selected = QPen(QColor(color_scheme[2]))
        graphics._pen_selected.setWidth(3)
        graphics._pen_selected.setStyle(Qt.PenStyle.DotLine)
        graphics._brush_title = QBrush(QColor(color_scheme[3]))
        graphics._brush_background = QBrush(QColor(color_scheme[4]))
        graphics.update()

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

    def _position_children_centered(self, parent_block):
        """Position all children for a parent block centered around the parent's X position"""
        children = parent_block.children
        if not children:
            return
            
        # Calculate starting X position
        total_width = len(children) * dim.BLOCK_BASE_WIDTH + (len(children) - 1) * dim.HORIZONTAL_SPACING
        start_x = parent_block.x - (total_width - dim.BLOCK_BASE_WIDTH) // 2
        
        # Position each child
        for i, child in enumerate(children):
            child_x = start_x + i * (dim.BLOCK_BASE_WIDTH + dim.HORIZONTAL_SPACING)
            child.x = child_x
            if hasattr(child, 'graphics') and child.graphics:
                child.graphics.setPos(child.x, child.y)
                
        # Update edge graphics
        for child in children:
            if hasattr(child, 'graphics') and child.graphics:
                child.update_edges()
                
        # Recursively position children of children to maintain tree structure
        for child in children:
            if hasattr(child, 'children') and child.children:
                self._position_children_centered(child)

    def _setup_block(self, block, x, y, socket_types):
        """Setup a block with position, sockets, and scene reference"""
        block.x, block.y = x, y
        block.sockets = [Socket(st, block) for st in socket_types]
        
        # Setup input/output socket lists
        block.inputs = [s for s in block.sockets if s.s_type == SocketType.INPUT]
        block.outputs = [s for s in block.sockets if s.s_type == SocketType.OUTPUT]
        return self.scene.add_block(block)
