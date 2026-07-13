import requests
import os
import socket
import os
import sys
import time
import socketio
import threading
import sqlite3
import winreg
import pystray
from pystray import MenuItem as item
from utils.room import generate_room_id
from utils.qr_generator import generate_qr
from PIL import Image
import customtkinter as ctk

# Import the Flask app explicitly to run it from here
from app import app as flask_app, socketio as flask_sio

room_id = generate_room_id()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()

    return ip

ip = get_local_ip()

server_url = f"https://boarddrop-1.onrender.com/upload?room={room_id}"

generate_qr(server_url)

room_id = generate_room_id()


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

sio = socketio.Client()


upload_count = 0
DATABASE = os.path.join("database", "boarddrop.db")

app = ctk.CTk()
app.title("BoardDrop")
app.geometry("1200x700")
app.minsize(1000, 650)

# ---------------- OS Integration (Auto-Start & Tray) ----------------
AUTOSTART_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "BoardDrop"

def get_app_command():
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    else:
        return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

def check_autostart():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except WindowsError:
        return False

def toggle_autostart():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_ALL_ACCESS)
        if autostart_var.get() == 1:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_app_command())
        else:
            winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Failed to configure autostart: {e}")

def quit_app(icon=None, item=None):
    if icon:
        icon.stop()
    app.quit()
    os._exit(0)

def show_app(icon, item):
    icon.stop()
    app.after(0, app.deiconify)

def hide_window():
    app.withdraw()
    try:
        image = Image.open("qr/qr.png")
    except:
        image = Image.new('RGB', (64, 64), color=(59, 130, 246))

    menu = (item('Show Dashboard', show_app), item('Quit BoardDrop', quit_app))
    icon = pystray.Icon("BoardDrop", image, "BoardDrop (Listening for files...)", menu)
    threading.Thread(target=icon.run, daemon=True).start()

app.protocol("WM_DELETE_WINDOW", hide_window)

# ---------------- Header ----------------
header = ctk.CTkFrame(app, height=70)
header.pack(fill="x")
title = ctk.CTkLabel(header, text="📡 BoardDrop", font=("Arial", 28, "bold"))
title.pack(side="left", padx=20, pady=15)
status = ctk.CTkLabel(header, text="🔴 Offline", text_color="red", font=("Arial", 18))
status.pack(side="right", padx=20)

# ---------------- Main Layout ----------------
main = ctk.CTkFrame(app)
main.pack(fill="both", expand=True)

# ---------------- Sidebar ----------------
sidebar = ctk.CTkFrame(main, width=220)
sidebar.pack(side="left", fill="y", padx=10, pady=10)
ctk.CTkLabel(sidebar, text="MENU", font=("Arial", 22, "bold")).pack(pady=20)

# ---------------- Content Area ----------------
content_container = ctk.CTkFrame(main)
content_container.pack(side="left", fill="both", expand=True, padx=10, pady=10)

frames = {}

# --- PAGE 1: Dashboard ---
dashboard_frame = ctk.CTkFrame(content_container, fg_color="transparent")
frames["dashboard"] = dashboard_frame

ctk.CTkLabel(dashboard_frame, text="QR CODE", font=("Arial", 26, "bold")).pack(pady=20)

qr_box = ctk.CTkFrame(dashboard_frame, width=250, height=250)
qr_box.pack()
qr_box.pack_propagate(False)

try:
    qr_image = ctk.CTkImage(
        light_image=Image.open("qr/qr.png"),
        dark_image=Image.open("qr/qr.png"),
        size=(250,250)
    )
    ctk.CTkLabel(qr_box, image=qr_image, text="").pack(expand=True)
except Exception as e:
    ctk.CTkLabel(qr_box, text="QR Missing").pack(expand=True)

ctk.CTkLabel(dashboard_frame, text=f"Room ID : {room_id}", font=("Arial", 20)).pack(pady=15)

devices_label = ctk.CTkLabel(dashboard_frame, text="Connected Devices : 0", font=("Arial", 18))
devices_label.pack()

waiting_label = ctk.CTkLabel(dashboard_frame, text="Waiting for Upload...", text_color="orange", font=("Arial", 18))
waiting_label.pack(pady=10)

today_label = ctk.CTkLabel(dashboard_frame, text="Today's Uploads : 0", font=("Arial",18))
today_label.pack(pady=10)

recent = ctk.CTkTextbox(dashboard_frame, height=150)
recent.pack(fill="x", padx=30, pady=20)
recent.insert("end", "Recent Files\n\n")
recent.configure(state="disabled")

# --- PAGE 2: History ---
history_frame = ctk.CTkFrame(content_container, fg_color="transparent")
frames["history"] = history_frame
ctk.CTkLabel(history_frame, text="📁 Upload History", font=("Arial", 26, "bold")).pack(pady=20)

history_scroll = ctk.CTkScrollableFrame(history_frame)
history_scroll.pack(fill="both", expand=True, padx=30, pady=10)

