#!/bin/env python3
"""
This module defines the main module for the VenomPot.
"""
import argparse
import threading
from web_VenomPot import run_web_VenomPot
from smb_ftp_VenomPot import run_ftp_smb_VenomPot 
# Note: Assuming you might import the SSH pot here too if it was integrated properly
# from pot import VenomPot as run_ssh_VenomPot 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VenomPot: Multi-protocol Honeypot")
    parser.add_argument('-a', '--address', type=str, default="0.0.0.0")
    parser.add_argument('-p', '--port', type=int, default=8080, help="Port for HTTP")
    parser.add_argument('-u', '--username', type=str, default="admin")
    parser.add_argument('-w', '--password', type=str, default="admin")
    
    # Flags for services
    parser.add_argument('-s', '--ssh', action="store_true", help="Enable SSH Honeypot")
    parser.add_argument('-wh', '--http', action="store_true", help="Enable HTTP Honeypot")
    parser.add_argument('-fs', '--ftpsmb', action="store_true", help="Enable FTP and SMB Honeypots")

    args = parser.parse_args()

    if not any([args.ssh, args.http, args.ftpsmb]):
        print("[!] You must choose at least one service: -s, -wh, or -fs")
        exit(1)

    threads = []

    try:
        # Start HTTP
        if args.http:
            print("[-] Starting HTTP WordPress Honeypot...")
            t_http = threading.Thread(target=run_web_VenomPot, args=(args.port, args.username, args.password))
            t_http.daemon = True
            t_http.start()
            threads.append(t_http)

        # Start FTP/SMB
        if args.ftpsmb:
            print("[-] Starting FTP & SMB Honeypots (Root privileges usually required for ports 21/4445)...")
            # We run this in a separate thread so it doesn't block
            t_fs = threading.Thread(target=run_ftp_smb_VenomPot, args=(21, 4445))
            t_fs.daemon = True
            t_fs.start()
            threads.append(t_fs)

        # Start SSH (Based on your provided pot.py logic)
        if args.ssh:
             # Ideally you should wrap the logic in pot.py into a callable function like run_ssh_VenomPot()
             # For now, we assume you might run it separately or adapt pot.py similarly.
             print("[-] SSH flag detected (Ensure pot.py is integrated or run separately)")

        # Keep main alive
        while True:
            pass

    except KeyboardInterrupt:
        print("\nProgram exited.")