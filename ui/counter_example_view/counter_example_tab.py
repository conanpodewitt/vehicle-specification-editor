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
from typing import List, Type, Dict
from collections import OrderedDict

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
                counter_examples["var_name"] = var_name
            except Exception as e:
                print(f"Error decoding {full_path}: {e}")

    return counter_examples


class CounterExampleWidget(QWidget):
    """Widget for displaying individual counterexamples with navigation."""

    def __init__(self, modes: Dict[str, List[BaseRenderer]] = {}, parent=None):
        """Initialize the counterexample widget. Modes is a dict of variable names to lists of renderers supported for that variable."""
        super().__init__(parent)
        self.modes = OrderedDict(modes)
        self.data_map = {}
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

        # Content display
        self.var_index = {}     # Map variable names to starting index in stacked layout
        ind = 0
        for var_name in self.modes:
            self.var_index[var_name] = ind
            ind += len(self.modes[var_name])

        self.stack = QStackedLayout()
        for mode in self.modes.values():
            self.stack.addWidget(mode)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(nav_layout)
        main_layout.addLayout(self.stack)
        self.setLayout(main_layout)

        # Connect signals
        self.prev_button.clicked.connect(self._go_previous)
        self.next_button.clicked.connect(self._go_next)

    def set_mode(self, local_ind: int):
        """Set the rendering mode."""
        mode_index = self.var_index.get(self.var_name, 0) + local_ind
        self.stack.setCurrentIndex(mode_index)
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

        # Update variable name if quantified variable changed
        key = self.ce_paths[self.ce_current_index]
        self.var_name = self.data_map[key]["var_name"]

        modes = self._get_modes_for_var(self.var_name)
        self.parent_ref.set_combo_box(modes)
        self.update_display()

    def _go_next(self):
        """Navigate to next counterexample."""
        if self.ce_current_index < len(self.ce_paths) - 1:
            self.ce_current_index += 1
        else:
            self.ce_current_index = 0
        
        # Update variable name if quantified variable changed
        key = self.ce_paths[self.ce_current_index]
        self.var_name = self.data_map[key]["var_name"]

        modes = self._get_modes_for_var(self.var_name)
        self.parent_ref.set_combo_box(modes)
        self.update_display()

    def _get_modes_for_var(self, var_name: str) -> List[str]:
        """Get the list of rendering modes available for a given variable."""
        if var_name in self.modes:
            return [type(renderer).__name__ for renderer in self.modes[var_name]]
        return []


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

        # Mode selector
        self.mode_selector = QComboBox()
        self.mode_selector.setFixedWidth(100)
        self.mode_selector.addItems()
        self.mode_selector.currentTextChanged.connect(self._change_mode)
        control_layout.addWidget(self.mode_selector)

        # Folder selection button
        self.folder_button = QPushButton()
        self.folder_button.setIcon(QIcon.fromTheme("folder"))
        self.folder_button.setFixedSize(32, 32)
        self.folder_button.clicked.connect(self._select_folder)
        control_layout.addWidget(self.folder_button)
        self.layout.addLayout(control_layout)

        # Content widget
        self.content_widget = CounterExampleWidget()
        self.content_widget.set_data(counter_examples_json)
        self.layout.addWidget(self.content_widget)
        self.setLayout(self.layout)

    def _change_mode(self, new_mode):
        """Change the rendering mode."""
        self.mode = self.mode_selector.currentIndex()
        self.content_widget.set_mode(self.mode)

    def _select_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_label.setText(folder)
            counter_examples_json = decode_counter_examples(folder)
            self.content_widget.set_data(counter_examples_json)

    def set_renderers(self, modes: Dict[str, List[BaseRenderer]]):
        """Set the variable renderers for the content widget."""
        # Reinitialise the content widget with new modes
        self.content_widget.setParent(None)
        self.content_widget = CounterExampleWidget(modes=modes)

    def set_combo_box(self, items: List[str]):
        """Set the items in the mode selector combo box."""
        self.mode_selector.clear()
        self.mode_selector.addItems(items)

