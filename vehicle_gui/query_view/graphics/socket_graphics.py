"""
Module socket_graphics.py

This module contains the graphical representation of a Socket element

Original author: Andrea Gimelli, Giacomo Rosato, Stefano Demarchi

"""

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPen, QBrush, QPainter
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem

import vehicle_gui.query_view.styling.dimension as dim
import vehicle_gui.query_view.styling.palette as palette
from ..base_types import Socket


class SocketGraphics(QGraphicsItem):
    """Graphics representation of a Socket domain model"""

    def __init__(self, socket: 'Socket', parent=None):
        super().__init__(parent)
        # Reference to socket domain model
        self.socket_ref = socket

        # Style parameters
        self.bg_color = QColor(palette.WHITE)
        self.outline_color = QColor(palette.WHITE)
        self.init_colors()

        self._pen = QPen(self.outline_color)
        self._pen.setWidth(dim.SOCKET_OUTLINE)
        self._brush = QBrush(self.bg_color)

        self.setZValue(-1)

    def init_colors(self):
        """Set socket colors using polymorphic behavior from the block"""
        socket_colors = self.socket_ref.block_ref.get_socket_colors()
        self.bg_color = QColor(socket_colors["bg_color"])
        self.outline_color = QColor(socket_colors["outline_color"])

    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget=None) -> None:
        painter.setBrush(self._brush)
        painter.setPen(self._pen)
        painter.drawEllipse(-dim.SOCKET_RADIUS, -dim.SOCKET_RADIUS, 2 * dim.SOCKET_RADIUS, 2 * dim.SOCKET_RADIUS)

    def boundingRect(self) -> QRectF:

        return QRectF(
            - dim.SOCKET_RADIUS - dim.SOCKET_OUTLINE,
            - dim.SOCKET_RADIUS - dim.SOCKET_OUTLINE,
            2 * (dim.SOCKET_RADIUS + dim.SOCKET_OUTLINE),
            2 * (dim.SOCKET_RADIUS + dim.SOCKET_OUTLINE),
        )
