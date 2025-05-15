import os
import traceback # For error signal
from PyQt6.QtWidgets import (QMainWindow, QTextEdit, QVBoxLayout, QPushButton, QWidget,
                             QLabel, QFileDialog, QHBoxLayout, QStatusBar, QMessageBox,
                             QScrollArea, QSizePolicy, QToolBar, QFrame)
from PyQt6.QtCore import Qt, QRunnable, pyqtSlot, QObject, pyqtSignal, QThreadPool
from PyQt6.QtGui import QFontDatabase, QIcon
from ui.code_editor import CodeEditor
from ui.resource_box import ResourceBox
from ui.vcl_bindings import VCLBindings
from vehicle_lang import VERSION 
from superqt.utils import CodeSyntaxHighlight


# --- Worker and Signals ---
class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """
    finished = pyqtSignal()
    error = pyqtSignal(str, str)  # Emits title and message for an error dialog
    result = pyqtSignal(str)      # Emits the string output of the operation


class Worker(QRunnable):
    """
    Generic worker thread that runs a function and emits signals.
    """
    def __init__(self, func_to_run, *args, **kwargs):
        super().__init__()
        self.func_to_run = func_to_run
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """
        Execute the worker function and emit appropriate signals.
        """
        try:
            output = self.func_to_run(*self.args, **self.kwargs)
            self.signals.result.emit(output)
        except Exception as e:
            tb_str = traceback.format_exc()
            print(f"Worker error: {e}\n{tb_str}") # Log for debugging
            self.signals.error.emit("Operation Failed", f"An error occurred: {e}\nDetails:\n{tb_str}")
        finally:
            self.signals.finished.emit()


class VCLEditor(QMainWindow):
    """Vehicle Specification Editor"""
    def __init__(self):
        super().__init__()
        self.resource_boxes = []
        self.vcl_bindings = VCLBindings()
        self.vcl_path = None
        self.setWindowTitle("Vehicle Specification Editor")
        self.setGeometry(100, 100, 1400, 800)

        # Initialize QThreadPool for managing worker threads
        self.thread_pool = QThreadPool()

        self.current_operation = None # Tracks 'compile' or 'verify'
        self.show_ui()

    def show_ui(self):
        """Initialize UI"""
        # Create menu bar -----------------------------------------------------
        file_toolbar = QToolBar("File")
        self.addToolBar(file_toolbar)
        file_toolbar.setMovable(False)
        file_toolbar.setFloatable(False)
        file_toolbar.addAction(QIcon.fromTheme("document-new"), "New", self.new_file)
        file_toolbar.addAction(QIcon.fromTheme("document-open"), "Open", self.open_file)
        file_toolbar.addAction(QIcon.fromTheme("document-save"), "Save", self.save_file)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        file_toolbar.addWidget(spacer)

        verifier_btn = QPushButton(QIcon.fromTheme("computer"), "Set Verifier")
        verifier_btn.clicked.connect(self.set_verifier)
        file_toolbar.addWidget(verifier_btn)

        self.compile_button = QPushButton(QIcon.fromTheme("scanner"), "Compile")
        self.compile_button.clicked.connect(self.compile_spec)
        file_toolbar.addWidget(self.compile_button)

        self.verify_button = QPushButton(QIcon.fromTheme("media-playback-start"), "Verify")
        self.verify_button.clicked.connect(self.verify_spec)
        file_toolbar.addWidget(self.verify_button)

        # Create main window widget 
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Create main edit area 
        main_edit_layout = QHBoxLayout()

        # Create left editor 
        left_layout = QVBoxLayout()
        left_label = QLabel("Editor")
        left_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = left_label.font()
        font.setPointSize(14)
        left_label.setFont(font)
        left_layout.addWidget(left_label)
        self.editor = CodeEditor()
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(14)
        self.editor.setFont(mono)
        self.editor.setPlaceholderText("Enter your Vehicle specification here...")
        self.highlighter = CodeSyntaxHighlight(self.editor.document(), "external", "vs")
        left_layout.addWidget(self.editor)
        main_edit_layout.addLayout(left_layout, 3)

        # Create right area for resource boxes and output
        right_layout = QVBoxLayout()
        right_label = QLabel("Additional Input") # Corrected typo
        right_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = right_label.font()
        font.setPointSize(14)
        right_label.setFont(font)
        right_layout.addWidget(right_label)

        # Create scroll area for resource boxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_content = QWidget()
        self.resource_layout = QVBoxLayout(scroll_content)
        self.resource_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_content.setLayout(self.resource_layout)
        scroll_area.setWidget(scroll_content)
        right_layout.addWidget(scroll_area)

        # Create output area
        output_label = QLabel("Output")
        output_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = output_label.font()
        font.setPointSize(14)
        output_label.setFont(font)
        right_layout.addWidget(output_label)
        self.output_box = QTextEdit()
        mono_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono_font.setPointSize(14)
        self.output_box.setFont(mono_font)
        self.output_box.setReadOnly(True)

        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.output_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_area.setMinimumWidth(200)
        right_layout.addWidget(self.output_box)
        main_edit_layout.addLayout(right_layout, 2)
        main_layout.addLayout(main_edit_layout)

        # Create status bar ---------------------------------------------------
        self.status_bar = QStatusBar()
        font = self.status_bar.font()
        font.setPointSize(12)
        self.status_bar.setFont(font)
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.setContentsMargins(0, 0, 0, 2)
        self.setStatusBar(self.status_bar)
        l, t, r, _ = self.centralWidget().layout().getContentsMargins()
        self.centralWidget().layout().setContentsMargins(l, t, r, 0)

        self.file_path_label = QLabel("No File Open")
        self.file_path_label.setContentsMargins(8, 0, 0, 0)
        self.file_path_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.file_path_label.mouseReleaseEvent = lambda event: self.open_file()
        self.status_bar.addWidget(self.file_path_label)

        sep_fd_cursor = QFrame()
        sep_fd_cursor.setFrameShape(QFrame.Shape.VLine)
        sep_fd_cursor.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_bar.addWidget(sep_fd_cursor)

        self.position_label = QLabel("Ln 1, Col 1")
        self.position_label.setContentsMargins(5, 0, 5, 0)
        self.status_bar.addWidget(self.position_label)

        sep_cursor_space = QFrame()
        sep_cursor_space.setFrameShape(QFrame.Shape.VLine)
        sep_cursor_space.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_bar.addWidget(sep_cursor_space)

        spacer_status = QWidget()
        spacer_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.status_bar.addWidget(spacer_status)

        sep_group2 = QFrame()
        sep_group2.setFrameShape(QFrame.Shape.VLine)
        sep_group2.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_bar.addPermanentWidget(sep_group2)

        self.version_label = QLabel(f"Vehicle Version: {VERSION}")
        self.version_label.setContentsMargins(0, 0, 0, 0)
        self.status_bar.addPermanentWidget(self.version_label)

        sep_verifier = QFrame()
        sep_verifier.setFrameShape(QFrame.Shape.VLine)
        sep_verifier.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_bar.addPermanentWidget(sep_verifier)

        self.verifier_label = QLabel("No Verifier Set")
        self.verifier_label.setContentsMargins(0, 0, 10, 0)
        self.verifier_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.verifier_label.mouseReleaseEvent = lambda event: self.set_verifier()
        self.status_bar.addPermanentWidget(self.verifier_label)

        self.editor.cursorPositionChanged.connect(self.update_cursor_position)

    def new_file(self):
        self.editor.clear()
        self.output_box.clear()
        self.file_path_label.setText("No file opened")
        self.status_bar.showMessage("New file created", 3000)
        self.vcl_path = None
        self.vcl_bindings.clear()
        self.clear_resource_boxes()

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Vehicle Specification", "", "VCL Files (*.vcl);;All Files (*)"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.editor.setPlainText(file.read())
            self.status_bar.showMessage(f"Opened: {file_path}", 3000)
            self.set_vcl_path(file_path)
        except Exception as e: 
            QMessageBox.critical(self, "Open File Error", f"Could not open file: {e}")
            self.file_path_label.setText("Error opening file")
            self.clear_resource_boxes() # Clear resources if file fails to load

    def save_file(self):
        current_file_path = self.vcl_path
        if not current_file_path: # If no path, it's a "Save As"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Vehicle Specification", "", "VCL Files (*.vcl);;All Files (*)"
            )
            if not file_path:
                return 
            current_file_path = file_path
        
        try:
            with open(current_file_path, 'w', encoding='utf-8') as file:
                file.write(self.editor.toPlainText())
            self.status_bar.showMessage(f"Saved: {current_file_path}", 3000)
            if self.vcl_path != current_file_path:
                self.set_vcl_path(current_file_path) 
            self.editor.document().setModified(False)
        except Exception as e:
            QMessageBox.critical(self, "Save File Error", f"Could not save file: {e}")

    def set_verifier(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Marabou Verifier", "", "Marabou Verifier (Marabou*);;All Files (*)"
        )
        if not file_path:
            return
        self.vcl_bindings.verifier_path = file_path
        self.verifier_label.setText(f"Verifier: {os.path.basename(file_path)}")
        self.status_bar.showMessage(f"Verifier set: {file_path}", 3000)

    def save_before_operation(self):
        if not self.vcl_path:
            reply = QMessageBox.question(
                self, "Save File", "The file needs to be saved before this operation. Save now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_file() # This will call set_vcl_path if successful on new file
                return bool(self.vcl_path)
            return False
        else:
            try:
                with open(self.vcl_path, 'w', encoding='utf-8') as file:
                    file.write(self.editor.toPlainText())
                self.editor.document().setModified(False)
                self.status_bar.showMessage(f"File saved: {self.vcl_path}", 2000)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Could not save file '{self.vcl_path}': {e}")
                return False

    def _perform_compile(self):
        return self.vcl_bindings.compile()

    def compile_spec(self):
        if not self.save_before_operation():
            return
        
        # Ensure resources are assigned (this part is quick, involves reading UI state)
        self.assign_resources() 
        if not all(box.is_loaded for box in self.resource_boxes):
            QMessageBox.warning(self, "Resource Error", "Please load all required file-based resources (networks, datasets) before compilation.")
            return

        self.status_bar.showMessage("Compiling... Please wait.", 0)
        self.compile_button.setEnabled(False)
        self.verify_button.setEnabled(False)
        self.current_operation = "compile"
        self.output_box.clear()

        worker = Worker(self._perform_compile)
        worker.signals.result.connect(self.handle_worker_result)
        worker.signals.finished.connect(self.handle_worker_finished)
        worker.signals.error.connect(self.handle_worker_error)

        self.thread_pool.start(worker)

    def _perform_verify(self):
        return self.vcl_bindings.verify()

    def verify_spec(self):
        if not self.save_before_operation():
            return
        if not self.vcl_bindings.verifier_path:
            QMessageBox.warning(self, "Verification Error", "Please set the verifier path first.")
            return
        
        self.assign_resources()
        if not all(box.is_loaded for box in self.resource_boxes if box.type != "parameter"):
            QMessageBox.warning(self, "Resource Error", "Please load all required file-based resources before verification.")
            return

        self.status_bar.showMessage("Verifying... Please wait.", 0)
        self.compile_button.setEnabled(False)
        self.verify_button.setEnabled(False)
        self.current_operation = "verify"
        self.output_box.clear()

        worker = Worker(self._perform_verify)
        worker.signals.result.connect(self.handle_worker_result)
        worker.signals.finished.connect(self.handle_worker_finished)
        worker.signals.error.connect(self.handle_worker_error)

        self.thread_pool.start(worker)

    # --- Worker Signal Handlers ---
    def handle_worker_result(self, output_text):
        self.output_box.setPlainText(output_text)
        self.status_bar.showMessage(f"{self.current_operation} completed successfully.", 5000)

    def handle_worker_finished(self):
        self.compile_button.setEnabled(True)
        self.verify_button.setEnabled(True)
        self.status_bar.showMessage(f"{self.current_operation} processing finished.", 3000)
        self.current_operation = None

    def handle_worker_error(self, title, message):
        QMessageBox.critical(self, title, message)
        self.status_bar.showMessage(f"Error during {self.current_operation}. Check output for details.", 5000)

    # --- Resource Management ---
    def clear_resource_boxes(self):
        while self.resource_layout.count():
            item = self.resource_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.resource_boxes.clear()

    def generate_resource_boxes(self):
        self.clear_resource_boxes()
        if not self.vcl_path:
            return
        try:
            resources = self.vcl_bindings.resources()
            for entry in resources:
                name = entry.get("entityName")
                type_ = entry.get("entitySort", "").lstrip("@")
                data_type = entry.get("entityType", None)
                if not name or not type_:
                    print(f"Skipping resource entry with missing name or type: {entry}")
                    continue
                box = ResourceBox(name, type_, data_type=data_type)
                self.resource_layout.addWidget(box)
                self.resource_boxes.append(box)

        except Exception as e:
            self.output_box.append(f"Error generating resource boxes: {e}\n{traceback.format_exc()}")

    def assign_resources(self):
        """Assign resources from GUI boxes to the VCLBindings object."""
        for box in self.resource_boxes:
            if box.is_loaded: # is_loaded should correctly reflect if a value/path is set
                try:
                    if box.type == "network":
                        self.vcl_bindings.set_network(box.name, box.path)
                    elif box.type == "dataset":
                        self.vcl_bindings.set_dataset(box.name, box.path)
                    elif box.type == "parameter":
                        self.vcl_bindings.set_parameter(box.name, box.value)
                except Exception as e:
                    QMessageBox.warning(self, "Resource Assignment Error", f"Error assigning resource {box.name}: {e}")

    def show_version(self):
        QMessageBox.information(self, "Version", f"Current version: {VERSION}")

    def set_vcl_path(self, path):
        self.vcl_bindings.clear() # Clear any old bindings/data
        self.vcl_bindings.vcl_path = path
        self.vcl_path = path
        self.file_path_label.setText(f"File: {os.path.basename(path)}")
        self.output_box.clear() # Clear previous output for new file
        self.generate_resource_boxes() # Regenerate resource inputs for the new file

    def update_cursor_position(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        self.position_label.setText(f"Ln {line}, Col {col}")

    def closeEvent(self, event):
        super().closeEvent(event)