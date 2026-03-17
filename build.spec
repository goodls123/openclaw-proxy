# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件
使用命令: pyinstaller build.spec --clean
"""

import os

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['main.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('assets/images/favicon.ico', 'assets/images'),
        ('assets/images/openclaw.png', 'assets/images'),
    ],
    hiddenimports=[
        'paramiko',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.simpledialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'matplotlib',
        'numpy',
        'pandas',
        'cv2',
        'IPython',
        'jupyter',
        'scipy',
        'sympy',
        'notebook',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='虾代理',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/images/favicon.ico',
    # DPI manifest - 支持高分屏
    manifest='dpi.manifest',
)
