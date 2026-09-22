"""Rotating file logging for Scan2Connect, written to %LOCALAPPDATA%\\Scan2Connect\\logs."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3


def log_dir():
    """Return %LOCALAPPDATA%\\Scan2Connect\\logs, creating it if needed."""
    local_appdata = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    path = Path(local_appdata) / "Scan2Connect" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def configure_logging():
    """Attach a rotating file handler to the root logger. Safe to call once at startup."""
    handler = RotatingFileHandler(
        log_dir() / "scan2connect.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
