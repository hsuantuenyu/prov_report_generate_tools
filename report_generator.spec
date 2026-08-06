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
TARGET_ARCH = os.environ.get('TARGET_ARCH', None)
if TARGET_ARCH == 'universal2':
    PYI_TARGET_ARCH = 'universal2'
elif TARGET_ARCH in ('x86_64', 'arm64'):
    PYI_TARGET_ARCH = TARGET_ARCH
else:
    PYI_TARGET_ARCH = None  # 使用当前系统架构

# 读取 macOS 部署目标版本 (默认 11.0，支持 11-14)
MACOS_MIN_VERSION = os.environ.get('MACOSX_DEPLOYMENT_TARGET', '11.0')
if sys.platform == 'darwin':
    os.environ.setdefault('MACOSX_DEPLOYMENT_TARGET', MACOS_MIN_VERSION)

# ===== 数据文件列表 =====
# 将需要打包的数据文件添加到 datas 中
# 格式: (源文件路径, 打包后相对路径)
DATAS = [
    ('prov_report.db', '.'),  # 将数据库文件打包到 .app 的资源根目录
    # 如果有其他数据文件或目录，可以继续添加：
    # ('config.json', '.'),
    # ('assets/', 'assets/'),
    # ('prov_generate_data.sql','.'),
]

# ===== 隐藏导入（按需添加）=====
HIDDEN_IMPORTS = [
    # 如果使用 tkinter，可能需要：
    # 'tkinter',
    # 如果使用 pandas/duckdb，可能需要：
    # 'duckdb',
]

# ===== Analysis =====
a = Analysis(
    ['report_generator.py'],
    pathex=[],  # 添加额外的模块搜索路径
    binaries=[],  # 二进制依赖（如 .so, .dylib）
    datas=DATAS,  # 数据文件
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'tkinter.test',
        'unittest',
        'test',
    ],
    noarchive=False,  # True 可以将代码打包为 .pyz 归档
)

# ===== PYZ (编译后的 Python 字节码) =====
pyz = PYZ(a.pure)

# ===== EXE 可执行文件 =====
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
    console=False,  # 不显示终端窗口（GUI应用）
    disable_windowed_traceback=False,
    argv_emulation=False,
    # macOS: 设置目标架构
    target_arch=PYI_TARGET_ARCH if sys.platform == 'darwin' else None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows 独有配置
    **({'version': 'file_version_info.txt'} if sys.platform == 'win32' else {}),
)

# ===== macOS: BUNDLE 生成 .app 应用包 =====
if sys.platform == 'darwin':
    # Info.plist 配置
    # 重要：应用程序的 Bundle Identifier 建议设置，避免冲突
    BUNDLE_IDENTIFIER = os.environ.get('BUNDLE_IDENTIFIER', 'com.yourcompany.report-generator')
    
    info_plist = {
        # 最低支持 macOS 版本
        'LSMinimumSystemVersion': MACOS_MIN_VERSION,
        # 应用显示名称 (显示在 Dock 和菜单栏)
        'CFBundleDisplayName': '疾控中心下发报告生成工具',
        # 应用短名称
        'CFBundleName': '疾控中心下发报告生成工具',
        # 内部标识符 (重要!)
        'CFBundleIdentifier': BUNDLE_IDENTIFIER,
        # 版本号
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        # 人类可读的版权信息
        'NSHumanReadableCopyright': 'Copyright © 2024-2025',
        # 标记为高分辨率就绪 (Retina 屏幕)
        'NSHighResolutionCapable': True,
        # 应用类别 (生产力工具)
        'LSApplicationCategoryType': 'public.app-category.productivity',
        # 是否支持后台运行 (对于不需要后台的应用，设为 False)
        'LSBackgroundOnly': False,
        # 应用使用场景 (可选)
        'LSUIElement': False,
        # 配合 sys._MEIPASS 使用的资源目录提示
        # (实际使用由 Python 代码通过 sys._MEIPASS 处理)
    }

    app = BUNDLE(
        exe,
        name='疾控中心下发报告生成工具.app',
        icon=None,  # 如果需要图标，改为 'icon.icns'
        bundle_identifier=BUNDLE_IDENTIFIER,
        info_plist=info_plist,
    )