def load_history():
    for widget in history_scroll.winfo_children():
        widget.destroy()
        
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT filename, upload_time FROM upload_history ORDER BY id DESC")
            records = cursor.fetchall()
            
            if not records:
                ctk.CTkLabel(history_scroll, text="No files uploaded yet.", font=("Arial", 16)).pack(pady=20)
                return

            for record in records:
                row = ctk.CTkFrame(history_scroll, fg_color=("gray80", "gray20"))
                row.pack(fill="x", pady=5, padx=5)
                ctk.CTkLabel(row, text=f"📄 {record[0]}", font=("Arial", 16)).pack(side="left", padx=15, pady=10)
                ctk.CTkLabel(row, text=record[1], font=("Arial", 12), text_color="gray").pack(side="right", padx=15, pady=10)
    except Exception as e:
        ctk.CTkLabel(history_scroll, text="Database not found or empty.", font=("Arial", 16)).pack(pady=20)

# --- PAGE 3: Settings ---
settings_frame = ctk.CTkFrame(content_container, fg_color="transparent")
frames["settings"] = settings_frame
ctk.CTkLabel(settings_frame, text="⚙ Settings", font=("Arial", 26, "bold")).pack(pady=20)

appearance_box = ctk.CTkFrame(settings_frame)
appearance_box.pack(fill="x", padx=30, pady=10)
ctk.CTkLabel(appearance_box, text="Appearance Mode", font=("Arial", 16)).pack(side="left", padx=20, pady=20)
theme_switch = ctk.CTkSegmentedButton(appearance_box, values=["System", "Dark", "Light"], command=ctk.set_appearance_mode)
theme_switch.set("Dark")
theme_switch.pack(side="right", padx=20, pady=20)

startup_box = ctk.CTkFrame(settings_frame)
startup_box.pack(fill="x", padx=30, pady=10)
ctk.CTkLabel(startup_box, text="Auto Start with Windows", font=("Arial", 16)).pack(side="left", padx=20, pady=20)
autostart_var = ctk.IntVar(value=1 if check_autostart() else 0)
startup_toggle = ctk.CTkSwitch(startup_box, text="", variable=autostart_var, command=toggle_autostart)
startup_toggle.pack(side="right", padx=20, pady=20)

# ---------------- Navigation Logic ----------------
def show_frame(frame_name):
    for frame in frames.values():
        frame.pack_forget()
    frames[frame_name].pack(fill="both", expand=True)
    if frame_name == "history":
        load_history()

ctk.CTkButton(sidebar, text="🏠 Dashboard", command=lambda: show_frame("dashboard")).pack(pady=10, padx=20, fill="x")
ctk.CTkButton(sidebar, text="📁 History", command=lambda: show_frame("history")).pack(pady=10, padx=20, fill="x")
ctk.CTkButton(sidebar, text="⚙ Settings", command=lambda: show_frame("settings")).pack(pady=10, padx=20, fill="x")
ctk.CTkButton(sidebar, text="❌ Exit", command=quit_app, fg_color="darkred", hover_color="red").pack(side="bottom", pady=20, padx=20, fill="x")

show_frame("dashboard")

# ---------------- Socket.IO Events ----------------
@sio.event
def connect():
    app.after(0, lambda: status.configure(text="🟢 Online", text_color="lightgreen"))
    sio.emit("sync_room_id", {"room_id": room_id})

@sio.event
def disconnect():
    app.after(0, lambda: status.configure(text="🔴 Offline", text_color="red"))

@sio.on("device_count")
def update_device_count(data):
    count = max(0, data["count"] - 1)
    app.after(0, lambda: devices_label.configure(text=f"Connected Devices : {count}"))

@sio.on("new_file")
def handle_new_file(data):
    global upload_count

    upload_count += 1
    filename = data["filename"]

    try:
        url = f"https://boarddrop-1.onrender.com/uploads/{filename}"

        os.makedirs("downloads", exist_ok=True)

        save_path = os.path.join("downloads", filename)

        r = requests.get(url, timeout=30)

        if r.status_code == 200:

            with open(save_path, "wb") as f:
                f.write(r.content)

            if os.name == "nt":
                os.startfile(os.path.abspath(save_path))

        else:
            print("Download Failed :", r.status_code)

    except Exception as e:
        print("Download Error :", e)

    def update_ui():
        today_label.configure(
            text=f"Today's Uploads : {upload_count}"
        )

        waiting_label.configure(
            text=f"Last upload : {filename}",
            text_color="lightgreen"
        )

        recent.configure(state="normal")
        recent.insert("end", f"📄 {filename}\n")
        recent.see("end")
        recent.configure(state="disabled")

    app.after(0, update_ui)

# ---------------- Threading Setup ----------------
def run_flask_server():
    """Runs the backend server silently in the background"""
    # use_reloader=False is REQUIRED when compiled into an EXE to prevent double-spawning
    flask_sio.run(flask_app, host="0.0.0.0", port=5000, use_reloader=False, debug=False)

def connect_to_server():
    while True:
        try:
            sio.connect("https://boarddrop-1.onrender.com")
            sio.wait()
        except Exception:
            app.after(0, lambda: status.configure(
                text="🔴 Offline",
                text_color="red"
            ))
            time.sleep(2)

if __name__ == "__main__":
    # 1. Start the Flask Backend
    threading.Thread(target=run_flask_server, daemon=True).start()
    
    # 2. Start the Socket Connection
    threading.Thread(target=connect_to_server, daemon=True).start()
    
    # 3. Launch the Desktop UI
    app.mainloop()