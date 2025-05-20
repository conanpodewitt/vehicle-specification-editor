import os
import traceback 
import asyncio
from PyQt6.QtWidgets import (QMainWindow, QTextEdit, QVBoxLayout, QPushButton, QWidget,
                             QLabel, QFileDialog, QHBoxLayout, QStatusBar, QMessageBox,
                             QScrollArea, QSizePolicy, QToolBar, QFrame, QSplitter,
                             QTabWidget)
from PyQt6.QtCore import Qt, QRunnable, pyqtSlot, QObject, pyqtSignal, QThreadPool
from PyQt6.QtGui import QFontDatabase, QIcon
from ui.code_editor import CodeEditor
from ui.resource_box import ResourceBox
from ui.vcl_bindings import VCLBindings
from vehicle_lang import VERSION 
from superqt.utils import CodeSyntaxHighlight
import functools
from typing import Callable


class OperationSignals(QObject):
    """
    Defines signals to communicate from worker thread to main GUI thread.
    """
    output_chunk = pyqtSignal(str, str)  # tag ('stdout'/'stderr'), chunk_text
    finished = pyqtSignal(int)           # return_code (0=success, 1=error, -1=stopped)
    error = pyqtSignal(str)              # For critical errors in worker setup itself


class OperationWorker(QRunnable):
    def __init__(self, operation: Callable, vcl_bindings: VCLBindings,
                 stop_event: asyncio.Event, signals: OperationSignals):
        super().__init__()
        self.operation = operation
        self.vcl_bindings = vcl_bindings
        self.stop_event = stop_event
        self.signals = signals

    def _callback_fn(self, tag: str, chunk: str):
        self.signals.output_chunk.emit(tag, chunk)

    def _finish_fn(self, return_code: int):
        if self.stop_event.is_set():
            self.signals.finished.emit(-1)  # -1 for user-stopped
        else:
            self.signals.finished.emit(return_code)

    @pyqtSlot()
    def run(self):
        try:
            self.operation(
                callback_fn=self._callback_fn,
                finish_fn=self._finish_fn,
                stop_event=self.stop_event
            )
        except Exception as e:
            tb_str = traceback.format_exc()
            self.signals.output_chunk.emit("stderr", f"Critical Worker Error: {e}\n{tb_str}")
            if self.stop_event.is_set(): # If stop was also requested
                self.signals.finished.emit(-1)
            else:
                self.signals.finished.emit(1)

    
