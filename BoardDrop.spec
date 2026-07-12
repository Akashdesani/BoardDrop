# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import customtkinter
import os

# Automatically locate where pip installed customtkinter so PyInstaller can bundle its themes
ctk_path = customtkinter.__path__[0]

a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        (ctk_path, 'customtkinter'),
    ],
    # Force PyInstaller to include hidden background libraries
    hiddenimports=[
        'engineio.async_drivers.threading', 
        'flask_socketio', 
        'pystray._win32'
    ],
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
    a.binaries,
    a.datas,
    [],
    name='BoardDrop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, # Compresses the final output size
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Hides the black terminal window (Runs as purely a GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE' # Optional: Add an icon path here later like 'icons/logo.ico'
)