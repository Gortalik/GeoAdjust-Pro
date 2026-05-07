"""PyInstaller spec файл для сборки .exe"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/geoadjust/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/geoadjust/resources', 'resources'),
    ],
    hiddenimports=[
        'scipy.sparse.csgraph',
        'scipy.linalg.cython_blas',
        'scipy.linalg.cython_lapack',
        'sksparse.cholmod',
        'PyQt5.sip',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'pandas._libs',
        'openpyxl',
        'striprtf',
        'networkx',
        'loguru',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 
        'unittest', 
        'matplotlib', 
        'jupyter',
        'notebook',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GeoAdjustPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # True для логов в dev, False для release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
