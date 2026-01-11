import os
import geoip2.database

# Get project root directory
ROOT = os.path.dirname(os.path.dirname(__file__))

CITY_DB = os.path.join(ROOT, "GeoLite2-City.mmdb")
ASN_DB = os.path.join(ROOT, "GeoLite2-ASN.mmdb")
TOR_FILE = os.path.join(ROOT, "tor_exit_nodes.txt")

city_reader = geoip2.database.Reader(CITY_DB)
asn_reader = geoip2.database.Reader(ASN_DB)

# Load TOR exit nodes into a set for O(1) lookup
TOR_EXIT_NODES = set()
if os.path.exists(TOR_FILE):
    with open(TOR_FILE, "r") as f:
        for line in f:
            ip = line.strip()
            if ip and not ip.startswith("#"):
                TOR_EXIT_NODES.add(ip)
    print(f"[+] Loaded {len(TOR_EXIT_NODES)} TOR exit nodes")

HOSTING_KEYWORDS = [
    "amazon", "aws", "google", "gcp", "azure",
    "digitalocean", "ovh", "linode", "hetzner"
]

def geo_lookup(ip):
    geo = {
        "country": "UNK",
        "city": "UNK",
        "asn": "UNK",
        "org": "UNK",
        "hosting": False,
        "vpn": False,
        "tor": ip in TOR_EXIT_NODES  # Check if IP is a TOR exit node
    }

    try:
        r = city_reader.city(ip)
        geo["country"] = r.country.iso_code or "UNK"
        geo["city"] = r.city.name or "UNK"
    except:
        pass

    try:
        a = asn_reader.asn(ip)
        geo["asn"] = f"AS{a.autonomous_system_number}"
        geo["org"] = a.autonomous_system_organization or "UNK"

        org = geo["org"].lower()
        if any(k in org for k in HOSTING_KEYWORDS):
            geo["hosting"] = True
        if "vpn" in org or "proxy" in org:
            geo["vpn"] = True
    except:
        pass

    return geo
