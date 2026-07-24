import os
import sys
import time
import socket
import threading
import sqlite3
import winreg
import requests
import traceback
import ctypes
import math
import subprocess
from datetime import datetime
from pathlib import Path
from multiprocessing import Process, freeze_support

import tkinter.messagebox as tkmb  
from tkinter import Menu, simpledialog

from PIL import Image
import pystray
from pystray import MenuItem as item
import socketio
import winsound
from win11toast import toast
import customtkinter as ctk

# Custom modules
from ui.mode_selection import ModeSelection
from network.mode import get_mode
from network.online import get_upload_url as online_upload
from network.offline import get_upload_url as offline_upload
from utils.room import generate_room_id
from utils.qr_generator import generate_qr, QR_PATH

# Import the Flask app explicitly to run it from here
from app import app as flask_app, socketio as flask_sio

# ---------------- Visual Theme Constants ----------------
COLOR_BG_DARK = "#0F172A"       # Deep Slate Background
COLOR_SURFACE = "#1E293B"      # Card / Container Surface
COLOR_SURFACE_LIGHT = "#334155"# Lighter Card Accent
COLOR_ACCENT = "#3B82F6"       # Electric Blue Accent
COLOR_ACCENT_HOVER = "#2563EB" # Hover Blue
COLOR_SUCCESS = "#10B981"      # Emerald Green
COLOR_ONLINE = "#06B6D4"       # Cyan
COLOR_DANGER = "#EF4444"       # Red
COLOR_DANGER_HOVER = "#DC2626" # Darker Red
COLOR_TEXT_MAIN = "#F8FAFC"    # Bright Text
COLOR_TEXT_MUTED = "#94A3B8"   # Slate Gray Text

# ---------------- Helper Functions ----------------
def play_notification_sound():
    try:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except:
        pass

APP_ID = "BoardDrop.DesaniTechnology"

def show_notification(filename):
    try:
        download_file = str(Path.home() / "Downloads" / filename)
        download_folder = str(Path.home() / "Downloads")

        toast(
            title="📦 BoardDrop",
            body=f"{filename}\nReceived Successfully",
            app_id=APP_ID,
            icon=resource_path("assets/boarddrop.ico"),
            buttons=[
                {
                    "activationType": "protocol",
                    "content": "📄 Open File",
                    "arguments": f"file:///{download_file.replace(os.sep, '/')}"
                },
                {
                    "activationType": "protocol",
                    "content": "📂 Open Folder",
                    "arguments": f"file:///{download_folder.replace(os.sep, '/')}"
                }
            ]
        )
    except Exception as e:
        print(f"Notification error: {e}")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def run_flask_server():
    """Runs the backend server silently in the background"""
    flask_sio.run(
        flask_app,
        host="0.0.0.0",
        port=5000,
        use_reloader=False,
        debug=False,
        allow_unsafe_werkzeug=True
    )

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

# ---------------- File Explorer Utilities ----------------
EXT_MAP = {
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
    "Images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".ico"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "Audio": [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Executables": [".exe", ".msi", ".bat", ".cmd", ".sh", ".apk"]
}

CATEGORY_BY_EXT = {}
for category, exts in EXT_MAP.items():
    for ext in exts:
        CATEGORY_BY_EXT[ext] = category

CATEGORY_ICONS = {
    "Documents": "📄", "Images": "📁", "Videos": "🎥", 
    "Audio": "🎵", "Archives": "📦", "Executables": "⚙️", 
    "unknown": "📝"
}

def get_category(ext):
    return CATEGORY_BY_EXT.get(ext, "unknown")

def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    sizes = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    s = round(size_bytes / math.pow(1024, i), 2)
    return f"{s} {sizes[i]}"


