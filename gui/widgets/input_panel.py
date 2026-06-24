from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QGroupBox, QSlider, QSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QImage
from utils.video_io import get_video_info
import cv2
import os

class InputPanel(QWidget):
    input_ready = Signal(list, str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._current_mode = "video"
        self._selected_files = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)

        self.setStyleSheet("""
            InputPanel QGroupBox {
                font-weight: 600;
                margin-top: 4px;
                padding-top: 8px;
            }
            InputPanel QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }
        """)

        mode_group = QGroupBox("Input Mode")
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(4, 2, 4, 2)
        self.btn_video = QPushButton("Video")
        self.btn_video.setCheckable(True)
        self.btn_video.setChecked(True)
        self.btn_video.clicked.connect(lambda: self._set_mode("video"))
        self.btn_images = QPushButton("Images")
        self.btn_images.setCheckable(True)
        self.btn_images.clicked.connect(lambda: self._set_mode("images"))
        mode_layout.addWidget(self.btn_video)
        mode_layout.addWidget(self.btn_images)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        file_group = QGroupBox("Input Files")
        file_layout = QVBoxLayout()
        file_layout.setContentsMargins(4, 2, 4, 2)
        file_layout.setSpacing(2)
        self.file_list = QListWidget()
        self.file_list.setAcceptDrops(True)
        self.file_list.setMinimumHeight(80)
        self.file_list.setMaximumHeight(160)
        file_layout.addWidget(self.file_list)

        btn_layout = QHBoxLayout()
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_files)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self._clear_files)
        btn_layout.addWidget(btn_browse)
        btn_layout.addWidget(btn_clear)
        file_layout.addLayout(btn_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        info_group = QGroupBox("File Info")
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(4, 2, 4, 2)
        self.info_label = QLabel("No file selected")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

    def _set_mode(self, mode):
        self._current_mode = mode
        self.btn_video.setChecked(mode == "video")
        self.btn_images.setChecked(mode == "images")
        self._clear_files()

    def _browse_files(self):
        last_dir = self.config.last_input_dir if self.config else os.path.expanduser("~")
        if self._current_mode == "video":
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Video", last_dir,
                "Videos (*.mp4 *.MP4 *.avi *.AVI *.mov *.MOV *.mkv *.MKV *.webm *.WEBM *.gif *.GIF);;All Files (*)"
            )
            if path:
                self._set_files([path])
        else:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Select Images", last_dir,
                "Images (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)"
            )
            if len(paths) >= 2:
                sorted_paths = sorted(paths)
                self._set_files(sorted_paths[:2])

    def _clear_files(self):
        self.file_list.clear()
        self._selected_files = []
        self.info_label.setText("No file selected")

    def _set_files(self, files):
        self._selected_files = files
        self.file_list.clear()
        for f in files:
            self.file_list.addItem(os.path.basename(f))

        if self._current_mode == "video" and len(files) == 1:
            info = get_video_info(files[0])
            if info:
                self.info_label.setText(
                    f"Resolution: {info['width']}x{info['height']}\n"
                    f"FPS: {info['fps']:.2f}\n"
                    f"Frames: {info['frames']}\n"
                    f"Duration: {info['duration']:.1f}s\n"
                    f"Output FPS: {info['fps'] * 2:.2f} (2x)"
                )
            else:
                self.info_label.setText("Cannot read video info")
        elif self._current_mode == "images" and len(files) == 2:
            self.info_label.setText(f"2 images selected")
        else:
            count = len(files)
            self.info_label.setText(f"{count} file(s) selected")

        if self.config and files:
            self.config.last_input_dir = os.path.dirname(files[0])

        self.input_ready.emit(files, self._current_mode)
