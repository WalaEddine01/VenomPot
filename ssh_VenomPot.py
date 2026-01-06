import socket
import threading
import logging
from logging.handlers import RotatingFileHandler
import paramiko
import time
import random
# NEW IMPORT
from virtual_fs import VirtualFS

# ===================== CONFIG =====================

SSH_BANNER = "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"
HOST_KEY = paramiko.RSAKey(filename="server.key") # Generate this using: ssh-keygen -t rsa -f server.key

LISTEN_ADDR = "0.0.0.0"
LISTEN_PORT = 2223

USERNAME = "user"
PASSWORD = "password"

# ===================== LOGGING =====================

logging_format = logging.Formatter("%(asctime)s - %(message)s")

venom_logger = logging.getLogger("VenomSSH")
venom_logger.setLevel(logging.INFO)
venom_handler = RotatingFileHandler("logs/ssh_logs.log", maxBytes=200000, backupCount=5)
venom_handler.setFormatter(logging_format)
venom_logger.addHandler(venom_handler)

# ===================== FAKE SHELL =====================

def emulated_shell(channel, client_ip):
    # Initialize the Virtual Filesystem for this specific session
    vfs = VirtualFS(user=USERNAME)
    
    prompt_base = f"{USERNAME}@ubuntu"
    
    def get_prompt():
        # returns user@ubuntu:~/dir$ 
        cwd = vfs.get_pwd()
        if cwd.startswith(f"/home/{USERNAME}"):
            cwd = cwd.replace(f"/home/{USERNAME}", "~")
        return f"\r\n{prompt_base}:{cwd}$ ".encode()

    def slow_send(data_str):
        # Simulate network latency/typing
        channel.send(data_str.replace("\n", "\r\n").encode())

    # Initial Welcome Message
    channel.send(b"Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-91-generic x86_64)\r\n\r\n")
    channel.send(b" * Documentation:  https://help.ubuntu.com\r\n")
    channel.send(b" * Management:     https://landscape.canonical.com\r\n")
    channel.send(b" * Support:        https://ubuntu.com/advantage\r\n\r\n")
    channel.send(f"Last login: {time.ctime()} from {client_ip}\r\n".encode())
    
    channel.send(get_prompt())

    command_buffer = b""

    while True:
        try:
            char = channel.recv(1)
            if not char:
                break
        except:
            break

        # ENTER KEY
        if char in (b"\r", b"\n"):
            channel.send(b"\r\n")
            cmd_line = command_buffer.strip().decode("utf-8", errors="ignore")
            command_buffer = b""

            # Log the command
            if cmd_line:
                venom_logger.info(f"CMD | {client_ip} | {cmd_line}")

            parts = cmd_line.split()
            if not parts:
                channel.send(get_prompt())
                continue

            cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            arg_str = parts[1] if len(parts) > 1 else ""

            # ---- COMMAND HANDLER ----
            
            if cmd == "exit" or cmd == "logout":
                channel.send(b"logout\r\n")
                break

            elif cmd == "pwd":
                slow_send(vfs.get_pwd())

            elif cmd == "cd":
                target = arg_str if arg_str else f"/home/{USERNAME}"
                err = vfs.cd(target)
                if err:
                    slow_send(err)

            elif cmd == "ls":
                # Handle flags roughly
                target = "."
                show_hidden = False
                long_fmt = False
                
                for a in args:
                    if a.startswith("-"):
                        if "l" in a: long_fmt = True
                        if "a" in a: show_hidden = True
                    else:
                        target = a
                
                if long_fmt:
                    res = vfs.ls_l(target)
                else:
                    res = vfs.ls(target)
                slow_send(res)

            elif cmd == "mkdir":
                if not arg_str:
                    slow_send("mkdir: missing operand")
                else:
                    err = vfs.mkdir(arg_str)
                    if err: slow_send(err)

            elif cmd == "rm":
                if not arg_str:
                    slow_send("rm: missing operand")
                else:
                    err = vfs.rm(arg_str)
                    if err: slow_send(err)
            
            elif cmd == "touch":
                if arg_str:
                    vfs.touch(arg_str)

            elif cmd == "cat":
                if not arg_str:
                    pass # cat waits for stdin, ignore for pot
                else:
                    res = vfs.cat(arg_str)
                    slow_send(res)

            elif cmd == "whoami":
                slow_send(USERNAME)

            elif cmd == "id":
                slow_send(f"uid=1000({USERNAME}) gid=1000({USERNAME}) groups=1000({USERNAME})")

            elif cmd == "uname":
                slow_send("Linux")

            elif cmd == "history":
                slow_send("1  ls\n2  exit")

            elif cmd == "clear":
                channel.send(b"\033[2J\033[H")

            # Default catch-all
            else:
                slow_send(f"{cmd}: command not found")

            channel.send(get_prompt())
            continue

        # BACKSPACE HANDLING
        if char in (b"\x7f", b"\b"):
            if len(command_buffer) > 0:
                command_buffer = command_buffer[:-1]
                # Erase character from terminal: Move back, Space, Move Back
                channel.send(b"\b \b")
            continue

        # Simple Echo
        command_buffer += char
        channel.send(char)

    channel.close()

