import winreg

import cv2

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
        return None, (
            "Camera access is blocked by Windows privacy settings.\n\n"
            "Go to Settings › Privacy & security → Camera and allow "
            "apps to access your camera."
        )

    capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if capture.isOpened():
        return capture, None

    capture.release()

    if not is_camera_present(index):
        return None, "No camera was found. Connect a webcam and try again."

    return None, (
        "Could not access the camera. It may be in use by another app.\n\n"
        "Close any other app using the camera (e.g. Camera, Teams, Zoom) and try again."
    )
