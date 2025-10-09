import idx2numpy
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QLabel, QTextEdit, QStackedLayout,
    QPushButton, QFileDialog, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from typing import List, Type, Dict
from collections import OrderedDict

from vehicle_gui.vcl_bindings import CACHE_DIR
from vehicle_gui.counter_example_view.base_renderer import *


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

    def __init__(self, parent=None):
        """Initialize the counterexample widget. Modes is a dict of variable names to lists of renderers supported for that variable."""
        super().__init__(parent)
        self.data_map = {}
        self.var_index = {}
        self.ce_paths = []
        self.ce_current_index = 0
        self.parent_ref = parent

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

        self.stack = QStackedLayout()

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(nav_layout)
        main_layout.addLayout(self.stack)
        self.setLayout(main_layout)

        # Connect signals
        self.prev_button.clicked.connect(self._go_previous)
        self.next_button.clicked.connect(self._go_next)

    def set_modes(self, modes: Dict[str, BaseRenderer]):
        """Set the rendering modes."""
        # Rebuild stack
        while self.stack.count():
            widget = self.stack.takeAt(0).widget()
            if widget:
                widget.setParent(None)

        self.var_index = {}    
        ind = 0
        for var_name, mode in modes.items():
            self.stack.addWidget(mode.widget)
            self.var_index[var_name] = ind

    def set_data(self, data: dict):
        """Set the counterexample data."""
        self.data_map = data
        self.ce_paths = list(data.keys())
        self.ce_current_index = 0
        if self.ce_paths:
            self.current_var_name = self.ce_paths[0].split('-')[-1]
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

        # Render the data for all modes of the current variable
        renderer : BaseRenderer = self.stack[self.var_index[self.current_var_name]]
        renderer.render(content)

    def _go_previous(self):
        """Navigate to previous counterexample."""
        if self.ce_current_index > 0:
            self.ce_current_index -= 1
        else:
            self.ce_current_index = len(self.ce_paths) - 1

        # Update variable name if quantified variable changed
        key = self.ce_paths[self.ce_current_index]
        self.current_var_name = key.split('-')[-1]
        self.update_display()

    def _go_next(self):
        """Navigate to next counterexample."""
        if self.ce_current_index < len(self.ce_paths) - 1:
            self.ce_current_index += 1
        else:
            self.ce_current_index = 0
        
        # Update variable name if quantified variable changed
        key = self.ce_paths[self.ce_current_index]
        self.current_var_name = key.split('-')[-1]
        self.update_display()


class CounterExampleTab(QWidget):
    """Main tab widget for counterexample visualization."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()

        # Control layout
        control_layout = QHBoxLayout()

        # Folder display
        if os.path.exists(CACHE_DIR):
            self.folder_label = QLabel(CACHE_DIR)
            counter_examples_json = decode_counter_examples(CACHE_DIR)
        else:
            self.folder_label = QLabel("Cache directory not found")
        control_layout.addWidget(self.folder_label)

        # Content widget
        self.content_widget = CounterExampleWidget(parent=self)
        self.content_widget.set_data(counter_examples_json)
        self.layout.addWidget(self.content_widget)
        self.setLayout(self.layout)

    def set_modes(self, modes: Dict[str, BaseRenderer]):
        """Set the rendering modes for variables."""
        self.content_widget.set_modes(modes)

    def refresh_from_cache(self):
        """Re-read counter examples from the cache directory."""
        if os.path.exists(CACHE_DIR):
            counter_examples_json = decode_counter_examples(CACHE_DIR)
            self.content_widget.set_data(counter_examples_json)
