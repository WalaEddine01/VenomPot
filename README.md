[![VenomPot Logo](https://github.com/WalaEddine01/VenomPot/blob/main/assets/images/honeypy-logo-white.png)](https://github.com/WalaEddine01/VenomPot)
# VenomPot — HTTP Honeypot & Dashboard

Lightweight HTTP honeypot and local dashboard for collecting and inspecting HTTP activity. This repository contains a Flask-based honeypot service, a Dash dashboard to visualize collected logs, parsers for the logs and several decoy templates and payloads used by the honeypot.

Important: this project contains decoy files and example payloads intended for research and detection. Do not run this code on production or public-facing infrastructure without understanding risks.

## Quick Start
1. Clone the repository:
   ```bash
   git clone https://github.com/WalaEddine01/VenomPot.git
    cd VenomPot
    ```
2. Install dependencies:
    ```bash
    pip3 install -r requirements.txt
    ```
3. Run the honeypot:
    ```bash
    python3 web_VenomPot.py
    ```
4. Access the web app at `http://localhost:8080`.

5. Run the dashboard:
    ```bash
    python3 web_APP.py
    ```

6. Access the dashboard at `http://localhost:8050`.

