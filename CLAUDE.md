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
- `scan2connect/__main__.py` — `QApplication`, applies `ui/theme.py` stylesheet, creates/shows `WifiQRScanner`.
- `resources.py` — `resource_path(rel)`: resolves against `sys._MEIPASS` when frozen (PyInstaller), else the package directory. Used for `assets/app_icon.ico`.
- `ui/main_window.py` — `WifiQRScanner(QMainWindow)` — camera preview via `cv2.VideoCapture(0)` + 30 ms `QTimer`, QR detection with `pyzbar`, orchestrates the connect flow.
- `ui/dialogs.py` — `CustomMessageBox(QMessageBox)` — SSID/password confirmation with Yes / No / Copy Password.
- `ui/theme.py` — `STYLESHEET` string applied to the `QApplication`.
- `qr/parser.py` — `parse_wifi_qr(data)` regex parser (module-level function, not a method).
- `wifi/connector.py` — `WifiConnector(QThread)` — `pywifi` connection off the GUI thread; signals `status_updated(str)`, `connection_completed(bool, str)`.

Known pre-plan hazards (all addressed by specific tasks): pywifi hardcodes WPA2 and **deletes all saved WiFi profiles**; pyzbar needs native DLLs + VC++ 2013 runtime on target PCs; `interfaces()[0]` and `VideoCapture(0)` are hardcoded; the scan timer keeps firing while the confirm dialog is open; the icon is loaded by a CWD-relative path.

## Platform notes

- WiFi features are Windows-only. Whether profile creation needs elevation is **unverified** — E-09 must test on a standard (non-admin) account.
- Win11 gates WLAN *scanning* behind Location permission; connecting via a saved profile does not need it.
- Camera access can be blocked under Settings › Privacy & security › Camera.

## Session Log

Single source of truth for progress. Update on every task completion and at the end of every session.

**Current focus:** E-06 (not started) — Phase 1 (Windows 11 runs) started
**Next up:** E-06

| Task | Status | Commit | Notes |
|---|---|---|---|
| E-01 chore .gitignore + untrack build | done | 06b2b32 | also untracked build/dist (15 files) |
| E-02 build pyproject + deps | done | 16b99fa | pip 21.2.3 in .venv couldn't do editable installs; upgraded pip/setuptools first. PySide6 6.4.1→6.11.2. Fixed pre-existing ruff findings in main.py (import order, trailing whitespace, unused import, one long f-string) since "ruff check . passes" is this task's own done-when bar. |
| E-03 refactor split package | done | 9f41e8d | `main.py` deleted; split 1:1 into `scan2connect/{__main__,qr/parser,wifi/connector,ui/{main_window,dialogs,theme}}.py`. `parse_wifi_qr` became a module-level function instead of a `WifiQRScanner` method (as the task specified). Icon still loaded via CWD-relative `"app_icon.ico"` — untouched, fixed in E-04. pyproject.toml switched from `py-modules=["main"]` to package discovery. |
| E-04 fix resource_path icon | done | 6e4e486 | `app_icon.ico` moved to `scan2connect/assets/`; added `resources.py::resource_path()`; wired into `ui/main_window.py` and `__main__.py`. Added `[tool.setuptools.package-data]` so the asset ships in non-editable installs too. Verified via `os.chdir()` to an unrelated directory before resolving the path (and a full app launch from there) — icon path resolves correctly regardless of CWD. |
| E-05 feat WIFI: parser + tests | done | TBD | `WifiCredentials` dataclass (ssid, password, security, hidden); full parser supports T/S/P/H fields, any order, escapes `\;` `\,` `\:` `\\`, quotes; 36 tests (basic, escapes, quotes, real-world, edge cases); `main_window.py` updated to use new return type. |
| E-06 feat OpenCV QR, drop pyzbar | todo | | |
| E-07 feat wlanapi bindings | todo | | |
| E-08 feat profile XML + tests | todo | | |
| E-09 feat connector on WLAN API, drop pywifi | todo | | verify on non-admin account |
| E-10 feat adapter handling | todo | | |
| E-11 feat state machine + connector tests | todo | | |
| E-12 feat camera DSHOW + errors | todo | | |
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
