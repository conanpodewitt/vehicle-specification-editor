from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QToolTip
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QColor, QPainter, QFontDatabase
from PyQt6.QtGui import QPen, QTextCharFormat
from superqt.utils import CodeSyntaxHighlight
from collections import defaultdict


class ExtendedSyntaxHighlight(CodeSyntaxHighlight):
    """Syntax highlighter for Vehicle language with error highlighting"""
    def __init__(self, parent, lang, theme):
        self.line_errors = defaultdict(list)
        super().__init__(parent, lang, theme)

        # Squiggle format for errors
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(QColor("red"))
        self.error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)

    def set_errors(self, errors: list[dict]):
        """Set the list of errors to highlight"""
        self.line_errors.clear()
        for err in  errors:
            line = err["provenance"]["contents"][0]
            self.line_errors[line].append(err)
        self.rehighlight()

    def highlightBlock(self, text):
        """Highlight the current block, adding error highlights if needed"""
        super().highlightBlock(text)
        if not text: return

        block_number = self.currentBlock().blockNumber() + 1

        # Reset formatting
        current_format = self.format(0)
        combined_format = QTextCharFormat(current_format)
        combined_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.NoUnderline)
        self.setFormat(0, len(text), combined_format)

        for err in self.line_errors.get(block_number, []):
            start_line, start_col, end_line, end_col = err["provenance"]["contents"]
            if block_number == start_line and block_number == end_line:     # Single-line error
                start_idx = max(0, start_col - 1)
                end_idx = min(len(text) - 1, end_col - 1)
            elif block_number == start_line:                                # First line of multi-line error
                start_idx = max(0, start_col - 1)
                end_idx = len(text) - 1
            elif block_number == end_line:                                  # Last line of multi-line error
                start_idx = 0
                end_idx = min(len(text) - 1, end_col - 1)
            elif start_line < block_number < end_line:                      # Middle line of multi-line error
                start_idx = 0
                end_idx = len(text) - 1
            else:
                continue                                                    # No error on this line
            
            # Apply error formatting
            length = max(0, end_idx - start_idx + 1)
            combined_format.merge(self.error_format)
            self.setFormat(start_idx, length, combined_format)

            
class CodeEditor(QPlainTextEdit):
    """Custom editor with line numbers"""
    def __init__(self, lang, theme, parent=None):
        super().__init__(parent)

        # Use a fixed-width font everywhere
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

        # Syntax highlighting
        self.highlighter = ExtendedSyntaxHighlight(self.document(), lang, theme)
        self.setMouseTracking(True)
        self.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        """Show tooltips for errors on hover"""
        if event.type() == event.Type.MouseMove:
            cursor = self.cursorForPosition(event.position().toPoint())
            block_number = cursor.blockNumber() + 1
            col = cursor.positionInBlock() + 1

            tooltip_shown = False
            messages = []

            errors = self.highlighter.line_errors.get(block_number, [])
            for err in errors:
                _, start_col, _, end_col = err["provenance"]["contents"]
                if start_col <= col <= end_col:
                    tooltip_shown = True
                    messages.append(f"Problem: {err['problem']}\nFix: {err['fix']}")
                    break

            if tooltip_shown:
                QToolTip.showText(event.globalPosition().toPoint(), "\n".join(messages))
            else:
                QToolTip.hideText() 
        
        return super().eventFilter(obj, event)

    def add_errors(self, errors: list[dict]):
        self.highlighter.set_errors(errors)

    def clear_errors(self):
        self.highlighter.set_errors([])

    def line_number_area_width(self):
        """Calculate the width of the line number area"""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = self.fontMetrics().horizontalAdvance('9') * digits
        padding = 4
        return space + 2 * padding

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
        # Draw line numbers in the same monospaced font
        painter.setFont(self.font())
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(150, 150, 150))
                padding = 4
                painter.drawText(
                    padding,
                    int(top),
                    self.line_number_area.width() - 2 * padding,
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

        color = QColor(200, 200, 200, 20)  
        pen = QPen(color, 2, Qt.SolidLine)
        painter.setPen(pen)

        cursor = self.textCursor()
        block = cursor.block()
        block_geo = self.blockBoundingGeometry(block).translated(self.contentOffset())
        top = block_geo.top()
        bottom = top + self.blockBoundingRect(block).height() - 4
        
        painter.drawLine(0, int(top), self.viewport().width(), int(top))
        painter.drawLine(0, int(bottom), self.viewport().width(), int(bottom))