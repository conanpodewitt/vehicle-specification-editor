import sys
import json
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QVBoxLayout, QPushButton, QLabel, QLineEdit, QFrame
)


class CurvedBox(QFrame):
    def __init__(self, name, type_):
        super().__init__()
        self.setObjectName("ResourceBox")
        layout = QVBoxLayout()
        title = QLabel(f"{type_.capitalize()}: {name}")
        title.setFont(QFont("Consolas", 11, weight=QFont.Weight.Bold))
        layout.addWidget(title)

        if type_ == "network":
            view_btn = QPushButton("View Network")
            load_btn = QPushButton("Load Network")
            view_btn.clicked.connect(lambda: print(f"Viewing network: {name}"))
            load_btn.clicked.connect(lambda: print(f"Loading network: {name}"))
            layout.addWidget(view_btn)
            layout.addWidget(load_btn)

        elif type_ == "dataset":
            load_path_btn = QPushButton("Load Dataset")
            load_path_btn.clicked.connect(lambda: print(f"Loading dataset: {name}"))
            layout.addWidget(load_path_btn)

        elif type_ == "parameter":
            input_box = QLineEdit()
            input_box.setPlaceholderText("Enter value")
            input_box.textChanged.connect(lambda val: print(f"Parameter {name} set to: {val}"))
            layout.addWidget(input_box)

        self.setLayout(layout)