import json
import copy
import os
import random
from datetime import datetime

class VirtualFS:
    def __init__(self, user="user", json_file="FileSystemUbuntu2204.json"):
        # Load the base filesystem from the JSON file
        try:
            # Assumes the JSON file is in the same directory
            base_path = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_path, json_file)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                self.base_fs = json.load(f)
        except FileNotFoundError:
            print(f"[!] Warning: {json_file} not found. Using empty root.")
            self.base_fs = {"name": "", "type": "dir", "children": {}}
        except Exception as e:
            print(f"[!] Error loading JSON: {e}")
            self.base_fs = {"name": "", "type": "dir", "children": {}}

        # Create a session-specific copy so one attacker doesn't affect another
        self.fs = copy.deepcopy(self.base_fs)
        self.user = user
        # Start in /home/user
        self.cwd = ["home", "user"]
        self.start_time = datetime.now()

    def get_pwd(self):
        return "/" + "/".join(self.cwd)

    def _resolve_node(self, path_str):
        """
        Navigates the internal dictionary tree.
        Returns: (parent_node, target_name, target_node)
        """
        if not path_str:
            return None, "", self.fs
            
        parts = []
        # Handle absolute vs relative paths
        if path_str.startswith("/"):
            parts = [p for p in path_str.split("/") if p]
            current_path = [] # Start at root
        else:
            parts = [p for p in path_str.split("/") if p]
            current_path = self.cwd.copy() # Start at CWD

        # Resolve ".." and "."
        final_path_stack = []
        for p in current_path + parts:
            if p == ".": 
                continue
            elif p == "..":
                if final_path_stack: final_path_stack.pop()
            else:
                final_path_stack.append(p)

        # Traverse the JSON dict
        cursor = self.fs
        parent = None
        target_name = ""
        
        # Root case
        if not final_path_stack:
            return None, "", self.fs

        for part in final_path_stack:
            if "children" in cursor and part in cursor["children"]:
                parent = cursor
                target_name = part
                cursor = cursor["children"][part]
            else:
                return None, None, None # Not found
        
        return parent, target_name, cursor

    # ================= COMMAND HANDLER =================

    def execute_command(self, cmd_line):
        """
        Central dispatcher for all shell commands.
        """
        if not cmd_line or not cmd_line.strip():
            return ""

        parts = cmd_line.strip().split()
        cmd = parts[0]
        args = parts[1:]
        arg1 = args[0] if len(args) > 0 else ""

        # --- Filesystem Operations ---
        if cmd == "ls": 
            return self.ls(arg1 if arg1 else ".")
        if cmd == "cd": 
            return self.cd(arg1 if arg1 else "~")
        if cmd == "pwd": 
            return self.get_pwd()
        if cmd == "cat": 
            return self.cat(arg1)
        if cmd == "mkdir": 
            return self.mkdir(arg1)
        if cmd == "rm": 
            return self.rm(arg1)
        if cmd == "touch": 
            return self.touch(arg1)
        if cmd == "cp":
            return "cp: missing destination file operand after '" + arg1 + "'" if len(args) < 2 else "" # Stub
        if cmd == "mv":
            return "mv: missing destination file operand after '" + arg1 + "'" if len(args) < 2 else "" # Stub
        if cmd in ["head", "tail", "less", "grep"]:
            # Basic file read simulation for these tools
            content = self.cat(arg1)
            if "No such file" in content: return content
            lines = content.split('\n')
            if cmd == "head": return "\n".join(lines[:10])
            if cmd == "tail": return "\n".join(lines[-10:])
            return content # less/grep return full for now

        # --- System Identity ---
        if cmd == "whoami": return self.user
        if cmd == "id": return f"uid=1000({self.user}) gid=1000({self.user}) groups=1000({self.user}),27(sudo)"
        if cmd == "hostname": return "ubuntu-server"
        if cmd == "uname": 
            if "-a" in args: return "Linux ubuntu-server 5.15.0-91-generic #101-Ubuntu SMP x86_64 GNU/Linux"
            return "Linux"
        if cmd == "uptime":
             delta = datetime.now() - self.start_time
             return f" {datetime.now().strftime('%H:%M:%S')} up {str(delta).split('.')[0]},  1 user,  load average: 0.00, 0.01, 0.05"

        # --- Network Tools ---
        if cmd in ["ifconfig", "ip"]:
            return """eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.1.34  netmask 255.255.255.0  broadcast 192.168.1.255
        inet6 fe80::a00:27ff:fe4e:66a1  prefixlen 64  scopeid 0x20<link>
        ether 08:00:27:4e:66:a1  txqueuelen 1000  (Ethernet)
        RX packets 5623  bytes 4561230 (4.5 MB)
        TX packets 4120  bytes 321456 (321.4 KB)

lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        inet6 ::1  prefixlen 128  scopeid 0x10<host>"""
        
        if cmd in ["netstat", "ss"]:
            return """Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State      
tcp        0      0 0.0.0.0:22              0.0.0.0:* LISTEN     
tcp        0      0 127.0.0.53:53           0.0.0.0:* LISTEN     
udp        0      0 127.0.0.53:53           0.0.0.0:* """

        if cmd == "ping":
            target = arg1 if arg1 else "8.8.8.8"
            return f"PING {target} ({target}) 56(84) bytes of data.\n64 bytes from {target}: icmp_seq=1 ttl=118 time=14.2 ms\n64 bytes from {target}: icmp_seq=2 ttl=118 time=15.1 ms\n^C"

        if cmd == "route":
            return """Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
default         _gateway        0.0.0.0         UG    100    0        0 eth0
192.168.1.0     0.0.0.0         255.255.255.0   U     100    0        0 eth0"""

        # --- Process Management ---
        if cmd == "ps":
            return """    PID TTY          TIME CMD
   1422 pts/0    00:00:00 bash
   1455 pts/0    00:00:00 ps"""
        if cmd == "top":
            return "top - 15:45:22 up 2 days,  1 user,  load average: 0.00, 0.00, 0.00\nTasks:  94 total,   1 running,  93 sleeping"

        # --- Admin / Permissions ---
        if cmd == "sudo":
            return f"[sudo] password for {self.user}: "
        if cmd == "su":
            return "Password: "
        if cmd in ["service", "systemctl"]:
            return "Failed to connect to bus: No such file or directory"

        # --- Hack Tools / Scanners (Simulated Failures/Time wasters) ---
        if cmd in ["nmap", "masscan"]:
            return f"Starting Nmap 7.80 ( https://nmap.org ) at {datetime.now().strftime('%Y-%m-%d %H:%M')}\nNote: Host seems down. If it is really up, but blocking our ping probes, try -Pn\nNmap done: 1 IP address (0 hosts up) scanned in 3.02 seconds"
        
        if cmd in ["hydra", "medusa"]:
            return "[ERROR] Target does not support password authentication or connection refused."
        
        if cmd in ["sqlmap", "nikto", "dirb", "gobuster"]:
            return f"[!] {cmd.upper()}: Connection timed out to target URL."
        
        if cmd == "msfconsole":
             return """
     ,           ,
    /             \\
   ((__---,,,---__))
      (_) O O (_)_________
         \ _ /            |\\
          o_o \   M S F   | \\
               \   _____  |  *
                |||   WW|||
                |||     |||

[!] Database not connected.
[*] Starting the Metasploit Framework console...
[-] Failed to connect to the database: connection refused
"""

        if cmd in ["nc", "netcat"]:
            return "" # Netcat often hangs silently if no connection

        if cmd in ["python", "python3"]:
            return "Python 3.10.12 (main, Nov 20 2023, 15:14:05) [GCC 11.4.0] on linux\nType \"help\", \"copyright\", \"credits\" or \"license\" for more information.\n>>> quit()\n"

        if cmd == "which":
            # Check against our fake list of commands
            all_cmds = self.get_all_commands()
            if arg1 in all_cmds:
                if arg1 in ["ls", "cat", "cp", "mv", "rm", "mkdir"]: return f"/usr/bin/{arg1}"
                if arg1 in ["ifconfig", "route"]: return f"/usr/sbin/{arg1}"
                return f"/bin/{arg1}"
            return ""

        # --- Default for unknown ---
        if cmd in self.get_all_commands():
            # If it's in our known list but not handled specifically above,
            # return a generic "command missing" or empty to simulate installed but no output
            return ""
            
        return f"{cmd}: command not found"

    # ================= FILESYSTEM LOGIC =================

    def cd(self, path):
        if not path or path == "~":
            self.cwd = ["home", self.user]
            return ""
            
        _, _, node = self._resolve_node(path)
        if node and node["type"] == "dir":
            # Re-resolve path to update CWD cleanly
            if path.startswith("/"):
                new_parts = [p for p in path.split("/") if p]
                self.cwd = new_parts
            else:
                # Relative path logic
                temp_cwd = self.cwd.copy()
                parts = [p for p in path.split("/") if p]
                for p in parts:
                    if p == "..": 
                        if temp_cwd: temp_cwd.pop()
                    elif p != ".": 
                        temp_cwd.append(p)
                self.cwd = temp_cwd
            return ""
        elif node and node["type"] == "file":
            return f"-bash: cd: {path}: Not a directory"
        else:
            return f"-bash: cd: {path}: No such file or directory"

    def ls(self, path="."):
        _, _, node = self._resolve_node(path)
        if not node:
            return f"ls: cannot access '{path}': No such file or directory"
        
        if node["type"] == "file":
            return path

        # Directory listing
        children = node.get("children", {})
        # Simple column output simulation
        names = list(children.keys())
        return "  ".join(names)

    def ls_l(self, path="."):
        # Detailed listing (for 'll' or 'ls -l')
        _, _, node = self._resolve_node(path)
        if not node: return f"ls: cannot access '{path}': No such file or directory"

        if node["type"] == "file":
             return f"{node['perm']} 1 {node['user']} {node['group']} {node['size']} {node['modified']} {path}"

        lines = [f"total {len(node.get('children', {})) * 4}"]
        for name, data in node.get("children", {}).items():
            line = f"{data['perm']} 1 {data['user']} {data['group']} {str(data['size']).rjust(5)} {data['modified']} {name}"
            lines.append(line)
        return "\r\n".join(lines)

    def cat(self, path):
        if not path: return ""
        _, _, node = self._resolve_node(path)
        if not node:
            return f"cat: {path}: No such file or directory"
        if node["type"] == "dir":
            return f"cat: {path}: Is a directory"
        return node.get("content", "")

    def mkdir(self, path):
        if not path: return "mkdir: missing operand"
        if "/" in path: return "mkdir: cannot create directory (nested paths not supported in beta)"
        
        _, _, cwd_node = self._resolve_node(".")
        if path in cwd_node["children"]:
            return f"mkdir: cannot create directory '{path}': File exists"
        
        cwd_node["children"][path] = {
            "type": "dir",
            "perm": "drwxr-xr-x",
            "user": self.user,
            "group": self.user,
            "size": 4096,
            "modified": datetime.now().strftime("%b %d %H:%M"),
            "children": {}
        }
        return ""

    def rm(self, path):
        if not path: return "rm: missing operand"
        parent, name, node = self._resolve_node(path)
        if parent is None: return f"rm: cannot remove '{path}': No such file or directory"
        
        if node["type"] == "dir":
            return f"rm: cannot remove '{path}': Is a directory"
        
        del parent["children"][name]
        return ""

    def touch(self, path):
        if not path: return "touch: missing file operand"
        if "/" in path: return ""
        
        _, _, cwd_node = self._resolve_node(".")
        if path in cwd_node["children"]:
            cwd_node["children"][path]["modified"] = datetime.now().strftime("%b %d %H:%M")
        else:
            cwd_node["children"][path] = {
                "type": "file",
                "perm": "-rw-r--r--",
                "user": self.user,
                "group": self.user,
                "size": 0,
                "modified": datetime.now().strftime("%b %d %H:%M"),
                "content": ""
            }
        return ""

    def get_all_commands(self):
        # List of "fake" commands that shouldn't return "command not found"
        return [
            "whoami", "id", "hostname", "uname", "cat", "ls", "pwd", "find", "locate", 
            "which", "ps", "netstat", "ss", "w", "last", "lastlog", "history", "ifconfig", 
            "ip", "ping", "nmap", "nc", "telnet", "ssh", "curl", "wget", "dig", "nslookup", 
            "host", "arp", "route", "tcpdump", "wireshark", "tshark", "sudo", "su", 
            "crontab", "systemctl", "less", "head", "tail", "grep", "cp", "mv", "scp", 
            "rsync", "tar", "gzip", "base64", "dd", "xxd", "echo", "chmod", "chown", 
            "useradd", "usermod", "passwd", "ssh-keygen", "ssh-copy-id", "top", "kill", 
            "killall", "pkill", "service", "rm", "shred", "unset", "export", "touch", 
            "utmpdump", "john", "hashcat", "hydra", "md5sum", "sha256sum", "openssl", 
            "msfconsole", "gcc", "python", "perl", "bash", "sqlmap", "nikto", "dirb", 
            "gobuster", "arpspoof", "ettercap", "bettercap", "socat", "enum4linux", 
            "linpeas", "linenum", "lse", "nohup", "disown", "screen", "tmux"
        ]