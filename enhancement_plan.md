# Scan2Connect — Enhancement Plan

Ordered work queue. **One task = one commit.** Work top to bottom; each task is small enough to finish in a single session and is safe to commit on its own (the app keeps working after every task).

- Task definitions live here. **Progress/status lives in `CLAUDE.md` → "Session Log"** (single source of truth — update it when a task is done).
- Commit messages follow Conventional Commits as documented in `CLAUDE.md`. Each task lists its commit message.
- Companion doc: `CODEBASE_GUIDE.md` describes the code as it was before this plan started.

## Goals (priority order)

1. **Runs on every Windows 11 machine** — fresh install, no Python, no VC++ runtimes, standard (non-admin) account, any webcam, any WiFi adapter.
2. **Smooth UI/UX** — no stutter, no frozen window, no stacked pop-ups; native-looking on Win11 light/dark.
3. **Top-notch functionality** — every real-world WiFi QR (WPA2/WPA3/open/hidden), never damages existing profiles, clear error messages.

## Decisions (locked)

| Area | Decision | Why |
|---|---|---|
| WiFi backend | ctypes bindings to `wlanapi.dll` | `pywifi` can't do WPA3, needs `comtypes`, and wipes all profiles. Direct API: WPA3, failure reason codes, no deps. |
| QR decoding | `cv2.QRCodeDetectorAruco` (opencv-python ≥ 4.8) | `pyzbar` needs native DLLs + VC++ 2013 runtime on target PCs. OpenCV is already a dependency. |
| Packaging | PyInstaller **onedir** + Inno Setup installer + portable zip; UPX off | Fast startup, Start Menu/uninstall, fewer AV false positives. |

## Target layout (what the tasks build toward)

```
scan2connect/
  __main__.py          entry: QApplication, theme, main window
  resources.py         resource_path() for source + PyInstaller
  qr/parser.py         WIFI: payload parser
  camera/worker.py     QThread capture + detection
  camera/devices.py    camera enumeration
  wifi/wlanapi.py      ctypes bindings to wlanapi.dll
  wifi/profile.py      WLAN profile XML builder
  wifi/connector.py    connection state machine (QThread)
  ui/main_window.py, ui/dialogs.py, ui/widgets.py, ui/theme.py
tests/
packaging/             scan2connect.spec, installer.iss, version_info.txt
.github/workflows/build.yml
```

---

## Phase 0 — Hygiene

### E-01 · chore · `.gitignore` + untrack build output
- **Why:** `build/` and `dist/` (~180 MB of binaries) are committed; every rebuild creates a huge diff.
- **Files:** `.gitignore`; `git rm --cached -r build dist`
- **Do:** ignore `build/`, `dist/`, `.venv/`, `__pycache__/`, `*.log`, `*.egg-info/`, `.pytest_cache/`, `.ruff_cache/`. Do **not** rewrite history.
- **Done when:** `git status` clean after a PyInstaller build.
- **Commit:** `chore: add .gitignore and stop tracking build artifacts`

### E-02 · build · `pyproject.toml` + dependency upgrade
- **Why:** `PySide6==6.4.1` has no Python 3.12 wheels; `opencv-python` must be ≥ 4.8 for `QRCodeDetectorAruco`.
- **Files:** `pyproject.toml` (new), `requirements.txt` (delete or generate from pyproject)
- **Do:** project metadata + version; runtime deps `PySide6` (current 6.x), `opencv-python>=4.8`; keep `pyzbar`/`pywifi`/`comtypes` **for now** (removed in E-06 / E-09); dev deps `ruff`, `pytest`, `pyinstaller`; ruff config (line-length, select rules).
- **Done when:** fresh venv → `pip install -e .[dev]` → `python main.py` runs; `ruff check .` passes.
- **Commit:** `build: add pyproject.toml and upgrade PySide6/OpenCV`

### E-03 · refactor · Split `main.py` into the `scan2connect` package
- **Why:** one 281-line file can't grow; every later task needs its own module.
- **Files:** `scan2connect/__main__.py`, `ui/main_window.py`, `ui/dialogs.py`, `wifi/connector.py`, `qr/parser.py`; delete `main.py`
- **Do:** move classes 1:1, **no behaviour change**. `CustomMessageBox` → `ui/dialogs.py`; `WifiConnector` → `wifi/connector.py`; `parse_wifi_qr` → `qr/parser.py`; `WifiQRScanner` → `ui/main_window.py`; stylesheet string → `ui/theme.py`. Run with `python -m scan2connect`.
- **Done when:** app behaves exactly as before; `ruff check .` passes.
- **Commit:** `refactor: split main.py into scan2connect package`

