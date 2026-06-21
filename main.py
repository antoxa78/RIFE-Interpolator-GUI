import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RIFE Interpolator")
    app.setOrganizationName("RIFEInterpolator")

    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
