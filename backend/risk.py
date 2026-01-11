# High-risk commands that indicate malicious intent
DANGEROUS_COMMANDS = [
    "wget", "curl", "nc", "netcat", "bash -i", "sh -i",
    "chmod +x", "chmod 777", "/tmp/", "python -c", "perl -e",
    "base64", "eval", "exec", "/dev/tcp", "/dev/udp",
    "nmap", "masscan", "hydra", "nikto",
    "rm -rf", "mkfifo", "mknod", ">/dev/null",
    "id_rsa", "shadow", "passwd", "sudoers",
    "crontab", "authorized_keys", "ssh-keygen"
]

# Medium-risk commands
SUSPICIOUS_COMMANDS = [
    "uname", "cat /etc", "whoami", "id", "ifconfig", "ip addr",
    "netstat", "ps aux", "find /", "locate", "which",
    "sudo", "su ", "su-", "apt", "yum", "pip install"
]

# Low-risk reconnaissance commands
RECON_COMMANDS = ["pwd", "ls", "cd", "echo", "date", "uptime", "w", "who"]

def compute_risk(event):
    score = 0
    geo = event.get("geo", {})
    cmd = event.get("command", "").lower()
    event_type = event.get("type", "")

    # Network-based risk
    if geo.get("tor"): score += 40
    if geo.get("vpn"): score += 25
    if geo.get("hosting"): score += 20

    # Auth event gets base risk
    if event_type == "auth":
        score += 15

    # Command-based risk
    if any(x in cmd for x in DANGEROUS_COMMANDS):
        score += 35

    if any(x in cmd for x in SUSPICIOUS_COMMANDS):
        score += 15

    # Reduce score for benign recon
    if any(cmd.startswith(x) for x in RECON_COMMANDS):
        score -= 5

    return max(0, min(score, 100))
