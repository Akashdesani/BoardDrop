# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import customtkinter

ctk_path = customtkinter.__path__[0]

datas = [
    ('templates', 'templates'),
    ('assets', 'assets'),
    (ctk_path, 'customtkinter'),
]

hiddenimports = (
    collect_submodules('flask_socketio') +
    collect_submodules('socketio') +
    collect_submodules('engineio') +
    [
        'requests',
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'customtkinter',
        'win11toast',
        'winsound',
        'plyer',
        'socketio.client',
        'engineio.client',
        'engineio.async_drivers.threading',
    ]
)

a = Analysis(
    ['desktop.py'],
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
    name='BoardDrop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon='assets/boarddrop.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BoardDrop',
)