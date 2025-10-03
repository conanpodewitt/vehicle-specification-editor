import os
import site
import traceback 
import asyncio
from PyQt6.QtWidgets import (QMainWindow, QTextEdit, QVBoxLayout, QPushButton, QWidget,
                             QLabel, QFileDialog, QHBoxLayout, QStatusBar, QMessageBox,
                             QScrollArea, QSizePolicy, QToolBar, QFrame, QSplitter,
                             QTabWidget, QProgressBar, QApplication)
from PyQt6.QtCore import Qt, QRunnable, pyqtSlot, QObject, pyqtSignal, QThreadPool, QTimer
from PyQt6.QtGui import QFontDatabase, QIcon
from superqt.utils import CodeSyntaxHighlight
import functools
import glob
from typing import Callable, OrderedDict
import shutil

from vehicle_gui.code_editor import CodeEditor
from vehicle_gui.vcl_bindings import VCLBindings
from vehicle_gui.query_view.query_tab import QueryTab
from vehicle_gui.counter_example_view.counter_example_tab import CounterExampleTab
from vehicle_gui.resource_view.resource_box import ResourceBox
from vehicle_gui.resource_view.property_selection_widget import PropertySelectionWidget
from vehicle_gui.vcl_bindings import CACHE_DIR
from vehicle_gui.counter_example_view.extract_renderers import load_renderer_classes
from vehicle_gui.counter_example_view.base_renderer import GSImageRenderer, TextRenderer

from vehicle_lang import VERSION 

