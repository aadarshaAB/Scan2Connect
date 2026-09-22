# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Scan2Connect** is a Windows GUI app (PySide6) that scans a WiFi QR code from the webcam and connects the PC to that network. It is being upgraded from a single-file prototype into a packaged, installable Win11 app followi ng `enhancement_plan.md`.

Reference docs:
- `enhancement_plan.md` — the ordered work queue (tasks `E-01` … `E-28`). **Work one task at a time, in order.**
- `CODEBASE_GUIDE.md` — deep dive into the original code (pre-plan snapshot).
- The **Session Log** at the bottom of this file — what is done, in progress, and next.

## Start-of-session routine

1. Read the Session Log below to find the current task and any notes left last time.
2. `git log --oneline -5` and `git status` to confirm the log matches reality.
3. Open the task's entry in `enhancement_plan.md` and work only on that task.

## Workflow: one task = one commit

1. Pick the next `todo` task from the Session Log (respect the order in `enhancement_plan.md`).
2. Mark it `in-progress` in the Session Log.
3. Implement only what the task describes. If something unrelated needs fixing, note it in the log's "Notes" column or add a backlog item — don't fold it into this commit.
4. Verify: `ruff check .`, `pytest` (once tests exist), and run the app for anything UI-facing.
5. Update the Session Log row to `done` with the short commit hash, and update any section of this file the task made stale (commands, architecture, dependencies).
6. Commit the code **and** this file together, using the commit message from the task entry.
7. Don't start the next task in the same commit.
8. I have created a own cutom / commit command so dont commit just remind me to commit from now one.
9. Commit message should be short precise and direct.

## Commit message convention (Conventional Commits)

```
<type>(<scope>): <summary>

<optional body — what and why, not how>

Refs: E-05
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

**Types**
| Type | Use for |
|---|---|
| `feat` | new user-visible capability or enhancement |
| `fix` | bug fix |
| `perf` | performance improvement with no behaviour change |
| `refactor` | code restructuring with no behaviour change |
| `build` | packaging, dependencies, PyInstaller/Inno, `pyproject.toml` |
| `ci` | GitHub Actions |
| `test` | adding or fixing tests only |
| `docs` | README, CLAUDE.md, plan docs only |
| `chore` | repo housekeeping (`.gitignore`, tooling config) |
| `style` | formatting only |

**Scopes** (optional, lowercase): `qr`, `wifi`, `camera`, `ui`, `deps`, `packaging`. Omit when the change is repo-wide.

**Rules**
- Summary: imperative mood, lowercase, no trailing period, ≤ 72 chars (`add`, not `added`/`adds`).
- Breaking change: add `!` after the scope (`feat(wifi)!: ...`) and a `BREAKING CHANGE:` footer.
- Always include `Refs: E-NN` for plan tasks (or `B-NN` for backlog). Use `Fixes #123` for GitHub issues.
- One task per commit; never mix a `feat` with an unrelated `fix`.
- Session-Log-only updates use `docs: update session log`.
- Don't auto run script to test. Tell me manually perform test after each phase / feature is completed.

Examples:
```
chore: add .gitignore and stop tracking build artifacts
feat(qr): parse full WIFI: payload with security type, hidden flag and escapes
fix(ui): pause scanning while dialogs are open and debounce repeat QR codes
```

## Commands

```bash
python -m scan2connect    # run
pip install -e .[dev]     # install runtime + dev deps (ruff, pytest, pyinstaller)
ruff check .              # lint
ruff format .             # format
pytest                    # tests (from E-05 onward)
pyinstaller wifi_qr_scanner.spec   # build exe (until E-16; then packaging/scan2connect.spec)
```
Keep this block current — update it in the same commit as the task that changes a command.

## Current architecture (update as tasks land)

