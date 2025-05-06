from PyQt6.QtWidgets import QPlainTextEdit, QWidget
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QColor, QPainter, QFontDatabase

class CodeEditor(QPlainTextEdit):
    """Custom editor with line numbers"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # use a fixed-width font everywhere
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(14)
        self.setFont(mono)
        # Create inline line-number area
        self.line_number_area = QWidget(self)
        # Bind the size hint and paint events
        self.line_number_area.sizeHint = lambda: QSize(self.line_number_area_width(), 0)
        self.line_number_area.paintEvent = self.line_number_area_paint_event
        # Connect signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        # Initial update
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_width(self):
        """Calculate the width of the line number area"""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, new_block_count):
        """Update the margin according to the line number area width"""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Update the line number area when needed"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Handle resize event"""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        """Paint the line numbers"""
        painter = QPainter(self.line_number_area)
        # draw line numbers in the same monospaced font
        painter.setFont(self.font())
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(150, 150, 150))
                painter.drawText(
                    0,
                    int(top),
                    self.line_number_area.width(),
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlight_current_line(self):
        """Trigger repaint to draw horizontal rules around the current line"""
        self.viewport().update()

    def paintEvent(self, event):
        """Paint editor normally, then draw rules above and below the current line"""
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        painter.setPen(QColor(200, 200, 200))
        cursor = self.textCursor()
        block = cursor.block()
        block_geo = self.blockBoundingGeometry(block).translated(self.contentOffset())
        top = block_geo.top()
        bottom = top + self.blockBoundingRect(block).height() - 4
        painter.drawLine(0, int(top), self.viewport().width(), int(top))
        painter.drawLine(0, int(bottom), self.viewport().width(), int(bottom))