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
