import os
from PyQt6.QtWidgets import QMainWindow, QTextEdit, QVBoxLayout, QPushButton, QWidget, QLabel, QFileDialog, QHBoxLayout, QStatusBar, QMessageBox, QScrollArea, QSizePolicy, QToolBar
from PyQt6.QtCore import Qt
from PyQt6.QtCore import (QRunnable, pyqtSlot)
from PyQt6.QtGui import QFontDatabase, QIcon
from ui.code_editor import CodeEditor
from ui.resource_box import ResourceBox
from ui.vcl_bindings import VCLBindings
from vehicle_lang import VERSION

from superqt.utils import CodeSyntaxHighlight

class VCLEditor(QMainWindow):
    """Vehicle Specification Editor"""
    def __init__(self):
        super().__init__()
        # Initialize paths
        self.resource_boxes = []
        self.vcl_bindings = VCLBindings()
        self.vcl_path = None
        # Set window properties
        self.setWindowTitle("Vehicle Editor")
        self.setGeometry(100, 100, 1200, 800)
        # Create main window widgets
        self.show_ui()
    
    def show_ui(self):
        """Initialize UI"""
        # Create real file toolbar
        file_toolbar = QToolBar("File")
        self.addToolBar(file_toolbar)
        file_toolbar.addAction(QIcon.fromTheme("document-new"),  "New",  self.new_file)
        file_toolbar.addAction(QIcon.fromTheme("document-open"), "Open", self.open_file)
        file_toolbar.addAction(QIcon.fromTheme("document-save"), "Save", self.save_file)
        # Create main window widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        # Create top toolbar layout
        top_toolbar = QHBoxLayout()
        # Add set verifier button
        verifier_button = QPushButton("Set Verifier")
        verifier_button.clicked.connect(self.set_verifier)
        top_toolbar.addWidget(verifier_button)
        top_toolbar.addStretch(1)
        # Add compile and verify buttons
        output_layout = QHBoxLayout()
        self.compile_button = QPushButton("Compile")
        self.compile_button.clicked.connect(self.compile_spec)
        output_layout.addWidget(self.compile_button)
        # Add verify button
        self.verify_button = QPushButton("Verify")
        self.verify_button.clicked.connect(self.verify_spec)
        output_layout.addWidget(self.verify_button)
        # Add clear output button
        top_toolbar.addLayout(output_layout)
        top_toolbar.addStretch(1)
        main_layout.addLayout(top_toolbar)
        # Create main edit area
        main_edit_layout = QHBoxLayout()
        # Create left editor
        left_layout = QVBoxLayout()
        left_label = QLabel("Editor")
        left_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(left_label)
        # Replace QTextEdit with CodeEditor
        self.editor = CodeEditor()
        # use a monospaced font for typed text
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(11)
        self.editor.setFont(mono)
        self.editor.setPlaceholderText("Enter your Vehicle specification here...")
        # Add syntax highlighting
        self.highlighter = CodeSyntaxHighlight(self.editor.document(), "external", "vs")
        left_layout.addWidget(self.editor)
        main_edit_layout.addLayout(left_layout, 3)  # Left side takes 3/5
        # Create right output area
        right_layout = QVBoxLayout()
        right_label = QLabel("Additonal Inputs")
        right_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(right_label)
        # Create scroll area for resource boxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        # Only show vertical scrollbar when needed
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Create a widget to hold the resource boxes
        scroll_content = QWidget()
        self.resource_layout = QVBoxLayout(scroll_content)
        self.resource_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_content.setLayout(self.resource_layout)
        scroll_area.setWidget(scroll_content)
        # Use regular QTextEdit for the output area
        self.output_box = QTextEdit()
        mono_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono_font.setPointSize(11)
        self.output_box.setFont(mono_font)
        self.output_box.setReadOnly(True)
        self.output_box.setPlaceholderText("....")
        # Set size policy for scroll area and output box
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.output_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_area.setMinimumWidth(200)
        right_layout.addWidget(scroll_area)
        right_layout.addWidget(self.output_box)
        main_edit_layout.addLayout(right_layout, 2)  # Right side takes 2/5
        main_layout.addLayout(main_edit_layout)
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        # Add file path display
        self.file_path_label = QLabel("No file opened")
        self.status_bar.addWidget(self.file_path_label, 1)
        self.verifier_label = QLabel("Verifier not set")
        self.status_bar.addPermanentWidget(self.verifier_label)
        # Create bottom toolbar
        bottom_layout = QHBoxLayout()
        version_button = QPushButton("Version")
        version_button.clicked.connect(self.show_version)
        bottom_layout.addWidget(version_button)
        bottom_layout.addStretch(1)
        main_layout.addLayout(bottom_layout)

    def new_file(self):
        """Create a new file"""
        self.editor.clear()
        self.output_box.clear()
        self.file_path_label.setText("No file opened")
        self.status_bar.showMessage("New file created", 3000)
        self.vcl_path = None
        self.vcl_bindings.clear()
    
    def open_file(self):
        """Open an existing file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Vehicle Specification", "", "VCL Files (*.vcl);;All Files (*)"
        )
        if not file_path:
            return
        with open(file_path, 'r') as file:
            self.editor.setPlainText(file.read())
        self.status_bar.showMessage(f"Opened: {file_path}", 3000)
        self.set_vcl_path(file_path)
    
    def save_file(self):
        """Save the current file"""
        file_path = self.vcl_path
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Vehicle Specification", "", "VCL Files (*.vcl);;All Files (*)"
            )
            if not file_path:
                return
        with open(self.vcl_path, 'w') as file:
            file.write(self.editor.toPlainText())
        self.status_bar.showMessage(f"Saved: {self.vcl_path}", 3000)
        self.set_vcl_path(file_path)

    def set_verifier(self):
        """Set the verifier path"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Marabou Verifier", "", "Marabou Verifier (Marabou*);;All Files (*)"
        )
        if not file_path:
            return
        self.vcl_bindings.verifier_path = file_path
        self.verifier_label.setText(f"Verifier: {os.path.basename(file_path)}")
        self.status_bar.showMessage(f"Verifier set: {file_path}", 3000)
    
    def compile_spec(self):
        """Compile the specification"""
        backgroundworker.compile_spec(self)
        # if not self.save_before_operation():
        #     return
        # self.assign_resources()
        # if not all(box.is_loaded for box in self.resource_boxes):
        #     QMessageBox.warning(self, "Resource Error", "Please load all resources before verification")
        #     return
        # self.status_bar.showMessage("Compiling...", 1000)
        # self.compile_button.setEnabled(False)
        # # Execute compilation
        # result = self.vcl_bindings.compile()
        # self.output_box.clear()
        # self.output_box.setPlainText(result)
        # self.compile_button.setEnabled(True)
    
    def verify_spec(self):
        """Verify the specification"""
        if not self.save_before_operation():
           return
        if not self.vcl_bindings.verifier_path:
           QMessageBox.warning(self, "Verification Error", "Please set the verifier path first")
           return
        self.assign_resources()
        if not all(box.is_loaded for box in self.resource_boxes):
            QMessageBox.warning(self, "Resource Error", "Please load all resources before verification")
            return
        self.status_bar.showMessage("Verifying...", 0)
        self.verify_button.setEnabled(False)
        # Execute verification
        result = self.vcl_bindings.verify() 
        self.output_box.clear()
        self.output_box.setPlainText(result)
        self.verify_button.setEnabled(True)

    def save_before_operation(self):
        """Save file before operation"""
        file_saved = bool(self.vcl_path)
        if not file_saved:
            reply = QMessageBox.question(
                self, "Save File", "You need to save the file before this operation. Save now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_file()
                file_saved = bool(self.vcl_path)
        else:
            # Write the latest changes to the file
            with open(self.vcl_path, 'w') as file:
                file.write(self.editor.toPlainText())
        return file_saved

    def generate_resource_boxes(self):
        # Clear old boxes
        for box in self.resource_boxes:
            box.deleteLater()
        self.resource_boxes.clear()
        # Add new boxes by calling 'vehicle list resources'
        for entry in self.vcl_bindings.resources():
            name = entry.get("entityName")
            type_ = entry.get("entitySort").lstrip("@")
            data_type = entry.get("entityType", None)    
            box = ResourceBox(name, type_, data_type=data_type)
            self.resource_layout.addWidget(box)
            self.resource_boxes.append(box)

    def assign_resources(self):
        """Assign resources to the VCLBindings"""
        for box in self.resource_boxes:
            if box.is_loaded:
                if box.type == "network":
                    self.vcl_bindings.set_network(box.name, box.path)
                elif box.type == "dataset":
                    self.vcl_bindings.set_dataset(box.name, box.path)
                elif box.type == "parameter":
                    self.vcl_bindings.set_parameter(box.name, box.value)
            else:
                QMessageBox.warning(self, "Resource Error", f"Resource {box.name} is not loaded")

    def show_version(self):
        """Show the current version of the application"""
        QMessageBox.information(self, "Version", f"Current version: {VERSION}")
    
    def set_vcl_path(self, path):
        """Set the VCL path"""
        self.vcl_bindings.clear()
        self.vcl_bindings.vcl_path = path
        self.vcl_path = path
        self.file_path_label.setText(f"File: {os.path.basename(path)}")
        self.generate_resource_boxes()

class backgroundworker(QRunnable):
    @pyqtSlot()
    def compile_spec(self):
        """Compile the specification"""
        if not self.save_before_operation():
            return
        self.assign_resources()
        if not all(box.is_loaded for box in self.resource_boxes):
            QMessageBox.warning(self, "Resource Error", "Please load all resources before verification")
            return
        self.status_bar.showMessage("Compiling...", 1000)
        self.compile_button.setEnabled(False)
        # Execute compilation
        result = self.vcl_bindings.compile()
        self.output_box.clear()
        self.output_box.setPlainText(result)
        self.compile_button.setEnabled(True)