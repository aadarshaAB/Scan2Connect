# Scan2Connect

Scan a WiFi QR code with your webcam and connect your Windows 11 PC directly to that network.

## Features

- 📱 **Scan WiFi QR codes** from your webcam in real-time
- 🔒 **Support for WPA2, WPA3, open, and hidden networks**
- 🎯 **Preserves existing WiFi profiles** (doesn't delete saved networks)
- 📋 **Copy password to clipboard** before connecting
- ⚡ **Fast and lightweight** — runs on any Windows 11 PC with a webcam
- 🖥️ **No installation required** — portable version available

## Installation

### Option 1: Installer (Recommended)

Download `Scan2Connect-Setup.exe` from [Releases](https://github.com/aadarshaAB/Scan2Connect/releases) and run it. Creates a Start Menu shortcut and uninstaller.

Requires: Windows 11, standard user account (no admin needed)

### Option 2: Portable ZIP

Download `Scan2Connect-portable.zip`, extract it anywhere, and run `Scan2Connect.exe`. No installation or registry changes.

### Requirements

- **Windows 11** (22H2 or later)
- **Webcam** (or use "Open image…" to scan from a file)
- **WiFi adapter** (must be present; can be disabled, will error gracefully)
- **Python 3.10+** (if running from source)

## Usage

1. **Launch** Scan2Connect
2. **Click "Start Scanning"** to begin camera preview
3. **Hold a WiFi QR code** in front of the camera
4. **Confirm** SSID and password in the dialog (with a Copy button for convenience)
5. **Connect** — app saves the profile and connects automatically

Once connected, the app shows the network SSID and signal strength with options to disconnect or forget the network.

### Scanning from a File

Don't have a webcam? Click **"Open image…"** (or press `Ctrl+O`) and select a screenshot or image containing the WiFi QR code.

### Keyboard Shortcuts

- **Space** — Start/stop scanning
- **Escape** — Cancel any dialog
- **Ctrl+O** — Open image file

## Windows 11 Permissions

### Camera Privacy

Scan2Connect needs access to your webcam. If the camera doesn't open:

1. Go to **Settings** → **Privacy & security** → **Camera**
2. Ensure **Camera access** is turned **On**
3. Scroll down and allow **Scan2Connect** to access the camera

### Location (WiFi Scanning)

Windows requires **Location** permission for WLAN *scanning* (detecting available networks). However, connecting to a saved profile does **not** require it. If you're scanning new networks:

1. Go to **Settings** → **Privacy & security** → **Location**
2. Ensure **Location** is **On** (or allow Scan2Connect specifically)

*Note: Scan2Connect does not store or transmit your location; it's purely for WiFi enumeration.*

## Troubleshooting

### Camera won't open

- Check Windows Camera privacy settings (see above)
- Ensure no other app is using the camera
- Try selecting a different camera from the dropdown (if multiple are available)

### "No WiFi adapter found"

- Ensure WiFi is enabled (check device manager or WiFi quick settings)
- Some adapters need drivers — update via Device Manager

### Connection fails with "Wrong password"

- Verify the QR code contains the correct password
- Try the password manually via Windows Settings to test it
- Hidden networks may need the exact SSID to match

### Icon or app doesn't start

- Reinstall via the installer, or
- Ensure `Scan2Connect.exe` and all bundled files are in the same directory

### Cannot scan hidden networks

Hidden networks require the exact SSID. The QR code must explicitly encode the network name (check the QR format: `WIFI:S:<ssid>;...`).

## Development

### Setup

```bash
git clone https://github.com/aadarshaAB/Scan2Connect.git
cd Scan2Connect
python -m venv .venv
source .venv/Scripts/activate  # or .\.venv\Scripts\Activate.ps1 on PowerShell
pip install -e .[dev]
```

### Run

```bash
python -m scan2connect
```

### Lint & Format

```bash
ruff check .      # lint
ruff format .     # auto-format
```

### Test

```bash
pytest            # (tests added from E-05 onward)
```

### Build

```bash
pyinstaller packaging/scan2connect.spec
```

Creates `dist/Scan2Connect/Scan2Connect.exe` (onedir).

### Project Structure

See `CODEBASE_GUIDE.md` for a deep dive into the code. The `enhancement_plan.md` file documents the roadmap and completed tasks with their commit hashes.

### Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <summary>

<optional body>

Refs: E-NN
Co-Authored-By: Author Name <email>
```

Types: `feat`, `fix`, `perf`, `refactor`, `build`, `ci`, `test`, `docs`, `chore`, `style`.

## License

[Add your license here, e.g., MIT, GPL-3.0, etc.]

## Contributing

Contributions welcome! Please:

1. Fork and create a feature branch
2. Follow the Conventional Commits format
3. Test your changes (`ruff check .` + `pytest`)
4. Submit a pull request

## Roadmap

See `enhancement_plan.md` for the detailed task queue and progress tracker.

### Planned (Phase 2+)

- Per-camera selection
- WiFi QR code generator
- Scan history
- Theme customization (light/dark)
- Update checker

## Author

**Aadarsha Bhattarai** — [GitHub](https://github.com/aadarshaAB)

## Support

Found a bug? Have a feature request? Open an [issue](https://github.com/aadarshaAB/Scan2Connect/issues).
