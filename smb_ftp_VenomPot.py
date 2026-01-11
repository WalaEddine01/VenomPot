import socket
import threading
import logging
import random
import time
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
import os
# # --- ADD THESE IMPORTS ---
# import sys
# import tempfile
# import shutil
# from impacket.smbserver import SimpleSMBServer
# from impacket import smbserver
# # -------------------------

# Import the Virtual File System
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
    """
    Logs events in a structured key=value format for easy parsing.
    """
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    # Escape quotes in data to prevent log injection/parsing errors
    safe_data = str(data).replace('"', "'")
    log_msg = f"event={event_type} protocol={proto} client_ip={client_ip} ts={ts} data=\"{safe_data}\""
    fs_logger.info(log_msg)
    print(f"[+] {proto} {event_type} from {client_ip}: {safe_data}")

# ===================== FTP HONEYPOT (REALISTIC) =====================

class FTPSession(threading.Thread):
    """
    Handles a single FTP client session with support for PASV, LIST, RETR, and STOR.
    """
    def __init__(self, conn, addr):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.ip = addr[0]
        self.vfs = VirtualFS(user="ftp_user") # Unique FS state per session
        self.authenticated = False
        self.pasv_socket = None
        self.pasv_conn = None
        self.mode = 'I' # Default to Binary (Image) mode
        self.running = True

    def send_ctrl(self, msg):
        """Send a control message to the client."""
        try:
            self.conn.send((msg + "\r\n").encode('utf-8'))
        except Exception:
            self.running = False

    def close_pasv(self):
        """Clean up passive data connections."""
        if self.pasv_conn:
            try: self.pasv_conn.close()
            except: pass
            self.pasv_conn = None
        if self.pasv_socket:
            try: self.pasv_socket.close()
            except: pass
            self.pasv_socket = None

    def get_data_socket(self):
        """
        Waits for the client to connect to the PASV port.
        Returns the socket or None on failure.
        """
        if not self.pasv_socket:
            self.send_ctrl("425 Use PASV or PORT first.")
            return None
        
        try:
            self.pasv_socket.settimeout(10) # Wait 10s for data connection
            conn, addr = self.pasv_socket.accept()
            self.pasv_conn = conn
            return conn
        except socket.timeout:
            self.send_ctrl("425 Data connection timed out.")
            self.close_pasv()
            return None
        except Exception as e:
            self.send_ctrl(f"425 Error opening data socket: {e}")
            self.close_pasv()
            return None

    def handle_list(self, arg):
        """Handle LIST (ls -l) requests via Data Channel."""
        data_sock = self.get_data_socket()
        if not data_sock: return

        self.send_ctrl("150 Here comes the directory listing.")
        
        try:
            # Generate listing using VirtualFS
            # We treat 'arg' as flags or path. 
            # Simple assumption: arg is usually flags (like -l) or empty in FTP LIST
            listing = self.vfs.do_ls(["-l", "-a"]) 
            
            # FTP listings require CRLF line endings
            listing = listing.replace("\n", "\r\n")
            if not listing.endswith("\r\n"): listing += "\r\n"
            
            data_sock.send(listing.encode('utf-8'))
            self.send_ctrl("226 Directory send OK.")
        except Exception as e:
            self.send_ctrl(f"451 Requested action aborted: {e}")
        finally:
            self.close_pasv()

    def handle_retr(self, filename):
        """Handle RETR (Download) requests."""
        data_sock = self.get_data_socket()
        if not data_sock: return

        self.send_ctrl(f"150 Opening {self.mode} mode data connection for {filename}.")
        
        try:
            # Fetch content from VFS
            content = self.vfs.do_cat([filename])
            
            if "No such file" in content or "Is a directory" in content:
                self.send_ctrl("550 Failed to open file.")
            else:
                data_sock.send(content.encode('utf-8'))
                self.send_ctrl("226 Transfer complete.")
                log_event("FTP", self.ip, f"Downloaded: {filename}", "file_download")
        except Exception:
            self.send_ctrl("550 Failed to read file.")
        finally:
            self.close_pasv()

    def handle_stor(self, filename):
        """Handle STOR (Upload) requests."""
        data_sock = self.get_data_socket()
        if not data_sock: return

        self.send_ctrl("150 Ok to send data.")
        
        try:
            received_data = b""
            while True:
                chunk = data_sock.recv(4096)
                if not chunk: break
                received_data += chunk
            
            # Write to VirtualFS
            # 1. Create file entry
            self.vfs.do_touch([filename])
            # 2. Inject content (Directly accessing internal structure for realism)
            #    (Resolving path again to find the node we just touched)
            parent, name, node = self.vfs._resolve_node(filename)
            if node:
                # Try to decode if text, otherwise keep raw repr or placeholders
                try:
                    node["content"] = received_data.decode('utf-8')
                except:
                    node["content"] = f"[Binary data: {len(received_data)} bytes]"
                # Update size
                node["size"] = len(received_data)

            self.send_ctrl("226 Transfer complete.")
            log_event("FTP", self.ip, f"Uploaded: {filename} ({len(received_data)} bytes)", "file_upload")
        except Exception as e:
            self.send_ctrl(f"451 Error writing file: {e}")
        finally:
            self.close_pasv()

    def handle_pasv(self):
        """
        Enter Passive Mode: Bind a random port and tell the client.
        """
        try:
            self.pasv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.pasv_socket.bind(('0.0.0.0', 0)) # Bind to random high port
            self.pasv_socket.listen(1)
            
            # Get the port we were assigned
            port = self.pasv_socket.getsockname()[1]
            
            # Get our local IP (the one the client connected to)
            # This handles cases where we are behind NAT or in Docker 
            # better than hardcoding public IP (usually).
            host_ip = self.conn.getsockname()[0] 
            
            # Format IP for PASV response: 127,0,0,1
            ip_split = host_ip.replace('.', ',')
            
            # Format Port: p1 * 256 + p2
            p1 = port // 256
            p2 = port % 256
            
            self.send_ctrl(f"227 Entering Passive Mode ({ip_split},{p1},{p2}).")
        except Exception as e:
            log_event("FTP", self.ip, f"PASV Error: {e}", "error")
            self.send_ctrl("500 PASV failed.")

    def run(self):
        log_event("FTP", self.ip, "Connection established")
        try:
            self.send_ctrl("220 (vsFTPd 3.0.3)")
            
            while self.running:
                data = self.conn.recv(1024).decode('utf-8', errors='ignore').strip()
                if not data: break

                log_event("FTP", self.ip, data, event_type="payload")
                
                parts = data.split(" ", 1)
                cmd = parts[0].upper()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "USER":
                    self.send_ctrl("331 Please specify the password.")
                
                elif cmd == "PASS":
                    self.send_ctrl("230 Login successful.")
                    self.authenticated = True

                elif cmd == "QUIT":
                    self.send_ctrl("221 Goodbye.")
                    break

                elif not self.authenticated:
                    self.send_ctrl("530 Please login with USER and PASS.")
                    continue

                elif cmd == "PWD":
                    cwd = "/" + "/".join(self.vfs.cwd)
                    self.send_ctrl(f'257 "{cwd}"')

                elif cmd == "CWD":
                    # Use VirtualFS CD logic
                    if arg == "/": 
                        self.vfs.cwd = ["home", self.vfs.user] # Reset
                        self.send_ctrl("250 Directory successfully changed.")
                    else:
                        output = self.vfs.do_cd([arg])
                        if "No such file" in output or "Not a directory" in output:
                            self.send_ctrl("550 Failed to change directory.")
                        else:
                            self.send_ctrl("250 Directory successfully changed.")

                elif cmd == "TYPE":
                    if arg.upper() == "A":
                        self.mode = "A"
                        self.send_ctrl("200 Switching to ASCII mode.")
                    elif arg.upper() == "I":
                        self.mode = "I"
                        self.send_ctrl("200 Switching to Binary mode.")
                    else:
                        self.send_ctrl("500 Unrecognised TYPE command.")

                elif cmd == "PASV":
                    self.handle_pasv()

                elif cmd in ["LIST", "NLST"]:
                    self.handle_list(arg)

                elif cmd == "RETR":
                    self.handle_retr(arg)

                elif cmd == "STOR":
                    self.handle_stor(arg)

                elif cmd == "MKD":
                    err = self.vfs.do_mkdir([arg])
                    if "cannot" in err:
                        self.send_ctrl(f"550 {err}")
                    else:
                        self.send_ctrl(f'257 "{arg}" created')

                elif cmd in ["DELE", "RMD"]:
                    err = self.vfs.do_rm([arg])
                    if "cannot" in err:
                        self.send_ctrl(f"550 {err}")
                    else:
                        self.send_ctrl("250 Delete operation successful.")

                elif cmd == "SYST":
                    self.send_ctrl("215 UNIX Type: L8")
                
                elif cmd == "FEAT":
                    self.send_ctrl("211-Features:\r\n PASV\r\n TYPE\r\n SIZE\r\n211 End")

                else:
                    self.send_ctrl("500 Unknown command.")

        except Exception as e:
            log_event("FTP", self.ip, f"Crash: {str(e)}", "error")
        finally:
            self.close_pasv()
            try: self.conn.close()
            except: pass