# ---------------- Main Execution Block ----------------
if __name__ == "__main__":

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    freeze_support()

    # 1. Mode Selection
    selector = ModeSelection()
    selector.mainloop()

    try:
        selector.destroy()
    except Exception:
        pass
        
    if not hasattr(selector, 'selected_mode') or not selector.selected_mode:
        print("No mode selected. Exiting...")
        sys.exit(0)
        
    mode = selector.selected_mode

    # 2. Paths Setup
    APPDATA = os.path.join(os.getenv("LOCALAPPDATA"), "BoardDrop")
    QR_DIR = os.path.join(APPDATA, "qr")
    os.makedirs(QR_DIR, exist_ok=True)
    DOWNLOADS_FOLDER = Path.home() / "Downloads"
    os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

    # 3. Network & QR Config
    room_id = generate_room_id()

    if mode == "online":
        server_url = f"https://boarddrop-1.onrender.com/upload?mode=online&room={room_id}"
    else:
        from network.offline import get_local_ip
        ip = get_local_ip()
        server_url = f"http://{ip}:5000/upload?mode=offline"

    generate_qr(server_url)

    # 4. Start Background Server
    server_process = Process(target=run_flask_server)
    server_process.start()

    # 5. CustomTkinter UI Theme Setup
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    sio = socketio.Client()
    upload_count = 0
    running = True

    app = ctk.CTk(fg_color=COLOR_BG_DARK)
    app.iconbitmap(resource_path("assets/boarddrop.ico"))
    app.title("BoardDrop - Seamless Local & Cloud Transfer")
    app.geometry("1200x720")
    app.minsize(1050, 680)

    # Explorer State Variables
    current_files = []
    selected_filepath = None
    selected_row = None
    DISPLAY_LIMIT = 100

    def open_system_file(filepath):
        try:
            if os.path.exists(filepath):
                os.startfile(filepath)
            else:
                tkmb.showerror("Not Found", "File no longer exists.")
                fetch_downloads_data()
        except Exception as e:
            print(f"Error opening file: {e}")

    # Keyboard Shortcuts
    def dashboard_shortcut(event=None): show_frame("dashboard")
    def history_shortcut(event=None): show_frame("history")
    def settings_shortcut(event=None): show_frame("settings")
    def exit_shortcut(event=None): quit_app()

    def search_focus_shortcut(event=None):
        if frames["history"].winfo_ismapped():
            search_entry.focus_set()

    def refresh_shortcut(event=None):
        if frames["history"].winfo_ismapped():
            fetch_downloads_data()

    def delete_shortcut(event=None):
        if frames["history"].winfo_ismapped() and selected_filepath:
            delete_file(selected_filepath)

    def enter_shortcut(event=None):
        if frames["history"].winfo_ismapped() and selected_filepath:
            open_system_file(selected_filepath)

    def register_shortcuts():
        app.bind("<Control-d>", dashboard_shortcut)
        app.bind("<Control-D>", dashboard_shortcut)
        app.bind("<Control-h>", history_shortcut)
        app.bind("<Control-H>", history_shortcut)
        app.bind("<Control-s>", settings_shortcut)
        app.bind("<Control-S>", settings_shortcut)
        
        # Exit Shortcuts (Alt+X and Ctrl+Q)
        app.bind("<Alt-x>", exit_shortcut)
        app.bind("<Alt-X>", exit_shortcut)
        app.bind("<Control-q>", exit_shortcut)
        app.bind("<Control-Q>", exit_shortcut)

        app.bind("<Control-f>", search_focus_shortcut)
        app.bind("<Control-F>", search_focus_shortcut)
        app.bind("<F5>", refresh_shortcut)
        app.bind("<Delete>", delete_shortcut)
        app.bind("<Return>", enter_shortcut)

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
        global running
        running = False
        try:
            if sio.connected: sio.disconnect()
        except: pass
        try:
            if server_process and server_process.is_alive():
                server_process.terminate()
                server_process.join(timeout=2)
        except Exception as e: print(e)
        try:
            if icon: icon.stop()
        except: pass
        try:
            app.quit()
            app.destroy()
        except: pass
        os._exit(0)

    def show_app(icon, item):
        if app.winfo_exists():
            icon.stop()
            app.after(0, app.deiconify)

    def hide_window():
        app.withdraw()
        try:
            image = Image.open(QR_PATH)
        except:
            image = Image.new('RGB', (64, 64), color=(59, 130, 246))
        menu = pystray.Menu(item('Show Dashboard', show_app), item('Quit BoardDrop', quit_app))
        icon = pystray.Icon("BoardDrop", image, "BoardDrop (Listening for files...)", menu)
        threading.Thread(target=icon.run, daemon=True).start()

    app.protocol("WM_DELETE_WINDOW", quit_app)

    # ---------------- Top Header ----------------
    header = ctk.CTkFrame(app, height=75, fg_color=COLOR_SURFACE, corner_radius=0)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)

    title_box = ctk.CTkFrame(header, fg_color="transparent")
    title_box.pack(side="left", padx=25, pady=15)

    title = ctk.CTkLabel(title_box, text="📡 BoardDrop", font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"), text_color=COLOR_TEXT_MAIN)
    title.pack(side="left")
    

    status_bg = COLOR_ONLINE if mode == "online" else COLOR_ACCENT
    status_text = "🌍 Online Mode" if mode == "online" else "⚡ Offline Mode"

    status_pill = ctk.CTkFrame(header, fg_color=COLOR_SURFACE_LIGHT, corner_radius=20)
    status_pill.pack(side="right", padx=25)

    status = ctk.CTkLabel(
        status_pill, 
        text=status_text, 
        text_color=status_bg, 
        font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
    )
    status.pack(padx=16, pady=8)

    # ---------------- Layout Container ----------------
    main = ctk.CTkFrame(app, fg_color="transparent")
    main.pack(fill="both", expand=True, padx=15, pady=15)

    # ---------------- Sidebar Navigation ----------------
    sidebar = ctk.CTkFrame(main, width=230, fg_color=COLOR_SURFACE, corner_radius=12)
    sidebar.pack(side="left", fill="y", padx=(0, 10))
    sidebar.pack_propagate(False)

    nav_title = ctk.CTkLabel(sidebar, text="MAIN MENU", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MUTED)
    nav_title.pack(anchor="w", padx=20, pady=(20, 10))

    nav_buttons = {}

    def set_active_nav(active_name):
        for name, btn in nav_buttons.items():
            if name == active_name:
                btn.configure(fg_color=COLOR_ACCENT, text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_TEXT_MUTED)

    content_container = ctk.CTkFrame(main, fg_color="transparent")
    content_container.pack(side="left", fill="both", expand=True)

    frames = {}

    # ==========================================================
    # --- PAGE 1: Dashboard ---
    # ==========================================================
    dashboard_frame = ctk.CTkFrame(content_container, fg_color="transparent")
    frames["dashboard"] = dashboard_frame

    # Quick Stats Row
    stats_row = ctk.CTkFrame(dashboard_frame, fg_color="transparent")
    stats_row.pack(fill="x", pady=(0, 15))

    # Stat Card 1
    card1 = ctk.CTkFrame(stats_row, fg_color=COLOR_SURFACE, corner_radius=12, height=90)
    card1.pack(side="left", fill="x", expand=True, padx=(0, 10))
    card1.pack_propagate(False)
    ctk.CTkLabel(card1, text="CONNECTION MODE", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=15, pady=(12, 0))
    info_text = f"Room: {room_id}" if mode == "online" else f"IP: {get_local_ip()}"
    ctk.CTkLabel(card1, text=info_text, font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=15, pady=(4, 0))

    # Stat Card 2
    card2 = ctk.CTkFrame(stats_row, fg_color=COLOR_SURFACE, corner_radius=12, height=90)
    card2.pack(side="left", fill="x", expand=True, padx=5)
    card2.pack_propagate(False)
    ctk.CTkLabel(card2, text="STATUS", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=15, pady=(12, 0))
    devices_label = ctk.CTkLabel(card2, text="Ready to Receive", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_SUCCESS)
    devices_label.pack(anchor="w", padx=15, pady=(4, 0))

    # Stat Card 3
    card3 = ctk.CTkFrame(stats_row, fg_color=COLOR_SURFACE, corner_radius=12, height=90)
    card3.pack(side="left", fill="x", expand=True, padx=(10, 0))
    card3.pack_propagate(False)
    ctk.CTkLabel(card3, text="TODAY'S UPLOADS", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=15, pady=(12, 0))
    today_label = ctk.CTkLabel(card3, text="0 Files", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_ACCENT)
    today_label.pack(anchor="w", padx=15, pady=(4, 0))

    # Main Grid (QR & Recent Activity)
    grid_container = ctk.CTkFrame(dashboard_frame, fg_color="transparent")
    grid_container.pack(fill="both", expand=True)

    # QR Card Panel
    qr_panel = ctk.CTkFrame(grid_container, fg_color=COLOR_SURFACE, corner_radius=12, width=320)
    qr_panel.pack(side="left", fill="y", padx=(0, 15))
    qr_panel.pack_propagate(False)

    ctk.CTkLabel(qr_panel, text="Scan to Connect", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(pady=(20, 10))

    qr_box = ctk.CTkFrame(qr_panel, width=230, height=230, fg_color=COLOR_SURFACE_LIGHT, corner_radius=10)
    qr_box.pack(pady=10)
    qr_box.pack_propagate(False)

    try:
        qr_image = ctk.CTkImage(light_image=Image.open(QR_PATH), dark_image=Image.open(QR_PATH), size=(220, 220))
        ctk.CTkLabel(qr_box, image=qr_image, text="").pack(expand=True)
    except Exception:
        ctk.CTkLabel(qr_box, text="QR Unavailable", text_color=COLOR_TEXT_MUTED).pack(expand=True)

    waiting_label = ctk.CTkLabel(qr_panel, text="Waiting for device...", font=ctk.CTkFont(size=13), text_color=COLOR_TEXT_MUTED)
    waiting_label.pack(pady=10)

    # Activity Panel
    activity_panel = ctk.CTkFrame(grid_container, fg_color=COLOR_SURFACE, corner_radius=12)
    activity_panel.pack(side="left", fill="both", expand=True)

    ctk.CTkLabel(activity_panel, text="⚡ Recent Transfer Activity", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(anchor="w", padx=20, pady=20)

    recent = ctk.CTkTextbox(
        activity_panel, 
        fg_color=COLOR_BG_DARK, 
        text_color=COLOR_TEXT_MAIN, 
        font=ctk.CTkFont(family="Consolas", size=13),
        corner_radius=8,
        border_width=1,
        border_color=COLOR_SURFACE_LIGHT
    )
    recent.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    recent.insert("end", "System initialized. Ready for incoming transfers...\n\n")
    recent.configure(state="disabled")

    ctk.CTkLabel(dashboard_frame, text="© Akash Desani • BoardDrop v2.4.1", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).pack(side="bottom", pady=5)
    

    # ==========================================================
    # --- PAGE 2: File Explorer (History) ---
    # ==========================================================
    history_frame = ctk.CTkFrame(content_container, fg_color="transparent")
    frames["history"] = history_frame

    # Controls Bar
    ctrl_bar = ctk.CTkFrame(history_frame, fg_color=COLOR_SURFACE, corner_radius=12, height=60)
    ctrl_bar.pack(fill="x", pady=(0, 15))

    search_var = ctk.StringVar()
    search_entry = ctk.CTkEntry(
        ctrl_bar, 
        placeholder_text="🔍 Search files... (Ctrl+F)", 
        textvariable=search_var, 
        width=280,
        height=38,
        fg_color=COLOR_BG_DARK,
        border_color=COLOR_SURFACE_LIGHT,
        corner_radius=8
    )
    search_entry.pack(side="left", padx=15, pady=10)
    search_entry.bind("<KeyRelease>", lambda e: render_explorer_ui())

    filter_var = ctk.StringVar(value="All Files")
    filter_menu = ctk.CTkOptionMenu(
        ctrl_bar, 
        variable=filter_var, 
        values=["All Files"] + list(EXT_MAP.keys()), 
        width=140, 
        height=38,
        fg_color=COLOR_SURFACE_LIGHT,
        button_color=COLOR_ACCENT,
        button_hover_color=COLOR_ACCENT_HOVER,
        command=lambda e: render_explorer_ui()
    )
    filter_menu.pack(side="left", padx=(0, 10), pady=10)

    sort_var = ctk.StringVar(value="Newest First")
    sort_menu = ctk.CTkOptionMenu(
        ctrl_bar, 
        variable=sort_var, 
        values=["Newest First", "Name A-Z", "Name Z-A", "Largest File", "Smallest File"], 
        width=150, 
        height=38,
        fg_color=COLOR_SURFACE_LIGHT,
        button_color=COLOR_ACCENT,
        button_hover_color=COLOR_ACCENT_HOVER,
        command=lambda e: render_explorer_ui()
    )
    sort_menu.pack(side="left", pady=10)

    refresh_btn = ctk.CTkButton(
        ctrl_bar, 
        text="Refresh", 
        width=100, 
        height=38, 
        fg_color=COLOR_SURFACE_LIGHT, 
        hover_color=COLOR_ACCENT,
        command=lambda: fetch_downloads_data()
    )
    refresh_btn.pack(side="right", padx=15, pady=10)

    # Table Header Row
    header_row = ctk.CTkFrame(history_frame, height=35, fg_color=COLOR_SURFACE, corner_radius=6)
    header_row.pack(fill="x", pady=(0, 8))
    
    ctk.CTkLabel(header_row, text="", width=40).pack(side="left") 
    ctk.CTkLabel(header_row, text="FILE NAME", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MUTED, anchor="w").pack(side="left", fill="x", expand=True, padx=5)
    ctk.CTkLabel(header_row, text="DATE MODIFIED", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MUTED, width=150, anchor="e").pack(side="right", padx=15)
    ctk.CTkLabel(header_row, text="SIZE", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MUTED, width=100, anchor="e").pack(side="right", padx=15)

    # Scrollable Explorer List
    history_scroll = ctk.CTkScrollableFrame(history_frame, fg_color="transparent")
    history_scroll.pack(fill="both", expand=True)

    # Explorer Logic Methods
    def select_row(filepath, row_frame):
        global selected_filepath, selected_row
        if selected_row and selected_row.winfo_exists():
            selected_row.configure(fg_color=COLOR_SURFACE)
        
        selected_filepath = filepath
        selected_row = row_frame
        
        if selected_row and selected_row.winfo_exists():
            selected_row.configure(fg_color=COLOR_SURFACE_LIGHT)

    def copy_path(filepath):
        app.clipboard_clear()
        app.clipboard_append(os.path.abspath(filepath))

    def rename_file(filepath):
        old_name = os.path.basename(filepath)
        new_name = simpledialog.askstring("Rename File", "Enter new filename:", initialvalue=old_name, parent=app)
        if new_name and new_name != old_name:
            try:
                new_path = os.path.join(os.path.dirname(filepath), new_name)
                os.rename(filepath, new_path)
                fetch_downloads_data()
            except Exception as e:
                tkmb.showerror("Error", f"Failed to rename file:\n{e}")

    def delete_file(filepath):
        filename = os.path.basename(filepath)
        confirm = tkmb.askyesno("Delete File", f"Are you sure you want to permanently delete:\n{filename}?")
        if confirm:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                global current_files, selected_filepath
                current_files = [f for f in current_files if f["path"] != filepath]
                if selected_filepath == filepath:
                    selected_filepath = None
                render_explorer_ui()
            except Exception as e:
                tkmb.showerror("Error", f"Failed to delete file:\n{e}")

    def show_context_menu(event, filepath, row):
        select_row(filepath, row)
        menu = Menu(app, tearoff=0)
        menu.add_command(label="📂 Open File", command=lambda: open_system_file(filepath))
        menu.add_command(label="📁 Open Folder Location", command=lambda: subprocess.Popen(f'explorer /select,"{os.path.abspath(filepath)}"'))
        menu.add_separator()
        menu.add_command(label="✏️ Rename", command=lambda: rename_file(filepath))
        menu.add_command(label="📋 Copy Full Path", command=lambda: copy_path(filepath))
        menu.add_separator()
        menu.add_command(label="🗑 Delete", command=lambda: delete_file(filepath))
        menu.tk_popup(event.x_root, event.y_root)

    def fetch_downloads_data():
        """ OPTIMIZATION: Runs in a background thread to prevent UI freeze """
        def scan_task():
            temp_files = []
            if DOWNLOADS_FOLDER.exists():
                try:
                    for entry in os.scandir(DOWNLOADS_FOLDER):
                        if entry.is_file():
                            stat = entry.stat()
                            ext = Path(entry.name).suffix.lower()
                            category = get_category(ext)
                            temp_files.append({
                                "name": entry.name,
                                "path": entry.path,
                                "size": stat.st_size,
                                "mtime": stat.st_mtime,
                                "category": category,
                                "ext": ext
                            })
                except Exception as e:
                    print(f"Error scanning folder: {e}")
            
            temp_files.sort(key=lambda x: x["mtime"], reverse=True)
            
            def update_ui():
                global current_files
                current_files = temp_files
                if frames["history"].winfo_ismapped():
                    render_explorer_ui()

            app.after(0, update_ui)
        
        threading.Thread(target=scan_task, daemon=True).start()

    def render_explorer_ui():
        """ Fast rendering: Limits widgets and processes sorting before rendering """
        for widget in history_scroll.winfo_children():
            widget.destroy()

        search_q = search_var.get().lower()
        active_filter = filter_var.get()
        active_sort = sort_var.get()

        filtered_files = []
        for f in current_files:
            if search_q in f["name"].lower():
                if active_filter == "All Files" or f["category"] == active_filter:
                    filtered_files.append(f)

        if active_sort == "Newest First":
            filtered_files.sort(key=lambda x: x["mtime"], reverse=True)
        elif active_sort == "Name A-Z":
            filtered_files.sort(key=lambda x: x["name"].lower())
        elif active_sort == "Name Z-A":
            filtered_files.sort(key=lambda x: x["name"].lower(), reverse=True)
        elif active_sort == "Largest File":
            filtered_files.sort(key=lambda x: x["size"], reverse=True)
        elif active_sort == "Smallest File":
            filtered_files.sort(key=lambda x: x["size"])

        if not filtered_files:
            ctk.CTkLabel(
                history_scroll, 
                text="No matching files found.", 
                font=ctk.CTkFont(size=15, italic=True), 
                text_color=COLOR_TEXT_MUTED
            ).pack(pady=50)
            return

        total_files = len(filtered_files)
        displayed_files = filtered_files[:DISPLAY_LIMIT]

        for f in displayed_files:
            icon_emoji = CATEGORY_ICONS.get(f["category"], "📝")
            date_str = datetime.fromtimestamp(f["mtime"]).strftime("%Y-%m-%d %H:%M")
            size_str = format_size(f["size"])
            filepath = f["path"]

            row = ctk.CTkFrame(history_scroll, fg_color=COLOR_SURFACE, corner_radius=8, height=44)
            row.pack(fill="x", pady=3)
            row.pack_propagate(False)

            icon_lbl = ctk.CTkLabel(row, text=icon_emoji, font=ctk.CTkFont(size=18), width=40)
            icon_lbl.pack(side="left", padx=5)

            name_lbl = ctk.CTkLabel(row, text=f["name"], font=ctk.CTkFont(size=13, weight="normal"), text_color=COLOR_TEXT_MAIN, anchor="w")
            name_lbl.pack(side="left", fill="x", expand=True, padx=5)

            date_lbl = ctk.CTkLabel(row, text=date_str, font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED, width=150, anchor="e")
            date_lbl.pack(side="right", padx=15)

            size_lbl = ctk.CTkLabel(row, text=size_str, font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED, width=100, anchor="e")
            size_lbl.pack(side="right", padx=15)

            def bind_events(widget, fp=filepath, r=row):
                widget.bind("<Button-1>", lambda e: select_row(fp, r))
                widget.bind("<Double-Button-1>", lambda e: open_system_file(fp))
                widget.bind("<Button-3>", lambda e: show_context_menu(e, fp, r))

            bind_events(row)
            bind_events(icon_lbl)
            bind_events(name_lbl)
            bind_events(date_lbl)
            bind_events(size_lbl)
            
            if filepath == selected_filepath:
                select_row(filepath, row)

        if total_files > DISPLAY_LIMIT:
            ctk.CTkLabel(
                history_scroll, 
                text=f"+ {total_files - DISPLAY_LIMIT} more files... (Use search filter)", 
                font=ctk.CTkFont(size=12, italic=True), 
                text_color=COLOR_TEXT_MUTED
            ).pack(pady=10)


    # ==========================================================
    # --- PAGE 3: Settings ---
    # ==========================================================
    settings_frame = ctk.CTkFrame(content_container, fg_color="transparent")
    frames["settings"] = settings_frame

    ctk.CTkLabel(settings_frame, text="⚙️ Preferences & Configuration", font=ctk.CTkFont(size=22, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(anchor="w", pady=(0, 20))

    # Setting Box 1
    appearance_box = ctk.CTkFrame(settings_frame, fg_color=COLOR_SURFACE, corner_radius=12)
    appearance_box.pack(fill="x", pady=10)
    
    ctk.CTkLabel(appearance_box, text="Appearance Theme", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(side="left", padx=20, pady=20)
    theme_switch = ctk.CTkSegmentedButton(
        appearance_box, 
        values=["System", "Dark", "Light"], 
        command=ctk.set_appearance_mode,
        selected_color=COLOR_ACCENT,
        selected_hover_color=COLOR_ACCENT_HOVER
    )
    theme_switch.set("Dark")
    theme_switch.pack(side="right", padx=20, pady=20)

    # Setting Box 2
    startup_box = ctk.CTkFrame(settings_frame, fg_color=COLOR_SURFACE, corner_radius=12)
    startup_box.pack(fill="x", pady=10)
    
    ctk.CTkLabel(startup_box, text="Start automatically with Windows", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(side="left", padx=20, pady=20)
    autostart_var = ctk.IntVar(value=1 if check_autostart() else 0)
    startup_toggle = ctk.CTkSwitch(
        startup_box, 
        text="", 
        variable=autostart_var, 
        command=toggle_autostart,
        progress_color=COLOR_ACCENT
    )
    startup_toggle.pack(side="right", padx=20, pady=20)

    # ---------------- Navigation Setup ----------------
    def create_nav_button(parent, text, frame_key):
        btn = ctk.CTkButton(
            parent, 
            text=text, 
            anchor="w",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            text_color=COLOR_TEXT_MUTED,
            hover_color=COLOR_SURFACE_LIGHT,
            corner_radius=8,
            command=lambda: show_frame(frame_key)
        )
        btn.pack(fill="x", padx=12, pady=4)
        return btn

    nav_buttons["dashboard"] = create_nav_button(sidebar, "🏠 Dashboard", "dashboard")
    nav_buttons["history"] = create_nav_button(sidebar, "📁 File Explorer", "history")
    nav_buttons["settings"] = create_nav_button(sidebar, "⚙️ Settings", "settings")

    # Clean Exit Button at Bottom of Sidebar
    exit_btn = ctk.CTkButton(
        sidebar, 
        text="❌ Exit App", 
        anchor="w",
        height=42,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=COLOR_DANGER, 
        text_color="#FFFFFF",
        hover_color=COLOR_DANGER_HOVER,
        corner_radius=8,
        command=quit_app
    )
    exit_btn.pack(side="bottom", fill="x", padx=12, pady=15)

    def show_frame(frame_name):
        for frame in frames.values():
            frame.pack_forget()
        frames[frame_name].pack(fill="both", expand=True)
        set_active_nav(frame_name)
        
        if frame_name == "history":
            fetch_downloads_data()

    show_frame("dashboard")

    # ---------------- SocketIO Handlers ----------------
    @sio.event
    def connect():
        print("Connected to server.")
        def update_ui():
            try:
                sio.emit("join", {"room": room_id, "mode": mode})
            except Exception as e:
                print("Join Error:", e)
        app.after(0, update_ui)

    @sio.on("new_file")
    def handle_new_file(data):
        filename = os.path.basename(data["filename"])

        def download_task():
            global upload_count
            try:
                if mode == "online":
                    url = f"https://boarddrop-1.onrender.com/uploads/{filename}"
                else:
                    ip = get_local_ip()
                    url = f"http://{ip}:5000/uploads/{filename}"

                save_path = DOWNLOADS_FOLDER / filename
                r = requests.get(url, stream=True, timeout=30)
                
                if r.status_code == 200:
                    with open(save_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk: f.write(chunk)
                    
                    if os.name == "nt":
                        try:
                            play_notification_sound()
                            show_notification(filename)
                        except: pass

                    def update_ui():
                        global upload_count
                        upload_count += 1
                        today_label.configure(text=f"{upload_count} Files")
                        waiting_label.configure(text=f"Last: {filename}", text_color=COLOR_SUCCESS)
                        
                        recent.configure(state="normal")
                        recent.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] 📄 Received: {filename}\n")
                        recent.see("end")
                        recent.configure(state="disabled")
                        
                        if save_path.exists():
                            stat = save_path.stat()
                            ext = save_path.suffix.lower()
                            current_files.insert(0, {
                                "name": save_path.name,
                                "path": str(save_path),
                                "size": stat.st_size,
                                "mtime": stat.st_mtime,
                                "category": get_category(ext),
                                "ext": ext
                            })
                            
                        if frames["history"].winfo_ismapped():
                            render_explorer_ui()

                    app.after(0, update_ui)
                else:
                    print("Download Failed :", r.status_code)

            except Exception as e:
                print("Download Error :", e)

        threading.Thread(target=download_task, daemon=True).start()

    # ---------------- Connection Management ----------------
    def connect_sio():
        while running:
            try:
                if not sio.connected:
                    if mode == "online":
                        sio.connect("https://boarddrop-1.onrender.com")
                    else:
                        ip = get_local_ip()
                        sio.connect(f"http://{ip}:5000")
            except Exception as e:
                pass
            time.sleep(3)

    threading.Thread(target=connect_sio, daemon=True).start()
    register_shortcuts()
    fetch_downloads_data()

    app.mainloop()