# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件 (macOS)
使用命令: pyinstaller build-macos.spec --clean

支持架构:
  - x86_64: Intel Mac
  - arm64: Apple Silicon (M1/M2/M3)

通过环境变量 TARGET_ARCH 指定目标架构
"""

import os
import sys

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(SPEC))

# 目标架构 (从环境变量获取，默认为当前架构)
target_arch = os.environ.get('TARGET_ARCH', None)

# 产物名称
app_name = 'xia_proxy_macos'
if target_arch:
    app_name = f'xia_proxy_macos-{target_arch}'

a = Analysis(
    ['main.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('resources/images/favicon.ico', 'resources/images'),
        ('resources/images/openclaw.png', 'resources/images'),
        ('resources/images/pc.png', 'resources/images'),
        ('resources/images/add.png', 'resources/images'),
        ('resources/images/run.png', 'resources/images'),
        ('resources/images/stop.png', 'resources/images'),
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
        # Windows 特定模块
        'win32api',
        'win32con',
        'win32event',
        'pywintypes',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

# macOS 单文件可执行
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # macOS 上启用 strip 减小体积
    upx=False,   # macOS 上 UPX 可能有问题，禁用
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=target_arch,  # 支持交叉编译
    codesign_identity=None,
    entitlements_file=None,
)

# macOS App Bundle (可选，如果需要 .app 格式)
# app = BUNDLE(
#     exe,
#     name=f'{app_name}.app',
#     icon='resources/images/favicon.ico',
#     bundle_identifier='com.openclaw.proxy',
#     info_plist={
#         'CFBundleName': '虾代理',
#         'CFBundleDisplayName': '虾代理',
#         'CFBundleIdentifier': 'com.openclaw.proxy',
#         'CFBundleVersion': '1.0.0',
#         'CFBundleShortVersionString': '1.0.0',
#         'NSHighResolutionCapable': True,
#         'LSMinimumSystemVersion': '10.15.0',
#     }
# )
