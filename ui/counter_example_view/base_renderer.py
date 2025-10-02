from abc import ABC, abstractmethod
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QTextEdit
from PyQt6.QtGui import QPixmap, QImage
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


class GSImageRenderer(BaseRenderer):
    def __init__(self):
        self._widget = QLabel()

    def _prepare_pixmap(self, data: np.ndarray) -> QPixmap:
        h, w = data.shape
        qimage = QImage(data.copy().data, w, h, w, QImage.Format_Grayscale8)
        return QPixmap.fromImage(qimage)

    def render(self, data: np.ndarray):
        pixmap = self._prepare_pixmap(data)
        self.widget.setPixmap(pixmap)

    @property
    def widget(self) -> QWidget:
        return self._widget

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
