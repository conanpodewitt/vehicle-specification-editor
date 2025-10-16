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
from collections import defaultdict

from vehicle_gui.vcl_bindings import CACHE_DIR
from vehicle_gui.counter_example_view.base_renderer import *


from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit, QCheckBox, QFrame, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFileDialog

from vehicle_gui.counter_example_view.extract_renderers import load_renderer_classes
from vehicle_gui.counter_example_view.base_renderer import TextRenderer, GSImageRenderer
from vehicle_gui import VEHICLE_DIR

RENDERERS_DIR = Path(VEHICLE_DIR) / "renderers"


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
            key = f"{subdir}-{var_name}" # e.g. prop1-assignments-varA
            try:
                tensors = idx2numpy.convert_from_file(full_path)
                counter_examples[key] = tensors
            except Exception as e:
                print(f"Error decoding {full_path}: {e}")

    return counter_examples


class VariableBox(QWidget):
    """Widget for variable renderer selection"""
    renderer_changed = pyqtSignal(str, object)  # variable_name, renderer_obj
    
    def __init__(self, var_name, parent=None):
        super().__init__(parent)
        self.variable_name = var_name
        self.renderer = None
        self.renderer_map = {}  # Maps dropdown text to renderer class
        
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Variable name label
        name_label = QLabel(f"{var_name}")
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(name_label)
        
        # Display box (read-only line edit like resource boxes)
        self.display_box = QLineEdit()
        self.display_box.setPlaceholderText("No renderer loaded")
        self.display_box.setReadOnly(True)
        layout.addWidget(self.display_box)
        
        # Renderer selection dropdown
        self.renderer_combo = QComboBox()
        self.renderer_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._populate_renderer_dropdown()
        self.renderer_combo.currentTextChanged.connect(self._on_renderer_changed)
        layout.addWidget(self.renderer_combo)
        
        self.setLayout(layout)
    
    def _populate_renderer_dropdown(self):
        """Populate the renderer dropdown with built-in and cached renderers."""
        # Add built-in renderers
        self.renderer_combo.addItem("GSImage Renderer")
        self.renderer_map["GSImage Renderer"] = GSImageRenderer()
        
        self.renderer_combo.addItem("Text Renderer")
        self.renderer_map["Text Renderer"] = TextRenderer()
        
        # Scan VEHICLE_DIR/renderers for additional renderers
        for py_file in RENDERERS_DIR.glob("*.py"):
            try:
                renderer_classes = load_renderer_classes(str(py_file))
                for renderer_class in renderer_classes:
                    renderer = renderer_class()
                    display_name = renderer.name
                    self.renderer_combo.addItem(display_name)
                    self.renderer_map[display_name] = renderer
            except Exception as e:
                error_msg = f"Error loading renderers from {py_file}: {e}"
                print(error_msg)
                raise RuntimeError(error_msg)
        
        # Add custom loader option
        self.renderer_combo.addItem("Load From Path...")

        if self.renderer_combo.count() > 0:
            first_item = self.renderer_combo.itemText(0)
            self.renderer_combo.setCurrentText(first_item)
            self._on_renderer_changed(first_item)
    
    def _on_renderer_changed(self, selection):
        if selection == "Load From Path...":
            self._load_from_path()
        elif selection in self.renderer_map:
            self._set_renderer_from_map(selection)
    
    def _set_renderer_from_map(self, selection):
        """Set renderer from the pre-loaded renderer map."""
        renderer = self.renderer_map[selection]
        try:
            self._set_renderer(renderer)
        except Exception as e:
            self._set_renderer_error(str(e))
            print(f"Error setting renderer {selection}: {e}")
    
    def _load_from_path(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Load Renderer for {self.variable_name}", "", "Renderer modules (*.py);;All Files (*)"
        )
        if file_path:
            try:
                renderer_classes = load_renderer_classes(file_path)
                if renderer_classes:
                    if len(renderer_classes) > 1:
                        print(f"Warning: Multiple renderer classes found in {file_path}. Using the first one.")
                    renderer = renderer_classes[0]
                    self._set_renderer(renderer, f"Custom: {Path(file_path).name}", file_path, "Load Custom Renderer...")
                else:
                    self._set_renderer_error("No valid renderer class found in the selected file")
            except Exception as e:
                self._set_renderer_error(str(e))
                print(f"Error loading renderer from {file_path}: {e}")
    
    def _set_renderer(self, renderer):
        """Common method to set a renderer class and update UI."""
        self.renderer = renderer
        self.display_box.setText(renderer.name)
        self.renderer_combo.setCurrentText(renderer.__class__.__name__)
        self.renderer_changed.emit(self.variable_name, renderer)
    
    def _set_renderer_error(self, error_message):
        """Common method to handle renderer loading errors."""
        self.display_box.setText("Failed to load renderer")
        self.display_box.setToolTip(error_message)


class PropertyBox(QFrame):
    """Widget representing a single property with its variables."""
    
    def __init__(self, prop_name, renderer_loader=None, parent=None):
        super().__init__(parent)
        self.renderer_loader = renderer_loader
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Property checkbox and label
        prop_layout = QHBoxLayout()
        prop_label = QLabel(f"{prop_name}")
        prop_label.setWordWrap(True)
        prop_layout.addWidget(prop_label, 1)
        layout.addLayout(prop_layout)

        var_title = QLabel("Variables:")
        var_title.setStyleSheet("font-weight: bold;")
        layout.addWidget(var_title)
        self.variable_widgets = {}
       
        self.setLayout(layout)

    def add_variable(self, var_name):
        self.var_container = QWidget()
        var_layout = QVBoxLayout(self.var_container)
        var_layout.setContentsMargins(20, 5, 5, 5)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        var_layout.addWidget(separator)

        var_widget = VariableBox(var_name, parent=self)
        if self.renderer_loader:
            var_widget.renderer_changed.connect(self.renderer_loader._on_variable_renderer_changed)
        var_layout.addWidget(var_widget)
        self.variable_widgets[var_name] = var_widget

        self.layout().addWidget(self.var_container)

    def _on_property_toggled(self, state):
        checked = state == Qt.CheckState.Checked
        self.property_toggled.emit(self.prop_data['name'], checked)
    
    def is_checked(self):
        return self.prop_checkbox.isChecked()
    
    def set_checked(self, checked):
        self.prop_checkbox.setChecked(checked)


class RendererLoader(QWidget):
    renderers_changed = pyqtSignal()  # emitted when any variable renderer changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.property_widgets = {}
        self._variable_renderers = {}
        self._is_syncing = False  # Flag to prevent recursive synchronization
        
        # Create scrollable area for properties
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.setSpacing(8)
        self.scroll_area.setWidget(self.content_widget)
        
        # Synchronization checkbox
        self.sync_checkbox = QCheckBox("Sync variables with same name")
        self.sync_checkbox.setToolTip("When enabled, changing a renderer for a variable will apply to all variables with the same name")
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.scroll_area)
        layout.addWidget(self.sync_checkbox)
        layout.addStretch()

    def load_properties(self, counter_examples: dict):
        """
        Loads a list of properties into the widget from the counterexample cache
        """
        self.property_widgets = {}
        prop_names = defaultdict(set)

        for key in counter_examples.keys():
            key_parts = key.split('-')
            prop_name, _, var_name = key_parts
            prop_names[prop_name].add(var_name)
        
        # Clear existing widgets
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create property widgets
        for prop_name in prop_names:
            prop_widget = PropertyBox(prop_name, renderer_loader=self, parent=self)
            prop_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.content_layout.addWidget(prop_widget)
            self.property_widgets[prop_name] = prop_widget

        # Add variables to each property
        for prop_name, var_names in prop_names.items():
            for var_name in var_names:
                self.property_widgets[prop_name].add_variable(var_name)
    
    def _on_variable_renderer_changed(self, variable_name, renderer):
        """Handle when a variable's renderer selection changes."""
        self._variable_renderers[variable_name] = renderer
        
        # If synchronization is enabled and we're not already syncing, update all variables with the same name
        if self.sync_checkbox.isChecked() and not self._is_syncing:
            self._sync_variable_renderer(variable_name, renderer)
        
        # Prevent recursive signal calls
        if not self._is_syncing:
            self.renderers_changed.emit()
    
    def _sync_variable_renderer(self, variable_name, renderer):
        """Update all variables with the same name to use the given renderer."""
        self._is_syncing = True  # Set flag to prevent recursive calls
        try:
            for prop_widget in self.property_widgets.values():
                var_widget = prop_widget.variable_widgets.get(variable_name)
                var_widget._set_renderer(renderer)
        except Exception as e:
            print(f"Error during variable renderer synchronization: {e}")
        finally:
            self._is_syncing = False

    @property
    def property_items(self):
        return [(name, widget) for name, widget in self.property_widgets.items()]
    
    def get_variable_renderers(self):
        """Return a dict of property_name-variable_name -> renderer for all variables."""
        renderers = {}
        for prop_name, prop_widget in self.property_widgets.items():
            for var_name, var_widget in prop_widget.variable_widgets.items():
                key = f"{prop_name}-{var_name}"
                if var_widget.renderer is not None:
                    renderers[key] = var_widget.renderer
        return renderers


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
        content = self.data_map.get(key, [])
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
        self.folder_label = QLabel(CACHE_DIR)
        counter_examples_json = decode_counter_examples(CACHE_DIR)
        control_layout.addWidget(self.folder_label)
        
        # Add control layout to main layout
        self.layout.addLayout(control_layout)

        # Main horizontal layout for property loader (left) and content (right)
        main_horizontal_layout = QHBoxLayout()

        # Property loader on the left side
        self.property_loader = RendererLoader(parent=self)
        self.property_loader.renderers_changed.connect(self._on_renderers_changed)
        self.property_loader.setMaximumWidth(350)  # Increase width for more breathing room
        self.property_loader.setMinimumWidth(320)  # Increase minimum width as well
        self.property_loader.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        main_horizontal_layout.addWidget(self.property_loader)

        # Content widget on the right side
        self.content_widget = CounterExampleWidget(parent=self)
        self.content_widget.set_data(counter_examples_json)
        main_horizontal_layout.addWidget(self.content_widget, 1)  # Give it stretch factor to take remaining space

        # Add the horizontal layout to main layout
        self.layout.addLayout(main_horizontal_layout)
        self.setLayout(self.layout)

    def refresh_from_cache(self):
        """Re-read counter examples from the cache directory."""
        if os.path.exists(CACHE_DIR):
            counter_examples = decode_counter_examples(CACHE_DIR)
            self.property_loader.load_properties(counter_examples)
            self.content_widget.set_data(counter_examples)
            self._on_renderers_changed()
        else:
            print(f"Cache directory {CACHE_DIR} does not exist")

    def _on_renderers_changed(self):
        """Handle when renderers change in the property loader."""
        variable_renderers = self.property_loader.get_variable_renderers()
        self.content_widget.set_modes(variable_renderers)

    def set_modes(self, modes: Dict[str, BaseRenderer]):
        """Set the rendering modes for variables."""
        self.content_widget.set_modes(modes)
