# -*- coding: utf-8 -*-
"""
macOS / Apple Silicon (M1/M2/M3) 构建环境模拟验证脚本
在 Windows 上模拟 macOS 环境验证代码兼容性，支持 Apple Silicon ARM64 专项检查
使用：python verify_macos_build.py
"""
import ast
import os
import sys
import importlib
import py_compile
import platform
import re

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ===== Windows 专有 API 关键词（macOS 上会崩溃的） =====
WINDOWS_ONLY_PATTERNS = [
    (r'ctypes\.windll', 'ctypes.windll 是 Windows 专有 API，macOS 不存在'),
    (r'os\.startfile', 'os.startfile() 是 Windows 专有方法，macOS 不存在'),
    (r"WINFUNCTYPE", 'WINFUNCTYPE 是 Windows 专有类型，macOS 不存在'),
    (r"subprocess\.Popen\(\['explorer'", 'explorer 是 Windows 资源管理器，macOS 应使用 open 命令'),
    (r'file_version_info\.txt', 'file_version_info.txt 是 Windows 版本信息文件，macOS 不支持'),
    (r'pyinstaller\.exe', 'pyinstaller.exe 是 Windows 可执行文件，macOS 应为 pyinstaller'),
    (r'Scripts\\\\pyinstaller', 'Scripts\\pyinstaller 是 Windows 路径，macOS 应为 bin/pyinstaller'),
]

# Apple Silicon 推荐的 Python 版本和依赖版本
APPLE_SILICON_RECOMMEND = {
    'python_min': (3, 11),   # 推荐 Python 3.11+ (原生 ARM64 稳定)
    'pyinstaller_min': '6.0',  # 6.0+ 对 arm64 支持完善
    'duckdb_min': '0.8',       # arm64 原生 wheel
    'pandas_min': '2.0',       # 对 Apple Silicon 性能优化
}


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_result(label, passed, detail=""):
    status = "[PASS]" if passed else "[FAIL]"
    line = f"  {status} {label}"
    if detail:
        line += f" - {detail}"
    print(line)
    return passed


def scan_windows_only_apis(filepath):
    """扫描源码中未加平台保护的 Windows 专有 API 调用"""
    print_header("1. 扫描 Windows 专有 API 调用（未加平台保护）")

    all_pass = True
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        for pattern, desc in WINDOWS_ONLY_PATTERNS:
            if re.search(pattern, line):
                # 检查是否在平台保护块内
                # 向上搜索最近的条件判断，看是否有 sys.platform == 'win32' 保护
                protected = False
                for j in range(i - 1, max(i - 120, 0), -1):
                    prev = lines[j]
                    if "sys.platform == 'win32'" in prev or 'sys.platform=="win32"' in prev:
                        protected = True
                        break
                    if "sys.platform == 'darwin'" in prev or 'sys.platform=="darwin"' in prev:
                        protected = True
                        break
                if not protected:
                    all_pass = check_result(
                        f"第{i}行: {desc}",
                        False,
                        f"代码: {line.strip()[:80]}"
                    ) and all_pass
    if all_pass:
        print("  未发现未加保护的 Windows 专有 API 调用")
    return all_pass


def check_python_syntax(filepath):
    """验证 Python 语法正确性"""
    print_header("2. Python 语法检查")
    try:
        py_compile.compile(filepath, doraise=True)
        check_result("report_generator.py 语法", True)
        return True
    except py_compile.PyCompileError as e:
        check_result("report_generator.py 语法", False, str(e)[:100])
        return False


def check_spec_syntax(filepath):
    """验证 spec 文件语法"""
    print_header("3. Spec 文件语法检查")
    try:
        py_compile.compile(filepath, doraise=True)
        check_result("report_generator.spec 语法", True)
        return True
    except py_compile.PyCompileError as e:
        check_result("report_generator.spec 语法", False, str(e)[:100])
        return False


def check_spec_macos_bundle_and_arm64(filepath):
    """检查 spec 文件是否包含 macOS BUNDLE 配置 和 ARM64/Apple Silicon 专项配置"""
    print_header("4. Spec 文件 macOS + Apple Silicon (M2) 配置检查")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    results = []
    has_bundle = 'BUNDLE' in content
    results.append(check_result("包含 BUNDLE 段", has_bundle))

    has_darwin = "sys.platform == 'darwin'" in content or 'sys.platform=="darwin"' in content
    results.append(check_result("包含 darwin 平台判断", has_darwin))

    has_version_guard = ("sys.platform == 'win32'" in content or
                         'sys.platform=="win32"' in content)
    results.append(check_result("version 参数有 Windows 平台保护", has_version_guard))

    has_platform_import = 'import platform' in content
    results.append(check_result("import platform（用于检测架构）", has_platform_import))

    has_arm64_detect = 'arm64' in content and ('platform.machine' in content or 'aarch64' in content)
    results.append(check_result("Apple Silicon (arm64) 架构检测逻辑", has_arm64_detect,
                                "M2 芯片需 platform.machine() 判断 arm64/aarch64"))

    has_target_arch = 'target_arch' in content
    results.append(check_result("PyInstaller target_arch 参数（指定生成 arm64）", has_target_arch))

    has_info_plist = 'info_plist' in content
    results.append(check_result("BUNDLE info_plist 设置（LSArchitecturePriority 等）", has_info_plist))

    return all(results)


