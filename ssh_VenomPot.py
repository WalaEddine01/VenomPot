import socket
import threading
import logging
from logging.handlers import RotatingFileHandler
import paramiko
import time
import random
import os
import traceback
from datetime import datetime
# SILENCE PARAMIKO INTERNAL LOGGING
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
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
    # Initialize VFS
    vfs = VirtualFS(user=USERNAME) 
    
    while True:
        # 1. Get the dynamic prompt from VFS
        prompt = vfs.get_prompt() 
        
        # 2. Send prompt to attacker
        channel.send(prompt)
        
        command = ""
        while True:
            char = channel.recv(1)
            if not char: break # Connection closed
            char = char.decode("utf-8", errors="ignore")
            
            # Simple Enter Key
            if char == "\r":
                channel.send("\r\n")
                break
                
            # Basic Backspace support
            if char == '\x7f': 
                if len(command) > 0:
                    command = command[:-1]
                    channel.send("\b \b")
                continue
                
            # Echo and build command
            channel.send(char)
            command += char
            
        command = command.strip()
        if command == "exit": 
            break
        
        # 3. Execute and get response
        response = vfs.execute_command(command)
        
        # 4. Send response if exists
        if response:
            channel.send(response.replace("\n", "\r\n") + "\r\n")
            
        # Log it
        venom_logger.info(f"CMD | {client_ip} | {command}")

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
# ===================== ERROR LOGGING CONFIG =====================
ERROR_LOG_DIR = "logs/errors"
if not os.path.exists(ERROR_LOG_DIR):
    os.makedirs(ERROR_LOG_DIR)

def log_error_to_file(client_ip, exception_msg):
    """Stores full traceback in a dated file for debugging."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_file = os.path.join(ERROR_LOG_DIR, f"ssh_errors_{date_str}.log")
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"--- ERROR AT {timestamp} | IP: {client_ip} ---\n")
        f.write(f"Message: {exception_msg}\n")
        f.write(traceback.format_exc())
        f.write("-" * 50 + "\n\n")
        
# ===================== HANDLE CLIENT =====================

def handle_client(client, address):
    client_ip = address[0]
    print(f"[+] SSH Connection from {client_ip}")
    transport = None
    
    try:
        transport = paramiko.Transport(client)
        transport.local_version = SSH_BANNER
        transport.add_server_key(HOST_KEY)
        
        server = Server(client_ip, USERNAME, PASSWORD)
        
        try:
            # start_server starts a background thread. 
            # If it fails, our CRITICAL log level silences the default output.
            transport.start_server(server=server)
        except Exception as e:
            error_str = str(e)
            # Identify the tool for your main audit log
            tool = "Scanner/Bruteforce"
            if "MessageOrderError" in error_str or "34" in error_str:
                tool = "Hydra/Medusa"
            elif "banner" in error_str.lower() or not error_str:
                tool = "Nmap/ZGrab"
            
            # Log clean summary to main audit log
            venom_logger.info(f"SCAN | {client_ip} | Tool: {tool} | Msg: {error_str}")
            
            # Print ONLY the clean summary to terminal
            print(f"[*] SSH Automated Attack detected from {client_ip} (Tool: {tool})")
            
            # Save full technical traceback to your dated error log
            # log_error_to_file(client_ip, error_str)
            emulated_shell(channel, client_ip, server.username)
            return

        # Wait for the client to request a channel
        channel = transport.accept(20)
        if channel is None:
            return

        emulated_shell(channel, client_ip)

    except Exception as e:
        # Catch unexpected session errors silently
        log_error_to_file(client_ip, str(e))
    finally:
        try:
            if transport:
                transport.close()
        except:
            pass
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