### E-04 · fix · `resource_path()` for the icon
- **Why:** `QIcon("app_icon.ico")` resolves against the CWD → icon vanishes when launched from a shortcut or from the exe.
- **Files:** `scan2connect/resources.py`, `ui/main_window.py`, `__main__.py`; move `app_icon.ico` → `scan2connect/assets/`
- **Do:** `resource_path(rel)` → `sys._MEIPASS` when frozen, else package dir. Use it for the icon.
- **Done when:** icon shows when run from any CWD.
- **Commit:** `fix(ui): resolve app icon via resource_path`

---

## Phase 1 — Runs on every Win11 machine

### E-05 · feat · Full `WIFI:` parser + tests
- **Why:** only `S`/`P` are read today; `T` (security) and `H` (hidden) are ignored and escapes break.
- **Files:** `qr/parser.py`, `tests/test_parser.py`
- **Do:** parse `T` (WPA/WPA2/WPA3/SAE/WEP/nopass), `S`, `P`, `H`, any field order, escapes `\;` `\,` `\:` `\\`, quoted values, trailing `;;`. Return `WifiCredentials` dataclass (`ssid`, `password`, `security`, `hidden`). Tests: Android share sheet, iOS, router labels, hidden, passwords containing `;`/`:`, open network.
- **Done when:** `pytest tests/test_parser.py` green; app still connects via existing flow.
- **Commit:** `feat(qr): parse full WIFI: payload with security type, hidden flag and escapes`

### E-06 · feat · QR decoding via OpenCV, drop pyzbar
- **Why:** pyzbar needs `libzbar-64.dll` + `libiconv.dll` + VC++ 2013 runtime on target PCs.
- **Files:** `camera/worker.py` (new, initially just the detect function), `ui/main_window.py`, `pyproject.toml`, `wifi_qr_scanner.spec`
- **Do:** `cv2.QRCodeDetectorAruco().detectAndDecodeMulti(frame)` → list of `(payload, corners)`. Remove `pyzbar` dep and the spec's `binaries=[...]` DLL entries.
- **Done when:** QR detected from webcam with pyzbar uninstalled.
- **Commit:** `feat(camera): decode QR codes with OpenCV and remove pyzbar`

### E-07 · feat · `wlanapi.dll` ctypes bindings
- **Why:** foundation for replacing pywifi.
- **Files:** `wifi/wlanapi.py`
- **Do:** structs + bindings for `WlanOpenHandle`, `WlanCloseHandle`, `WlanEnumInterfaces`, `WlanQueryInterface` (`wlan_intf_opcode_current_connection`), `WlanGetProfile`, `WlanSetProfile`, `WlanDeleteProfile`, `WlanConnect`, `WlanDisconnect`, `WlanRegisterNotification`, `WlanFreeMemory`. Context-manager `WlanHandle`. Small `list_interfaces()` / `current_connection(iface)` helpers. Not wired into the app yet.
- **Done when:** `python -c "from scan2connect.wifi.wlanapi import list_interfaces; print(list_interfaces())"` prints the adapter and current SSID.
- **Commit:** `feat(wifi): add ctypes bindings for wlanapi.dll`

### E-08 · feat · WLAN profile XML builder + tests
- **Files:** `wifi/profile.py`, `tests/test_profile_xml.py`
- **Do:** `build_profile_xml(creds: WifiCredentials) -> str` for WPA2PSK/AES, WPA3SAE/AES, open/none, WEP; `<nonBroadcast>true</nonBroadcast>` when hidden; XML-escape SSID/key. Golden-file tests per security type.
- **Done when:** tests green; XML validates against a profile exported by `netsh wlan export profile`.
- **Commit:** `feat(wifi): build WLAN profile XML for WPA2/WPA3/open/WEP/hidden`

