import cv2

_detector = cv2.QRCodeDetectorAruco()


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
