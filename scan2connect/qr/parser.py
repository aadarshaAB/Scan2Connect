from dataclasses import dataclass


@dataclass
class WifiCredentials:
    ssid: str
    password: str | None = None
    security: str = "WPA2"
    hidden: bool = False


def parse_wifi_qr(data: str) -> WifiCredentials | None:
    r"""
    Parse WIFI: QR code payload per WiFi Alliance spec.
    Handles: S (SSID), P (password), T (security), H (hidden),
    escapes (\; \, \: \\), quoted values, and any field order.
    """
    if not data or not data.startswith("WIFI:"):
        return None

    try:
        payload = data[5:]
        if payload.endswith(";;"):
            payload = payload[:-2]
        elif payload.endswith(";"):
            payload = payload[:-1]

        fields = _split_fields(payload)
        params = {}
        for field in fields:
            if ":" not in field:
                continue
            key, val = field.split(":", 1)
            params[key.strip()] = _unescape(val)

        ssid = params.get("S", "")
        if not ssid:
            return None

        password = params.get("P")
        security = params.get("T", "WPA2").upper()
        hidden = params.get("H", "false").lower() == "true"

        return WifiCredentials(
            ssid=ssid,
            password=password,
            security=security,
            hidden=hidden
        )
    except Exception:
        return None


def _split_fields(payload: str) -> list[str]:
    """Split WIFI: payload into fields, respecting escapes and quotes."""
    fields = []
    current = []
    i = 0
    in_quotes = False

    while i < len(payload):
        char = payload[i]

        if char == '"' and (i == 0 or payload[i - 1] != "\\"):
            in_quotes = not in_quotes
            current.append(char)
        elif char == ";" and not in_quotes and (i == 0 or payload[i - 1] != "\\"):
            fields.append("".join(current))
            current = []
        else:
            current.append(char)

        i += 1

    if current:
        fields.append("".join(current))

    return [f for f in fields if f]


def _unescape(value: str) -> str:
    r"""Unescape special characters: \; \, \: \\"""
    if not value:
        return value
    result = []
    i = 0
    has_leading_quote = value.startswith('"')
    has_trailing_quote = value.endswith('"') and len(value) > 1

    while i < len(value):
        char = value[i]
        if (i == 0 and has_leading_quote) or (i == len(value) - 1 and has_trailing_quote):
            i += 1
            continue
        if char == "\\" and i + 1 < len(value):
            next_char = value[i + 1]
            if next_char in (";", ",", ":", "\\"):
                result.append(next_char)
                i += 2
                continue
        result.append(char)
        i += 1
    return "".join(result)