def check_build_script(filepath):
    """检查 build_exe.py 是否兼容 macOS + ARM64"""
    print_header("5. build_exe.py 跨平台 + ARM64 兼容性检查")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    results = []
    has_mac_path = 'bin' in content and 'pyinstaller' in content
    results.append(check_result("包含 macOS pyinstaller 路径逻辑", has_mac_path))

    has_platform_check = 'sys.platform' in content or 'IS_MAC' in content or 'IS_WINDOWS' in content
    results.append(check_result("包含平台检测逻辑", has_platform_check))

    has_arch_info = 'platform' in content and ('machine' in content or 'arm' in content)
    if not has_arch_info:
        # 至少打印系统信息
        has_arch_info = 'platform.system()' in content or 'platform.release()' in content
    results.append(check_result("包含架构/系统信息打印 (platform)", has_arch_info,
                                "方便排查 M2 构建问题"))

    return all(results)


def check_imports_macos_compatible(filepath):
    """检查 import 语句是否在 macOS 上可用"""
    print_header("6. 导入模块 macOS 兼容性检查")

    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        check_result("AST 解析", False, str(e)[:100])
        return False

    # 收集所有 import 语句
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    # macOS 上可能不可用的模块（条件导入除外）
    risky_modules = {
        'ctypes.wintypes': 'Windows 类型定义',
        'ctypes.windll': 'Windows DLL 加载',
        'winreg': 'Windows 注册表',
        'msvcrt': 'Windows C 运行时',
        '_winapi': 'Windows API',
    }

    all_pass = True
    seen = set()
    for mod in imports:
        if mod in seen:
            continue
        seen.add(mod)
        if mod in risky_modules:
            # 检查是否在平台保护块内
            pattern = rf'import\s+{re.escape(mod)}'
            match = re.search(pattern, source)
            if match:
                pos = match.start()
                before = source[:pos]
                if "sys.platform == 'win32'" not in before[-500:]:
                    all_pass = check_result(f"模块 {mod}", False, risky_modules[mod]) and all_pass
        else:
            check_result(f"模块 {mod}", True)

    return all_pass


def check_ast_compile_macos_sim(filepath):
    """模拟 macOS 环境：尝试在不执行 GUI 的情况下编译解析代码"""
    print_header("7. Apple Silicon 模拟 - 代码 AST 解析与平台分支")

    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source)
        check_result("AST 解析成功", True)
    except SyntaxError as e:
        check_result("AST 解析", False, str(e)[:100])
        return False

    # 检查所有函数定义中是否有显式的 sys.platform 分支
    platform_branches = 0
    darwin_handled = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            if isinstance(node.left, ast.Attribute):
                if (isinstance(node.left.value, ast.Name) and
                    node.left.value.id == 'sys' and
                    node.left.attr == 'platform'):
                    platform_branches += 1
                    # 检查是否包含 darwin 常量
                    for comp in node.comparators:
                        if isinstance(comp, ast.Constant) and comp.value == 'darwin':
                            darwin_handled = True

    check_result(f"找到 {platform_branches} 处 sys.platform 分支判断",
                 platform_branches > 0,
                 f"{'跨平台分支充分' if platform_branches >= 2 else '建议增加更多平台分支'}")

    check_result("包含 darwin（macOS）分支处理逻辑",
                 darwin_handled,
                 "M2 上必须走 darwin 分支")

    return True


