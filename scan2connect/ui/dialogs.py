from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox, QPushButton


class CustomMessageBox(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.clipboard = QApplication.clipboard()

    def setup_ui(self, ssid, password):
        self.setIcon(QMessageBox.Question)
        self.setWindowTitle("Connect to WiFi")
        self.setText(
            f"WiFi Details:\nSSID: {ssid}\nPassword: {password}\n\n"
            f'Do you want to connect to "{ssid}"?'
        )

        layout = self.layout()

        self.setStandardButtons(QMessageBox.NoButton)

        button_box = QDialogButtonBox()

        yes_button = QPushButton("Yes")
        no_button = QPushButton("No")
        copy_button = QPushButton("Copy Password")

        button_box.addButton(yes_button, QDialogButtonBox.YesRole)
        button_box.addButton(no_button, QDialogButtonBox.NoRole)
        button_box.addButton(copy_button, QDialogButtonBox.ActionRole)

        yes_button.clicked.connect(lambda: self.done(QMessageBox.Yes))
        no_button.clicked.connect(lambda: self.done(QMessageBox.No))
        copy_button.clicked.connect(lambda: self.copy_password(password))

        # Add button box to layout
        layout.addWidget(button_box, 3, 0, 1, layout.columnCount())

    def copy_password(self, password):
        self.clipboard.setText(password)
        QMessageBox.information(self, "Copied", "Password copied to clipboard!")
