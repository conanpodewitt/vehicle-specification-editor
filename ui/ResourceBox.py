import sys
import json
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QVBoxLayout, QPushButton, QLabel, QLineEdit, QFrame, QFileDialog, QMessageBox
)


class ResourceBox(QFrame):
    def __init__(self, name, type_):
        super().__init__()
        self.setObjectName("ResourceBox")
        layout = QVBoxLayout()
        title = QLabel(f"{type_.capitalize()}: {name}")
        title.setFont(QFont("Consolas", 11, weight=QFont.Weight.Bold))
        layout.addWidget(title)

        self.is_loaded = False

        if type_ == "network":
            view_btn = QPushButton("View Network")
            load_btn = QPushButton("Load Network")
            view_btn.clicked.connect(lambda: print(f"Viewing network: {name}"))
            load_btn.clicked.connect(self.set_path)
            layout.addWidget(view_btn)
            layout.addWidget(load_btn)

        elif type_ == "dataset":
            load_path_btn = QPushButton("Load Dataset")
            load_path_btn.clicked.connect(self.set_path)
            layout.addWidget(load_path_btn)

        elif type_ == "parameter":
            input_box = QLineEdit()
            input_box.setPlaceholderText("Enter value")
            input_box.textChanged.connect(self.set_value)
            layout.addWidget(input_box)

        self.setLayout(layout)

    
    def set_path(self):
        """Open a network path"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Vehicle Specification", "", "ONNX Files (*.onnx);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r') as file:
                self.editor.setPlainText(file.read())
            self.path = file_path
            self.is_loaded = True
        except Exception as e:
            QMessageBox.critical(self, "File Open Error", f"Could not open file: {str(e)}")

    
    def set_value(self, value):
        """Set the value of the parameter"""
        self.value = value
        self.is_loaded = True