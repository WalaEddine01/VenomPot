import os
import sys
import socket
import threading
import asyncio
import paramiko
import websockets

# Ensure project root is on sys.path so `from backend...` works when this
# script is executed directly (python VenomPot/server.py)
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.geoip import geo_lookup
from backend.ws import WSServer
from backend.events import EVENTS
from VenomPot.shell import FakeShell

# Use a persistent host key so SSH fingerprint stays constant across restarts
HOST_KEY_PATH = os.path.join(ROOT, "honeypot_host_key")

def load_or_create_host_key():
    if os.path.exists(HOST_KEY_PATH):
        return paramiko.RSAKey(filename=HOST_KEY_PATH)
    key = paramiko.RSAKey.generate(2048)
    key.write_private_key_file(HOST_KEY_PATH)
    print(f"[+] Generated new host key: {HOST_KEY_PATH}")
    return key

HOST_KEY = load_or_create_host_key()

class SSHServer(paramiko.ServerInterface):
    def __init__(self, ip):
        self.ip = ip

    def check_auth_password(self, u, p):
        EVENTS.emit({
            "type": "auth",
            "ip": self.ip,
            "geo": geo_lookup(self.ip),
            "username": u,
            "password": p
        })
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        return True

def ssh_worker():
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 2224))
    sock.listen(100)
    print("[+] SSH honeypot on 2224")

    while True:
        try:
            c, addr = sock.accept()
            ip = addr[0]
            geo = geo_lookup(ip)
            print(f"[+] Connection from {ip} ({geo.get('country', 'UNK')})")

            try:
                transport = paramiko.Transport(c)
                transport.add_server_key(HOST_KEY)
                transport.start_server(server=SSHServer(ip))
                chan = transport.accept(20)

                if chan:
                    threading.Thread(
                        target=FakeShell(chan, ip, geo).run,
                        daemon=True
                    ).start()
            except paramiko.SSHException as e:
                print(f"[-] SSH error from {ip}: {e}")
            except Exception as e:
                print(f"[-] Error handling {ip}: {e}")
        except Exception as e:
            print(f"[-] Accept error: {e}")

async def main():
    ws = WSServer()
    loop = asyncio.get_running_loop()
    EVENTS.attach_ws(ws, loop)

    threading.Thread(target=ssh_worker, daemon=True).start()

    async with websockets.serve(ws.handler, "0.0.0.0", 8765):
        print("[+] WebSocket on 8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
