import json
import time
import os

# Get project root directory
ROOT = os.path.dirname(__file__)
LOG_FILE = os.path.join(ROOT, "logs", "sessions.json")

# Ensure logs directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log_event(event_type, data):
    entry = {
        "time": time.time(),
        "type": event_type,
        "data": data
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