class VCLEditor(QMainWindow):
    """Vehicle Specification Editor"""
    def __init__(self):
        super().__init__()
        self.resource_boxes = []
        self.stop_event = asyncio.Event()
        self.vcl_bindings = VCLBindings()
        self.vcl_path = None
        self.setWindowTitle("Vehicle Specification Editor")
        self.setGeometry(100, 100, 1400, 800)
        self.current_operation = None # Tracks 'compile' or 'verify'

        self.thread_pool = QThreadPool()
        self.operation_signals = OperationSignals()
        self.operation_signals.output_chunk.connect(self._gui_process_output_chunk)
        self.operation_signals.finished.connect(self._gui_operation_finished)

        self.show_ui()

    def show_ui(self):
        """Initialize UI"""
        # Create menu bar
        file_toolbar = QToolBar("File")
        self.addToolBar(file_toolbar)
        file_toolbar.setMovable(False)
        file_toolbar.setFloatable(False)
        file_toolbar.addAction(QIcon.fromTheme("document-new"), "New", self.new_file)
        file_toolbar.addAction(QIcon.fromTheme("document-open"), "Open", self.open_file)
        file_toolbar.addAction(QIcon.fromTheme("document-save"), "Save", self.save_file)

        # Add a spacer to the toolbar. This will push the buttons to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        file_toolbar.addWidget(spacer)

        # Add set verifier, compile, and verify buttons
        verifier_btn = QPushButton(QIcon.fromTheme("computer"), "Set Verifier")
        verifier_btn.clicked.connect(self.set_verifier)
        file_toolbar.addWidget(verifier_btn)

        self.compile_button = QPushButton(QIcon.fromTheme("scanner"), "Compile")
        self.compile_button.clicked.connect(self.compile_spec)
        file_toolbar.addWidget(self.compile_button)

        self.verify_button = QPushButton(QIcon.fromTheme("media-playback-start"), "Verify")
        self.verify_button.clicked.connect(self.verify_spec)
        file_toolbar.addWidget(self.verify_button)

        # Add stop button for running operations
        self.stop_button = QPushButton(QIcon.fromTheme("process-stop", QIcon.fromTheme("media-playback-stop")), "Stop")
        self.stop_button.setToolTip("Stop the current operation")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_current_operation)
        file_toolbar.addWidget(self.stop_button)

        # Create main window widget 
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Create main edit area 
        main_edit_layout = QHBoxLayout()

        # Create left area, containing the editor and the console
        left_layout = QVBoxLayout()
        left_label = QLabel("Editor")
        left_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = left_label.font()
        font.setPointSize(14)
        left_label.setFont(font)
        left_layout.addWidget(left_label)

        # Create a splitter for the editor and the console
        editor_console_splitter = QSplitter(Qt.Orientation.Vertical)

        # Create left editor 
        self.editor = CodeEditor()
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(14)
        self.editor.setFont(mono)
        self.editor.setPlaceholderText("Enter your Vehicle specification here...")
        self.highlighter = CodeSyntaxHighlight(self.editor.document(), "external", "vs")    # Added syntax highlighting
        editor_console_splitter.addWidget(self.editor) # Add editor to splitter

        # Create the new console area, containing the problems and output tabs
        self.console_tab_widget = QTabWidget()
        console_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        console_font.setPointSize(12)

        # Create the Problems tab
        self.problems_console = QTextEdit()
        self.problems_console.setFont(console_font)
        self.problems_console.setReadOnly(True)
        self.console_tab_widget.addTab(self.problems_console, "Problems")

        # Create the Output tab
        self.log_console = QTextEdit() # For "Output" tab
        self.log_console.setFont(console_font)
        self.log_console.setReadOnly(True)
        self.console_tab_widget.addTab(self.log_console, "Output")

        editor_console_splitter.addWidget(self.console_tab_widget) # Add console to splitter

        # Set the size policy for the editor and the console: editor takes 3/4 of the space
        editor_console_splitter.setStretchFactor(0, 3)
        editor_console_splitter.setStretchFactor(1, 1)

        # Add the splitter
        left_layout.addWidget(editor_console_splitter) 

        # Add the left layout to the main layout
        main_edit_layout.addLayout(left_layout, 3)

        # Create right area for resource boxes and output
        right_layout = QVBoxLayout()
        right_label = QLabel("Additional Input")
        right_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = right_label.font()
        font.setPointSize(14)
        right_label.setFont(font)
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

        # Set size policy for output box and scroll area
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.output_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_area.setMinimumWidth(200)
        right_layout.addWidget(self.output_box)
        main_edit_layout.addLayout(right_layout, 2)
        main_layout.addLayout(main_edit_layout)

        # Create status bar
        self.status_bar = QStatusBar()
        font = self.status_bar.font()
        font.setPointSize(12)
        self.status_bar.setFont(font)
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.setContentsMargins(0, 0, 0, 2)
        self.setStatusBar(self.status_bar)
        l, t, r, _ = self.centralWidget().layout().getContentsMargins()
        self.centralWidget().layout().setContentsMargins(l, t, r, 0)

        # File path label
        self.file_path_label = QLabel("No File Open")
        self.file_path_label.setContentsMargins(8, 0, 0, 0)
        self.file_path_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.file_path_label.mouseReleaseEvent = lambda event: self.open_file()
        self.status_bar.addWidget(self.file_path_label)

        # Sperateor between file display and cursor position
        sep_fd_cursor = QFrame()
        sep_fd_cursor.setFrameShape(QFrame.Shape.VLine)
        sep_fd_cursor.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_bar.addWidget(sep_fd_cursor)

        # Cursor position label
        self.position_label = QLabel("Ln 1, Col 1")
        self.position_label.setContentsMargins(5, 0, 5, 0)
        self.status_bar.addWidget(self.position_label)

        # Spacer between cursor position and spacer
        sep_cursor_space = QFrame()
        sep_cursor_space.setFrameShape(QFrame.Shape.VLine)
        sep_cursor_space.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_bar.addWidget(sep_cursor_space)

        # Big expanding spacer
        spacer_status = QWidget()
        spacer_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.status_bar.addWidget(spacer_status)

        # Seperator before version and verifier
        sep_group2 = QFrame()
        sep_group2.setFrameShape(QFrame.Shape.VLine)
        sep_group2.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_bar.addPermanentWidget(sep_group2)
        
        # Version label
        self.version_label = QLabel(f"Vehicle Version: {VERSION}")
        self.version_label.setContentsMargins(0, 0, 0, 0)
        self.status_bar.addPermanentWidget(self.version_label)

        # Seperator between version and verifier
        sep_verifier = QFrame()
        sep_verifier.setFrameShape(QFrame.Shape.VLine)
        sep_verifier.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_bar.addPermanentWidget(sep_verifier)

        # Verifier label
        self.verifier_label = QLabel("No Verifier Set")
        self.verifier_label.setContentsMargins(0, 0, 10, 0)
        self.verifier_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.verifier_label.mouseReleaseEvent = lambda event: self.set_verifier()
        self.status_bar.addPermanentWidget(self.verifier_label)

        # Connect cursor movements to update the position indicator
        self.editor.cursorPositionChanged.connect(self.update_cursor_position)

    # --- File Operations ---

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
            self.set_vcl_path(current_file_path)
            self.editor.document().setModified(False) 
            
        except Exception as e:
            QMessageBox.critical(self, "Save File Error", f"Could not save file: {e}")
            self.problems_console.append(f"Error saving file: {e}")

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
        if not self.vcl_path or self.editor.document().isModified():
            if not self.vcl_path:
                 msg = "The file needs to be saved before this operation. Save now?"
            else:
                 msg = "The file has been modified. Save changes before this operation?"
            
            reply = QMessageBox.question(
                self, "Save File", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_file()
                return bool(self.vcl_path) and not self.editor.document().isModified()
            else:
                return False
        return True

    # --- Compilation and Verification ---

    @pyqtSlot(str, str)
    def _gui_process_output_chunk(self, tag: str, chunk: str):
        """Processes output chunks received from the worker thread."""
        if tag == "stderr":
            self.problems_console.insertPlainText(chunk)
            self.problems_console.ensureCursorVisible()
        elif tag == "stdout":
            self.log_console.insertPlainText(chunk)
            self.log_console.ensureCursorVisible()

    @pyqtSlot(int)
    def _gui_operation_finished(self, return_code: int):
        """Handles the completion of a VCL operation from the worker thread."""
        self.compile_button.setEnabled(True)
        self.verify_button.setEnabled(True)
        self.stop_button.setVisible(False)
        self.stop_button.setEnabled(False) # Should already be if stop was clicked

        if return_code == 0: # Success
            self.status_bar.showMessage(f"{self.current_operation.capitalize()} completed successfully.", 5000)
            self.log_console.append(f"\n--- {self.current_operation.capitalize()} finished successfully. ---")
        elif return_code == -1: # Stopped by user
            self.status_bar.showMessage(f"{self.current_operation.capitalize()} stopped by user.", 5000)
            self.problems_console.append(f"\n--- {self.current_operation.capitalize()} stopped by user. ---")
            if self.console_tab_widget: self.console_tab_widget.setCurrentWidget(self.problems_console)
        else: # Error
            self.status_bar.showMessage(f"Error during {self.current_operation.capitalize()}. Check Problems tab.", 5000)
            self.problems_console.append(f"\n--- {self.current_operation.capitalize()} failed. ---")
            if self.console_tab_widget: self.console_tab_widget.setCurrentWidget(self.problems_console)
        
        self.current_operation = None

    def stop_current_operation(self):
        self.status_bar.showMessage(f"Attempting to stop {self.current_operation}...", 0)
        self.stop_event.set() 
        self.stop_button.setEnabled(False) 
    
    def _start_vcl_operation(self, operation_name: str):
        """Common logic to start a VCL compile or verify operation."""
        if not self.save_before_operation():
            return

        self.assign_resources()

        if operation_name == "verify" and not self.vcl_bindings.verifier_path:
            QMessageBox.warning(self, "Verification Error", "Please set the verifier path first.")
            return
        
        if not all(box.is_loaded for box in self.resource_boxes):
            QMessageBox.warning(self, "Resource Error", "Please load all required resources (networks, datasets, parameters) before compilation/verification")
            return

        self.status_bar.showMessage(f"{operation_name.capitalize()}... Please wait.", 0)
        self.compile_button.setEnabled(False)
        self.verify_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.current_operation = operation_name

        self.stop_event.clear() # Clear any previous stop signal
        self.problems_console.clear()
        self.log_console.clear()
        self.output_box.clear() # Clear the original right-side log as well

        if operation_name == "compile":
            operation = functools.partial(self.vcl_bindings.compile, stop_event=self.stop_event)
        elif operation_name == "verify":
            operation = functools.partial(self.vcl_bindings.verify, stop_event=self.stop_event)

        # Create and start the worker
        worker = OperationWorker(
            operation = operation,
            vcl_bindings=self.vcl_bindings,
            stop_event=self.stop_event,
            signals=self.operation_signals
        )
        self.thread_pool.start(worker)

    def compile_spec(self):
        self._start_vcl_operation("compile")

    def verify_spec(self):
        self._start_vcl_operation("verify")

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
            tb_str = traceback.format_exc()
            self.problems_console.append(f"Error generating resource boxes: {e}\n{tb_str}")
            self.console_tab_widget.setCurrentWidget(self.problems_console)

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
                    self.problems_console.append(f"Error assigning resource {box.name}: {e}")

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
        if self.current_operation:
            reply = QMessageBox.question(self, "Confirm Exit",
                                         f"A '{self.current_operation}' operation is in progress. "
                                         "Stopping it and exiting might take a moment. Exit anyway?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if self.stop_event:
                    self.stop_event.set() # Signal stop
                self.thread_pool.waitForDone(3000) # Wait up to 3 seconds
                self.thread_pool.clear() # Clear the thread pool
                event.accept()
            else:
                event.ignore()
                return
        else:
            event.accept()
        super().closeEvent(event)