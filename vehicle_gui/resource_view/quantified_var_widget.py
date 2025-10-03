from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import (QVBoxLayout, QLabel, QFrame, 
                           QSizePolicy, QHBoxLayout, QComboBox)

# usage : box = QuantifiedVarRenderWidget("property_name", "var_name", ["opt1", "opt2", "opt3"])
#         box.get_value() -> "opt1"
#         box.set_value("opt2")
#         box.get_property() -> "property_name"
class QuantifiedVarRenderWidget(QFrame):
    def __init__(self, property_name, var_name, options=None):
        super().__init__()
        self.setObjectName("QuantifiedVarRenderWidget")
        layout = QHBoxLayout()
        
        self.property_name = property_name
        self.var_name = var_name
        self.options = options or []
        
        # Variable label
        var_label = QLabel(f"{var_name}")
        label_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        label_font.setPointSize(10)
        var_label.setFont(label_font)
        layout.addWidget(var_label)
        
        # Dropdown for options
        self.dropdown = QComboBox()
        self.dropdown.addItems(self.options)
        layout.addWidget(self.dropdown)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setLayout(layout)
    
    def get_value(self):
        """Get selected value"""
        return self.dropdown.currentText()
    
    def set_value(self, value):
        """Set dropdown value"""
        self.dropdown.setCurrentText(value)
        
    def get_property(self):
        """Get the property name this box was created for"""
        return self.property_name
        
    def get_var_name(self):
        """Get the variable name this box represents"""
        return self.var_name