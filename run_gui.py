import sys
#sys.path.append("...")
import io
import re
import os
import subprocess
from contextlib import redirect_stdout
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSplitter, QTextEdit,
                           QVBoxLayout, QPushButton, QWidget, QLabel, QFileDialog,
                           QHBoxLayout, QStatusBar, QProgressBar, QFrame, QMessageBox,
                           QComboBox, QPlainTextEdit)
from PyQt6.QtCore import Qt, QRegularExpression, QRect, QSize
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter, QTextCursor, QPainter, QTextFormat
from ui.vcl_widget import VCLEditor
import ui.code_editor

#import vehicle_lang as vcl--

TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    editor = VCLEditor()
    editor.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()