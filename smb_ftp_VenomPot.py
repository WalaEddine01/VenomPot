import socket
import threading
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone

# ===================== LOGGING CONFIG =====================

LOG_FILENAME = "logs/ftp_smb_logs.log"

# Ensure logs dir exists (same as your web pot)
import os
if not os.path.exists("logs"):
    os.makedirs("logs")

logging_format = logging.Formatter("%(message)s")

# Logger for FTP/SMB
fs_logger = logging.getLogger("FTP_SMB_Logger")
fs_logger.setLevel(logging.INFO)
fs_handler = RotatingFileHandler(LOG_FILENAME, maxBytes=5_000_000, backupCount=5)
fs_handler.setFormatter(logging_format)
fs_logger.addHandler(fs_handler)

def log_event(proto, client_ip, data, event_type="connection"):
    """
    Logs events in a key=value format for easy parsing later.
    """
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    log_msg = (
        f"event={event_type} "
        f"protocol={proto} "
        f"client_ip={client_ip} "
        f"ts={ts} "
        f"data=\"{data}\""
    )
    fs_logger.info(log_msg)
    print(f"[+] {proto} {event_type} from {client_ip}: {data}")

# ===================== FTP HONEYPOT =====================

def handle_ftp_client(client_socket, address):
    ip = address[0]
    log_event("FTP", ip, "Connection established")

    try:
        # 1. Send Banner (Mimic vsFTPd)
        client_socket.send(b"220 (vsFTPd 3.0.3)\r\n")

        # 2. Receive Data (Simple state machine)
        while True:
            data = client_socket.recv(1024).decode('utf-8', errors='ignore').strip()
            if not data:
                break

            # Log whatever commands they send
            log_event("FTP", ip, data, event_type="payload")

            if data.upper().startswith("USER"):
                client_socket.send(b"331 Please specify the password.\r\n")
            
            elif data.upper().startswith("PASS"):
                # Always fail the login to trap them in a loop or make them leave
                client_socket.send(b"530 Login incorrect.\r\n")
            
            elif data.upper().startswith("QUIT"):
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
    """
    A low-interaction SMB trap. It accepts the handshake and logs it.
    It does not implement the full SMB protocol, which is complex.
    It catches worms (like WannaCry probes) that try to negotiate protocols.
    """
    ip = address[0]
    log_event("SMB", ip, "Connection established")

    try:
        # Receive the Negotiate Protocol Request
        data = client_socket.recv(1024)
        
        # Convert bytes to hex for analysis if needed, or just log length
        hex_dump = data.hex()[:50] # Log first 50 bytes hex
        log_event("SMB", ip, f"Header_Hex={hex_dump}", event_type="negotiate")

        # We don't respond with valid SMB packets to avoid helping them.
        # We just hold the connection briefly or close it.
        client_socket.close()

    except Exception as e:
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
        print(f"[!] SMB Failed to bind (sudo required?): {e}")

# ===================== THREADING RUNNER =====================

def run_ftp_smb_VenomPot(ftp_port=21, smb_port=445):
    # Start FTP Thread
    t_ftp = threading.Thread(target=start_ftp_server, args=(ftp_port,))
    t_ftp.daemon = True
    t_ftp.start()

    # Start SMB Thread
    t_smb = threading.Thread(target=start_smb_server, args=(smb_port,))
    t_smb.daemon = True
    t_smb.start()

    # Keep main thread alive
    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass