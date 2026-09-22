# packaging/scan2connect.spec
# -*- mode: python ; coding: utf-8 -*-
#
# onedir build. Run from the repo root: pyinstaller packaging/scan2connect.spec

from pathlib import Path

repo_root = Path(SPECPATH).parent

block_cipher = None

a = Analysis(
    [str(repo_root / 'scan2connect' / '__main__.py')],
    pathex=[str(repo_root)],
    binaries=[],
    datas=[
        (str(repo_root / 'scan2connect' / 'assets' / 'app_icon.ico'), 'scan2connect/assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineQuick',
        'PySide6.QtQuick',
        'PySide6.QtQuick3D',
        'PySide6.QtQuickWidgets',
        'PySide6.QtQml',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic',
        'PySide6.Qt3DAnimation',
        'PySide6.Qt3DExtras',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Drop Qt translation files (*.qm) — not used, and the biggest chunk of
# per-locale bloat in a PySide6 build.
a.datas = [entry for entry in a.datas if not entry[0].endswith('.qm')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Scan2Connect',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(repo_root / 'scan2connect' / 'assets' / 'app_icon.ico'),
    version=str(repo_root / 'packaging' / 'version_info.txt'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Scan2Connect',
)
