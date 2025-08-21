import os
from PyQt6.QtWidgets import QVBoxLayout, QSizePolicy, QWidget
from pathlib import Path

# Import high-level node editor components
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
        self.create_verification_workflow()
    
    def clear(self):
        """Clear and recreate the verification workflow"""
        self.graphics_scene.clear()
        self.workflow_generator = VerificationWorkflow(self.graphics_scene)
        self.create_verification_workflow()
    
    def create_verification_workflow(self):
        """Create the verification workflow from cache data"""
        # In the future, this would parse cache files and create a workflow from real data
        # For now, it creates an example workflow
        self.workflow_generator.create_example_workflow()