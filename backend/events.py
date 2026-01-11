import json
import time
import asyncio
import os
from backend.risk import compute_risk

# Get project root directory
ROOT = os.path.dirname(os.path.dirname(__file__))
LOG_FILE = os.path.join(ROOT, "logs", "sessions.json")

# Ensure logs directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

class EventBus:
    def __init__(self):
        self.ws = None
        self.loop = None

    def attach_ws(self, ws_server, loop):
        self.ws = ws_server
        self.loop = loop

    def emit(self, event):
        event["time"] = time.time()
        event["risk"] = compute_risk(event)

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

        if self.ws and self.loop:
            asyncio.run_coroutine_threadsafe(
                self.ws.broadcast(event),
                self.loop
            )

EVENTS = EventBus()
