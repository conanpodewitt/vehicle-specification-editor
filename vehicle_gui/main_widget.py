import os
import site
import traceback 
import asyncio
from PyQt6.QtWidgets import (QMainWindow, QTextEdit, QVBoxLayout, QPushButton, QWidget,
                             QLabel, QFileDialog, QHBoxLayout, QStatusBar, QMessageBox,
                             QScrollArea, QSizePolicy, QToolBar, QFrame, QSplitter,
                             QTabWidget, QProgressBar, QApplication, QComboBox)
from PyQt6.QtCore import Qt, QRunnable, pyqtSlot, QObject, pyqtSignal, QThreadPool, QTimer
from PyQt6.QtGui import QFontDatabase, QIcon
from superqt.utils import CodeSyntaxHighlight
import functools
from typing import Callable
from pathlib import Path
import json
import math
from datetime import datetime

from vehicle_gui.code_editor import CodeEditor
from vehicle_gui.vcl_bindings import VCLBindings
from vehicle_gui.query_view.query_tab import QueryTab
from vehicle_gui.counter_example_view.counter_example_tab import CounterExampleTab
from vehicle_gui.resource_view.input_view import InputView
from vehicle_gui.resource_view.property_view import PropertyView
from vehicle_gui.vcl_bindings import CACHE_DIR
from vehicle_gui.counter_example_view.base_renderer import GSImageRenderer, TextRenderer
from vehicle_gui.util import which_all

