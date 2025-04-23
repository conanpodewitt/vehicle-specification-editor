
import os
import traceback

from PyQt6.QtWidgets import (QApplication, QMainWindow, QSplitter, QTextEdit,
                           QVBoxLayout, QPushButton, QWidget, QLabel, QFileDialog,
                           QHBoxLayout, QStatusBar, QProgressBar, QFrame, QMessageBox,
                           QComboBox, QPlainTextEdit, QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.CodeEditor import CodeEditor
from ui.ResourceBox import ResourceBox
from ui.VCLBindings import VCLBindings
from vehicle_lang import verify, VERSION

from pygments.lexers import get_lexer_by_name
from pygments import highlight
from pygments.formatters import NullFormatter

from superqt.utils import CodeSyntaxHighlight

class VCLEditor(QMainWindow):
    """Vehicle Specification Editor"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize paths
        self.resource_boxes = []
        self.vcl = VCLBindings()
        self.vcl_path = None
        
        # Set window properties
        self.setWindowTitle("Vehicle Editor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create main window widgets
        self.init_ui()
    

    def init_ui(self):
        """Initialize UI"""
        # Create main window widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Create top toolbar
        top_toolbar = QHBoxLayout()
        
        # New, Open, Save buttons for VCL files
        file_buttons_layout = QHBoxLayout()
        new_button = QPushButton("New")
        new_button.clicked.connect(self.new_file)
        file_buttons_layout.addWidget(new_button)
        
        open_button = QPushButton("Open")
        open_button.clicked.connect(self.open_file)
        file_buttons_layout.addWidget(open_button)
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_file)
        file_buttons_layout.addWidget(save_button)
        
        top_toolbar.addLayout(file_buttons_layout)
        top_toolbar.addStretch(1)

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

        self.verify_button = QPushButton("Verify")
        self.verify_button.clicked.connect(self.verify_spec)
        output_layout.addWidget(self.verify_button)
        
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
        self.editor.setFont(QFont("Consolas", 11))
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

        # Create a widget to hold the resource boxes
        scroll_content = QWidget()
        self.resource_layout = QVBoxLayout(scroll_content)
        scroll_content.setLayout(self.resource_layout)
        scroll_area.setWidget(scroll_content)
        
        # Use regular QTextEdit for the output area
        self.output_box = QTextEdit()
        self.output_box.setFont(QFont("Consolas", 11))
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
        self.vcl.clear()
    

    def open_file(self):
        """Open an existing file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Vehicle Specification", "", "VCL Files (*.vcl);;All Files (*)"
        )
        if not file_path:
            return

        file_open_success = True

        try:
            with open(file_path, 'r') as file:
                self.editor.setPlainText(file.read())
            self.vcl_path = file_path
            self.file_path_label.setText(f"File: {os.path.basename(file_path)}")
            self.status_bar.showMessage(f"Opened: {file_path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "File Open Error", f"Could not open file: {str(e)}")
            file_open_success = False

        if file_open_success:
            self.vcl.vcl_path = file_path

    
    def save_file(self):
        """Save the current file"""
        if not self.vcl_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Vehicle Specification", "", "VCL Files (*.vcl);;All Files (*)"
            )
            if not file_path:
                return
            self.vcl_path = file_path
        
        try:
            with open(self.vcl_path, 'w') as file:
                file.write(self.editor.toPlainText())
            self.file_path_label.setText(f"File: {os.path.basename(self.vcl_path)}")
            self.status_bar.showMessage(f"Saved: {self.vcl_path}", 3000)

        except Exception as e:
            QMessageBox.critical(self, "File Save Error", f"Could not save file: {str(e)}")

        
    def set_verifier(self):
        """Set the verifier path"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Marabou Verifier", "", "Marabou Verifier (Marabou*);;All Files (*)"
        )
        if not file_path:
            return

        self.vcl.verifier_path = file_path
        self.verifier_label.setText(f"Verifier: {os.path.basename(file_path)}")
        self.status_bar.showMessage(f"Verifier set: {file_path}", 3000)
    

    def compile_spec(self):
        """Compile the specification"""
        if not self.save_before_operation():
            return
        
        self.status_bar.showMessage("Compiling...", 1000)
        self.compile_button.setEnabled(False)

        # Execute compilation
        try:
            result = VCLBindings.compile()
            self.output.clear()
            self.output.setPlainText(result)

        except Exception as e:
            error_msg = f"Exception during verification:\n{str(e)}\n\n{traceback.format_exc()}"
            self.output.setPlainText(error_msg)
            self.status_bar.showMessage("Verification error", 3000)
        
        finally:
            self.compile_button.setEnabled(True)
        
        self.output.clear()
        self.output.setPlainText(result)
    

    def verify_spec(self):
        """Verify the specification"""
        if not self.save_before_operation():
           return
        
        if not self.vcl.verifier_path:
           QMessageBox.warning(self, "Verification Error", "Please set the verifier path first")
           return
        
        if not self.are_resources_loaded():
            QMessageBox.warning(self, "Resource Error", "Please load all required resources before verification")
            return
        
        self.status_bar.showMessage("Verifying...", 0)
        self.verify_button.setEnabled(False)
        
        # Execute verification
        try:
            result = verify(self.vcl_path)  
            self.output.clear()
            self.output.setPlainText(result)
            
            if "Error" in result or "error" in result:
                self.status_bar.showMessage("Verification failed", 3000)
            else:
                self.status_bar.showMessage("Verification successful", 3000)
                
        except Exception as e:
            error_msg = f"Exception during verification:\n{str(e)}\n\n{traceback.format_exc()}"
            self.output.setPlainText(error_msg)
            self.status_bar.showMessage("Verification error", 3000)
        
        finally:
            self.verify_button.setEnabled(True)
    

    def save_before_operation(self):
        """Save file before operation"""
        if not self.vcl_path: # TODO: Check if there are unsaved changes in the editor
            reply = QMessageBox.question(
                self, "Save File", "You need to save the file before this operation. Save now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.save_file()
                return bool(self.vcl_path)
            else:
                return False
        
        # Save file to ensure using the latest content
        with open(self.vcl_path, 'w') as file:
            file.write(self.editor.toPlainText())


    def generate_resource_boxes(self, resource_json):
        # Clear old boxes
        for box in self.resource_boxes:
            box.deleteLater()

        self.resource_boxes.clear()

        # Add new boxes from example json
        for entry in resource_json:
            name = entry.get("name")
            type_ = entry.get("type")
            box = ResourceBox(name, type_)
            self.resource_layout.addWidget(box)
            self.resource_boxes.append(box)

    
    def are_resources_loaded(self):
        """Check if all resources are loaded"""
        return all(box.is_loaded for box in self.resource_boxes)


    def show_version(self):
        """Show the current version of the application"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Version", f"Current version: {VERSION}")
