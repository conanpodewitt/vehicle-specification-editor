import os
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QLabel, QLineEdit, QFrame, QFileDialog, QMessageBox, QSizePolicy, QHBoxLayout

class ResourceBox(QFrame):
    def __init__(self, name, type_, data_type=None):
        super().__init__()
        self.setObjectName("ResourceBox")
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