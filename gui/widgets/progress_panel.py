from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QGroupBox, QTextEdit
)
from PySide6.QtCore import Qt

class ProgressPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        group = QGroupBox("Processing")
        group_layout = QVBoxLayout()

        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        group_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        group_layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.btn_process = QPushButton("Start Processing")
        self.btn_process.setObjectName("btn_process")
        self.btn_process.setEnabled(False)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setEnabled(False)
        btn_layout.addWidget(self.btn_process)
        btn_layout.addWidget(self.btn_cancel)
        group_layout.addLayout(btn_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        group_layout.addWidget(self.log_text)

        group.setLayout(group_layout)
        layout.addWidget(group)

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
