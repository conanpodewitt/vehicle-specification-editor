import os
import json

from PyQt6.QtWidgets import QTabWidget, QTextEdit, QTabBar, QSizePolicy, QWidget, QVBoxLayout, QComboBox, QLabel, QHBoxLayout
from PyQt6.QtCore import pyqtSignal
from pathlib import Path

from vehicle_gui.query_view.verification.blocks import Status, PropertyQuantifier
from vehicle_gui.query_view.graphics.block_graphics import BlockGraphics
from vehicle_gui.query_view.graphics.graphics_scene import GraphicsScene
from vehicle_gui.query_view.graphics.graphics_view import GraphicsView
from vehicle_gui.query_view.verification import VerificationWorkflow
from vehicle_gui.vcl_bindings import CACHE_DIR


class PropertyLoader:
    """Handles loading and parsing of VCL properties"""
    
    def __init__(self, workflow_generator):
        self.workflow_generator = workflow_generator
        self.global_query_id = 0
        self.property_name = None
    
    def load_property(self, property_name: str, cache_location: Path):
        """Load a property and create its workflow"""
        self.global_query_id = 0
        self.workflow_generator.clear_workflow()
        self.property_name = property_name
        plan_path = cache_location / f"{property_name}.vcl-plan"
        if plan_path.exists():
            self._create_workflow_from_plan(str(plan_path), property_name)
        else:
            raise FileNotFoundError(f"Property plan file not found: {plan_path}")
    
    def _create_workflow_from_plan(self, plan_path: str, title: str):
        """Create workflow from VCL plan file using pure JSON structure"""
        try:
            with open(plan_path, 'r') as f:
                plan_data = json.load(f)
            prop = self.workflow_generator.add_property(title=title)

            # Extract the root structure from the plan
            query_meta = plan_data.get('queryMetaData', {}).get('contents', {})
            
            # Handle flat structure with single disjunction of Queries
            if query_meta.get('tag') == 'Query':
                contents = query_meta.get('contents', {})
                queries = contents.get('queries', {}).get('unDisjunctAll', [])
                or_block = self.workflow_generator.add_or(prop)
                negated = contents.get('negated', False)
                for _ in queries:
                    self.global_query_id += 1
                    query_path = os.path.join(CACHE_DIR, f"{self.property_name}-query{self.global_query_id}.txt")
                    self.workflow_generator.add_query(self.global_query_id, or_block, query_path, is_negated=negated)

            # Handle multi-level structure
            else:
                self._parse_node(prop, query_meta)
                
            self.workflow_generator._position_children_centered(prop)

        except Exception as e:
            print(f"Error loading {title}: {e}")
            return self.workflow_generator.add_property(title=f"{title} (Error)")
    
    def _parse_node(self, parent_block, item):
        """Parse a single item from the vcl-plan structure - relies on actual JSON structure"""
        tag = item.get('tag', '')
        contents = item.get('contents', {})
        
        if tag == 'Disjunct':
            sub_items = contents.get('unDisjunctAll', [])
            or_block = self.workflow_generator.add_or(parent_block)
            for sub_item in sub_items:
                self._parse_node(or_block, sub_item)

        elif tag == 'Conjunct':
            sub_items = contents.get('unConjunctAll', [])
            and_block = self.workflow_generator.add_and(parent_block)
            for sub_item in sub_items:
                self._parse_node(and_block, sub_item)

        elif tag == 'Query':
            queries = contents.get('queries', {}).get('unDisjunctAll', [])
            negated = contents.get('negated', False)
            
            for _ in queries:
                self.global_query_id += 1
                query_path = os.path.join(CACHE_DIR, f"{self.property_name}-query{self.global_query_id}.txt")
                self.workflow_generator.add_query(self.global_query_id, parent_block, query_path, is_negated=negated)


