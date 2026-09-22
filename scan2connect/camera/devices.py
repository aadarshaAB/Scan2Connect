"""Camera enumeration: pair CAP_DSHOW indices with human-readable device names.

Not surfaced in the UI yet — that's E-25 (camera selector + settings).
"""

import json
import subprocess

import cv2

MAX_PROBE_INDEX = 9
MAX_CONSECUTIVE_MISSES = 2
LOG_LEVEL_SILENT = 0

_WMI_QUERY = (
    "Get-CimInstance Win32_PnPEntity | "
    "Where-Object { $_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image' } | "
    "Select-Object -ExpandProperty Name | ConvertTo-Json -Compress"
)


def _device_names():
    """Return camera device names from WMI, in enumeration order. Best-effort."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _WMI_QUERY],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return []

    output = result.stdout.strip()
    if not output:
        return []

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, str):
        return [parsed]
    if isinstance(parsed, list):
        return [name for name in parsed if isinstance(name, str)]
    return []


def list_cameras():
    """Probe camera indices with CAP_DSHOW. Returns a list of (index, name) tuples.

    Stops after MAX_CONSECUTIVE_MISSES indices in a row fail to open — Windows
    DSHOW indices are contiguous starting at 0 in virtually all real setups, so
    this keeps the common 1-2 camera case fast instead of always probing up to
    MAX_PROBE_INDEX.

    Names come from a best-effort WMI lookup matched to probe order; if WMI
    yields fewer names than working indices (or fails entirely), remaining
    cameras fall back to a generic "Camera N" name.
    """
    indices = []
    consecutive_misses = 0
    previous_log_level = cv2.getLogLevel()
    cv2.setLogLevel(LOG_LEVEL_SILENT)
    try:
        for index in range(MAX_PROBE_INDEX + 1):
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            try:
                opened = capture.isOpened()
            finally:
                capture.release()

            if opened:
                indices.append(index)
                consecutive_misses = 0
            else:
                consecutive_misses += 1
                if consecutive_misses >= MAX_CONSECUTIVE_MISSES:
                    break
    finally:
        cv2.setLogLevel(previous_log_level)

    names = _device_names()

    return [
        (index, names[position] if position < len(names) else f"Camera {index}")
        for position, index in enumerate(indices)
    ]
