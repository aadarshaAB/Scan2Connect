# Scan2Connect

Scan a WiFi QR code with your webcam and connect your Windows PC directly to that network.

## Features

- Scan WiFi QR codes from your webcam in real time
- Supports WPA2, WPA3, open, and hidden networks
- Connects via the native Windows WLAN API — no admin rights needed, and no other saved networks are touched or deleted
- Detects and handles missing or multiple WiFi adapters
- Skips reconnecting if already on the target network
- Distinguishes a wrong password from a connection timeout

## Requirements

- Windows 10/11 with a WiFi adapter
- A webcam
- Python 3.10+

## Installation

```bash
git clone https://github.com/aadarshaAB/Scan2Connect.git
cd Scan2Connect
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell; use `source .venv/Scripts/activate` on bash
pip install -e .[dev]
```

## Usage

```bash
python -m scan2connect
```

1. Click **Start Scanning** to open the camera preview.
2. Hold a WiFi QR code up to the camera.
3. Confirm the SSID and password in the dialog.
4. Scan2Connect saves a WiFi profile and connects automatically.

## Development

```bash
ruff check .      # lint
ruff format .     # format
pytest            # run tests
```

See `CLAUDE.md` and `enhancement_plan.md` for the project's architecture notes and task roadmap.

## License

[Add your license here, e.g., MIT, GPL-3.0, etc.]

## Author

**Aadarsha Bhattarai** — [GitHub](https://github.com/aadarshaAB)
