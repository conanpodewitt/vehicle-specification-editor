import idx2numpy
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QLabel, QTextEdit, QStackedLayout,
    QPushButton, QFileDialog, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import numpy as np
from enum import Enum
from typing import List, Type

from ui.vcl_bindings import CACHE_DIR
from ui.counter_example_view.base_renderer import *


def _vehicle_type(dtype: str) -> str:
    """Get the vehicle type based on the dtype."""
    if dtype == 'ubyte':
        return "NatTensor"
    elif dtype == 'byte' or dtype == '>i2' or dtype == '>i4':
        return "IntTensor"
    elif dtype == '>f4' or dtype == '>f8':
        return "RatTensor"
    else:
        raise ValueError(f"Unsupported data type: {dtype}")


def decode_counter_examples(cache_dir: str = CACHE_DIR) -> dict:
    """Decode counterexamples from IDX files in assignment directories."""
    subdirs = [
        d for d in os.listdir(cache_dir)
        if os.path.isdir(os.path.join(cache_dir, d)) and d.endswith("-assignments")
    ]

    counter_examples = {}
    for subdir in subdirs:
        subdir_path = os.path.join(cache_dir, subdir)
        for filename in os.listdir(subdir_path):
            full_path = os.path.join(subdir_path, filename)
            var_name = filename.strip('\"')
            key = f"{subdir}-{var_name}"
            try:
                tensors = idx2numpy.convert_from_file(full_path)
                counter_examples[key] = tensors
            except Exception as e:
                print(f"Error decoding {full_path}: {e}")

    return counter_examples


class CounterExampleWidget(QWidget):
    """Widget for displaying individual counterexamples with navigation."""

    def __init__(self, modes: List[BaseRenderer], parent=None):
        super().__init__(parent)
        self.modes = modes
        self.data_map = {}
        self.ce_paths = []
        self.ce_current_index = 0

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
        self.stack = QStackedLayout()
        for mode in self.modes:
            self.stack.addWidget(mode.widget)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(nav_layout)
        main_layout.addLayout(self.stack)
        self.setLayout(main_layout)

        # Connect signals
        self.prev_button.clicked.connect(self._go_previous)
        self.next_button.clicked.connect(self._go_next)

    def set_mode(self, mode: int):
        """Set the rendering mode."""
        self.mode = mode
        self.stack.setCurrentIndex(mode)
        self.update_display()

    def set_data(self, data: dict):
        """Set the counterexample data."""
        self.data_map = data
        self.ce_paths = list(data.keys())
        self.ce_current_index = 0
        self.update_display()

    def update_display(self):
        """Update the display based on current data and mode."""
        if not self.ce_paths:
            self.name_label.setText("No data")
            self.prev_button.hide()
            self.next_button.hide()
            return

        self.prev_button.show()
        self.next_button.show()

        key = self.ce_paths[self.ce_current_index]
        content = self.data_map[key]
        self.name_label.setText(f"{key}")

        # Render based on mode
        try:
            self.modes[self.stack.currentIndex()].render(content)
        except Exception as e:
            self.name_label.setText(f"Error rendering {key}: {e}")

    def _go_previous(self):
        """Navigate to previous counterexample."""
        if self.ce_current_index > 0:
            self.ce_current_index -= 1
        else:
            self.ce_current_index = len(self.ce_paths) - 1
        self.update_display()

    def _go_next(self):
        """Navigate to next counterexample."""
        if self.ce_current_index < len(self.ce_paths) - 1:
            self.ce_current_index += 1
        else:
            self.ce_current_index = 0
        self.update_display()


class CounterExampleTab(QWidget):
    """Main tab widget for counterexample visualization."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()

        # Control layout
        control_layout = QHBoxLayout()

        # Temporary modes for counterexample visualization
        TEMPORARY_MODES = [GSImageRenderer(), TextRenderer()]

        # Mode selector
        self.mode_selector = QComboBox()
        self.mode_selector.addItems([mode.__class__.__name__ for mode in TEMPORARY_MODES])
        self.mode_selector.currentTextChanged.connect(self._change_mode)
        self.mode_selector.setFixedWidth(100)
        control_layout.addWidget(self.mode_selector)

        # Folder selection button
        self.folder_button = QPushButton()
        self.folder_button.setIcon(QIcon.fromTheme("folder"))
        self.folder_button.setFixedSize(32, 32)
        self.folder_button.clicked.connect(self._select_folder)
        control_layout.addWidget(self.folder_button)
        self.layout.addLayout(control_layout)

        # Content widget
        self.content_widget = CounterExampleWidget(modes=TEMPORARY_MODES)
        self.layout.addWidget(self.content_widget)
        self.setLayout(self.layout)

        # Folder display
        if os.path.exists(CACHE_DIR):
            self.folder_label = QLabel(CACHE_DIR)
            counter_examples_json = decode_counter_examples(CACHE_DIR)
            self.content_widget.set_data(counter_examples_json)
            self.load_counter_examples(CACHE_DIR)
        else:
            self.folder_label = QLabel("Cache directory not found")
        control_layout.addWidget(self.folder_label)

    def _change_mode(self, new_mode):
        """Change the rendering mode."""
        self.mode = self.mode_selector.currentIndex()
        self.content_widget.set_mode(self.mode)

    def _select_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_label.setText(folder)
            self.load_counter_examples(folder)

    def load_counter_examples(self, folder=CACHE_DIR):
        """Load counterexamples from the selected folder."""
        counter_examples_json = decode_counter_examples(folder)
        self.content_widget.set_data(counter_examples_json)
