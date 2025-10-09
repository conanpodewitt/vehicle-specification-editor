import os
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QLabel, QLineEdit, QFrame, QFileDialog, QMessageBox, QSizePolicy, QHBoxLayout, QWidget, QScrollArea


class InputBox(QFrame):
    # Signal emitted when load status changes
    load_status_changed = pyqtSignal(bool)  # True when loaded, False when unloaded

    def __init__(self, name, type_, data_type=None):
        super().__init__()
        self.setObjectName("InputBox")
        layout = QVBoxLayout()
        title = QLabel(f"{type_}: {name}")
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(11)
        mono.setWeight(QFont.Weight.Bold)
        title.setFont(mono)
        layout.addWidget(title)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.is_loaded = False
        self.type = type_
        self.name = name
        self.data_type = data_type

        if type_ == "Network" or type_ == "Dataset" or type_ == "Variable":
            input_layout = QHBoxLayout()
            self.input_box = QLineEdit()
            self.input_box.setPlaceholderText(f"No {type_} loaded")
            self.input_box.setReadOnly(True)
            input_layout.addWidget(self.input_box)

            # Create small folder icon button
            self.load_btn = QPushButton()
            self.load_btn.setIcon(QIcon.fromTheme("folder"))
            self.load_btn.setFixedSize(32, 32)
            self.load_btn.clicked.connect(self.set_path)
            input_layout.addWidget(self.load_btn)
            input_layout.setSpacing(4)
            layout.addLayout(input_layout)

        elif type_ == "Parameter":
            self.value = None       # Unset value is None

            self.input_box = QLineEdit()
            self.input_box.editingFinished.connect(self.set_value)
            layout.addWidget(self.input_box)

            # Add a label to show the data type
            self.data_type_label = QLabel(f"Data Type: {data_type}")
            label_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
            label_font.setPointSize(10)
            self.data_type_label.setFont(label_font)
            self.data_type_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            layout.addWidget(self.data_type_label)
            self.input_box.setPlaceholderText(f"Enter {self.data_type} value")
            self.data_type = data_type

        self.setLayout(layout)

    def set_path(self):
        """Open a dataset path"""
        if self.type == "Network":
            file_filter = "ONNX Files (*.onnx);;All Files (*)"
        elif self.type == "Dataset":
            file_filter = "All Files (*)"
        elif self.type == "Variable":
            file_filter = "Renderer modules (*.py);;All Files (*)"

        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Open {self.type}", "", file_filter
        )
        if not file_path:
            return
        self.path = file_path
        self.input_box.setText(os.path.basename(file_path))
        self.input_box.setToolTip(file_path) # Show full path on hover
        self.is_loaded = True
        self.load_status_changed.emit(True)

    def set_value(self):
        value = self.input_box.text()
        """Set the value of the parameter"""
        if self.data_type == "Real":
            try:
                value = float(value)
            except ValueError:
                QMessageBox.critical(self, "Invalid Value", "Value must be a number.")
                return
        elif self.data_type == "Nat":
            try:
                value = int(value)
            except ValueError:
                QMessageBox.critical(self, "Invalid Value", "Value must be a natural number.")
                return
        elif self.data_type == "Bool":
            if value.lower() not in ["true", "false"]:
                QMessageBox.critical(self, "Invalid Value", "Value must be 'true' or 'false'.")
                return
            value = value.lower() == "true"
        else:
            raise ValueError(f"Unexpected data type: {self.data_type}")

        self.input_box.setText(str(value))
        self.is_loaded = True
        self.value = value
        self.load_status_changed.emit(True)