Split into the `scan2connect` package (E-03), 1:1 moves from the original `main.py`, no behaviour change:
- `scan2connect/__main__.py` — `QApplication` with `setOrganizationName`/`setApplicationName("Scan2Connect")` (added E-10, required for `QSettings()` to persist reliably), applies `ui/theme.py` stylesheet, creates/shows `WifiQRScanner`.
- `resources.py` — `resource_path(rel)`: resolves against `sys._MEIPASS` when frozen (PyInstaller), else the package directory. Used for `assets/app_icon.ico`.
- `ui/main_window.py` — `WifiQRScanner(QMainWindow)` — camera preview via `camera/worker.py::open_camera(0)` + 30 ms `QTimer`, QR detection via `camera/worker.py::detect_qr_codes()`, orchestrates the connect flow. `start_camera()` (E-12) calls `open_camera()` and shows its `error_message` in a `QMessageBox` on failure instead of opening `cv2.VideoCapture` directly. `connect_to_wifi()` enumerates adapters via `wlanapi.list_interfaces()` first: 0 → error dialog ("No WiFi adapter found or WiFi is off"), 1 → auto-selected, >1 → `resolve_adapter()` shows a `QInputDialog.getItem` picker and remembers the chosen GUID in `QSettings` (key `wifi/adapter_guid`), reused on future connects while still present.
- `ui/dialogs.py` — `CustomMessageBox(QMessageBox)` — SSID/password confirmation with Yes / No / Copy Password.
- `ui/theme.py` — `STYLESHEET` string applied to the `QApplication`.
- `qr/parser.py` — `parse_wifi_qr(data)` regex parser (module-level function, not a method).
- `camera/worker.py` — `detect_qr_codes(frame)`: `cv2.QRCodeDetectorAruco().detectAndDecodeMulti(frame)` wrapper, returns `list[(payload, corners)]`. `open_camera(index=0)` (E-12): opens with `cv2.CAP_DSHOW` and returns `(capture, error_message)` — classifies failures into 3 actionable messages instead of one generic "Cannot access camera": privacy-blocked (checked first, before even trying to open, via `is_camera_privacy_blocked()` reading the `CapabilityAccessManager\ConsentStore\webcam` registry key under both `HKCU` and `HKLM` — either set to `Deny` blocks access), no device present (`is_camera_present()` probes the index independently once the main open attempt fails), or in-use-by-another-app (device present but open still failed). Opens in ~0.5s on this machine, including the registry check.
- `wifi/connector.py` — `WifiConnector(QThread)`, on the native WLAN API: builds a profile via `wifi/profile.py`, `WlanSetProfile`s it per-user (overwrites only the same-SSID profile, other saved profiles untouched), `WlanConnect`s, polls `current_connection` up to 15s per attempt, up to `MAX_ATTEMPTS = 3` attempts on plain timeout (E-11). Signals unchanged: `status_updated(str)`, `connection_completed(bool, str)`. Constructor takes `(credentials, interface_guid=None)` — the full `WifiCredentials` object so security type and hidden-network flag reach the profile builder, plus an optional pre-resolved adapter GUID (E-10; falls back to auto-picking the first enumerated adapter when omitted, used by tests and any caller that hasn't resolved one). `ui/main_window.py` always passes the GUID it resolved. State machine (E-11): already-connected-to-target-SSID short-circuits before touching any profile ("Already connected to {ssid}"); a public `cancel()` sets a flag polled once per second-long poll iteration ("Cancelled", not wired to any UI button yet — that's later UI work); wrong-password is detected heuristically by polling `wlanapi.interface_state()` — if the interface reaches `WLAN_INTERFACE_STATE_AUTHENTICATING` and then falls back to `WLAN_INTERFACE_STATE_DISCONNECTED` without ever reaching the target SSID, that's reported as "Wrong password" immediately (no retry, since retrying won't fix a bad password); a plain timeout (never even reaches authenticating) retries up to `MAX_ATTEMPTS` times before reporting "Connection Timeout". Every failure path (wrong password, cancel, final timeout) calls `_cleanup()`: best-effort `wlanapi.disconnect()` + `delete_profile()` of the profile this run added, so no stale/failed profile is left behind. `pywifi`/`comtypes` fully removed.
- `wifi/wlanapi.py` — ctypes bindings for `wlanapi.dll` (WlanOpenHandle/CloseHandle, EnumInterfaces, QueryInterface, Get/Set/DeleteProfile, Connect, Disconnect, RegisterNotification, FreeMemory). `WlanHandle` context manager; `list_interfaces()` / `current_connection(guid)` helpers; `set_profile(..., all_user=False)` for per-user profiles; `interface_state(wlan_handle, interface_guid)` (E-11) re-enumerates and returns the `WLAN_INTERFACE_STATE_*` value for one interface, used by the connector's wrong-password heuristic.
- `wifi/profile.py` — `build_profile_xml(creds: WifiCredentials) -> str`: WLAN_profile v1 XML for WPA2PSK/AES, WPA3SAE/AES, WPA/TKIP, open/none, WEP; `<nonBroadcast>` for hidden networks; XML-escapes SSID/key. WPA3SAE validated as a plain v1-namespace profile — no v3 namespace or `transitionMode` element needed (confirmed against `netsh wlan add profile`, which is stricter than XML well-formedness).

