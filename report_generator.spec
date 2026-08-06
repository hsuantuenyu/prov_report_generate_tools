# -*- mode: python ; coding: utf-8 -*-
"""跨平台 PyInstaller 打包配置
Windows: 生成 exe（含版本信息）
macOS (Intel x86_64 / Apple Silicon arm64): 生成对应架构的 .app
"""
import sys
import platform

# Apple Silicon (M1/M2/M3) 默认 arm64；Intel Mac 默认 x86_64
IS_ARM = platform.machine().lower() in ('arm64', 'aarch64')
_arch = 'arm64' if IS_ARM else 'x86_64'

a = Analysis(
    ['report_generator.py'],
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
    name='疾控中心下发报告生成工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    # macOS: 指定目标架构（M1/M2 arm64 / Intel x86_64）
    target_arch=_arch,
    codesign_identity=None,
    entitlements_file=None,
    # Windows 独有：版本信息文件（macOS 不支持）
    **({'version': 'file_version_info.txt'} if sys.platform == 'win32' else {}),
)

# macOS: 生成 .app 应用包
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='疾控中心下发报告生成工具.app',
        icon=None,
        bundle_identifier=None,
        # 显式指定 Info.plist 中的架构信息
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSArchitecturePriority': [_arch],
            'MinimumSystemVersion': '12.0' if IS_ARM else '10.15',
        },
    )
