import hashlib
import cv2
import numpy as np
import imagehash
from PIL import Image
import easyocr

from app.gemini.exceptions import GeminiSafetyError

from .logger import logger


def compute_video_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def extract_raw_frames(path, interval_ms=300):
    frames = []
    cap = cv2.VideoCapture(path)

    if not cap.isOpened():
        logger.error("Cannot open video")
        return []

    last = -interval_ms
    ok, img = cap.read()

    while ok:
        t = cap.get(cv2.CAP_PROP_POS_MSEC)
        if t - last >= interval_ms:
            frames.append(img.copy())
            last = t
        ok, img = cap.read()

    cap.release()
    return frames


def dedupe_frames(frames, threshold=5):
    unique = []
    last_hash = None

    for f in frames:
        pil = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        h = imagehash.phash(pil)

        if last_hash is None or abs(h - last_hash) > threshold:
            unique.append(f)
            last_hash = h

    return unique


def prepare_frames(frames):
    prepared = []
    for f in frames:
        _, buf = cv2.imencode(".jpg", f)
        prepared.append({"mime_type": "image/jpeg", "data": buf.tobytes()})
    return prepared


def ocr_fallback(prepared_frames):
    logger.info(f"Starting OCR fallback processing with EasyOCR and for frames {prepared_frames}.")
    reader = easyocr.Reader(["en"])
    resume, jd = [], []

    for frame in prepared_frames:
        arr = np.frombuffer(frame["data"], np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        text = " ".join(reader.readtext(img, detail=0))

        if "experience" in text.lower() or "education" in text.lower():
            resume.append(text)
        else:
            jd.append(text)

    return {
        "resume_text": "\n".join(resume),
        "jd_text": "\n".join(jd),
    }


def validate_extraction(data):
    if not data:
        raise GeminiSafetyError("Empty or blocked extraction")
    if "resume_text" not in data or "jd_text" not in data: 
        raise GeminiSafetyError("Missing expected fields in extraction") 
    if data.get("blocked", False):
        raise GeminiSafetyError("Gemini Vision safety block detected")
    return data
