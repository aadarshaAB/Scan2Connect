# Scan2Connect — Codebase Guide

A learning-oriented deep dive into how this project works, for use as a reference when planning enhancements.

## 1. What the app does

Scan2Connect is a Windows desktop app that:
1. Opens your webcam and shows a live preview.
2. Continuously scans each frame for a QR code.
3. If the QR code encodes WiFi credentials (the standard `WIFI:S:...;P:...;` format used by routers/phones), it parses out the SSID and password.
4. Shows a confirmation dialog with the credentials (and a "copy password" button).
5. If confirmed, connects the machine to that WiFi network using Windows' native WiFi APIs (via `pywifi`).

It's packaged into a standalone `.exe` with PyInstaller so it can run without a Python install.

## 2. Tech stack

| Library | Version (requirements.txt) | Role |
|---|---|---|
| `PySide6` | 6.4.1 | Qt6 GUI bindings — windows, widgets, threads, signals/slots |
| `opencv-python` | 4.10.0.84 | Webcam capture (`cv2.VideoCapture`) and image color conversion |
| `pyzbar` | 0.1.9 | QR/barcode decoding from image frames (wraps the native ZBar library) |
| `pywifi` | 1.1.12 | Cross-platform WiFi profile management (add/remove profiles, connect) — talks to Windows WLAN API under the hood |
| `comtypes` | 1.4.8 | Windows COM bridge; a transitive dependency `pywifi` needs on Windows |
| `ruff` | 0.7.2 | Linting/formatting (dev-only) |

`pyzbar` on Windows needs two native DLLs (`libiconv.dll`, `libzbar-64.dll`) which live inside the `pyzbar` package in the venv — these have to be explicitly bundled when packaging (see §6).

## 3. Project layout

```
main.py                  # entire application — single file, ~281 lines
wifi_qr_scanner.spec     # PyInstaller build recipe → produces Scan2Connect.exe
requirements.txt         # pinned dependencies
app_icon.ico             # window/app icon
README.md                # one-line project description
build/, dist/            # PyInstaller output (currently committed to git — see §8)
```

There is no package structure, no tests, no config files, and no separate modules — everything (UI, threading, WiFi logic, QR parsing) lives in `main.py`.

## 4. Architecture

Three classes, all in `main.py`:

### `WifiQRScanner(QMainWindow)` — the app
The main window and controller. Owns:
- The camera (`cv2.VideoCapture`) and a `QTimer` that fires every 30 ms to pull a frame and run detection (`update_frame`).
- The UI: a camera preview `QLabel`, a "Start/Stop Scanning" button, a status label, and a watermark.
- QR parsing (`parse_wifi_qr`) and orchestration of the connect flow.

### `WifiConnector(QThread)` — background WiFi worker
Runs the actual connection attempt off the GUI thread so the UI doesn't freeze:
- `disconnect()` any current network, `remove_all_network_profiles()`, build a new `pywifi.Profile()` (WPA2-PSK/CCMP), `add_network_profile()`, then `connect()`.
- Polls `iface.status()` once per second for up to 10 seconds waiting for `IFACE_CONNECTED`.
- Reports progress and outcome via two Qt signals: `status_updated(str)` and `connection_completed(bool, str)`.

### `CustomMessageBox(QMessageBox)` — confirmation dialog
Shows SSID + password, with three actions:
- **Yes** → proceed to connect (`self.done(QMessageBox.Yes)`)
- **No** → cancel (`self.done(QMessageBox.No)`)
- **Copy Password** → writes the password to the system clipboard via `QApplication.clipboard()` and shows a small confirmation popup. This button does **not** close the dialog, so you can copy the password and still say Yes/No afterward.

## 5. End-to-end flow (what happens on a scan)

```
QTimer (30ms tick)
  → update_frame()
      → camera.read() → frame
      → pyzbar.decode(frame) → list of detected barcodes
      → for each barcode whose payload starts with "WIFI:":
          → parse_wifi_qr(data) → (ssid, password) via regex
          → draw a green rectangle around the QR in the frame
          → show_wifi_details_dialog(ssid, password)   [BLOCKING modal dialog]
              → user clicks Yes/No/Copy Password
          → if Yes: connect_to_wifi(ssid, password)
              → shows a QProgressDialog
              → starts WifiConnector(ssid, password) as a QThread
                  → status_updated signal → updates progress dialog text
                  → connection_completed signal → handle_connection_result()
                      → success: QMessageBox.information + status label update
                      → failure: QMessageBox.critical + status label update
      → convert frame BGR→RGB, wrap as QImage/QPixmap, render into camera_label
```

