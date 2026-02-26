#!/usr/bin/env python3
"""
CENTRALKA - PROSTA WERSJA DZIAŁAJĄCA + WIDOK KIOSK (fullscreen + ustawienia + ikony)
+ TRYB SERWISOWY (ukryty) Z LOGINEM/HASŁEM
"""
import socket
import threading
import time
import secrets
from datetime import datetime
from flask import Flask, jsonify, request
import sys

# =========== KONFIGURACJA ===========
ARDUINO_PORT = 8080
WEB_PORT = 5000

# ====== LOGIN DO TRYBU SERWISOWEGO ======
ADMIN_USER = "serwis"
ADMIN_PASS = "raspberry123"   # <-- ZMIEŃ!
ADMIN_SESSION_TTL = 600       # sekundy (10 min)

admin_sessions = {}  # token -> expires_epoch

# Globalne dane
sensor_data = {
    'temperature': '--',
    'humidity': '--',
    'last_update': None
}

# =========== SERWER ARDUINO ===========
def arduino_server():
    """Prosty serwer TCP"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', ARDUINO_PORT))
    sock.listen(5)

    print(f"📡 Serwer Arduino nasłuchuje na porcie {ARDUINO_PORT}")
    print("👂 Czekam na dane z Arduino...")

    while True:
        client, addr = sock.accept()
        print(f"✅ Arduino połączone: {addr[0]}")

        thread = threading.Thread(
            target=handle_arduino,
            args=(client, addr[0]),
            daemon=True
        )
        thread.start()

def handle_arduino(client, ip):
    """Obsługa Arduino"""
    global sensor_data

    try:
        client.settimeout(30.0)

        while True:
            try:
                data = client.recv(1024)
                if not data:
                    print(f"📭 {ip} rozłączony")
                    break

                message = data.decode(errors="ignore").strip()
                print(f"📩 {ip}: {message}")

                process_message(message, ip)

                client.send(b'OK\n')

            except socket.timeout:
                print(f"⏰ Timeout: {ip}")
                break

    except Exception as e:
        print(f"❌ Błąd: {e}")
    finally:
        try:
            client.close()
        except:
            pass
        print(f"🔌 Rozłączono: {ip}")

def process_message(message, ip):
    """Przetwarzaj wiadomość od Arduino"""
    global sensor_data

    if "TEMP:" in message and "HUM:" in message:
        # Format: TEMP:23.5:HUM:45
        try:
            parts = message.split(":")
            if len(parts) >= 4:
                temp = parts[1]
                hum = parts[3]

                sensor_data['temperature'] = temp
                sensor_data['humidity'] = hum
                sensor_data['last_update'] = datetime.now()

                print(f"🌡️ {ip}: {temp}°C, {hum}%")
        except:
            print(f"Błąd parsowania: {message}")

    elif "{" in message and "}" in message:
        # JSON format
        try:
            import json
            data = json.loads(message)

            temp = data.get('temp', data.get('temperature', '--'))
            hum = data.get('hum', data.get('humidity', '--'))

            sensor_data['temperature'] = str(temp)
            sensor_data['humidity'] = str(hum)
            sensor_data['last_update'] = datetime.now()

            print(f"📊 {ip}: {temp}°C, {hum}% (JSON)")
        except:
            print(f"Błąd JSON: {message}")

    elif "HELLO" in message:
        print(f"👋 {ip}: {message}")

    else:
        print(f"📝 {ip}: {message}")

# =========== FLASK APP ===========
app = Flask(__name__)

# ====== AUTH HELPERS ======
def _cleanup_sessions():
    now = time.time()
    for tok, exp in list(admin_sessions.items()):
        if exp < now:
            admin_sessions.pop(tok, None)

@app.route('/api/admin_login', methods=['POST'])
def api_admin_login():
    """
    JSON: {"user":"...", "pass":"..."}
    OK: {"ok": true, "token": "...", "ttl": 600}
    """
    _cleanup_sessions()
    data = request.get_json(silent=True) or {}
    user = str(data.get("user", ""))
    pw = str(data.get("pass", ""))

    if user == ADMIN_USER and pw == ADMIN_PASS:
        token = secrets.token_urlsafe(24)
        admin_sessions[token] = time.time() + ADMIN_SESSION_TTL
        return jsonify({"ok": True, "token": token, "ttl": ADMIN_SESSION_TTL})

    return jsonify({"ok": False}), 401

@app.route('/api/admin_check', methods=['POST'])
def api_admin_check():
    """
    JSON: {"token":"..."}
    """
    _cleanup_sessions()
    data = request.get_json(silent=True) or {}
    token = str(data.get("token", ""))

    exp = admin_sessions.get(token)
    if exp and exp >= time.time():
        return jsonify({"ok": True})

    return jsonify({"ok": False}), 401


@app.route('/')
def index():
    """Strona główna (normalna)"""
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Stacja pogodowa</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: auto; background: #f0f0f0; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; }
        .data-box { background: #e3f2fd; padding: 20px; margin: 20px 0; border-radius: 8px; text-align: center; }
        .temp { font-size: 48px; color: #d32f2f; font-weight: bold; }
        .hum { font-size: 48px; color: #1976d2; font-weight: bold; }
        .label { font-size: 18px; color: #666; margin-bottom: 10px; }
        .time { text-align: center; color: #666; margin-top: 20px; font-size: 14px; }
        .status { padding: 10px; background: #f5f5f5; border-radius: 5px; margin: 10px 0; }
        button, a.kiosk { padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; margin-right: 10px; margin-top: 10px; }
        button:hover, a.kiosk:hover { background: #45a049; }
        .row { display:flex; gap:10px; flex-wrap:wrap; justify-content:center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌡️ Stacja pogodowa</h1>

        <div class="data-box">
            <div class="label">Temperatura</div>
            <div class="temp" id="temperature">-- °C</div>
        </div>

        <div class="data-box">
            <div class="label">Wilgotność</div>
            <div class="hum" id="humidity">-- %</div>
        </div>

        <div class="time">
            Ostatnia aktualizacja: <span id="updateTime">--:--:--</span>
        </div>

        <div class="status">
            Status połączenia: <span id="connectionStatus">⏳ Ładowanie…</span>
        </div>

        <div class="row">
            <button onclick="updateData()">🔄 Odśwież</button>
            <button onclick="testConnection()">🔍 Test połączenia</button>
            <a class="kiosk" href="/kiosk">🖥️ Tryb Kiosk</a>
        </div>
    </div>

    <script>
        function updateData() {
            fetch('/api/data', {cache:'no-store'})
                .then(r => { if (!r.ok) throw new Error('Błąd sieci'); return r.json(); })
                .then(d => {
                    document.getElementById('temperature').textContent = d.temperature + ' °C';
                    document.getElementById('humidity').textContent = d.humidity + ' %';

                    if (d.time !== '--:--:--') {
                        document.getElementById('updateTime').textContent = d.time;
                        document.getElementById('connectionStatus').textContent = '✅ Aktywne';
                        document.getElementById('connectionStatus').style.color = 'green';
                    } else {
                        document.getElementById('connectionStatus').textContent = '⚠️ Brak danych';
                        document.getElementById('connectionStatus').style.color = 'orange';
                    }
                })
                .catch(() => {
                    document.getElementById('connectionStatus').textContent = '❌ Błąd połączenia';
                    document.getElementById('connectionStatus').style.color = 'red';
                });
        }

        function testConnection() {
            fetch('/api/test', {cache:'no-store'})
                .then(r => r.json())
                .then(d => alert('Serwer działa! Czas: ' + d.time))
                .catch(() => alert('Błąd połączenia z serwerem!'));
        }

        setInterval(updateData, 3000);
        updateData();
    </script>
</body>
</html>
"""