### E-09 · feat · Connector on WLAN API, drop pywifi
- **Why:** pywifi hardcodes WPA2 and **deletes every saved profile** on the machine.
- **Files:** `wifi/connector.py`, `pyproject.toml`
- **Do:** `WifiConnector` uses `wlanapi` + `profile`: overwrite only the same-SSID profile (`WlanSetProfile` overwrite flag, per-user), `WlanConnect`, poll `current_connection` up to N s. Remove `pywifi` and `comtypes`. Keep existing signals so the UI is unchanged.
- **Done when:** connects to WPA2 and WPA3 networks; other saved profiles untouched (`netsh wlan show profiles` before/after); works on a standard (non-admin) account.
- **Commit:** `feat(wifi): connect via native WLAN API and stop deleting other profiles`

### E-10 · feat · Adapter handling (none / multiple)
- **Files:** `wifi/connector.py`, `ui/main_window.py`
- **Do:** enumerate; 0 → error "No WiFi adapter found or WiFi is off"; >1 → picker, remember in `QSettings`.
- **Done when:** no crash with WiFi disabled; picker appears with two adapters.
- **Commit:** `feat(wifi): handle missing and multiple WiFi adapters`

### E-11 · feat · Connection state machine + connector tests
- **Files:** `wifi/connector.py`, `tests/test_connector.py`
- **Do:** already-connected-to-SSID → skip; wrong-password vs timeout via `WlanRegisterNotification` reason codes; bounded retry; cancellable; always clean up on failure. Tests mock the `wlanapi` layer: success, wrong password, timeout, cancel, no adapter.
- **Done when:** wrong password reports "Wrong password", not "Timeout"; tests green.
- **Commit:** `feat(wifi): distinguish wrong password from timeout and add connector tests`

### E-12 · feat · Camera: DirectShow backend + error classification
- **Files:** `camera/worker.py`, `ui/main_window.py`
- **Do:** open with `cv2.CAP_DSHOW`; classify failures: no device / in use by another app / blocked by Privacy settings, each with an actionable message (Settings › Privacy & security › Camera).
- **Done when:** each failure shows the right message; camera opens in < 1 s.
- **Commit:** `feat(camera): use DirectShow and report actionable camera errors`

### E-13 · feat · Camera enumeration
- **Files:** `camera/devices.py`
- **Do:** probe indices with `CAP_DSHOW`, return `(index, name)` list. Not surfaced in UI yet (E-25).
- **Commit:** `feat(camera): enumerate available cameras`

### E-14 · feat · Scan from image file
- **Why:** PCs with no webcam can still use the app.
- **Files:** `ui/dialogs.py`, `ui/main_window.py`, `camera/worker.py`
- **Do:** "Open image…" button + drag-and-drop; run the same detector on the file.
- **Commit:** `feat(ui): scan WiFi QR from an image file`

### E-15 · feat · Logging
- **Files:** `__main__.py`, all modules
- **Do:** rotating file log in `%LOCALAPPDATA%\Scan2Connect\logs`; every WLAN API return code logged; Help › Open log folder.
- **Commit:** `feat: add rotating file logging`

### E-16 · build · onedir PyInstaller spec
- **Files:** `packaging/scan2connect.spec`, `packaging/version_info.txt`; delete `wifi_qr_scanner.spec`
- **Do:** onedir; exclude `QtWebEngine*`, `QtQuick*`, `Qt3D*`, `QtMultimedia`, `QtCharts`, `QtDataVisualization`, translations; `upx=False`; icon + assets via `datas`; version resource.
- **Done when:** `dist/Scan2Connect/Scan2Connect.exe` starts in < 2 s on a clean VM.
- **Commit:** `build: switch to onedir PyInstaller build with Qt excludes`

### E-17 · build · Inno Setup installer
- **Files:** `packaging/installer.iss`
- **Do:** `PrivilegesRequired=lowest`, Start Menu shortcut, optional desktop shortcut, uninstaller, icon, version read from `pyproject.toml`.
- **Done when:** install → run → uninstall works on a standard account.
- **Commit:** `build: add Inno Setup installer`

### E-18 · ci · GitHub Actions build
- **Files:** `.github/workflows/build.yml`
- **Do:** `windows-latest`: ruff → pytest → PyInstaller → Inno → upload installer + portable zip as artifacts; on `v*` tag, attach to a GitHub Release.
- **Commit:** `ci: build installer and portable zip on GitHub Actions`

