import sys
import os
from PyQt6.QtWidgets import QApplication
from vehicle_gui.main_widget import VehicleGUI
from vehicle_gui import VEHICLE_DIR
from vehicle_gui.vcl_bindings import CACHE_DIR
from vehicle_gui.counter_example_view.counter_example_tab import RENDERERS_DIR
import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)

os.makedirs(VEHICLE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(RENDERERS_DIR, exist_ok=True)

def main():
    app = QApplication(sys.argv)
    # Set application style
    app.setStyle("Fusion")
    
    try:
        editor = VehicleGUI()
        editor.show()
        exit_code = app.exec()
        
        # Use os._exit to avoid Python cleanup that causes segfaults
        os._exit(exit_code)
        
    except Exception as e:
        print(f"Error during application execution: {e}")
        import traceback
        traceback.print_exc()
        os._exit(1)

if __name__ == "__main__":
    main()