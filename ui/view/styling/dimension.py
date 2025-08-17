"""
Module dimension.py

This module contains the dimension references for the graphics

Original author: Andrea Gimelli, Giacomo Rosato, Stefano Demarchi

"""

# Scene
# ------------

# Width and height
SCENE_WIDTH = 12800
SCENE_HEIGHT = 6400

# Window size
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768

# Other dimensions
GRID_SIZE = 20
GRID_SQUARE = 5
ABS_BLOCK_DISTANCE = 100

# Graphics View
# ------------

# Zoom parameters
ZOOM = 10
ZOOM_IN_FACTOR = 1.25
ZOOM_STEP = 1
ZOOM_RANGE = [0, 10]

# Blocks
# ------------

# Width values - All blocks now have the same width for consistency
BLOCK_BASE_WIDTH = 180
BLOCK_PARAM_WIDTH = 180
BLOCK_PROPERTY_WIDTH = 180

# Height values
BLOCK_BASE_HEIGHT = 35
TITLE_HEIGHT = 25

# Other dimensions
EDGE_ROUNDNESS = 10
EDGE_CP_ROUNDNESS = 100
TITLE_PAD = 10.0
SOCKET_SPACING = 22

NEXT_BLOCK_DISTANCE = 200
SCENE_BORDER = 4600

# Sockets
# ------------

# Parameters
SOCKET_RADIUS = 2  # Reduced from 6 to make it like a small dot
SOCKET_OUTLINE = 1  # Reduced outline to match smaller socket

# Verification Workflow Layout
# ------------

# Hierarchical tree layout spacing
PROPERTY_SPACING_Y = 600    # Vertical spacing between properties (changed from horizontal)
PROPERTY_X = -400           # X position for all properties (fixed horizontal position)
QUERY_Y_OFFSET = 200        # Vertical offset for queries below properties
WITNESS_Y_OFFSET = 200      # Vertical offset for witnesses below queries
QUERY_SPACING = 200         # Horizontal spacing between queries under same property (increased from 180)

# Starting position for workflow
WORKFLOW_START_Y = -300     # Starting Y position for first property
