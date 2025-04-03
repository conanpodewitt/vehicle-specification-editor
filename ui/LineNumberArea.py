from PyQt6.QtWidgets import (QApplication, QMainWindow, QSplitter, QTextEdit,
                           QVBoxLayout, QPushButton, QWidget, QLabel, QFileDialog,
                           QHBoxLayout, QStatusBar, QProgressBar, QFrame, QMessageBox,
                           QComboBox, QPlainTextEdit)
from PyQt6.QtCore import Qt, QRegularExpression, QRect, QSize
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter, QTextCursor, QPainter, QTextFormat


class LineNumberArea(QWidget):
    """Widget for showing line numbers"""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        
    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)
        
    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)