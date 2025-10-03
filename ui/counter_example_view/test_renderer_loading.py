from abc import ABC, abstractmethod
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

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

class PlotRenderer(BaseRenderer):
    """Renderer for 1D numeric data as a line plot."""

    def __init__(self):
        self._widget = QWidget()
        layout = QVBoxLayout(self._widget)

        # Create a matplotlib figure and canvas
        self._fig = Figure(figsize=(4, 3))
        self._canvas = FigureCanvas(self._fig)
        layout.addWidget(self._canvas)
        self._ax = self._fig.add_subplot(111)

    def render(self, data: np.ndarray):
        """Render a 1D array as a line plot."""
        self._ax.clear()
        self._ax.plot(np.arange(len(data)), data, marker="o")
        self._ax.set_xlabel("Index")
        self._ax.set_ylabel("Value")
        self._ax.set_title("Array Values")
        self._canvas.draw()

    @property
    def widget(self) -> QWidget:
        return self._widget