RELEASE_VERSION = "0.1.3"

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
        self.set_verifier_from_PATH() # Attempt to set verifier from PATH on startup

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
        verifier_btn.clicked.connect(self.set_verifier_from_button)
        file_toolbar.addWidget(verifier_btn)

        self.compile_button = QPushButton(QIcon.fromTheme("scanner"), "Compile")
        self.compile_button.clicked.connect(self.compile_spec)
        file_toolbar.addWidget(self.compile_button)

        self.verify_button = QPushButton(QIcon.fromTheme("media-playback-start"), "Verify")
        self.verify_button.clicked.connect(self.verify_spec)
        self.verify_button.setEnabled(False)
        file_toolbar.addWidget(self.verify_button)

        # Add stop button for running operations
        self.stop_button = QPushButton(QIcon.fromTheme("process-stop", QIcon.fromTheme("media-playback-stop")), "Stop")
        self.stop_button.setToolTip("Stop the current operation")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_current_operation)
        file_toolbar.addWidget(self.stop_button)

        # Create main window widget 
        main_widget = QSplitter(Qt.Orientation.Vertical)
        # Create top tabbed section
        main_tab = QTabWidget()
        main_widget.addWidget(main_tab)
        # Create each of the tabs
        input_tab = QWidget()
        output_tab = QWidget()
        main_tab.addTab(input_tab, "Input")
        main_tab.addTab(output_tab, "Queries")

        # Define the splitter as the main widget
        self.setCentralWidget(main_widget)
        
        # Define layouts for each tab
        input_layout = QVBoxLayout(input_tab)
        output_layout = QVBoxLayout(output_tab)

        # Create main edit area 
        input_edit_layout = QHBoxLayout()

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
        self.editor = CodeEditor(lang="external", theme="vse-style")
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(14)
        self.editor.setFont(mono)
        self.editor.setPlaceholderText("Enter your Vehicle specification here...")
        editor_console_splitter.addWidget(self.editor) # Add editor to splitter

        # Create the new console area, containing the problems and output tabs
        self.console_tab_widget = QTabWidget()
        console_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        console_font.setPointSize(12)

        # Create the Problems tab in the console
        self.problems_console = QTextEdit()
        self.problems_console.setFont(console_font)
        self.problems_console.setReadOnly(True)
        self.console_tab_widget.addTab(self.problems_console, "Problems")

        # Create the Output tab in the console
        self.log_console = QTextEdit() # For "Output" tab
        self.log_console.setFont(console_font)
        self.log_console.setReadOnly(True)
        self.console_tab_widget.addTab(self.log_console, "Output")

        # Add console to splitter
        main_widget.addWidget(self.console_tab_widget)

        # Create the Counter Examples tab
        self.counter_example_tab = CounterExampleTab()
        main_tab.addTab(self.counter_example_tab, " Results")

        # Set the size policy for the editor and the console: editor takes 3/4 of the space
        editor_console_splitter.setStretchFactor(0, 3)
        editor_console_splitter.setStretchFactor(1, 1)

        # Add the splitter
        left_layout.addWidget(editor_console_splitter) 

        # Add the left layout to the main layout
        input_edit_layout.addLayout(left_layout, 3)

        # Create right area for resource boxes and output
        right_layout = QVBoxLayout()
        right_label = QLabel("Additional Input")
        right_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = right_label.font()
        font.setPointSize(14)
        right_label.setFont(font)
        right_layout.addWidget(right_label)

        # Create scroll area for resource boxes
        resource_scroll_area = QScrollArea()
        resource_scroll_area.setWidgetResizable(True)
        resource_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        resource_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create a widget to hold the resource boxes
        resource_scroll_content = QWidget()
        self.resource_layout = QVBoxLayout(resource_scroll_content)
        self.resource_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        resource_scroll_content.setLayout(self.resource_layout)
        resource_scroll_area.setWidget(resource_scroll_content)
        right_layout.addWidget(resource_scroll_area)

        # Property selection widget
        properties_label = QLabel("Properties")
        properties_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = properties_label.font()
        font.setPointSize(14)
        properties_label.setFont(font)
        right_layout.addWidget(properties_label)

        self.property_selector = PropertySelectionWidget()
        right_layout.addWidget(self.property_selector)
        
        # Create output box
        self.query_tab = QueryTab()
        output_layout.addWidget(self.query_tab)

        # Set size policy for output box
        resource_scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.query_tab.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        resource_scroll_area.setMinimumWidth(200)
        input_edit_layout.addLayout(right_layout, 2)
        input_layout.addLayout(input_edit_layout)

        # Create status bar
        self.status_bar = QStatusBar()
        font = self.status_bar.font()
        font.setPointSize(12)
        self.status_bar.setFont(font)
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.setContentsMargins(0, 0, 0, 2)
        self.setStatusBar(self.status_bar)

        # File path label
        self.file_path_label = QLabel("No File Open")
        self.file_path_label.setContentsMargins(8, 0, 0, 0)
        self.file_path_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.file_path_label.mouseReleaseEvent = lambda event: self.open_file()
        self.status_bar.addWidget(self.file_path_label)

        # Separator between file display and cursor position
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

        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_bar.addPermanentWidget(progress_bar)

        # Separator before version and verifier
        sep_group2 = QFrame()
        sep_group2.setFrameShape(QFrame.Shape.VLine)
        sep_group2.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_bar.addPermanentWidget(sep_group2)
        
        # Version label
        self.gui_version_label = QLabel(f"VSE Version: {RELEASE_VERSION}")
        self.gui_version_label.setContentsMargins(0, 0, 0, 0)
        self.status_bar.addPermanentWidget(self.gui_version_label)

        # Separator between VSE version and vehicle version
        sep_vse_verifier = QFrame()
        sep_vse_verifier.setFrameShape(QFrame.Shape.VLine)
        sep_vse_verifier.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_bar.addPermanentWidget(sep_vse_verifier)
        
        self.vehicle_version_label = QLabel(f"Vehicle Version: {VERSION}")
        self.vehicle_version_label.setContentsMargins(0, 0, 0, 0)
        self.status_bar.addPermanentWidget(self.vehicle_version_label)

        # Separator between version and verifier
        sep_verifier = QFrame()
        sep_verifier.setFrameShape(QFrame.Shape.VLine)
        sep_verifier.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_bar.addPermanentWidget(sep_verifier)

        # Verifier label
        self.verifier_label = QLabel("No Verifier Set")
        self.verifier_label.setContentsMargins(0, 0, 10, 0)
        self.verifier_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.verifier_label.mouseReleaseEvent = lambda event: self.set_verifier_from_button()
        self.status_bar.addPermanentWidget(self.verifier_label)

        # Connect cursor movements to update the position indicator
        self.editor.cursorPositionChanged.connect(self.update_cursor_position)

    # --- File Operations ---

    def new_file(self):
        self.editor.clear()
        self.query_tab.clear()
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

            if not self.is_valid_vcl():
                return
            self.load_resources()               # Regenerate resource inputs and properties

        except Exception as e: 
            QMessageBox.critical(self, "Open File Error", f"Could not open file: {e}")
            self.file_path_label.setText("Error opening file")
            self.clear_resource_boxes()         # Clear resources if file fails to load

        # Load properties
        self.regenerate_properties()
        self.update_counter_example_modes()
    
    def save_file(self):
        current_file_path = self.vcl_path

        # If no path, it's a "Save As"
        if not current_file_path:      
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Vehicle Specification", "", "VCL Files (*.vcl);;All Files (*)"
            )
            if not file_path:
                return False
            current_file_path = file_path
        try:
            with open(current_file_path, 'w', encoding='utf-8') as file:
                file.write(self.editor.toPlainText())
            self.status_bar.showMessage(f"Saved: {current_file_path}", 3000)
            self.set_vcl_path(current_file_path)
            self.editor.document().setModified(False) 
        
        except Exception as e:
            QMessageBox.critical(self, "Save File Error", f"Could not save file: {e}")
            self.append_to_problems(f"Error saving file: {e}")
            self.clear_resource_boxes()
            return False   
        
        if not self.is_valid_vcl():
            self.clear_resource_boxes()
            return False
        old_boxes = {box.name: box for box in self.resource_boxes}
        self.regenerate_resource_boxes(old_boxes)
        self.update_counter_example_modes()

        # Remember selected properties
        selected_properties = self.property_selector.selected_properties()
        self.regenerate_properties(selected_properties)
        return True                            

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
            return reply == QMessageBox.StandardButton.Yes and self.save_file()
        return self.save_file()
    
    # --- Verifier Management ---

    def set_verifier_from_button(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Marabou Verifier", "", "Marabou Verifier (Marabou*);;All Files (*)"
        )
        if not file_path:
            return
        self.vcl_bindings.verifier_path = file_path
        self.verify_button.setEnabled(True)
        self.verifier_label.setText(f"Verifier: {os.path.basename(file_path)}")
        self.status_bar.showMessage(f"Verifier set: {file_path}", 3000)

    def set_verifier_from_PATH(self):
        """Attempt to find Marabou in system PATH and set it as the verifier."""
        marabou_exec = shutil.which("Marabou")
        if marabou_exec:
            self.vcl_bindings.verifier_path = marabou_exec
            self.verifier_label.setText(f"Verifier: {os.path.basename(marabou_exec)}")
            self.append_to_log(f"Marabou found: {marabou_exec}")
            self.verify_button.setEnabled(True)
        else:
            self.append_to_log("Marabou not found in PATH.")

    # --- Compilation and Verification ---

    @pyqtSlot(str, str)
    def _gui_process_output_chunk(self, tag: str, chunk: str):
        """Processes output chunks received from the worker thread."""
        if tag == "stderr":
            current_widget = self.problems_console
        elif tag == "stdout":
            current_widget = self.log_console
        current_widget.insertPlainText(chunk)
        current_widget.ensureCursorVisible()
        self.console_tab_widget.setCurrentWidget(current_widget)

        # Refresh properties in query tab after any output
        if self.current_operation == "verify":
            self.counter_example_tab.refresh_from_cache()

    @pyqtSlot(int)
    def _gui_operation_finished(self, return_code: int):
        """Handles the completion of a VCL operation from the worker thread."""
        self.compile_button.setEnabled(True)
        self.verify_button.setEnabled(True)
        self.stop_button.setVisible(False)
        self.stop_button.setEnabled(False)

        if return_code == 0: # Success
            self.status_bar.showMessage(f"{self.current_operation.capitalize()} completed successfully.", 5000)
            self.append_to_log(f"\n--- {self.current_operation.capitalize()} finished successfully. ---")
        elif return_code == -1: # Stopped by user
            self.status_bar.showMessage(f"{self.current_operation.capitalize()} stopped by user.", 5000)
            self.append_to_log(f"\n--- {self.current_operation.capitalize()} stopped by user. ---")
            if self.console_tab_widget: self.console_tab_widget.setCurrentWidget(self.problems_console)
        else: # Error
            self.status_bar.showMessage(f"Error during {self.current_operation.capitalize()}. Check Problems tab.", 5000)
            self.append_to_problems(f"\n--- {self.current_operation.capitalize()} failed. ---")
            if self.console_tab_widget: self.console_tab_widget.setCurrentWidget(self.problems_console)
        
        self.query_tab.refresh_properties()
        if self.current_operation == "verify":
            self.counter_example_tab.refresh_from_cache()
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
        loaded_resources = [box.name for box in self.resource_boxes if box.is_loaded and box.type != "Variable"]
        if not all(loaded_resources):
            QMessageBox.warning(self, "Resource Error", "Please load all required resources (networks, datasets, parameters) before compilation/verification")
            return
        
        if operation_name == "verify":
            selected_properties = self.property_selector.selected_properties()
            self.vcl_bindings.set_properties(selected_properties)
            if not selected_properties:
                QMessageBox.warning(self, "No Properties Selected", "Please select at least one property to verify.")
                return

        self.status_bar.showMessage(f"Performing {operation_name.capitalize()}... Please wait.", 0)
        self.compile_button.setEnabled(False)
        self.verify_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.current_operation = operation_name

        self.stop_event.clear() # Clear any previous stop signal
        self.problems_console.clear()
        self.log_console.clear()
        self.query_tab.clear() # Clear previous queries

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
        # Recursively clear cache directory
        for root, _, files in os.walk(CACHE_DIR, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except Exception as e:
                    self.append_to_problems(f"Error clearing cache file {name}: {e}")
        self.query_tab.refresh_properties()
        self._start_vcl_operation("compile")

    def verify_spec(self):
        self.compile_spec() # Always compile before verifying

        while self.current_operation == "compile":
            QApplication.processEvents() # Wait for compilation to finish

        if not self.vcl_bindings.verifier_path:
            QMessageBox.warning(self, "Verification Error", "Please set the verifier path first.")
            return
        self._start_vcl_operation("verify")

    # --- Resource Management ---

    def clear_resource_boxes(self):
        while self.resource_layout.count():
            item = self.resource_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.resource_boxes.clear()

    def load_resources(self):
        self.clear_resource_boxes()
        if not self.vcl_path:
            return
        
        # Generate resource boxes
        try:
            resources = self.vcl_bindings.resources()
            variables = self.vcl_bindings.variables()

            for entry in resources + variables:
                name = entry.get("name")
                type_ = entry.get("tag")
                data_type = entry.get("typeText", None)
                if not name or not type_:
                    print(f"Skipping resource entry with missing name or type: {entry}")
                    continue
                box = ResourceBox(name, type_, data_type=data_type)
                self.resource_layout.addWidget(box)
                self.resource_boxes.append(box)
                
        except Exception as e:
            tb_str = traceback.format_exc()
            self.append_to_problems(f"Error generating resource boxes: {e}\n{tb_str}")
            self.console_tab_widget.setCurrentWidget(self.problems_console)

    def assign_resources(self):
        """Assign resources from GUI boxes to the VCLBindings object."""
        for box in self.resource_boxes:
            if box.is_loaded: # is_loaded should correctly reflect if a value/path is set
                try:
                    if box.type == "Network":
                        self.vcl_bindings.set_network(box.name, box.path)
                    elif box.type == "Dataset":
                        self.vcl_bindings.set_dataset(box.name, box.path)
                    elif box.type == "Parameter":
                        self.vcl_bindings.set_parameter(box.name, box.value)
                except Exception as e:
                    QMessageBox.warning(self, "Resource Assignment Error", f"Error assigning resource {box.name}: {e}")
                    self.append_to_problems(f"Error assigning resource {box.name}: {e}")

    def show_version(self):
        QMessageBox.information(self, "Version", f"Current version: {VERSION}")

    def regenerate_resource_boxes(self, old_boxes=None):
        """Regenerate resource boxes, preserving any already-set values."""
        if old_boxes is None:
            old_boxes = {}
        self.load_resources()
        for box in self.resource_boxes:
            old_box = old_boxes.get(box.name)
            if old_box and old_box.is_loaded:
                box.is_loaded = True
                if box.type in ["Network", "Dataset", "Variable"]:
                    box.path = old_box.path
                    box.input_box.setText(old_box.input_box.text())
                elif box.type == "Parameter":
                    box.value = old_box.value
                    if old_box.value is not None:
                        box.input_box.setText(str(old_box.value))

    def regenerate_properties(self, selected_properties=None):
        """Regenerate property selector, preserving any previously selected values."""
        try:
            properties = self.vcl_bindings.properties()
            self.property_selector.load_properties(properties)

            if selected_properties is not None:
                for prop_name, item in self.property_selector.property_items:
                    # By default, all items are unchecked. Uncheck those not in selected_properties
                    if prop_name not in selected_properties:
                        item.setCheckState(Qt.CheckState.Unchecked)
        except Exception as e:
            tb_str = traceback.format_exc()
            self.append_to_problems(f"Error loading properties: {e}\n{tb_str}")
            self.console_tab_widget.setCurrentWidget(self.problems_console)

    # --- Type Checking ---

    def is_valid_vcl(self):
        self.problems_console.clear()
        self.editor.clear_errors()
        errors = self.vcl_bindings.type_check()
        if errors:
            for error in errors:
                self.append_to_problems(f"Problem: {error['problem']}")
                self.append_to_problems(f"Fix: {error['fix']}")
                self.append_to_problems(f"Provenance: {error['provenance']['contents']}")
            self.editor.add_errors(errors)
            return False
        return True

    # --- Utility Methods ---

    def set_vcl_path(self, path):
        self.vcl_bindings.clear() # Clear any old bindings/data
        self.vcl_bindings.vcl_path = path
        self.vcl_path = path
        self.file_path_label.setText(f"File: {os.path.basename(path)}")
        self.query_tab.clear() # Clear previous output for new file

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

        if QApplication.instance():
            QApplication.instance().quit()

    def append_to_log(self, message: str):
        self.log_console.append(message)
        self.log_console.ensureCursorVisible()
        self.console_tab_widget.setCurrentWidget(self.log_console)
    
    def append_to_problems(self, message: str):
        self.problems_console.append(message)
        self.problems_console.ensureCursorVisible()
        self.console_tab_widget.setCurrentWidget(self.problems_console)

    def update_counter_example_modes(self):
        """Update counter example modes based on loaded variable resources."""
        base_renderers = [GSImageRenderer(), TextRenderer()]
        modes = OrderedDict()
        variable_boxes = [box for box in self.resource_boxes if box.type == 'Variable']
        for box in variable_boxes:
            modes[box.name] = []
            if box.is_loaded:
                try:
                    custom_renderers = load_renderer_classes(box.path)
                    modes[box.name] += custom_renderers
                except Exception as e:
                    print(f"Error loading renderers for {box.name}: {e}")
            modes[box.name] += base_renderers
        self.counter_example_tab.set_modes(modes)