def start_ftp_server(port=21):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(("0.0.0.0", port))
        server.listen(100)
        print(f"[-] FTP Honeypot listening on port {port} (Mode: Passive-Enabled)...")
        while True:
            client, addr = server.accept()
            # Spawn a new thread class for the session
            session = FTPSession(client, addr)
            session.daemon = True
            session.start()
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
        # We will hold the connection open for a few seconds to simulate processing
        # ("Tarpit" behavior) which annoys scanners/bruteforcers.
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
# # ===================== SMB HONEYPOT =====================

# def setup_smb_honey_dir():
#     """
#     Creates a temporary real directory to act as the SMB Share.
#     Impacket requires a real path, so we populate this to look interesting.
#     """
#     # Create a temp directory
#     honey_dir = tempfile.mkdtemp(prefix="corp_share_")
    
#     # Create some decoy files inside to entice attackers
#     # These match the 'theme' of your honeypot
#     with open(os.path.join(honey_dir, 'Confidential.txt'), 'w') as f:
#         f.write("INTERNAL USE ONLY - DO NOT DISTRIBUTE")
    
#     with open(os.path.join(honey_dir, 'passwords.txt'), 'w') as f:
#         f.write("admin:Summer2024!\nroot:P@ssw0rd123")
        
#     with open(os.path.join(honey_dir, 'HR_Report_2024.pdf'), 'w') as f:
#         f.write("%PDF-1.4 ... (Corrupted file)")
        
