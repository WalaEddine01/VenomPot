import os
import sys
import time
import random

# Ensure project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from logger import log_event

# Fake filesystem structure
FAKE_FS = {
    "/": ["bin", "boot", "dev", "etc", "home", "lib", "lib64", "media", "mnt", "opt", "proc", "root", "run", "sbin", "srv", "sys", "tmp", "usr", "var"],
    "/home": ["user"],
    "/home/user": ["Documents", "Downloads", "Pictures", "Music", "Videos", ".bashrc", ".profile", ".ssh", ".bash_history"],
    "/home/user/Documents": ["notes.txt", "work.pdf", "budget.xlsx"],
    "/home/user/Downloads": ["setup.sh", "archive.tar.gz"],
    "/home/user/.ssh": ["id_rsa", "id_rsa.pub", "known_hosts", "authorized_keys"],
    "/etc": ["passwd", "shadow", "hosts", "hostname", "resolv.conf", "ssh", "apache2", "nginx", "mysql", "crontab", "sudoers"],
    "/etc/ssh": ["sshd_config", "ssh_config", "ssh_host_rsa_key", "ssh_host_rsa_key.pub"],
    "/var": ["log", "www", "lib", "cache", "tmp"],
    "/var/log": ["syslog", "auth.log", "kern.log", "apache2", "mysql", "nginx"],
    "/var/www": ["html"],
    "/var/www/html": ["index.html", "info.php"],
    "/tmp": [".X0-lock", "systemd-private-abc123"],
    "/root": [".bashrc", ".profile", ".ssh"],
    "/usr": ["bin", "lib", "local", "share", "sbin"],
    "/usr/bin": ["python3", "perl", "ruby", "gcc", "make", "wget", "curl", "vim", "nano"],
}

# Fake file contents
FAKE_FILES = {
    "/etc/passwd": """root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
user:x:1000:1000:user:/home/user:/bin/bash
sshd:x:105:65534::/run/sshd:/usr/sbin/nologin
mysql:x:106:110:MySQL Server,,,:/nonexistent:/bin/false
""",
    "/etc/hosts": """127.0.0.1	localhost
127.0.1.1	ubuntu-server
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
""",
    "/etc/hostname": "ubuntu-server\n",
    "/home/user/.bashrc": """# ~/.bashrc: executed by bash(1) for non-login shells.
export PS1='\\u@\\h:\\w\\$ '
export PATH=$PATH:/usr/local/bin
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
""",
    "/home/user/Documents/notes.txt": """TODO:
- Update server packages
- Check backup status
- Review access logs
""",
    "/var/www/html/index.html": """<!DOCTYPE html>
<html>
<head><title>Welcome to nginx!</title></head>
<body><h1>Welcome to nginx!</h1></body>
</html>
""",
    "/etc/resolv.conf": """nameserver 8.8.8.8
nameserver 8.8.4.4
""",
}