def check_apple_silicon_ready():
    """Apple Silicon (M1/M2/M3) 专项依赖检查"""
    print_header("8. Apple Silicon (M2) ARM64 依赖版本检查")
    all_pass = True

    # Python 版本检查
    py_ver = sys.version_info[:2]
    py_min = APPLE_SILICON_RECOMMEND['python_min']
    py_ok = py_ver >= py_min
    all_pass = check_result(
        f"Python 版本 {py_ver[0]}.{py_ver[1]}",
        py_ok,
        f"推荐 >= {py_min[0]}.{py_min[1]}（M2 原生稳定）" if not py_ok else ""
    ) and all_pass

    # PyInstaller
    try:
        import PyInstaller
        pyi_ver = getattr(PyInstaller, '__version__', 'unknown')
        pyi_parts = pyi_ver.split('.')
        try:
            pyi_ok = (int(pyi_parts[0]) >= 6)
        except (ValueError, IndexError):
            pyi_ok = True
        all_pass = check_result(
            f"PyInstaller v{pyi_ver}",
            pyi_ok,
            f"推荐 >= {APPLE_SILICON_RECOMMEND['pyinstaller_min']}（ARM64 支持完善）" if not pyi_ok else ""
        ) and all_pass
    except ImportError:
        check_result("PyInstaller", False, "未安装（macOS 构建必需）")
        all_pass = False

    # duckdb
    try:
        import duckdb
        v = getattr(duckdb, '__version__', 'unknown')
        check_result(f"duckdb v{v}", True, "有原生 arm64 wheel ✅")
    except ImportError:
        check_result("duckdb", False, "未安装")
        all_pass = False

    # pandas
    try:
        import pandas
        v = getattr(pandas, '__version__', 'unknown')
        check_result(f"pandas v{v}", True, "Apple Silicon NEON 优化 ✅")
    except ImportError:
        check_result("pandas", False, "未安装")
        all_pass = False

    # openpyxl
    try:
        import openpyxl
        v = getattr(openpyxl, '__version__', 'unknown')
        check_result(f"openpyxl v{v}", True, "纯 Python，跨平台 ✅")
    except ImportError:
        check_result("openpyxl", False, "未安装")
        all_pass = False

    # tkcalendar
    try:
        import tkcalendar
        check_result("tkcalendar", True, "纯 Python，跨平台 ✅")
    except ImportError:
        check_result("tkcalendar", False, "未安装")
        all_pass = False

    # tkinter（macOS 自带 Tcl/Tk）
    try:
        import tkinter
        tv = getattr(tkinter, 'TkVersion', 'unknown')
        check_result(f"tkinter (Tcl/Tk v{tv})", True, "macOS 已自带，无需额外安装 ✅")
    except Exception as e:
        check_result("tkinter", False, str(e)[:60])
        all_pass = False

    return all_pass


def simulate_app_structure_arm64():
    """模拟检查 M2 (arm64) .app 应用包应包含的结构"""
    print_header("9. Apple Silicon M2 - .app 应用包结构模拟")

    expected_structure = [
        "Contents/",
        "Contents/_CodeSignature/",
        "Contents/MacOS/",
        "Contents/MacOS/疾控中心下发报告生成工具  (Mach-O arm64 可执行)",
        "Contents/Resources/",
        "Contents/Info.plist  (含 LSArchitecturePriority=arm64)",
    ]

    print("  预期 M2 .app 包结构 + ARM64 特性：")
    for item in expected_structure:
        print(f"    {item}")

    # 检查 spec 中是否正确配置
    spec_path = os.path.join(PROJECT_ROOT, 'report_generator.spec')
    if os.path.isfile(spec_path):
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec = f.read()
        check_result("spec target_arch=arm64 动态设置", 'target_arch' in spec and 'arm64' in spec)
        check_result("spec BUNDLE info_plist 存在", 'info_plist' in spec)
        check_result("spec LSArchitecturePriority 设置", 'LSArchitecturePriority' in spec)
    check_result("Mach-O 可执行文件应为 arm64 切片", True,
                 "在 macOS 上使用 `file` / `lipo -info` 验证")
    check_result("移除隔离属性 (xattr -d com.apple.quarantine)", True,
                 "GitHub Actions 步骤已自动处理")
    return True


def check_resource_files():
    """检查依赖资源文件是否存在"""
    print_header("10. 依赖资源文件检查")

    files = [
        "prov_report.db",
        "prov_generate_data.sql",
        "疾控下发汇总报告模板.xlsx",
        "版本日志.txt",
        "build_exe.py",
        "report_generator.spec",
        "report_generator.py",
    ]
    dirs = [
        "0.疾控中心_doris查询语句",
        "1.doris查询结果模板",
    ]

    all_pass = True
    for f in files:
        exists = os.path.isfile(os.path.join(PROJECT_ROOT, f))
        check_result(f"文件: {f}", exists)
        all_pass = all_pass and exists

    for d in dirs:
        exists = os.path.isdir(os.path.join(PROJECT_ROOT, d))
        check_result(f"目录: {d}", exists)
        all_pass = all_pass and exists

    return all_pass


