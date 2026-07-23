from flask import Flask, render_template, request, jsonify
from flask import send_from_directory
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

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
)

# Configuration Constants
from pathlib import Path
import os

APP_DATA = Path(os.getenv("LOCALAPPDATA")) / "BoardDrop"

UPLOAD_FOLDER = APP_DATA / "uploads"
DATABASE_DIR = APP_DATA / "database"

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE = DATABASE_DIR / "boarddrop.db" 
ALLOWED_EXTENSIONS = {
    # Documents
    "pdf", "doc", "docx", "txt", "rtf", "odt",

    # Office
    "ppt", "pptx", "xls", "xlsx", "csv",

    # Images
    "png", "jpg", "jpeg", "gif", "bmp", "webp", "tiff", "svg",

    # Audio
    "mp3", "wav", "aac", "flac", "ogg",

    # Video
    "mp4", "avi", "mkv", "mov", "wmv", "webm",

    # Archives
    "zip", "rar", "7z", "tar", "gz",

    # Executables
    "exe", "msi", "apk", "iso"
}
FILE_RETENTION_SECONDS = 24 * 3600  # 24 hours

app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024   # 1 GB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATABASE_DIR, exist_ok=True)

connected_devices = 0
active_room_id = None
CURRENT_MODE = "online"

# ---------------- Database Setup ----------------
def init_db():
    with sqlite3.connect(DATABASE, timeout=30) as conn:
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
                        with sqlite3.connect(DATABASE, timeout=30) as conn:
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
    if CURRENT_MODE == "online":
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

    # Save upload history
    with sqlite3.connect(DATABASE, timeout=30) as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO upload_history (filename, filepath, upload_time) VALUES (?, ?, ?)",
            (filename, path, timestamp)
        )
        conn.commit()

    # Notify Desktop App
    socketio.emit("new_file", {
    "filename": filename,
    "filepath": str(path),
    "mode": CURRENT_MODE
        })

    return "Upload Successful", 200

@app.route("/uploads/<filename>")
def get_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ---------------- Socket.IO Events ----------------
@socketio.on("connect")
def handle_connect():
    global connected_devices

    connected_devices += 1

    print(f"[CONNECTED] Devices : {connected_devices}")

    socketio.emit(
    "device_count",
    {"count": connected_devices}
)
@socketio.on("disconnect")
def handle_disconnect():
    global connected_devices

    connected_devices = max(0, connected_devices - 1)

    print(f"[DISCONNECTED] Devices : {connected_devices}")

    socketio.emit(
    "device_count",
    {"count": connected_devices}
)

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

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
