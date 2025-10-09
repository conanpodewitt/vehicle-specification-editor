import idx2numpy
import os
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QLabel, QTextEdit, QStackedLayout,
    QPushButton, QFileDialog, QHBoxLayout, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from typing import List, Type, Dict
from collections import OrderedDict

from vehicle_gui.vcl_bindings import CACHE_DIR
from vehicle_gui.counter_example_view.base_renderer import *


def _wait_until_stable_size(path: str, checks: int = 3, interval: float = 0.05) -> bool:
    """
    Return True if the file's size is stable over a series of checks.
    """
    try:
        last = os.path.getsize(path)
        if last <= 4:
            return False
        for _ in range(checks - 1):
            time.sleep(interval)
            now = os.path.getsize(path)
            if now != last:
                last = now
        time.sleep(interval)
        return os.path.getsize(path) == last and last > 4
    except FileNotFoundError:
        return False


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
            if not os.path.isfile(full_path):
                continue

            if not _wait_until_stable_size(full_path, checks=4, interval=0.05):
                continue

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
        self.renderers = {}
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
        
        # Create a container widget for the stack
        stack_container = QWidget()
        stack_container.setLayout(self.stack)
        main_layout.addWidget(stack_container)
        
        self.setLayout(main_layout)

        # Connect signals
        self.prev_button.clicked.connect(self._go_previous)
        self.next_button.clicked.connect(self._go_next)

    def set_modes(self, modes: Dict[str, BaseRenderer]):
        """Set the rendering modes."""
        # Ignore if no new modes provided
        if len(modes) == 0:
            return
        
        # Rebuild stack
        while self.stack.count():
            widget = self.stack.takeAt(0).widget()
            if widget:
                widget.setParent(None)

        self.var_index = {}
        self.renderers = {}

        ind = 0
        for var_name, renderer in modes.items():
            self.stack.addWidget(renderer.widget)
            self.var_index[var_name] = ind
            self.renderers[var_name] = renderer
            ind += 1
        
        # If we have data and just got renderers, update the display
        if len(modes) > 0 and self.ce_paths:
            self.update_display()

    def set_data(self, data: dict):
        """Set the counterexample data."""
        self.data_map = data
        self.ce_paths = list(data.keys())
        self.ce_current_index = 0
        if self.ce_paths:
            self._update_current_names()
        
        # Only update display if we have data, otherwise wait for renderers
        if self.ce_paths and len(self.renderers) > 0:
            self.update_display()
        elif not self.ce_paths:
            self.update_display()  # Clear display when no data

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

        # Render the data for the current variable if it has a renderer
        compound_key = f"{self.current_prop_name}-{self.current_var_name}"
        
        if compound_key in self.renderers:
            renderer = self.renderers[compound_key]
            try:
                renderer.render(content)
                self.stack.setCurrentIndex(self.var_index[compound_key])
            except Exception as e:
                print(f"Error during rendering: {e}")
        else:
            # No renderer available for this variable
            print(f"No renderer available for {compound_key}")

    def _go_previous(self):
        """Navigate to previous counterexample."""
        if self.ce_current_index > 0:
            self.ce_current_index -= 1
        else:
            self.ce_current_index = len(self.ce_paths) - 1

        # Update property and variable names
        self._update_current_names()
        self.update_display()

    def _go_next(self):
        """Navigate to next counterexample."""
        if self.ce_current_index < len(self.ce_paths) - 1:
            self.ce_current_index += 1
        else:
            self.ce_current_index = 0
        
        # Update property and variable names
        self._update_current_names()
        self.update_display()

    def _update_current_names(self):
        """Update current property and variable names based on current counterexample."""
        key = self.ce_paths[self.ce_current_index]
        key_parts = key.split('-')

        # Find the assignments part and extract property and variable
        assignments_idx = key_parts.index('assignments')
        self.current_prop_name = '-'.join(key_parts[:assignments_idx])
        self.current_var_name = '-'.join(key_parts[assignments_idx + 1:])


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
        print(f"=== refresh_from_cache called ===")
        if os.path.exists(CACHE_DIR):
            counter_examples_json = decode_counter_examples(CACHE_DIR)
            print(f"Decoded {len(counter_examples_json)} counter examples")
            self.content_widget.set_data(counter_examples_json)
        else:
            print(f"Cache directory {CACHE_DIR} does not exist")