# ===================== SSH SERVER SETUP =====================

class Server(paramiko.ServerInterface):
    def __init__(self, client_ip, username, password):
        self.client_ip = client_ip
        self.username = username
        self.password = password
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == "session": return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auth(self, username):
        return "password"

    def check_auth_password(self, username, password):
        venom_logger.info(f"LOGIN_ATTEMPT | {self.client_ip} | {username}:{password}")
        if username == self.username and password == self.password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

def handle_client(client, address):
    client_ip = address[0]
    print(f"[+] SSH Connection from {client_ip}")
    try:
        transport = paramiko.Transport(client)
        transport.local_version = SSH_BANNER
        transport.add_server_key(HOST_KEY)
        server = Server(client_ip, USERNAME, PASSWORD)
        try:
            transport.start_server(server=server)
        except paramiko.SSHException:
            return

        channel = transport.accept(20)
        if channel is None: return

        emulated_shell(channel, client_ip)

    except Exception as e:
        print(f"[!] SSH Error: {e}")
    finally:
        try: transport.close()
        except: pass
        client.close()

# def run_ssh_VenomPot():
#     # Ensure key exists
#     if not list(map(str, sorted(paramiko.util.list_keys()))): # rough check
#         # In reality you must generate a key file beforehand:
#         # ssh-keygen -f server.key -N ""
#         pass

#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     sock.bind((LISTEN_ADDR, LISTEN_PORT))
#     sock.listen(100)
#     print(f"[+] SSH Honeypot listening on {LISTEN_PORT} (User: {USERNAME})")

#     while True:
#         client, addr = sock.accept()
#         t = threading.Thread(target=handle_client, args=(client, addr))
#         t.daemon = True
#         t.start()

# if __name__ == "__main__":
#     run_ssh_VenomPot()
def run_ssh_VenomPot(port=2223, username="user", password="password"):
    # Ensure we use the arguments provided
    global USERNAME, PASSWORD
    USERNAME = username
    PASSWORD = password

    # Ensure key exists (Basic check)
    try:
        # In a real scenario, check if server.key exists; if not, you might want to raise an error
        # or generate one programmatically.
        pass 
    except Exception as e:
        print(f"[!] SSH Key Error: {e}")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind((LISTEN_ADDR, port))
        sock.listen(100)
        print(f"[+] SSH Honeypot listening on {port} (User: {username})")
    except Exception as e:
        print(f"[!] Could not start SSH server on port {port}: {e}")
        return

    while True:
        try:
            client, addr = sock.accept()
            t = threading.Thread(target=handle_client, args=(client, addr))
            t.daemon = True
            t.start()
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    # Default execution if run standalone
    run_ssh_VenomPot(LISTEN_PORT, USERNAME, PASSWORD)