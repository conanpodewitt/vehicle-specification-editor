import os
import re
import json
from PyQt6.QtWidgets import QTabWidget, QTextEdit, QTabBar, QSizePolicy
from pathlib import Path

# Import high-level node editor components
from ui.view.verification.blocks import Status, PropertyQuantifier
from ui.view.component.block_graphics import BlockGraphics
from ui.view.graphics_scene import GraphicsScene
from ui.view.graphics_view import GraphicsView
from ui.view.verification import VerificationWorkflow

CACHE_LOCATION = os.path.join(os.path.dirname(__file__), "../temp/cache")


class HeirarchicalOutput(QTabWidget):
    """Verification node editor widget for displaying verification workflows, query information, and counter-examples"""
    
    def __init__(self, parent=None, cache_location=CACHE_LOCATION):
        super().__init__(parent)
        self.cache_location = Path(cache_location)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setMovable(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._close_tab)
        self.tabBar().tabMoved.connect(self._refresh_close_buttons)
        self.currentChanged.connect(self._refresh_close_buttons)
        
        # Create the graphics scene and view
        self.graphics_scene = GraphicsScene()
        self.graphics_view = GraphicsView(self.graphics_scene)
        self.workflow_generator = VerificationWorkflow(self.graphics_scene, self.graphics_view)
        self._fixed_widget = self.graphics_view
        self.addTab(self._fixed_widget, "Workflow")     # Fixed tab for workflow
        self._refresh_close_buttons()

        # Connect to block signals for query double-click events
        BlockGraphics.signals.query_double_clicked.connect(self._on_query_double_clicked)

        # Generate the initial workflow
        self.mock_verification_output()
    
    
    def clear(self):
        """Clear the workflow"""
        self.workflow_generator.clear_workflow()
        self._clear_text_tabs()

    
    def add_text_tab(self, title: str, text: str) -> int:
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(text)
        idx = self.addTab(editor, title or "Untitled")
        self._refresh_close_buttons()
        return idx
    

    def _clear_text_tabs(self):
        """Remove all text tabs except the fixed workflow tab"""
        # Remove tabs from right to left to avoid index shifting
        for i in range(self.count() - 1, -1, -1):
            widget = self.widget(i)
            if not self._is_fixed(widget):
                self.removeTab(i)
                widget.deleteLater()
    

    def _on_query_double_clicked(self, file_path: str, tab_title: str):
        """Handle query double-click signal by opening file content in new tab"""
        try:
            # Read the query file content
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Create a new tab with the content
            self.add_text_tab(tab_title, content)
            
        except Exception as e:
            # If file reading fails, show error in a tab
            error_content = f"Error reading query file: {file_path}\n\nError: {str(e)}"
            self.add_text_tab(f"Error - {tab_title}", error_content)
    

    def _is_fixed(self, w) -> bool:
        return w is self._fixed_widget
    

    def _close_tab(self, index: int):
        if index < 0 or index >= self.count():
            return
        w = self.widget(index)
        if self._is_fixed(w):
            return  # ignore close on the fixed tab
        self.removeTab(index)
        w.deleteLater()

    
    def _refresh_close_buttons(self, *_):
        tb = self.tabBar()
        for i in range(self.count()):
            w = self.widget(i)
            unclosable_tab = self._is_fixed(w)
            for side in (QTabBar.ButtonPosition.LeftSide, QTabBar.ButtonPosition.RightSide):
                btn = tb.tabButton(i, side)
                if btn:
                    btn.setVisible(not unclosable_tab)
                    btn.setEnabled(not unclosable_tab)


    def mock_verification_output(self):
        """Create the verification workflow from cache data"""
        glob_pattern = "property*.vcl-plan"
        plan_files = list(self.cache_location.glob(glob_pattern))
        sort_key = lambda p: int(re.findall(r"(\d+)", p.stem)[-1])
        plan_files.sort(key=sort_key)

        for pfile in plan_files:
            try:
                plan_json = json.loads(pfile.read_text())
                is_negated = bool(plan_json["queryMetaData"]["contents"]["contents"]["negated"])
            except Exception:
                is_negated = False

            ptype = PropertyQuantifier.FOR_ALL if is_negated else PropertyQuantifier.EXISTS
            # total_num_queries = len(plan_json['queryMetaData']['contents']['contents']['queries']['unDisjunctAll'])
            prop = self.workflow_generator.add_property(ptype, title=pfile.stem)

            result_path = pfile.with_suffix('.vcl-result')
            verification_result = bool(result_path.read_text().strip())
            prop.verification_status = Status.VERIFIED if verification_result else Status.DISPROVEN

        for prop in self.workflow_generator.properties:
            glob_pattern = f"{prop.title}-query*.txt"
            q_files = list(self.cache_location.glob(glob_pattern))
            q_files.sort(key=sort_key)

            for i, qfile in enumerate(q_files, start=1):
                query_block = self.workflow_generator.add_query(i, prop, str(qfile), is_negated=is_negated)

                if i == len(q_files):
                    if prop.verification_status == Status.DISPROVEN and query_block.is_negated:
                        self.workflow_generator.add_witness(query_block)
                    elif prop.verification_status == Status.VERIFIED and not query_block.is_negated:
                        self.workflow_generator.add_witness(query_block)
                    query_status = prop.verification_status
                else:
                    if query_block.is_negated:
                        query_status = Status.VERIFIED
                    if not query_block.is_negated:
                        query_status = Status.DISPROVEN

                self.workflow_generator.update_status(query_block, query_status)