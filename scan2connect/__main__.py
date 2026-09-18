import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from scan2connect.ui.main_window import WifiQRScanner
from scan2connect.ui.theme import STYLESHEET


def main():
    app = QApplication(sys.argv)
    app_icon = QIcon("app_icon.ico")
    app.setWindowIcon(app_icon)
    app.setStyleSheet(STYLESHEET)

    window = WifiQRScanner()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