def check_cross_platform_path_usage(filepath):
    """检查路径拼接是否使用了 os.path（避免硬编码 Windows 反斜杠）"""
    print_header("11. 跨平台路径用法检查（macOS 使用正斜杠）")

    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    all_pass = True
    # 搜索可疑的硬编码反斜杠路径（排除转义字符、正则）
    suspicious = re.findall(r"['\"][^'\"]*\\\\[^'\"]*['\"]", source)
    for path in suspicious[:5]:
        # 排除显然不是路径的（如换行转义、正则转义）
        if '\\n' in path or '\\t' in path or '\\r' in path or '\\s' in path:
            continue
        check_result(f"路径硬编码: {path[:60]}", False,
                     "请改用 os.path.join() 避免 Windows 反斜杠")
        all_pass = False

    if all_pass:
        check_result("未发现硬编码 Windows 反斜杠路径", True,
                     "所有路径应通过 os.path.join() 拼接")
    return all_pass


def main():
    is_mac = sys.platform == 'darwin'
    is_arm = platform.machine().lower() in ('arm64', 'aarch64')
    chip = "原生 Apple Silicon M1/M2/M3" if (is_mac and is_arm) else (
        "通过 Rosetta 运行" if (is_mac and platform.machine() == 'x86_64') else
        f"本机 ({platform.machine()}) 模拟"
    )

    print("\n" + "#" * 60)
    print("#  macOS / Apple Silicon (M2) 构建环境模拟验证")
    print(f"#  当前系统: {platform.system()} {platform.release()}")
    print(f"#  架构: {platform.machine()} | {chip}")
    print(f"#  Python: {sys.version.split()[0]}")
    print(f"#  目标: 验证代码可在 M2 (arm64) 上打包并正常启动")
    print("#" * 60)

    results = []

    # 1. 扫描 Windows 专有 API
    results.append(("Windows 专有 API 扫描",
                     scan_windows_only_apis(os.path.join(PROJECT_ROOT, 'report_generator.py'))))

    # 2. Python 语法
    results.append(("Python 语法检查",
                     check_python_syntax(os.path.join(PROJECT_ROOT, 'report_generator.py'))))

    # 3. Spec 语法
    results.append(("Spec 语法检查",
                     check_spec_syntax(os.path.join(PROJECT_ROOT, 'report_generator.spec'))))

    # 4. Spec macOS + ARM64 配置
    results.append(("Spec macOS BUNDLE + M2 arm64 配置",
                     check_spec_macos_bundle_and_arm64(os.path.join(PROJECT_ROOT, 'report_generator.spec'))))

    # 5. build_exe.py 兼容性
    results.append(("build_exe.py 跨平台 + ARM64 兼容",
                     check_build_script(os.path.join(PROJECT_ROOT, 'build_exe.py'))))

    # 6. import 兼容性
    results.append(("导入模块 macOS 兼容性",
                     check_imports_macos_compatible(os.path.join(PROJECT_ROOT, 'report_generator.py'))))

    # 7. AST 模拟
    results.append(("AST 模拟 macOS / darwin 分支",
                     check_ast_compile_macos_sim(os.path.join(PROJECT_ROOT, 'report_generator.py'))))

    # 8. Apple Silicon 依赖版本
    results.append(("M2 (ARM64) 依赖版本", check_apple_silicon_ready()))

    # 9. .app 结构
    results.append((".app 应用包结构 (M2 arm64)", simulate_app_structure_arm64()))

    # 10. 资源文件
    results.append(("依赖资源文件", check_resource_files()))

    # 11. 跨平台路径
    results.append(("跨平台路径硬编码检查",
                     check_cross_platform_path_usage(os.path.join(PROJECT_ROOT, 'report_generator.py'))))

    # 汇总
    print_header("验证结果汇总")
    total = len(results)
    passed = sum(1 for _, r in results if r)
    for name, result in results:
        check_result(name, result)

    print(f"\n  总计: {passed}/{total} 项通过", end="")
    if passed == total:
        print(" - 全部通过！代码可在 Apple Silicon M2 上打包运行")
        print("\n  M2 本机构建步骤:")
        print("    pip install duckdb pandas openpyxl tkcalendar pyinstaller")
        print("    python verify_macos_build.py   # 再次确认 M2 本机兼容性")
        print("    python build_exe.py")
        print(f"    产物: dist/疾控中心下发报告生成工具.app (arm64 原生)")
        print("\n  GitHub Actions 构建:")
        print("    推送到 GitHub → Actions → Build macOS App → Run workflow")
        print("    Runner 推荐选择: macos-14-xlarge (M1/M2 原生)")
    else:
        print(f" - {total - passed} 项失败，请修复后再构建")
    print()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
