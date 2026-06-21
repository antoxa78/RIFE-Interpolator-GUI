import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from gui.main_window import MainWindow

STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Ubuntu", "Noto Sans", sans-serif;
    font-size: 12px;
}

QGroupBox {
    background-color: #262638;
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 14px;
    padding: 12px 10px 10px 10px;
    font-weight: bold;
    font-size: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    color: #89b4fa;
}

QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 5px;
    padding: 5px 14px;
    font-weight: bold;
    font-size: 11px;
}

QPushButton:hover {
    background-color: #585b70;
    border-color: #89b4fa;
}

QPushButton:pressed {
    background-color: #313244;
}

QPushButton:disabled {
    background-color: #313244;
    color: #6c7086;
    border-color: #45475a;
}

QPushButton#btn_process {
    background-color: #1e8650;
    border-color: #23a86c;
    color: #cdd6f4;
}

QPushButton#btn_process:hover {
    background-color: #23a86c;
}

QPushButton#btn_process:disabled {
    background-color: #313244;
    color: #6c7086;
    border-color: #45475a;
}

QPushButton#btn_cancel {
    background-color: #8b3a3a;
    border-color: #c94f4f;
}

QPushButton#btn_cancel:hover {
    background-color: #c94f4f;
}

QPushButton#btn_cancel:disabled {
    background-color: #313244;
    color: #6c7086;
    border-color: #45475a;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 12px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #45475a;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}

QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
    border: 1px solid #45475a;
    border-radius: 4px;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #45475a;
    border-radius: 3px;
    width: 14px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #585b70;
}

QProgressBar {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 5px;
    text-align: center;
    color: #cdd6f4;
    font-size: 11px;
    font-weight: bold;
    min-height: 18px;
    max-height: 18px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #45475a, stop:0.5 #89b4fa, stop:1 #a6e3a1);
    border-radius: 4px;
}

QCheckBox {
    spacing: 6px;
    color: #cdd6f4;
    font-size: 12px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #585b70;
    border-radius: 3px;
    background-color: #313244;
}

QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

QRadioButton {
    spacing: 6px;
    color: #cdd6f4;
    padding: 2px 0;
    font-size: 12px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #585b70;
    border-radius: 8px;
    background-color: #313244;
}

QRadioButton::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

QSlider::groove:horizontal {
    background: #313244;
    height: 5px;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #89b4fa;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

QSlider::sub-page:horizontal {
    background: #89b4fa;
    border-radius: 2px;
}

QListWidget {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 2px;
    color: #cdd6f4;
    font-size: 12px;
}

QListWidget::item {
    padding: 3px 6px;
    border-radius: 3px;
}

QListWidget::item:selected {
    background-color: #45475a;
    color: #cdd6f4;
}

QListWidget::item:hover {
    background-color: #3a3b50;
}

QTextEdit {
    background-color: #181825;
    color: #a6adc8;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 4px;
    font-family: "JetBrains Mono", "Fira Code", "Monospace", monospace;
    font-size: 10px;
    max-height: 80px;
}

QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
    font-size: 11px;
    padding: 1px 6px;
}

QStatusBar::item {
    border: none;
}

QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    padding: 1px 3px;
    font-size: 12px;
}

QMenuBar::item:selected {
    background-color: #313244;
    border-radius: 4px;
}

QMenu {
    background-color: #262638;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 3px;
}

QMenu::item {
    padding: 5px 20px;
    border-radius: 3px;
}

QMenu::item:selected {
    background-color: #45475a;
}

QSplitter::handle {
    background-color: #45475a;
    width: 1px;
}

QLabel {
    color: #cdd6f4;
}

QScrollBar:vertical {
    background: #1e1e2e;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
    min-height: 16px;
}

QScrollBar::handle:vertical:hover {
    background: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #1e1e2e;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: #45475a;
    border-radius: 4px;
    min-width: 16px;
}

QMessageBox {
    background-color: #262638;
    color: #cdd6f4;
}

QMessageBox QLabel {
    color: #cdd6f4;
}

QDialog {
    background-color: #262638;
    color: #cdd6f4;
}

QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 3px;
    padding: 3px 6px;
    font-size: 11px;
}
"""

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RIFE Interpolator")
    app.setOrganizationName("RIFEInterpolator")

    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    font = app.font()
    font.setPointSize(9)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
