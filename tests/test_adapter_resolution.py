import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QInputDialog

from scan2connect.ui.main_window import SETTINGS_ADAPTER_GUID_KEY, WifiQRScanner

ADAPTER_A = {"description": "Realtek RTL8822CE", "guid": "guid-a", "ssid": None}
ADAPTER_B = {"description": "Intel AX210", "guid": "guid-b", "ssid": None}


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setOrganizationName("Scan2Connect")
    app.setApplicationName("Scan2ConnectTests")
    yield app


@pytest.fixture
def window(qapp):
    QSettings().clear()
    win = WifiQRScanner()
    yield win
    QSettings().clear()


class TestSingleAdapter:
    def test_auto_selected_without_prompt(self, window):
        with patch.object(QInputDialog, "getItem") as getitem_mock:
            guid = window.resolve_adapter([ADAPTER_A])

        assert guid == "guid-a"
        getitem_mock.assert_not_called()


class TestMultipleAdapters:
    def test_prompts_and_remembers_choice(self, window):
        with patch.object(QInputDialog, "getItem", return_value=(ADAPTER_B["description"], True)):
            guid = window.resolve_adapter([ADAPTER_A, ADAPTER_B])

        assert guid == "guid-b"
        assert QSettings().value(SETTINGS_ADAPTER_GUID_KEY) == "guid-b"

    def test_remembered_choice_skips_prompt(self, window):
        QSettings().setValue(SETTINGS_ADAPTER_GUID_KEY, "guid-b")

        with patch.object(QInputDialog, "getItem") as getitem_mock:
            guid = window.resolve_adapter([ADAPTER_A, ADAPTER_B])

        assert guid == "guid-b"
        getitem_mock.assert_not_called()

    def test_stale_remembered_guid_reprompts(self, window):
        QSettings().setValue(SETTINGS_ADAPTER_GUID_KEY, "guid-removed")

        with patch.object(QInputDialog, "getItem", return_value=(ADAPTER_A["description"], True)):
            guid = window.resolve_adapter([ADAPTER_A, ADAPTER_B])

        assert guid == "guid-a"

    def test_cancel_returns_none(self, window):
        with patch.object(QInputDialog, "getItem", return_value=("", False)):
            guid = window.resolve_adapter([ADAPTER_A, ADAPTER_B])

        assert guid is None
