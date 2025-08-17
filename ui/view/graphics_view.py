"""
Module graphics_view.py

This module contains the GraphicsView class for rendering graphics objects in the viewport

Original author: Andrea Gimelli, Giacomo Rosato, Stefano Demarchi

"""

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QPainter, QMouseEvent
from PyQt6 import QtGui
from PyQt6.QtWidgets import QGraphicsView

import ui.view.styling.dimension as dim
from .graphics_scene import GraphicsScene


class GraphicsView(QGraphicsView):
    """
    This class visualizes the contents of the GraphicsScene in a scrollable viewport

    """

    def __init__(self, gr_scene: 'GraphicsScene', parent=None):
        super().__init__(parent)

        # Reference to the graphics scene
        self.gr_scene_ref = gr_scene
        self.setScene(self.gr_scene_ref)
        self.zoom = dim.ZOOM

        self.init_ui()

    def init_ui(self):
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing |
                            QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Enable scrollbars
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    
    def zoom_in(self):
        self.zoom += dim.ZOOM_STEP
        self.set_scale(dim.ZOOM_IN_FACTOR)

    def zoom_out(self):
        self.zoom -= dim.ZOOM_STEP
        self.set_scale(1 / dim.ZOOM_IN_FACTOR)

    def set_scale(self, factor: float):
        clipped = False
        if self.zoom < dim.ZOOM_RANGE[0]:
            self.zoom = dim.ZOOM_RANGE[0]
            clipped = True
        if self.zoom > dim.ZOOM_RANGE[1]:
            self.zoom = dim.ZOOM_RANGE[1]
            clipped = True

        # Set scene scale
        if not clipped:
            self.scale(factor, factor)

    def delete_items(self, sel_ids: list):
        for block_id in sel_ids:
            block = self.gr_scene_ref.scene_ref.blocks[block_id]
            self.gr_scene_ref.scene_ref.remove_block(block, logic=True)

    def mousePressEvent(self, event: 'QtGui.QMouseEvent') -> None:
        """
        Differentiate the mouse buttons click

        """

        if event.button() == Qt.MouseButton.MiddleButton:
            self.middle_mouse_click(event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: 'QtGui.QMouseEvent') -> None:
        """
        Differentiate the mouse buttons click

        """

        if event.button() == Qt.MouseButton.MiddleButton:
            self.middle_mouse_release(event)
        else:
            super().mouseReleaseEvent(event)

    def middle_mouse_click(self, event: 'QtGui.QMouseEvent') -> None:
        """
        Drag the view

        """

        release_event = QMouseEvent(QEvent.Type.MouseButtonRelease, event.position(), event.globalPosition(),
                                    Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, event.modifiers())
        super().mouseReleaseEvent(release_event)

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        # Fake press event
        fake_event = QMouseEvent(event.type(), event.position(), event.globalPosition(),
                                 Qt.MouseButton.LeftButton, event.buttons() | Qt.MouseButton.LeftButton,
                                 event.modifiers())
        super().mousePressEvent(fake_event)

    def middle_mouse_release(self, event: 'QtGui.QMouseEvent') -> None:
        fake_event = QMouseEvent(event.type(), event.position(), event.globalPosition(),
                                 Qt.MouseButton.LeftButton, event.buttons() & ~Qt.MouseButton.LeftButton,
                                 event.modifiers())
        super().mouseReleaseEvent(fake_event)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

    def wheelEvent(self, event: 'QtGui.QWheelEvent') -> None:
        """
        Override the event to enable zoom

        """

        factor = 1 / dim.ZOOM_IN_FACTOR

        if event.angleDelta().y() > 0:
            factor = dim.ZOOM_IN_FACTOR
            self.zoom += dim.ZOOM_STEP
        else:
            self.zoom -= dim.ZOOM_STEP

        self.set_scale(factor)
