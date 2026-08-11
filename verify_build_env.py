# -*- coding: utf-8 -*-
"""构建环境验证脚本（跨平台: Windows / macOS）
供 GitHub Actions 调用，避免在 YAML 中写多行 Python 导致转义问题。
用法：python verify_build_env.py
返回码：0 全部通过，1 有失败项
"""
import os
import sys
import platform

# Windows GitHub Actions Runner 默认 stdout 编码是 cp1252，无法输出中文
# 强制 UTF-8 输出，避免 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def _check(desc, cond, detail=""):
    tag = "OK" if cond else "FAIL"
    line = f"  [{tag}] {desc}"
    if detail:
        line += f" — {detail}"
    print(line)
    return cond


def main():
    all_pass = True
    py_arch = platform.machine()
    print(f"=== 构建环境验证 ({sys.platform} / {py_arch}) ===")

    # 1. 语法检查
    print("\n1. 语法检查")
    try:
        import py_compile
        py_compile.compile("report_generator.py", doraise=True)
        all_pass = _check("report_generator.py", True) and all_pass
    except Exception as e:
        all_pass = _check("report_generator.py", False, str(e)[:80]) and all_pass

    try:
        import py_compile
        py_compile.compile("report_generator.spec", doraise=True)
        all_pass = _check("report_generator.spec", True) and all_pass
    except Exception as e:
        all_pass = _check("report_generator.spec", False, str(e)[:80]) and all_pass

    # 2. 依赖模块
    print("\n2. 依赖导入 & 版本")
    deps = [("duckdb", True), ("pandas", True), ("openpyxl", True),
            ("tkcalendar", False), ("PyInstaller", True)]
    dep_versions = {}
    for mod_name, need_ver in deps:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "n/a") if need_ver else "OK"
            dep_versions[mod_name] = ver
            all_pass = _check(f"import {mod_name}", True,
                              f"v{ver}" if need_ver else "") and all_pass
        except Exception as e:
            all_pass = _check(f"import {mod_name}", False, str(e)[:60]) and all_pass

    # 3. tkinter / Tcl
    print("\n3. Tcl/Tk (tkinter)")
    try:
        import tkinter
        tv = getattr(tkinter, "TkVersion", "?")
        tcl_patch = tkinter.Tcl().eval("info patchlevel")
        all_pass = _check("tkinter", True,
                          f"Tk={tv}, Tcl={tcl_patch}") and all_pass
    except Exception as e:
        all_pass = _check("tkinter", False, str(e)[:60]) and all_pass

    # 4. 资源文件
    print("\n4. 资源文件")
    files = [
        "prov_report.db",
        "prov_generate_data.sql",
        "疾控下发汇总报告模板.xlsx",
        "版本日志.txt",
    ]
    # Windows 额外检查 file_version_info.txt
    if sys.platform == "win32":
        files.append("file_version_info.txt")

    for f in files:
        exists = os.path.isfile(f)
        all_pass = _check(f"文件: {f}", exists) and all_pass

    # 5. 附加目录（非必需，存在即可）
    print("\n5. 附加目录 (非必需)")
    dirs = ["0.疾控中心_doris查询语句", "1.doris查询结果模板"]
    for d in dirs:
        exists = os.path.isdir(d)
        _check(f"目录: {d}", exists, "" if exists else "跳过复制")

    # 汇总
    print("\n" + "=" * 50)
    if all_pass:
        print("全部通过 ✅  可以开始构建")
        return 0
    else:
        print("存在失败项 ❌  请修复后再构建")
        return 1


if __name__ == "__main__":
    sys.exit(main())
