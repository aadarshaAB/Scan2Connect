import logging
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from scan2connect.logging_setup import configure_logging
from scan2connect.resources import resource_path
from scan2connect.ui.main_window import WifiQRScanner
from scan2connect.ui.theme import STYLESHEET

log = logging.getLogger(__name__)


def main():
    configure_logging()
    log.info("Scan2Connect starting")

    app = QApplication(sys.argv)
    app.setOrganizationName("Scan2Connect")
    app.setApplicationName("Scan2Connect")
    app_icon = QIcon(resource_path("assets/app_icon.ico"))
    app.setWindowIcon(app_icon)
    app.setStyleSheet(STYLESHEET)

    window = WifiQRScanner()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
