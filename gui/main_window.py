from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QMenuBar, QStatusBar, QLabel, QGroupBox,
    QPushButton, QMenu, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
import os
import sys

from core.engine import InferenceEngine, TORCH_COMPILE_AVAILABLE
from core.worker import InferenceWorker
from utils.config import AppConfig
from utils.video_io import get_video_info
from gui.widgets.input_panel import InputPanel
from gui.widgets.settings_panel import SettingsPanel
from gui.widgets.progress_panel import ProgressPanel
from gui.dialogs.model_downloader import ModelDownloaderDialog
from gui.dialogs import build_info


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RIFE Interpolator")
        self.setMinimumSize(800, 500)
        self.resize(1000, 650)

        self.config = AppConfig()
        self.engine = InferenceEngine(fp16=self.config.default_fp16)
        self.worker = None
        self._current_input_files = []
        self._current_mode = "video"

        self._init_menu()
        self._init_ui()
        self._init_statusbar()

        info = self.engine.device_info
        if info["type"] != "cuda" or not info.get("fp16_supported", False):
            self.settings_panel.check_fp16.setChecked(False)
            self.settings_panel.check_fp16.setEnabled(False)

        if info["type"] != "cuda" or not TORCH_COMPILE_AVAILABLE:
            self.settings_panel.check_compile.setChecked(False)
            self.settings_panel.check_compile.setEnabled(False)
            if not TORCH_COMPILE_AVAILABLE and info["type"] == "cuda":
                self.settings_panel.check_compile.setToolTip(
                    "torch.compile unavailable — update PyTorch or Python")

        if info["type"] not in ("cuda", "mps"):
            self.settings_panel.check_force_cpu.setChecked(True)
            self.settings_panel.check_force_cpu.setEnabled(False)
            self.settings_panel.check_force_cpu.setText("CPU mode (no GPU detected)")

        loaded = self._try_auto_load_model()
        if not loaded:
            QTimer.singleShot(500, self._offer_download)

    def _init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        load_model_action = QAction("Load Model...", self)
        load_model_action.triggered.connect(self._load_model_dialog)
        file_menu.addAction(load_model_action)

        download_model_action = QAction("Download Model...", self)
        download_model_action.triggered.connect(self._download_model)
        file_menu.addAction(download_model_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        quit_action.setShortcut("Ctrl+Q")
        file_menu.addAction(quit_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.input_panel = InputPanel(self.config)
        self.input_panel.input_ready.connect(self._on_input_ready)
        left_layout.addWidget(self.input_panel)

        self.settings_panel = SettingsPanel(self.config)

        self.settings_panel.setMinimumHeight(self.settings_panel.sizeHint().height())

        scroll = QScrollArea()
        scroll.setWidget(self.settings_panel)
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        left_layout.addWidget(scroll)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.progress_panel = ProgressPanel()
        self.progress_panel.btn_process.clicked.connect(self._start_processing)
        self.progress_panel.btn_cancel.clicked.connect(self._cancel_processing)
        right_layout.addWidget(self.progress_panel)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)

    def _init_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.avg_fps_label = QLabel("")
        self.status_bar.addPermanentWidget(self.avg_fps_label)
        self.gpu_label = QLabel(self._gpu_status_text())
        self.status_bar.addPermanentWidget(self.gpu_label)
        self.model_status = QLabel("Model: not loaded")
        self.status_bar.addPermanentWidget(self.model_status)
        self.status_bar.showMessage("Ready")

        self._gpu_monitor_timer = QTimer(self)
        self._gpu_monitor_timer.timeout.connect(self._update_gpu_stats)
        self._gpu_monitor_timer.start(5000)

    def _update_gpu_stats(self):
        if self.engine.device.type != "cuda":
            return
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                line = result.stdout.strip()
                if "," in line:
                    temp, util = line.split(",")
                    temp = temp.strip()
                    util = util.strip()
                    self.gpu_label.setText(
                        f"GPU: {temp}\u00b0C | {util}%")
        except Exception:
            pass

    def _gpu_status_text(self):
        info = self.engine.device_info
        if info["type"] == "cuda":
            parts = [f"GPU: {info['name']}", f"CC {info['compute']}"]
            if info["fp16"]:
                parts.append("FP16 ON")
            parts.append(info.get("fp16_note", ""))
            return " | ".join(p for p in parts if p)
        elif info["type"] == "mps":
            return "GPU: Apple Metal (MPS)"
        else:
            return "Device: CPU only"

    def _try_auto_load_model(self):
        checkpoint_dir = os.path.expanduser(self.config.checkpoint_path)
        os.makedirs(checkpoint_dir, exist_ok=True)

        # Scan for .pkl files in checkpoint dir
        pkl_files = []
        if os.path.isdir(checkpoint_dir):
            pkl_files = sorted([
                os.path.join(checkpoint_dir, f)
                for f in os.listdir(checkpoint_dir)
                if f.endswith(".pkl")
            ], key=os.path.getmtime, reverse=True)

        if pkl_files:
            ckpt_file = pkl_files[0]
            try:
                self.engine.load_model(ckpt_file)
                self.model_status.setText(f"Model: loaded ({os.path.basename(ckpt_file)})")
                self._update_process_enabled()
                self.status_bar.showMessage("Model loaded successfully", 3000)
                return True
            except Exception as e:
                QMessageBox.warning(self, "Model Load Error", str(e))
        return False

    def _offer_download(self):
        if self.engine.is_loaded:
            return
        reply = QMessageBox.question(
            self, "No Model Found",
            "No pretrained RIFE model is loaded.\n\n"
            "Would you like to download one automatically?\n"
            "(Models are ~195 MB each.)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self._download_model()

    def _download_model(self):
        output_dir = os.path.expanduser(self.config.checkpoint_path)
        os.makedirs(output_dir, exist_ok=True)

        dialog = ModelDownloaderDialog(output_dir, self)
        if dialog.exec() == ModelDownloaderDialog.Accepted:
            path = dialog.get_downloaded_path()
            if not path or not os.path.isfile(path):
                QMessageBox.critical(self, "Download Error",
                    "Download completed but the model file was not found.")
                return

            try:
                self.engine.load_model(path)
                self.config.checkpoint_path = output_dir
                self.model_status.setText(f"Model: loaded ({os.path.basename(path)})")
                self._update_process_enabled()
                self.status_bar.showMessage(f"Model loaded: {os.path.basename(path)}", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Model Load Error",
                    f"Downloaded but cannot load:\n{e}")

    def _load_model_dialog(self):
        start_dir = os.path.expanduser(self.config.checkpoint_path)
        os.makedirs(start_dir, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self, "Load RIFE Model", start_dir,
            "PyTorch Checkpoints (*.pkl *.pth *.pt);;All Files (*)"
        )
        if not path:
            return
        try:
            self.engine.load_model(path)
            self.config.checkpoint_path = os.path.dirname(path)
            self.model_status.setText(f"Model: loaded ({os.path.basename(path)})")
            self._update_process_enabled()
            self.status_bar.showMessage(f"Model loaded: {os.path.basename(path)}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Model Load Error", str(e))

    def _on_input_ready(self, files, mode):
        self._current_input_files = files
        self._current_mode = mode
        self._update_process_enabled()

        if mode == "video" and len(files) == 1:
            info = get_video_info(files[0])
            if info:
                self.settings_panel.set_video_info(info)

                # Auto-set scale for high-res video
                max_dim = max(info["width"], info["height"])
                current_scale = self.settings_panel.spin_scale.value()
                if max_dim >= 3840 and current_scale >= 0.8:
                    self.settings_panel.spin_scale.setValue(0.5)
                    self.status_bar.showMessage(
                        "4K+ video detected — Scale auto-set to 0.5 for speed", 8000)
                elif max_dim >= 2560 and current_scale >= 0.8:
                    self.settings_panel.spin_scale.setValue(0.75)
                    self.status_bar.showMessage(
                        "1440p video detected — Scale auto-set to 0.75", 5000)

    def _update_process_enabled(self):
        has_model = self.engine.is_loaded
        has_input = len(self._current_input_files) > 0
        self.progress_panel.btn_process.setEnabled(has_model and has_input)

    def _start_processing(self):
        if not self.engine.is_loaded:
            return
        if not self._current_input_files:
            return

        settings = self.settings_panel.get_settings()

        if self._current_mode == "video":
            input_path = self._current_input_files[0]
            base = os.path.splitext(os.path.basename(input_path))[0]
            out_fmt = settings["format"]

            out_dir = self.config.last_output_dir or os.path.expanduser("~")
            if not os.path.isdir(out_dir):
                out_dir = os.path.expanduser("~")

            if out_fmt == "png (sequence)":
                out_dir = QFileDialog.getExistingDirectory(
                    self, "Select Output Directory for Frame Sequence", out_dir)
                if not out_dir:
                    return
                output_path = out_dir
                self.config.last_output_dir = out_dir
            else:
                default_name = os.path.join(out_dir, f"{base}_interpolated.{out_fmt}")
                out_path, selected_filter = QFileDialog.getSaveFileName(
                    self, "Save Output Video", default_name,
                    f"Videos (*.{out_fmt});;All Files (*)")
                if not out_path:
                    self.status_bar.showMessage("Save cancelled", 3000)
                    return
                if not os.path.splitext(out_path)[1]:
                    out_path += f".{out_fmt}"
                out_parent = os.path.dirname(out_path)
                if not os.path.isdir(out_parent):
                    QMessageBox.critical(self, "Invalid Path",
                        f"Output directory does not exist:\n{out_parent}")
                    return
                output_path = out_path
                self.config.last_output_dir = os.path.dirname(out_path)
                self.status_bar.showMessage(f"Output: {os.path.basename(out_path)}", 5000)
        else:
            input_path = self._current_input_files
            out_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
            if not out_dir:
                return
            output_path = out_dir
            self.config.last_output_dir = out_dir

        exp = settings["exp"]
        scale = settings["scale"]
        fps = settings["fps"] if self._current_mode == "video" else None

        self.engine.fp16 = settings["fp16"]
        self.engine.compile_enabled = settings.get("compile", False)

        num_threads = settings.get("num_threads", 4)
        force_cpu = settings.get("force_cpu", False)
        if force_cpu:
            import torch
            self.engine.device = torch.device("cpu")
            if self.engine.flownet is not None:
                self.engine.flownet.to("cpu")
        torch.set_num_threads(num_threads)

        encoding = {
            "codec": settings.get("codec", "h264"),
            "crf": settings.get("crf", 23),
            "preset": settings.get("preset", "medium"),
            "pix_fmt": settings.get("pix_fmt", "yuv420p"),
            "bit_depth": settings.get("bit_depth", 8),
        }

        self.worker = InferenceWorker(
            self.engine,
            input_path,
            output_path,
            mode=self._current_mode,
            exp=exp,
            scale=scale,
            fps=fps,
            TTA=settings["tta"],
            encoding=encoding,
        )
        self.worker.progress.connect(self.progress_panel.set_progress)
        self.worker.status_update.connect(self.progress_panel.set_status)
        self.worker.avg_fps_update.connect(self._on_avg_fps_update)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)

        self.progress_panel.set_processing(True)
        self.progress_panel.log_text.clear()
        self.progress_panel.set_status("Starting...")
        self.worker.start()

    def _cancel_processing(self):
        if not self.worker or not self.worker.isRunning():
            return
        reply = QMessageBox.question(
            self, "Cancel Processing",
            "Are you sure you want to cancel?\nProgress so far will be lost.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.worker.cancel()
            self.progress_panel.set_status("Cancelling...")

    def _on_avg_fps_update(self, text):
        self.avg_fps_label.setText(text)

    def _on_finished(self, result):
        self.avg_fps_label.setText("")
        self.progress_panel.set_processing(False)
        if result == "cancelled":
            self.status_bar.showMessage("Processing cancelled", 5000)
            self.progress_panel.set_status("Cancelled")
        else:
            self.status_bar.showMessage(f"Done: {result}", 10000)
            self.progress_panel.set_status(f"Completed: {result}")
            QMessageBox.information(self, "Done", f"Output saved to:\n{result}")

    def _on_error(self, message):
        self.progress_panel.set_processing(False)
        self.progress_panel.set_status("Error occurred")
        self.progress_panel.log(message)
        QMessageBox.critical(self, "Processing Error", message)

    def _show_about(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt

        dialog = QDialog(self)
        dialog.setWindowTitle("About RIFE Interpolator")
        dialog.setFixedSize(420, 280)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)

        # Logo + title row
        top = QHBoxLayout()
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "resources", "icon.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "usr", "share", "icons", "hicolor",
                "256x256", "apps", "rife-interpolator.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(
                "/usr", "share", "icons", "hicolor",
                "256x256", "apps", "rife-interpolator.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pix)
        top.addWidget(logo_label)

        title_layout = QVBoxLayout()
        title = QLabel("<b>RIFE Interpolator</b>")
        title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        title_layout.addWidget(title)
        title_layout.addWidget(QLabel(f"Version {build_info.VERSION}"))
        top.addLayout(title_layout)
        top.addStretch()
        layout.addLayout(top)

        # Info
        info = QLabel(
            "Real-Time Intermediate Flow Estimation<br>"
            "for Video Frame Interpolation<br><br>"
            "Based on ECCV 2022 paper by Huang et al.<br>"
            "Built with PySide6 and PyTorch"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()

        # Build info
        build_label = QLabel(
            f"<span style='color: #888;'>Build: {build_info.BUILD_DATE}<br>"
            f"IFNet params: 10,708,215</span>"
        )
        build_label.setWordWrap(True)
        layout.addWidget(build_label)

        btn = QPushButton("OK")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

        dialog.exec()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
        event.accept()
