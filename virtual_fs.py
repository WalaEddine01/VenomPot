import json
import os
import copy
import time
import random
from datetime import datetime

# Default configuration if JSON is missing
DEFAULT_FS = {
    "name": "", "type": "dir", "perm": "drwxr-xr-x", "user": "root", "group": "root",
    "size": 4096, "modified": "Jan 1 10:00", "children": {
        "home": {"type": "dir", "perm": "drwxr-xr-x", "user": "root", "group": "root", "size": 4096, "children": {
            "admin": {"type": "dir", "perm": "drwxr-x---", "user": "admin", "group": "admin", "size": 4096, "children": {}},
            "user": {"type": "dir", "perm": "drwxr-x---", "user": "user", "group": "user", "size": 4096, "children": {}}
        }},
        "etc": {"type": "dir", "perm": "drwxr-xr-x", "user": "root", "group": "root", "size": 4096, "children": {
            "hostname": {"type": "file", "perm": "-rw-r--r--", "user": "root", "group": "root", "size": 12, "content": "ubuntu-server"}
        }},
        "bin": {"type": "dir", "perm": "drwxr-xr-x", "user": "root", "group": "root", "size": 4096, "children": {}}
    }
}

class VirtualFS:
    def __init__(self, user="user", json_file="FileSystemUbuntu2204.json"):
        self.json_file = json_file
        self.user = user
        self.hostname = "ubuntu-server"
        self.start_time = datetime.now()
        
        # Load FS
        self.fs = self._load_fs()
        
        # Ensure the user's home directory actually exists in the dict
        if "home" in self.fs["children"]:
            if self.user not in self.fs["children"]["home"]["children"]:
                # Dynamically create the home folder if missing
                self.fs["children"]["home"]["children"][self.user] = {
                    "type": "dir", "perm": "drwxr-x---", "user": self.user, 
                    "group": self.user, "size": 4096, 
                    "modified": "Jan 1 10:00", "children": {}
                }
        
        self.cwd = ["home", self.user]
        self.old_pwd = self.cwd.copy()
        
        # State
        self.cwd = ["home", self.user] # Current Working Directory (list of parts)
        self.old_pwd = self.cwd.copy() # For 'cd -'
        
        # Mock Package Database
        self.installed_packages = {"nano", "vim", "git", "curl", "wget", "python3"}

    def _load_fs(self):
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[!] JSON Load Error: {e}")
        return copy.deepcopy(DEFAULT_FS)

    def _save_fs(self):
        """Persist changes to the real JSON file immediately."""
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(self.fs, f, indent=2)
        except Exception as e:
            print(f"[!] JSON Save Error: {e}")

    # ================= PATH RESOLUTION =================

    def get_pwd_str(self):
        if not self.cwd: return "/"
        return "/" + "/".join(self.cwd)

    def get_prompt(self):
        """
        Returns the clean prompt string. 
        Format: user@hostname:~/current/dir$ 
        """
        path_str = self.get_pwd_str()
        home = f"/home/{self.user}"
        if path_str.startswith(home):
            path_str = path_str.replace(home, "~", 1)
        
        # Only return the suffix part so you can format it in the main loop
        return f"{self.user}@{self.hostname}:{path_str}$ "

    def _resolve_node(self, path_str, parent_only=False):
        """
        Navigates the dictionary tree.
        path_str: The path to resolve.
        parent_only: If True, returns the parent node of the target.
        Returns: (parent_node, target_name, target_node)
        """
        if path_str == "/" and not parent_only:
            return None, "", self.fs

        # 1. Determine start point
        if path_str.startswith("/"):
            parts = [p for p in path_str.split("/") if p]
            cursor_path = [] # Root
        elif path_str.startswith("~"):
            parts = [p for p in path_str.replace("~", f"home/{self.user}").split("/") if p]
            cursor_path = []
        else:
            parts = [p for p in path_str.split("/") if p]
            cursor_path = self.cwd.copy()

        # 2. Resolve . and ..
        final_stack = []
        for p in cursor_path + parts:
            if p == ".": continue
            elif p == "..":
                if final_stack: final_stack.pop()
            else:
                final_stack.append(p)

        # 3. Handle parent_only request (pop the last item)
        target_name = ""
        if parent_only:
            if not final_stack: return None, "", self.fs # Root has no parent we can edit easily here
            target_name = final_stack.pop()
        
        # 4. Traverse
        cursor = self.fs
        parent = None
        
        for part in final_stack:
            if "children" in cursor and part in cursor["children"]:
                parent = cursor
                cursor = cursor["children"][part]
            else:
                return None, None, None # Invalid path

        if parent_only:
            return cursor, target_name, cursor.get("children", {}).get(target_name)
        
        # Navigate one last step if we are looking for a child of what we resolved
        return parent, final_stack[-1] if final_stack else "", cursor

    # ================= COMMAND DISPATCHER =================

    def execute_command(self, cmd_line):
        if not cmd_line or not cmd_line.strip(): return ""
        
        # Handle simple piping/redirection placeholders (stub logic)
        if ">" in cmd_line:
            cmd_line = cmd_line.split(">")[0].strip()
        
        parts = cmd_line.strip().split()
        cmd = parts[0]
        args = parts[1:]
        
        # --- File & Dir Management ---
        if cmd == "ls": return self.do_ls(args)
        if cmd == "cd": return self.do_cd(args)
        if cmd == "pwd": return self.get_pwd_str()
        if cmd == "mkdir": return self.do_mkdir(args)
        if cmd == "rmdir": return self.do_rmdir(args)
        if cmd == "rm": return self.do_rm(args)
        if cmd == "cp": return self.do_cp(args)
        if cmd == "mv": return self.do_mv(args)
        if cmd == "touch": return self.do_touch(args)
        
        # --- Viewing & Editing ---
        if cmd == "cat": return self.do_cat(args)
        if cmd in ["head", "tail"]: return self.do_head_tail(cmd, args)
        if cmd in ["less", "more"]: return self.do_cat(args) # Simpler for now
        if cmd in ["nano", "vim", "vi"]: return f"\n[!] Opened {args[0] if args else 'file'}. (Editor simulation mode: Press Ctrl+X to exit)"

        # --- Permissions & Groups ---
        if cmd == "chmod": return self.do_chmod(args)
        if cmd == "chown": return "" # Fake success
        if cmd == "chgrp": return "" # Fake success
        
        # --- System Info ---
        if cmd == "uname": return "Linux ubuntu-server 5.15.0-91-generic x86_64 GNU/Linux" if "-a" in args else "Linux"
        if cmd == "hostname": return self.hostname
        if cmd == "uptime": return self.do_uptime()
        if cmd == "whoami": return self.user
        if cmd == "id": return f"uid=1000({self.user}) gid=1000({self.user}) groups=1000({self.user}),4(adm),24(cdrom),27(sudo)"
        if cmd == "groups": return f"{self.user} adm cdrom sudo dip plugdev lxd"
        
        # --- Disk & Hardware ---
        if cmd == "df": return "Filesystem     1K-blocks    Used Available Use% Mounted on\n/dev/sda1       30646684 8456122  22190562  28% /"
        if cmd == "du": return "4\t./.bashrc\n4\t./.profile\n12\t."
        if cmd == "free": return "              total        used        free      shared  buff/cache   available\nMem:        8104640     1254320     4501230       12040     2349090     6540230"
        if cmd == "lscpu": return "Architecture:            x86_64\n  CPU op-mode(s):        32-bit, 64-bit\n  Address sizes:         39 bits physical, 48 bits virtual\n  Byte Order:            Little Endian\nCPU(s):                  2"
        
        # --- Networking (Fake) ---
        if cmd in ["ip", "ifconfig"]: return self.fake_network_info()
        if cmd == "ping": return f"PING {args[0] if args else '8.8.8.8'} ({args[0] if args else '8.8.8.8'}) 56(84) bytes of data.\n64 bytes from {args[0] if args else '8.8.8.8'}: icmp_seq=1 ttl=117 time=12.1 ms\n64 bytes from {args[0] if args else '8.8.8.8'}: icmp_seq=2 ttl=117 time=12.3 ms"
        if cmd in ["netstat", "ss"]: return "tcp  0  0 0.0.0.0:22  0.0.0.0:* LISTEN"
        
        # --- Package Management (APT) ---
        if cmd in ["apt", "apt-get"]: return self.do_apt(args)
        
        # --- System Control ---
        if cmd in ["shutdown", "reboot", "init"]: return f"Failed to talk to init daemon."
        if cmd in ["systemctl", "service"]: return "Failed to connect to bus: No such file or directory"
        
        # --- Shell/Env ---
        if cmd == "echo": return " ".join(args)
        if cmd == "export": return "" # Fake success
        if cmd == "env": return f"USER={self.user}\nHOME=/home/{self.user}\nSHELL=/bin/bash\nTERM=xterm-256color"
        
        # --- Fallback ---
        return f"{cmd}: command not found"

    # ================= IMPLEMENTATIONS =================

    def do_ls(self, args):
        show_hidden = "-a" in args
        show_details = "-l" in args or "ll" in args
        
        # Parse path from args (ignore flags)
        target = "."
        for arg in args:
            if not arg.startswith("-"): target = arg; break
            
        _, _, node = self._resolve_node(target)
        if not node: return f"ls: cannot access '{target}': No such file or directory"
        
        if node["type"] == "file": return target

        children = node.get("children", {})
        items = []
        for name in children.keys():
            if not show_hidden and name.startswith("."): continue
            items.append(name)
        
        # Add . and .. for -a
        if show_hidden:
            items = [".", ".."] + items
            
        if show_details:
            lines = [f"total {len(items) * 4}"]
            for name in items:
                if name in [".", ".."]:
                    # Fake stats for . and ..
                    lines.append(f"drwxr-xr-x 2 {self.user} {self.user} 4096 Jan 1 10:00 {name}")
                    continue
                
                data = children[name]
                line = f"{data['perm']} 1 {data['user']} {data['group']} {str(data['size']).rjust(5)} {data['modified']} {name}"
                lines.append(line)
            return "\r\n".join(lines)
        
        return "  ".join(items)

    def do_cd(self, args):
        target = args[0] if args else "~"
        
        if target == "-":
            target_path = self.old_pwd
            print_path = True
        else:
            print_path = False
            # Resolve target
            if target == "~": 
                target_path = ["home", self.user]
            elif target == ".":
                return ""
            elif target == "..":
                target_path = self.cwd[:-1] if self.cwd else []
            else:
                # Resolve complex path
                parent, name, node = self._resolve_node(target)
                if not node: return f"-bash: cd: {target}: No such file or directory"
                if node["type"] != "dir": return f"-bash: cd: {target}: Not a directory"
                
                # Re-calculate absolute stack for cwd
                # This is a simplification; for robust relative paths we'd need better stack logic
                # But since resolve_node traverses, we can cheat by just setting CWD if it was absolute
                # For this snippet, let's just assume we found it.
                # A proper implementation requires tracking the stack in resolve_node.
                
                # Hacky fix for relative paths updates:
                if target.startswith("/"):
                    target_path = [p for p in target.split("/") if p]
                else:
                    new_stack = self.cwd.copy()
                    for p in target.split("/"):
                        if p == "..": 
                            if new_stack: new_stack.pop()
                        elif p != ".": 
                            new_stack.append(p)
                    target_path = new_stack

        self.old_pwd = self.cwd
        self.cwd = target_path
        return "/" + "/".join(self.cwd) if print_path else ""

    def do_mkdir(self, args):
        if not args: return "mkdir: missing operand"
        path = args[-1] # Assume last arg is path, ignore flags like -p for now
        
        # Get parent
        parent, name, node = self._resolve_node(path, parent_only=True)
        if not parent: return f"mkdir: cannot create directory '{path}': No such file or directory"
        
        if name in parent["children"]:
            return f"mkdir: cannot create directory '{path}': File exists"
            
        parent["children"][name] = {
            "type": "dir", "perm": "drwxr-xr-x", "user": self.user, "group": self.user,
            "size": 4096, "modified": datetime.now().strftime("%b %d %H:%M"), "children": {}
        }
        self._save_fs()
        return ""

    def do_rm(self, args):
        recursive = "-r" in args or "-rf" in args
        targets = [a for a in args if not a.startswith("-")]
        if not targets: return "rm: missing operand"
        
        output = []
        for path in targets:
            parent, name, node = self._resolve_node(path, parent_only=True)
            if not parent or name not in parent["children"]:
                output.append(f"rm: cannot remove '{path}': No such file or directory")
                continue
            
            node_to_del = parent["children"][name]
            if node_to_del["type"] == "dir" and not recursive:
                output.append(f"rm: cannot remove '{path}': Is a directory")
                continue
            
            del parent["children"][name]
            self._save_fs()
            
        return "\n".join(output)

    def do_touch(self, args):
        if not args: return "touch: missing file operand"
        path = args[0]
        
        parent, name, node = self._resolve_node(path, parent_only=True)
        if not parent: return f"touch: cannot touch '{path}': No such file or directory"
        
        if name in parent["children"]:
            # Update timestamp
            parent["children"][name]["modified"] = datetime.now().strftime("%b %d %H:%M")
        else:
            parent["children"][name] = {
                "type": "file", "perm": "-rw-r--r--", "user": self.user, "group": self.user,
                "size": 0, "modified": datetime.now().strftime("%b %d %H:%M"), "content": ""
            }
        self._save_fs()
        return ""

    def do_cat(self, args):
        if not args: return ""
        path = args[0]
        _, _, node = self._resolve_node(path)
        if not node: return f"cat: {path}: No such file or directory"
        if node["type"] == "dir": return f"cat: {path}: Is a directory"
        return node.get("content", "")

    def do_apt(self, args):
        if "update" in args:
            return "Hit:1 http://archive.ubuntu.com/ubuntu jammy InRelease\nHit:2 http://security.ubuntu.com/ubuntu jammy-security InRelease\nReading package lists... Done"
        if "install" in args:
            pkgs = [a for a in args if a not in ["install", "-y"]]
            if not pkgs: return "apt: missing package name"
            time.sleep(1) # Fake delay
            self.installed_packages.update(pkgs)
            return f"Reading package lists... Done\nBuilding dependency tree... Done\nThe following NEW packages will be installed:\n  {' '.join(pkgs)}\n0 upgraded, {len(pkgs)} newly installed, 0 to remove.\nSetting up {pkgs[0]} (1.0.0)... Done."
        return ""

    def do_chmod(self, args):
        if len(args) < 2: return "chmod: missing operand"
        mode = args[0]
        path = args[1]
        
        _, _, node = self._resolve_node(path)
        if not node: return f"chmod: cannot access '{path}': No such file or directory"
        
        # Fake permission change (simple)
        if mode == "+x":
            node["perm"] = node["perm"].replace("-", "x")
        # In a real impl, you'd parse 777 or u+x logic here
        self._save_fs()
        return ""
    
    def fake_network_info(self):
        return """eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.1.34  netmask 255.255.255.0  broadcast 192.168.1.255
        ether 08:00:27:1a:2b:3c  txqueuelen 1000  (Ethernet)
        RX packets 1234  bytes 987654 (987.6 KB)
        TX packets 567   bytes 123456 (123.4 KB)"""

    def do_uptime(self):
        delta = datetime.now() - self.start_time
        return f" {datetime.now().strftime('%H:%M:%S')} up {str(delta).split('.')[0]},  1 user,  load average: 0.00, 0.01, 0.05"
        
    def do_head_tail(self, cmd, args):
        if not args: return ""
        content = self.do_cat([args[0]])
        if "No such file" in content: return content
        lines = content.split('\n')
        if cmd == "head": return "\n".join(lines[:10])
        return "\n".join(lines[-10:])

    def do_cp(self, args):
        if len(args) < 2: return "cp: missing file operand"
        src, dest = args[0], args[1]
        
        # Read src
        parent_src, name_src, node_src = self._resolve_node(src, parent_only=True)
        if not node_src or name_src not in parent_src["children"]:
            return f"cp: cannot stat '{src}': No such file"
            
        # Write dest
        parent_dst, name_dst, node_dst = self._resolve_node(dest, parent_only=True)
        if not parent_dst: return f"cp: cannot create regular file '{dest}': No such file or directory"
        
        # Actual copy in memory
        parent_dst["children"][name_dst] = copy.deepcopy(parent_src["children"][name_src])
        self._save_fs()
        return ""

    def do_mv(self, args):
        if len(args) < 2: return "mv: missing file operand"
        src, dest = args[0], args[1]
        
        res = self.do_cp([src, dest])
        if "cannot" in res: return res
        self.do_rm([src]) # CP then RM = MV
        self._save_fs()
        return ""
    
    def do_rmdir(self, args):
        if not args: return "rmdir: missing operand"
        path = args[0]
        parent, name, node = self._resolve_node(path, parent_only=True)
        if not node or name not in parent["children"]:
            return f"rmdir: failed to remove '{path}': No such file or directory"
        
        target = parent["children"][name]
        if target["type"] != "dir": return f"rmdir: failed to remove '{path}': Not a directory"
        if target["children"]: return f"rmdir: failed to remove '{path}': Directory not empty"
        
        del parent["children"][name]
        self._save_fs()
        return ""