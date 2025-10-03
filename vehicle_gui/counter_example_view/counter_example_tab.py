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
        self.modes = OrderedDict()  # variable name -> list of renderers
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

        self.stack = QStackedLayout()

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(nav_layout)
        main_layout.addLayout(self.stack)
        self.setLayout(main_layout)

        # Connect signals
        self.prev_button.clicked.connect(self._go_previous)
        self.next_button.clicked.connect(self._go_next)

    def set_modes(self, modes: Dict[str, List[BaseRenderer]]):
        """Set the rendering modes."""
        self.modes = OrderedDict(modes)
        self.var_index = {}
        ind = 0
        for var_name in self.modes:
            self.var_index[var_name] = ind
            ind += len(self.modes[var_name])

        # Rebuild stack
        while self.stack.count():
            widget = self.stack.takeAt(0).widget()
            if widget:
                widget.setParent(None)
        for mode_list in self.modes.values():
            for renderer in mode_list:
                self.stack.addWidget(renderer.widget)

    def set_data(self, data: dict):
        """Set the counterexample data."""
        self.data_map = data
        self.ce_paths = list(data.keys())
        self.ce_current_index = 0
        if self.ce_paths:
            self.var_name = self.ce_paths[0].split('-')[-1]
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
        for renderer in self.modes.get(self.var_name, []):
            try:
                renderer.render(content)
            except Exception as e:
                print(f"Error rendering {self.var_name} with {renderer}: {e}")

    def _go_previous(self):
        """Navigate to previous counterexample."""
        if self.ce_current_index > 0:
            self.ce_current_index -= 1
        else:
            self.ce_current_index = len(self.ce_paths) - 1

        # Update variable name if quantified variable changed
        key = self.ce_paths[self.ce_current_index]
        self.var_name = key.split('-')[-1]

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
        self.var_name = key.split('-')[-1]

        modes = self._get_modes_for_var(self.var_name)
        self.parent_ref.set_combo_box(modes)
        self.update_display()

    def _get_modes_for_var(self, var_name: str) -> List[str]:
        """Get the list of rendering modes available for a given variable."""
        renderers = self.modes.get(var_name, self.modes.get("default", []))
        return [type(renderer).__name__ for renderer in renderers]


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
        self.content_widget = CounterExampleWidget(parent=self)
        self.content_widget.set_data(counter_examples_json)
        self.layout.addWidget(self.content_widget)
        self.setLayout(self.layout)

    def set_modes(self, modes: Dict[str, List[BaseRenderer]]):
        """Set the rendering modes for variables."""
        self.modes = OrderedDict(modes)
        self.content_widget.set_modes(modes)
        # Update combo for current var if data loaded
        self._update_combo_for_current_data()

    def set_combo_box(self, mode_names: List[str]):
        """Set the combo box items for the current variable's modes."""
        self.mode_selector.clear()
        self.mode_selector.addItems(mode_names)
        self.current_var_modes = mode_names

    def _change_mode(self, new_mode):
        """Change the rendering mode."""
        mode_index = self.mode_selector.currentIndex()
        stack_index = self.content_widget.var_index[self.var_name] + mode_index
        self.content_widget.stack.setCurrentIndex(stack_index)

    def _select_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_label.setText(folder)
            counter_examples_json = decode_counter_examples(folder)
            self.content_widget.set_data(counter_examples_json)
            # Set initial combo
            self._update_combo_for_current_data()

    def refresh_from_cache(self):
        """Re-read counter examples from the cache directory."""
        if os.path.exists(CACHE_DIR):
            counter_examples_json = decode_counter_examples(CACHE_DIR)
            self.content_widget.set_data(counter_examples_json)
            # Update combo for current data
            self._update_combo_for_current_data()

    def _update_combo_for_current_data(self):
        """Update the combo box based on the current loaded data."""
        if self.content_widget.ce_paths:
            key = self.content_widget.ce_paths[0]
            self.var_name = key.split('-')[-1]
            mode_names = self.content_widget._get_modes_for_var(self.var_name)
            self.set_combo_box(mode_names)