@app.route('/kiosk')
def kiosk():
    """
    Widok KIOSK: fullscreen + ustawienia + ikony.
    Tryb serwisowy: 5 tapów w tytuł (wymaga login/hasło).
    Wyjście z fullscreen: F lub F11 lub ESC.
    """
    return r"""
<!DOCTYPE html>
<html lang="pl" data-theme="auto">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Stacja pogodowa – Kiosk</title>

  <style>
    :root{
      --bg:#070a14;
      --text:rgba(255,255,255,.95);
      --muted:rgba(255,255,255,.65);
      --good:#22c55e;
      --bad:#ef4444;
      --warn:#fbbf24;
      --accent:#60a5fa;
      --glass: rgba(255,255,255,.08);
      --glass2: rgba(255,255,255,.05);
      --shadow: 0 18px 50px rgba(0,0,0,.55);
      --radius: 24px;
      --scale: 100%;
    }

    @media (prefers-color-scheme: light){
      :root{
        --bg:#f3f6fb;
        --text:#111827;
        --muted:#6b7280;
        --glass:#ffffff;
        --glass2:#f1f5ff;
        --shadow: 0 16px 40px rgba(16,24,40,.10);
      }
    }

    html[data-theme="light"]{
      --bg:#f3f6fb;
      --text:#111827;
      --muted:#6b7280;
      --glass:#ffffff;
      --glass2:#f1f5ff;
      --shadow: 0 16px 40px rgba(16,24,40,.10);
    }
    html[data-theme="dark"]{
      --bg:#070a14;
      --text:rgba(255,255,255,.95);
      --muted:rgba(255,255,255,.65);
      --glass: rgba(255,255,255,.08);
      --glass2: rgba(255,255,255,.05);
      --shadow: 0 18px 50px rgba(0,0,0,.55);
    }

    *{ box-sizing: border-box; }

    body{
      margin:0;
      min-height:100vh;
      background:
        radial-gradient(1200px 700px at 18% 10%, rgba(96,165,250,.22), transparent 60%),
        radial-gradient(900px 700px at 80% 25%, rgba(34,197,94,.18), transparent 60%),
        var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      padding: 22px;
      font-size: var(--scale);
    }

    .wrap{
      width:min(1100px, 100%);
      margin: 0 auto;
      display:flex;
      flex-direction:column;
      gap: 16px;
    }

    header{
      display:flex;
      justify-content:space-between;
      align-items:flex-start;
      gap: 16px;
      padding: 18px 20px;
      border-radius: var(--radius);
      background: linear-gradient(180deg, var(--glass), var(--glass2));
      box-shadow: var(--shadow);
    }

    h1{
      margin:0;
      font-size: 22px;
      letter-spacing: .2px;
      display:flex;
      align-items:center;
      gap:10px;
      user-select:none;
      touch-action: manipulation;
    }

    .sub{
      margin:6px 0 0 0;
      color: var(--muted);
      font-size: 14px;
      display:flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items:center;
    }

    .pill{
      display:inline-flex;
      align-items:center;
      gap: 10px;
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(96,165,250,.14);
      border: 1px solid rgba(96,165,250,.24);
      font-size: 14px;
      white-space:nowrap;
    }

    .dot{
      width: 12px; height: 12px; border-radius: 999px;
      background: var(--warn);
      box-shadow: 0 0 0 6px rgba(251,191,36,.20);
    }

    main{
      display:grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    main.one{ grid-template-columns: 1fr; }

    @media (max-width: 900px){
      main{ grid-template-columns: 1fr; }
    }

    .tile{
      border-radius: var(--radius);
      background: linear-gradient(180deg, var(--glass), var(--glass2));
      box-shadow: var(--shadow);
      padding: 22px;
      position:relative;
      overflow:hidden;
    }

    .tile::after{
      content:"";
      position:absolute;
      inset:-80px -80px auto auto;
      width: 320px;
      height: 320px;
      background: radial-gradient(circle at 30% 30%, rgba(96,165,250,.20), transparent 62%);
      transform: rotate(18deg);
      pointer-events:none;
    }

    .label{
      color: var(--muted);
      font-size: 14px;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap: 12px;
    }

    .big{
      font-variant-numeric: tabular-nums;
      font-weight: 900;
      letter-spacing: -1px;
      font-size: clamp(64px, 10vw, 160px);
      line-height: 1;
      margin: 10px 0 0 0;
      white-space: nowrap;
    }

    .unit{
      font-size: clamp(18px, 2.6vw, 34px);
      color: var(--muted);
      font-weight: 800;
      margin-left: 10px;
    }

    .meta{
      margin-top: 14px;
      color: var(--muted);
      font-size: 14px;
      display:flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items:center;
    }

    .chip{
      display:inline-flex;
      align-items:center;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(255,255,255,.08);
      border: 1px solid rgba(255,255,255,.10);
      backdrop-filter: blur(6px);
    }
    @media (prefers-color-scheme: light){
      .chip{
        background: rgba(17,24,39,.04);
        border: 1px solid rgba(17,24,39,.08);
      }
    }

    footer{
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap: 12px;
      padding: 14px 18px;
      border-radius: var(--radius);
      background: linear-gradient(180deg, var(--glass), var(--glass2));
      box-shadow: var(--shadow);
      color: var(--muted);
      font-size: 14px;
      flex-wrap: wrap;
    }

    button, a.back{
      border: 1px solid rgba(96,165,250,.28);
      background: rgba(96,165,250,.18);
      color: var(--text);
      padding: 10px 14px;
      border-radius: 14px;
      font-weight: 800;
      font-size: 14px;
      cursor: pointer;
      text-decoration:none;
      display:inline-flex;
      align-items:center;
      gap:8px;
    }
    button:active{ transform: translateY(1px); }

    .hint{ opacity:.95; }

    /* ====== MODAL (używamy do ustawień + login/serwis) ====== */
    .modalBg{
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,.35);
      backdrop-filter: blur(2px);
      display:none;
      align-items:center;
      justify-content:center;
      padding: 18px;
      z-index: 50;
    }
    .modalBg.show{ display:flex; }

    .modal{
      width: min(620px, 100%);
      border-radius: 18px;
      background: linear-gradient(180deg, var(--glass), var(--glass2));
      box-shadow: var(--shadow);
      border: 1px solid rgba(255,255,255,.12);
      overflow:hidden;
    }
    .modalHead{
      display:flex;
      align-items:center;
      justify-content:space-between;
      padding: 14px 16px;
      border-bottom: 1px solid rgba(255,255,255,.10);
      color: var(--text);
      font-weight: 900;
    }
    .modalBody{ padding: 14px 16px; display:flex; flex-direction:column; gap: 12px; }

    .rowSet{
      display:grid;
      grid-template-columns: 1fr 220px;
      gap: 12px;
      align-items:center;
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(255,255,255,.06);
      border: 1px solid rgba(255,255,255,.10);
    }
    @media (max-width: 520px){
      .rowSet{ grid-template-columns: 1fr; }
    }
    .rowSet .t{ font-weight: 900; color: var(--text); }
    .rowSet .d{ font-size: 12px; color: var(--muted); margin-top: 4px; }

    select, input[type="range"], input[type="text"], input[type="password"]{
      width:100%;
      padding: 10px 10px;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,.14);
      background: rgba(0,0,0,.15);
      color: var(--text);
      font-weight: 800;
    }
    @media (prefers-color-scheme: light){
      select, input[type="range"], input[type="text"], input[type="password"]{
        background: rgba(17,24,39,.04);
        border: 1px solid rgba(17,24,39,.12);
        color: var(--text);
      }
    }

    .modalFoot{
      display:flex;
      justify-content:space-between;
      gap: 10px;
      padding: 14px 16px;
      border-top: 1px solid rgba(255,255,255,.10);
    }
  </style>
</head>

<body>
  <div class="wrap">
    <header>
      <div>
        <h1 id="kioskTitle">🖥️ <span>Stacja pogodowa</span> <span style="font-size:14px;color:var(--muted);font-weight:800;">(Kiosk)</span></h1>
        <div class="sub">
          <span>🕒 RPi:</span> <strong id="piClock">--</strong>
          <span>·</span>
          <span>📡 Arduino:</span> <strong id="updateTime">--:--:--</strong>
        </div>
      </div>

      <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap; justify-content:flex-end;">
        <div class="pill" title="Status danych">
          <span class="dot" id="statusDot"></span>
          <strong id="connectionStatus">Ładowanie…</strong>
        </div>
        <button onclick="openSettings()" title="Ustawienia">⚙️</button>
      </div>
    </header>

    <main id="grid">
      <section class="tile" id="tileTemp">
        <div class="label">
          <span>🌡️ Temperatura</span>
          <span class="chip">📡 /api/data</span>
        </div>

        <div class="big"><span id="temperature">--</span><span class="unit">°C</span></div>

        <div class="meta">
          <span class="chip">⏱️ Minęło: <strong id="ago">--</strong></span>
          <span class="chip">✅ OK: <strong id="lastOk">--</strong></span>
        </div>
      </section>

      <section class="tile" id="tileHum">
        <div class="label">
          <span>💧 Wilgotność</span>
          <span class="chip">🧠 cache: <strong id="cacheInfo">OK</strong></span>
        </div>

        <div class="big"><span id="humidity">--</span><span class="unit">%</span></div>

        <div class="meta">
          <span class="chip">⌨️ Wyjście: F / F11 / ESC</span>
          <span class="chip">🔄 Auto: <strong id="refreshLabel">3</strong>s</span>
        </div>
      </section>
    </main>

    <footer>
      <div class="hint">
        ⛶ Fullscreen auto (może wymagać kliknięcia). Wyjście: F/F11/ESC. • Serwis: 5 tapów w tytuł.
      </div>
      <div style="display:flex; gap:10px; flex-wrap:wrap;">
        <button onclick="updateData(true)">🔄 Odśwież</button>
        <button onclick="toggleFullscreen()">⛶ Fullscreen</button>
        <a class="back" href="/">↩ Panel</a>
      </div>
    </footer>
  </div>

  <!-- SETTINGS MODAL -->
  <div class="modalBg" id="modalBg" onclick="closeSettings(event)">
    <div class="modal" onclick="event.stopPropagation()">
      <div class="modalHead">
        <div>⚙️ Ustawienia</div>
        <button onclick="closeSettings()">✖</button>
      </div>

      <div class="modalBody">
        <div class="rowSet">
          <div>
            <div class="t">⛶ Fullscreen</div>
            <div class="d">Włącz/wyłącz pełny ekran.</div>
          </div>
          <select id="setFullscreen">
            <option value="auto">Auto (spróbuj)</option>
            <option value="on">Włącz</option>
            <option value="off">Wyłącz</option>
          </select>
        </div>

        <div class="rowSet">
          <div>
            <div class="t">🔄 Odświeżanie</div>
            <div class="d">Co ile sekund pobierać /api/data.</div>
          </div>
          <select id="setRefresh">
            <option value="1">1 s</option>
            <option value="3">3 s</option>
            <option value="5">5 s</option>
            <option value="10">10 s</option>
          </select>
        </div>

        <div class="rowSet">
          <div>
            <div class="t">🧩 Układ</div>
            <div class="d">1 kafel lub 2 kafle.</div>
          </div>
          <select id="setLayout">
            <option value="2">2 kafle</option>
            <option value="1">1 kafel (tylko temp)</option>
          </select>
        </div>

        <div class="rowSet">
          <div>
            <div class="t">🔠 Skala</div>
            <div class="d">Rozmiar UI na ekranie.</div>
          </div>
          <select id="setScale">
            <option value="90">90%</option>
            <option value="100">100%</option>
            <option value="110">110%</option>
            <option value="120">120%</option>
          </select>
        </div>

        <div class="rowSet">
          <div>
            <div class="t">🎨 Motyw</div>
            <div class="d">Auto / ciemny / jasny.</div>
          </div>
          <select id="setTheme">
            <option value="auto">Auto</option>
            <option value="dark">Ciemny</option>
            <option value="light">Jasny</option>
          </select>
        </div>

        <div class="rowSet">
          <div>
            <div class="t">⏳ Timeout danych</div>
            <div class="d">Po ilu sekundach bez update uznać „brak danych”.</div>
          </div>
          <select id="setTimeout">
            <option value="5">5 s</option>
            <option value="12">12 s</option>
            <option value="30">30 s</option>
          </select>
        </div>
      </div>

      <div class="modalFoot">
        <button onclick="resetSettings()">♻️ Reset</button>
        <button onclick="saveSettings()">✅ Zapisz</button>
      </div>
    </div>
  </div>

  <!-- LOGIN (TRYB SERWISOWY) -->
  <div class="modalBg" id="loginBg" onclick="closeLogin(event)">
    <div class="modal" onclick="event.stopPropagation()">
      <div class="modalHead">
        <div>🔒 Logowanie do trybu serwisowego</div>
        <button onclick="closeLogin()">✖</button>
      </div>

      <div class="modalBody">
        <div class="rowSet">
          <div>
            <div class="t">Login</div>
            <div class="d">Dostęp do serwisu.</div>
          </div>
          <input id="loginUser" type="text" autocomplete="username" placeholder="login">
        </div>

        <div class="rowSet">
          <div>
            <div class="t">Hasło</div>
            <div class="d">Dostęp do serwisu.</div>
          </div>
          <input id="loginPass" type="password" autocomplete="current-password" placeholder="hasło">
        </div>

        <div class="rowSet">
          <div>
            <div class="t">Status</div>
            <div class="d">Informacja logowania.</div>
          </div>
          <div id="loginStatus" style="font-weight:900;">Wpisz dane i kliknij Zaloguj</div>
        </div>
      </div>

      <div class="modalFoot">
        <button onclick="logout()">🚪 Wyloguj</button>
        <button onclick="doLogin()">✅ Zaloguj</button>
      </div>
    </div>
  </div>

  <!-- TRYB SERWISOWY -->
  <div class="modalBg" id="svcBg" onclick="closeSvc(event)">
    <div class="modal" onclick="event.stopPropagation()">
      <div class="modalHead">
        <div>🧰 Tryb serwisowy</div>
        <button onclick="closeSvc()">✖</button>
      </div>

      <div class="modalBody">
        <div class="rowSet">
          <div>
            <div class="t">🌐 Adres</div>
            <div class="d">Adres przeglądarki / origin.</div>
          </div>
          <div style="font-weight:900;" id="svcOrigin">--</div>
        </div>

        <div class="rowSet">
          <div>
            <div class="t">🔌 Porty</div>
            <div class="d">WEB / Arduino.</div>
          </div>
          <div style="font-weight:900;" id="svcPorts">--</div>
        </div>

        <div class="rowSet">
          <div>
            <div class="t">🕒 Czas RPi (/api/test)</div>
            <div class="d">Czy serwer Flask odpowiada.</div>
          </div>
          <div style="font-weight:900;" id="svcServerTime">--</div>
        </div>

        <div class="rowSet">
          <div>
            <div class="t">⏱️ Sekundy od ostatniego pakietu</div>
            <div class="d">Licznik od ostatniej aktualizacji danych.</div>
          </div>
          <div style="font-weight:900;" id="svcAgo">--</div>
        </div>

        <div class="rowSet">
          <div>
            <div class="t">📍 Ostatnie wartości</div>
            <div class="d">T / H.</div>
          </div>
          <div style="font-weight:900;" id="svcLast">--</div>
        </div>
      </div>

      <div class="modalFoot">
        <button onclick="logout()">🚪 Wyloguj</button>
        <button onclick="refreshSvc()">🔄 Odśwież serwis</button>
      </div>
    </div>
  </div>

  <script>
    // ====== SETTINGS (localStorage) ======
    const KEY = 'kiosk_settings_v1';
    const defaults = {
      fullscreen: 'auto',  // auto | on | off
      refresh: 3,          // seconds
      layout: 2,           // 1 | 2
      scale: 100,          // percent
      theme: 'auto',       // auto | dark | light
      staleTimeout: 12     // seconds
    };

    let settings = {...defaults};

    function loadSettings(){
      try{
        const raw = localStorage.getItem(KEY);
        if(raw){
          const obj = JSON.parse(raw);
          settings = {...defaults, ...obj};
        }
      }catch(e){}
      applySettingsToUI();
    }

    function applySettingsToUI(){
      document.documentElement.dataset.theme = settings.theme;
      document.documentElement.style.setProperty('--scale', settings.scale + '%');

      const grid = document.getElementById('grid');
      const humTile = document.getElementById('tileHum');
      if(settings.layout === 1){
        grid.classList.add('one');
        humTile.style.display = 'none';
      }else{
        grid.classList.remove('one');
        humTile.style.display = '';
      }

      document.getElementById('refreshLabel').textContent = String(settings.refresh);

      // ustaw wartości w modalu
      document.getElementById('setFullscreen').value = settings.fullscreen;
      document.getElementById('setRefresh').value = String(settings.refresh);
      document.getElementById('setLayout').value = String(settings.layout);
      document.getElementById('setScale').value = String(settings.scale);
      document.getElementById('setTheme').value = settings.theme;
      document.getElementById('setTimeout').value = String(settings.staleTimeout);

      restartRefreshTimer();
      enforceFullscreenSetting();
    }

    function saveSettings(){
      settings.fullscreen = document.getElementById('setFullscreen').value;
      settings.refresh = parseInt(document.getElementById('setRefresh').value, 10);
      settings.layout = parseInt(document.getElementById('setLayout').value, 10);
      settings.scale = parseInt(document.getElementById('setScale').value, 10);
      settings.theme = document.getElementById('setTheme').value;
      settings.staleTimeout = parseInt(document.getElementById('setTimeout').value, 10);

      localStorage.setItem(KEY, JSON.stringify(settings));
      applySettingsToUI();
      closeSettings();
    }

    function resetSettings(){
      settings = {...defaults};
      localStorage.setItem(KEY, JSON.stringify(settings));
      applySettingsToUI();
    }

    function openSettings(){
      document.getElementById('modalBg').classList.add('show');
      applySettingsToUI();
    }

    function closeSettings(ev){
      if(ev && ev.target && ev.target.id !== 'modalBg') return;
      document.getElementById('modalBg').classList.remove('show');
    }

    // ====== FULLSCREEN ======
    function isFullscreen(){
      return !!(document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement);
    }
    function enterFullscreen(){
      const el = document.documentElement;
      if (el.requestFullscreen) return el.requestFullscreen();
      if (el.webkitRequestFullscreen) return el.webkitRequestFullscreen();
      if (el.msRequestFullscreen) return el.msRequestFullscreen();
      return Promise.resolve();
    }
    function exitFullscreen(){
      if (document.exitFullscreen) return document.exitFullscreen();
      if (document.webkitExitFullscreen) return document.webkitExitFullscreen();
      if (document.msExitFullscreen) return document.msExitFullscreen();
      return Promise.resolve();
    }
    function toggleFullscreen(){
      if (isFullscreen()) exitFullscreen();
      else enterFullscreen();
    }
    function enforceFullscreenSetting(){
      if(settings.fullscreen === 'on'){
        if(!isFullscreen()) enterFullscreen().catch(()=>{});
      }else if(settings.fullscreen === 'off'){
        if(isFullscreen()) exitFullscreen().catch(()=>{});
      }
    }

    // Wyjście z fullscreen: F / F11 / ESC
    document.addEventListener('keydown', (e) => {
      const key = (e.key || '').toLowerCase();
      if (key === 'f' || key === 'f11' || e.keyCode === 122 || key === 'escape' || e.key === 'Esc') {
        if (key === 'f11' || e.keyCode === 122) e.preventDefault();
        exitFullscreen().catch(()=>{});
      }
    }, { passive: false });

    // klik: jeśli auto fullscreen i nie jest FS, spróbuj
    document.addEventListener('click', () => {
      if(settings.fullscreen === 'auto' && !isFullscreen()){
        enterFullscreen().catch(()=>{});
      }
    });

    // ====== STATUS / CLOCK / DATA ======
    let lastUpdateEpoch = null;
    let refreshTimer = null;

    function setStatus(state, msg){
      // state: ok | stale | bad
      const dot = document.getElementById('statusDot');
      const text = document.getElementById('connectionStatus');

      if(state === 'ok'){
        dot.style.background = 'var(--good)';
        dot.style.boxShadow = '0 0 0 6px rgba(34,197,94,.20)';
        text.textContent = msg || 'Online';
      }else if(state === 'stale'){
        dot.style.background = 'var(--warn)';
        dot.style.boxShadow = '0 0 0 6px rgba(251,191,36,.20)';
        text.textContent = msg || 'Stare dane';
      }else{
        dot.style.background = 'var(--bad)';
        dot.style.boxShadow = '0 0 0 6px rgba(239,68,68,.20)';
        text.textContent = msg || 'Brak danych';
      }
    }

    function formatAgo(seconds){
      if(seconds === null) return '--';
      if(seconds < 5) return 'teraz';
      if(seconds < 60) return seconds + ' s';
      const m = Math.floor(seconds/60);
      const s = seconds % 60;
      if(m < 60) return m + ' min ' + s + ' s';
      const h = Math.floor(m/60);
      const mm = m % 60;
      return h + ' h ' + mm + ' min';
    }

    function tickClock(){
      const now = new Date();
      const dd = String(now.getDate()).padStart(2,'0');
      const mo = String(now.getMonth()+1).padStart(2,'0');
      const yy = now.getFullYear();
      const hh = String(now.getHours()).padStart(2,'0');
      const mi = String(now.getMinutes()).padStart(2,'0');
      const ss = String(now.getSeconds()).padStart(2,'0');
      document.getElementById('piClock').textContent = `${dd}.${mo}.${yy} ${hh}:${mi}:${ss}`;

      if(lastUpdateEpoch){
        const ago = Math.max(0, Math.floor((Date.now() - lastUpdateEpoch)/1000));
        document.getElementById('ago').textContent = formatAgo(ago);

        if(ago > settings.staleTimeout){
          setStatus('bad', 'Brak danych z Arduino');
        }else if(ago > Math.max(3, Math.floor(settings.staleTimeout/2))){
          setStatus('stale', 'Stare dane');
        }
      }

      // jeśli serwis otwarty, odśwież licznik
      if(document.getElementById('svcBg').classList.contains('show')){
        document.getElementById('svcAgo').textContent = lastUpdateEpoch ? (Math.floor((Date.now()-lastUpdateEpoch)/1000) + " s") : "--";
      }
    }

    async function updateData(manual=false){
      try{
        const res = await fetch('/api/data', { cache: 'no-store' });
        if(!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();

        document.getElementById('temperature').textContent = data.temperature;
        document.getElementById('humidity').textContent = data.humidity;
        document.getElementById('updateTime').textContent = data.time || '--:--:--';
        document.getElementById('cacheInfo').textContent = 'OK';

        if(data.time && data.time !== '--:--:--'){
          lastUpdateEpoch = Date.now();
          document.getElementById('lastOk').textContent = new Date().toLocaleTimeString();
          setStatus('ok', 'Online');
        }else{
          setStatus('stale', 'Brak aktualizacji');
        }
      }catch(e){
        document.getElementById('cacheInfo').textContent = 'ERR';
        setStatus('bad', 'Błąd połączenia');
      }
    }

    function restartRefreshTimer(){
      if(refreshTimer) clearInterval(refreshTimer);
      refreshTimer = setInterval(()=>updateData(false), settings.refresh * 1000);
    }

    // ====== TRYB SERWISOWY (LOGIN) ======
    const ADMIN_TOKEN_KEY = 'admin_token_v1';

    function getToken(){ return localStorage.getItem(ADMIN_TOKEN_KEY) || ''; }
    function setToken(t){ localStorage.setItem(ADMIN_TOKEN_KEY, t); }
    function clearToken(){ localStorage.removeItem(ADMIN_TOKEN_KEY); }

    async function checkToken(){
      const token = getToken();
      if(!token) return false;
      try{
        const r = await fetch('/api/admin_check', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({token})
        });
        if(!r.ok) return false;
        const d = await r.json();
        return !!d.ok;
      }catch{
        return false;
      }
    }

    function openLogin(){
      document.getElementById('loginStatus').textContent = 'Wpisz dane i kliknij Zaloguj';
      document.getElementById('loginBg').classList.add('show');
      setTimeout(()=>document.getElementById('loginUser').focus(), 80);
    }
    function closeLogin(ev){
      if(ev && ev.target && ev.target.id !== 'loginBg') return;
      document.getElementById('loginBg').classList.remove('show');
    }

    async function doLogin(){
      const user = document.getElementById('loginUser').value || '';
      const pass = document.getElementById('loginPass').value || '';
      const st = document.getElementById('loginStatus');
      st.textContent = 'Logowanie…';

      try{
        const r = await fetch('/api/admin_login', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({user, pass})
        });

        if(!r.ok){
          st.textContent = '❌ Zły login lub hasło';
          return;
        }

        const d = await r.json();
        if(d.ok && d.token){
          setToken(d.token);
          st.textContent = '✅ Zalogowano';
          closeLogin();
          openSvc(); // otwórz serwis po loginie
        }else{
          st.textContent = '❌ Błąd logowania';
        }
      }catch{
        st.textContent = '❌ Brak połączenia z serwerem';
      }
    }

    function logout(){
      clearToken();
      // zamknij oba, żeby było czytelnie
      document.getElementById('loginBg').classList.remove('show');
      document.getElementById('svcBg').classList.remove('show');
    }

    async function openSvc(){
      const ok = await checkToken();
      if(!ok){
        openLogin();
        return;
      }
      document.getElementById('svcBg').classList.add('show');
      refreshSvc();
    }

    function closeSvc(ev){
      if(ev && ev.target && ev.target.id !== 'svcBg') return;
      document.getElementById('svcBg').classList.remove('show');
    }

    async function refreshSvc(){
      document.getElementById('svcOrigin').textContent = window.location.origin;
      const webPort = (window.location.port || (window.location.protocol === 'https:' ? '443' : '80'));
      document.getElementById('svcPorts').textContent = `WEB: ${webPort} | Arduino: 8080`;
      document.getElementById('svcLast').textContent = `T: ${document.getElementById('temperature').textContent} °C | H: ${document.getElementById('humidity').textContent} %`;
      document.getElementById('svcAgo').textContent = lastUpdateEpoch ? (Math.floor((Date.now()-lastUpdateEpoch)/1000) + " s") : "--";

      try{
        const r = await fetch('/api/test', {cache:'no-store'});
        const d = await r.json();
        document.getElementById('svcServerTime').textContent = d.time || '--';
      }catch{
        document.getElementById('svcServerTime').textContent = 'ERR';
      }
    }

    // 5 tapów w tytuł -> serwis
    let taps = 0;
    let tapTimer = null;
    const title = document.getElementById('kioskTitle');
    title.addEventListener('click', () => {
      taps++;
      if(tapTimer) clearTimeout(tapTimer);
      tapTimer = setTimeout(()=>{ taps = 0; }, 1200);

      if(taps >= 5){
        taps = 0;
        openSvc();
      }
    });

    // ====== START ======
    loadSettings();
    setStatus('stale', 'Ładowanie…');
    tickClock();
    updateData(false);
    setInterval(tickClock, 1000);

    setTimeout(() => {
      if(settings.fullscreen === 'auto'){
        enterFullscreen().catch(()=>{});
      }else{
        enforceFullscreenSetting();
      }
    }, 250);
  </script>
</body>
</html>
"""