class FakeShell:
    def __init__(self, chan, ip, geo):
        self.chan = chan
        self.ip = ip
        self.geo = geo
        self.cwd = "/home/user"
        self.history = []
        self.env = {
            "HOME": "/home/user",
            "USER": "user",
            "SHELL": "/bin/bash",
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PWD": "/home/user",
            "LANG": "en_US.UTF-8",
            "TERM": "xterm-256color",
            "HOSTNAME": "ubuntu-server",
        }
        self.username = "user"
        self.hostname = "ubuntu-server"

    def send(self, msg):
        self.chan.send(msg)

    def prompt(self):
        # Shorten path like real bash (replace /home/user with ~)
        display_cwd = self.cwd.replace("/home/user", "~") if self.cwd.startswith("/home/user") else self.cwd
        return f"{self.username}@{self.hostname}:{display_cwd}$ "

    def run(self):
        # Realistic Ubuntu SSH login banner
        self.send("\r\nWelcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-88-generic x86_64)\r\n\r\n")
        self.send(" * Documentation:  https://help.ubuntu.com\r\n")
        self.send(" * Management:     https://landscape.canonical.com\r\n")
        self.send(" * Support:        https://ubuntu.com/advantage\r\n\r\n")
        self.send(f"  System load:  0.{random.randint(10,50)}             Processes:             {random.randint(120,180)}\r\n")
        self.send(f"  Usage of /:   {random.randint(25,45)}% of 49.12GB   Users logged in:       1\r\n")
        self.send(f"  Memory usage: {random.randint(30,60)}%              IPv4 address for eth0: 10.0.0.{random.randint(2,254)}\r\n")
        self.send(f"  Swap usage:   {random.randint(0,15)}%\r\n\r\n")
        self.send(f"Last login: {time.strftime('%a %b %d %H:%M:%S %Y')} from {self.ip}\r\n")
        
        while True:
            self.send(self.prompt())
            try:
                cmd = self.chan.recv(1024).decode().strip()
            except:
                break

            if not cmd:
                continue

            self.history.append(cmd)
            log_event("command", {
                "ip": self.ip,
                "geo": self.geo,
                "command": cmd
            })

            if cmd in ("exit", "logout", "quit"):
                self.send("logout\r\n")
                break

            self.handle_command(cmd)

    def get_dir_contents(self, path):
        """Get directory contents from fake filesystem"""
        normalized = path.rstrip("/") or "/"
        return FAKE_FS.get(normalized, None)

    def handle_command(self, cmd):
        parts = cmd.split()
        if not parts:
            return
        
        base_cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        # pwd
        if base_cmd == "pwd":
            self.send(self.cwd + "\r\n")

        # ls command with flags
        elif base_cmd == "ls":
            self._handle_ls(args)

        # cd command
        elif base_cmd == "cd":
            self._handle_cd(args)

        # cat command
        elif base_cmd == "cat":
            self._handle_cat(args)

        # echo
        elif base_cmd == "echo":
            self._handle_echo(args)

        # whoami
        elif base_cmd == "whoami":
            self.send("user\r\n")

        # id
        elif base_cmd == "id":
            self.send("uid=1000(user) gid=1000(user) groups=1000(user),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),116(lxd)\r\n")

        # uname
        elif base_cmd == "uname":
            if "-a" in args:
                self.send("Linux ubuntu-server 5.15.0-88-generic #98-Ubuntu SMP Mon Oct 2 15:18:56 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux\r\n")
            elif "-r" in args:
                self.send("5.15.0-88-generic\r\n")
            else:
                self.send("Linux\r\n")

        # hostname
        elif base_cmd == "hostname":
            self.send("ubuntu-server\r\n")

        # uptime
        elif base_cmd == "uptime":
            days = random.randint(5, 120)
            hours = random.randint(0, 23)
            mins = random.randint(0, 59)
            users = random.randint(1, 3)
            load1 = random.uniform(0.01, 0.8)
            load5 = random.uniform(0.01, 0.5)
            load15 = random.uniform(0.01, 0.3)
            self.send(f" {time.strftime('%H:%M:%S')} up {days} days, {hours}:{mins:02d},  {users} user,  load average: {load1:.2f}, {load5:.2f}, {load15:.2f}\r\n")

        # w / who
        elif base_cmd in ("w", "who"):
            self.send(f"user     pts/0        {time.strftime('%Y-%m-%d %H:%M')} ({self.ip})\r\n")

        # ps
        elif base_cmd == "ps":
            self._handle_ps(args)

        # top
        elif base_cmd == "top":
            self.send("top - use 'q' to quit (interactive mode not supported)\r\n")

        # free
        elif base_cmd == "free":
            self.send("               total        used        free      shared  buff/cache   available\r\n")
            self.send("Mem:         8134656     2847532     1892456      234156     3394668     4756892\r\n")
            self.send("Swap:        2097148      156432     1940716\r\n")

        # df
        elif base_cmd == "df":
            self.send("Filesystem     1K-blocks     Used Available Use% Mounted on\r\n")
            self.send("udev             4032936        0   4032936   0% /dev\r\n")
            self.send("tmpfs             813468     1876    811592   1% /run\r\n")
            self.send("/dev/sda1       51474044 18562348  30272780  38% /\r\n")
            self.send("tmpfs            4067328        0   4067328   0% /dev/shm\r\n")

        # env / printenv
        elif base_cmd in ("env", "printenv"):
            for k, v in self.env.items():
                self.send(f"{k}={v}\r\n")

        # export
        elif base_cmd == "export":
            if args:
                for arg in args:
                    if "=" in arg:
                        key, val = arg.split("=", 1)
                        self.env[key] = val.strip('"\'')
            else:
                for k, v in self.env.items():
                    self.send(f"declare -x {k}=\"{v}\"\r\n")

        # history
        elif base_cmd == "history":
            for i, c in enumerate(self.history, 1):
                self.send(f"  {i}  {c}\r\n")

        # clear
        elif base_cmd == "clear":
            self.send("\033[2J\033[H")

        # date
        elif base_cmd == "date":
            self.send(time.strftime("%a %b %d %H:%M:%S %Z %Y") + "\r\n")

        # ifconfig / ip
        elif base_cmd == "ifconfig":
            self._handle_ifconfig()
        elif base_cmd == "ip":
            if args and args[0] in ("a", "addr", "address"):
                self._handle_ip_addr()
            else:
                self.send("Usage: ip [ OPTIONS ] OBJECT { COMMAND | help }\r\n")

        # netstat
        elif base_cmd == "netstat":
            self._handle_netstat()

        # wget / curl
        elif base_cmd in ("wget", "curl"):
            if args:
                time.sleep(random.uniform(0.5, 1.5))
                self.send(f"Connecting to {args[-1]}... failed: Connection timed out.\r\n")
            else:
                self.send(f"{base_cmd}: missing URL\r\n")

        # ping
        elif base_cmd == "ping":
            if args:
                self.send(f"PING {args[-1]} ({args[-1]}): 56 data bytes\r\n")
                self.send(f"^C\r\n--- {args[-1]} ping statistics ---\r\n")
                self.send("0 packets transmitted, 0 packets received, 100% packet loss\r\n")
            else:
                self.send("ping: usage error: Destination address required\r\n")

        # sudo
        elif base_cmd == "sudo":
            if args:
                self.send("[sudo] password for user: ")
                try:
                    self.chan.recv(1024)  # Capture password attempt
                except:
                    pass
                self.send("\r\nuser is not in the sudoers file. This incident will be reported.\r\n")
            else:
                self.send("usage: sudo -h | -K | -k | -V\r\n")

        # su
        elif base_cmd == "su":
            self.send("Password: ")
            try:
                self.chan.recv(1024)
            except:
                pass
            self.send("\r\nsu: Authentication failure\r\n")

        # chmod / chown
        elif base_cmd in ("chmod", "chown"):
            if len(args) < 2:
                self.send(f"{base_cmd}: missing operand\r\n")
            else:
                self.send(f"{base_cmd}: changing permissions of '{args[-1]}': Operation not permitted\r\n")

        # rm
        elif base_cmd == "rm":
            if args:
                self.send(f"rm: cannot remove '{args[-1]}': Permission denied\r\n")
            else:
                self.send("rm: missing operand\r\n")

        # mkdir
        elif base_cmd == "mkdir":
            if args:
                self.send(f"mkdir: cannot create directory '{args[-1]}': Permission denied\r\n")
            else:
                self.send("mkdir: missing operand\r\n")

        # touch
        elif base_cmd == "touch":
            if args:
                self.send(f"touch: cannot touch '{args[-1]}': Permission denied\r\n")
            else:
                self.send("touch: missing operand\r\n")

        # cp / mv
        elif base_cmd in ("cp", "mv"):
            if len(args) < 2:
                self.send(f"{base_cmd}: missing file operand\r\n")
            else:
                self.send(f"{base_cmd}: cannot stat '{args[0]}': Permission denied\r\n")

        # find
        elif base_cmd == "find":
            if args:
                self.send(f"find: '{args[-1]}': Permission denied\r\n")
            else:
                self.send("find: missing path\r\n")

        # grep
        elif base_cmd == "grep":
            if len(args) < 2:
                self.send("Usage: grep [OPTION]... PATTERNS [FILE]...\r\n")
            else:
                # Simulate no matches
                pass

        # head / tail
        elif base_cmd in ("head", "tail"):
            if args:
                filepath = self._resolve_path(args[-1])
                if filepath in FAKE_FILES:
                    lines = FAKE_FILES[filepath].strip().split("\n")
                    if base_cmd == "head":
                        for line in lines[:10]:
                            self.send(line + "\r\n")
                    else:
                        for line in lines[-10:]:
                            self.send(line + "\r\n")
                else:
                    self.send(f"{base_cmd}: cannot open '{args[-1]}' for reading: No such file or directory\r\n")
            else:
                self.send(f"{base_cmd}: missing file operand\r\n")

        # which
        elif base_cmd == "which":
            if args:
                common_bins = ["ls", "cat", "grep", "find", "python3", "bash", "sh", "wget", "curl", "vim", "nano", "ssh", "scp"]
                if args[0] in common_bins:
                    self.send(f"/usr/bin/{args[0]}\r\n")
            else:
                self.send("which: missing argument\r\n")

        # type
        elif base_cmd == "type":
            if args:
                self.send(f"{args[0]} is /usr/bin/{args[0]}\r\n")

        # file
        elif base_cmd == "file":
            if args:
                self.send(f"{args[0]}: ASCII text\r\n")
            else:
                self.send("Usage: file [OPTION...] [FILE...]\r\n")

        # man
        elif base_cmd == "man":
            if args:
                self.send(f"No manual entry for {args[0]}\r\n")
            else:
                self.send("What manual page do you want?\r\n")

        # crontab
        elif base_cmd == "crontab":
            if "-l" in args:
                self.send("no crontab for user\r\n")
            elif "-e" in args:
                self.send("no crontab for user - using an empty one\r\n")
                self.send("crontab: no editor found\r\n")
            else:
                self.send("no crontab for user\r\n")

        # service / systemctl
        elif base_cmd == "service":
            if len(args) >= 2:
                self.send(f"Failed to {args[1]} {args[0]}.service: Access denied\r\n")
            else:
                self.send("Usage: service <service> <action>\r\n")
        elif base_cmd == "systemctl":
            if args:
                self.send(f"Failed to {args[0]}: Access denied\r\n")
            else:
                self.send("systemctl: missing command\r\n")

        # apt / apt-get / yum
        elif base_cmd in ("apt", "apt-get", "yum", "dnf"):
            self.send(f"E: Could not open lock file - open (13: Permission denied)\r\n")
            self.send(f"E: Unable to lock the administration directory, are you root?\r\n")

        # pip
        elif base_cmd in ("pip", "pip3"):
            if args and args[0] == "install":
                self.send("ERROR: Could not install packages due to permission error\r\n")
            else:
                self.send("pip 23.0.1 from /usr/lib/python3/dist-packages/pip (python 3.10)\r\n")

        # python
        elif base_cmd in ("python", "python3"):
            if not args:
                self.send("Python 3.10.12 (main, Jun 11 2023, 05:26:28) [GCC 11.4.0] on linux\r\n")
                self.send("Type \"help\", \"copyright\", \"credits\" or \"license\" for more information.\r\n")
                self.send(">>> (use Ctrl+D to exit)\r\n")
            elif args[0] == "--version" or args[0] == "-V":
                self.send("Python 3.10.12\r\n")

        # gcc / make
        elif base_cmd in ("gcc", "g++", "make"):
            if args:
                self.send(f"{base_cmd}: error: no input files\r\n")
            else:
                self.send(f"{base_cmd}: fatal error: no input files\r\n")

        # vim / nano / vi
        elif base_cmd in ("vim", "vi", "nano"):
            if args:
                self.send(f"E: Cannot open '{args[0]}' for writing: Permission denied\r\n")
            else:
                self.send("Vim - Vi IMproved 8.2 (terminal mode not supported)\r\n")

        # ssh / scp
        elif base_cmd in ("ssh", "scp"):
            if args:
                time.sleep(random.uniform(1, 2))
                self.send(f"ssh: connect to host {args[-1]} port 22: Connection timed out\r\n")
            else:
                self.send(f"usage: {base_cmd} [-options] [user@]host\r\n")

        # nmap
        elif base_cmd == "nmap":
            self.send("bash: nmap: command not found\r\n")

        # nc / netcat
        elif base_cmd in ("nc", "netcat"):
            self.send("bash: nc: command not found\r\n")

        # alias
        elif base_cmd == "alias":
            self.send("alias ll='ls -alF'\r\n")
            self.send("alias la='ls -A'\r\n")
            self.send("alias l='ls -CF'\r\n")

        # help
        elif base_cmd == "help":
            self.send("GNU bash, version 5.1.16(1)-release (x86_64-pc-linux-gnu)\r\n")
            self.send("These shell commands are defined internally. Type `help name' for more info.\r\n")

        # true / false
        elif base_cmd == "true":
            pass
        elif base_cmd == "false":
            pass

        # sleep
        elif base_cmd == "sleep":
            if args:
                try:
                    secs = min(float(args[0]), 5)  # Cap at 5 seconds
                    time.sleep(secs)
                except:
                    self.send("sleep: invalid time interval\r\n")
            else:
                self.send("sleep: missing operand\r\n")

        # Unknown command
        else:
            self.send(f"bash: {base_cmd}: command not found\r\n")

    def _resolve_path(self, path):
        """Resolve relative paths to absolute"""
        if path.startswith("/"):
            return path
        elif path.startswith("~"):
            return path.replace("~", "/home/user", 1)
        else:
            return os.path.join(self.cwd, path).replace("\\", "/")

    def _handle_ls(self, args):
        """Handle ls command with various flags"""
        show_all = "-a" in args or "-la" in args or "-al" in args
        show_long = "-l" in args or "-la" in args or "-al" in args or "-lh" in args
        
        # Determine target path
        target = self.cwd
        for arg in args:
            if not arg.startswith("-"):
                target = self._resolve_path(arg)
                break

        contents = self.get_dir_contents(target)
        if contents is None:
            self.send(f"ls: cannot access '{target}': No such file or directory\r\n")
            return

        if show_long:
            if show_all:
                self.send("total 48\r\n")
                self.send(f"drwxr-xr-x  5 user user 4096 {time.strftime('%b %d %H:%M')} .\r\n")
                self.send(f"drwxr-xr-x  3 root root 4096 {time.strftime('%b %d %H:%M')} ..\r\n")
            for item in contents:
                if item.startswith(".") and not show_all:
                    continue
                is_dir = item in FAKE_FS.get(target.rstrip("/") + "/" + item, []) or "/" + item in FAKE_FS or target.rstrip("/") + "/" + item in FAKE_FS
                if target == "/" or target + "/" + item in FAKE_FS or item in ["bin", "boot", "dev", "etc", "home", "lib", "lib64", "media", "mnt", "opt", "proc", "root", "run", "sbin", "srv", "sys", "tmp", "usr", "var", "Documents", "Downloads", "Pictures", "Music", "Videos", ".ssh"]:
                    is_dir = True
                perms = "drwxr-xr-x" if is_dir else "-rw-r--r--"
                size = random.randint(100, 8000) if not is_dir else 4096
                self.send(f"{perms}  1 user user {size:5} {time.strftime('%b %d %H:%M')} {item}\r\n")
        else:
            visible = [f for f in contents if show_all or not f.startswith(".")]
            self.send("  ".join(visible) + "\r\n")

    def _handle_cd(self, args):
        """Handle cd command"""
        if not args or args[0] == "~":
            self.cwd = "/home/user"
        elif args[0] == "-":
            self.send(self.cwd + "\r\n")
        elif args[0] == "..":
            parent = os.path.dirname(self.cwd)
            self.cwd = parent if parent else "/"
        elif args[0].startswith("/"):
            self.cwd = args[0]
        elif args[0].startswith("~"):
            self.cwd = args[0].replace("~", "/home/user", 1)
        else:
            self.cwd = os.path.join(self.cwd, args[0]).replace("\\", "/")
        self.env["PWD"] = self.cwd

    def _handle_cat(self, args):
        """Handle cat command"""
        if not args:
            self.send("cat: missing file operand\r\n")
            return
        
        for arg in args:
            if arg.startswith("-"):
                continue
            filepath = self._resolve_path(arg)
            if filepath in FAKE_FILES:
                self.send(FAKE_FILES[filepath])
            elif "shadow" in filepath or "id_rsa" in filepath.lower() or "sudoers" in filepath:
                self.send(f"cat: {arg}: Permission denied\r\n")
            else:
                self.send(f"cat: {arg}: No such file or directory\r\n")

    def _handle_echo(self, args):
        """Handle echo command"""
        text = " ".join(args)
        # Handle environment variables
        for var, val in self.env.items():
            text = text.replace(f"${var}", val)
            text = text.replace(f"${{{var}}}", val)
        # Remove quotes
        text = text.strip('"\'')
        self.send(text + "\r\n")

    def _handle_ps(self, args):
        """Handle ps command"""
        if "aux" in args or "-aux" in args or "-ef" in args:
            self.send("USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\r\n")
            self.send("root           1  0.0  0.1 169436 11896 ?        Ss   Jan01   0:12 /sbin/init\r\n")
            self.send("root           2  0.0  0.0      0     0 ?        S    Jan01   0:00 [kthreadd]\r\n")
            self.send("root         432  0.0  0.1  72296  6144 ?        Ss   Jan01   0:02 /usr/sbin/sshd -D\r\n")
            self.send("mysql        815  0.1  2.5 1834568 198432 ?      Ssl  Jan01   8:42 /usr/sbin/mysqld\r\n")
            self.send("www-data     923  0.0  0.3 214628 25432 ?        S    Jan01   0:15 /usr/sbin/apache2 -k start\r\n")
            self.send(f"user       {random.randint(10000,30000)}  0.0  0.1  21532  5328 pts/0    Ss   {time.strftime('%H:%M')}   0:00 -bash\r\n")
            self.send(f"user       {random.randint(30001,40000)}  0.0  0.0  38372  3456 pts/0    R+   {time.strftime('%H:%M')}   0:00 ps aux\r\n")
        else:
            self.send("    PID TTY          TIME CMD\r\n")
            self.send(f"  {random.randint(10000,30000)} pts/0    00:00:00 bash\r\n")
            self.send(f"  {random.randint(30001,40000)} pts/0    00:00:00 ps\r\n")

    def _handle_ifconfig(self):
        """Handle ifconfig command"""
        self.send("eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\r\n")
        self.send(f"        inet 10.0.0.{random.randint(2,254)}  netmask 255.255.255.0  broadcast 10.0.0.255\r\n")
        self.send("        inet6 fe80::215:5dff:fe00:1234  prefixlen 64  scopeid 0x20<link>\r\n")
        self.send("        ether 00:15:5d:00:12:34  txqueuelen 1000  (Ethernet)\r\n")
        self.send(f"        RX packets {random.randint(100000,999999)}  bytes {random.randint(10000000,99999999)} ({random.randint(10,99)}.{random.randint(0,9)} MB)\r\n")
        self.send(f"        TX packets {random.randint(50000,500000)}  bytes {random.randint(5000000,50000000)} ({random.randint(5,50)}.{random.randint(0,9)} MB)\r\n\r\n")
        self.send("lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536\r\n")
        self.send("        inet 127.0.0.1  netmask 255.0.0.0\r\n")
        self.send("        inet6 ::1  prefixlen 128  scopeid 0x10<host>\r\n")
        self.send("        loop  txqueuelen 1000  (Local Loopback)\r\n")

    def _handle_ip_addr(self):
        """Handle ip addr command"""
        self.send("1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000\r\n")
        self.send("    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00\r\n")
        self.send("    inet 127.0.0.1/8 scope host lo\r\n")
        self.send("2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000\r\n")
        self.send("    link/ether 00:15:5d:00:12:34 brd ff:ff:ff:ff:ff:ff\r\n")
        self.send(f"    inet 10.0.0.{random.randint(2,254)}/24 brd 10.0.0.255 scope global eth0\r\n")

    def _handle_netstat(self):
        """Handle netstat command"""
        self.send("Active Internet connections (servers and established)\r\n")
        self.send("Proto Recv-Q Send-Q Local Address           Foreign Address         State\r\n")
        self.send("tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN\r\n")
        self.send("tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN\r\n")
        self.send("tcp        0      0 127.0.0.1:3306          0.0.0.0:*               LISTEN\r\n")
        self.send(f"tcp        0      0 10.0.0.5:22             {self.ip}:{random.randint(40000,60000)}     ESTABLISHED\r\n")