Known pre-plan hazards (all addressed by specific tasks): ~~pywifi hardcodes WPA2 and **deletes all saved WiFi profiles**~~ fixed in E-09; `interfaces()[0]` and `VideoCapture(0)` are hardcoded; the scan timer keeps firing while the confirm dialog is open; the icon is loaded by a CWD-relative path.

## Platform notes

- WiFi features are Windows-only. Profile creation/connect via the native WLAN API does not need elevation: `netsh wlan add profile`/`delete profile` (E-08) worked fine as a standard user, and E-09's connector code follows the same calls. Actually driving `WifiConnector` against a live adapter (`WlanConnect` succeeding end-to-end, not just schema-valid `WlanSetProfile`) is still **user-verified, not Claude-verified** — E-09 was implemented + unit-tested with `wlanapi` mocked per the user's choice, not live-connected during the session.
- `netsh wlan export profile` (reading a saved profile's XML back out) **does** require elevation on this account — hit this while trying to get a reference profile for E-08; worked around it by round-tripping generated XML through `netsh wlan add profile` instead, which validates against the same schema.
- Win11 gates WLAN *scanning* behind Location permission; connecting via a saved profile does not need it.
- Camera access can be blocked under Settings › Privacy & security › Camera.

## Session Log

Single source of truth for progress. Update on every task completion and at the end of every session.

**Current focus:** E-13 (not started) — Phase 1 (Windows 11 runs) in progress
**Next up:** E-13

| Task | Status | Commit | Notes |
|---|---|---|---|
| E-01 chore .gitignore + untrack build | done | 06b2b32 | also untracked build/dist (15 files) |
| E-02 build pyproject + deps | done | 16b99fa | pip 21.2.3 in .venv couldn't do editable installs; upgraded pip/setuptools first. PySide6 6.4.1→6.11.2. Fixed pre-existing ruff findings in main.py (import order, trailing whitespace, unused import, one long f-string) since "ruff check . passes" is this task's own done-when bar. |
| E-03 refactor split package | done | 9f41e8d | `main.py` deleted; split 1:1 into `scan2connect/{__main__,qr/parser,wifi/connector,ui/{main_window,dialogs,theme}}.py`. `parse_wifi_qr` became a module-level function instead of a `WifiQRScanner` method (as the task specified). Icon still loaded via CWD-relative `"app_icon.ico"` — untouched, fixed in E-04. pyproject.toml switched from `py-modules=["main"]` to package discovery. |
| E-04 fix resource_path icon | done | 6e4e486 | `app_icon.ico` moved to `scan2connect/assets/`; added `resources.py::resource_path()`; wired into `ui/main_window.py` and `__main__.py`. Added `[tool.setuptools.package-data]` so the asset ships in non-editable installs too. Verified via `os.chdir()` to an unrelated directory before resolving the path (and a full app launch from there) — icon path resolves correctly regardless of CWD. |
| E-05 feat WIFI: parser + tests | done | 4e2a041 | `WifiCredentials` dataclass (ssid, password, security, hidden); full parser supports T/S/P/H fields, any order, escapes `\;` `\,` `\:` `\\`, quotes; 36 tests (basic, escapes, quotes, real-world, edge cases); `main_window.py` updated to use new return type. |
| E-06 feat OpenCV QR, drop pyzbar | done | 70e90fd | New `camera/worker.py::detect_qr_codes(frame)` wraps `cv2.QRCodeDetectorAruco().detectAndDecodeMulti()`, returns `list[(payload, corners)]`. `main_window.py` updated: `pyzbar` import/`decode()` replaced, rectangle draw replaced with `cv2.polylines` using detector corner points. Removed `pyzbar` from `pyproject.toml` deps and the DLL `binaries=[...]` entries from `wifi_qr_scanner.spec`. Verified with `pyzbar` uninstalled: app modules import cleanly, `ruff check .` and `pytest` (36 tests) pass. Manual webcam scan test still pending (user to run). |
| E-07 feat wlanapi bindings | done | 581b3e1 | New `wifi/wlanapi.py`: ctypes structs/bindings for WlanOpenHandle/CloseHandle, EnumInterfaces, QueryInterface (current-connection opcode), Get/Set/DeleteProfile, Connect, Disconnect, RegisterNotification, FreeMemory. `WlanHandle` context manager; `list_interfaces()`/`current_connection(guid)` helpers. Not wired into the app (that's E-09). Hit and fixed two ctypes dangling-buffer bugs during verification: `enum_interfaces()` and `query_current_connection()` both returned `Structure` field views into buffers freed by the following `WlanFreeMemory` call, corrupting the GUID/SSID once read by the caller — fixed with `from_buffer_copy()`. Verified `list_interfaces()` output GUID/SSID against `netsh wlan show interfaces` — exact match, stable across repeated runs. `ruff check .` and `pytest` (36 tests) pass. |
| E-08 feat profile XML + tests | done | 5f1ccf8 | New `wifi/profile.py::build_profile_xml(creds)` builds WLAN_profile v1 XML for WPA2PSK/AES, WPA3SAE/AES, WPA/TKIP, open/none, WEP, with `<nonBroadcast>` for hidden and XML-escaped SSID/key. 12 tests in `tests/test_profile_xml.py` (structural + 2 golden-string) covering all security types, hidden, escaping, unknown-security fallback to WPA2. Initial WPA3 implementation wrongly added a v3 namespace + `transitionMode` element (guessed from memory, not verified) — `netsh wlan add profile` rejected it with a schema error; corrected to a plain v1-namespace profile with just `authentication=WPA3SAE`, which Windows accepted and registered as `WPA3-Personal`. Validated all 5 variants (WPA2, WPA3, WEP, open, hidden) by round-tripping through `netsh wlan add profile` / `netsh wlan show profiles` / `netsh wlan delete profile` (no elevation needed for add/delete) since `netsh wlan export profile` needs elevation on this account and couldn't be used to get a reference file directly — all test profiles cleaned up afterward, `netsh wlan show profiles` confirmed no leftovers. `ruff check .` and `pytest` (48 tests) pass. |
| E-09 feat connector on WLAN API, drop pywifi | done | 7d48547 | `WifiConnector` rewritten on `wifi/wlanapi.py` + `wifi/profile.py`: builds a per-SSID profile, `WlanSetProfile`s it per-user (`all_user=False`, overwrites only the same-SSID profile), `WlanConnect`s, polls `current_connection` up to 15s. Signals unchanged. Removed `pywifi`/`comtypes` from `pyproject.toml` and the stale `hiddenimports=['pywifi', ...]` entry in `wifi_qr_scanner.spec`. Deviated from the task's stated file list: also updated `ui/main_window.py`'s one call site and widened `WifiConnector.__init__` to take the full `WifiCredentials` object instead of just `(ssid, password)` — the old signature silently dropped `security`/`hidden`, which would have hardcoded WPA2PSK and misconnected to WPA3/hidden networks scanned from a QR code; confirmed with the user before making the change. Also fixed a bug carried over from E-07: `wlanapi.set_profile`'s per-user flag was `1` (`WLAN_PROFILE_GROUP_POLICY`), should be `WLAN_PROFILE_USER` (`2`) — added named constants and corrected it. 7 new tests in `tests/test_connector.py` run `WifiConnector.run()` synchronously against a mocked `wlanapi` module (no `pytest-qt` needed): WPA2/WPA3 success, no-adapter, timeout, `WlanApiError` from `set_profile`/`connect`. Verified with `pywifi`/`comtypes` uninstalled: app imports cleanly. Per user's choice, did **not** drive a live `WlanConnect`/`WlanSetProfile` against the real adapter this session — confirmed `netsh wlan show profiles` unchanged before/after (no live profile calls were made). User to manually verify live WPA2 (and WPA3 if available) connection via `python -m scan2connect`. `ruff check .` and `pytest` (55 tests) pass. |
| E-10 feat adapter handling | done | b7d9eca | `WifiConnector.__init__` gained an optional `interface_guid` param — when given, skips `enum_interfaces()` entirely (used by `main_window.py`); when omitted, falls back to the old auto-pick-first behavior (used by connector tests). `main_window.py::connect_to_wifi()` now calls `wlanapi.list_interfaces()` first: 0 adapters → `QMessageBox.critical` "No WiFi adapter found or WiFi is off" (also the connector's own fallback message, updated to match); 1 → auto-selected; >1 → new `resolve_adapter()` shows `QInputDialog.getItem` (per user's choice over a custom dialog class) and remembers the choice in `QSettings` under `wifi/adapter_guid`, re-using it next time as long as that GUID is still among the enumerated adapters (falls back to re-prompting if the remembered adapter was unplugged/removed). Required setting `QApplication.setOrganizationName`/`setApplicationName("Scan2Connect")` in `__main__.py` for `QSettings()` to persist reliably — outside E-10's stated file list but a direct, minimal dependency of "remember in QSettings" actually working; caught by a real test failure (`resolve_adapter` calling the picker on a run that should've used the remembered GUID), not by inspection. 8 new tests: `tests/test_connector.py` gained an explicit-GUID case; new `tests/test_adapter_resolution.py` (5 tests) drives `WifiQRScanner.resolve_adapter()` directly against a headless `QApplication` (`QT_QPA_PLATFORM=offscreen`-compatible, also passes with a real display) — single-adapter auto-select, multi-adapter prompt-and-remember, remembered-choice skips prompt, stale/removed remembered GUID re-prompts, cancel returns `None`. Could not test the true multi-adapter or WiFi-disabled paths against real hardware (single adapter on this machine) — user should verify by disabling WiFi (0-adapter path) and, if a second adapter/USB dongle is available, that the picker actually appears. `ruff check .` and `pytest` (61 tests) pass, both under `QT_QPA_PLATFORM=offscreen` and with a normal display. |
| E-11 feat state machine + connector tests | done | bcb1d94 | `WifiConnector`: already-connected-to-SSID short-circuits before touching any profile; wrong-password detected via `wlanapi.interface_state()` polling (authenticating→disconnected without ever connecting) rather than a `WlanRegisterNotification` callback — user chose the polling heuristic over the real ACM notification callback (WINFUNCTYPE + native-thread marshaling) as disproportionate to this task's done-when bar; bounded retry (`MAX_ATTEMPTS = 3`) only on plain timeout, not on wrong-password (retrying won't fix a bad password); public `cancel()` polled once per second (not wired to any UI button — that's later UI work, confirmed with user to keep E-11 to `connector.py`/`test_connector.py` only); every failure path best-effort disconnects + deletes the profile this run added (confirmed with user: cleanup applies to timeout too, not just wrong-password/cancel, matching "always clean up on failure" literally — this changes prior behavior where a timed-out profile was left saved for a later retry). New `wlanapi.interface_state()` helper (re-enumerates, reads one interface's `isState`) plus named `WLAN_INTERFACE_STATE_*` constants. 12 new tests in `tests/test_connector.py` (already-connected skip, wrong-password + its cleanup + no-retry, timeout retry-then-succeed + cleanup, cancel-before-start, cancel-during-poll) plus fixes to existing tests' default mocks (`current_connection` now returns not-yet-connected then connected, since it's called both for the already-connected check and per poll). Not hardware-verified — this session could not force a real wrong-password attempt or multi-attempt timeout against live hardware; heuristic is a reasonable approximation per user's explicit choice, may need adjustment if real-world testing shows false positives/negatives. `ruff check .` and `pytest` (69 tests) pass. |
| E-12 feat camera DSHOW + errors | done | 5ddfa2f | New `camera/worker.py::open_camera(index=0)` opens with `cv2.CAP_DSHOW` and returns `(capture, error_message)`, classifying failures into 3 actionable messages instead of `main_window.py`'s old generic "Cannot access camera": privacy-blocked (checked first via a new `is_camera_privacy_blocked()` reading the `CapabilityAccessManager\ConsentStore\webcam` registry key under `HKCU` and `HKLM` — either `Deny` blocks access, confirmed both keys read `Allow` on this machine), no device present (new `is_camera_present()` probes the index independently, used only once the main open attempt has already failed), in-use-by-another-app (device present but open still failed — the only case OpenCV can't further disambiguate, since DSHOW doesn't surface the underlying HRESULT). `main_window.py::start_camera()` rewritten to call `open_camera()` and show its message via `QMessageBox.critical` instead of raising/catching a generic exception around `cv2.VideoCapture(0)` directly. No task-mandated tests (task's done-when is UI-observable: right message per failure, camera opens in < 1s) — user to manually verify by (a) normal open, (b) Settings › Privacy & security › Camera set to off, (c) another app (e.g. Windows Camera) holding the device, (d) no webcam attached if possible. Verified on this machine: privacy check reads `Allow`/`Allow`, camera opens successfully, `open_camera()` end-to-end (including the registry check) took ~0.49s — under the 1s bar; could not force the "blocked" or "in use" paths live this session (only one physical webcam, not currently privacy-blocked). `ruff check .` and `pytest` (69 tests, unchanged) pass. |
| E-13 feat camera enumeration | todo | | |
| E-14 feat scan from image | todo | | |
| E-15 feat logging | todo | | |
| E-16 build onedir spec | todo | | |
| E-17 build Inno installer | todo | | |
| E-18 ci GitHub Actions | todo | | |
| E-19 docs README | todo | | |
| E-20 perf camera worker thread | todo | | |
| E-21 fix pause + debounce | todo | | |
| E-22 feat overlay + viewfinder | todo | | |
| E-23 feat status panel + toasts | todo | | |
| E-24 feat theme | todo | | |
| E-25 feat camera selector + settings | todo | | |
| E-26 feat busy indicator + shortcuts | todo | | |
| E-27 feat confirm dialog + save-only | todo | | |
| E-28 feat connected card | todo | | |

