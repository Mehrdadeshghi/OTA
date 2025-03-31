from flask import Flask, request, send_file, render_template_string, redirect, url_for
import json, time, os

app = Flask(__name__)

DEVICE_FILE = "devices.json"
FIRMWARE_FILE = "firmware.bin"

# HTML-Template direkt im Code
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>OTA Dashboard</title>
    <style>
        body { font-family: Arial; background: #f5f5f5; padding: 20px; }
        table { border-collapse: collapse; width: 100%; background: white; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #eee; }
        h1 { color: #333; }
        .upload-box { margin-top: 20px; background: white; padding: 20px; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>OTA Dashboard</h1>
    <h3>Online-Geräte</h3>
    <table>
        <tr><th>MAC-Adresse</th><th>IP</th><th>Zuletzt gesehen</th></tr>
        {% for mac, info in devices.items() %}
        <tr>
            <td>{{ mac }}</td>
            <td>{{ info.ip }}</td>
            <td>{{ info.last_seen }}</td>
        </tr>
        {% endfor %}
    </table>

    <div class="upload-box">
        <h3>Firmware hochladen (.bin)</h3>
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <input type="file" name="firmware" accept=".bin" required>
            <button type="submit">Upload</button>
        </form>
    </div>
</body>
</html>
'''

# ESP32 meldet sich hier
@app.route('/ping', methods=['POST'])
def ping():
    data = request.get_json()
    if not data or 'mac' not in data:
        return "Fehlende MAC-Adresse", 400

    devices = {}
    if os.path.exists(DEVICE_FILE):
        with open(DEVICE_FILE, 'r') as f:
            devices = json.load(f)

    devices[data['mac']] = {
        'ip': request.remote_addr,
        'last_seen': time.strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(DEVICE_FILE, 'w') as f:
        json.dump(devices, f)

    return "OK", 200

# OTA: ESP lädt Firmware
@app.route('/firmware')
def firmware():
    if os.path.exists(FIRMWARE_FILE):
        return send_file(FIRMWARE_FILE, mimetype='application/octet-stream')
    return "Firmware nicht gefunden", 404

# Upload der Firmware durch Admin
@app.route('/upload', methods=['POST'])
def upload():
    if 'firmware' not in request.files:
        return redirect(url_for('dashboard'))

    file = request.files['firmware']
    if file and file.filename.endswith('.bin'):
        file.save(FIRMWARE_FILE)
    return redirect(url_for('dashboard'))

# Admin Dashboard
@app.route('/')
def dashboard():
    devices = {}
    if os.path.exists(DEVICE_FILE):
        with open(DEVICE_FILE, 'r') as f:
            devices = json.load(f)
    return render_template_string(HTML_TEMPLATE, devices=devices)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8008)
