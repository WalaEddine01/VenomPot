import socket
import threading
import logging
from logging.handlers import RotatingFileHandler
import paramiko
import time
import random

# ===================== CONFIG =====================

SSH_BANNER = "SSH-2.0-MySSHServer_1.0"
HOST_KEY = paramiko.RSAKey(filename="server.key")

LISTEN_ADDR = "127.0.0.1"
LISTEN_PORT = 2223

USERNAME = "username"
PASSWORD = "1123"

# ===================== LOGGING =====================

logging_format = logging.Formatter("%(asctime)s - %(message)s")

venom_logger = logging.getLogger("Venom")
venom_logger.setLevel(logging.INFO)
venom_handler = RotatingFileHandler("audits.log", maxBytes=2000, backupCount=5)
venom_handler.setFormatter(logging_format)
venom_logger.addHandler(venom_handler)

# ===================== FAKE SHELL =====================

def emulated_shell(channel, client_ip):
    prompt = b"r34l-4dmin@ubuntu:~$ "
    hostname = b"ubuntu"
    user = b"root"
    cwd = b"/home/joxh199"
    history = []

    def slow_send(data, min_d=0.02, max_d=0.06):
        for b in data:
            channel.send(bytes([b]))
            time.sleep(random.uniform(min_d, max_d))

    channel.send(b"\r\nWelcome to Ubuntu 22.04.3 LTS\r\n")
    channel.send(b"Last login: Tue Jan  1 12:00:00 2026 from ")
    channel.send(client_ip.encode() + b"\r\n\r\n")
    channel.send(prompt)

    command = b""

    while True:
        char = channel.recv(1)
        if not char:
            break

        # ENTER
        if char in (b"\r", b"\n"):
            channel.send(b"\r\n")
            cmd = command.strip()
            history.append(cmd.decode(errors="ignore"))
            command = b""

            # ---- COMMANDS ----
            if cmd == b"exit" or cmd == b"logout":
                channel.send(b"logout\r\n")
                break

            elif cmd == b"pwd":
                channel.send(cwd + b"\r\n")

            elif cmd == b"ls":
                slow_send(b"secrets.txt  clientsID.csv  notes.md\r\n")

            elif cmd == b"whoami":
                channel.send(user + b"\r\n")

            elif cmd == b"hostname":
                channel.send(hostname + b"\r\n")

            elif cmd == b"uname -a":
                channel.send(
                    b"Linux ubuntu 5.15.0-91-generic #101-Ubuntu SMP x86_64 GNU/Linux\r\n"
                )

            elif cmd == b"id":
                channel.send(
                    b"uid=0(root) gid=0(root) groups=0(root)\r\n"
                )

            elif cmd.startswith(b"cat"):
                if b"secrets.txt" in cmd:
                    channel.send(
                        b"admin:Sup3rS3cret!\r\nbackup:backup123\r\n"
                    )
                elif b"clientsID.csv" in cmd:
                    channel.send(
                        b"id,name,email\r\n1,John,john@mail.com\r\n"
                    )
                else:
                    channel.send(b"cat: file not found\r\n")

            elif cmd == b"history":
                for i, h in enumerate(history[-20:], 1):
                    channel.send(f"{i}  {h}\r\n".encode())

            elif cmd.startswith(b"cd"):
                channel.send(b"\r\n")  # fake success

            elif cmd == b"clear":
                channel.send(b"\033[2J\033[H")

            elif cmd in (b"top", b"htop"):
                channel.send(b"top: command terminated\r\n")

            elif cmd.startswith(b"wget") or cmd.startswith(b"curl"):
                channel.send(b"Connecting... failed: Network unreachable\r\n")

            elif cmd:
                channel.send(cmd + b": command not found\r\n")

            channel.send(prompt)
            continue

        # BACKSPACEe
        if char in (b"\x7f", b"\b"):
            if command:
                command = command[:-1]
                channel.send(b"\b \b")
            continue

        # ANTI-AUTOMATION: DROP FAST INPUT
        if len(command) > 128:
            channel.send(b"\r\nInput overflow detected\r\n")
            break

        # ECHO
        command += char
        channel.send(char)

    channel.close()

# ===================== SSH SERVER =====================

class Server(paramiko.ServerInterface):
    def __init__(self, client_ip, username, password):
        self.client_ip = client_ip
        self.username = username
        self.password = password
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auth(self, username):
        return "password"

    def check_auth_password(self, username, password):
        venom_logger.info(
            f"LOGIN ATTEMPT | {self.client_ip} | {username}:{password}"
        )

        if username == self.username and password == self.password:
            return paramiko.AUTH_SUCCESSFUL

        return paramiko.AUTH_FAILED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True

    def check_channel_exec_request(self, channel, command):
        return True

# ===================== CLIENT HANDLER =====================

def handle_client(client, address):
    client_ip = address[0]
    print(f"[+] Connection from {client_ip}")

    try:
        transport = paramiko.Transport(client)
        transport.local_version = SSH_BANNER
        transport.add_server_key(HOST_KEY)

        server = Server(client_ip, USERNAME, PASSWORD)
        transport.start_server(server=server)

        channel = transport.accept(20)
        if channel is None:
            return

        channel.send(b"Welcome to Ubuntu 22.04 LTS\n\n")
        emulated_shell(channel, client_ip)

    except Exception as e:
        print(f"[!] Error: {e}")

    finally:
        try:
            transport.close()
        except:
            pass
        client.close()

# ===================== MAIN LISTENER =====================

def VenomPot():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((LISTEN_ADDR, LISTEN_PORT))
    sock.listen(100)

    print(f"[+] SSH honeypot listening on {LISTEN_PORT}")

    while True:
        client, addr = sock.accept()
        t = threading.Thread(target=handle_client, args=(client, addr))
        t.daemon = True
        t.start()

# ===================== START =====================

if __name__ == "__main__":
    VenomPot()
