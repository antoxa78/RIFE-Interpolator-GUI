import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QGuiApplication

from gui.main_window import MainWindow

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("RIFE Interpolator")
    app.setOrganizationName("RIFEInterpolator")

    app.setStyle("Fusion")

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "resources", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    screen = QGuiApplication.primaryScreen()
    screen_height = screen.availableGeometry().height() if screen else 768
    font_size = max(8, min(14, int(screen_height * 9 / 768)))
    font = app.font()
    font.setPointSize(font_size)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