### QR payload parsing
`parse_wifi_qr` uses two regexes against the raw QR string:
```python
ssid_match = re.search(r"WIFI:S:(.*?);", data)
pass_match = re.search(r"P:(.*?);", data)
```
This only extracts SSID and password. The real WIFI QR spec also carries a `T:` field (security type: `WPA`, `WEP`, or `nopass`) and an `H:` field (hidden network flag), neither of which are read — the connector always hardcodes WPA2-PSK/CCMP regardless of what the QR actually specifies (see §7).

## 6. Packaging (PyInstaller)

`wifi_qr_scanner.spec` builds a single windowed (no console) executable named `Scan2Connect.exe`:
- Entry point: `main.py`.
- `binaries=[...]` manually bundles `pyzbar`'s two native DLLs from the venv's `site-packages` — PyInstaller's dependency analysis doesn't discover these automatically, which is what commit `d3ec0c2 "Fixed dll missing file problem"` addressed.
- `hiddenimports=['pywifi', 'PySide6']` — forces inclusion of modules PyInstaller's static analysis might miss (dynamic imports).
- `icon='app_icon.ico'`, `console=False` (windowed app), UPX compression enabled.

Build with:
```
pyinstaller wifi_qr_scanner.spec
```
Output lands in `dist/Scan2Connect.exe`. Note the spec file hardcodes an absolute path (`E:\Python\Scan2Connect\.venv\...`) to the DLLs, so this only builds correctly on a machine with the venv at that exact path.

## 7. Notable behaviors, gaps & rough edges

These are things observed directly in the code that are worth knowing before planning enhancements:

- **Only WPA2-PSK is supported.** `WifiConnector` always sets `AKM_TYPE_WPA2PSK` / `CIPHER_TYPE_CCMP`, regardless of the QR's actual security type. Open networks (`T:nopass`) or WEP networks would fail to connect correctly, and a QR with no password (`P:` empty) would still be routed through the WPA2 flow.
- **`H:` (hidden network) field is ignored** — not parsed, not used.
- **Scanning isn't paused during the confirmation dialog.** `show_wifi_details_dialog` is a blocking modal call *inside* `update_frame`, but the `QTimer` driving `update_frame` keeps running in the background during Qt's nested event loop. This can cause re-entrant calls to `update_frame` while a dialog is already open, potentially stacking multiple dialogs if the QR stays in frame.
- **Single hardcoded camera:** `cv2.VideoCapture(0)` always opens the first camera; no device selection for machines with multiple cameras.
- **Single hardcoded WiFi interface:** `WifiConnector.__init__` does `self.wifi.interfaces()[0]` — assumes at least one WiFi adapter exists; raises `IndexError` on a machine with none, and always picks the first on multi-adapter machines.
- **No `.gitignore` / build artifacts are committed to git.** `build/` and `dist/` (including a ~91MB `.exe` and a ~90MB `.pkg`) are tracked in the repository history, which bloats clone size significantly. Several commits (`b02e42b`, `d3ec0c2`) are almost entirely binary build-output diffs.
- **No automated tests.**
- **No error handling around a busy/in-use camera beyond the initial open check**, and no retry/backoff if `camera.read()` fails mid-session.
- **UI styling is inlined** as a single Qt stylesheet string in `if __name__ == "__main__":` rather than factored out.

## 8. Git history (how it evolved)

1. `d53379a`, `8ead006` — initial README only.
2. `f033f7e` "Finished Connection module" — first WiFi-connection logic.
3. `a33120d` "Work on Core code" — camera/QR scanning added.
4. `e086b17` "Scan2Connect python script" — refactor, app icon, PyInstaller spec added.
5. `d3ec0c2` "Fixed dll missing file problem" — bundled pyzbar DLLs explicitly in the spec; first committed build/dist output.
6. `b02e42b`, `58bc5ca` "feat copy password to clipboard" — added the `CustomMessageBox` copy-password button and renamed the exe from "WiFi QR Scanner" to "Scan2Connect".

## 9. Possible directions for enhancement

Grounded in the gaps above — not decisions, just candidates to discuss:
- Parse and respect the `T:` (security type) and `H:` (hidden) fields; support open/WEP networks, not just WPA2-PSK.
- Pause the capture timer while the confirmation/progress dialogs are open to prevent re-entrant scans.
- Let the user pick which camera and which WiFi interface to use when more than one is available.
- Add a `.gitignore` for `build/`/`dist/`, and scrub them from tracked files going forward (history rewrite would be a separate, larger decision).
- Split `main.py` into modules (e.g. `ui.py`, `wifi.py`, `qr.py`) as functionality grows.
- Add unit tests around `parse_wifi_qr` (pure function, easy to test) and integration-style tests around the connection state machine.
- Show connection progress/errors inline in the main window instead of stacked modal dialogs.
