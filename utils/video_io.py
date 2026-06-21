import os
import subprocess
import cv2
import tempfile

def extract_audio(input_video, output_dir=None):
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    audio_path = os.path.join(output_dir, "audio.aac")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_video, "-vn", "-acodec", "aac", audio_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return audio_path
    except Exception:
        return None

def merge_audio(input_video, video_only, output_video):
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_only, "-i", input_video,
             "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0?",
             "-shortest", output_video],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False

def get_video_info(path):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return None
    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "duration": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / max(cap.get(cv2.CAP_PROP_FPS), 1),
    }
    cap.release()
    return info
