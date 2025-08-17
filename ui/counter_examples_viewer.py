from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QTextEdit, QStackedLayout
from PyQt6.QtCore import Qt as AlignCenter
from counter_examples.render_counter_examples import array_to_pixmap
import numpy as np

class CounterExampleWidget(QWidget):
    def __init__(self, mode="image", parent=None):
        super().__init__(parent)

        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(AlignCenter)

        # Text display
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        # Stack layout to switch views
        self.stack = QStackedLayout()
        self.stack.addWidget(self.image_label)  # index 0
        self.stack.addWidget(self.text_edit)    # index 1

        self.setLayout(self.stack)
        self.set_mode(mode)

    def set_mode(self, mode: str):
        """Switch between 'image' and 'text' mode."""
        if mode == "image":
            self.stack.setCurrentIndex(0)
        elif mode == "text":
            self.stack.setCurrentIndex(1)
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        self.mode = mode

    def update_data(self, image_array: np.ndarray):
        """Update the display based on current mode."""
        if self.mode == "image":
            qimage = array_to_pixmap(image_array)
            self.image_label.setPixmap(qimage)
        elif self.mode == "text":
            text = "\n".join(" ".join(f"{val:3}" for val in row) for row in image_array)
            self.text_edit.setText(text)


class CounterExampleViewer(QWidget):
    def __init__(self, mode="image", parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.display = CounterExampleWidget(mode=mode)
        self.layout.addWidget(self.display)

    def set_mode(self, mode):
        self.display.set_mode(mode)

    def update_data(self, data):
        self.display.update_data(data)