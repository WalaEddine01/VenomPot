# 🍯 VenomPot - SSH Honeypot with Real-Time Visualization

<p align="center">
  <img src="frontend/assets/honeypy-logo-white.png" alt="VenomPot Logo" width="150">
</p>

A sophisticated SSH honeypot with real-time attack visualization, geographic tracking, and threat intelligence integration.

## ✨ Features

- **SSH Honeypot** - Captures attacker credentials and commands on port 2224
- **Realistic Fake Shell** - 50+ Linux commands with authentic responses
- **Real-Time Visualization** - Interactive D3.js network graph
- **Geographic Tracking** - GeoIP lookup with country/city/ASN info
- **TOR Detection** - Identifies connections from TOR exit nodes
- **Risk Scoring** - Automatic threat level assessment (0-100)
- **Live Dashboard** - WebSocket-powered real-time updates

## 📸 Dashboard

The visualization shows:

- 🟢 **Honeypot Server** (center node)
- 🔵 **Country Nodes** (grouped by origin)
- 🟣 **TOR Exit Nodes**
- 🔴 **VPN/Proxy Connections**
- 🟠 **Hosting/Cloud IPs**
- 🟢 **Residential IPs**

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Honeypot

```bash
python VenomPot/server.py
```

This starts:

- SSH Honeypot on port `2224`
- WebSocket server on port `8765`

### 3. Open the Dashboard

```bash
cd frontend
python -m http.server 8080
```

Then open `http://localhost:8080` in your browser.

### 4. Test the Honeypot

```bash
ssh user@localhost -p 2224
# Use any password - it will always accept
```

## 📁 Project Structure

```
VenomPot/
├── backend/
│   ├── events.py      # Event bus with logging
│   ├── geoip.py       # GeoIP + TOR detection
│   ├── risk.py        # Risk scoring engine
│   └── ws.py          # WebSocket server
├── frontend/
│   ├── assets/        # Logo and images
│   ├── graph.js       # D3.js visualization
│   └── index.html     # Dashboard UI
├── logs/
│   └── sessions.json  # Attack logs (JSON lines)
├── VenomPot/
│   ├── server.py      # Main SSH honeypot server
│   ├── shell.py       # Fake shell implementation
│   └── users.py       # User configuration
├── GeoLite2-*.mmdb    # MaxMind GeoIP databases
├── tor_exit_nodes.txt # TOR exit node list (~1200 IPs)
└── requirements.txt   # Python dependencies
```

## 🔧 Configuration

### Ports

| Service      | Port | Description          |
| ------------ | ---- | -------------------- |
| SSH Honeypot | 2224 | Fake SSH server      |
| WebSocket    | 8765 | Real-time events     |
| Frontend     | 8080 | Dashboard (optional) |

### Risk Scoring

| Factor             | Points |
| ------------------ | ------ |
| TOR Exit Node      | +40    |
| VPN/Proxy          | +25    |
| Hosting/Cloud      | +20    |
| Auth Attempt       | +15    |
| Dangerous Command  | +35    |
| Suspicious Command | +15    |
| Recon Command      | -5     |

## 🛡️ Fake Shell Commands

The honeypot supports 50+ realistic commands:

| Category   | Commands                                       |
| ---------- | ---------------------------------------------- |
| Navigation | `cd`, `pwd`, `ls -la`                          |
| Files      | `cat`, `head`, `tail`, `touch`, `rm`           |
| System     | `uname -a`, `hostname`, `uptime`, `free`, `df` |
| Network    | `ifconfig`, `ip addr`, `netstat`, `ping`       |
| User       | `whoami`, `id`, `w`, `who`, `history`          |
| Security   | `sudo` (captures passwords), `su`, `chmod`     |
| Services   | `systemctl`, `service`, `crontab`              |

## 📊 Logs

All events are logged to `logs/sessions.json` in JSON Lines format:

```json
{"time": 1736617200, "type": "auth", "ip": "192.168.1.100", "geo": {"country": "US", "tor": true}, "username": "root", "password": "admin123", "risk": 55}
{"time": 1736617205, "type": "command", "ip": "192.168.1.100", "command": "cat /etc/passwd", "risk": 70}
```

## 🔑 Requirements

- Python 3.8+
- MaxMind GeoLite2 databases (City, ASN)
- Modern browser for dashboard

## 📜 License

MIT License - Use responsibly for research and defense purposes only.

## ⚠️ Disclaimer

This tool is designed for **security research** and **defensive purposes**.
Deploy only on networks you own or have explicit permission to monitor.
