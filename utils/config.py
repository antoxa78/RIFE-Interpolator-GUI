from PySide6.QtCore import QSettings
import os

ORGANIZATION = "RIFEInterpolator"
APPLICATION = "RIFEInterpolatorGUI"

def _default_checkpoints_dir():
    return os.path.join(os.path.expanduser("~"), ".local", "share", "rife-interpolator", "checkpoints")


class AppConfig:
    def __init__(self):
        self._settings = QSettings(ORGANIZATION, APPLICATION)

    def get(self, key, default=None):
        return self._settings.value(key, default)

    def set(self, key, value):
        self._settings.setValue(key, value)

    @property
    def last_input_dir(self):
        return self.get("paths/last_input_dir", os.path.expanduser("~"))

    @last_input_dir.setter
    def last_input_dir(self, value):
        self.set("paths/last_input_dir", value)

    @property
    def last_output_dir(self):
        return self.get("paths/last_output_dir", os.path.expanduser("~"))

    @last_output_dir.setter
    def last_output_dir(self, value):
        self.set("paths/last_output_dir", value)

    @property
    def checkpoint_path(self):
        return self.get("model/checkpoint_path", _default_checkpoints_dir())

    @checkpoint_path.setter
    def checkpoint_path(self, value):
        self.set("model/checkpoint_path", value)

    @property
    def default_exp(self):
        return int(self.get("defaults/exp", 2))

    @default_exp.setter
    def default_exp(self, value):
        self.set("defaults/exp", int(value))

    @property
    def default_scale(self):
        return float(self.get("defaults/scale", 1.0))

    @default_scale.setter
    def default_scale(self, value):
        self.set("defaults/scale", float(value))

    @property
    def default_fp16(self):
        return self.get("defaults/fp16", "false") == "true"

    @default_fp16.setter
    def default_fp16(self, value):
        self.set("defaults/fp16", "true" if value else "false")

    @property
    def default_tta(self):
        return self.get("defaults/tta", "false") == "true"

    @default_tta.setter
    def default_tta(self, value):
        self.set("defaults/tta", "true" if value else "false")

    @property
    def num_threads(self):
        return int(self.get("cpu/num_threads", 4))

    @num_threads.setter
    def num_threads(self, value):
        self.set("cpu/num_threads", int(value))

    @property
    def force_cpu(self):
        return self.get("cpu/force_cpu", "false") == "true"

    @force_cpu.setter
    def force_cpu(self, value):
        self.set("cpu/force_cpu", "true" if value else "false")

    @property
    def default_codec(self):
        return self.get("encoding/codec", "h264")

    @default_codec.setter
    def default_codec(self, value):
        self.set("encoding/codec", value)

    @property
    def default_crf(self):
        return int(self.get("encoding/crf", 23))

    @default_crf.setter
    def default_crf(self, value):
        self.set("encoding/crf", int(value))

    @property
    def default_preset(self):
        return self.get("encoding/preset", "medium")

    @default_preset.setter
    def default_preset(self, value):
        self.set("encoding/preset", value)

    @property
    def default_pix_fmt(self):
        return self.get("encoding/pix_fmt", "yuv420p")

    @default_pix_fmt.setter
    def default_pix_fmt(self, value):
        self.set("encoding/pix_fmt", value)

    @property
    def default_bit_depth(self):
        return int(self.get("encoding/bit_depth", 8))

    @default_bit_depth.setter
    def default_bit_depth(self, value):
        self.set("encoding/bit_depth", int(value))

    @property
    def default_lossless(self):
        return self.get("encoding/lossless", "false") == "true"

    @default_lossless.setter
    def default_lossless(self, value):
        self.set("encoding/lossless", "true" if value else "false")
