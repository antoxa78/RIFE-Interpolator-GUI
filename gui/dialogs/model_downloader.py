import os
import requests
import re
from html.parser import HTMLParser
from urllib.parse import urljoin
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QGroupBox, QRadioButton, QButtonGroup,
    QMessageBox
)
from PySide6.QtCore import QThread, Signal, Qt

MODELS = {
    "rife": {
        "name": "RIFE (ECCV 2022 paper)",
        "file_id": "1h42aGYPNJn2q8j_GVkS_yDu__G_UZ2GX",
        "filename": "flownet.pkl",
        "archive_name": "RIFE_trained_v6.zip",
        "size": "~38 MB",
        "description": "Standard RIFE model for IFNet. Best balance of speed and quality. Works for 2x-8x interpolation."
    },
}

GOOGLE_DRIVE_URL = "https://docs.google.com/uc?export=download"
CONFIRM_PATTERN = re.compile(r'<form[^>]*action="([^"]*)"[^>]*>.*?</form>', re.DOTALL)
INPUT_PATTERN = re.compile(r'<input[^>]*name="([^"]*)"[^>]*value="([^"]*)"[^>]*>')
NONCE_PATTERN = re.compile(r'id="download-form"[^>]*nonce="(\S+)"')


def _extract_download_params(html_text):
    form_match = re.search(r'<form[^>]*id="download-form"[^>]*action="([^"]*)"[^>]*>(.*?)</form>', html_text, re.DOTALL)
    if not form_match:
        return None, None
    download_url = form_match.group(1).replace("&amp;", "&")
    form_content = form_match.group(2)
    inputs = dict(re.findall(r'<input[^>]*name="([^"]*)"[^>]*value="([^"]*)"', form_content))
    return download_url, inputs


class DownloadWorker(QThread):
    progress = Signal(int, int)
    status = Signal(str)
    finished = Signal(str, str)
    error = Signal(str)

    def __init__(self, model_key, output_path):
        super().__init__()
        self.model_key = model_key
        self.output_path = output_path

    def run(self):
        try:
            model = MODELS[self.model_key]
            file_id = model["file_id"]

            self.status.emit("Connecting to Google Drive...")

            session = requests.Session()
            response = session.get(
                GOOGLE_DRIVE_URL,
                params={"id": file_id, "export": "download"},
                stream=True,
            )

            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                html_sample = response.text[:20000]
                download_url, params = _extract_download_params(html_sample)
                if download_url and params:
                    self.status.emit("Confirming download...")
                    response = session.get(download_url, params=params, stream=True)

            total = int(response.headers.get("content-length", 0))
            if total == 0:
                self.status.emit("Downloading (unknown size)...")
            else:
                self.status.emit(f"Downloading {model['name']} ({total // (1024*1024)} MB)...")

            downloaded = 0
            with open(self.output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if self.isInterruptionRequested():
                        f.close()
                        os.remove(self.output_path)
                        self.error.emit("Download cancelled")
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            self.progress.emit(downloaded, total)

            self.status.emit("Download complete, verifying...")

            file_size = os.path.getsize(self.output_path)
            if file_size < 1000000:
                os.remove(self.output_path)
                self.error.emit(
                    f"Downloaded file is too small ({file_size} bytes). "
                    "Google Drive may have blocked the download. Try again later."
                )
                return

            if self.output_path.endswith(".zip"):
                is_zip = True
            elif file_size > 0:
                with open(self.output_path, "rb") as fh:
                    is_zip = fh.read(2) == b"PK"
            else:
                is_zip = False

            if is_zip:
                self.status.emit("Extracting archive...")
                import zipfile
                extract_dir = os.path.dirname(self.output_path)
                with zipfile.ZipFile(self.output_path, "r") as zf:
                    zf.extractall(extract_dir)
                os.remove(self.output_path)

                # Recursively find the first .pkl file
                pkl_files = []
                for root, _, files in os.walk(extract_dir):
                    for f in files:
                        if f.endswith(".pkl"):
                            pkl_files.append(os.path.join(root, f))
                if pkl_files:
                    self.output_path = pkl_files[0]

            self.finished.emit(self.output_path, model["name"])

        except requests.exceptions.ConnectionError:
            self.error.emit("Network error: cannot connect to Google Drive. Check your internet connection.")
        except Exception as e:
            self.error.emit(f"Download failed: {type(e).__name__}: {e}")


class ModelDownloaderDialog(QDialog):
    def __init__(self, output_dir, parent=None):
        super().__init__(parent)
        self.output_dir = output_dir
        self.worker = None
        self._downloaded_path = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Download RIFE Model")
        self.setMinimumWidth(500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel(
            "Select a pretrained RIFE model to download.\n"
            "Models are ~195 MB each and will be saved to the checkpoints directory."
        ))

        model_group = QGroupBox("Available Models")
        model_layout = QVBoxLayout()
        self.model_group = QButtonGroup(self)

        first = True
        for key, model in MODELS.items():
            radio = QRadioButton(
                f"{model['name']} ({model['size']})\n{model['description']}"
            )
            radio.setProperty("model_key", key)
            self.model_group.addButton(radio)
            model_layout.addWidget(radio)
            if first:
                radio.setChecked(True)
                first = False

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.btn_download = QPushButton("Download")
        self.btn_download.clicked.connect(self._start_download)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_cancel.setEnabled(False)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_download)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _start_download(self):
        selected = self.model_group.checkedButton()
        if not selected:
            return

        model_key = selected.property("model_key")
        model = MODELS[model_key]
        archive_name = model.get("archive_name", model["filename"])
        output_path = os.path.join(self.output_dir, archive_name)
        pkl_path = os.path.join(self.output_dir, model["filename"])

        if os.path.exists(pkl_path):
            reply = QMessageBox.question(
                self, "File Exists",
                f"{model['filename']} already exists.\nOverwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.btn_download.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.status_label.setText("Starting download...")
        self.progress_bar.setValue(0)

        self.worker = DownloadWorker(model_key, output_path)
        self.worker.status.connect(self._on_status)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.status_label.setText("Cancelling...")
            self.btn_cancel.setEnabled(False)

    def _on_status(self, text):
        self.status_label.setText(text)

    def _on_progress(self, downloaded, total):
        if total > 0:
            pct = int(downloaded * 100 / total)
            self.progress_bar.setValue(pct)
            mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.status_label.setText(f"Downloading... {mb:.0f} / {total_mb:.0f} MB")

    def _on_finished(self, path, name):
        self._downloaded_path = path
        self.status_label.setText(f"Downloaded: {name}")
        self.progress_bar.setValue(100)
        self.btn_download.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.accept()

    def _on_error(self, message):
        self.status_label.setText(f"Error: {message}")
        self.btn_download.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        QMessageBox.critical(self, "Download Error", message)

    def get_downloaded_path(self):
        return self._downloaded_path
