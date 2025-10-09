from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QHBoxLayout, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem, QComboBox, QLineEdit, QCheckBox, QFrame, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class VariableBox(QWidget):
    """Widget for variable renderer selection"""
    
    renderer_changed = pyqtSignal(str, str)  # variable_name, renderer_path
    
    def __init__(self, variable_name, parent=None):
        super().__init__(parent)
        self.variable_name = variable_name
        self.renderer_path = None
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Variable name label
        name_label = QLabel(f"{variable_name}:")
        name_label.setMinimumWidth(80)
        name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(name_label)
        
        # Display box (read-only line edit like resource boxes)
        self.display_box = QLineEdit()
        self.display_box.setPlaceholderText("No renderer loaded")
        self.display_box.setReadOnly(True)
        layout.addWidget(self.display_box)
        
        # Renderer selection dropdown
        self.renderer_combo = QComboBox()
        self.renderer_combo.addItem("Default Renderers")
        self.renderer_combo.addItem("Load Custom Renderer...")
        self.renderer_combo.currentTextChanged.connect(self._on_renderer_changed)
        layout.addWidget(self.renderer_combo)
        
        layout.setSpacing(4)
        self.setLayout(layout)
    
    def _on_renderer_changed(self, selection):
        if selection == "Load Custom Renderer...":
            self._load_custom_renderer()
        elif selection == "Default Renderers":
            self._set_default_renderer()
    
    def _load_custom_renderer(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Load Renderer for {self.variable_name}", "", "Renderer modules (*.py);;All Files (*)"
        )
        if file_path:
            self.renderer_path = file_path
            self.display_box.setText(f"Custom: {file_path.split('/')[-1]}")
            self.display_box.setToolTip(file_path)
            self.renderer_combo.setCurrentText("Custom Renderer")
            self.renderer_changed.emit(self.variable_name, file_path)
    
    def _set_default_renderer(self):
        self.renderer_path = None
        self.display_box.setText("Default Renderers")
        self.display_box.setToolTip("Using default GSImage and Text renderers")
        self.renderer_changed.emit(self.variable_name, None)


class PropertyBox(QFrame):
    """Widget representing a single property with its variables."""
    
    property_toggled = pyqtSignal(str, bool)  # property_name, checked
    
    def __init__(self, prop_data, parent=None):
        super().__init__(parent)
        self.prop_data = prop_data
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Property checkbox and label
        prop_layout = QHBoxLayout()
        self.prop_checkbox = QCheckBox()
        self.prop_checkbox.setChecked(True)
        self.prop_checkbox.stateChanged.connect(self._on_property_toggled)
        
        prop_label = QLabel(f"{prop_data['name']} : {prop_data['type']}")
        prop_label.setWordWrap(True)
        prop_layout.addWidget(self.prop_checkbox)
        prop_layout.addWidget(prop_label, 1)
        prop_layout.addStretch()
        layout.addLayout(prop_layout)
        
        # Variables section
        variables = prop_data.get("quantifiedVariablesInfo", [])
        if variables:
            # Container for variable widgets with indentation
            self.var_container = QWidget()
            var_layout = QVBoxLayout(self.var_container)
            var_layout.setContentsMargins(20, 5, 5, 5)  # Left margin for indentation
            
            # Add a subtle separator
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            var_layout.addWidget(separator)
            
            var_title = QLabel("Variables:")
            var_title.setStyleSheet("font-weight: bold;")
            var_layout.addWidget(var_title)
            
            self.variable_widgets = {}
            for var_name in variables:
                var_widget = VariableBox(var_name)
                if parent and hasattr(parent, '_on_variable_renderer_changed'):
                    var_widget.renderer_changed.connect(parent._on_variable_renderer_changed)
                var_layout.addWidget(var_widget)
                self.variable_widgets[var_name] = var_widget
            
            layout.addWidget(self.var_container)
        
        self.setLayout(layout)
    
    def _on_property_toggled(self, state):
        checked = state == Qt.CheckState.Checked
        self.property_toggled.emit(self.prop_data['name'], checked)
    
    def is_checked(self):
        return self.prop_checkbox.isChecked()
    
    def set_checked(self, checked):
        self.prop_checkbox.setChecked(checked)


