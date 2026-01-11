

# VenomPot 🐍🍯

**A High-Interaction Multi-Protocol Honeypot & Monitoring Dashboard**

VenomPot is a modular, high-interaction honeypot written in Python. It simulates multiple network services (HTTP, SSH, FTP, and SMB) to deceive attackers, capture their behavior, and log their activities. It features a realistic virtual file system and a real-time web dashboard to visualize attacks.

---

## 🚀 Features

### 1. Multi-Protocol Deception

* **HTTP Honeypot**:
* Simulates a vulnerable web application (fake login portal).
* **Command Injection Trap**: A fake "dashboard" that simulates a shell vulnerability to capture attacker payloads.
* **HTA Traps**: Serves fake `robots.txt` and hidden config files that trigger malicious HTA (HTML Application) downloads to track advanced bot behavior.


* **SSH Honeypot**:
* High-interaction shell simulation using a **Virtual Filesystem (VFS)**.
* Supports common commands (`ls`, `cd`, `cat`, `nano`, `apt`, etc.) making the attacker feel like they are on a real Ubuntu server.
* Captures credentials (username/passwords) and session keystrokes.


* **FTP Honeypot**:
* Fully functional FTP server simulation supporting `PASV` mode.
* Shared **Virtual Filesystem** with SSH (files uploaded via FTP appear in SSH).
* Allows file uploads (`STOR`) and downloads (`RETR`) for forensic analysis of attacker tools.


* **SMB Honeypot**:
* Listens on port 445 to tarpit scanners and log connection attempts.



### 2. Virtual File System (VFS)

* A persistent, in-memory JSON-based file system (`FileSystemUbuntu2204.json`).
* Attackers can create directories, write files, and delete them. The changes persist during their session, providing a convincing environment.
* Includes fake system files (`/etc/passwd`, `/var/log`, etc.) to fool reconnaissance tools.

### 3. Live Threat Dashboard

* A dedicated **Dash/Plotly** web interface (`web_APP.py`).
* Visualizes real-time attack data:
* Top Attacker IPs (Geolocation).
* SSH Credential stuffing attempts.
* HTTP Request logs.
* FTP/SMB activity.


* Auto-refreshes every 3 seconds.

---

## 🛠️ Installation & Usage

### Prerequisites

* Python 3.8+
* Root/Administrator privileges (required to bind to ports like 21, 445, or 22).

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/VenomPot.git
cd VenomPot

```


2. **Install dependencies:**
```bash
pip install -r requirements.txt

```


*(Note: On Linux, you may need to install `libcairo2-dev` or similar if you face issues with graphical libraries, though usually pip handles it.)*

### Running the Honeypot (VenomPot)

The main entry point is `VenomPot.py`. You can choose which services to enable using flags.

**Common Usage:**

```bash
# Run HTTP on 8080, SSH on 2222, and FTP/SMB
sudo python3 VenomPot.py --http --ssh --ftpsmb -p 8080 -sp 2222

```

**Arguments:**
| Flag | Description | Default |
| :--- | :--- | :--- |
| `-wh`, `--http` | Enable the HTTP web honeypot | `False` |
| `-s`, `--ssh` | Enable the SSH honeypot | `False` |
| `-fs`, `--ftpsmb` | Enable FTP and SMB honeypots | `False` |
| `-p`, `--port` | Port for HTTP service | `8080` |
| `-sp`, `--sshport`| Port for SSH service | `21` (Change to 2222 to avoid conflict with FTP) |
| `-u`, `--username`| Fake admin username for the web login | `admin` |
| `-w`, `--password`| Fake admin password for the web login | `admin` |

**⚠️ Important:** * If running SSH on port 22, ensure your real SSH service is moved to a different port to avoid locking yourself out.

* FTP typically uses port 21. If you use `-sp 21` for SSH, they will conflict. **Use `-sp 2222` for SSH testing.**

---

### Running the Dashboard

To view the logs in real-time, run the dashboard application in a separate terminal window:

```bash
python3 web_APP.py

```

* Access the dashboard at: `http://127.0.0.1:8050`
* The dashboard reads logs from the `./logs/` directory automatically created by VenomPot.

---

## 🧪 How to Test It

Once VenomPot is running, you can act as the attacker to test the features.

### 1. Test HTTP (Web Trap)

* **Browser:** Navigate to `http://localhost:8080`.
* **Login:** Attempt to log in. Default valid creds are `admin` / `admin`.
* **Exploit:** On the dashboard page, try a command injection payload in the input box, e.g., `{{ 7*7 }}` or typical shell commands.
* **Traps:** Visit `http://localhost:8080/robots.txt` or `http://localhost:8080/.CONFIG` to trigger the decoy file download.

### 2. Test SSH (Shell Simulation)

* Connect using an SSH client:
```bash
ssh user@localhost -p 2222

```


*(Any password is accepted by default unless modified in code).*
* **Commands:** Try `ls -la`, `cd /etc`, `cat passwd`, or `mkdir hacker_stuff`. You will see these files persist in the virtual environment.

### 3. Test FTP (File Transfer)

* Connect using an FTP client:
```bash
ftp -p localhost 21

```


* **Upload/Download:** Try putting a file (`put test.txt`) or listing directories (`ls`).
* **Cross-Protocol Check:** Upload a file via FTP, then SSH in and run `ls`. You should see the file you just uploaded!

### 4. Test SMB

* Use `nmap` to scan the host and see port 445 open:
```bash
nmap -p 445 localhost

```



---

## 📂 Project Structure

* `VenomPot.py`: Main orchestrator script.
* `web_VenomPot.py`: Flask application for HTTP honeypot.
* `ssh_VenomPot.py`: Paramiko-based SSH server.
* `smb_ftp_VenomPot.py`: FTP server and SMB listener.
* `virtual_fs.py`: Logic for the fake filesystem (handles `cd`, `ls`, `mkdir`, etc.).
* `FileSystemUbuntu2204.json`: The "database" representing the fake file structure.
* `web_APP.py`: The Dash visualization tool.
* `logs/`: Directory where all attack logs are stored.