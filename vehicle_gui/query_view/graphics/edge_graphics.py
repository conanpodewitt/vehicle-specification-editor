"""
Module edge_graphics.py

This module contains the class EdgeGraphics and its concrete children
DirectEdgeGraphics and BezierEdgeGraphics for displaying edges connecting
the blocks

Original author: Andrea Gimelli, Giacomo Rosato, Stefano Demarchi

"""

import abc
import math

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QColor, QPainter, QPolygonF, QPainterPath
from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import QGraphicsPathItem, QStyleOptionGraphicsItem

import vehicle_gui.query_view.styling.dimension as dim
import vehicle_gui.query_view.styling.palette as palette
from ..base_types import Edge, SocketType


class EdgeGraphics(QGraphicsPathItem):
    """Graphics representation of an Edge domain model"""

    def __init__(self, edge: 'Edge', parent=None):
        super().__init__(parent)

        # Reference to edge domain model
        self.edge_ref = edge

        if self.edge_ref.view_dim:
            self._pen = QPen(QColor(palette.DARK_TEAL))
        else:
            self._pen = QPen(QColor(palette.DARK_ORANGE))
        self._pen.setWidth(2)
        self.setZValue(-1)

        # Edge dimension label
        self.label = ''

        # Position
        self.src_pos = [0, 0]
        self.dest_pos = [200, 200]

        self.update()

    @abc.abstractmethod
    def update_path(self):
        """
        Abstract method to be implemented

        """

        pass

    @abc.abstractmethod
    def calc_path(self) -> QPainterPath:
        """
        Abstract method to be implemented

        """

        pass

    def set_label(self, text):
        self.label = text
        self.update()

    def build_arrow(self) -> list:
        """
        This method computes and returns the three vertices of the arrow

        Returns
        ----------
        list
            Three QPointF objects

        """

        radius = 7

        xs, ys = self.src_pos
        xd, yd = self.dest_pos[0] - radius, self.dest_pos[1]

        arrow_dimension = 5

        # Point1: equals self.position_destination
        point1 = QPointF(xd, yd)

        # Angular coefficient given 2 points
        try:
            ang_cf = (yd - ys) / (xd - xs)  # If xd-xs == 0 raises exception

            # Find the angle in degrees: atan(ang_cf)
            theta = math.atan(ang_cf)

            # Find point (coordinate) distant arrow_dimension pixel from point destination on the line
            p_auxiliary = QPointF(xd - arrow_dimension * math.cos(theta), yd - arrow_dimension * math.sin(theta))
            gamma = math.atan(-1 / ang_cf)

            # Point2
            point2 = QPointF(p_auxiliary.x() - arrow_dimension * math.cos(gamma),
                             p_auxiliary.y() - arrow_dimension * math.sin(gamma))

            # Point3
            point3 = QPointF(p_auxiliary.x() + arrow_dimension * math.cos(gamma),
                             p_auxiliary.y() + arrow_dimension * math.sin(gamma))

        except ZeroDivisionError:
            p_auxiliary = QPointF(xd - arrow_dimension, yd)
            point2 = QPointF(p_auxiliary.x(), p_auxiliary.y() - arrow_dimension)
            point3 = QPointF(p_auxiliary.x(), p_auxiliary.y() + arrow_dimension)

        return [point1, point2, point3]

    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget=None) -> None:
        """
        Draw the edge, the arrow in the destination and the label

        """

        # Draw edge path
        self.update_path()
        painter.setPen(self._pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        # Draw edge label
        painter.setBrush(QColor('yellow'))
        label_rect = QRectF((self.src_pos[0] + self.dest_pos[0]) / 2 - 48,
                            (self.src_pos[1] + self.dest_pos[1]) / 2, 100, 40)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self.label)

        # No arrow - just solid lines

    def shape(self) -> 'QtGui.QPainterPath':
        return self.calc_path()

    def boundingRect(self) -> 'QtCore.QRectF':
        return self.shape().boundingRect()


class DirectEdgeGraphics(EdgeGraphics):
    """
    This class displays a direct edge from point A to point B

    """

    def update_path(self):
        """
        This method draws the actual line between two positions

        """

        path = QPainterPath(QPointF(self.src_pos[0], self.src_pos[1]))
        path.lineTo(self.dest_pos[0], self.dest_pos[1])
        self.setPath(path)

    def boundingRect(self) -> QRectF:
        return self.shape().boundingRect()

    def shape(self) -> QPainterPath:
        return self.path()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None) -> None:
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.setPen(self._pen)
        painter.drawPath(self.path())


class BezierEdgeGraphics(EdgeGraphics):
    """Graphics representation using a bezier path for the edge"""

    def __init__(self, edge, parent=None):
        super().__init__(edge, parent)
        super().__init__(edge, parent)

    def update_path(self):
        """Update path for hierarchical vertical connections with symmetric curves"""
        vertical_distance = abs(self.dest_pos[1] - self.src_pos[1])
        control_point_offset = min(vertical_distance * 0.4, 100)
        
        path = QPainterPath(QPointF(self.src_pos[0], self.src_pos[1]))
        path.cubicTo(
            self.src_pos[0], self.src_pos[1] + control_point_offset,   
            self.dest_pos[0], self.dest_pos[1] - control_point_offset, 
            self.dest_pos[0], self.dest_pos[1]
        )
        self.setPath(path)

    def calc_path(self) -> QPainterPath:
        """
        Compute the cubic Bezier line connection for hierarchical vertical layout

        Returns
        ----------
        QPainterPath
            The path of this edge with symmetric vertical curves

        """
        s = self.src_pos
        d = self.dest_pos
        
        vertical_distance = abs(d[1] - s[1])
        control_point_offset = min(vertical_distance * 0.4, 100) 
        
        cpx_s = 0  
        cpy_s = control_point_offset  
        cpx_d = 0  
        cpy_d = -control_point_offset  

        path = QPainterPath(QPointF(s[0], s[1]))
        path.cubicTo(s[0] + cpx_s, s[1] + cpy_s, d[0] + cpx_d, d[1] + cpy_d,
                     d[0], d[1])

        return path