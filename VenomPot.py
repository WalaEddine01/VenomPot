#!/bin/env python3
"""
This module defines the main module for the VenomPot.
"""
# Librariesimport argparse
from web_VenomPot import *
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--address', type=str, required=True)
    parser.add_argument('-p', '--port', type=int, required=True)
    parser.add_argument('-u', '--username', type=str)
    parser.add_argument('-w', '--password', type=str)
    parser.add_argument('-s', '--ssh', action="store_true")
    parser.add_argument('-wh', '--http', action="store_true")
    parser.add_argument('-t', '--tarpit', action="store_true")

    args = parser.parse_args()

    if not args.ssh and not args.http:
        print("[!] You must choose at least one service: SSH (-s) or HTTP (-wh)")
        exit(1)

    try:
        if args.http:
            print("[-] Running HTTP WordPress Honeypot...")

            if not args.username:
                args.username = "admin"
                print("[-] Default username: admin")

            if not args.password:
                args.password = "admin"
                print("[-] Default password: admin")

            print(f"Port: {args.port} Username: {args.username}")
            run_web_VenomPot(args.port, args.username, args.password)

    except KeyboardInterrupt:
        print("\nProgram exited.")

