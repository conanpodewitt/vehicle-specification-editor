from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QLabel, QTextEdit, QStackedLayout, QPushButton, QFileDialog, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import numpy as np
from ui.counter_examples.render_counter_examples import array_to_pixmap
from ui.counter_examples.decode_counter_examples import decode_counter_examples
import json

class CounterExampleWidget(QWidget):
    def __init__(self, mode="image", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.data = {}
        self.keys = []
        self.current_index = 0

        self.name_label = QLabel("No data loaded")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Previous button (◀)
        self.prev_button = QPushButton("◀")
        self.prev_button.setFixedSize(32, 32)
        self.prev_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
        """)

        # Next button (▶)
        self.next_button = QPushButton("▶")
        self.next_button.setFixedSize(32, 32)
        self.next_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
        """)

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.name_label)
        nav_layout.addWidget(self.next_button)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        self.stack = QStackedLayout()
        self.stack.addWidget(self.image_label)
        self.stack.addWidget(self.text_edit)

        main_layout = QVBoxLayout()
        main_layout.addLayout(nav_layout)
        main_layout.addLayout(self.stack)
        self.setLayout(main_layout)

        self.set_mode(mode)

        self.prev_button.clicked.connect(self.go_previous)
        self.next_button.clicked.connect(self.go_next)

    def set_mode(self, mode: str):
        self.mode = mode
        self.stack.setCurrentIndex(0 if mode == "image" else 1)
        self.update_display()

    def set_data(self, data: dict):
        self.data = data
        self.keys = list(data.keys())
        self.current_index = 0
        self.update_display()

    def update_display(self):
        if not self.keys:
            self.name_label.setText("No data")
            self.prev_button.hide()
            self.next_button.hide()
            return

        self.prev_button.show()
        self.next_button.show()

        key = self.keys[self.current_index]
        shape = list(self.data[key]["shape"])
        self.name_label.setText(f"{key.strip('"')} {shape}")
        content = self.data[key]

        if self.mode == "image":
            try:
                # Attempt to render image
                image_array = np.squeeze(content["data"])
                qimage = array_to_pixmap(image_array)
                self.image_label.setPixmap(qimage)
                self.stack.setCurrentIndex(0)  # Show image view
            except Exception as e:
                # Fallback to text view
                self.text_edit.setText("image rendering requires a 2D tensor")
                self.stack.setCurrentIndex(1)  # Show text view
        elif self.mode == "text":
            self.text_edit.setText(json.dumps(content["data"], default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o), indent=2))
        elif self.mode == "json":
            self.text_edit.setText(json.dumps(content, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o), indent=2))

    def go_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()

    def go_next(self):
        if self.current_index < len(self.keys) - 1:
            self.current_index += 1
            self.update_display()

class CounterExampleViewer(QWidget):
    def __init__(self, mode="image", parent=None):
        super().__init__(parent)
        self.mode = mode

        self.layout = QVBoxLayout()

        # Horizontal controls
        control_layout = QHBoxLayout()

        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["image", "text", "json"])
        self.mode_selector.setCurrentText(self.mode)
        self.mode_selector.currentTextChanged.connect(self.change_mode)
        self.mode_selector.setFixedWidth(100)
        control_layout.addWidget(self.mode_selector)

        self.folder_label = QLabel("No folder selected")
        control_layout.addWidget(self.folder_label)

        self.folder_button = QPushButton()
        self.folder_button.setIcon(QIcon.fromTheme("folder"))
        self.folder_button.setFixedSize(32, 32)
        # self.folder_button.setStyleSheet("QPushButton { border: none; background-color: transparent; }")
        self.folder_button.clicked.connect(self.select_folder)
        control_layout.addWidget(self.folder_button)

        self.layout.addLayout(control_layout)

        # Viewer widget
        self.content_widget = CounterExampleWidget(mode=self.mode)
        self.layout.addWidget(self.content_widget)

        self.setLayout(self.layout)

    def change_mode(self, new_mode):
        self.mode = new_mode
        self.content_widget.set_mode(new_mode)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_label.setText(folder)
            self.load_counter_examples_from_folder(folder)

    def load_counter_examples_from_folder(self, folder):
        counter_examples_json = decode_counter_examples(folder)
        self.content_widget.set_data(counter_examples_json)