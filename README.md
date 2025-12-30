# LOGO
[![VenomPot Logo](https://raw.githubusercontent.com/WalaEddine01/VenomPot/assets/images/honeypy-logo-white.png)](https://github.com/WalaEddine01/VenomPot)
# VenomPot — HTTP Honeypot & Dashboard

Lightweight HTTP honeypot and local dashboard for collecting and inspecting HTTP activity. This repository contains a Flask-based honeypot service, a Dash dashboard to visualize collected logs, parsers for the logs and several decoy templates and payloads used by the honeypot.

Important: this project contains decoy files and example payloads intended for research and detection. Do not run this code on production or public-facing infrastructure without understanding risks.

## Quick links
- Honeypot server: [web_VenomPot.py](web_VenomPot.py) — see [`web_VenomPot.web_VenomPot`](web_VenomPot.py) and [`web_VenomPot.run_web_VenomPot`](web_VenomPot.py)  
- Dashboard (Dash): [web_APP.py](web_APP.py) — exposes [`web_APP.app`](web_APP.py)  
- Log parser: [dashboard_data_parser.py](dashboard_data_parser.py) — see [`dashboard_data_parser.parse_http_requests_log`](dashboard_data_parser.py) and [`dashboard_data_parser.top_10_calculator`](dashboard_data_parser.py)  
- Entrypoint script: [VenomPot.py](VenomPot.py)  
- Requirements: [requirements.txt](requirements.txt)  
- Example env: [.env.example](.env.example) and active [.env](.env)  
- Templates: [templates/](templates/) — includes [templates/login.html](templates/login.html), [templates/dashboard.html](templates/dashboard.html), [templates/notFound.html](templates/notFound.html), and decoy payloads like [templates/.config.html](templates/.config.html) and [templates/.config_html.hta](templates/.config_html.hta)  
- Logs: [logs/http_logs.log](logs/http_logs.log) (runtime)

## Features
- Flask-based HTTP honeypot with decoy endpoints and downloadable decoy files ([web_VenomPot.py](web_VenomPot.py)).  
- Live Dash dashboard that reads the honeypot log and shows a table and top-attacker bar chart ([web_APP.py](web_APP.py)).  
- Simple log parser that normalizes key fields into a Pandas DataFrame ([dashboard_data_parser.py](dashboard_data_parser.py)).  
- Several template decoys (HTML/HTA/scripts) in [templates/](templates/).

## Install
```sh
python3 -m pip install -r [requirements.txt](http://_vscodecontentref_/0)