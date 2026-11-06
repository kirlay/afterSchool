# -*- mode: python ; coding: utf-8 -*-
#
# 打包说明：
#   * 用 32 位 Python 3.8 + PyInstaller 5.13.2 打包（见 build_x86.ps1），
#     产物兼容 Windows 7 SP1 32/64 位与 Windows 10/11。
#   * 默认单文件（onefile）；设置环境变量 ASCHOOL_ONEDIR=1 时出多文件（onedir）。
#   * 图标和屏幕 logo 是外置文件（xb.ico、logo.png），不打包进 exe；
#     这里的 icon 只用于写入 exe 自身的资源图标，供资源管理器显示。

import os

ONEDIR = os.environ.get("ASCHOOL_ONEDIR") == "1"
APP_NAME = "放学情况"

a = Analysis(
    ['over.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    [] if ONEDIR else a.binaries,
    [] if ONEDIR else a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    exclude_binaries=ONEDIR,
    icon=['xb.ico'],
)

if ONEDIR:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )
