from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit, QCheckBox, QFrame, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal


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