from vehicle_gui.counter_example_view.counter_example_tab import decode_counter_examples

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

    
class VehicleGUI(QMainWindow):
    """Vehicle GUI"""
    def __init__(self):
        super().__init__()
        self.stop_event = asyncio.Event()
        self.vcl_bindings = VCLBindings()
        self.vcl_path = None
        self.verifier_paths = {}  # Store mapping of verifier display names to paths
        self.setWindowTitle("Vehicle GUI")
        self.setGeometry(100, 100, 1400, 800)
        self.current_operation = None  # Tracks 'compile' or 'verify'
        # Buffer for incoming JSON chunks and per-property progress tracking
        self._json_buffer = ""
        self.current_property_name = ""
        self.property_total_queries = 0
        self.property_completed_queries = 0
        # Pause duration before starting next property (ms)
        self.property_pause_ms = 300
         
        # Track if error dialog has been displayed
        self._error_shown = False

        self._waiting_transition = False

        self.thread_pool = QThreadPool()
        self.operation_signals = OperationSignals()
        self.operation_signals.output_chunk.connect(self._gui_process_output_chunk)
        self.operation_signals.finished.connect(self._gui_operation_finished)

        self.show_ui()
        # Verifier dropdown will automatically populate and set default verifier

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

        # Add compile, and verify buttons
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
        main_tab.addTab(input_tab, "Specification")
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

        # Create the Output tab in the console
        self.log_console = QTextEdit()  # For "Output" tab
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
        right_label = QLabel("Input")
        right_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        right_label.setIndent(10)
        font = right_label.font()
        font.setPointSize(14)
        right_label.setFont(font)
        right_layout.addWidget(right_label)

        # Create resource view widget
        self.input_view = InputView(error_callback=self._show_error)
        right_layout.addWidget(self.input_view)

        # Property selection widget
        properties_label = QLabel("Properties and Variables")
        properties_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        properties_label.setIndent(10)
        font = properties_label.font()
        font.setPointSize(14)
        properties_label.setFont(font)
        right_layout.addWidget(properties_label)

        self.property_view = PropertyView()
        self.property_view.renderers_changed.connect(self.update_counter_example_modes)
        right_layout.addWidget(self.property_view)
        
        # Create output box
        self.query_tab = QueryTab()
        output_layout.addWidget(self.query_tab)

        # Set size policy for output box
        self.input_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.query_tab.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.input_view.setMinimumWidth(200)
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
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

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

        # Verifier dropdown
        self.verifier_dropdown = QComboBox()
        self.verifier_dropdown.setMinimumWidth(150)
        self.verifier_dropdown.setMaximumWidth(200)
        self.verifier_dropdown.currentTextChanged.connect(self._on_verifier_selected)
        self.status_bar.addPermanentWidget(self.verifier_dropdown)
        self.verifier_paths = set() 

        # Populate verifier dropdown
        self._populate_verifier_dropdown()
        
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
        self.input_view.clear_input_boxes()

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
            self.input_view.load_inputs(self.vcl_bindings)               # Regenerate resource inputs and properties

        except Exception as e: 
            QMessageBox.critical(self, "Open File Error", f"Could not open file: {e}")
            self.file_path_label.setText("Error opening file")
            self.input_view.clear_input_boxes()         # Clear resources if file fails to load

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
            self.input_view.clear_input_boxes()
            return False   
        
        if not self.is_valid_vcl():
            self.input_view.clear_input_boxes()
            return False
        
        # Preserve current resource state before regenerating
        self.regenerate_input_boxes()
        self.update_counter_example_modes()

        # Remember selected properties
        selected_properties = self.property_view.selected_properties()
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

    def load_verifier_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Marabou Verifier", "", "Marabou Verifier (Marabou*);;All Files (*)"
        )
        if not file_path:
            return
        
        if file_path not in self.verifier_paths:
            insert_index = self.verifier_dropdown.count() - 1
            self.verifier_dropdown.insertItem(insert_index, file_path)
        
        self.verifier_paths.add(file_path)
        self.verifier_dropdown.setCurrentText(file_path)
        self._set_verifier_path(file_path)


    def _populate_verifier_dropdown(self):
        """Populate the verifier dropdown with detected verifiers."""
        self.verifier_dropdown.clear()
        verifier_name = "Marabou"

        paths = which_all(verifier_name)
        
        for path in paths:
            self.verifier_dropdown.addItem(path)
            self.verifier_paths.add(path)

        # Add option to load from path
        self.verifier_dropdown.addItem("Load from Path...")
        
        # If verifiers found, set the first one as default
        if self.verifier_paths:
            first_verifier_path = self.verifier_paths.pop()
            self.verifier_dropdown.setCurrentText(first_verifier_path)
            self._set_verifier_path(first_verifier_path)
        else:
            self.verifier_dropdown.setCurrentText("No Verifier Set")
            self.verify_button.setEnabled(False)


    def _on_verifier_selected(self, text: str):
        """Handle verifier selection from dropdown."""
        if text == "No Verifier Set":
            self.verify_button.setEnabled(False)
        elif text == "Load from Path...":
            self.load_verifier_from_file()
        elif text in self.verifier_paths:
            self._set_verifier_path(text)
        else:
            self.verifier_dropdown.setCurrentText("No Verifier Set")

    def _set_verifier_path(self, path: str):
        """Set the verifier path and update UI."""
        self.vcl_bindings.verifier_path = path
        self.verify_button.setEnabled(True)

    # --- Compilation and Verification ---

    @pyqtSlot(str, str)
    def _gui_process_output_chunk(self, tag: str, chunk: str):
        """Processes output chunks received from the worker thread."""
        if tag == "stderr":
            # Distinguish warnings vs errors on stderr
            text = chunk.strip()
            if text.lower().startswith("warning") or "warning" in text.lower():
                # Log warnings in yellow without interrupting flow
                self.append_to_log(chunk, color='yellow')
            else:
                # Handle errors via common error handler
                self._show_error(chunk)
            return

        if self.current_operation == 'verify' and tag == 'stdout':
            # Parse JSON chunks for verify operations
            self._process_json_chunk(chunk)
            return
        # Normal stdout: timestamped output
        self.append_to_log(chunk)

    @pyqtSlot(int)
    def _gui_operation_finished(self, return_code: int):
        """Handles the completion of a VCL operation from the worker thread."""
        self.progress_bar.setVisible(False)  # Hide progress bar when operation completes
        # If an error dialog was shown during this operation, suppress success/failure logs and clear status
        if self._error_shown:
            self.status_bar.clearMessage()
            self.current_operation = None
            return
        self.compile_button.setEnabled(True)
        self.verify_button.setEnabled(True)
        self.stop_button.setVisible(False)
        self.stop_button.setEnabled(False)

        if return_code == 0: # Success
            msg = f"{self.current_operation.capitalize()} completed successfully."
            self.status_bar.showMessage(msg, 5000)
            self.append_to_log(f"\n--- {self.current_operation.capitalize()} finished successfully. ---")
            # If verify, list any failed properties and their queries
            if self.current_operation == 'verify':
                try:
                    failures = decode_counter_examples()
                    if failures:
                        # Group failures by property name
                        groups = {}
                        for key, tensor in failures.items():
                            # key format: '<property>-assignments-<var>'
                            prop = key.split('-assignments-')[0]
                            groups.setdefault(prop, []).append((key, tensor))
                        # Log each property's result
                        for prop, items in groups.items():
                            # Property header
                            self.append_to_log(f"  {prop}", color='red')
                            # Result line
                            self.append_to_log(f"    Verifier found a counterexample", color='red')
                            # Show sample vector for each counterexample variable
                            for _, tensor in items:
                                try:
                                    flat = tensor.flatten()
                                    sample = flat[:5].tolist()
                                    self.append_to_log(f"      x: {sample}", color='red')
                                except Exception:
                                    self.append_to_log(f"      x: {tensor}", color='red')
                    else:
                        # All passed
                        self.append_to_log("All properties hold - Verifier found no counterexamples", color='green')
                except Exception:
                    pass
        elif return_code == -1: # Stopped by user
            self.status_bar.showMessage(f"{self.current_operation.capitalize()} stopped by user.", 5000)
            self.append_to_log(f"\n--- {self.current_operation.capitalize()} stopped by user. ---")
        else: # Error
            # Handle error using common error handler
            self._show_error(f"\n--- {self.current_operation.capitalize()} failed. ---")
        
        self.query_tab.refresh_properties()
        if self.current_operation == "verify":
            # Wait a moment to ensure all files are written
            QTimer.singleShot(500, self.counter_example_tab.refresh_from_cache)
        self.current_operation = None

    def stop_current_operation(self):
        # Only stop if an operation is active
        if not self.current_operation:
            return
        self.status_bar.showMessage(f"Attempting to stop {self.current_operation}...", 0)
        self.stop_event.set()
        self.stop_button.setEnabled(False)
    
    def _start_vcl_operation(self, operation_name: str):
        """Common logic to start a VCL compile or verify operation."""
        # Reset error state for new operation
        self._error_shown = False

        if not self.save_before_operation():
            return

        self.input_view.assign_inputs(self.vcl_bindings)
        loaded_resources = self.input_view.get_loaded_inputs()
        if not all(loaded_resources):
            QMessageBox.warning(self, "Resource Error", "Please load all required resources (networks, datasets, parameters) before compilation/verification")
            return
        
        if operation_name == "verify":
            selected_properties = self.property_view.selected_properties()
            self.vcl_bindings.set_properties(selected_properties)
            if not selected_properties:
                QMessageBox.warning(self, "No Properties Selected", "Please select at least one property to verify.")
                return
            # Reset progress tracking
            self._json_buffer = ""
            self.verify_total_queries = 0
            self.verify_completed_queries = 0
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(0)

        self.status_bar.showMessage(f"Performing {operation_name.capitalize()}... Please wait.", 0)
        self.compile_button.setEnabled(False)
        self.verify_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.current_operation = operation_name
        # Show and reset progress bar for operation
        self.progress_bar.reset()
        self.progress_bar.setVisible(True)

        self.stop_event.clear()  # Clear any previous stop signal

        # Set up the operation callback and reset progress for verify
        if operation_name == "compile":
            operation = functools.partial(self.vcl_bindings.compile, stop_event=self.stop_event)
        elif operation_name == "verify":
            # Reset per-property progress tracking
            self._json_buffer = ""
            self.current_property_name = ""
            self.property_total_queries = 0
            self.property_completed_queries = 0
            self.progress_bar.reset()
            operation = functools.partial(self.vcl_bindings.verify, stop_event=self.stop_event)
        else:
            return
        # Create and start worker
        worker = OperationWorker(
            operation=operation,
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
        self._start_vcl_operation("compile")

    def verify_spec(self):
        self.compile_spec()  # Always compile before verify
        if self.current_operation is None:
            return
        # Wait for compilation to finish
        while self.current_operation == "compile":
            QApplication.processEvents()

        # Abort verify if compile error occurred
        if self._error_shown:
            return
        if not self.vcl_bindings.verifier_path:
            QMessageBox.warning(self, "Verification Error", "Please set the verifier path first.")
            return
        self._start_vcl_operation("verify")

    # --- Resource Management ---

    def show_version(self):
        QMessageBox.information(self, "Version", f"Current version: {VERSION}")

    def regenerate_input_boxes(self):
        """Regenerate input boxes, preserving any already-set values."""
        self.input_view.load_inputs(self.vcl_bindings)

    def regenerate_properties(self, selected_properties=None):
        """Regenerate property selector, preserving any previously selected values."""
        try:
            properties = self.vcl_bindings.properties()
            self.property_view.load_properties(properties)

            if selected_properties is not None:
                for prop_name, prop_widget in self.property_view.property_items:
                    # By default, all items are checked. Uncheck those not in selected_properties
                    if prop_name not in selected_properties:
                        prop_widget.set_checked(False)
        except Exception as e:
            tb_str = traceback.format_exc()
            # Use common error handler to log and display errors
            self._show_error(f"Error loading properties: {e}\n{tb_str}")

    # --- Type Checking ---

    def is_valid_vcl(self):
        # Clear previous editor errors
        self.editor.clear_errors()
        errors = self.vcl_bindings.type_check()
        if errors:
            # Show type check errors in a dialog
            msgs = []
            for error in errors:
                msgs.append(f"Problem: {error['problem']}")
                msgs.append(f"Fix: {error['fix']}")
                prov = error.get('provenance', {}).get('contents')
                if prov:
                    msgs.append(f"Provenance: {prov}")
            # Display type check errors in console using common error handler
            self._show_error(f"Type Check Errors\n" + "\n".join(msgs))
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

    def append_to_log(self, message: str, color: str = None):
        """Append a timestamped message to the log console, optionally colored."""
        # Format timestamp
        try:
            ts = datetime.now().strftime('%H:%M:%S')
            line = f"[{ts}] {message}"
        except Exception:
            line = message
        # Wrap in color if specified
        if color:
            line = f'<span style="color:{color}">{line}</span>'
        # Append rich text
        self.log_console.append(line)
        self.log_console.ensureCursorVisible()
        self.console_tab_widget.setCurrentWidget(self.log_console)
    
    def _show_error(self, message: str):
        """Display an error message in a pop-up dialog."""
        # Determine if this is the first error
        first_error = not self._error_shown
        # Always log the error to the console in red
        self.append_to_log(message, color='red')
        self.console_tab_widget.setCurrentWidget(self.log_console)
        if not first_error:
            # Subsequent errors are logged only
            return
        # First error: clear status and halt operation
        self.status_bar.clearMessage()
        self._error_shown = True
        self.stop_current_operation()
        # Restore UI controls
        self.compile_button.setEnabled(True)
        self.verify_button.setEnabled(True)
        self.stop_button.setVisible(False)
        self.stop_button.setEnabled(False)
        # Hide progress bar and clear operation state
        self.progress_bar.setVisible(False)
        self.current_operation = None
        # Modal dialogs suppressed; errors are highlighted in console

    def update_counter_example_modes(self):
        """Update counter example modes based on variables from properties."""
        modes = {}
        try:
            variable_renderers = self.property_view.get_variable_renderers()
            for key, renderer_class in variable_renderers.items():
                if renderer_class:
                    try:
                        # Instantiate the renderer class
                        renderer_instance = renderer_class()
                        modes[key] = renderer_instance
                    except Exception as e:
                        print(f"Error instantiating renderer {renderer_class.__name__} for {key}: {e}")
                        self.append_to_problems(f"Failed to instantiate renderer for {key}: {e}")
        except Exception as e:
            print(f"Error updating counter example modes: {e}")
            self.append_to_problems(f"Error updating counter example modes: {e}")
        self.counter_example_tab.set_modes(modes)

    def _process_json_chunk(self, chunk: str):
        """Accumulate and parse complete JSON objects from chunked output."""
        # Append new data to buffer
        self._json_buffer += chunk
        """
        Accumulate and parse complete JSON objects from chunked output using brace matching.
        """
        buf = self._json_buffer
        pos = 0
        length = len(buf)
        # Find JSON objects by matching braces
        start = buf.find('{', pos)
        while start != -1 and pos < length:
            brace_count = 0
            end = start
            for i in range(start, length):
                if buf[i] == '{':
                    brace_count += 1
                elif buf[i] == '}':
                    brace_count -= 1
                if brace_count == 0:
                    end = i
                    candidate = buf[start:end+1]
                    try:
                        obj = json.loads(candidate)
                        self._handle_json_event(obj)
                    except ValueError:
                        # Incomplete or invalid JSON
                        pass
                    pos = end + 1
                    break
            else:
                # No complete JSON object found
                break
            start = buf.find('{', pos)
        # Retain unprocessed part of buffer
        self._json_buffer = buf[pos:]

    def _init_property(self, prop: str, total: int):
        """Initialize progress bar for a new property."""
        self.current_property_name = prop
        self.property_total_queries = total
        self.property_completed_queries = 0
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"{prop}: %v/%m (%p%)")

    def _end_property_transition(self):
        """End transition pause and allow next property start."""
        self._waiting_transition = False

    def _handle_json_event(self, event):
        """Update progress bar based on JSON verification events."""
        # Some JSON chunks may be lists of events
        if isinstance(event, list):
            for ev in event:
                self._handle_json_event(ev)
            return
        tag = event.get('tag')
        # Human-readable logging for JSON events
        if tag == 'VerificationStart':
            self.append_to_log('Verification started', color='blue')
        elif tag == 'VerificationFinish':
            self.append_to_log('Verification finished successfully', color='blue')
        elif tag == 'MultiPropertyStart':
            contents = event.get('contents')
            if not isinstance(contents, dict):
                contents = {}
            pname = contents.get('propertyName', '')
            self.append_to_log(f"Batch start for '{pname}'", color='blue')
        elif tag == 'MultiPropertyFinish':
            contents = event.get('contents')
            if not isinstance(contents, dict):
                contents = {}
            pname = contents.get('propertyName', '')
            self.append_to_log(f"Batch finish for '{pname}'", color='blue')
        # Handle per-property progress
        if tag == 'PropertyStart':
            contents = event.get('contents')
            if not isinstance(contents, dict):
                contents = {}
            prop = contents.get('propertyName', '')
            total = contents.get('numberOfQueries', 0)
            # Log property start
            self.append_to_log(f"Property '{prop}' started ({total} queries)", color='green')
            # Schedule or perform initialization based on transition state
            def init_prop():
                self._init_property(prop, total)
            if self._waiting_transition:
                QTimer.singleShot(self.property_pause_ms, init_prop)
            else:
                init_prop()
        elif tag == 'QueryStart':
            contents = event.get('contents')
            if not isinstance(contents, dict):
                contents = {}
            qid = contents.get('queryID', '')
            self.append_to_log(f"Query {qid} started", color='black')
            # Show halfway progress if available
            if self.property_total_queries > 0:
                half_value = math.ceil(self.property_completed_queries + 0.5)
                self.progress_bar.setValue(half_value)
        elif tag == 'QueryFinish':
            contents = event.get('contents')
            if not isinstance(contents, dict):
                contents = {}
            qid = contents.get('queryID', '')
            # Increment completed queries
            self.property_completed_queries += 1
            self.progress_bar.setValue(self.property_completed_queries)
            self.append_to_log(f"Query {qid} finished", color='black')
        elif tag == 'PropertyFinish':
            # Ensure progress is complete for this property
            self.progress_bar.setValue(self.property_total_queries)
            self.append_to_log(f"Property '{self.current_property_name}' finished", color='green')
            # Enter transition pause before next property
            self._waiting_transition = True
            QTimer.singleShot(self.property_pause_ms, self._end_property_transition)