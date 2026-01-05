import json
import copy
from datetime import datetime

# ===================== BASE FILESYSTEM (UBUNTU 22.04) =====================
# This mimics a standard Ubuntu tree.
BASE_FS = {
    "name": "",
    "type": "dir",
    "perm": "drwxr-xr-x",
    "user": "root",
    "group": "root",
    "size": 4096,
    "modified": "Jan 1 10:00",
    "children": {
        "bin": {"type": "dir", "perm": "drwxr-xr-x", "user": "root", "group": "root", "size": 4096, "modified": "Jan 1 10:00", "children": {
            "bash": {"type": "file", "perm": "-rwxr-xr-x", "user": "root", "group": "root", "size": 1234000, "modified": "Jan 1 10:00", "content": ""},
            "ls": {"type": "file", "perm": "-rwxr-xr-x", "user": "root", "group": "root", "size": 140000, "modified": "Jan 1 10:00", "content": ""},
        }},
        "etc": {"type": "dir", "perm": "drwxr-xr-x", "user": "root", "group": "root", "size": 4096, "modified": "Jan 1 10:00", "children": {
            "passwd": {"type": "file", "perm": "-rw-r--r--", "user": "root", "group": "root", "size": 1500, "modified": "Jan 1 10:00", "content": "root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000:user:/home/user:/bin/bash"},
            "shadow": {"type": "file", "perm": "-rw-r-----", "user": "root", "group": "shadow", "size": 1000, "modified": "Jan 1 10:00", "content": "PERMISSION DENIED"},
            "hostname": {"type": "file", "perm": "-rw-r--r--", "user": "root", "group": "root", "size": 12, "modified": "Jan 1 10:00", "content": "ubuntu-server"},
        }},
        "home": {"type": "dir", "perm": "drwxr-xr-x", "user": "root", "group": "root", "size": 4096, "modified": "Jan 1 10:00", "children": {
            "user": {"type": "dir", "perm": "drwxr-x---", "user": "user", "group": "user", "size": 4096, "modified": "Jan 1 12:00", "children": {
                "secrets.txt": {"type": "file", "perm": "-rw-------", "user": "user", "group": "user", "size": 52, "modified": "Jan 2 14:20", "content": "CONFIDENTIAL DATA\nApiKey: 8f9s89f89s89f8"},
                "notes.md": {"type": "file", "perm": "-rw-r--r--", "user": "user", "group": "user", "size": 102, "modified": "Jan 2 15:00", "content": "# TODO\n1. Backup server\n2. Update firewall"},
            }}
        }},
        "var": {"type": "dir", "perm": "drwxr-xr-x", "user": "root", "group": "root", "size": 4096, "modified": "Jan 1 10:00", "children": {
            "www": {"type": "dir", "perm": "drwxr-xr-x", "user": "root", "group": "root", "size": 4096, "modified": "Jan 1 10:00", "children": {
                "html": {"type": "dir", "perm": "drwxr-xr-x", "user": "root", "group": "root", "size": 4096, "modified": "Jan 1 10:00", "children": {
                    "index.html": {"type": "file", "perm": "-rw-r--r--", "user": "www-data", "group": "www-data", "size": 500, "modified": "Jan 1 10:00", "content": "<html>Hello World</html>"}
                }}
            }}
        }},
        "tmp": {"type": "dir", "perm": "drwxrwxrwt", "user": "root", "group": "root", "size": 4096, "modified": "Jan 1 10:00", "children": {}}
    }
}

class VirtualFS:
    def __init__(self, user="user"):
        # Create a completely independent copy of the FS for this session
        self.fs = copy.deepcopy(BASE_FS)
        self.user = user
        # Start in home directory
        self.cwd = ["home", "user"] 

    def get_pwd(self):
        return "/" + "/".join(self.cwd)

    def _resolve_node(self, path_str):
        """
        Navigates the JSON tree to find a specific node.
        Returns (parent_node, target_node_name, target_node)
        """
        parts = []
        if path_str == "/" or path_str == "":
            parts = []
            current_path = []
        elif path_str.startswith("/"):
            parts = [p for p in path_str.split("/") if p]
            current_path = []
        else:
            parts = [p for p in path_str.split("/") if p]
            current_path = self.cwd.copy()

        # Navigate logic
        for part in parts:
            if part == ".":
                continue
            elif part == "..":
                if current_path:
                    current_path.pop()
            else:
                current_path.append(part)

        # Traverse dict
        cursor = self.fs
        parent = None
        target_name = ""
        
        # Root case
        if not current_path:
            return None, "", self.fs

        for idx, part in enumerate(current_path):
            if "children" in cursor and part in cursor["children"]:
                parent = cursor
                target_name = part
                cursor = cursor["children"][part]
            else:
                return None, None, None # Not found
        
        return parent, target_name, cursor

    def cd(self, path):
        _, _, node = self._resolve_node(path)
        if node and node["type"] == "dir":
            # Re-calculate absolute path for storage
            if path.startswith("/"):
                temp_cwd = []
            else:
                temp_cwd = self.cwd.copy()
            
            for part in path.split("/"):
                if not part or part == ".": continue
                if part == "..": 
                    if temp_cwd: temp_cwd.pop()
                else: temp_cwd.append(part)
            
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

        output = []
        # Basic LS (names only) - logic can be extended for -la
        for name, data in node["children"].items():
            output.append(name)
        return "  ".join(output)

    def ls_l(self, path="."):
        # Simulate 'ls -l'
        _, _, node = self._resolve_node(path)
        if not node:
            return f"ls: cannot access '{path}': No such file or directory"

        if node["type"] == "file":
             return f"{node['perm']} 1 {node['user']} {node['group']} {node['size']} {node['modified']} {path}"

        lines = [f"total {len(node['children']) * 4}"]
        for name, data in node["children"].items():
            line = f"{data['perm']} 1 {data['user']} {data['group']} {str(data['size']).rjust(5)} {data['modified']} {name}"
            lines.append(line)
        return "\r\n".join(lines)

    def mkdir(self, path):
        # Simplistic mkdir: assumes parent exists
        if "/" in path.rstrip("/"):
            # logic for deep paths omitted for brevity, handling local dir only
            parent_path, new_dir = path.rsplit("/", 1)
            _, _, parent = self._resolve_node(parent_path)
        else:
            parent_path = "."
            _, _, parent = self._resolve_node(".")
            new_dir = path

        if parent and "children" in parent:
            if new_dir in parent["children"]:
                return f"mkdir: cannot create directory '{path}': File exists"
            
            parent["children"][new_dir] = {
                "type": "dir",
                "perm": "drwxr-xr-x",
                "user": self.user,
                "group": self.user,
                "size": 4096,
                "modified": datetime.now().strftime("%b %d %H:%M"),
                "children": {}
            }
            return ""
        return f"mkdir: cannot create directory '{path}': No such file or directory"

    def rm(self, path):
        parent, name, node = self._resolve_node(path)
        if parent and node:
            if node["type"] == "dir":
                return f"rm: cannot remove '{path}': Is a directory"
            del parent["children"][name]
            return ""
        return f"rm: cannot remove '{path}': No such file or directory"

    def touch(self, path):
        # Creates an empty file
        if "/" in path:
            return "touch: cannot touch complex paths in this beta"
        
        _, _, cwd_node = self._resolve_node(".")
        if path in cwd_node["children"]:
            # Update time
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

    def cat(self, path):
        _, _, node = self._resolve_node(path)
        if not node:
            return f"cat: {path}: No such file or directory"
        if node["type"] == "dir":
            return f"cat: {path}: Is a directory"
        return node.get("content", "")