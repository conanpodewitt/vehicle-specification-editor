import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QLabel, QLineEdit, QFrame, QFileDialog, QMessageBox, QSizePolicy

class ResourceBox(QFrame):
    def __init__(self, name, type_, data_type=None):
        super().__init__()
        self.setObjectName("ResourceBox")
        layout = QVBoxLayout()
        title = QLabel(f"{type_.capitalize()}: {name}")
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

        if type_ == "network":
            self.view_btn = QPushButton("View Network")
            self.load_btn = QPushButton("Load Network")
            self.view_btn.clicked.connect(lambda: print(f"Viewing network: {name}"))
            self.load_btn.clicked.connect(self.set_network)
            layout.addWidget(self.view_btn)
            layout.addWidget(self.load_btn)

        elif type_ == "dataset":
            self.load_btn = QPushButton("Load Dataset")
            self.load_btn.clicked.connect(self.set_dataset)
            layout.addWidget(self.load_btn)

        elif type_ == "parameter":
            # TODO: Fix `vehicle list resources` to not show inferred parameters
            self.is_loaded = True   # Parameters are considered loaded by default since they may be optional
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
    
    def set_network(self):
        """Open a network path"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Vehicle Specification", "", "ONNX Files (*.onnx);;All Files (*)"
        )
        if not file_path:
            return
        self.path = file_path
        self.load_btn.setText(f"Loaded: {os.path.basename(file_path)}")
        self.is_loaded = True

    def set_dataset(self):
        """Open a dataset path"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Dataset", "", "All Files (*)"
        )
        if not file_path:
            return
        self.path = file_path
        self.load_btn.setText(f"Loaded: {os.path.basename(file_path)}")
        self.is_loaded = True
    
    def set_value(self):
        value = self.input_box.text()
        """Set the value of the parameter"""
        if self.data_type == "Rat":
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