#     return honey_dir

# def start_smb_server(port=445):
#     """
#     Starts a realistic SMB Server using Impacket.
#     This handles full NTLM authentication and File Sharing protocols.
#     """
#     try:
#         # 1. Setup the Honey Directory (Real files on disk)
#         honey_dir = setup_smb_honey_dir()
#         print(f"[-] SMB Honeypot Share created at: {honey_dir}")

#         # 2. Configure Impacket SMB Server
#         # 'listenAddress' is 0.0.0.0, 'listenPort' is customizable
#         server = SimpleSMBServer(listenAddress="0.0.0.0", listenPort=port)
        
#         # 3. Register a Share
#         # Attackers will see a share named 'DOCUMENTS'
#         server.addShare("DOCUMENTS", honey_dir, "Corporate Documents Share")
        
#         # 4. Security Settings (Realistic Configuration)
#         server.setSMB2Support(True)  # Enable modern SMB2
#         server.setSMBChallenge('')   # Random challenge for NTLM capture
        
#         # 5. Logging Hook
#         # Impacket uses the standard Python logging module. 
#         # We attach our existing 'fs_handler' to Impacket's logger so events go to ftp_smb_logs.log
#         impacket_logger = logging.getLogger('impacket')
#         impacket_logger.setLevel(logging.INFO)
#         impacket_logger.addHandler(fs_handler)
        
#         # Manually log start event
#         log_event("SMB", "0.0.0.0", f"Server Started on port {port} (Share: DOCUMENTS)", "service_start")
#         print(f"[-] SMB Honeypot listening on port {port} (Impacket Engine)...")

#         # 6. Start the Server (Blocking call)
#         server.start()
        
#     except Exception as e:
#         # Clean up temp dir if it crashes immediately
#         if 'honey_dir' in locals():
#             shutil.rmtree(honey_dir, ignore_errors=True)
            
#         print(f"[!] SMB Server Failed: {e}")
#         log_event("SMB", "LOCAL", f"Startup Error: {e}", "error")

#         # Fallback: If port is Permission Denied (common on 445 without root), allow script to continue
#         if "Permission denied" in str(e):
#             print("[!] HINT: You must run with 'sudo' to bind port 445.")

# ===================== RUNNER =====================

def run_ftp_smb_VenomPot(ftp_port=21, smb_port=445):
    t_ftp = threading.Thread(target=start_ftp_server, args=(ftp_port,))
    t_ftp.daemon = True
    t_ftp.start()

    t_smb = threading.Thread(target=start_smb_server, args=(smb_port,))
    t_smb.daemon = True
    t_smb.start()

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass

if __name__ == "__main__":
    run_ftp_smb_VenomPot()