class InputView(QWidget):
    """Widget for managing input boxes (Networks, Datasets, Parameters)."""

    def __init__(self, parent=None, error_callback=None):
        super().__init__(parent)
        self.error_callback = error_callback or (lambda msg: print(f"Error: {msg}"))
        self.input_boxes = []
        # Store input state: name -> {"definition": {...}, "loaded": (path/value, display_text) or None}
        self._input_state = {}

        # Create scrollable area for input boxes
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Create a widget to hold the input boxes
        self.content_widget = QWidget()
        self.input_layout = QVBoxLayout(self.content_widget)
        self.input_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.content_widget)

        # Status label
        self.status_label = QLabel("0 inputs loaded")

        # Control buttons
        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(self.clear_input_boxes)

        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addLayout(btn_row)
        layout.addWidget(self.scroll_area)

    def _remove_all_boxes(self):
        """Remove all input boxes without recreating them."""
        # Remove and delete existing boxes
        while self.input_layout.count():
            item = self.input_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.input_boxes.clear()

    def clear_input_boxes(self):
        """Delete all input boxes and recreate empty ones."""
        self._remove_all_boxes()

        # Recreate empty boxes from stored input definitions
        for name, state in self._input_state.items():
            definition = state["definition"]
            type_ = definition.get("tag")
            data_type = definition.get("typeText", None)
            if not name or not type_:
                continue
            box = InputBox(name, type_, data_type=data_type)
            box.load_status_changed.connect(self._update_status)
            self.input_layout.addWidget(box)
            self.input_boxes.append(box)

        self._update_status()

    def _save_loaded_state(self):
        """Update the loaded state of all input boxes."""
        for box in self.input_boxes:
            if box.name in self._input_state:
                if box.is_loaded:
                    if hasattr(box, 'path'):
                        # For Network, Dataset, Variable
                        self._input_state[box.name]["loaded"] = (box.path, box.input_box.text())
                    elif hasattr(box, 'value'):
                        # For Parameter
                        self._input_state[box.name]["loaded"] = (box.value, box.input_box.text())
                else:
                    self._input_state[box.name]["loaded"] = None

    def load_inputs(self, vcl_bindings):
        """Load inputs from VCL bindings and create input boxes."""
        self._save_loaded_state()
        self._remove_all_boxes()

        try:
            inputs = vcl_bindings.resources()
            
            # Update input state with new definitions, preserving loaded state where possible
            new_input_state = {}
            for entry in inputs:
                name = entry.get("name")
                if name:
                    # Preserve existing loaded state if input still exists
                    existing_loaded = None
                    if name in self._input_state and self._input_state[name]["loaded"] is not None:
                        existing_loaded = self._input_state[name]["loaded"]
                    
                    new_input_state[name] = {
                        "definition": entry,
                        "loaded": existing_loaded
                    }
            self._input_state = new_input_state

            for name, state in self._input_state.items():
                definition = state["definition"]
                type_ = definition.get("tag")
                data_type = definition.get("typeText", None)
                if not name or not type_:
                    print(f"Skipping input entry with missing name or type: {definition}")
                    continue
                box = InputBox(name, type_, data_type=data_type)
                box.load_status_changed.connect(self._update_status)
                self.input_layout.addWidget(box)
                self.input_boxes.append(box)

                # Restore loaded state if it exists
                if state["loaded"] is not None:
                    value, display_text = state["loaded"]
                    if type_ in ["Network", "Dataset", "Variable"]:
                        box.path = value
                        box.input_box.setText(display_text)
                        box.input_box.setToolTip(value)  # Show full path on hover
                        box.is_loaded = True
                    elif type_ == "Parameter":
                        box.value = value
                        box.input_box.setText(display_text)
                        box.is_loaded = True

        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            self.error_callback(f"Error generating input boxes: {e}\n{tb_str}")

        self._update_status()

    def assign_inputs(self, vcl_bindings):
        """Assign inputs from InputBox widgets to the VCLBindings object."""
        assigned = []
        for box in self.input_boxes:
            if box.is_loaded:
                try:
                    if box.type == "Network":
                        vcl_bindings.set_network(box.name, box.path)
                    elif box.type == "Dataset":
                        vcl_bindings.set_dataset(box.name, box.path)
                    elif box.type == "Parameter":
                        vcl_bindings.set_parameter(box.name, box.value)
                    assigned.append(box.name)
                except Exception as e:
                    self.error_callback(f"Error assigning input {box.name}: {e}")
        return assigned

    def regenerate_input_boxes(self):
        """Regenerate input boxes, preserving any previously loaded values."""
        # Restore values from stored loaded state to the newly created boxes
        for box in self.input_boxes:
            if box.name in self._loaded_state:
                box.is_loaded = True
                state_data = self._loaded_state[box.name]
                if box.type in ["Network", "Dataset"]:
                    box.path, display_text = state_data
                    box.input_box.setText(display_text)
                    box.input_box.setToolTip(box.path)
                elif box.type == "Parameter":
                    box.value = state_data
                    box.input_box.setText(str(state_data))

        self._update_status()

    def get_loaded_inputs(self):
        """Get list of loaded input names"""
        return [box.name for box in self.input_boxes if box.is_loaded]

    def _update_status(self):
        """Update the status label with current input count."""
        loaded = len([box for box in self.input_boxes if box.is_loaded])
        total = len(self.input_boxes)
        self.status_label.setText(f"{loaded} / {total} inputs loaded")