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


class QueryTab(QTabWidget):
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
        """Create the verification workflow from hierarchical vcl-plan data"""
        complex_plan_path = "temp/mnist_cache/p.vcl-plan"
        abs_complex_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), complex_plan_path)
        
        if os.path.exists(abs_complex_path):
            self._create_hierarchical_workflow(abs_complex_path, "MNIST Property")
            return
        
    def _create_hierarchical_workflow(self, plan_path, title):
        """Create a hierarchical workflow from a vcl-plan file"""
        with open(plan_path, 'r') as f:
            plan_data = json.load(f)
        
        self._global_query_id = 0
        prop = self.workflow_generator.add_property(title=title)
        
        # Extract the root structure from the plan
        query_meta = plan_data.get('queryMetaData', {}).get('contents', {}).get('contents', {})
        root_disjuncts = query_meta.get('unDisjunctAll', [])
        
        # Parse the root level - this represents an OR at top level
        self._parse_tree(prop, root_disjuncts, is_disjunct=True)
        self.workflow_generator._position_children_centered(prop)

    def _parse_tree(self, parent_block, items, is_disjunct=True):
        """
        Recursively parse logical structure from vcl-plan data
        
        Args:
            parent_block: The parent block to attach children to
            items: List of items (queries, disjuncts, or conjuncts)
            is_disjunct: True if items are connected by OR, False for AND
        """
        if not items:
            return

        if len(items) == 1:
            self._parse_node(parent_block, items[0])
            return
        
        # Multiple items need a logical connector
        if is_disjunct:
            # Create OR block for multiple disjuncts
            or_block = self.workflow_generator.add_or(parent_block)
            for item in items:
                self._parse_node(or_block, item)
        else:
            # Create AND block for multiple conjuncts
            and_block = self.workflow_generator.add_and(parent_block)
            for item in items:
                self._parse_node(and_block, item)
    
    def _parse_node(self, parent_block, item):
        """
        Parse a single item from the vcl-plan structure
        
        Args:
            parent_block: The parent block to attach the item to
            item: Single item (Query, Disjunct, or Conjunct)
        """
        tag = item.get('tag', '')
        contents = item.get('contents', {})
        
        if tag == 'Query':
            # Extract query - use global query ID counter
            queries = contents.get('queries', {}).get('unDisjunctAll', [])
            for _ in queries:
                # Increment global query ID for each query
                self._global_query_id += 1
                query_text = f"Query {self._global_query_id}"
                self.workflow_generator.add_query(self._global_query_id, parent_block, query_text, is_negated=False)
        
        elif tag == 'Disjunct':
            # Recursive disjunct (OR)
            sub_items = contents.get('unDisjunctAll', [])
            self._parse_tree(parent_block, sub_items, is_disjunct=True)
        
        elif tag == 'Conjunct':
            # Recursive conjunct (AND)
            sub_items = contents.get('unConjunctAll', [])
            self._parse_tree(parent_block, sub_items, is_disjunct=False)