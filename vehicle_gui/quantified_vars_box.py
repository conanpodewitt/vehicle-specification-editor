from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import (QVBoxLayout, QLabel, QFrame, 
                           QSizePolicy, QHBoxLayout, QComboBox)

# usage : box = QuantifiedVarsBox("property_name", ["var1", "var2"], ["opt1", "opt2", "opt3"])
#         box.get_values() -> {"var1": "opt1", "var2": "opt2"}
#         box.set_values({"var1": "opt2", "var2": "opt1"})
class QuantifiedVarsBox(QFrame):
    def __init__(self, property_name, quant_vars=None, options=None):
        super().__init__()
        self.setObjectName("QuantifiedVarsBox")
        layout = QVBoxLayout()
        title = QLabel(f"Property: {property_name}")
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(11)
        mono.setWeight(QFont.Weight.Bold)
        title.setFont(mono)
        layout.addWidget(title)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.property_name = property_name
        self.quant_vars = quant_vars or []
        self.options = options or []
        self.selected = {}
        
        
        # Add quantified variable rows
        for attr in self.quant_vars:
            attr_layout = QHBoxLayout()
            
            # quantified variable label
            attr_label = QLabel(f"{attr}")
            label_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
            label_font.setPointSize(10)
            attr_label.setFont(label_font)
            attr_layout.addWidget(attr_label)
            
            # Dropdown for the quantified variable rendering option
            dropdown = QComboBox()
            dropdown.addItems(self.options)
            self.selected[attr] = dropdown
            attr_layout.addWidget(dropdown)
            
            layout.addLayout(attr_layout)

        self.setLayout(layout)
    
    def get_values(self):
        """Get dictionary of selected rendering for quantified variables"""
        return {attr: widget.currentText()
                for attr, widget in self.selected.items()}
    
    def set_values(self, values):
        """Set dropdown values from dictionary"""
        for attr, value in values.items():
            if attr in self.selected:
                self.selected[attr].setCurrentText(value)