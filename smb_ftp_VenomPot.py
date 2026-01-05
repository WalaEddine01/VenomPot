import socket
import threading
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
import os

# NEW IMPORT: Use the same virtual FS logic
from virtual_fs import VirtualFS

# ===================== LOGGING CONFIG =====================

LOG_FILENAME = "logs/ftp_smb_logs.log"
if not os.path.exists("logs"):
    os.makedirs("logs")

logging_format = logging.Formatter("%(message)s")
fs_logger = logging.getLogger("FTP_SMB_Logger")
fs_logger.setLevel(logging.INFO)
fs_handler = RotatingFileHandler(LOG_FILENAME, maxBytes=5_000_000, backupCount=5)
fs_handler.setFormatter(logging_format)
fs_logger.addHandler(fs_handler)

def log_event(proto, client_ip, data, event_type="connection"):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    log_msg = f"event={event_type} protocol={proto} client_ip={client_ip} ts={ts} data=\"{data}\""
    fs_logger.info(log_msg)
    print(f"[+] {proto} {event_type} from {client_ip}: {data}")

# ===================== FTP HONEYPOT (DYNAMIC FS) =====================

def handle_ftp_client(client_socket, address):
    ip = address[0]
    log_event("FTP", ip, "Connection established")
    
    # Instantiate a fresh filesystem for this FTP session
    vfs = VirtualFS(user="ftp_user")
    
    # State tracking
    authenticated = False
    
    try:
        client_socket.send(b"220 (vsFTPd 3.0.3)\r\n")

        while True:
            data = client_socket.recv(1024).decode('utf-8', errors='ignore').strip()
            if not data: break

            log_event("FTP", ip, data, event_type="payload")
            cmd = data.split(" ")[0].upper()
            arg = data.split(" ", 1)[1] if " " in data else ""

            if cmd == "USER":
                client_socket.send(b"331 Please specify the password.\r\n")
            
            elif cmd == "PASS":
                # Allow login to let them interact with the fake FS
                client_socket.send(b"230 Login successful.\r\n")
                authenticated = True

            elif not authenticated and cmd not in ["QUIT", "USER", "PASS"]:
                 client_socket.send(b"530 Please login with USER and PASS.\r\n")

            elif cmd == "PWD":
                # Return the virtual current directory
                cwd = vfs.get_pwd()
                client_socket.send(f'257 "{cwd}"\r\n'.encode())

            elif cmd == "CWD":
                err = vfs.cd(arg)
                if err:
                    client_socket.send(b"550 Failed to change directory.\r\n")
                else:
                    client_socket.send(b"250 Directory successfully changed.\r\n")

            elif cmd == "MKD":
                err = vfs.mkdir(arg)
                if err:
                    client_socket.send(b"550 Create directory operation failed.\r\n")
                else:
                    client_socket.send(f'257 "{arg}" created\r\n'.encode())

            elif cmd == "DELE" or cmd == "RMD":
                err = vfs.rm(arg)
                if err:
                    client_socket.send(b"550 Delete operation failed.\r\n")
                else:
                    client_socket.send(b"250 Delete operation successful.\r\n")

            elif cmd == "LIST" or cmd == "NLST":
                client_socket.send(b"150 Here comes the directory listing.\r\n")
                # We need to simulate the Data Channel transfer.
                # In a real passive FTP, we'd open a second port.
                # Since this is a simple honeypot, we cheat and send it on control 
                # OR we just say transfer complete if we can't handle passive.
                # NOTE: Real FTP clients expect a 2nd connection. 
                # For this honeypot simplicity, we will assume the client might fail
                # or we just log the attempt. To support LIST, we'd need full PASV logic.
                # We will send a 425 error (Use PORT or PASV first) to confuse automated tools
                # OR send the list in-band if they support it (they don't usually).
                
                # However, to be "helpful", we'll just log it and close nicely.
                # Implementing PASV/PORT in a single script is code-heavy.
                client_socket.send(b"425 Use PORT or PASV first.\r\n")

            elif cmd == "SYST":
                client_socket.send(b"215 UNIX Type: L8\r\n")

            elif cmd == "QUIT":
                client_socket.send(b"221 Goodbye.\r\n")
                break
            
            else:
                client_socket.send(b"500 Unknown command.\r\n")

    except Exception as e:
        log_event("FTP", ip, f"Error: {str(e)}", event_type="error")
    finally:
        client_socket.close()

def start_ftp_server(port=21):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(("0.0.0.0", port))
        server.listen(5)
        print(f"[-] FTP Honeypot listening on port {port}...")
        while True:
            client, addr = server.accept()
            threading.Thread(target=handle_ftp_client, args=(client, addr)).start()
    except Exception as e:
        print(f"[!] FTP Failed to bind: {e}")

# ===================== SMB HONEYPOT =====================

def handle_smb_client(client_socket, address):
    ip = address[0]
    log_event("SMB", ip, "Connection established")
    try:
        # SMB is binary. We read the negotiation packet.
        data = client_socket.recv(4096)
        
        # Simple heuristic to detect SMB dialects in the raw bytes
        smb_dialects = []
        if b"SMB 2.002" in data: smb_dialects.append("SMB2")
        if b"SMB 2.???" in data: smb_dialects.append("SMB2_Wildcard")
        if b"\xffSMB" in data: smb_dialects.append("SMB1")

        readable_info = f"Length: {len(data)} bytes. Dialects found: {smb_dialects}"
        log_event("SMB", ip, readable_info, event_type="negotiate")

        # To make it "look real", we should ideally respond with a Negotiate Response.
        # But sending garbage usually makes scanners disconnect immediately.
        # We will hold the connection open for 5 seconds to simulate processing
        # ("Tarpit" behavior) which annoys scanners.
        import time
        time.sleep(2) 
        client_socket.close()

    except Exception:
        pass

def start_smb_server(port=445):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(("0.0.0.0", port))
        server.listen(5)
        print(f"[-] SMB Honeypot listening on port {port}...")
        while True:
            client, addr = server.accept()
            threading.Thread(target=handle_smb_client, args=(client, addr)).start()
    except Exception as e:
        print(f"[!] SMB Failed: {e}")

# ===================== RUNNER =====================

def run_ftp_smb_VenomPot(ftp_port=21, smb_port=445):
    t_ftp = threading.Thread(target=start_ftp_server, args=(ftp_port,))
    t_ftp.daemon = True
    t_ftp.start()

    t_smb = threading.Thread(target=start_smb_server, args=(smb_port,))
    t_smb.daemon = True
    t_smb.start()

    try:
        while True: pass
    except KeyboardInterrupt: pass