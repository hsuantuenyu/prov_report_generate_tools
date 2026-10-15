# -*- mode: python ; coding: utf-8 -*-
"""跨平台 PyInstaller 打包配置
Windows: 生成 exe（含版本信息）
macOS:   生成 .app 应用包 (兼容 macOS 11+)
"""
import sys
import os
import platform

# ===== macOS 兼容性配置 =====
# 通过环境变量控制目标架构: x86_64 / arm64 / universal2
# 注意：当目标架构与当前系统架构相同时，不显式设置 target_arch，
# 让 PyInstaller 自动使用当前架构。显式设置会触发对单架构 .so 文件
# （如 numpy 的 _multiarray_tests.so）的架构转换处理，导致
# "is not a fat binary" 错误。
_TARGET_ARCH_ENV = os.environ.get('TARGET_ARCH', None)
_CURRENT_ARCH = platform.machine().lower()  # arm64 / x86_64 / aarch64

if _TARGET_ARCH_ENV == 'universal2':
    # universal2 需要特殊处理，PyInstaller 会尝试构建通用二进制
    PYI_TARGET_ARCH = 'universal2'
elif _TARGET_ARCH_ENV in ('x86_64', 'arm64') and _TARGET_ARCH_ENV != _CURRENT_ARCH:
    # 仅当目标架构与当前系统架构不同时才显式设置（跨架构构建）
    PYI_TARGET_ARCH = _TARGET_ARCH_ENV
else:
    # 目标架构未指定或与当前架构相同：使用 None 让 PyInstaller 自动处理
    PYI_TARGET_ARCH = None

# 读取 macOS 部署目标版本 (默认 11.0，支持 11-14)
MACOS_MIN_VERSION = os.environ.get('MACOSX_DEPLOYMENT_TARGET', '11.0')
if sys.platform == 'darwin':
    os.environ.setdefault('MACOSX_DEPLOYMENT_TARGET', MACOS_MIN_VERSION)

a = Analysis(
    ['report_generator.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 将资源文件打包到 .app/exe 内部，避免移动后找不到
        ('prov_report.db', '.'),
        ('prov_generate_data.sql', '.'),
        ('emergency_warning.sql', '.'),
        ('emergency_warning_all.sql', '.'),
        ('疾控下发汇总报告模板.xlsx', '.'),
        ('应急处下发汇总报告_模板.xlsx', '.'),
        ('应急处下发汇总报告_模板_全部.xlsx', '.'),
        ('版本日志.txt', '.'),
    ],
    hiddenimports=[
        # macOS 上 tkinter 有时打包不进去，显式声明作为双保险
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.simpledialog',
        'tkinter.constants',
        'tkinter.dialog',
        '_tkinter',
        'tkcalendar',
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
    # macOS: 设置目标架构以支持通用二进制/指定架构构建
    target_arch=PYI_TARGET_ARCH if sys.platform == 'darwin' else None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows 独有：版本信息文件（macOS 不支持）
    **({'version': 'file_version_info.txt'} if sys.platform == 'win32' else {}),
)

# macOS: 生成 .app 应用包，配置最低系统版本
if sys.platform == 'darwin':
    # Info.plist 配置 - 声明最低 macOS 版本 (从 MACOSX_DEPLOYMENT_TARGET 读取)
    info_plist = {
        # 最低支持 macOS 版本 (11.0-14.0，由环境变量控制)
        'LSMinimumSystemVersion': MACOS_MIN_VERSION,
        # 应用显示名称
        'CFBundleDisplayName': '疾控中心下发报告生成工具',
        # 包名称
        'CFBundleName': '疾控中心下发报告生成工具',
        # 人类可读的版权信息
        'NSHumanReadableCopyright': 'Copyright © 2024',
        # 标记为高分辨率就绪
        'NSHighResolutionCapable': True,
        # 应用类别
        'LSApplicationCategoryType': 'public.app-category.productivity',
        # 关键：声明主类为 NSApplication，确保 macOS 正确初始化 GUI 应用
        # 缺少此项时，窗口标题栏按钮（关闭/最小化/最大化）可能不显示
        'NSPrincipalClass': 'NSApplication',
        # 标记为普通 GUI 应用（非后台/菜单栏应用），确保显示 Dock 图标和窗口装饰
        'LSBackgroundOnly': False,
    }

    app = BUNDLE(
        exe,
        name='疾控中心下发报告生成工具.app',
        icon=None,
        bundle_identifier=None,
        # 注入 Info.plist 配置（最低版本由 MACOSX_DEPLOYMENT_TARGET 控制）
        info_plist=info_plist,
    )
