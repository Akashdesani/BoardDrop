# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files
)

hiddenimports = []

hiddenimports += collect_submodules("socketio")
hiddenimports += collect_submodules("engineio")
hiddenimports += collect_submodules("flask_socketio")
hiddenimports += collect_submodules("eventlet")
hiddenimports += collect_submodules("dns")
hiddenimports += collect_submodules("requests")
hiddenimports += collect_submodules("urllib3")
hiddenimports += collect_submodules("PIL")
hiddenimports += collect_submodules("customtkinter")
hiddenimports += collect_submodules("pystray")
hiddenimports += collect_submodules("winotify")

datas = []

# Project folders
datas += [
    ("templates", "templates"),
    ("static", "static"),
    ("assets", "assets"),
    ("network", "network"),
    ("utils", "utils"),
    ("ui", "ui"),
]

# Package data
datas += collect_data_files("customtkinter")
datas += collect_data_files("PIL")

a = Analysis(
    ["desktop.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BoardDrop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/boarddrop.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BoardDrop",
)