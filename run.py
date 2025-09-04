import sys
import os
from PyQt6.QtWidgets import QApplication
from ui.main_widget import VCLEditor

TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

def main():
    app = QApplication(sys.argv)
    # Set application style
    app.setStyle("Fusion")
    editor = VCLEditor()
    editor.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()