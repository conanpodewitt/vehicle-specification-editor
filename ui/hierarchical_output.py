import os
import re
import json
from PyQt6.QtWidgets import QVBoxLayout, QSizePolicy, QWidget
from pathlib import Path

# Import high-level node editor components
from ui.view.verification.blocks import Status, PropertyQuantifier
from ui.view.graphics_scene import GraphicsScene
from ui.view.graphics_view import GraphicsView
from ui.view.verification import VerificationWorkflow

CACHE_LOCATION = os.path.join(os.path.dirname(__file__), "../temp/cache")


class HeirarchicalOutput(QWidget):
    """Verification node editor widget for displaying verification workflows"""
    
    def __init__(self, parent=None, cache_location=CACHE_LOCATION):
        super().__init__(parent)
        self.cache_location = Path(cache_location)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Setup node editor
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the graphics scene and view
        self.graphics_scene = GraphicsScene()
        self.graphics_view = GraphicsView(self.graphics_scene)
        layout.addWidget(self.graphics_view)
        self.workflow_generator = VerificationWorkflow(self.graphics_scene, self.graphics_view)

        # Generate the initial workflow
        self.mock_verification_output()
    
    def clear(self):
        """Clear the workflow"""
        self.workflow_generator.clear_workflow()
    
    def mock_verification_output(self):
        """Create the verification workflow from cache data"""
        glob_pattern = "property*.vcl-plan"
        files = list(self.cache_location.glob(glob_pattern))
        sort_key = lambda p: int(re.findall(r"(\d+)", p.stem)[-1])
        files.sort(key=sort_key)

        for file in files:
            plan_file = self.cache_location / f"{file.stem}.vcl-plan"
            plan_json = json.loads(plan_file.read_text()) if plan_file.exists() else {}
            is_negated = plan_json["queryMetaData"]["contents"]["contents"]['negated']

            property_type = PropertyQuantifier.FOR_ALL if is_negated else PropertyQuantifier.EXISTS
            self.workflow_generator.add_property(property_type, title=file.stem)

        for prop in self.workflow_generator.properties:
            glob_pattern = f"{prop.title}-query*.txt"
            files = list(self.cache_location.glob(glob_pattern))
            files.sort(key=sort_key)
            for i, file in enumerate(files):
                query_block = self.workflow_generator.add_query(i + 1, prop, is_negated=is_negated)
                
                if i == len(files) - 1:
                    query_status = Status.DISPROVEN if is_negated else Status.VERIFIED
                    self.workflow_generator.add_witness(query_block)
                else:
                    query_status = Status.VERIFIED if is_negated else Status.DISPROVEN

                self.workflow_generator.update_status(query_block, query_status)