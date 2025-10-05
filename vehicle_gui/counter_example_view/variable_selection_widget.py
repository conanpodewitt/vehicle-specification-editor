from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

class VariableWidget(QWidget):
    qvar_clicked = pyqtSignal(str, str) # emits (property_name, quantified_variable)

    def __init__(self, property_name, quantified_vars, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Property name label
        label = QLabel(f"<b>{property_name}</b>")
        layout.addWidget(label)

        # Quantified variables as buttons
        for quantified_var in quantified_vars:
            button = QPushButton(quantified_var)
            button.clicked.connect(lambda _, i=property_name, s=quantified_var: self.qvar_clicked.emit(i, s))
            layout.addWidget(button)

        self.setLayout(layout)

class PropertyListQV(QWidget):
    def __init__(self, data:dict, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.list_widget = QListWidget()

        for property_name, quantified_var_names in data:
            property_group = QListWidgetItem()
            property_group.setFlags(Qt.NoItemFlags)
            qv_widget = VariableWidget(property_name, quantified_var_names)
            qv_widget.qvar_clicked.connect(self.handleQuantifiedVariablesClick)
            property_group.setSizeHint(qv_widget.sizeHint())
            self.list_widget.addItem(property_group)
            self.list_widget.setItemWidget(property_group, qv_widget)

        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def handleQuantifiedVariablesClick(self, item_name, QuantifiedVariables_label):
        print(f"Selected: ({item_name}, {QuantifiedVariables_label})")