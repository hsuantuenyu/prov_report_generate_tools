# -*- coding: utf-8 -*-
"""
疾控中心下发报告生成工具 - 打包脚本
使用：python build_exe.py
功能：1. 使用 PyInstaller 打包（Windows 生成 exe，macOS 生成 .app）
      2. 将依赖的目录和文件复制到 dist 目录
"""
import os
import platform
import shutil
import subprocess
import sys

# 平台检测
IS_WINDOWS = sys.platform == 'win32'
IS_MAC = sys.platform == 'darwin'

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
PYTHON_EXE = sys.executable

# 根据平台确定 PyInstaller 可执行文件路径
if IS_WINDOWS:
    PYINSTALLER_CMD = os.path.join(os.path.dirname(PYTHON_EXE), "Scripts", "pyinstaller.exe")
else:
    # macOS / Linux: 使用 bin/pyinstaller，找不到则回退到 PATH 中的 pyinstaller
    _candidate = os.path.join(os.path.dirname(PYTHON_EXE), "bin", "pyinstaller")
    PYINSTALLER_CMD = _candidate if os.path.isfile(_candidate) else "pyinstaller"

# PyInstaller spec 文件
SPEC_FILE = os.path.join(PROJECT_ROOT, "report_generator.spec")

# 需要复制到 dist 的目录和文件
DIRS_TO_COPY = [
    "0.疾控中心_doris查询语句",
    "1.doris查询结果模板",
]
FILES_TO_COPY = [
    "prov_report.db",
    "prov_generate_data.sql",
    "emergency_warning.sql",
    "emergency_warning_all.sql",
    "疾控下发汇总报告模板.xlsx",
    "应急处下发汇总报告_模板.xlsx",
    "应急处下发汇总报告_模板_全部.xlsx",
    "版本日志.txt"
]


def run_pyinstaller():
    """执行 PyInstaller 打包"""
    print("=" * 60)
    print(f"开始执行 PyInstaller 打包...")
    print(f"操作系统：{platform.system()} {platform.release()}")
    machine = platform.machine()
    arch_label = machine
    if sys.platform == 'darwin':
        if machine.lower() in ('arm64', 'aarch64'):
            arch_label = f"{machine} (Apple Silicon M1/M2/M3 原生)"
        elif machine == 'x86_64':
            arch_label = f"{machine} (Intel / Rosetta)"
    print(f"CPU 架构：{arch_label}")
    print(f"Python：{sys.version.split()[0]} ({machine})")
    print(f"PyInstaller：{PYINSTALLER_CMD}")
    if sys.platform == 'darwin' and machine.lower() in ('arm64', 'aarch64'):
        print(f"目标产物：原生 arm64 .app 应用包（M2 兼容，无需 Rosetta）")
    print("=" * 60)

    cmd = [PYINSTALLER_CMD, "--clean", "--noconfirm", SPEC_FILE]
    print(f"执行命令：{' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise Exception(f"PyInstaller 打包失败，返回码：{result.returncode}")

    # macOS 构建完成后，自动移除隔离属性（方便分发）
    if sys.platform == 'darwin':
        app_name = '疾控中心下发报告生成工具.app'
        app_path = os.path.join(DIST_DIR, app_name)
        if os.path.isdir(app_path):
            try:
                subprocess.run(['xattr', '-dr', 'com.apple.quarantine', app_path],
                               capture_output=True, timeout=30)
                print("\n 已移除 macOS 隔离属性 com.apple.quarantine")
                print(" 用户双击即可打开 .app，无需右键")
            except Exception:
                pass

    print("\n PyInstaller 打包完成！\n")


def copy_to_dist():
    """将依赖目录和文件复制到 dist 目录"""
    print("=" * 60)
    print("复制依赖文件到 dist 目录...")
    print("=" * 60)

    # 确保 dist 目录存在
    os.makedirs(DIST_DIR, exist_ok=True)

    # 复制目录
    for dir_name in DIRS_TO_COPY:
        src = os.path.join(PROJECT_ROOT, dir_name)
        dst = os.path.join(DIST_DIR, dir_name)
        if os.path.isdir(src):
            # 清理旧目录再复制
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f" [OK] 目录：{dir_name}")
        else:
            print(f" [!] 目录不存在：{dir_name}")

    # 复制文件
    for file_name in FILES_TO_COPY:
        src = os.path.join(PROJECT_ROOT, file_name)
        dst = os.path.join(DIST_DIR, file_name)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            print(f" [OK] 文件：{file_name}")
        else:
            print(f" [!] 文件不存在：{file_name}")

    print("\n 文件复制完成！\n")


def show_result():
    """显示 dist 目录中的内容"""
    print("=" * 60)
    print("dist 目录内容：")
    print("=" * 60)
    if os.path.isdir(DIST_DIR):
        for item in sorted(os.listdir(DIST_DIR)):
            item_path = os.path.join(DIST_DIR, item)
            size = ""
            if os.path.isfile(item_path):
                size_bytes = os.path.getsize(item_path)
                if size_bytes > 1024 * 1024:
                    size = f" ({size_bytes / 1024 / 1024:.1f} MB)"
                elif size_bytes > 1024:
                    size = f" ({size_bytes / 1024:.1f} KB)"
            elif os.path.isdir(item_path) and item.endswith('.app'):
                size = " (macOS 应用)"
                # macOS: 尝试读取可执行文件架构信息
                bin_path = os.path.join(item_path, "Contents", "MacOS", item[:-4])
                if os.path.isfile(bin_path):
                    try:
                        res = subprocess.run(['lipo', '-info', bin_path],
                                             capture_output=True, text=True, timeout=10)
                        arch_info = res.stdout.strip()
                        if 'Non-fat' in arch_info:
                            if 'arm64' in arch_info:
                                size = " (Apple Silicon arm64 原生)"
                            elif 'x86_64' in arch_info:
                                size = " (Intel x86_64)"
                        elif 'arm64' in arch_info and 'x86_64' in arch_info:
                            size = " (Universal2: arm64 + x86_64)"
                    except Exception:
                        pass
            print(f"  - {item}{size}")
    print("\n" + "=" * 60)
    print(f"产物路径：{DIST_DIR}")
    print("=" * 60)


def main():
    try:
        run_pyinstaller()
        copy_to_dist()
        show_result()
        print("\n 打包全部完成！")
    except Exception as e:
        print(f"\n 打包失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
