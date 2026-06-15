# -*- coding: utf-8 -*-
"""
疾控中心下发报告生成工具 - 打包脚本
使用：python build_exe.py
功能：1. 使用 PyInstaller 生成 exe   2. 将依赖的目录和文件复制到 dist 目录
"""
import os
import shutil
import subprocess
import sys

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
PYTHON_EXE = sys.executable
PYINSTALLER_CMD = os.path.join(os.path.dirname(PYTHON_EXE), "Scripts", "pyinstaller.exe")

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
    "疾控下发汇总报告模板.xlsx",
]


def run_pyinstaller():
    """执行 PyInstaller 打包"""
    print("=" * 60)
    print("开始执行 PyInstaller 打包...")
    print("=" * 60)

    cmd = [PYINSTALLER_CMD, "--clean", "--noconfirm", SPEC_FILE]
    print(f"执行命令：{' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise Exception(f"PyInstaller 打包失败，返回码：{result.returncode}")

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