class PropertyView(QWidget):
    selection_changed = pyqtSignal(list)  # list of selected property ids

    def __init__(self, parent=None):
        super().__init__(parent)
        self._properties = []  # {"name": str, "type": str, "quantifiedVariablesInfo": list}
        self.property_widgets = {}
        
        # Create scrollable area for properties
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.content_widget)
        
        self.status_label = QLabel("0 / 0 selected")

        btn_all = QPushButton("All")
        btn_none = QPushButton("None")
        btn_all.clicked.connect(self.select_all)
        btn_none.clicked.connect(self.select_none)

        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        
        # Synchronization checkbox
        self.sync_checkbox = QCheckBox("Sync variables with same name")
        self.sync_checkbox.setToolTip("When enabled, changing a renderer for a variable will apply to all variables with the same name")
        btn_row.addWidget(self.sync_checkbox)
        
        btn_row.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addLayout(btn_row)
        layout.addWidget(self.scroll_area)

    def load_properties(self, props):
        """
        Loads a list of properties into the widget. Properties are a list of dictionaries in the form:
        {"name": str, "type": str, "quantifiedVariablesInfo": list}
        """
        self._properties = props
        self.property_widgets = {}
        
        # Clear existing widgets
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create property widgets
        for prop in props:
            prop_widget = PropertyBox(prop, self)
            prop_widget.property_toggled.connect(self._on_property_toggled)
            self.content_layout.addWidget(prop_widget)
            self.property_widgets[prop['name']] = prop_widget
        
        self._update_status()
        self._emit_selection()
    
    def _on_property_toggled(self, prop_name, checked):
        """Handle when a property checkbox is toggled."""
        self._update_status()
        self._emit_selection()
    
    def _on_variable_renderer_changed(self, variable_name, renderer_path):
        """Handle when a variable's renderer selection changes."""
        # Store the renderer path for this variable
        if not hasattr(self, '_variable_renderers'):
            self._variable_renderers = {}
        self._variable_renderers[variable_name] = renderer_path
        
        # If synchronization is enabled, update all variables with the same name
        if self.sync_checkbox.isChecked():
            self._sync_variable_renderer(variable_name, renderer_path)
    
    def _sync_variable_renderer(self, variable_name, renderer_path):
        """Update all variables with the same name to use the given renderer."""
        for prop_widget in self.property_widgets.values():
            if hasattr(prop_widget, 'variable_widgets') and variable_name in prop_widget.variable_widgets:
                var_widget = prop_widget.variable_widgets[variable_name]
                # Update the widget's renderer without triggering the signal again
                var_widget.renderer_path = renderer_path
                if renderer_path:
                    var_widget.display_box.setText(f"Custom: {renderer_path.split('/')[-1]}")
                    var_widget.display_box.setToolTip(renderer_path)
                    var_widget.renderer_combo.setCurrentText("Custom Renderer")
                else:
                    var_widget.display_box.setText("Default Renderers")
                    var_widget.display_box.setToolTip("Using default GSImage and Text renderers")
                    var_widget.renderer_combo.setCurrentText("Default Renderers")

    def selected_properties(self):
        """Return list of selected property names"""
        return [name for name, widget in self.property_widgets.items() if widget.is_checked()]

    def select_all(self):
        self._set_all(True)

    def select_none(self):
        self._set_all(False)

    def _set_all(self, checked):
        for widget in self.property_widgets.values():
            widget.set_checked(checked)
        self._update_status()
        self._emit_selection()

    def _emit_selection(self):
        self._update_status()
        self.selection_changed.emit(self.selected_properties())

    def _update_status(self):
        total = len(self.property_widgets)
        selected = len(self.selected_properties())
        self.status_label.setText(f"{selected} / {total} selected")

    @property
    def property_items(self):
        return [(name, widget) for name, widget in self.property_widgets.items()]
    
    def get_variable_renderers(self):
        """Return a dict of variable_name -> renderer_path for all variables."""
        if not hasattr(self, '_variable_renderers'):
            self._variable_renderers = {}
        return self._variable_renderers.copy()