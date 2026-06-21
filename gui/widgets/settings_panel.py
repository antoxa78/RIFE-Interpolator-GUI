from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QDoubleSpinBox, QComboBox, QCheckBox, QGroupBox, QPushButton
)
from PySide6.QtCore import Signal

class SettingsPanel(QWidget):
    settings_changed = Signal(dict)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._input_fps = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        interp_group = QGroupBox("Interpolation")
        interp_layout = QVBoxLayout()

        exp_layout = QHBoxLayout()
        exp_layout.addWidget(QLabel("Factor:"))
        self.spin_exp = QSpinBox()
        self.spin_exp.setRange(1, 6)
        self.spin_exp.setValue(self.config.default_exp if self.config else 2)
        self.spin_exp.setSuffix(f"x ({2 ** self.spin_exp.value()}x)")
        self.spin_exp.valueChanged.connect(self._on_exp_changed)
        exp_layout.addWidget(self.spin_exp)
        self.interp_fps_label = QLabel("")
        exp_layout.addWidget(self.interp_fps_label)
        interp_layout.addLayout(exp_layout)

        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Scale:"))
        self.spin_scale = QDoubleSpinBox()
        self.spin_scale.setRange(0.1, 4.0)
        self.spin_scale.setSingleStep(0.1)
        self.spin_scale.setValue(self.config.default_scale if self.config else 1.0)
        scale_layout.addWidget(self.spin_scale)
        scale_layout.addWidget(QLabel("(0.5 for 4K)"))
        interp_layout.addLayout(scale_layout)

        interp_group.setLayout(interp_layout)
        layout.addWidget(interp_group)

        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()

        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        self.check_auto_fps = QCheckBox("Auto")
        self.check_auto_fps.setChecked(True)
        self.check_auto_fps.toggled.connect(self._on_auto_fps_toggled)
        fps_layout.addWidget(self.check_auto_fps)
        self.spin_fps = QDoubleSpinBox()
        self.spin_fps.setRange(1, 240)
        self.spin_fps.setDecimals(2)
        self.spin_fps.setValue(60.0)
        self.spin_fps.setEnabled(False)
        self.spin_fps.setToolTip("Output FPS (disabled when Auto)")
        fps_layout.addWidget(self.spin_fps)
        output_layout.addLayout(fps_layout)

        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("Format:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["mp4", "avi", "mov", "png (sequence)"])
        fmt_layout.addWidget(self.combo_format)
        output_layout.addLayout(fmt_layout)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        perf_group = QGroupBox("Performance")
        perf_layout = QVBoxLayout()

        self.check_fp16 = QCheckBox("FP16 (half precision)")
        self.check_fp16.setChecked(self.config.default_fp16 if self.config else False)
        self.check_fp16.setToolTip("Requires NVIDIA GPU with CUDA")
        perf_layout.addWidget(self.check_fp16)

        self.check_compile = QCheckBox("torch.compile (graph fusion)")
        self.check_compile.setChecked(False)
        self.check_compile.setToolTip("PyTorch 2.0+ JIT compilation for 10-15% speedup. First run is slower (compilation), then faster.")
        perf_layout.addWidget(self.check_compile)

        self.check_tta = QCheckBox("TTA (test-time augmentation)")
        self.check_tta.setChecked(self.config.default_tta if self.config else False)
        self.check_tta.setToolTip("Enable for higher quality (doubles processing time)")
        perf_layout.addWidget(self.check_tta)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        layout.addStretch()

        self.spin_exp.valueChanged.connect(self._emit_settings)
        self.spin_scale.valueChanged.connect(self._emit_settings)
        self.spin_fps.valueChanged.connect(self._emit_settings)
        self.combo_format.currentTextChanged.connect(self._emit_settings)
        self.check_fp16.toggled.connect(self._emit_settings)
        self.check_compile.toggled.connect(self._emit_settings)
        self.check_tta.toggled.connect(self._emit_settings)
        self.check_auto_fps.toggled.connect(self._emit_settings)

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
        }

    def set_video_info(self, info):
        if info:
            self._input_fps = info["fps"]
            self.interp_fps_label.setText(
                f"Input: {info['fps']:.1f} fps")
            if self.check_auto_fps.isChecked():
                self._update_auto_fps()
