from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QDoubleSpinBox, QComboBox, QCheckBox, QGroupBox, QPushButton,
    QSlider
)
from PySide6.QtCore import Signal, Qt

class SettingsPanel(QWidget):
    settings_changed = Signal(dict)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._input_fps = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)

        self.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                margin-top: 6px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
            }
        """)

        interp_group = QGroupBox("Interpolation")
        interp_layout = QHBoxLayout()
        interp_layout.setSpacing(4)

        lbl = QLabel("Factor:")
        interp_layout.addWidget(lbl)
        self.spin_exp = QSpinBox()
        self.spin_exp.setRange(1, 6)
        self.spin_exp.setValue(self.config.default_exp if self.config else 2)
        self.spin_exp.setSuffix(f"x ({2 ** self.spin_exp.value()}x)")
        self.spin_exp.setMinimumWidth(80)
        self.spin_exp.setToolTip(
            "Frame multiplication factor (power of 2).\n"
            "1 = 2x, 2 = 4x, 3 = 8x, ..., 6 = 64x.\n"
            "More frames = smoother slow-motion\nbut longer processing time.")
        self.spin_exp.valueChanged.connect(self._on_exp_changed)
        interp_layout.addWidget(self.spin_exp)

        self.interp_fps_label = QLabel("")
        self.interp_fps_label.setToolTip("Detected input video frame rate")
        interp_layout.addWidget(self.interp_fps_label)

        lbl = QLabel("Scale:")
        interp_layout.addWidget(lbl)
        self.spin_scale = QDoubleSpinBox()
        self.spin_scale.setRange(0.1, 4.0)
        self.spin_scale.setSingleStep(0.1)
        self.spin_scale.setValue(self.config.default_scale if self.config else 1.0)
        self.spin_scale.setMinimumWidth(60)
        self.spin_scale.setToolTip(
            "Resolution scale factor.\n"
            "1.0 = original, 0.5 = half, 2.0 = double.\n"
            "Lower = faster, higher = sharper (uses more VRAM).")
        interp_layout.addWidget(self.spin_scale)

        scale_hint = QLabel("(downscale for 4K)")
        scale_hint.setToolTip("Recommended: 0.5 for 4K+, 0.75 for 1440p")
        interp_layout.addWidget(scale_hint)
        interp_layout.addStretch()

        interp_group.setLayout(interp_layout)
        layout.addWidget(interp_group)

        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()

        fps_layout = QHBoxLayout()
        lbl = QLabel("FPS:")
        lbl.setFixedWidth(50)
        fps_layout.addWidget(lbl)
        self.check_auto_fps = QCheckBox("Auto")
        self.check_auto_fps.setChecked(True)
        self.check_auto_fps.setToolTip(
            "Auto-calculate output FPS from input FPS\n"
            "multiplied by the interpolation factor.\n"
            "Uncheck to set a custom target FPS.")
        self.check_auto_fps.toggled.connect(self._on_auto_fps_toggled)
        fps_layout.addWidget(self.check_auto_fps)
        self.spin_fps = QDoubleSpinBox()
        self.spin_fps.setRange(1, 240)
        self.spin_fps.setDecimals(2)
        self.spin_fps.setValue(60.0)
        self.spin_fps.setEnabled(False)
        self.spin_fps.setMinimumWidth(80)
        self.spin_fps.setToolTip(
            "Custom output frame rate.\n"
            "Lower than auto = slow-motion effect.\n"
            "Higher = speed-up.")
        fps_layout.addWidget(self.spin_fps)
        fps_layout.addStretch()
        output_layout.addLayout(fps_layout)

        fmt_layout = QHBoxLayout()
        lbl = QLabel("Format:")
        lbl.setFixedWidth(50)
        fmt_layout.addWidget(lbl)
        self.combo_format = QComboBox()
        self.combo_format.addItems(["mp4", "avi", "mov", "png (sequence)"])
        self.combo_format.setMinimumWidth(120)
        self.combo_format.setToolTip(
            "Output container format.\n"
            "mp4 = best compatibility\n"
            "png (sequence) = frame-by-frame for editing")
        fmt_layout.addWidget(self.combo_format)
        fmt_layout.addStretch()
        output_layout.addLayout(fmt_layout)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        enc_group = QGroupBox("Encoding")
        enc_vlayout = QVBoxLayout()
        enc_vlayout.setSpacing(2)
        enc_layout = QHBoxLayout()
        enc_layout.setSpacing(4)

        lbl = QLabel("Codec:")
        enc_layout.addWidget(lbl)
        self.combo_codec = QComboBox()
        self.combo_codec.addItems(["h264", "h265 (hevc)", "vp9", "av1", "ffv1"])
        idx = self.combo_codec.findText(self.config.default_codec if self.config else "h264")
        if idx >= 0:
            self.combo_codec.setCurrentIndex(idx)
        self.combo_codec.setMinimumWidth(90)
        self.combo_codec.setToolTip(
            "Video codec:\n"
            "h264 — best compatibility, small files\n"
            "h265 — 50% smaller at same quality\n"
            "vp9 — web-optimized (YouTube)\n"
            "av1 — next-gen, best compression\n"
            "ffv1 — mathematically lossless, archival")
        enc_layout.addWidget(self.combo_codec)

        lbl = QLabel("CRF:")
        enc_layout.addWidget(lbl)
        self.slider_crf = QSlider(Qt.Horizontal)
        self.slider_crf.setRange(0, 51)
        self.slider_crf.setValue(self.config.default_crf if self.config else 23)
        self.slider_crf.setMinimumWidth(60)
        self.slider_crf.setToolTip(
            "Constant Rate Factor (quality).\n"
            "0 = lossless (huge files)\n"
            "18 = visually lossless\n"
            "23 = default (good balance)\n"
            "28 = noticeable loss\n"
            "51 = worst quality")
        enc_layout.addWidget(self.slider_crf)
        self.label_crf = QLabel(str(self.slider_crf.value()))
        self.label_crf.setFixedWidth(20)
        enc_layout.addWidget(self.label_crf)

        lbl = QLabel("Preset:")
        enc_layout.addWidget(lbl)
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        idx = self.combo_preset.findText(self.config.default_preset if self.config else "medium")
        if idx >= 0:
            self.combo_preset.setCurrentIndex(idx)
        self.combo_preset.setMinimumWidth(90)
        self.combo_preset.setToolTip(
            "Encoding speed vs file size.\n"
            "faster = bigger file, less CPU\n"
            "slower = smaller file, more CPU")
        enc_layout.addWidget(self.combo_preset)

        lbl = QLabel("Pix:")
        enc_layout.addWidget(lbl)
        self.combo_pix_fmt = QComboBox()
        self.combo_pix_fmt.addItems(["yuv420p", "yuv422p", "yuv444p"])
        idx = self.combo_pix_fmt.findText(self.config.default_pix_fmt if self.config else "yuv420p")
        if idx >= 0:
            self.combo_pix_fmt.setCurrentIndex(idx)
        self.combo_pix_fmt.setMinimumWidth(60)
        self.combo_pix_fmt.setToolTip(
            "Chroma subsampling:\n"
            "4:2:0 — standard, 1/4 color res (default)\n"
            "4:2:2 — half color res, better for text/graphics\n"
            "4:4:4 — full color res, no subsampling")
        enc_layout.addWidget(self.combo_pix_fmt)

        lbl = QLabel("Bit:")
        enc_layout.addWidget(lbl)
        self.combo_bit_depth = QComboBox()
        self.combo_bit_depth.addItems(["8", "10", "12"])
        idx = self.combo_bit_depth.findText(str(self.config.default_bit_depth if self.config else 8))
        if idx >= 0:
            self.combo_bit_depth.setCurrentIndex(idx)
        self.combo_bit_depth.setMinimumWidth(40)
        self.combo_bit_depth.setToolTip(
            "Color bit depth per channel.\n"
            "8-bit = 16.7M colors (standard)\n"
            "10-bit = 1B colors (HDR, less banding)\n"
            "12-bit = 68B colors (pro mastering)")
        enc_layout.addWidget(self.combo_bit_depth)

        enc_vlayout.addLayout(enc_layout)

        lossless_row = QHBoxLayout()
        self.check_lossless = QCheckBox("Lossless (no compression)")
        self.check_lossless.setChecked(self.config.default_lossless if self.config else False)
        self.check_lossless.setToolTip(
            "Save video without any quality loss.\n"
            "Uses CRF 0 and full chroma (4:4:4).\n"
            "Produces very large files — only for archival.")
        self.check_lossless.toggled.connect(self._on_lossless_toggled)
        lossless_row.addWidget(self.check_lossless)
        lossless_row.addStretch()
        enc_vlayout.addLayout(lossless_row)

        enc_group.setLayout(enc_vlayout)
        layout.addWidget(enc_group)

        perf_group = QGroupBox("Performance")
        perf_layout = QVBoxLayout()
        perf_layout.setContentsMargins(4, 2, 4, 2)
        perf_layout.setSpacing(2)

        self.check_fp16 = QCheckBox("FP16 (half precision)")
        self.check_fp16.setChecked(self.config.default_fp16 if self.config else False)
        self.check_fp16.setToolTip(
            "Use 16-bit floating point instead of 32-bit.\n"
            "~2x faster on Tensor Core GPUs (CC 7.0+)\n"
            "~2x less VRAM usage.\n"
            "Requires NVIDIA GPU with CUDA.")
        perf_layout.addWidget(self.check_fp16)

        self.check_compile = QCheckBox("torch.compile (graph fusion)")
        self.check_compile.setChecked(False)
        self.check_compile.setToolTip(
            "JIT-compile the model for 10-20% speedup.\n"
            "First run takes longer (warmup compilation),\n"
            "then cached for subsequent frames.\n"
            "Requires CUDA GPU + PyTorch 2.0+.")
        perf_layout.addWidget(self.check_compile)

        self.check_tta = QCheckBox("TTA (test-time augmentation)")
        self.check_tta.setChecked(self.config.default_tta if self.config else False)
        self.check_tta.setToolTip(
            "Test-time augmentation: processes each frame\n"
            "twice (normal + flipped) and averages result.\n"
            "Slightly better quality, ~2x slower.")
        perf_layout.addWidget(self.check_tta)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        cpu_group = QGroupBox("CPU Mode")
        cpu_layout = QVBoxLayout()
        cpu_layout.setContentsMargins(4, 2, 4, 2)
        cpu_layout.setSpacing(2)

        threads_layout = QHBoxLayout()
        lbl = QLabel("Threads:")
        lbl.setFixedWidth(50)
        threads_layout.addWidget(lbl)
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 64)
        self.spin_threads.setValue(self.config.num_threads if self.config else 4)
        self.spin_threads.setMinimumWidth(80)
        self.spin_threads.setToolTip(
            "Number of CPU threads for PyTorch inference.\n"
            "More threads = faster on CPU (up to core count).\n"
            "Set to your physical core count for best performance.")
        threads_layout.addWidget(self.spin_threads)
        threads_layout.addStretch()
        cpu_layout.addLayout(threads_layout)

        self.check_force_cpu = QCheckBox("Force CPU (disable GPU)")
        self.check_force_cpu.setChecked(self.config.force_cpu if self.config else False)
        self.check_force_cpu.setToolTip(
            "Run inference on CPU even if a GPU is available.\n"
            "Useful for debugging or when GPU is needed\n"
            "for other tasks. Much slower than GPU.")
        cpu_layout.addWidget(self.check_force_cpu)

        cpu_group.setLayout(cpu_layout)
        layout.addWidget(cpu_group)

        self.spin_exp.valueChanged.connect(self._emit_settings)
        self.spin_scale.valueChanged.connect(self._emit_settings)
        self.spin_fps.valueChanged.connect(self._emit_settings)
        self.combo_format.currentTextChanged.connect(self._emit_settings)
        self.check_fp16.toggled.connect(self._emit_settings)
        self.check_compile.toggled.connect(self._emit_settings)
        self.check_tta.toggled.connect(self._emit_settings)
        self.check_auto_fps.toggled.connect(self._emit_settings)
        self.spin_threads.valueChanged.connect(self._emit_settings)
        self.check_force_cpu.toggled.connect(self._emit_settings)
        self.combo_codec.currentTextChanged.connect(self._on_codec_changed)
        self.combo_codec.currentTextChanged.connect(self._emit_settings)
        self.slider_crf.valueChanged.connect(self._on_crf_changed)
        self.combo_preset.currentTextChanged.connect(self._emit_settings)
        self.combo_pix_fmt.currentTextChanged.connect(self._emit_settings)
        self.combo_bit_depth.currentTextChanged.connect(self._emit_settings)
        self.check_lossless.toggled.connect(self._emit_settings)

    def _on_auto_fps_toggled(self, checked):
        self.spin_fps.setEnabled(not checked)
        if checked and self._input_fps:
            self._update_auto_fps()
        self._emit_settings()

    def _on_exp_changed(self, val):
        self.spin_exp.setSuffix(f"x ({2 ** val}x)")
        if self.check_auto_fps.isChecked() and self._input_fps:
            self._update_auto_fps()
        self._emit_settings()

    def _update_auto_fps(self):
        interp_factor = 2 ** self.spin_exp.value()
        auto_fps = self._input_fps * interp_factor
        self.spin_fps.blockSignals(True)
        self.spin_fps.setValue(auto_fps)
        self.spin_fps.blockSignals(False)

    def _on_crf_changed(self, val):
        self.label_crf.setText(str(val))
        self._emit_settings()

    def _on_lossless_toggled(self, checked):
        self._update_encoding_enabled()

    def _on_codec_changed(self, codec):
        if codec == "ffv1":
            self.check_lossless.setChecked(True)

    def _update_encoding_enabled(self):
        disabled = self.check_lossless.isChecked() or self.combo_codec.currentText() == "ffv1"
        self.slider_crf.setEnabled(not disabled)
        self.combo_preset.setEnabled(not disabled)
        self.combo_pix_fmt.setEnabled(not disabled)
        self.combo_bit_depth.setEnabled(not disabled)

    def _emit_settings(self):
        self.settings_changed.emit(self.get_settings())

    def get_settings(self):
        return {
            "exp": self.spin_exp.value(),
            "scale": self.spin_scale.value(),
            "fps": None if self.check_auto_fps.isChecked() else self.spin_fps.value(),
            "format": self.combo_format.currentText(),
            "fp16": self.check_fp16.isChecked(),
            "compile": self.check_compile.isChecked(),
            "tta": self.check_tta.isChecked(),
            "num_threads": self.spin_threads.value(),
            "force_cpu": self.check_force_cpu.isChecked(),
            "codec": self.combo_codec.currentText(),
            "crf": self.slider_crf.value(),
            "preset": self.combo_preset.currentText(),
            "pix_fmt": self.combo_pix_fmt.currentText(),
            "bit_depth": int(self.combo_bit_depth.currentText()),
            "lossless": self.check_lossless.isChecked(),
        }

    def set_video_info(self, info):
        if info:
            self._input_fps = info["fps"]
            self.interp_fps_label.setText(
                f"Input: {info['fps']:.1f} fps")
            if self.check_auto_fps.isChecked():
                self._update_auto_fps()
