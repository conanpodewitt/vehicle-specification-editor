from PyQt6.QtWidgets import (QApplication, QMainWindow, QSplitter, QTextEdit,
                           QVBoxLayout, QPushButton, QWidget, QLabel, QFileDialog,
                           QHBoxLayout, QStatusBar, QProgressBar, QFrame, QMessageBox,
                           QComboBox, QPlainTextEdit)
from PyQt6.QtCore import Qt, QRegularExpression, QRect, QSize
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter, QTextCursor, QPainter, QTextFormat
#from pygments import PythonLexer
from pygments.lexers import get_lexer_by_name
from pygments.lexers import *
import pygments
from superqt.utils import CodeSyntaxHighlight


class VCLSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for VCL specification files"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create highlight formats
        self.formats = {}

        lexer = get_lexer_by_name("external")
        tokens = lexer.get_tokens_unprocessed()
        pygments.lex(lexer)
        
        #tokens = lexer.get_tokens("string", False)
        # Keyword format _
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        self.formats['keyword'] = keyword_format
        
        # Comment format _/
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        self.formats['comment'] = comment_format
        
        # Number format -- Numeric_literals
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        self.formats['number'] = number_format
        
        # String format
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        self.formats['string'] = string_format
        
        # Operator format -- Holes??
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor("#D4D4D4"))
        self.formats['operator'] = operator_format
        
        #Builtins?

        # Define highlighting rules
        self.highlighting_rules = []
        
        # Keywords
        keywords = [
            "@network", "@dataset", "@parameter", "@property", "@postulate", "@noinline",
            "forall", "exists", "foreach", "let", "in", "if", "then", "else",
            "True", "False", "nil", "not", "map", "dfold", "fold", "indices", "fromNat", "fromInt",
            "Unit", "Bool", "Nat", "Int", "Real", "Vector", "Tensor", "  ", "Index", "Type"
        ]
 
        #Builtins
        builtins = {
            "forall", "Unit", "Bool", "Nat", "Int", "Rat", "Vector", "Tensor", "List",
            "Index", "Type(\s*([0-9]+)?)"
        }
        

        # Operators
        operators = [
            r"->", r"\.", r":", r"\\", r"=>", r"==", r"!=", r"<=", r"<", 
            r">=", r">", r"\*", r"/", r"\+", r"-", r"::", r"!", r"=", r"and", r"or"
        ]
        
        for op in operators:
            pattern = QRegularExpression(op)
            self.highlighting_rules.append((pattern, 'operator'))

        for word in keywords:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self.highlighting_rules.append((pattern, 'keyword'))
        
        
        # Comments (lines starting with --)
        self.highlighting_rules.append((QRegularExpression(r'--.*$'), 'comment'))
        
        # Numbers
        self.highlighting_rules.append((QRegularExpression(r'\b\d+(\.\d+)?\b'), 'number'))
        
        # Strings (assuming double quotes)
        self.highlighting_rules.append((QRegularExpression(r'"[^"]*"'), 'string'))

    def highlightBlock(self, text):
        """Apply highlighting rules to a text block"""
        for pattern, format_name in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), self.formats[format_name])