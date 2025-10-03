"""
Module graphics_scene.py

This module contains the GraphicsScene class for handling graphics objects representation

Original author: Andrea Gimelli, Giacomo Rosato, Stefano Demarchi

"""

import math

from PyQt6.QtCore import QLine, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtWidgets import QGraphicsScene

import vehicle_gui.query_view.styling.dimension as dim
import vehicle_gui.query_view.styling.palette as palette


class GraphicsScene(QGraphicsScene):
    """
    This class manages the graphics scene, i.e., the handler of graphical objects. Objects in the
    GraphicsScene can be rendered in the viewport provided by the GraphicsView

    Attributes
    ----------

    Methods
    ----------

    """

    # The following signals are intercepted by QGraphicsScene.selectedItems()
    itemSelected = pyqtSignal()
    itemsDeselected = pyqtSignal()

    def __init__(self, scene=None, parent=None):
        super().__init__(parent)

        # Reference to the scene (optional)
        self.scene_ref = scene

        # Start with a smaller initial scene size
        self.min_scene_width = dim.INITIAL_SCENE_WIDTH
        self.min_scene_height = dim.INITIAL_SCENE_HEIGHT
        self.padding = dim.SCENE_PADDING 
        
        # Set initial smaller scene rectangle
        self.setSceneRect(-self.min_scene_width // 2, -self.min_scene_height // 2, 
                         self.min_scene_width, self.min_scene_height)

        self._color_background = QColor(palette.BACKGROUND_GREY)
        self._color_light = QColor(palette.BACKGROUND_LIGHT_LINE_GREY)
        self._color_dark = QColor(palette.BACKGROUND_DARK_LINE_GREY)

        # Pen settings
        self._pen_light = QPen(self._color_light)
        self._pen_light.setWidth(1)
        self._pen_dark = QPen(self._color_dark)
        self._pen_dark.setWidth(2)

        self.setBackgroundBrush(self._color_background)
        self._size_adjustment_pending = False  # Flag to track size adjustment state

    def auto_adjust_scene_size(self):
        """Automatically adjust scene size to fit all items with padding"""
        if not self.items():
            # No items, keep minimum size
            self.setSceneRect(-self.min_scene_width // 2, -self.min_scene_height // 2, 
                             self.min_scene_width, self.min_scene_height)
            return

        # Calculate the bounding rect of all items
        items_rect = self.itemsBoundingRect()
        
        # Add padding around the content
        content_left = items_rect.left() - self.padding
        content_top = items_rect.top() - self.padding
        content_right = items_rect.right() + self.padding
        content_bottom = items_rect.bottom() + self.padding
        
        # Calculate required dimensions
        required_width = content_right - content_left
        required_height = content_bottom - content_top
        
        # Ensure minimum size
        scene_width = max(required_width, self.min_scene_width)
        scene_height = max(required_height, self.min_scene_height)
        
        # Center the scene around the content
        center_x = (content_left + content_right) / 2
        center_y = (content_top + content_bottom) / 2
        
        # Set new scene rect centered on content
        new_left = center_x - scene_width / 2
        new_top = center_y - scene_height / 2
        
        self.setSceneRect(new_left, new_top, scene_width, scene_height)

    def addItem(self, item):
        """Override addItem to auto-adjust scene size"""
        super().addItem(item)
        # Defer the size adjustment to avoid performance issues during bulk additions
        if not self._size_adjustment_pending:
            self._size_adjustment_pending = True
            QTimer.singleShot(0, self._perform_size_adjustment)     # Batch size adjustments

    def removeItem(self, item):
        """Override removeItem to auto-adjust scene size"""
        super().removeItem(item)
        # Defer the size adjustment
        if not self._size_adjustment_pending:
            self._size_adjustment_pending = True
            QTimer.singleShot(0, self._perform_size_adjustment)

    def _perform_size_adjustment(self):
        """Perform the actual size adjustment (called via QTimer)"""
        if self._size_adjustment_pending:
            self._size_adjustment_pending = False
        self.auto_adjust_scene_size()

    def clear(self):
        """Override clear to reset scene size"""
        super().clear()
        # Reset to minimum size when clearing
        self.setSceneRect(-self.min_scene_width // 2, -self.min_scene_height // 2, 
                         self.min_scene_width, self.min_scene_height)

    def dragMoveEvent(self, event):
        """
        Necessary override for enabling events

        """

        pass

    # Event handlers to ignore right-click events and allow propagation to view

    def mousePressEvent(self, event):
        """Handle mouse press events in the scene"""
        # Don't consume right mouse events
        if event.button() == Qt.MouseButton.RightButton:
            event.ignore() 
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events in the scene"""
        # Don't consume right mouse events during dragging
        if event.buttons() & Qt.MouseButton.RightButton:
            event.ignore()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events in the scene"""
        # Don't consume right mouse events
        if event.button() == Qt.MouseButton.RightButton:
            event.ignore()
        else:
            super().mouseReleaseEvent(event)

    def drawBackground(self, painter, rect):
        """
        This method draws the background of the scene (setting the color and adding a grid)
        using the painter and a set of QPens

        Parameters
        ----------
        painter : QPainter
            QPainter performs low-level painting on widgets and other paint devices
        rect : QRectF
            A rectangle is normally expressed as a top-left corner and a size

        """

        super().drawBackground(painter, rect)

        # Here we create our grid
        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))
        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        first_left = left - (left % dim.GRID_SIZE)
        first_top = top - (top % dim.GRID_SIZE)

        # Compute all lines to be drawn
        lines_light, lines_dark = [], []  # position (x1, y1), (x2, y2)

        for x in range(first_left, right, dim.GRID_SIZE):
            if x % (dim.GRID_SIZE * dim.GRID_SQUARE) != 0:
                lines_light.append(QLine(x, top, x, bottom))
            else:
                lines_dark.append(QLine(x, top, x, bottom))

        for y in range(first_top, bottom, dim.GRID_SIZE):
            if y % (dim.GRID_SIZE * dim.GRID_SQUARE) != 0:
                lines_light.append(QLine(left, y, right, y))
            else:
                lines_dark.append(QLine(left, y, right, y))

        painter.setPen(self._pen_light)
        painter.drawLines(*lines_light)
        painter.setPen(self._pen_dark)
        painter.drawLines(*lines_dark)
