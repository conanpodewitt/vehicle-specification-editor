"""
Module graphics_view.py

This module contains the GraphicsView class for rendering graphics objects in the viewport

Original author: Andrea Gimelli, Giacomo Rosato, Stefano Demarchi

"""

from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QPropertyAnimation, QObject, QEvent
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
        self.h_scrollbar = self.horizontalScrollBar()
        self.v_scrollbar = self.verticalScrollBar()

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

    def scroll_item_into_view(self, item, margin_scene=20.0):
        """
        Ensure `item` is fully visible in `view`.
        - Pans horizontally if the item is out of view horizontally.
        - Pans vertically if the item is out of view vertically.
        - `margin_scene` is in scene units (zoom-independent).
        - If `animate=True`, does a short smooth pan (assumes scale-only transform).
        """
        def _do():
            # Item bounds in scene coords
            item_rect: QRectF = item.mapToScene(item.boundingRect()).boundingRect()
            view_rect: QRectF = self.mapToScene(self.viewport().rect()).boundingRect()

            dx = 0.0
            dy = 0.0

            # Horizontal adjustment
            if item_rect.left() - margin_scene < view_rect.left():
                dx = (item_rect.left() - margin_scene) - view_rect.left()
            elif item_rect.right() + margin_scene > view_rect.right():
                dx = (item_rect.right() + margin_scene) - view_rect.right()

            # Vertical adjustment
            if item_rect.top() - margin_scene < view_rect.top():
                dy = (item_rect.top() - margin_scene) - view_rect.top()
            elif item_rect.bottom() + margin_scene > view_rect.bottom():
                dy = (item_rect.bottom() + margin_scene) - view_rect.bottom()

            if dx == 0.0 and dy == 0.0:
                return

            # Compute target viewport rect
            new_left   = view_rect.left() + dx
            new_top    = view_rect.top() + dy
            new_width  = view_rect.width()
            new_height = view_rect.height()

            # Clamp to scene
            scene_rect = self.sceneRect()
            if scene_rect.isValid():
                new_left = max(scene_rect.left(), min(new_left, scene_rect.right() - new_width))
                new_top  = max(scene_rect.top(),  min(new_top,  scene_rect.bottom() - new_height))

            # Convert to a target center and pan
            target_center = QPointF(new_left + new_width / 2.0, new_top + new_height / 2.0)
            self.centerOn(target_center)

        QTimer.singleShot(0, _do)    