### E-19 · docs · README
- **Files:** `README.md`
- **Do:** install (installer / portable), usage, Win11 permissions (camera privacy; Location is needed for WLAN *scanning*, not for profile connect), troubleshooting, dev setup.
- **Commit:** `docs: write README with install, permissions and troubleshooting`

---

## Phase 2 — Smooth UI/UX

### E-20 · perf · Camera worker thread + detection throttle
- **Why:** capture + decode run on the GUI thread in a 30 ms timer → stutter.
- **Files:** `camera/worker.py`, `ui/main_window.py`
- **Do:** `CameraWorker(QThread)` emits `frame_ready(QImage)` and `qr_found(payload, corners)`; detect every 2nd–3rd frame or on a downscaled copy; GUI only paints.
- **Commit:** `perf(camera): move capture and detection to a worker thread`

### E-21 · fix · Pause detection during dialogs + debounce
- **Why:** timer keeps firing during a modal `exec()` → stacked dialogs.
- **Files:** `ui/main_window.py`
- **Do:** pause detection while any dialog is open; ignore the same payload for ~10 s after Cancel.
- **Commit:** `fix(ui): pause scanning while dialogs are open and debounce repeat QR codes`

### E-22 · feat · Visible highlight overlay + viewfinder
- **Files:** `ui/widgets.py`
- **Do:** draw QR corners in the paint path (today drawn but never rendered); viewfinder guide when idle.
- **Commit:** `feat(ui): draw QR highlight overlay and viewfinder`

### E-23 · feat · Inline status panel, toasts, progress with cancel
- **Files:** `ui/widgets.py`, `ui/main_window.py`
- **Do:** replace `QMessageBox`/`QProgressDialog` chain with in-window status + non-blocking toasts; progress steps (Saving profile → Connecting → Verifying) + Cancel.
- **Commit:** `feat(ui): replace modal dialogs with inline status panel and toasts`

### E-24 · feat · Theme (light/dark, HiDPI)
- **Files:** `ui/theme.py`
- **Do:** Fusion + QSS; follow Windows colour scheme (`Qt.ColorScheme`); no fixed pixel sizes.
- **Commit:** `feat(ui): add light/dark theme following Windows setting`

### E-25 · feat · Camera selector + persisted settings
- **Files:** `ui/main_window.py`
- **Do:** combo from `camera/devices.py`; `QSettings` for camera, adapter, window geometry.
- **Commit:** `feat(ui): add camera selector and remember window settings`

### E-26 · feat · Busy indicator + keyboard shortcuts
- **Files:** `ui/widgets.py`, `ui/main_window.py`
- **Do:** spinner "Starting camera…"; Space start/stop, Esc cancel, Ctrl+O open image.
- **Commit:** `feat(ui): add camera busy indicator and keyboard shortcuts`

### E-27 · feat · Confirm dialog polish + save-only option
- **Files:** `ui/dialogs.py`, `wifi/connector.py`
- **Do:** show/hide password toggle beside Copy; show security type; buttons Connect / Save only / Cancel; auto-connect toggle.
- **Commit:** `feat(ui): polish confirm dialog and add save-only option`

### E-28 · feat · Connected-network card
- **Files:** `ui/widgets.py`
- **Do:** after success: SSID, signal strength, Disconnect / Forget.
- **Commit:** `feat(ui): show connected network card with disconnect and forget`

---

## Backlog (not scheduled)

- B-01 Generate a QR for the currently connected network.
- B-02 Opt-in scan history.
- B-03 Update check against GitHub Releases.
- B-04 Localisation (Qt `.ts`).
- B-05 Code signing (paid certificate) to clear SmartScreen.

## Release checklist

**Test matrix:** Win11 22H2/23H2/24H2 · fresh VM (no Python, no VC++ redist, standard account) · 0/1/2 webcams · 0/1/2 WiFi adapters · WPA2 / WPA3 / open / hidden / WEP · wrong password, out of range, camera blocked, camera busy · installer and portable zip.

**Steps:** bump version in `pyproject.toml` → update `CHANGELOG.md` → tag `vX.Y.Z` → CI attaches installer + zip to the GitHub Release.
