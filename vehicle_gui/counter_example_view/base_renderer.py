from abc import ABC, abstractmethod
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QTextEdit
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt
from typing import Optional, Dict
import numpy as np


class BaseRenderer(ABC):
    @abstractmethod
    def render(self, data: np.ndarray):
        """Render the given data in the internal widget."""
        pass

    @property
    @abstractmethod
    def widget(self):
        """Subclasses must provide a widget property."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Subclasses must provide a name property."""
        pass


class GSImageRenderer(BaseRenderer):
    # Constant for maximum display height
    MAX_DISPLAY_HEIGHT = 300
    
    def __init__(self):
        self._widget = QLabel()

    def _prepare_pixmap(self, data: np.ndarray) -> QPixmap:
        h, w = data.shape
        qimage = QImage(data.copy().data, w, h, w, QImage.Format_Grayscale8)
        return QPixmap.fromImage(qimage)

    def render(self, data: np.ndarray):
        pixmap = self._prepare_pixmap(data)
        
        # Calculate scale factor based on max display height
        original_height = pixmap.height()
        scale_factor = self.MAX_DISPLAY_HEIGHT / original_height
        scale_factor = max(1.0, scale_factor)  
        scaled_pixmap = pixmap.scaled(
            int(pixmap.width() * scale_factor), 
            int(pixmap.height() * scale_factor),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.widget.setPixmap(scaled_pixmap)

    @property
    def widget(self) -> QWidget:
        return self._widget
    
    @property
    def name(self) -> str:
        return "Grayscale Image Renderer"

class TextRenderer(BaseRenderer):
    """Renderer for text data."""
    def __init__(self):
        self._widget = QTextEdit()
        self._widget.setReadOnly(True)

    def render(self, data: np.ndarray):
        with np.printoptions(precision=3, threshold=20, suppress=True):
            string_rept = str(data)
            self.widget.setText(string_rept)

    @property
    def widget(self) -> QWidget:
        return self._widget
    
    @property
    def name(self) -> str:
        return "Text Renderer"
