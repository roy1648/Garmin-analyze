# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_all

datas = []
binaries = []
hiddenimports = []

# Collect everything from streamlit
tmp_datas, tmp_binaries, tmp_hiddenimports = collect_all('streamlit')
datas.extend(tmp_datas)
binaries.extend(tmp_binaries)
hiddenimports.extend(tmp_hiddenimports)

# Add our own package files (the src/garmin_tcx_ai directory containing ui_streamlit.py)
datas.append(('../src/garmin_tcx_ai', 'src/garmin_tcx_ai'))

block_cipher = None

a = Analysis(
    ['../src/garmin_tcx_ai/ui_exe_launcher.py'],
    pathex=['../src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='garmin-tcx-ai-ui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='garmin-tcx-ai-ui',
)
