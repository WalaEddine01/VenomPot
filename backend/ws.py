import json
import os
import websockets
import asyncio

# Resolve LOG_FILE relative to project root (parent of backend/)
ROOT = os.path.dirname(os.path.dirname(__file__))
LOG_FILE = os.path.join(ROOT, "logs", "sessions.json")

class WSServer:
    def __init__(self):
        self.clients = set()

    def load_history(self):
        """Load historical events from log file."""
        events = []
        print(f"[WS] Loading history from: {LOG_FILE}")
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                events.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
                print(f"[WS] Loaded {len(events)} events from history")
            except Exception as e:
                print(f"[WS] Error loading history: {e}")
        else:
            print(f"[WS] History file not found: {LOG_FILE}")
        return events

    async def handler(self, ws):
        self.clients.add(ws)
        print(f"[WS] Client connected. Total: {len(self.clients)}")
        try:
            # Send historical data on connect
            history = self.load_history()
            if history:
                msg = json.dumps({"type": "history", "events": history})
                await ws.send(msg)
                print(f"[WS] Sent history ({len(history)} events) to client")
            async for _ in ws:
                pass
        finally:
            self.clients.remove(ws)
            print(f"[WS] Client disconnected. Total: {len(self.clients)}")

    async def broadcast(self, event):
        if not self.clients:
            return
        # ensure clients know GPT-5 is enabled
        try:
            event["enable_gpt5"] = True
            event["model"] = event.get("model", "gpt-5")
        except Exception:
            pass
        msg = json.dumps(event)
        await asyncio.gather(*(c.send(msg) for c in self.clients))
