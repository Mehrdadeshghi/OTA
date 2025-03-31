from flask import Flask, request, send_file, redirect, url_for, render_template_string, flash
import os
import json
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__))
FIRMWARE_PATH = os.path.join(UPLOAD_FOLDER, 'firmware.bin')
VERSION_PATH = os.path.join(UPLOAD_FOLDER, 'firmware.json')
DEVICES_PATH = os.path.join(UPLOAD_FOLDER, 'devices.json')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>OTA Management Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f4f4; padding: 30px; }
        .card { margin-bottom: 20px; }
        .table th, .table td { vertical-align: middle; }
    </style>
</head>
<body>
<div class="container">
    <h1 class="mb-4 text-center">ESP32 OTA Management</h1>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="alert alert-success">
          {% for message in messages %}
            <div>{{ message }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}

    <div class="card">
        <div class="card-body">
            <h5 class="card-title">Firmware hochladen</h5>
            <form action="/upload" method="post" enctype="multipart/form-data" class="row g-3">
                <div class="col-md-6">
                    <input type="file" name="firmware" accept=".bin" class="form-control" required>
                </div>
                <div class="col-md-4">
                    <input type="text" name="version" placeholder="Version z.B. 1.0.2" class="form-control" required>
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-primary w-100">Hochladen</button>
                </div>
            </form>
            <p class="mt-3">Aktuelle Version (Server): <strong>{{ version }}</strong></p>
            <p>Firmware-Link: <code>/firmware</code> | Versionsinfo: <code>/firmware.json</code></p>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
            <h5 class="card-title">Online-Geräte</h5>
            <table class="table table-bordered table-striped">
                <thead class="table-light">
                    <tr>
                        <th>MAC-Adresse</th>
                        <th>IP-Adresse</th>
                        <th>Firmware-Version</th>
                        <th>Zuletzt gesehen</th>
                    </tr>
                </thead>
                <tbody>
                    {% for mac, info in devices.items() %}
                    <tr>
                        <td>{{ mac }}</td>
                        <td>{{ info.ip }}</td>
                        <td>{{ info.version if 'version' in info else 'unbekannt' }}</td>
                        <td>{{ info.last_seen }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="4" class="text-center">Keine Geräte online.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
</body>
</html>
'''

@app.route('/')
def index():
    version = "unbekannt"
    if os.path.exists(VERSION_PATH):
        with open(VERSION_PATH, 'r') as f:
            try:
                version = json.load(f).get("version", "unbekannt")
            except:
                pass

    devices = {}
    if os.path.exists(DEVICES_PATH):
        with open(DEVICES_PATH, 'r') as f:
            try:
                devices = json.load(f)
            except:
                pass

    sorted_devices = dict(sorted(devices.items(), key=lambda item: item[1]['last_seen'], reverse=True))
    return render_template_string(HTML_TEMPLATE, version=version, devices=sorted_devices)

@app.route('/upload', methods=['POST'])
def upload():
    if 'firmware' not in request.files or 'version' not in request.form:
        flash("Fehler: Datei oder Version fehlt.")
        return redirect(url_for('index'))

    file = request.files['firmware']
    version = request.form['version']
    filename = secure_filename(file.filename)

    if not filename.endswith('.bin'):
        flash("Nur .bin-Dateien erlaubt!")
        return redirect(url_for('index'))

    file.save(FIRMWARE_PATH)

    with open(VERSION_PATH, 'w') as f:
        json.dump({"version": version, "url": request.url_root.rstrip('/') + "/firmware"}, f)

    flash("Firmware und Version erfolgreich aktualisiert!")
    return redirect(url_for('index'))

@app.route('/firmware')
def firmware():
    if os.path.exists(FIRMWARE_PATH):
        return send_file(FIRMWARE_PATH, mimetype='application/octet-stream')
    return "Firmware nicht gefunden", 404

@app.route('/firmware.json')
def firmware_info():
    if os.path.exists(VERSION_PATH):
        return send_file(VERSION_PATH, mimetype='application/json')
    return json.dumps({"error": "Keine Versionsinfo vorhanden"}), 404

@app.route('/ping', methods=['POST'])
def ping():
    data = request.get_json()
    if not data or 'mac' not in data:
        return "Fehlende MAC-Adresse", 400

    devices = {}
    if os.path.exists(DEVICES_PATH):
        with open(DEVICES_PATH, 'r') as f:
            try:
                devices = json.load(f)
            except:
                devices = {}

    devices[data['mac']] = {
        'ip': request.remote_addr,
        'last_seen': time.strftime('%Y-%m-%d %H:%M:%S'),
        'version': data.get('version', 'unbekannt')
    }

    with open(DEVICES_PATH, 'w') as f:
        json.dump(devices, f, indent=2)

    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8008, debug=True)

