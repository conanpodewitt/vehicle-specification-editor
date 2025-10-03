"""
Module graphics_view.py

This module contains the GraphicsView class for rendering graphics objects in the viewport

Original author: Andrea Gimelli, Giacomo Rosato, Stefano Demarchi

"""

from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QPropertyAnimation, QObject
from PyQt6.QtGui import QPainter
from PyQt6 import QtGui
from PyQt6.QtWidgets import QGraphicsView

import vehicle_gui.query_view.styling.dimension as dim
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

        # Right mouse drag state
        self.right_mouse_dragging = False
        self.last_mouse_pos = None

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
        
        # Ensure the view can receive mouse events
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)  # Disable right-click context menu

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
        Handle mouse press events, including right mouse button for dragging
        """

        if event.button() == Qt.MouseButton.RightButton:
            self.setFocus()
            self.right_mouse_dragging = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: 'QtGui.QMouseEvent') -> None:
        """
        Handle mouse release events
        """

        if event.button() == Qt.MouseButton.RightButton:
            self.right_mouse_dragging = False
            self.last_mouse_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: 'QtGui.QMouseEvent') -> None:
        """
        Handle mouse move events, including right mouse dragging
        """

        if self.right_mouse_dragging and self.last_mouse_pos is not None:
            # Calculate the delta movement
            delta = event.position() - self.last_mouse_pos
            
            # Scroll the view by the delta amount
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
            
            # Update the last position
            self.last_mouse_pos = event.position()
            event.accept()
        else:
            super().mouseMoveEvent(event)

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
            # Check if item is still valid before accessing it
            try:
                if not item or not hasattr(item, 'mapToScene') or not hasattr(item, 'boundingRect'):
                    return
                
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
            # Ignore if item has been deleted
            except (RuntimeError, AttributeError) as e:
                return

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
