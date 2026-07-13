from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
from plyer import notification
import os
import sys
import sqlite3
from datetime import datetime
import threading
import time

# ---------------- PyInstaller Path Routing ----------------
# When compiled, PyInstaller unpacks files into a temp folder (_MEIPASS)
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    app = Flask(__name__, template_folder=template_folder)
else:
    app = Flask(__name__)

socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration Constants
UPLOAD_FOLDER = "uploads"
DATABASE_DIR = "database"
DATABASE = os.path.join(DATABASE_DIR, "boarddrop.db")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB Limit
ALLOWED_EXTENSIONS = {'pdf', 'ppt', 'pptx', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'zip', 'rar', 'txt'}
FILE_RETENTION_SECONDS = 24 * 3600  # 24 hours

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATABASE_DIR, exist_ok=True)

connected_devices = 0
active_room_id = None

# ---------------- Database Setup ----------------
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS upload_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                upload_time TEXT NOT NULL
            )
        ''')
        conn.commit()

init_db()

# ---------------- Background Auto-Cleanup ----------------
def auto_delete_old_files():
    while True:
        time.sleep(3600)
        now = time.time()
        try:
            for filename in os.listdir(UPLOAD_FOLDER):
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.isfile(filepath):
                    if os.path.getmtime(filepath) < now - FILE_RETENTION_SECONDS:
                        os.remove(filepath)
                        with sqlite3.connect(DATABASE) as conn:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM upload_history WHERE filename = ?", (filename,))
                            conn.commit()
                        print(f"[Auto-Cleanup] Deleted old file: {filename}")
        except Exception as e:
            print(f"[Auto-Cleanup Error] {e}")

threading.Thread(target=auto_delete_old_files, daemon=True).start()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- API Routes ----------------
@app.route("/")
def home():
    return "BoardDrop Server Running"

@app.route("/upload")
def upload():
    return render_template("upload.html")

@app.route("/verify_room", methods=["POST"])
def verify_room():
    data = request.json
    provided_id = data.get("room_id")
    if active_room_id and provided_id != active_room_id:
        return jsonify({"status": "error", "message": "Invalid Room ID"}), 403
    return jsonify({"status": "success"})

@app.route("/upload_file", methods=["POST"])
def upload_file():
    provided_room_id = request.form.get("room_id")
    if active_room_id and provided_room_id != active_room_id:
        return "Invalid Room ID. Access Denied.", 403

    if "file" not in request.files:
        return "No File", 400

    file = request.files["file"]
    if file.filename == "":
        return "No File Selected", 400

    if not allowed_file(file.filename):
        return "File type not allowed", 403

    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO upload_history (filename, filepath, upload_time) VALUES (?, ?, ?)",
                       (filename, path, timestamp))
        conn.commit()

    socketio.emit("new_file", {"filename": filename})

    # Desktop-only features (Windows only)
    if os.name == "nt":
        try:
            notification.notify(
                title="BoardDrop",
                message=f"{filename} Received",
                timeout=5
            )

            os.startfile(path)

        except Exception as e:
            print(f"Desktop feature error: {e}")

    return "Upload Successful", 200

# ---------------- Socket.IO Events ----------------
@socketio.on('connect')
def handle_connect():
    global connected_devices
    connected_devices += 1
    socketio.emit("device_count", {"count": connected_devices})

@socketio.on('disconnect')
def handle_disconnect():
    global connected_devices
    connected_devices = max(0, connected_devices - 1)
    socketio.emit("device_count", {"count": connected_devices})

@socketio.on('sync_room_id')
def sync_room_id(data):
    global active_room_id
    active_room_id = data.get("room_id")
    print(f"Server secured with Room ID: {active_room_id}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False
    )