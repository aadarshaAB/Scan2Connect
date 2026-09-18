import re


def parse_wifi_qr(data):
    try:
        ssid_match = re.search(r"WIFI:S:(.*?);", data)
        pass_match = re.search(r"P:(.*?);", data)
        if ssid_match and pass_match:
            return ssid_match.group(1), pass_match.group(1)
    except Exception:
        pass
    return None, None
