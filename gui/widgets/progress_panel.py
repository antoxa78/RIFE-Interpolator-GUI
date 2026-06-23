from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QTextEdit
)
from PySide6.QtCore import Qt

class ProgressPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        self.btn_process = QPushButton("Start Processing")
        self.btn_process.setEnabled(False)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        btn_layout.addWidget(self.btn_process)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def set_status(self, text):
        self.status_label.setText(text)
        if text and text != "Ready":
            self.log_text.append(text)

    def set_progress(self, current, total):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)

    def set_processing(self, active):
        self.btn_process.setEnabled(not active)
        self.btn_cancel.setEnabled(active)
        self.progress_bar.setValue(0)
        if not active:
            self.status_label.setText("Ready")

    def log(self, message):
        self.log_text.append(message)
