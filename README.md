# Scan2Connect

Scan a WiFi QR code with your webcam (or an image file) and connect your Windows PC directly to that network — no typing the password.

## Features

- Scan WiFi QR codes from your webcam in real time, or from an image file / drag-and-drop
- Supports WPA2, WPA3, open, and hidden networks
- Connects via the native Windows WLAN API — no admin rights needed, and no other saved networks are touched or deleted
- Detects and handles missing or multiple WiFi adapters
- Skips reconnecting if already on the target network
- Distinguishes a wrong password from a connection timeout
- Rotating file log for troubleshooting (Help › Open log folder)

## Install

### Option A: Installer (recommended)

1. Download `Scan2Connect-<version>-setup.exe` from the [latest release](https://github.com/aadarshaAB/Scan2Connect/releases/latest).
2. Run it. No admin rights required — it installs for your user account only.
3. Launch Scan2Connect from the Start Menu (or the desktop, if you checked that option during install).

To uninstall: Settings › Apps › Scan2Connect › Uninstall, or via the Start Menu shortcut.

### Option B: Portable zip

1. Download `Scan2Connect-<version>-portable.zip` from the [latest release](https://github.com/aadarshaAB/Scan2Connect/releases/latest).
2. Extract it anywhere.
3. Run `Scan2Connect.exe` inside the extracted folder. Nothing is installed — delete the folder to remove it.

## Usage

1. Click **Start Scanning** to open the camera preview, or use **Open image…** / drag-and-drop to scan a QR code from a file instead.
2. Hold a WiFi QR code up to the camera (or point it at the image).
3. Confirm the SSID and password in the dialog.
4. Scan2Connect saves a WiFi profile and connects automatically.

## Windows permissions

- **Camera**: Settings › Privacy & security › Camera must allow desktop apps to use your camera, or webcam scanning will fail with a clear error message telling you where to fix it.
- **Location**: Windows gates WiFi *scanning* (seeing nearby networks) behind Location permission, but Scan2Connect doesn't scan for networks — it connects directly using a profile built from the QR code. Location permission is **not** needed for Scan2Connect to work.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Camera access is blocked by Windows privacy settings" | Settings › Privacy & security › Camera → allow apps to access your camera. |
| "Could not access the camera. It may be in use by another app." | Close other apps that might be using the webcam (Camera, Teams, Zoom, another browser tab, etc.) and try again. |
| "No camera was found" | Check the webcam is connected. Built-in and USB webcams are both supported via DirectShow. |
| "No WiFi adapter found or WiFi is off" | Turn WiFi on, or check the adapter is enabled in Device Manager. |
| "Wrong password" | The QR code's password didn't match what the router expects — re-scan or check the network's actual password. |
| "Connection Timeout" | The adapter couldn't reach the network in time; Scan2Connect retries automatically before reporting this. Check signal strength and that the network is in range. |
| Still stuck | Use **Help › Open log folder** in the app to find `scan2connect.log`, which records every step of the last few runs (including the raw Windows WLAN API error codes) — useful when filing an issue. |

## Development

```bash
git clone https://github.com/aadarshaAB/Scan2Connect.git
cd Scan2Connect
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell; use `source .venv/Scripts/activate` on bash
pip install -e .[dev]

python -m scan2connect   # run from source
ruff check .             # lint
ruff format .            # format
pytest                   # run tests
```

### Building a release locally

```bash
pyinstaller packaging/scan2connect.spec                        # onedir build → dist/Scan2Connect/
iscc /DAppVersion=<version> packaging/installer.iss             # installer → dist/Scan2Connect-<version>-setup.exe
```

`<version>` should match the `version` field in `pyproject.toml`. GitHub Actions (`.github/workflows/build.yml`) does this automatically on every push to `main` and on version tags, publishing both the installer and a portable zip as build artifacts (and, on a `v*` tag, attaching them to a GitHub Release).

See `CLAUDE.md` and `enhancement_plan.md` for the project's architecture notes and task roadmap.

## Requirements

- Windows 10/11 with a WiFi adapter
- A webcam (optional — image-file/drag-and-drop scanning works without one)

## License

[Add your license here, e.g., MIT, GPL-3.0, etc.]

## Author

**Aadarsha Bhattarai** — [GitHub](https://github.com/aadarshaAB)