class QueryTab(QTabWidget):
    """Verification node editor widget with property dropdown navigation"""
    property_changed = pyqtSignal(str)
    
    def __init__(self, parent=None, cache_location=CACHE_DIR):
        super().__init__(parent)
        self.cache_location = Path(cache_location)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Setup tab behavior
        self.setMovable(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._close_tab)
        self.tabBar().tabMoved.connect(self._refresh_close_buttons)
        self.currentChanged.connect(self._refresh_close_buttons)
        
        # Create workflow components
        self.graphics_scene = GraphicsScene()
        self.graphics_view = GraphicsView(self.graphics_scene)
        self.workflow_generator = VerificationWorkflow(self.graphics_scene, self.graphics_view)
        self.property_loader = PropertyLoader(self.workflow_generator)
        
        # Create and add workflow tab
        self._workflow_widget = self._create_workflow_widget()
        self.addTab(self._workflow_widget, "Workflow")
        self.setCurrentIndex(0)  # Ensure the workflow tab is selected
        self._refresh_close_buttons()
        
        # Connect signals and load initial property
        BlockGraphics.signals.query_double_clicked.connect(self._on_query_double_clicked)
        self._populate_property_dropdown()
        self._load_current_property()
    
    def _create_workflow_widget(self):
        """Create workflow widget with property dropdown"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Property selection header
        header = QHBoxLayout()
        header.addWidget(QLabel("Property:"))
        
        self.property_dropdown = QComboBox()
        self.property_dropdown.setMinimumWidth(150)
        self.property_dropdown.currentTextChanged.connect(self._on_property_changed)
        header.addWidget(self.property_dropdown)
        header.addStretch()
        
        # Add to main layout
        layout.addLayout(header)
        layout.addWidget(self.graphics_view)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        return widget
    
    def _populate_property_dropdown(self):
        """Populate dropdown with available properties"""
        properties = []
        self.property_dropdown.clear()

        if self.cache_location.exists():
            pattern = "*.vcl-plan"
            plan_files = list(self.cache_location.glob(pattern))
            properties.extend([f.stem for f in plan_files])

        self.property_dropdown.addItems(properties if properties else ["No properties found"])
    
    def _on_property_changed(self, property_name: str):
        """Handle property selection change"""
        if property_name and property_name != "No properties found":
            self._load_current_property()
            self.property_changed.emit(property_name)
    
    def _load_current_property(self):
        """Load the currently selected property"""
        property_name = self.property_dropdown.currentText()
        if property_name and property_name != "No properties found":
            self.property_loader.load_property(property_name, self.cache_location)
    
    def _on_query_double_clicked(self, file_path: str, tab_title: str):
        """Handle query double-click by opening file in new tab"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            self.add_text_tab(tab_title, content)
        except Exception as e:
            error_content = f"Error reading query file: {file_path}\n\nError: {str(e)}"
            self.add_text_tab(f"Error - {tab_title}", error_content)
    
    def add_text_tab(self, title: str, text: str) -> int:
        """Add a new text tab"""
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(text)
        idx = self.addTab(editor, title)
        self._refresh_close_buttons()
        return idx
    
    def clear(self):
        """Clear workflow and text tabs"""
        self.workflow_generator.clear_workflow()
        self._clear_text_tabs()
    
    def refresh_properties(self):
        """Refresh available properties list"""
        current = self.property_dropdown.currentText()
        self._populate_property_dropdown()
        
        # Restore selection if possible
        index = self.property_dropdown.findText(current)
        if index != -1:
            self.property_dropdown.setCurrentIndex(index)
        else:
            self.property_dropdown.setCurrentIndex(0)
        self._load_current_property()
    
    def _clear_text_tabs(self):
        """Remove all text tabs except workflow tab"""
        for i in range(self.count() - 1, -1, -1):   # Start from bottom
            widget = self.widget(i)
            if widget is not self._workflow_widget:
                self.removeTab(i)
                widget.deleteLater()
    
    def _close_tab(self, index: int):
        """Close tab if not the workflow tab"""
        if 0 <= index < self.count():
            widget = self.widget(index)
            if widget is not self._workflow_widget:
                self.removeTab(index)
                widget.deleteLater()
    
    def _refresh_close_buttons(self):
        """Update close button visibility"""
        tb = self.tabBar()
        for i in range(self.count()):
            widget = self.widget(i)
            is_closable = widget is not self._workflow_widget   # Only workflow tab is not closable
            btn = tb.tabButton(i, QTabBar.ButtonPosition.RightSide)
            if btn:
                btn.setVisible(is_closable)
                btn.setEnabled(is_closable)