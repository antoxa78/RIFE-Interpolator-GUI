import os
import time
import traceback
import queue
import threading
import numpy as np
import cv2
from PySide6.QtCore import QThread, Signal

class InferenceWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(str)
    error = Signal(str)
    status_update = Signal(str)
    avg_fps_update = Signal(str)

    def __init__(self, engine, input_path, output_path, mode="video",
                 exp=2, scale=1.0, fps=None, TTA=False, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.input_path = input_path
        self.output_path = output_path
        self.mode = mode
        self.exp = exp
        self.scale = scale
        self.target_fps = fps
        self.TTA = TTA
        self._cancelled = False
        self._start_time = 0
        self._last_report_time = 0
        self._frames_since_report = 0

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            self._start_time = time.time()
            self._last_report_time = self._start_time
            self._frames_since_report = 0
            if self.mode == "video":
                self._process_video()
            elif self.mode == "images":
                self._process_images()
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")

    def _update_progress(self, processed, total_pairs):
        now = time.time()
        self._frames_since_report += 1
        if now - self._last_report_time >= 2.0:
            current_fps = self._frames_since_report / (now - self._last_report_time)
            elapsed = now - self._start_time
            avg_fps = processed / max(elapsed, 0.01)
            eta = (total_pairs - processed) / max(avg_fps, 0.01)
            device_type = self.engine.device.type.upper()
            self.status_update.emit(
                f"Frame pair {processed}/{total_pairs} | "
                f"{current_fps:.1f} fps | {device_type} | "
                f"ETA {self._fmt_time(eta)}"
            )
            self.avg_fps_update.emit(f"{avg_fps:.1f} fps avg | {self._fmt_time(elapsed)} elapsed |")
            self._last_report_time = now
            self._frames_since_report = 0
        self.progress.emit(processed, total_pairs)

    @staticmethod
    def _fmt_time(seconds):
        s = max(0, int(seconds))
        h, m = divmod(s, 3600)
        m, s = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _process_video(self):
        cap = cv2.VideoCapture(self.input_path)
        if not cap.isOpened():
            self.error.emit("Cannot open video file")
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        orig_fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out_fps = self.target_fps if self.target_fps else orig_fps * (2 ** self.exp)
        speed_note = ""
        if self.target_fps:
            auto_fps = orig_fps * (2 ** self.exp)
            speed_note = f" | {auto_fps / max(self.target_fps, 0.01):.1f}x slow-mo" if self.target_fps < auto_fps else ""

        png_mode = os.path.isdir(self.output_path)
        out = None
        frame_counter = [0]

        if png_mode:
            os.makedirs(self.output_path, exist_ok=True)
        else:
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            out = cv2.VideoWriter(self.output_path, fourcc, out_fps, (width, height))
            if not out.isOpened():
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(self.output_path, fourcc, out_fps, (width, height))

        write_queue = queue.Queue(maxsize=200)
        write_done = threading.Event()

        def _writer_thread():
            try:
                while True:
                    item = write_queue.get()
                    if item is None:
                        break
                    if png_mode:
                        path = os.path.join(self.output_path, f"{frame_counter[0]:08d}.png")
                        cv2.imwrite(path, item)
                        frame_counter[0] += 1
                    else:
                        out.write(item)
            except Exception:
                pass
            finally:
                write_done.set()

        writer = threading.Thread(target=_writer_thread, daemon=True)
        writer.start()

        # Diagnostic: check actual model device
        import torch
        first_param = next(self.engine.flownet.parameters())
        actual_device = str(first_param.device)
        device_type = "CUDA" if "cuda" in actual_device else "CPU"
        self.status_update.emit(
            f"Video: {width}x{height} | Scale: {self.scale:.2f} | "
            f"Device: {device_type} ({actual_device}) | "
            f"Output: {out_fps:.1f} fps{speed_note} | Starting..."
        )

        ret, prev = cap.read()
        if not ret:
            self.error.emit("Failed to read first frames")
            cap.release()
            out.release()
            return

        write_queue.put(prev)

        total_pairs = total_frames - 1
        processed = 0

        n = 2 ** self.exp - 1
        if n > 1:
            timesteps = [(i + 1) / (n + 1) for i in range(n)]

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if self._cancelled:
                break

            if n == 1:
                inter = self.engine.inference_image_pair(prev, frame, self.scale, self.TTA)
                write_queue.put(inter)
            else:
                inters = self.engine.inference_image_pair_batch(prev, frame, timesteps, self.scale, self.TTA)
                for inter in inters:
                    write_queue.put(inter)

            write_queue.put(frame)
            prev = frame
            processed += 1
            self._update_progress(processed, total_pairs)

        cap.release()

        write_queue.put(None)
        writer.join(timeout=30)

        if not write_done.is_set():
            self.status_update.emit("Waiting for writer to finish...")
            writer.join(timeout=60)

        if out is not None:
            out.release()

        elapsed = time.time() - self._start_time
        if self._cancelled:
            self.finished.emit("cancelled")
        else:
            self.finished.emit(self.output_path)
            self.status_update.emit(
                f"Done in {self._fmt_time(elapsed)} | "
                f"{processed / max(elapsed, 0.01):.1f} fps avg"
            )

    def _process_images(self):
        img0 = cv2.imread(self.input_path[0])
        img1 = cv2.imread(self.input_path[1])
        if img0 is None or img1 is None:
            self.error.emit("Cannot read input images")
            return

        img0 = cv2.cvtColor(img0, cv2.COLOR_BGR2RGB)
        img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)

        out_dir = os.path.dirname(self.output_path) or "."
        os.makedirs(out_dir, exist_ok=True)

        n = 2 ** self.exp
        timesteps = [(i + 1) / (n + 1) for i in range(n)]
        total = len(timesteps)

        self.status_update.emit(f"Generating {total} intermediate frames")

        results = []
        for i, t in enumerate(timesteps):
            if self._cancelled:
                break
            inter = self.engine.inference_image_pair_batch(img0, img1, [t], self.scale, self.TTA)[0]
            path = os.path.join(out_dir, f"frame_{i:04d}.png")
            cv2.imwrite(path, cv2.cvtColor(inter, cv2.COLOR_RGB2BGR))
            results.append(path)
            self.progress.emit(i + 1, total)

        if self._cancelled:
            self.finished.emit("cancelled")
        else:
            self.finished.emit(self.output_path)
