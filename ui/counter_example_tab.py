import idx2numpy
import os
import json
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QLabel, QTextEdit, QStackedLayout,
    QPushButton, QFileDialog, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QImage, QPixmap
import numpy as np
from enum import Enum


class RenderMode(Enum):
    """Rendering modes for counterexamples"""
    IMAGE = "image"
    TEXT = "text"
    JSON = "json"


def get_vehicle_type(dtype: str) -> str:
    """Get the vehicle type based on the dtype."""
    if dtype == 'ubyte':
        return "NatTensor"
    elif dtype == 'byte' or dtype == '>i2' or dtype == '>i4':
        return "IntTensor"
    elif dtype == '>f4' or dtype == '>f8':
        return "RatTensor"
    else:
        raise ValueError(f"Unsupported data type: {dtype}")


def convert_to_tensor(ndarr) -> dict:
    """Convert numpy array to tensor JSON format."""
    return {
        "type": get_vehicle_type(str(ndarr.dtype)),
        "shape": list(ndarr.shape),
        "data": ndarr.tolist() if hasattr(ndarr, 'tolist') else ndarr
    }


def decode_idx(filename: str) -> dict:
    """Decode IDX file and convert to tensor format."""
    ndarr = idx2numpy.convert_from_file(filename)
    return convert_to_tensor(ndarr)


def decode_counter_examples(cache_dir: str = "../temp") -> dict:
    """Decode counterexamples from IDX files in assignment directories."""
    subdirs = [
        d for d in os.listdir(cache_dir)
        if os.path.isdir(os.path.join(cache_dir, d)) and d.endswith("-assignments")
    ]

    counter_examples = {}
    for subdir in subdirs:
        subdir_path = os.path.join(cache_dir, subdir)
        for filename in os.listdir(subdir_path):
            if filename.endswith('.idx'):
                full_path = os.path.join(subdir_path, filename)
                try:
                    tensor_json = decode_idx(full_path)
                    counter_examples[filename] = tensor_json
                except Exception as e:
                    print(f"Error decoding {full_path}: {e}")

    return counter_examples


def array_to_qimage(array: np.ndarray) -> QImage:
    """Convert 2D numpy array to QImage."""
    array = array.astype(np.uint8)

    if array.ndim != 2:
        raise ValueError("Expected a 2D grayscale array")

    height, width = array.shape
    bytes_per_line = width
    return QImage(array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)


def array_to_pixmap(array: np.ndarray) -> QPixmap:
    """Convert numpy array to QPixmap."""
    qimage = array_to_qimage(array)
    return QPixmap.fromImage(qimage)


class CounterExampleWidget(QWidget):
    """Widget for displaying individual counterexamples with navigation."""

    def __init__(self, mode=RenderMode.IMAGE, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.data = {}
        self.keys = []
        self.current_index = 0

        # Navigation controls
        self.name_label = QLabel("No data loaded")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.prev_button = QPushButton("◀")
        self.prev_button.setFixedSize(32, 32)

        self.next_button = QPushButton("▶")
        self.next_button.setFixedSize(32, 32)

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.name_label)
        nav_layout.addWidget(self.next_button)

        # Content display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        self.stack = QStackedLayout()
        self.stack.addWidget(self.image_label)
        self.stack.addWidget(self.text_edit)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(nav_layout)
        main_layout.addLayout(self.stack)
        self.setLayout(main_layout)

        self.set_mode(mode)

        # Connect signals
        self.prev_button.clicked.connect(self.go_previous)
        self.next_button.clicked.connect(self.go_next)

    def set_mode(self, mode: RenderMode):
        """Set the rendering mode."""
        self.mode = mode
        self.stack.setCurrentIndex(0 if mode == RenderMode.IMAGE else 1)
        self.update_display()

    def set_data(self, data: dict):
        """Set the counterexample data."""
        self.data = data
        self.keys = list(data.keys())
        self.current_index = 0
        self.update_display()

    def update_display(self):
        """Update the display based on current data and mode."""
        if not self.keys:
            self.name_label.setText("No data")
            self.prev_button.hide()
            self.next_button.hide()
            return

        self.prev_button.show()
        self.next_button.show()

        key = self.keys[self.current_index]
        content = self.data[key]
        shape = content.get("shape", [])

        # Update label with filename and shape
        self.name_label.setText(f"{key} {shape}")

        # Render based on mode
        if self.mode == RenderMode.IMAGE:
            try:
                image_array = np.squeeze(content["data"])
                if image_array.ndim == 2:
                    qimage = array_to_pixmap(image_array)
                    self.image_label.setPixmap(qimage)
                    self.stack.setCurrentIndex(0)
                else:
                    raise ValueError("Not a 2D array")
            except Exception:
                self.text_edit.setText("Image rendering requires a 2D tensor")
                self.stack.setCurrentIndex(1)

        elif self.mode == RenderMode.TEXT:
            self.text_edit.setText(json.dumps(content["data"], indent=2))
            self.stack.setCurrentIndex(1)

        elif self.mode == RenderMode.JSON:
            self.text_edit.setText(json.dumps(content, indent=2))
            self.stack.setCurrentIndex(1)

    def go_previous(self):
        """Navigate to previous counterexample."""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()

    def go_next(self):
        """Navigate to next counterexample."""
        if self.current_index < len(self.keys) - 1:
            self.current_index += 1
            self.update_display()


class CounterExampleTab(QWidget):
    """Main tab widget for counterexample visualization."""

    def __init__(self, mode=RenderMode.IMAGE, parent=None):
        super().__init__(parent)
        self.mode = mode

        self.layout = QVBoxLayout()

        # Control layout
        control_layout = QHBoxLayout()

        # Mode selector
        self.mode_selector = QComboBox()
        self.mode_selector.addItems([mode.value for mode in RenderMode])
        self.mode_selector.currentTextChanged.connect(self.change_mode)
        self.mode_selector.setFixedWidth(100)
        control_layout.addWidget(self.mode_selector)

        # Folder display
        self.folder_label = QLabel("No folder selected")
        control_layout.addWidget(self.folder_label)

        # Folder selection button
        self.folder_button = QPushButton()
        self.folder_button.setIcon(QIcon.fromTheme("folder"))
        self.folder_button.setFixedSize(32, 32)
        self.folder_button.clicked.connect(self.select_folder)
        control_layout.addWidget(self.folder_button)

        self.layout.addLayout(control_layout)

        # Content widget
        self.content_widget = CounterExampleWidget(mode=self.mode)
        self.layout.addWidget(self.content_widget)

        self.setLayout(self.layout)

    def change_mode(self, new_mode):
        """Change the rendering mode."""
        self.mode = RenderMode(new_mode)
        self.content_widget.set_mode(self.mode)

    def select_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_label.setText(folder)
            self.load_counter_examples_from_folder(folder)

    def load_counter_examples_from_folder(self, folder):
        """Load counterexamples from the selected folder."""
        counter_examples_json = decode_counter_examples(folder)
        self.content_widget.set_data(counter_examples_json)


# Command-line testing
if __name__ == "__main__":
    if len(sys.argv) > 1:
        cache_location = sys.argv[1]
        result = decode_counter_examples(cache_location)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python counter_example_tab.py <cache_directory>")
