# -*- mode: python ; coding: utf-8 -*-
#
# 打包说明：
#   * 用 32 位 Python 3.8 + PyInstaller 5.13.2 打包（见 build_x86.ps1），
#     产物兼容 Windows 7 SP1 32/64 位与 Windows 10/11。
#   * 只出单文件（onefile）；单文件运行时会把自身解压到系统临时目录，目标机 %TEMP% 必须可用。
#   * 图标和屏幕 logo 是外置文件（xb.ico、logo.png），不打包进 exe；
#     这里的 icon 只用于写入 exe 自身的资源图标，供资源管理器显示。

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
    a.binaries,
    a.datas,
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
    icon=['xb.ico'],
)
