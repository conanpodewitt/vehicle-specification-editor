"""
Module dimension.py

This module contains the dimension references for the graphics

Original author: Andrea Gimelli, Giacomo Rosato, Stefano Demarchi

"""

# Scene
# ------------

# Minimum scene dimensions
INITIAL_SCENE_WIDTH = 800
INITIAL_SCENE_HEIGHT = 600
SCENE_PADDING = 200

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

# Width values
BLOCK_BASE_WIDTH = 120

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

# Font
FONT_FAMILY = "Arial"
FONT_SIZE = 8
FONT_BOLD = True

# Sockets
# ------------

# Parameters
SOCKET_RADIUS = 2
SOCKET_OUTLINE = 1

# Verification Workflow Layout
# ------------

# Hierarchical tree layout spacing
VERTICAL_SPACING = 100      # Vertical spacing between blocks
HORIZONTAL_SPACING = 50    # Horizontal spacing between blocks
PROPERTY_SPACING_Y = 300    # Vertical spacing between properties
PROPERTY_X = -400           # X position for properties

# Starting position for workflow
WORKFLOW_START_Y = -300     # Starting Y position for first property
