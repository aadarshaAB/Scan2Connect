import logging
import winreg

import cv2
from PySide6.QtCore import QMutex, QThread, Signal
from PySide6.QtGui import QImage

log = logging.getLogger(__name__)

DETECT_EVERY_N_FRAMES = 3

_detector = cv2.QRCodeDetectorAruco()

CAMERA_PRIVACY_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam"
)


def detect_qr_codes(frame):
    """Detect QR codes in a BGR frame. Returns a list of (payload, corners) for decoded codes."""
    ok, payloads, points, _ = _detector.detectAndDecodeMulti(frame)
    if not ok:
        return []

    return [
        (payload, corners)
        for payload, corners in zip(payloads, points, strict=False)
        if payload
    ]


def detect_qr_codes_in_image(path):
    """Detect QR codes in an image file. Returns a list of (payload, corners),
    or [] if the file can't be read as an image."""
    frame = cv2.imread(path)
    if frame is None:
        return []
    return detect_qr_codes(frame)


def _consent_value(hive, key_path):
    try:
        with winreg.OpenKey(hive, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "Value")
            return value
    except OSError:
        return None


def is_camera_privacy_blocked():
    """Return True if Windows camera privacy settings deny access, per-user or system-wide."""
    per_user = _consent_value(winreg.HKEY_CURRENT_USER, CAMERA_PRIVACY_KEY)
    if per_user == "Deny":
        return True

    system_wide = _consent_value(winreg.HKEY_LOCAL_MACHINE, CAMERA_PRIVACY_KEY)
    return system_wide == "Deny"


def is_camera_present(index=0):
    """Return True if a camera device responds at `index` (regardless of open state)."""
    probe = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    try:
        return probe.isOpened()
    finally:
        probe.release()


def open_camera(index=0):
    """Open a camera with the DirectShow backend.

    Returns (capture, error_message). On success, `capture` is an opened
    cv2.VideoCapture and `error_message` is None. On failure, `capture` is
    None and `error_message` is an actionable, user-facing string.
    """
    if is_camera_privacy_blocked():
        log.warning("Camera open blocked: privacy settings deny webcam access")
        return None, (
            "Camera access is blocked by Windows privacy settings.\n\n"
            "Go to Settings › Privacy & security → Camera and allow "
            "apps to access your camera."
        )

    capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if capture.isOpened():
        log.info("Camera %d opened", index)
        return capture, None

    capture.release()

    if not is_camera_present(index):
        log.warning("Camera open failed: no device at index %d", index)
        return None, "No camera was found. Connect a webcam and try again."

    log.warning("Camera open failed: index %d present but busy/in use", index)
    return None, (
        "Could not access the camera. It may be in use by another app.\n\n"
        "Close any other app using the camera (e.g. Camera, Teams, Zoom) and try again."
    )


class CameraWorker(QThread):
    """Owns capture + QR detection off the GUI thread.

    Emits `frame_ready(QImage)` for every captured frame (GUI only paints)
    and `qr_found(str, object)` (payload, corners) when a frame decodes a
    QR code. Detection runs on a downscaled copy every `DETECT_EVERY_N_FRAMES`
    frames rather than every frame, since decode is the expensive step.
    """

    frame_ready = Signal(QImage)
    qr_found = Signal(str, object)
    camera_error = Signal(str)

    def __init__(self, index=0, parent=None):
        super().__init__(parent)
        self.index = index
        self._mutex = QMutex()
        self._running = False

    def stop(self):
        self._mutex.lock()
        self._running = False
        self._mutex.unlock()
        self.wait()

    def run(self):
        capture, error_message = open_camera(self.index)
        if error_message is not None:
            self.camera_error.emit(error_message)
            return

        self._mutex.lock()
        self._running = True
        self._mutex.unlock()

        frame_count = 0
        try:
            while True:
                self._mutex.lock()
                running = self._running
                self._mutex.unlock()
                if not running:
                    break

                ret, frame = capture.read()
                if not ret:
                    continue

                frame_count += 1
                if frame_count % DETECT_EVERY_N_FRAMES == 0:
                    scale = 0.5
                    small = cv2.resize(frame, None, fx=scale, fy=scale)
                    for payload, corners in detect_qr_codes(small):
                        self.qr_found.emit(payload, corners / scale)

                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
                ).copy()
                self.frame_ready.emit(qt_image)
        finally:
            capture.release()
