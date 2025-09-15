import sys
import os
from PyQt6.QtWidgets import QApplication
from ui.main_widget import VCLEditor
from ui.vcl_bindings import CACHE_DIR

os.makedirs(CACHE_DIR, exist_ok=True)

def main():
    app = QApplication(sys.argv)
    # Set application style
    app.setStyle("Fusion")
    editor = VCLEditor()
    editor.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()