@app.route('/api/data')
def api_data():
    """API z danymi"""
    global sensor_data

    time_str = '--:--:--'
    if sensor_data['last_update']:
        time_str = sensor_data['last_update'].strftime("%H:%M:%S")

    return jsonify({
        'temperature': sensor_data['temperature'],
        'humidity': sensor_data['humidity'],
        'time': time_str
    })

@app.route('/api/test')
def api_test():
    """Testowe API"""
    return jsonify({
        'status': 'ok',
        'time': datetime.now().strftime("%H:%M:%S"),
        'message': 'Serwer działa'
    })

# =========== URUCHOMIENIE ===========
def main():
    print("\n" + "="*50)
    print("STACJA POGODOWA - PROSTA WERSJA")
    print("="*50)

    server_thread = threading.Thread(target=arduino_server, daemon=True)
    server_thread.start()

    import subprocess
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        ip = result.stdout.strip().split()[0]
    except:
        ip = '127.0.0.1'

    print(f"\n✅ System gotowy")
    print(f"🌐 Panel web:  http://{ip}:{WEB_PORT}/")
    print(f"🖥️ Kiosk:      http://{ip}:{WEB_PORT}/kiosk")
    print(f"📡 Port Arduino: {ARDUINO_PORT}")
    print("🧰 Serwis: 5 tapów w tytuł (wymaga login/hasło)")
    print("\n🔄 Serwer uruchomiony")
    print("⏳ Ctrl+C aby zakończyć\n")

    app.run(host='0.0.0.0', port=WEB_PORT, debug=False, threaded=True)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Zamykanie...")
        sys.exit(0)