Status values: `todo` · `in-progress` · `done` · `blocked (reason)` · `skipped (reason)`

### Session history
- **2026-09-18** — Codebase analysed; `CLAUDE.md`, `CODEBASE_GUIDE.md`, `enhancement_plan.md` written. Decisions locked: ctypes WLAN API, OpenCV QR detector, onedir + Inno Setup. No code changed yet.
- **2026-09-18** — E-01 done: `.gitignore` added (incl. `.claude/`), `build/`/`dist/` untracked (06b2b32). Docs bootstrap committed (64ca661). Starting E-02.
- **2026-09-18** — E-02 done: `pyproject.toml` added, `requirements.txt` removed, PySide6/OpenCV upgraded, verified `pip install -e .[dev]` + `python main.py` + `ruff check .` in the project's `.venv`. Starting E-03 next session.
- **2026-09-18** — E-03 done: `main.py` split 1:1 into the `scan2connect` package (no behaviour change), verified `python -m scan2connect` runs and `ruff check .` passes. Starting E-04 next session.
- **2026-09-18** — E-04 done: icon resolved via `resource_path()` instead of a CWD-relative string; Phase 0 (Hygiene) complete. Starting E-05 (Phase 1) next session.
- **2026-09-20** — E-05 done: `WifiCredentials` dataclass, full WIFI: parser (T/S/P/H, escapes, quotes, any field order), 36 comprehensive tests. Updated `main_window.py` to use new return type. All tests + linting pass. Starting E-06 next session.
- **2026-09-21** — E-06 done: added `camera/worker.py::detect_qr_codes()` using `cv2.QRCodeDetectorAruco()`, removed `pyzbar` from `main_window.py`, `pyproject.toml`, and `wifi_qr_scanner.spec` (dropped its DLL `binaries=[...]` entries). Verified with `pyzbar` uninstalled from the venv: imports clean, `ruff check .` and `pytest` (36 tests) pass. Per updated CLAUDE.md rule, did not auto-run the app — user to manually verify webcam QR scanning still works before this task is considered fully done. Starting E-07 next session.
- **2026-09-21** — E-07 done: added `wifi/wlanapi.py`, ctypes bindings for `wlanapi.dll` (open/close handle, enum interfaces, query current connection, get/set/delete profile, connect, disconnect, register notification, free memory) plus `WlanHandle` context manager and `list_interfaces()`/`current_connection()` helpers. Not wired into the app yet. Found and fixed two ctypes dangling-buffer bugs while verifying the done-when command (GUID/SSID read after `WlanFreeMemory` freed the backing buffer) — fixed with `from_buffer_copy()`; output now matches `netsh wlan show interfaces` exactly and is stable across runs. `ruff check .` and `pytest` pass. User now uses their own `/commit-msg` command going forward — Claude implements/verifies and updates this log, but doesn't run `git commit` unless invoked through that command.
- **2026-09-21** — E-08 done: added `wifi/profile.py::build_profile_xml()` (WLAN_profile v1 XML for WPA2PSK/AES, WPA3SAE/AES, WPA/TKIP, open/none, WEP, hidden) and 12 tests in `tests/test_profile_xml.py`. First WPA3 attempt guessed at a v3-namespace schema with a `transitionMode` element and was wrong — `netsh wlan add profile` rejected it with a real schema error; fixed by using a plain v1-namespace profile with `authentication=WPA3SAE`, which Windows accepted and reported as `WPA3-Personal`. Validated all 5 security/hidden variants by round-tripping through `netsh wlan add profile`/`show profiles`/`delete profile` (no elevation needed) since `netsh wlan export profile` needs elevation on this account. All test profiles cleaned up; `netsh wlan show profiles` confirmed no leftovers. `ruff check .` and `pytest` (48 tests) pass. Starting E-09 next session.
- **2026-09-21** — E-09 done: `WifiConnector` rewritten on `wifi/wlanapi.py` + `wifi/profile.py` (per-SSID `WlanSetProfile` overwrite, per-user, `WlanConnect`, poll `current_connection` up to 15s), `pywifi`/`comtypes` removed from `pyproject.toml` and `wifi_qr_scanner.spec`. Asked the user before widening `WifiConnector`'s constructor to take the full `WifiCredentials` object (task's file list only named `wifi/connector.py`/`pyproject.toml`, but keeping `(ssid, password)` would have hardcoded WPA2 and broken WPA3/hidden QR codes) — user said do whatever's correct, so also updated `ui/main_window.py`'s one call site. Also fixed a real bug from E-07: `wlanapi.set_profile`'s per-user flag was using `WLAN_PROFILE_GROUP_POLICY` (1) instead of `WLAN_PROFILE_USER` (2). 7 new mocked-`wlanapi` tests in `tests/test_connector.py` (no `pytest-qt` needed — `run()` called synchronously). Per the user's explicit choice this session, did not drive a live `WlanConnect` against the real adapter — implementation is unit-tested/schema-verified only; confirmed `netsh wlan show profiles` unchanged before/after (10 profiles, none touched). `ruff check .` and `pytest` (55 tests) pass. **User must manually verify a live connection** (`python -m scan2connect`, scan a real WPA2 QR code, ideally a WPA3 one too if available) before E-09 is fully trusted. Starting E-10 next session.
- **2026-09-21** — E-10 done: `WifiConnector` takes an optional pre-resolved `interface_guid`; `main_window.py::connect_to_wifi()` enumerates adapters first (0 → error dialog, 1 → auto-select, >1 → `QInputDialog.getItem` picker remembered in `QSettings`). Had to set `QApplication.setOrganizationName`/`setApplicationName` in `__main__.py` for `QSettings` to actually persist — a real test failure caught this, not just inspection. 8 new tests (1 in `test_connector.py`, 5 in new `test_adapter_resolution.py` using a headless `QApplication`). Only one physical adapter on this machine, so the true multi-adapter picker and WiFi-disabled paths are unit-tested/mocked only, not hardware-verified — user should check both if possible. `ruff check .` and `pytest` (61 tests) pass under both `QT_QPA_PLATFORM=offscreen` and a normal display. Starting E-11 next session.
- **2026-09-21** — E-11 done: `WifiConnector` gained a connection state machine. Asked the user upfront how to detect wrong-password since the task's literal wording ("via `WlanRegisterNotification` reason codes") would need a much larger addition (WINFUNCTYPE native callback, cross-thread marshaling into Qt signals) than the done-when bar warrants — user chose a polling heuristic instead: new `wlanapi.interface_state()` re-enumerates and reads one interface's `isState`; if it reaches `WLAN_INTERFACE_STATE_AUTHENTICATING` and then falls back to `DISCONNECTED` without reaching the target SSID, that's "Wrong password", reported immediately with no retry. Plain timeout (never even authenticates) retries up to `MAX_ATTEMPTS = 3` — user chose to retry only on timeout, not on wrong-password. Already-connected-to-target-SSID now short-circuits before touching any profile. Added a public `cancel()` polled once per second; per user's choice, left it unwired from the UI (E-11's file list is `connector.py`/`test_connector.py` only — the progress dialog's cancel button is later UI work). Every failure path (wrong password, cancel, final timeout) now best-effort disconnects and deletes the profile this run added — confirmed with the user that this should include plain timeout too (not just wrong-password/cancel), even though it means a timed-out profile is no longer left saved for a later retry, since the task says "always clean up on failure". 12 new tests plus fixes to existing tests' default `current_connection` mock (now models not-yet-connected → connected across the already-connected check and the poll loop, instead of always-connected). None of this is hardware-verified this session (couldn't force a real wrong-password or multi-retry timeout against live hardware) — the heuristic is a reasonable approximation per the user's explicit choice and may need adjustment based on real-world behavior. `ruff check .` and `pytest` (69 tests) pass. Starting E-12 next session.
- **2026-09-22** — E-12 done: `camera/worker.py` gained `open_camera(index=0)`, opening with `cv2.CAP_DSHOW` and returning `(capture, error_message)` instead of `main_window.py` catching a generic exception around a bare `cv2.VideoCapture(0)`. Asked the user how to classify failures into 3 distinct messages given OpenCV/DSHOW doesn't surface the underlying HRESULT — went with the user's choice of a registry check for Windows' camera privacy consent (`CapabilityAccessManager\ConsentStore\webcam` under `HKCU` and `HKLM`, either `Deny` blocks access) checked first, then a device-presence probe (`is_camera_present()`, a minimal private helper kept in `worker.py` rather than building out the full E-13 `camera/devices.py` named-enumeration API early) to tell "no device" from "device present but busy/in use by another app" once the main open attempt fails. `main_window.py::start_camera()` rewritten to call `open_camera()` and show its message via `QMessageBox.critical`. No tests added — this task's done-when is UI-observable (right message per failure, camera opens in < 1s), not unit-testable against the real registry/hardware; user to manually verify all 3 failure paths (privacy off, another app holding the camera, no camera attached if possible). Verified on this machine: privacy reads `Allow`/`Allow`, camera opens normally, full `open_camera()` round-trip (including the registry read) took ~0.49s. Could not force the privacy-blocked or in-use paths live this session (single webcam, not currently blocked). `ruff check .` and `pytest` (69 tests, unchanged) pass. Starting E-13 next session.
