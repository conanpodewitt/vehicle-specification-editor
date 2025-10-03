"""
Module block_graphics.py

This module contains the graphics elements of Block objects for representing the high-level properties,
low-level queries, and witnesses in the verification output

This module was migrated from the network node editor in CoCoNet.

Original author: Andrea Gimelli, Giacomo Rosato, Stefano Demarchi

"""

from PyQt6 import QtCore
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QPen, QColor, QFont, QBrush, QPainterPath, QPainter
from PyQt6.QtWidgets import QGraphicsItem, QWidget, QGraphicsProxyWidget, QGraphicsTextItem, QVBoxLayout, QGridLayout, \
    QHBoxLayout, QMessageBox, QStyleOptionGraphicsItem, QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent

import vehicle_gui.query_view.styling.dimension as dim
import vehicle_gui.query_view.styling.palette as palette
from ..verification.blocks import QueryBlock
from ..base_types import Block


class BlockSignals(QObject):
    """Signal emitter for block events"""
    query_double_clicked = pyqtSignal(str, str)  # path, title


class BlockGraphics(QGraphicsItem):
    """Graphics representation of a Block domain model"""
    signals = BlockSignals()     
    
    def __init__(self, block: 'Block', parent=None):
        super().__init__(parent)
        # Reference to the block domain model
        self.block_ref = block

        # Hover flag
        self.hover = False

        # Content widget
        self.content = None
        self.width = dim.BLOCK_BASE_WIDTH
        self.height = dim.BLOCK_BASE_HEIGHT

        # Init graphics content
        self.title_item = QGraphicsTextItem(self)
        self.graphics_content = QGraphicsProxyWidget(self)
        self.init_graphics_content()

        # Style parameters
        self.color_scheme = []
        self.init_colors()
        self._pen_default = QPen(QColor(self.color_scheme[0]))
        self._pen_default.setWidth(2)
        self._pen_hovered = QPen(QColor(self.color_scheme[1]))
        self._pen_hovered.setWidth(2)
        self._pen_selected = QPen(QColor(self.color_scheme[2]))
        self._pen_selected.setWidth(3)
        self._pen_selected.setStyle(Qt.PenStyle.DotLine)
        self._brush_title = QBrush(QColor(self.color_scheme[3]))
        self._brush_background = QBrush(QColor(self.color_scheme[4]))

        self.init_flags()

    def init_title(self):
        """
        This method sets up the title widget

        """

        self.title_item.setDefaultTextColor(QColor(palette.WHITE))
        self.title_item.setFont(QFont(dim.FONT_FAMILY, dim.FONT_SIZE))
        self.title_item.setPos(dim.TITLE_PAD, 0)
        self.title_item.setPlainText(self.block_ref.title)
        self.title_item.setTextWidth(self.width - 2 * dim.TITLE_PAD)

    def init_colors(self):
        """
        This method sets up the color scheme of the block
        using polymorphic behavior from the block itself
        """
        self.color_scheme = self.block_ref.get_color_scheme()

    def init_graphics_content(self):
        """
        This method sets up the graphics properties of the block
        depending on the content
        """
        if self.block_ref.has_parameters():
            self.width = dim.BLOCK_PARAM_WIDTH
        else:
            self.width = self.block_ref.get_block_width()

        # Init title card after setting the correct widget width
        self.init_title()
        if isinstance(self.block_ref, QueryBlock):
            self.setToolTip("Double click to view the query")

    def init_flags(self):
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

    def open_dock_params(self):
        self.block_ref.scene_ref.editor_widget_ref.show_inspector()

    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self.hover = True
        if isinstance(self.block_ref, QueryBlock):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self.hover = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseMoveEvent(event)

        for block in self.block_ref.scene_ref.blocks.values():
            if block.graphics.isSelected():
                block.update_edges()

        self.block_ref.update_edges()

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if isinstance(self.block_ref, QueryBlock) and hasattr(self.block_ref, "path"):
            # Emit signal to hierarchical output
            tab_title = f"{self.block_ref.title} - {self.block_ref.path.split('/')[-1]}"
            self.signals.query_double_clicked.emit(self.block_ref.path, tab_title)


    def paint(self, painter: 'QPainter', option: 'QStyleOptionGraphicsItem', widget=None) -> None:
        """
        This method draws the graphicsBlock item. It is a rounded rectangle divided in 3 sections:

        Outline section: draw the contours of the block
        Title section: a darker rectangle in which lays the title
        Content section: container for the block parameters

        """

        # Title section
        path_title = QPainterPath()
        path_title.setFillRule(Qt.FillRule.WindingFill)
        path_title.addRoundedRect(0, 0, self.width, dim.TITLE_HEIGHT, dim.EDGE_ROUNDNESS, dim.EDGE_ROUNDNESS)

        # Remove bottom rounded corners for title box
        path_title.addRect(0, dim.TITLE_HEIGHT - dim.EDGE_ROUNDNESS, dim.EDGE_ROUNDNESS, dim.EDGE_ROUNDNESS)
        path_title.addRect(self.width - dim.EDGE_ROUNDNESS, dim.TITLE_HEIGHT - dim.EDGE_ROUNDNESS,
                           dim.EDGE_ROUNDNESS, dim.EDGE_ROUNDNESS)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._brush_title)
        painter.drawPath(path_title.simplified())

        # Content
        path_content = QPainterPath()
        path_content.setFillRule(Qt.FillRule.WindingFill)
        path_content.addRoundedRect(0, dim.TITLE_HEIGHT, self.width,
                                    self.height - dim.TITLE_HEIGHT, dim.EDGE_ROUNDNESS, dim.EDGE_ROUNDNESS)

        # Remove top rounded corners for content box
        # left
        path_content.addRect(0, dim.TITLE_HEIGHT, dim.EDGE_ROUNDNESS, dim.EDGE_ROUNDNESS / 2)
        # right
        path_content.addRect(self.width - dim.EDGE_ROUNDNESS, dim.TITLE_HEIGHT,
                             dim.EDGE_ROUNDNESS, dim.EDGE_ROUNDNESS / 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._brush_background)
        painter.drawPath(path_content.simplified())

        # Outline
        path_outline = QPainterPath()
        path_outline.addRoundedRect(0, 0, self.width, self.height, dim.EDGE_ROUNDNESS, dim.EDGE_ROUNDNESS)
        painter.setPen(self._pen_default if not self.isSelected() else self._pen_selected)

        if self.hover and not self.isSelected():
            painter.setPen(self._pen_hovered)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path_outline.simplified())

    def boundingRect(self) -> QtCore.QRectF:
        """
        Defines the Qt bounding rectangle

        Returns
        ----------
        QRectF
            The area in which the click triggers the item

        """

        return QtCore.QRectF(0, 0, self.width, self.height).normalized()
