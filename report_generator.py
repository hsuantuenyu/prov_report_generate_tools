import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import duckdb
import pandas as pd
import os
import re
import json
import sys
import shutil
import threading
import warnings
from datetime import datetime
from copy import copy
from tkcalendar import Calendar

# 忽略 pandas 的 DBAPI2 警告
warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')


VERSION = "V1.15"
BUILD_DATE = "2026-10-30"

# 业务处室配置
# 字段说明：
#   name             界面下拉框显示名称
#   table_flag       prov_table_list 中过滤表范围的标志字段
#   template         数据导出默认模板文件
#   has_national_flag 是否有省标/国标区分（仅预警处为 True）
#   sql_file         数据加工使用的整体 SQL 文件（不做语句拼接）
#   sql_variant      导出 SQL 复用的处室版本，缺省为自身 key
#   visible          是否在界面下拉框中显示
#   report_prefix    导出文件名前缀（预警处除外，其前缀随国标/全部切换）
#   thresholds        数据加工达标率阈值（%），可在界面调整并持久化保存：
#                     real-实时表  hour-2小时表  other-T+0表  association-关联达标率
DEPT_CONFIG = {
    "early_warning": {
        "name": "预警处",
        "table_flag": "early_warning",
        "template": "疾控下发汇总报告模板.xlsx",
        "has_national_flag": True,  # 只有预警处有省标/国标区分
        "sql_file": "prov_generate_data.sql",
        "visible": True,
        "thresholds": {"real": 90, "hour": 100, "other": 100, "association": 90},
        "export_sheets": [
            '地市(州)', '机构汇总', '时效性明细', '必填字段完整性',
            '重要建议填字段完整性', '条件必填字段完整性',
            '第二批次更新字段明细', '关联关系明细',
            '业务主键唯一率', '主诉明细', '现病史明细'
        ]
    },
    "emergency_warning": {
        "name": "应急处(11张表)",
        "table_flag": "emergency_warning",
        "template": "应急处下发汇总报告_模板.xlsx",
        "has_national_flag": False,
        "sql_file": "emergency_warning.sql",
        "visible": True,
        "report_prefix": "应急处下发汇总报告(省标表11张表)_质控日期：",
        "thresholds": {"real": 90, "hour": 100, "other": 100, "association": 90},
        "export_sheets": [
            '地市(州)', '机构汇总', '时效性明细', '必填字段完整性',
            '重要建议填字段完整性', '条件必填字段完整性',
            '第二批次更新字段明细', '关联关系明细',
            '主诉明细', '现病史明细'
        ]
    },
    "emergency_warning_all": {
        "name": "应急处(41张表)",
        "table_flag": "enable_status",
        "template": "应急处下发汇总报告_模板_全部.xlsx",
        "has_national_flag": False,
        "sql_file": "emergency_warning_all.sql",
        # 机构汇总、全部关联关系等导出 SQL 复用应急处版本（按应急处逻辑计算）
        "sql_variant": "emergency_warning",
        "visible": True,
        "report_prefix": "应急处下发汇总报告(省标表41张表)_质控日期：",
        "thresholds": {"real": 90, "hour": 100, "other": 98, "association": 90},
        # 模板复制自疾控模板（共 10 个 Sheet，无"业务主键唯一率"），Sheet 与应急处(11张表)一致
        "export_sheets": [
            '地市(州)', '机构汇总', '时效性明细', '必填字段完整性',
            '重要建议填字段完整性', '条件必填字段完整性',
            '第二批次更新字段明细', '关联关系明细',
            '主诉明细', '现病史明细'
        ]
    },
    "medicine_regulatory": {
        "name": "药政处",
        "table_flag": "medicine_regulatory",
        "template": "药政处下发汇总报告_模板.xlsx",
        "has_national_flag": False,
        "sql_file": "medicine_regulatory.sql",
        "visible": False,  # 界面暂不显示
        "report_prefix": "药政处下发汇总报告(省标表)_质控日期：",
        "thresholds": {"real": 90, "hour": 100, "other": 100, "association": 100},
        "export_sheets": [
            '地市(州)', '机构汇总', '时效性明细', '必填字段完整性',
            '重要建议填字段完整性', '条件必填字段完整性',
            '第二批次更新字段明细', '关联关系明细',
            '主诉明细', '现病史明细'
        ]
    }
}


def _fmt_threshold(value):
    """阈值数值 → 字符串（整数不带小数点，便于界面显示）"""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# ===== 跨平台路径解析 =====
# PyInstaller 打包后，sys._MEIPASS 指向临时解压目录（只读）
# exe 所在目录同级放置 db/sql/txt 等可写资源
# 开发模式下，资源文件在脚本所在目录
_FROZEN = getattr(sys, 'frozen', False)
if _FROZEN:
    _EXE_DIR = os.path.dirname(sys.executable)
    _RESOURCE_DIR = sys._MEIPASS
    if sys.platform == 'darwin':
        # macOS .app: sys.executable = xxx.app/Contents/MacOS/xxx
        # 资源文件（db/sql/txt）在 .app 同级目录
        _APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(_EXE_DIR)))
    else:
        # Windows: exe 所在目录即资源目录
        _APP_DIR = _EXE_DIR
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))
    _RESOURCE_DIR = _APP_DIR

# 数据库完整性检查：必须存在的关键表（缺少任何一个视为数据库损坏）
_REQUIRED_TABLES = ['org_list']


def _is_db_valid(db_path):
    """检查数据库是否包含关键表，防止使用空壳/损坏的数据库文件。"""
    try:
        conn = duckdb.connect(db_path)
        existing_tables = [row[0] for row in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()]
        conn.close()
        return all(t in existing_tables for t in _REQUIRED_TABLES)
    except Exception:
        return False


def resolve_resource(filename):
    """解析只读资源文件路径（SQL、模板、版本日志等）
    查找顺序：
      1. _APP_DIR（exe/.app 同级目录）—— build_exe.py 复制到 dist 的外部文件
      2. _RESOURCE_DIR（PyInstaller bundle 内部 sys._MEIPASS）—— spec datas 打包的文件
    这样用户如果只把 .app 拖到 /Applications/（未携带外部资源），仍然能从 bundle 内读取只读资源。
    """
    # 1. 优先外部同级目录（方便用户替换 SQL/模板而无需重新打包）
    sibling = os.path.join(_APP_DIR, filename)
    if os.path.isfile(sibling):
        return sibling
    # 2. 回退 bundle 内部（PyInstaller datas 打进的文件）
    internal = os.path.join(_RESOURCE_DIR, filename)
    if os.path.isfile(internal):
        return internal
    # 都没有则返回外部路径，让上层给出"找不到 xxx 文件：path"的报错提示
    return sibling


def get_writable_db_path(db_name):
    """获取可写的数据库路径。
    macOS .app 包内的资源是只读的，需要将数据库复制到可写位置。
    采用三级回退策略：
      1. 优先检查 .app/exe 同级目录（build_exe.py 复制的文件位置）
      2. 检查 .app/exe 同级的 data/ 子目录
      3. 回退到用户数据目录（macOS: ~/Library/Application Support/）
    每一步都会测试写权限，确保目标目录可写。
    发现数据库文件时会验证表完整性（排除空壳/损坏文件）。
    """
    if _FROZEN:
        if sys.platform == 'darwin':
            exe_dir = os.path.dirname(sys.executable)
            app_contents_dir = os.path.dirname(exe_dir)       # Contents/
            app_bundle_dir = os.path.dirname(app_contents_dir)  # .app/
            sibling_dir = os.path.dirname(app_bundle_dir)
        else:
            sibling_dir = os.path.dirname(sys.executable)

        # 1. 优先检查 .app/exe 同级目录是否已有有效数据库
        candidate = os.path.join(sibling_dir, db_name)
        if os.path.exists(candidate) and _is_db_valid(candidate):
            return candidate

        # 如果文件存在但无效（空壳/损坏），删除以便后续步骤重新复制
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except Exception:
                pass

        # 2. 检查 .app/exe 同级的 data/ 子目录
        data_dir = os.path.join(sibling_dir, 'data')
        if os.path.isdir(data_dir):
            candidate = os.path.join(data_dir, db_name)
            if os.path.exists(candidate) and _is_db_valid(candidate):
                return candidate
            if os.path.exists(candidate):
                try:
                    os.remove(candidate)
                except Exception:
                    pass

        # 3. 以上都没有，创建可写副本
        try:
            os.makedirs(data_dir, exist_ok=True)
            test_file = os.path.join(data_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except (PermissionError, OSError):
            # 回退到用户数据目录
            if sys.platform == 'darwin':
                data_dir = os.path.join(
                    os.path.expanduser('~/Library/Application Support/疾控中心下发报告生成工具'),
                    'data'
                )
            else:
                data_dir = os.path.join(
                    os.path.expanduser('~'), '.疾控中心下发报告生成工具', 'data'
                )
            os.makedirs(data_dir, exist_ok=True)

        writable_path = os.path.join(data_dir, db_name)

        # 从 PyInstaller 包内复制数据库到可写位置
        resource_db = os.path.join(_RESOURCE_DIR, db_name)
        if not os.path.exists(writable_path) and os.path.exists(resource_db):
            shutil.copy2(resource_db, writable_path)

        return writable_path
    else:
        # 开发模式：直接在脚本所在目录操作
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dev_path = os.path.join(script_dir, db_name)
        # 如果开发目录的数据库无效，尝试从资源目录复制
        if os.path.exists(dev_path) and not _is_db_valid(dev_path):
            resource_db = os.path.join(_RESOURCE_DIR, db_name)
            if os.path.exists(resource_db):
                try:
                    shutil.copy2(resource_db, dev_path)
                except Exception:
                    pass
        try:
            test_file = os.path.join(script_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return dev_path
        except (PermissionError, OSError):
            data_dir = os.path.join(os.path.expanduser('~'), '.疾控中心下发报告生成工具')
            os.makedirs(data_dir, exist_ok=True)
            writable_path = os.path.join(data_dir, db_name)
            if not os.path.exists(writable_path) and os.path.exists(dev_path):
                shutil.copy2(dev_path, writable_path)
            return writable_path


class ReportGeneratorTool:
    def __init__(self, root):
        self.root = root
        self.root.title(f"疾控中心下发报告生成辅助工具 {VERSION} ({BUILD_DATE})")

        # 确定基准目录
        self.app_base_dir = _APP_DIR

        # ===== 窗口大小 =====
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        if sys.platform == 'darwin':
            # macOS：固定 700x660
            window_width = 700
            window_height = 660
        else:
            # Windows：固定 700x700
            window_width = 700
            window_height = 760

        # 启动时居中
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 允许调整大小（macOS 上必须为 True 才会显示绿色最大化按钮）
        self.root.resizable(False, False)

        # ===== ttk 主题与样式 =====
        # 全局滚动条样式
        style = ttk.Style()

        if sys.platform == 'darwin':
            # macOS 必须使用 aqua 主题才能获得原生外观（圆角按钮、原生标签页、白色背景）
            # 注意：PyInstaller 打包后 Aqua 主题必须由 tk 自带的 libtk 渲染，
            # 显式设置 theme_use('aqua') 比依赖默认值更可靠。
            try:
                available_themes = style.theme_names()
                if 'aqua' in available_themes:
                    style.theme_use('aqua')
                else:
                    # 打包时若 Tk 库未携带 aqua，退而求其次用 default/classic，
                    # 绝对不要使用 clam（灰色很丑）。
                    for fallback in ('default', 'classic'):
                        if fallback in available_themes:
                            style.theme_use(fallback)
                            break
            except Exception:
                pass

            # Aqua 主题大部分样式不可覆盖（是系统原生渲染），
            # 这里仅配置不会破坏原生外观的值。滚动条按 aqua 原生大小（不要配置 width，会破坏原生比例）
            try:
                style.configure("TFrame", padding=0)
                style.configure("TLabel", padding=0)
                style.configure("TNotebook", tabposition='n')
                style.configure("TEntry", padding=3)
                style.configure("TButton", padding=(12, 4))
            except Exception:
                pass
        else:
            # Windows：滚动条加宽
            style.configure("Vertical.TScrollbar", width=32, arrowsize=24)
            style.configure("Horizontal.TScrollbar", width=32, arrowsize=24)

        # 资源文件路径解析
        # 数据库需要写入权限 → 三级回退策略定位可写路径
        self.db_path = get_writable_db_path("prov_report.db")
        # 只读资源 → 从 _RESOURCE_DIR（PyInstaller 包内或脚本目录）读取
        # self.sql_file_path = resolve_resource("prov_generate_data.sql")
        self.version_log_path = resolve_resource("版本日志.txt")
        self.default_template_path = resolve_resource("疾控下发汇总报告模板.xlsx")

        self.template_path = None
        self.export_path = None
        self.data_dir = None
        self.start_date = tk.StringVar()
        self.start_date.set("")  # 初始化为空
        self.end_date = tk.StringVar()
        self.end_date.set("")  # 初始化为空
        self.dept_var = tk.StringVar(value="early_warning")  # 默认预警处
        self.national_flag_var = tk.StringVar(value="national")  # 默认国标
        self.date_range_mode = tk.StringVar(value="single")  # 默认单日
        self.data_imported = False  # 是否已导入数据
        self._is_dept_changing = False  # 标志：是否正在切换处室（避免重复弹窗）

        # 达标率阈值配置（可从界面调整，按处室持久化保存）
        self.threshold_vars = {k: tk.StringVar() for k in ("real", "hour", "other", "association")}
        self._threshold_form_dept_key = None    # 当前输入框中显示的处室
        self.threshold_entries = []             # 输入框控件（用于整体启用/禁用）
        self._thresholds_editable = False       # 是否处于可编辑状态（默认锁定，防误改）
        self.thresholds_config = self._load_thresholds_config()

        # 绑定切换类别时的检查回调
        self.national_flag_var.trace_add('write', self.on_flag_change)

        self.create_main_interface()

        # 初始化达标率输入框（显示当前处室的值）
        self._threshold_form_dept_key = self.get_dept_key()
        self.sync_thresholds_ui(self._threshold_form_dept_key)

    def get_dept_key(self, dept_name=None):
        """根据业务处室名称获取配置key，或根据当前选择获取"""
        if dept_name is None:
            dept_name = self.dept_var.get()
        # 名称到key的映射
        name_to_key = {v["name"]: k for k, v in DEPT_CONFIG.items()}
        return name_to_key.get(dept_name, "early_warning")
        
    def get_current_dept_config(self):
        """获取当前业务处室的配置"""
        dept_key = self.get_dept_key()
        return DEPT_CONFIG.get(dept_key, DEPT_CONFIG["early_warning"])
        
    
    def get_sql_file_path(self):
        """根据当前业务处室获取对应的 SQL 文件路径"""
        dept_config = self.get_current_dept_config()
        sql_file = dept_config.get("sql_file", "prov_generate_data.sql")
        return resolve_resource(sql_file)

    def get_sql_variant(self):
        """获取导出 SQL 复用的处室版本（sql_variant 缺省为处室自身 key）"""
        dept_config = self.get_current_dept_config()
        return dept_config.get("sql_variant", self.get_dept_key())

    # ===== 达标率阈值配置（持久化） =====
    _THRESHOLD_KEYS = ("real", "hour", "other", "association")

    def get_thresholds_file_path(self):
        """达标率配置文件路径（与数据库同目录，保证可写）"""
        return os.path.join(os.path.dirname(self.db_path), "达标率配置.json")

    def _load_thresholds_config(self):
        """读取持久化的达标率配置：以内置默认值打底，再叠加本地文件中的有效值"""
        config = {k: dict(DEPT_CONFIG[k].get("thresholds", {})) for k in DEPT_CONFIG}
        path = self.get_thresholds_file_path()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                for dept_key, vals in saved.items():
                    if dept_key in config and isinstance(vals, dict):
                        for key in self._THRESHOLD_KEYS:
                            if key in vals:
                                config[dept_key][key] = vals[key]
        except Exception:
            pass  # 文件损坏时静默回退到默认值
        return config

    def save_thresholds_config(self):
        """把当前阈值配置写入本地文件"""
        try:
            with open(self.get_thresholds_file_path(), 'w', encoding='utf-8') as f:
                json.dump(self.thresholds_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def sync_thresholds_ui(self, dept_key):
        """把指定处室的阈值填入界面输入框"""
        vals = self.thresholds_config.get(dept_key, {})
        for key in self._THRESHOLD_KEYS:
            self.threshold_vars[key].set(_fmt_threshold(vals.get(key)))

    def read_thresholds_from_ui(self, dept_key):
        """从界面读取阈值并校验写回配置；非法值回退到该处室内置默认值"""
        defaults = DEPT_CONFIG.get(dept_key, {}).get("thresholds", {})
        dept_vals = self.thresholds_config.setdefault(dept_key, {})
        for key in self._THRESHOLD_KEYS:
            raw = self.threshold_vars[key].get().strip()
            try:
                val = float(raw)
                if val < 0:
                    raise ValueError
                dept_vals[key] = int(val) if val.is_integer() else val
            except (ValueError, TypeError):
                dept_vals[key] = defaults.get(key, 0)
                self.threshold_vars[key].set(_fmt_threshold(dept_vals[key]))
        return dept_vals

    def get_current_thresholds(self):
        """获取当前处室的阈值（优先取界面值，非法时用持久化/默认值兜底）"""
        return self.read_thresholds_from_ui(self.get_dept_key())

    def apply_threshold_replacements(self, sql_content, thresholds):
        """把 SQL 中硬编码的达标阈值替换为当前配置值。
        b/c/d 分别为实时表、2小时表、T+0表；m 为机构级、t 为规则级关联达标。
        """
        mapping = {
            r"(b\.compliance_rate\s*>=\s*)[0-9.]+": thresholds.get("real"),
            r"(c\.compliance_rate\s*>=\s*)[0-9.]+": thresholds.get("hour"),
            r"(d\.compliance_rate\s*>=\s*)[0-9.]+": thresholds.get("other"),
            r"(m\.association_rate\s*>=\s*)[0-9.]+": thresholds.get("association"),
            r"(t\.association_rate\s*>=\s*)[0-9.]+": thresholds.get("association"),
        }
        for pattern, value in mapping.items():
            if value is None:
                continue
            sql_content = re.sub(pattern, lambda m, v=value: f"{m.group(1)}{v}", sql_content)
        return sql_content

    def _validate_threshold_input(self, proposed):
        """达标率输入框校验：仅允许正整数/小数（禁止负号、字母等）"""
        if proposed == "":
            return True  # 允许清空后重新输入
        return re.fullmatch(r"\d+\.?\d*", proposed) is not None

    def commit_thresholds_ui(self, event=None):
        """失焦时从界面读取当前处室阈值，校验后保存"""
        self.read_thresholds_from_ui(self.get_dept_key())
        self.save_thresholds_config()

    def toggle_threshold_edit(self):
        """切换达标率输入框的编辑/锁定状态，防止误改"""
        if self._thresholds_editable:
            # 锁定前先校验并保存当前处室阈值
            self.commit_thresholds_ui()
            state, btn_text = 'disabled', "修改"
        else:
            state, btn_text = 'normal', "完成"
        for entry in self.threshold_entries:
            entry.config(state=state)
        self._thresholds_editable = not self._thresholds_editable
        self.threshold_edit_btn.config(text=btn_text)

    def on_dept_change(self, event=None):
        """切换业务处室时的回调"""
        self._is_dept_changing = True
        try:
            # 先保存上一处室界面上填写的达标率，再载入新处室的值
            if getattr(self, '_threshold_form_dept_key', None):
                self.read_thresholds_from_ui(self._threshold_form_dept_key)
                self.save_thresholds_config()

            dept_config = self.get_current_dept_config()

            # 控制国标/全部选择框的显示/隐藏
            if hasattr(self, 'flag_frame'):
                if dept_config["has_national_flag"]:
                    self.flag_frame.grid()
                    # 预警处默认使用国标
                    self.national_flag_var.set("national")
                else:
                    self.flag_frame.grid_remove()
                    # 非预警处自动切换到"全部"模式（即省标表）
                    if self.national_flag_var.get() != "all":
                        self.national_flag_var.set("all")

            # 载入新处室的达标率
            self._threshold_form_dept_key = self.get_dept_key()
            self.sync_thresholds_ui(self._threshold_form_dept_key)

            # 更新模板文件
            self.update_template_by_dept()
            
            # 更新导出文件名
            if hasattr(self, 'export_name_var'):
                self.update_export_filename()
            
            # 强制切换到"3. 数据加工"选项卡（索引为2）
            if hasattr(self, 'notebook'):
                self.notebook.select(2)
        finally:
            self._is_dept_changing = False

    def update_template_by_dept(self):
        """根据当前业务处室更新模板文件"""
        dept_config = self.get_current_dept_config()
        template_name = dept_config["template"]
        
        if template_name:
            template_path = resolve_resource(template_name)
            if os.path.exists(template_path):
                self.template_path = template_path
                if hasattr(self, 'template_label'):
                    self.template_label.config(text=f"模板文件：{template_name}（{dept_config['name']}）")
            else:
                # 模板文件不存在，使用默认模板
                self.template_path = self.default_template_path
                if hasattr(self, 'template_label'):
                    self.template_label.config(text=f"模板文件：疾控下发汇总报告模板.xlsx（默认）")
        else:
            # 没有配置模板，使用默认模板
            self.template_path = self.default_template_path
            if hasattr(self, 'template_label'):
                self.template_label.config(text=f"模板文件：疾控下发汇总报告模板.xlsx（默认）")
        
            
    def on_flag_change(self, *args):
        """切换质控报告生成类别时的回调"""
        # 强制切换到"3. 数据加工"选项卡（索引为2）
        if hasattr(self, 'notebook'):
            self.notebook.select(2)

    def on_date_range_change(self, *args):
        """切换日期区间模式时的回调：控制结束日期的显示/隐藏"""
        if not hasattr(self, 'end_date_frame'):
            return
        if self.date_range_mode.get() == "single":
            self.end_date_frame.grid_remove()
        else:
            self.end_date_frame.grid()
        self.update_export_filename()

    def show_version_log(self):
        """显示版本日志弹窗"""
        top = tk.Toplevel(self.root)
        top.title("版本日志")
        top.geometry("550x450")
        top.resizable(False, False)
        top.attributes('-topmost', True)
        top.transient(self.root)

        # 居中显示
        top.update_idletasks()
        width = 550
        height = 450
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        top.geometry(f"{width}x{height}+{x}+{y}")

        # 标题
        title_label = ttk.Label(top, text="版本更新日志", font=('微软雅黑', 14, 'bold'))
        title_label.pack(pady=(15, 10))

        # 带滚动条的文本框
        text_frame = ttk.Frame(top)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, font=('微软雅黑', 10))
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        # 读取版本日志文件（使用绝对路径）
        log_file = self.version_log_path
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                text_widget.insert(tk.END, content)
            else:
                text_widget.insert(tk.END, f"未找到版本日志文件：{log_file}")
        except Exception as e:
            text_widget.insert(tk.END, f"读取版本日志失败：{str(e)}")

        text_widget.config(state=tk.DISABLED)

        # 关闭按钮
        btn_frame = ttk.Frame(top)
        btn_frame.pack(pady=(5, 15))
        close_btn = ttk.Button(btn_frame, text="关闭", command=top.destroy)
        close_btn.pack()

        top.wait_window()

    def create_main_interface(self):
        """创建主界面"""
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="版本日志", command=self.show_version_log)
        menubar.add_cascade(label="帮助", menu=help_menu)
        self.root.config(menu=menubar)

        # macOS 优化：外层 padding 使用对称边距（均匀的左右上下内边距）
        if sys.platform == 'darwin':
            # aqua 主题自带内部 padding，外层只需要很小的边距即可保持美观对称
            outer_pad = (3, 2, 3, 2)
        else:
            # Windows：收紧外层留白，避免内容与窗口边框之间出现空白
            outer_pad = 4
        main_frame = ttk.Frame(self.root, padding=outer_pad)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        # 确保根窗口也给 main_frame 均匀分配空间
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 业务处室选择框
        dept_frame = ttk.Frame(main_frame)
        dept_frame.grid(row=0, column=0, sticky=tk.W, pady=(0, 2 if sys.platform == 'darwin' else 5))

        dept_label = ttk.Label(dept_frame, text="业务处室：", font=('微软雅黑', 10, 'bold'))
        dept_label.pack(side=tk.LEFT, padx=5)

        dept_combobox = ttk.Combobox(dept_frame, textvariable=self.dept_var, state="readonly", width=16)
        # 下拉选项从 DEPT_CONFIG 动态生成（visible=False 的处室不显示）
        dept_combobox['values'] = tuple(
            cfg["name"] for cfg in DEPT_CONFIG.values() if cfg.get("visible", True)
        )
        dept_combobox.current(0)
        dept_combobox.pack(side=tk.LEFT, padx=5)
        # 绑定选择变化事件
        dept_combobox.bind("<<ComboboxSelected>>", self.on_dept_change)

        # 国标/全部选择框（只有预警处才显示）
        self.flag_frame = ttk.Frame(main_frame)
        self.flag_frame.grid(row=1, column=0, sticky=tk.W, pady=(0, 2 if sys.platform == 'darwin' else 5))

        flag_label = ttk.Label(self.flag_frame, text="质控报告生成类别：", font=('微软雅黑', 10, 'bold'))
        flag_label.pack(side=tk.LEFT, padx=5)

        self.national_radio = ttk.Radiobutton(self.flag_frame, text="国标", variable=self.national_flag_var, value="national")
        self.national_radio.pack(side=tk.LEFT, padx=5)

        self.all_radio = ttk.Radiobutton(self.flag_frame, text="全部", variable=self.national_flag_var, value="all")
        self.all_radio.pack(side=tk.LEFT, padx=5)

        # Notebook 样式：macOS 上使用较小内边距
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # macOS 上 Tab Frame 用统一的对称 padding: (左,上,右,下)
        if sys.platform == 'darwin':
            # aqua 主题的 Notebook/Tab 自带较大内部 padding，只需要小值
            tab_pad = (2, 1, 2, 1)
        else:
            # Windows：左右收紧，避免选项卡内容与边框之间出现大片空白
            tab_pad = (2, 6, 2, 6)

        tab1 = ttk.Frame(self.notebook, padding=tab_pad)
        tab2 = ttk.Frame(self.notebook, padding=tab_pad)
        tab3 = ttk.Frame(self.notebook, padding=tab_pad)
        tab4 = ttk.Frame(self.notebook, padding=tab_pad)
        tab5 = ttk.Frame(self.notebook, padding=tab_pad)

        # 注意：notebook.add(..., padding=...) 的 padding 是"页面客户区内边距"，
        # 会让内容四周（尤其左右）出现大片空白，因此此处不传该参数，
        # 选项卡标签沿用主题默认内边距。
        self.notebook.add(tab1, text="① 数据库测试")
        self.notebook.add(tab2, text="② 数据导入")
        self.notebook.add(tab3, text="③ 数据加工")
        self.notebook.add(tab4, text="④ 数据导出")
        self.notebook.add(tab5, text="⑤ 机构管理")

        self.create_db_test_tab(tab1)
        self.create_data_import_tab(tab2)
        self.create_data_process_tab(tab3)
        self.create_data_export_tab(tab4)
        self.create_org_management_tab(tab5)
        
    def create_db_test_tab(self, parent):
        """创建数据库测试 Tab"""
        # 左右对称 padding: (左, 上, 右, 下)
        if sys.platform == 'darwin':
            # aqua 主题原生 LabelFrame 自带漂亮边框与 padding，只需要小内边距
            lf_pad = (2, 1, 2, 1)
        else:
            lf_pad = 5
        frame = ttk.LabelFrame(parent, text="DuckDB 数据库连接测试", padding=lf_pad)
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        db_label = ttk.Label(frame, text=f"数据库文件：{self.db_path}")
        db_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        self.db_status_label = ttk.Label(frame, text="状态：未测试", foreground="orange")
        self.db_status_label.grid(row=1, column=0, sticky=tk.W, pady=2)

        test_btn = ttk.Button(frame, text="测试数据库连接", command=self.test_database)
        test_btn.grid(row=2, column=0, pady=2)

        # 带滚动条的日志文本框，自适应剩余空间
        text_frame = ttk.Frame(frame)
        text_frame.grid(row=3, column=0, pady=(2, 10), sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.db_info_text = tk.Text(text_frame, yscrollcommand=scrollbar.set, wrap=tk.WORD)
        self.db_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.db_info_text.yview)
        
    def test_database(self):
        """测试数据库连接"""
        try:
            conn = duckdb.connect(self.db_path)
            result = conn.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main'").fetchone()
            
            self.db_status_label.config(text="状态：连接成功", foreground="green")
            
            self.db_info_text.delete(1.0, tk.END)
            self.db_info_text.insert(tk.END, f"✓ 数据库连接成功\n")
            self.db_info_text.insert(tk.END, f"✓ 数据库文件：{os.path.abspath(self.db_path)}\n")
            self.db_info_text.insert(tk.END, f"✓ 表数量：{result[0]}\n\n")
            
            tables = conn.execute("SELECT table_name FROM information_schema.tables order by table_name").fetchall()
            self.db_info_text.insert(tk.END, "数据库表列表:\n")
            for table in tables:
                count = conn.execute(f"SELECT COUNT(*) FROM {table[0]}").fetchone()[0]
                self.db_info_text.insert(tk.END, f"  - {table[0]}: {count} 条记录\n")
            
            conn.close()
            
        except Exception as e:
            self.db_status_label.config(text="状态：连接失败", foreground="red")
            self.db_info_text.delete(1.0, tk.END)
            self.db_info_text.insert(tk.END, f"✗ 数据库连接失败\n错误信息：{str(e)}\n")
            
    def create_data_import_tab(self, parent):
        """创建数据导入 Tab"""
        # 左右对称 padding: (左, 上, 右, 下)
        if sys.platform == 'darwin':
            # aqua 主题原生 LabelFrame 自带漂亮边框与 padding，只需要小内边距
            lf_pad = (2, 1, 2, 1)
        else:
            lf_pad = 5
        frame = ttk.LabelFrame(parent, text="数据导入", padding=lf_pad)
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        # 创建日期选择框架
        date_frame = ttk.Frame(frame)
        date_frame.grid(row=0, column=0, sticky=tk.W, pady=2)

        # 数据区间选择
        range_frame = ttk.Frame(date_frame)
        range_frame.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        range_label = ttk.Label(range_frame, text="数据区间:", font=('微软雅黑', 10, 'bold'))
        range_label.pack(side=tk.LEFT, padx=5)
        
        single_radio = ttk.Radiobutton(range_frame, text="单日", variable=self.date_range_mode, value="single")
        single_radio.pack(side=tk.LEFT, padx=5)
        
        range_radio = ttk.Radiobutton(range_frame, text="区间", variable=self.date_range_mode, value="range")
        range_radio.pack(side=tk.LEFT, padx=5)

        # 日期输入框架
        input_frame = ttk.Frame(date_frame)
        input_frame.grid(row=1, column=0, sticky=tk.W)

        # 设置初始日期为今天
        today = datetime.now().strftime('%Y-%m-%d')
        self.start_date.set(today)
        self.end_date.set(today)

        # 开始日期
        start_label = ttk.Label(input_frame, text="开始日期:", font=('微软雅黑', 10, 'bold'))
        start_label.grid(row=0, column=0, padx=5)

        start_date_entry = ttk.Entry(input_frame, textvariable=self.start_date, width=12, font=('微软雅黑', 10), state='readonly')
        start_date_entry.grid(row=0, column=1, padx=5)

        start_calendar_btn = ttk.Button(input_frame, text="📅", width=3, command=lambda: self.open_date_picker('start'))
        start_calendar_btn.grid(row=0, column=2, padx=2)

        start_date_entry.bind('<Button-1>', lambda e: self.open_date_picker('start'))

        # 结束日期（放在独立frame中以便显示/隐藏）
        self.end_date_frame = ttk.Frame(input_frame)
        self.end_date_frame.grid(row=0, column=3, padx=5)

        end_label = ttk.Label(self.end_date_frame, text="结束日期:", font=('微软雅黑', 10, 'bold'))
        end_label.pack(side=tk.LEFT, padx=5)

        end_date_entry = ttk.Entry(self.end_date_frame, textvariable=self.end_date, width=12, font=('微软雅黑', 10), state='readonly')
        end_date_entry.pack(side=tk.LEFT, padx=5)

        end_calendar_btn = ttk.Button(self.end_date_frame, text="📅", width=3, command=lambda: self.open_date_picker('end'))
        end_calendar_btn.pack(side=tk.LEFT, padx=2)

        end_date_entry.bind('<Button-1>', lambda e: self.open_date_picker('end'))
        
        # 绑定日期区间模式变化
        self.date_range_mode.trace_add('write', self.on_date_range_change)
        # 初始状态
        self.on_date_range_change()

        select_btn = ttk.Button(frame, text="选择数据文件目录", command=self.select_data_directory)
        select_btn.grid(row=1, column=0, sticky=tk.W, pady=2)

        self.dir_label = ttk.Label(frame, text="当前目录：未选择")
        self.dir_label.grid(row=2, column=0, sticky=tk.W, pady=2)

        # 导入按钮框架（居中显示）
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, pady=2 if sys.platform == 'darwin' else 5)
        import_btn = ttk.Button(btn_frame, text="开始导入数据", command=self.import_data)
        import_btn.pack()

        self.import_status_label = ttk.Label(frame, text="导入状态：未开始")
        self.import_status_label.grid(row=4, column=0, sticky=tk.W, pady=2)

        self.import_progress = ttk.Progressbar(frame, mode='determinate')
        self.import_progress.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=2)

        # 带滚动条的日志文本框，自适应剩余空间
        text_frame = ttk.Frame(frame)
        text_frame.grid(row=6, column=0, pady=(2, 10), sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(6, weight=1)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_list_text = tk.Text(text_frame, yscrollcommand=scrollbar.set, wrap=tk.WORD)
        self.file_list_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.file_list_text.yview)
        
    def open_date_picker(self, date_type='start'):
        """按当前区间模式打开日期选择器：单日→单日历；区间→一次选择起止日期"""
        if self.date_range_mode.get() == 'range':
            self.popup_calendar_range()
        else:
            self.popup_calendar(date_type)

    def popup_calendar_range(self):
        """弹出日历窗口，一次选择开始与结束日期（区间模式）"""
        top = tk.Toplevel(self.root)
        top.title("选择日期区间")
        top.resizable(False, False)
        top.attributes('-topmost', True)
        top.geometry(f"+{self.root.winfo_x() + 200}+{self.root.winfo_y() + 100}")

        def parse(text):
            try:
                return datetime.strptime(text, '%Y-%m-%d')
            except (ValueError, TypeError):
                return datetime.now()

        s = parse(self.start_date.get())
        e = parse(self.end_date.get())

        body = ttk.Frame(top, padding=10)
        body.pack()

        start_box = ttk.LabelFrame(body, text="开始日期", padding=5)
        start_box.grid(row=0, column=0, padx=5)
        cal_start = Calendar(start_box, selectmode='day', date_pattern='yyyy-mm-dd',
                             year=s.year, month=s.month, day=s.day)
        cal_start.pack()

        end_box = ttk.LabelFrame(body, text="结束日期", padding=5)
        end_box.grid(row=0, column=1, padx=5)
        cal_end = Calendar(end_box, selectmode='day', date_pattern='yyyy-mm-dd',
                           year=e.year, month=e.month, day=e.day)
        cal_end.pack()

        def on_confirm():
            start_str = cal_start.get_date()
            end_str = cal_end.get_date()
            if start_str > end_str:
                messagebox.showwarning("提示", "开始日期不能晚于结束日期", parent=top)
                return
            self.start_date.set(start_str)
            self.end_date.set(end_str)
            self.update_export_filename()
            top.destroy()

        btn_frame = ttk.Frame(body, padding=(0, 8, 0, 0))
        btn_frame.grid(row=1, column=0, columnspan=2)
        ttk.Button(btn_frame, text="确定", command=on_confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=top.destroy).pack(side=tk.LEFT, padx=5)

        top.wait_window()

    def popup_calendar(self, date_type='start'):
        """弹出日历选择窗口"""
        # 创建顶级窗口
        top = tk.Toplevel(self.root)
        top.title("选择日期")
        top.resizable(False, False)

        # 设置窗口始终在最前
        top.attributes('-topmost', True)

        # 获取按钮位置，设置窗口在按钮右侧
        x = self.root.winfo_x() + 280  # 主窗口 X 坐标 + 按钮位置
        y = self.root.winfo_y() + 100  # 主窗口 Y 坐标 + 偏移量
        top.geometry(f"+{x}+{y}")

        # 创建 Calendar 控件
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd')
        cal.pack(padx=10, pady=10)

        # 设置当前选中的日期
        current_date = self.start_date.get() if date_type == 'start' else self.end_date.get()
        if current_date:
            cal.selection_set(current_date)

        # 确认选择函数
        def on_confirm():
            selected_date = cal.get_date()
            if date_type == 'start':
                self.start_date.set(selected_date)
            else:
                self.end_date.set(selected_date)
            self.update_export_filename()
            top.destroy()

        # 取消选择函数
        def on_cancel():
            top.destroy()

        # 创建按钮框架
        btn_frame = ttk.Frame(top)
        btn_frame.pack(pady=5)

        # 确认按钮
        confirm_btn = ttk.Button(btn_frame, text="确定", command=on_confirm)
        confirm_btn.pack(side=tk.LEFT, padx=5)

        # 取消按钮
        cancel_btn = ttk.Button(btn_frame, text="取消", command=on_cancel)
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # 等待窗口关闭
        top.wait_window()
    
    def get_base_name(self):
        """根据业务处室和国标/全部选择返回对应的基础文件名"""
        dept_config = self.get_current_dept_config()
        dept_name = dept_config["name"]
        dept_key = self.get_dept_key()

        if dept_key == "early_warning":
            # 预警处：有省标/国标区分
            flag = getattr(self, 'national_flag_var', None)
            if flag and flag.get() == "all":
                return "疾控下发汇总报告(省标表)_质控日期："
            else:
                return "疾控下发汇总报告(省标对照国标)_质控日期："
        else:
            # 其他处室：从配置读取文件名前缀
            return dept_config.get("report_prefix", "疾控下发汇总报告(省标对照国标)_质控日期：")

    def update_export_filename(self):
        """更新导出文件名中的质控日期"""
        start_date_str = self.start_date.get()
        end_date_str = self.end_date.get()
        if start_date_str and hasattr(self, 'export_name_var'):
            base_name = self.get_base_name()
            if self.date_range_mode.get() == "single" or start_date_str == end_date_str:
                new_name = f"{base_name}{start_date_str}.xlsx"
            else:
                new_name = f"{base_name}{start_date_str}至{end_date_str}.xlsx"
            self.export_name_var.set(new_name)
    
    def select_data_directory(self):
        """选择数据文件目录"""
        directory = filedialog.askdirectory(title="选择包含 Excel 数据文件的目录")
        if directory:
            self.data_dir = directory
            self.dir_label.config(text=f"当前目录：{directory}")
            
            self.file_list_text.delete(1.0, tk.END)
            self.file_list_text.insert(tk.END, "找到的数据文件:\n")
            
            prov_files = [f for f in os.listdir(directory) if f.startswith('prov_') and f.endswith('.xlsx')]
            for file in prov_files:
                self.file_list_text.insert(tk.END, f"  - {file}\n")
                
            if len(prov_files) == 0:
                self.file_list_text.insert(tk.END, "\n未找到以 prov_开头的 Excel 文件\n")
                
    def import_data(self):
        """导入数据"""
        if not self.data_dir:
            messagebox.showwarning("警告", "请先选择数据文件目录")
            return
            
        def do_import():
            try:
                conn = duckdb.connect(self.db_path)
                prov_files = [f for f in os.listdir(self.data_dir) if f.startswith('prov_') and f.endswith('.xlsx')]
                
                if not prov_files:
                    raise Exception("未找到以 prov_开头的 Excel 文件")
                
                total_files = len(prov_files)
                self.import_progress['maximum'] = total_files
                
                self.file_list_text.delete(1.0, tk.END)
                self.file_list_text.insert(tk.END, "开始导入数据...\n")
                
                for i, file in enumerate(prov_files):
                    table_name = os.path.splitext(file)[0]
                    
                    file_path = os.path.join(self.data_dir, file)
                    
                    self.file_list_text.insert(tk.END, f"导入：{file} -> {table_name}\n")
                    self.root.update_idletasks()
                    
                    try:
                        df = pd.read_excel(file_path)

                        # national_flag、column_level 转为字符串类型：
                        # 数字值(1/1.0) → '1'，非数字字符串(如 update_1) → 保持原样，空值 → None(NULL)
                        def to_str_flag(x):
                            if pd.isna(x):
                                return None
                            x_str = str(x).strip()
                            if x_str in ('', 'nan', 'None'):
                                return None
                            try:
                                return str(int(float(x_str)))
                            except (ValueError, TypeError):
                                return x_str

                        for col in ['national_flag','nation_flag', 'column_level']:
                            if col in df.columns:
                                df[col] = df[col].apply(to_str_flag)

                        conn.execute(f"DELETE FROM {table_name}")

                        insert_sql = f"INSERT INTO {table_name} SELECT * FROM df"
                        conn.execute(insert_sql)
                        
                        self.import_progress['value'] = i + 1
                        self.root.update_idletasks()
                        
                        self.file_list_text.insert(tk.END, f"  ✓ 成功导入 {len(df)} 条记录\n")
                        
                    except Exception as e:
                        self.file_list_text.insert(tk.END, f"  ✗ 导入失败：{str(e)}\n")
                        raise
                    
                conn.commit()
                conn.close()

                self.data_imported = True
                self.import_status_label.config(text="导入状态：完成", foreground="green")
                messagebox.showinfo("成功", f"成功导入 {total_files} 个数据表")
                
            except Exception as e:
                self.import_status_label.config(text="导入状态：失败", foreground="red")
                messagebox.showerror("错误", f"数据导入失败:\n{str(e)}")
                
        thread = threading.Thread(target=do_import)
        thread.start()
        
    def create_data_process_tab(self, parent):
        """创建数据加工 Tab"""
        # 左右对称 padding: (左, 上, 右, 下)
        if sys.platform == 'darwin':
            # aqua 主题原生 LabelFrame 自带漂亮边框与 padding，只需要小内边距
            lf_pad = (2, 1, 2, 1)
        else:
            lf_pad = 5
        frame = ttk.LabelFrame(parent, text="数据加工", padding=lf_pad)
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        sql_label = ttk.Label(frame, text="执行 加工数据 SQL 脚本")
        sql_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.process_status_label = ttk.Label(frame, text="加工状态：未开始")
        self.process_status_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        process_btn = ttk.Button(frame, text="执行数据加工 SQL", command=self.process_data)
        process_btn.grid(row=3, column=0, pady=2)

        # 达标率设置（%，按业务处室保存）：分两组 —— 表实时性(3项) / 关联一致性(1项)
        # 置于"执行数据加工"按钮之前，符合"先调整达标率、再执行加工"的操作习惯
        th_frame = ttk.LabelFrame(frame, text="达标率设置（%，按业务处室保存）", padding=lf_pad)
        th_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=4)

        # 输入校验：仅允许整数/小数（不含负号、字母），即只能填非负数值
        self._threshold_validate_cmd = self.root.register(self._validate_threshold_input)
        groups = [
            ("表实时性", [("实时表", "real"), ("2小时表", "hour"), ("T+0表", "other")]),
            ("关联一致性", [("关联达标率", "association")]),
        ]
        for col, (group_name, fields) in enumerate(groups):
            group_frame = ttk.LabelFrame(th_frame, text=group_name, padding=(4, 2))
            group_frame.grid(row=0, column=col, sticky=(tk.W, tk.E),
                             padx=(2, 6) if col == 0 else (0, 8), pady=2)
            for i, (text, key) in enumerate(fields):
                ttk.Label(group_frame, text=f"{text}：").grid(row=0, column=i * 2, sticky=tk.W, padx=(4, 2))
                entry = ttk.Entry(
                    group_frame, textvariable=self.threshold_vars[key], width=6,
                    validate='key', validatecommand=(self._threshold_validate_cmd, '%P')
                )
                entry.grid(row=0, column=i * 2 + 1, sticky=tk.W, padx=(0, 8))
                # 失焦时按当前处室校验并保存（避免输入过程中被回退值打断）
                entry.bind('<FocusOut>', self.commit_thresholds_ui)
                # 默认锁定，防止误改；需点击"修改"按钮后才可编辑
                entry.config(state='disabled')
                self.threshold_entries.append(entry)

        # "修改"按钮：点击后解锁输入框，再次点击锁定并保存
        self.threshold_edit_btn = ttk.Button(th_frame, text="修改", width=8,
                                             command=self.toggle_threshold_edit)
        self.threshold_edit_btn.grid(row=0, column=len(groups), sticky=(tk.W, tk.E), padx=(0, 4), pady=2)

        # 创建带滚动条的文本框
        text_frame = ttk.Frame(frame)
        text_frame.grid(row=4, column=0, pady=(2, 10), sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(4, weight=1)
        
        # 垂直滚动条
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 文本框 (缩小高度)
        self.process_text = tk.Text(text_frame, yscrollcommand=scrollbar.set, wrap=tk.WORD)
        self.process_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定滚动条
        scrollbar.config(command=self.process_text.yview)
        
    def process_data(self):
        """执行数据加工 SQL"""
        def do_process():
            try:
                self.process_status_label.config(text="加工状态：执行中...", foreground="orange")
                self.process_text.delete(1.0, tk.END)

                # 根据当前业务处室读取对应的 SQL 文件
                sql_file = self.get_sql_file_path()
                if not os.path.exists(sql_file):
                    raise Exception(f"找不到 SQL 文件：{sql_file}")

                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()

                # 获取当前业务处室配置
                dept_config = self.get_current_dept_config()
                dept_flag = dept_config["table_flag"]
                dept_name = dept_config["name"]
                
                self.process_text.insert(tk.END, f"当前业务处室：{dept_name}\n")
                # self.process_text.insert(tk.END, f"过滤字段：{dept_flag} = '1'\n\n")

                # 根据选择动态修改SQL
                # 1. 添加业务处室过滤条件（在所有 prov_table_list 的引用上添加）
                #    替换 b.national_flag = '1' → b.national_flag = '1' and b.dept_flag = '1'
                sql_content = sql_content.replace(
                    "and b.national_flag = '1'",
                    f"and b.national_flag = '1' and b.{dept_flag} = '1'"
                )
                sql_content = sql_content.replace(
                    "and b.national_flag='1'",
                    f"and b.national_flag='1' and b.{dept_flag}='1'"
                )
                sql_content = sql_content.replace(
                    "and c.national_flag = '1'",
                    f"and c.national_flag = '1' and c.{dept_flag} = '1'"
                )
                sql_content = sql_content.replace(
                    "and c.national_flag='1'",
                    f"and c.national_flag='1' and c.{dept_flag}='1'"
                )
                
                # 2. 对于没有 national_flag 但有 prov_table_list 的查询（如业务主键唯一率），
                #    需要在 where a.table_name = b.table_name 后添加业务处室过滤
                #    匹配模式：where a.table_name = b.table_name\n （后面没有其他条件直接跟 group by）
                #    这种情况出现在 prov_business_org 的插入语句中
                sql_content = sql_content.replace(
                    "where a.table_name = b.table_name\ngroup by",
                    f"where a.table_name = b.table_name and b.{dept_flag} = '1'\ngroup by"
                )

                # 2b. 对于明细表（如 prov_column_level_detail）带有 national_flag 的查询，
                #     模式：where {detail_alias}.table_name = {prov_alias}.table_name and {detail_alias}.national_flag = '1'
                #     需要根据处室和国标/全部模式做不同处理：
                #       - 预警处+国标：保留 national_flag，不加 dept_flag
                #       - 预警处+全部：移除 national_flag，不加 dept_flag
                #       - 应急处/药政处：移除 national_flag，加 dept_flag
                dept_key = self.get_dept_key()

                def replace_detail_national_flag(match):
                    detail_alias = match.group(1)
                    prov_alias = match.group(2)
                    if dept_key == "early_warning":
                        if self.national_flag_var.get() == "all":
                            # 预警处 + 全部：移除 national_flag，不加 dept_flag
                            return f"where {detail_alias}.table_name = {prov_alias}.table_name"
                        else:
                            # 预警处 + 国标：保留 national_flag，不加 dept_flag
                            return match.group(0)
                    else:
                        # 应急处/药政处：移除 national_flag，加 dept_flag
                        return f"where {detail_alias}.table_name = {prov_alias}.table_name and {prov_alias}.{dept_flag} = '1'"

                pattern = r"where\s+(\w+)\.table_name\s*=\s*(\w+)\.table_name\s+and\s+\1\.national_flag\s*=\s*'1'"
                sql_content = re.sub(pattern, replace_detail_national_flag, sql_content)

                # 3. 根据国标/全部选择处理 national_flag 条件
                if self.national_flag_var.get() == "all":
                    # 选择"全部"时，移除所有 national_flag='1' 的条件
                    sql_content = sql_content.replace("and a.national_flag = '1'", "")
                    sql_content = sql_content.replace("and c.national_flag = '1'", "")
                    sql_content = sql_content.replace("and b.national_flag = '1'", "")
                    sql_content = sql_content.replace("and c.national_flag='1'", "")
                    sql_content = sql_content.replace("and b.national_flag='1'", "")
                    # 同时也要移除 a.national_flag='1' 的情况（明细表中的字段）
                    sql_content = sql_content.replace("and a.national_flag='1'", "")

                # 4. 按当前处室的达标率阈值替换 SQL 中硬编码的达标值
                thresholds = self.get_current_thresholds()
                self.save_thresholds_config()
                sql_content = self.apply_threshold_replacements(sql_content, thresholds)

                self.process_text.insert(
                    tk.END,
                    f"达标率阈值：实时 {thresholds['real']}% | 2小时 {thresholds['hour']}% | "
                    f"T+0 {thresholds['other']}% | 关联 {thresholds['association']}%\n"
                )
                self.process_text.insert(tk.END, f"执行 SQL 脚本：{sql_file}\n\n")

                conn = duckdb.connect(self.db_path)

                # 当前处室依赖 prov_table_list.enable_status 时，确保该字段存在
                if dept_flag == "enable_status":
                    self._ensure_enable_status_column(conn)

                # 改进 SQL 分割逻辑，处理多行 SQL 语句
                statements = []
                current_stmt = []
                for line in sql_content.split('\n'):
                    line = line.strip()
                    if line.startswith('--'):
                        continue
                    if line.endswith(';'):
                        current_stmt.append(line[:-1])
                        full_stmt = ' '.join(current_stmt).strip()
                        if full_stmt:
                            statements.append(full_stmt)
                        current_stmt = []
                    elif line:
                        current_stmt.append(line)
                
                if current_stmt:
                    full_stmt = ' '.join(current_stmt).strip()
                    if full_stmt:
                        statements.append(full_stmt)
                
                success_count = 0
                error_count = 0
                
                for i, stmt in enumerate(statements):
                    stmt = stmt.strip()
                    if stmt:
                        try:
                            result = conn.execute(stmt)
                            if result:
                                rows_affected = result.rowcount
                                self.process_text.insert(tk.END, f"✓ 语句 {i+1}: 成功")
                                if rows_affected >= 0:
                                    self.process_text.insert(tk.END, f" (影响 {rows_affected} 行)\n")
                                else:
                                    self.process_text.insert(tk.END, f"\n")
                                success_count += 1
                            else:
                                self.process_text.insert(tk.END, f"✓ 语句 {i+1}: 成功\n")
                                success_count += 1
                        except Exception as e:
                            self.process_text.insert(tk.END, f"✗ 语句 {i+1} 失败：{str(e)[:200]}\n")
                            error_count += 1
                
                conn.commit()
                
                self.process_text.insert(tk.END, f"\n执行统计：成功 {success_count} 条，失败 {error_count} 条\n")
                
                # 查询生成的汇总数据表 (包括 qzrj_city_summary)
                result = conn.execute("""
                    SELECT table_name FROM information_schema.tables WHERE table_name
in('prov_association_org', 'prov_column_level_org', 'prov_dict_org', 'prov_realtime_org','prov_business_org','prov_city_summary')
                """).fetchall()
                
                self.process_text.insert(tk.END, f"\n✓ 生成的汇总数据表:\n")
                for table in result:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table[0]}").fetchone()[0]
                    self.process_text.insert(tk.END, f"  - {table[0]}: {count} 条记录\n")
                
                conn.close()
                
                self.process_status_label.config(text="加工状态：完成", foreground="green")
                
            except Exception as e:
                self.process_status_label.config(text="加工状态：失败", foreground="red")
                self.process_text.insert(tk.END, f"\n✗ 错误：{str(e)}\n")
                
        thread = threading.Thread(target=do_process)
        thread.start()

    def _ensure_enable_status_column(self, conn):
        """确保 prov_table_list 存在 enable_status 字段。

        应急处(41张表)按 prov_table_list.enable_status 关联过滤。
        老版本数据库无此字段时自动补齐：41 张正式表初始化为 1，
        组合行（table_name 含逗号）初始化为 0；字段已存在时不改动任何数据。
        """
        cols = [row[1] for row in conn.execute("PRAGMA table_info('prov_table_list')").fetchall()]
        if 'enable_status' in cols:
            return
        self.process_text.insert(tk.END, " prov_table_list 缺少 enable_status 字段，自动补齐...\n")
        conn.execute("ALTER TABLE prov_table_list ADD COLUMN enable_status INTEGER")
        conn.execute("""
            UPDATE prov_table_list
            SET enable_status = CASE WHEN table_name LIKE '%,%' THEN 0 ELSE 1 END
        """)
        conn.commit()
        cnt = conn.execute("SELECT COUNT(*) FROM prov_table_list WHERE enable_status = 1").fetchone()[0]
        self.process_text.insert(
            tk.END,
            f"✓ 已初始化 enable_status：{cnt} 张表标记为 1（如需调整请维护 prov_table_list 后重新加工）\n\n"
        )

    def create_data_export_tab(self, parent):
        """创建数据导出 Tab"""
        # 左右对称 padding: (左, 上, 右, 下)
        if sys.platform == 'darwin':
            # aqua 主题原生 LabelFrame 自带漂亮边框与 padding，只需要小内边距
            lf_pad = (2, 1, 2, 1)
        else:
            lf_pad = 5
        inner_pad = (2, 1, 2, 1) if sys.platform == 'darwin' else 5
        frame = ttk.LabelFrame(parent, text="数据导出", padding=lf_pad)
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 模板文件区域
        template_frame = ttk.LabelFrame(frame, text="模板文件", padding=inner_pad)
        template_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        frame.columnconfigure(0, weight=1)
        
        self.template_label = ttk.Label(template_frame, text="模板文件：未选择")
        self.template_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        select_template_btn = ttk.Button(template_frame, text="选择模板文件", command=self.select_template)
        select_template_btn.grid(row=0, column=1, padx=5)
        
        # 初始化时根据业务处室自动选择模板
        self.update_template_by_dept()
        
        # 导出设置区域
        export_frame = ttk.LabelFrame(frame, text="导出设置", padding=inner_pad)
        export_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        frame.columnconfigure(0, weight=1)
        
        # 使用当前质控日期作为默认文件名，根据国标/全部选择动态设置
        default_date = datetime.now().strftime('%Y-%m-%d')
        self.start_date.set(default_date)
        self.end_date.set(default_date)
        default_base_name = self.get_base_name()
        default_name = f"{default_base_name}{default_date}.xlsx"
        self.export_name_var = tk.StringVar(value=default_name)

        # 绑定国标/全部切换时更新文件名
        if hasattr(self, 'national_flag_var'):
            self.national_flag_var.trace('w', lambda *args: self.update_export_filename())
        export_name_label = ttk.Label(export_frame, text="导出文件名:")
        export_name_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        export_name_entry = ttk.Entry(export_frame, textvariable=self.export_name_var, width=80)
        export_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)
        export_frame.columnconfigure(1, weight=1)

        # ===== 默认导出目录：优化策略 =====
        # 优先级：Windows 特殊处理 > Documents > 桌面 > 用户主目录 > 兜底
        default_export_dir = self._find_writable_export_dir()
        self._export_dir = default_export_dir

        # 添加路径显示
        default_full_path = os.path.join(self._export_dir, default_name)
        self.export_path_var = tk.StringVar(value=default_full_path)
        export_path_label = ttk.Label(export_frame, text="完整路径:")
        export_path_label.grid(row=1, column=0, sticky=tk.W, pady=2)

        export_path_entry = ttk.Entry(export_frame, textvariable=self.export_path_var, width=80)
        export_path_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)
        export_frame.columnconfigure(1, weight=1)

        # 文件名变化时更新路径（保留目录部分，只替换文件名）
        def update_path(*args):
            filename = self.export_name_var.get()
            self.export_path_var.set(os.path.join(self._export_dir, filename))

        self.export_name_var.trace('w', update_path)
        
        # 导出按钮（三个按钮放在同一行，独立按钮框架）
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, pady=2 if sys.platform == 'darwin' else 5)

        choose_dir_btn = ttk.Button(btn_frame, text="选择保存目录", command=self.choose_export_dir)
        choose_dir_btn.pack(side=tk.LEFT, padx=5)

        export_btn = ttk.Button(btn_frame, text="开始导出报告", command=self.export_report)
        export_btn.pack(side=tk.LEFT, padx=5)

        open_dir_btn = ttk.Button(btn_frame, text="打开质控报告目录", command=self.open_report_dir)
        open_dir_btn.pack(side=tk.LEFT, padx=5)
        
        self.export_status_label = ttk.Label(frame, text="导出状态：未开始")
        self.export_status_label.grid(row=3, column=0, sticky=tk.W, pady=1)
        
        self.export_progress = ttk.Progressbar(frame, mode='indeterminate')
        self.export_progress.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=1)
        frame.columnconfigure(0, weight=1)
        
        # 创建带滚动条的文本框
        text_frame = ttk.Frame(frame)
        text_frame.grid(row=5, column=0, pady=(1, 10), sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(5, weight=1)
        
        # 垂直滚动条
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 文本框
        self.export_text = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        self.export_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定滚动条
        scrollbar.config(command=self.export_text.yview)

    def create_org_management_tab(self, parent):
        """创建机构管理 Tab"""
        # 左右对称 padding: (左, 上, 右, 下)
        if sys.platform == 'darwin':
            # aqua 主题原生 LabelFrame 自带漂亮边框与 padding，只需要小内边距
            lf_pad = (2, 1, 2, 1)
        else:
            lf_pad = 5
        frame = ttk.LabelFrame(parent, text="机构管理", padding=lf_pad)
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        # 查询区域
        search_frame = ttk.Frame(frame)
        search_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        frame.columnconfigure(0, weight=1)

        search_label = ttk.Label(search_frame, text="搜索：")
        search_label.pack(side=tk.LEFT, padx=5)

        self.org_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.org_search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=5)

        # 点击搜索框自动清空
        search_entry.bind('<Button-1>', lambda e: self.org_search_var.set(''))

        search_btn = ttk.Button(search_frame, text="查询", command=self.refresh_org_tree)
        search_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = ttk.Button(search_frame, text="刷新", command=self.refresh_org_tree)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # 操作按钮区域
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, pady=2 if sys.platform == 'darwin' else 5)

        add_btn = ttk.Button(btn_frame, text="新增机构", command=self.add_org)
        add_btn.pack(side=tk.LEFT, padx=5)

        edit_btn = ttk.Button(btn_frame, text="编辑机构", command=self.edit_org)
        edit_btn.pack(side=tk.LEFT, padx=5)

        delete_btn = ttk.Button(btn_frame, text="删除机构", command=self.delete_org)
        delete_btn.pack(side=tk.LEFT, padx=5)

        # Treeview 展示区域
        tree_frame = ttk.Frame(frame)
        tree_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(2, 5))
        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)

        # 垂直滚动条
        v_scrollbar = ttk.Scrollbar(tree_frame)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 水平滚动条
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # 定义显示的列
        self.org_tree = ttk.Treeview(tree_frame, columns=('city', '区县', 'org_code', 'org_name', 'is_516_flag'),
                                      show='headings', yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # 设置列标题和宽度
        self.org_tree.heading('city', text='地市(州)')
        self.org_tree.heading('区县', text='区县')
        self.org_tree.heading('org_code', text='机构代码')
        self.org_tree.heading('org_name', text='机构名称')
        self.org_tree.heading('is_516_flag', text='是否516')

        self.org_tree.column('city', width=80)
        self.org_tree.column('区县', width=80)
        self.org_tree.column('org_code', width=100)
        self.org_tree.column('org_name', width=200)
        self.org_tree.column('is_516_flag', width=80)

        self.org_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        v_scrollbar.config(command=self.org_tree.yview)
        h_scrollbar.config(command=self.org_tree.xview)

        # 双击编辑
        self.org_tree.bind('<Double-1>', lambda e: self.edit_org())

        # 状态栏
        self.org_status_label = ttk.Label(frame, text="机构管理：未加载")
        self.org_status_label.grid(row=3, column=0, sticky=tk.W, pady=2)

        # 初始加载数据
        self.refresh_org_tree()

    def refresh_org_tree(self):
        """刷新机构列表"""
        search_text = self.org_search_var.get().strip()

        try:
            conn = duckdb.connect(self.db_path)

            if search_text:
                sql = f"""
                    SELECT city, 区县, org_code, org_name, is_516_flag
                    FROM org_list
                    WHERE city LIKE '%{search_text}%' 
                       OR 区县 LIKE '%{search_text}%' 
                       OR org_code LIKE '%{search_text}%' 
                       OR org_name LIKE '%{search_text}%'
                    ORDER BY city, org_code
                """
            else:
                sql = "SELECT city, 区县, org_code, org_name, is_516_flag FROM org_list ORDER BY city, org_code"

            result = conn.execute(sql).fetchall()
            conn.close()

            # 清空现有数据
            for item in self.org_tree.get_children():
                self.org_tree.delete(item)

            # 添加新数据
            for row in result:
                self.org_tree.insert('', tk.END, values=row)

            self.org_status_label.config(text=f"机构管理：共 {len(result)} 条记录", foreground="black")

        except Exception as e:
            self.org_status_label.config(text=f"机构管理：加载失败 - {str(e)}", foreground="red")
            messagebox.showerror("错误", f"加载机构数据失败：\n{str(e)}")

    def add_org(self):
        """新增机构"""
        self.show_org_edit_dialog()

    def edit_org(self):
        """编辑选中的机构"""
        selected = self.org_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选中要编辑的机构")
            return

        item = selected[0]
        values = self.org_tree.item(item, 'values')

        # 获取完整数据
        org_code = values[2]
        try:
            conn = duckdb.connect(self.db_path)
            result = conn.execute(f"SELECT * FROM org_list WHERE org_code = '{org_code}'").fetchone()
            conn.close()

            if result:
                self.show_org_edit_dialog(result)
        except Exception as e:
            messagebox.showerror("错误", f"获取机构数据失败：\n{str(e)}")

    def show_org_edit_dialog(self, org_data=None):
        """显示机构编辑弹窗"""
        top = tk.Toplevel(self.root)
        top.title("编辑机构" if org_data else "新增机构")
        top.resizable(True, True)
        top.attributes('-topmost', True)

        # 计算居中位置
        top.update_idletasks()
        width = 480
        height = 360
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        top.geometry(f"{width}x{height}+{x}+{y}")

        # 两行布局：内容区（可滚动）| 按钮
        top.columnconfigure(0, weight=1)
        top.rowconfigure(0, weight=1)
        top.rowconfigure(1, weight=0)

        # 获取列名
        try:
            conn = duckdb.connect(self.db_path)
            columns = [col[1] for col in conn.execute("PRAGMA table_info('org_list')").fetchall()]
            conn.close()
        except Exception as e:
            messagebox.showerror("错误", f"获取表结构失败：\n{str(e)}")
            top.destroy()
            return

        # 第一行：表单内容区（限制高度，超出自动滚动）
        content_frame = ttk.Frame(top)
        content_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        content_frame.columnconfigure(0, weight=1)

        # 垂直滚动条
        v_scrollbar = ttk.Scrollbar(content_frame)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Canvas + Frame 实现滚动
        canvas = tk.Canvas(content_frame, yscrollcommand=v_scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        scrollable_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def on_canvas_configure(event):
            canvas.itemconfig(scrollable_window, width=event.width)

        canvas.bind('<Configure>', on_canvas_configure)
        v_scrollbar.config(command=canvas.yview)

        # 创建输入控件
        entry_vars = {}
        row_idx = 0

        # 字段中文映射
        FIELD_LABEL_MAP = {
            'city': '地市(州)',
            'org_code': '机构编码',
            'org_name': '机构名称',
            'is_516_flag': '是否516标志',
            'station_hospital': '是否哨点医院',
            'is_412名单': '是否412名单',
        }
        # 必填字段
        REQUIRED_FIELDS = ['city', 'org_code', 'org_name', 'is_516_flag']
        # 下拉选项字段
        DROPDOWN_FIELDS = ['is_412名单', 'is_516_flag', '是否分院区', '是否基层', '是否26', '是否满足实时要求', '是否主院区']

        # 注册数字输入校验函数
        validate_num_cmd = top.register(lambda P: P.isdigit() or P == '')

        for col_name in columns:
            display_name = FIELD_LABEL_MAP.get(col_name, col_name)
            is_required = col_name in REQUIRED_FIELDS
            is_dropdown = col_name in DROPDOWN_FIELDS

            # 必填项标签标红（tk.Label 才支持 fg 颜色设置）
            if is_required:
                label = tk.Label(scrollable_frame, text=f"{display_name}：", fg='red')
            else:
                label = ttk.Label(scrollable_frame, text=f"{display_name}：")
            label.grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=2)

            var = tk.StringVar()
            if org_data and row_idx < len(org_data):
                value = org_data[row_idx]
                var.set(value if value is not None else '')
            entry_vars[col_name] = var

            if is_dropdown:
                # 非必填的下拉框允许选择空值来清空
                combo_values = ("是", "否") if is_required else ("", "是", "否")
                entry = ttk.Combobox(scrollable_frame, textvariable=var, values=combo_values, state="readonly", width=38)
            elif col_name == 'city':
                # 地市(州)下拉选项
                city_values = (
                    "鄂州市", "恩施州", "黄冈市", "黄石市", "荆门市", "荆州市",
                    "潜江市", "神农架林区", "省本级", "十堰市", "随州市", "天门市",
                    "武汉市", "仙桃市", "咸宁市", "襄阳市", "孝感市", "宜昌市"
                )
                entry = ttk.Combobox(scrollable_frame, textvariable=var, values=city_values, width=38)
            elif col_name == 'org_code':
                # 机构编码仅允许输入数字
                entry = ttk.Entry(scrollable_frame, textvariable=var, width=40, validate='key', validatecommand=(validate_num_cmd, '%P'))
            else:
                entry = ttk.Entry(scrollable_frame, textvariable=var, width=40)
            entry.grid(row=row_idx, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)

            row_idx += 1

        scrollable_frame.columnconfigure(1, weight=1)

        # 第二行：保存、取消按钮
        btn_frame = ttk.Frame(top)
        btn_frame.grid(row=1, column=0, pady=5)

        def save():
            try:
                # 必填校验
                for field in REQUIRED_FIELDS:
                    if not entry_vars[field].get().strip():
                        display_name = FIELD_LABEL_MAP.get(field, field)
                        top.attributes('-topmost', False)
                        messagebox.showwarning("提示", f"【{display_name}】为必填项，请输入内容", parent=top)
                        top.attributes('-topmost', True)
                        return

                conn = duckdb.connect(self.db_path)

                if org_data:
                    # 获取原始的 org_code（用于 WHERE 条件）
                    original_org_code = org_data[columns.index('org_code')] if 'org_code' in columns else None
                    
                    # 更新：使用原始 org_code 作为 WHERE 条件
                    if original_org_code:
                        set_clause = ", ".join([f"{col} = '{entry_vars[col].get()}'" for col in columns])
                        sql = f"UPDATE org_list SET {set_clause} WHERE org_code = '{original_org_code}'"
                    else:
                        top.attributes('-topmost', False)
                        messagebox.showerror("错误", "无法获取原始机构代码", parent=top)
                        top.attributes('-topmost', True)
                        conn.close()
                        return
                else:
                    # 新增
                    col_str = ", ".join(columns)
                    val_str = ", ".join([f"'{entry_vars[col].get()}'" for col in columns])
                    sql = f"INSERT INTO org_list ({col_str}) VALUES ({val_str})"

                conn.execute(sql)
                conn.commit()
                conn.close()

                top.attributes('-topmost', False)
                messagebox.showinfo("成功", "机构数据保存成功", parent=top)
                top.attributes('-topmost', True)
                top.destroy()
                self.refresh_org_tree()

                # 提示重新数据加工
                if hasattr(self, 'data_imported') and self.data_imported:
                    messagebox.showwarning(
                        "提示",
                        "机构数据已修改，请重新执行数据加工操作。\n\n请切换到【3. 数据加工】选项卡，点击【执行数据加工SQL】按钮。"
                    )

            except Exception as e:
                top.attributes('-topmost', False)
                messagebox.showerror("错误", f"保存失败：\n{str(e)}", parent=top)
                top.attributes('-topmost', True)

        save_btn = ttk.Button(btn_frame, text="保存", command=save)
        save_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = ttk.Button(btn_frame, text="取消", command=top.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=10)

        top.wait_window()

    def delete_org(self):
        """删除选中的机构"""
        selected = self.org_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选中要删除的机构")
            return

        item = selected[0]
        values = self.org_tree.item(item, 'values')
        org_name = values[3]
        org_code = values[2]

        if messagebox.askyesno("确认删除", f"确定要删除机构【{org_name}】吗？"):
            try:
                conn = duckdb.connect(self.db_path)
                conn.execute(f"DELETE FROM org_list WHERE org_code = '{org_code}'")
                conn.commit()
                conn.close()

                self.refresh_org_tree()
                messagebox.showinfo("成功", "机构删除成功")

                # 提示重新数据加工
                if hasattr(self, 'data_imported') and self.data_imported:
                    messagebox.showwarning(
                        "提示",
                        "机构数据已修改，请重新执行数据加工操作。\n\n请切换到【3. 数据加工】选项卡，点击【执行数据加工SQL】按钮。"
                    )

            except Exception as e:
                messagebox.showerror("错误", f"删除失败：\n{str(e)}")

    def log_message(self, message):
        """输出日志并自动滚动到最新消息"""
        self.export_text.insert(tk.END, message)
        self.export_text.see(tk.END)  # 自动滚动到最新消息
        self.root.update_idletasks()
        
    def select_template(self):
        """选择模板文件"""
        file_path = filedialog.askopenfilename(
            title="选择 Excel 模板文件",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if file_path:
            self.template_path = file_path
            self.template_label.config(text=f"模板文件：{os.path.basename(file_path)}")
            
    def open_report_dir(self):
        """打开质控报告所在目录：已打开则切换过去，未打开则新建打开"""
        # 获取导出文件所在目录（优先使用 _export_dir，兜底用 export_path_var）
        directory = self._export_dir if hasattr(self, '_export_dir') else None
        if not directory:
            file_path = self.export_path_var.get()
            if not file_path:
                messagebox.showwarning("提示", "未设置导出文件路径")
                return
            directory = os.path.dirname(os.path.abspath(file_path))
        if not os.path.isdir(directory):
            # 目录不存在，尝试创建后再打开
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                messagebox.showerror("错误", f"目录不存在且无法创建：\n{directory}\n原因：{str(e)}")
                return

        if sys.platform == 'win32':
            # Windows：先检查是否已有资源管理器窗口打开了该目录
            # 如果已打开，将其置前；未打开则新建打开
            try:
                import ctypes
                from ctypes import wintypes

                SW_SHOW = 5
                SW_RESTORE = 9
                HWND_TOP = 0
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001

                user32 = ctypes.windll.user32
                shell32 = ctypes.windll.shell32

                found_hwnd = ctypes.c_void_p(0)
                dir_normalized = os.path.normpath(directory).lower()

                def enum_windows_proc(hwnd, _lparam):
                    # 只检查可见窗口
                    if not user32.IsWindowVisible(hwnd):
                        return True
                    # 获取窗口类名（应为 "CabinetWClass" 或 "ExploreWClass" 等资源管理器类名）
                    class_name = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(hwnd, class_name, 256)
                    if 'cabinet' not in class_name.value.lower() and 'explore' not in class_name.value.lower():
                        return True
                    # 获取窗口标题（对资源管理器窗口，标题通常是文件夹名或路径）
                    title_length = user32.GetWindowTextLengthW(hwnd)
                    if title_length == 0:
                        return True
                    title_buf = ctypes.create_unicode_buffer(title_length + 1)
                    user32.GetWindowTextW(hwnd, title_buf, title_length + 1)
                    window_title = title_buf.value.lower()
                    # 比较窗口标题或父目录名称是否匹配
                    folder_name = os.path.basename(dir_normalized).lower()
                    if window_title and (window_title == folder_name or dir_normalized in window_title):
                        found_hwnd.value = hwnd
                        return False  # 停止枚举
                    return True

                enum_callback = ctypes.WINFUNCTYPE(
                    ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
                )(enum_windows_proc)
                user32.EnumWindows(enum_callback, 0)

                if found_hwnd.value:
                    # 已打开：将窗口置前并激活
                    if user32.IsIconic(found_hwnd.value):
                        user32.ShowWindow(found_hwnd.value, SW_RESTORE)
                    user32.SetForegroundWindow(found_hwnd.value)
                    user32.BringWindowToTop(found_hwnd.value)
                else:
                    # 未打开：新建打开
                    try:
                        os.startfile(directory)
                    except Exception:
                        import subprocess
                        subprocess.Popen(['explorer', directory])
            except Exception:
                # 兜底方案：直接用资源管理器打开
                try:
                    os.startfile(directory)
                except Exception:
                    import subprocess
                    subprocess.Popen(['explorer', directory])
        elif sys.platform == 'darwin':
            # macOS：使用 open 命令打开 Finder
            import subprocess
            subprocess.Popen(['open', directory])
        else:
            # Linux：使用 xdg-open
            import subprocess
            subprocess.Popen(['xdg-open', directory])

    def _find_writable_export_dir(self):
        """寻找一个可写的默认导出目录
        Windows：优先用 SHGetFolderPath 获取真实 Documents 路径（支持中文系统）
        通用：Documents → 桌面 → 用户主目录 → 兜底到 app_base_dir
        """
        candidates = []

        if sys.platform == 'win32':
            # 用 Windows API 获取真实路径（兼容"文档"等本地化名称）
            try:
                import ctypes
                from ctypes import wintypes
                CSIDL_PERSONAL = 0x0005       # Documents
                CSIDL_DESKTOPDIRECTORY = 0x0010  # 桌面
                SHGFP_TYPE_CURRENT = 0

                buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(
                    0, CSIDL_PERSONAL, 0, SHGFP_TYPE_CURRENT, buf
                )
                if buf.value:
                    candidates.append(buf.value)

                buf2 = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(
                    0, CSIDL_DESKTOPDIRECTORY, 0, SHGFP_TYPE_CURRENT, buf2
                )
                if buf2.value:
                    candidates.append(buf2.value)
            except Exception:
                pass

        # 通用候选（跨平台）
        home = os.path.expanduser('~')
        candidates.extend([
            os.path.join(home, 'Documents'),
            os.path.join(home, 'Desktop'),
            os.path.join(home, '桌面'),
            home,
        ])

        # 逐个检查是否存在且可写
        for dir_path in candidates:
            if dir_path and os.path.isdir(dir_path) and os.access(dir_path, os.W_OK):
                return dir_path

        # 最终兜底
        if os.access(self.app_base_dir, os.W_OK):
            return self.app_base_dir
        return home  # home 目录几乎总是可写的

    def choose_export_dir(self):
        """选择报告保存目录"""
        directory = filedialog.askdirectory(
            title="选择报告保存目录",
            initialdir=self._export_dir
        )
        if directory:
            self._export_dir = directory
            # 重新拼接完整路径
            filename = self.export_name_var.get()
            self.export_path_var.set(os.path.join(directory, filename))

    def export_report(self):
        """导出报告"""
        if not self.template_path:
            messagebox.showwarning("警告", "请先选择模板文件")
            return
            
        def do_export():
            try:
                from openpyxl import load_workbook
                
                self.export_status_label.config(text="导出状态：处理中...", foreground="orange")
                self.export_progress.start()
                self.export_text.delete(1.0, tk.END)
                
                self.log_message("加载模板文件...\n")
                wb = load_workbook(self.template_path)
                
                self.log_message("连接数据库...\n")
                conn = duckdb.connect(self.db_path)
                
                # Sheet 名称到 SQL 方法的映射
                sheet_method_map = {
                    '地市(州)': self.get_city_state_sql,
                    '机构汇总': self.get_org_summary_sql,
                    '时效性明细': self.get_realtime_detail_sql,
                    '必填字段完整性': self.get_column_level1_sql,
                    '重要建议填字段完整性': self.get_column_level2_sql,
                    '条件必填字段完整性': self.get_column_level3_sql,
                    '第二批次更新字段明细': self.get_column_version_2_sql,
                    '关联关系明细': self.get_association_sql,
                    '业务主键唯一率': self.get_business_sql,
                    '主诉明细': self.get_chief_sql,
                    '现病史明细': self.get_present_sql
                }
                
                # 根据当前处室获取需要导出的 Sheet 列表
                dept_config = self.get_current_dept_config()
                export_sheet_names = dept_config.get("export_sheets", list(sheet_method_map.keys()))
                export_sheets = {name: sheet_method_map[name]() for name in export_sheet_names if name in sheet_method_map}
                
                
                total_sheets = len(export_sheets)
                processed = 0
                
                for sheet_idx, (sheet_name, sql) in enumerate(export_sheets.items(), 1):
                    try:
                        self.log_message(f"\n[{sheet_idx}/{total_sheets}] 处理 Sheet: {sheet_name}...\n")
                        
                        if sheet_name in wb.sheetnames:
                            ws = wb[sheet_name]
                            
                            self.log_message(f"  执行 SQL 查询...\n")
                            self.root.update_idletasks()
                            
                            df = pd.read_sql_query(sql, conn)
                            record_count = len(df)
                            self.log_message(f"  查询到 {record_count} 条记录\n")
                            self.root.update_idletasks()
                            
                            start_row = 4
                        
                        # 优化写入操作：批量写入
                        if record_count > 0:
                            # 使用 append 方法批量写入，比逐个单元格写入快 10-100 倍
                            values = df.values.tolist()
                            
                            # 检查第一行是否是合计行
                            has_total_row = False
                            total_row_data = None
                            if len(values) > 0 and values[0][0] in ['Total', '合计']:
                                has_total_row = True
                                total_row_data = values[0]  # 保存合计行数据
                                # 将第一列的值修改为"合计"
                                total_row_data[0] = '合计'
                                values = values[1:]  # 移除第一行合计
                                record_count = len(values)
                            
                            # 批量追加数据 (先写数据行)
                            for row_values in values:
                                ws.append(row_values)
                            
                            # 在末尾写入合计行
                            if has_total_row and total_row_data:
                                # 导入样式模块
                                from openpyxl.styles import Font, PatternFill, Alignment
                                
                                # 黄色背景填充
                                yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
                                # 粗体字体
                                bold_font = Font(bold=True)
                                # 居中对齐
                                center_alignment = Alignment(horizontal='center', vertical='center')
                                
                                # 写入合计行到最后一行
                                ws.append(total_row_data)
                                total_row = ws.max_row
                                
                                # 应用黄色背景、粗体字体和居中对齐到合计行
                                for col_idx in range(1, len(total_row_data) + 1):
                                    cell = ws.cell(row=total_row, column=col_idx)
                                    cell.fill = yellow_fill
                                    cell.font = bold_font
                                    # 除 A 列外都居中对齐
                                    if col_idx > 1:
                                        cell.alignment = center_alignment
                                
                                self.log_message(f"  ✓ 已创建合计行（黄色背景、粗体）\n")
                            
                            # 设置地市(州)Sheet 页的对齐方式：除 A 列外所有单元格居中
                            if sheet_name == '地市(州)':
                                from openpyxl.styles import Alignment
                                center_alignment = Alignment(horizontal='center', vertical='center')
                                
                                # 遍历所有数据行（从第 4 行到最后一行）
                                for row_idx in range(start_row, ws.max_row + 1):
                                    # 从 B 列开始（第 2 列）到最后一列
                                    for col_idx in range(2, ws.max_column + 1):
                                        cell = ws.cell(row=row_idx, column=col_idx)
                                        cell.alignment = center_alignment
                            
                            self.log_message(f"  写入完成，共 {record_count} 条记录\n")
                            
                            processed += 1
                            self.log_message(f"  ✓ 导出成功\n")
                            self.root.update_idletasks()
                        else:
                            self.log_message(f"  ✗ Sheet 不存在，跳过\n")
                            self.root.update_idletasks()
                            
                    except Exception as e:
                        self.log_message(f"  ✗ 错误：{str(e)}\n")
                        import traceback
                        self.log_message(f"  {traceback.format_exc()}\n")
                
                conn.close()
                
                # 设置列宽 (在地市 (州)Sheet 页之后)
                self.log_message(f"\n设置列宽...\n")
                
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    
                    # 地市 (州)Sheet 页使用自定义列宽
                    if sheet_name == '地市 (州)':
                        # 地市 (州)Sheet 页：A 列（地市）列宽 12，B 列开始根据表头设置
                        try:
                            ws.column_dimensions['A'].width = 12  # 地市
                            # 遍历其他列，根据第 3 行的表头设置列宽
                            for col_idx in range(2, ws.max_column + 1):
                                # 使用列索引直接获取列字母，避免合并单元格问题
                                from openpyxl.utils import get_column_letter
                                col_letter = get_column_letter(col_idx)
                                header_value = ws.cell(row=3, column=col_idx).value
                                
                                if header_value:
                                    header_str = str(header_value)
                                    if '机构编码' in header_str or 'org_code' in header_str.lower():
                                        ws.column_dimensions[col_letter].width = 12
                                    elif '机构名称' in header_str or 'org_name' in header_str.lower():
                                        ws.column_dimensions[col_letter].width = 24
                            
                            self.log_message(f"  ✓ {sheet_name}: 已设置列宽\n")
                        except Exception as e:
                            self.log_message(f"  ✗ {sheet_name}: 列宽设置失败 - {str(e)}\n")
                    else:
                        # 其他 Sheet 页：根据列名设置列宽
                        try:
                            # 遍历所有列
                            for col_idx in range(1, ws.max_column + 1):
                                # 使用列索引直接获取列字母，避免合并单元格问题
                                from openpyxl.utils import get_column_letter
                                col_letter = get_column_letter(col_idx)
                                header_value = ws.cell(row=3, column=col_idx).value
                                
                                # 根据列名设置列宽
                                if header_value:
                                    header_str = str(header_value)
                                    if '机构编码' in header_str or 'org_code' in header_str.lower():
                                        ws.column_dimensions[col_letter].width = 12
                                        self.log_message(f"  ✓ {sheet_name}: {header_str} 列宽设置为 12\n")
                                    elif '机构名称' in header_str or 'org_name' in header_str.lower():
                                        ws.column_dimensions[col_letter].width = 24
                                        self.log_message(f"  ✓ {sheet_name}: {header_str} 列宽设置为 24\n")
                                    elif any(keyword in header_str for keyword in 
                                             ['表名称', '表注释', '关联表名称', '关联表注释', 
                                              '列名称', '列注释', 'table_name', 'table_comment',
                                              'column_name', 'column_comment']):
                                        ws.column_dimensions[col_letter].width = 29
                                        self.log_message(f"  ✓ {sheet_name}: {header_str} 列宽设置为 29\n")
                            
                            self.log_message(f"  ✓ {sheet_name}: 已设置列宽\n")
                        except Exception as e:
                            self.log_message(f"  ✗ {sheet_name}: 列宽设置失败 - {str(e)}\n")
                
                self.root.update_idletasks()
                
                # 设置单元格对齐方式：指定列居中
                self.log_message(f"\n设置对齐方式...\n")
                
                # 需要居中的列名关键词
                center_keywords = [
                    '纳入统计记录数', '达标数据量', '达标率',
                    '不为空记录数', '完整率', '关联记录数', '关联率',
                    '纳入统计数据条数', '值域在有效范围的数据条数', '值域在有效范围的数据占比',
                    '达标机构数', '达标率 (%)'
                ]
                
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    
                    try:
                        from openpyxl.styles import Alignment
                        
                        # 创建居中对齐样式
                        center_alignment = Alignment(horizontal='center', vertical='center')
                        
                        # 遍历第 3 行（表头行）查找需要居中的列
                        for col_idx in range(1, ws.max_column + 1):
                            header_value = ws.cell(row=3, column=col_idx).value
                            
                            if header_value:
                                header_str = str(header_value)
                                # 检查是否包含需要居中的关键词
                                if any(keyword in header_str for keyword in center_keywords):
                                    col_letter = ws.cell(row=1, column=col_idx).column_letter
                                    
                                    # 设置该列所有数据单元格居中（从第 4 行开始）
                                    for row_idx in range(4, ws.max_row + 1):
                                        cell = ws.cell(row=row_idx, column=col_idx)
                                        cell.alignment = center_alignment
                                    
                                    self.log_message(f"  ✓ {sheet_name}: {header_str} 已设置居中\n")
                    except Exception as e:
                        pass  # 忽略错误，继续处理
                
                self.root.update_idletasks()
                
                # 使用用户可写目录 + 文件名组成完整路径
                export_path = self.export_name_var.get()
                full_path = self.export_path_var.get()
                self.log_message(f"\n保存文件到：{full_path}...\n")

                # 确保目录存在且可写
                export_dir = os.path.dirname(full_path)
                try:
                    os.makedirs(export_dir, exist_ok=True)
                    # 测试写入权限
                    test_file = os.path.join(export_dir, '.write_test_tmp')
                    with open(test_file, 'w') as tf:
                        tf.write('test')
                    os.remove(test_file)
                except Exception:
                    # 目录不可写，回退到用户文档目录
                    fallback_dir = os.path.expanduser('~/Documents')
                    if os.path.isdir(fallback_dir) and os.access(fallback_dir, os.W_OK):
                        self.log_message(f"  ⚠ 目标目录不可写，回退到：{fallback_dir}\n")
                        full_path = os.path.join(fallback_dir, export_path)
                        self._export_dir = fallback_dir
                        self.export_path_var.set(full_path)
                    else:
                        raise Exception(f"导出目录不可写：{export_dir}\n请使用【选择保存目录】按钮指定一个可写的位置")

                wb.save(full_path)
                
                self.export_progress.stop()
                self.export_status_label.config(text="导出状态：完成", foreground="green")
                self.log_message(f"\n✓ 报告已成功导出到：{full_path}\n")
                self.log_message(f"✓ 共处理 {processed}/{total_sheets} 个 Sheet 页\n")
                
                # 显示带滚动条的消息框
                messagebox.showinfo("报告生成", f"导出成功！\n\n文件位置：{full_path}")
                
            except Exception as e:
                self.export_progress.stop()
                self.export_status_label.config(text="导出状态：失败", foreground="red")
                import traceback
                error_msg = f"错误：{str(e)}\n\n{traceback.format_exc()}"
                self.log_message(f"\n{error_msg}\n")
                messagebox.showerror("错误", f"导出失败:\n{str(e)}")
                
        thread = threading.Thread(target=do_export)
        thread.start()
    
    def show_scrollable_messagebox(self, title, message):
        """显示带垂直滚动条的消息框"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 创建文本框和滚动条
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, height=20, width=70)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=text_widget.yview)
        
        # 插入消息内容
        text_widget.insert(tk.END, message)
        text_widget.config(state=tk.DISABLED)  # 设为只读
        
        # 添加按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(0, 20))
        
        ok_btn = ttk.Button(btn_frame, text="确定", command=dialog.destroy)
        ok_btn.pack()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        dialog.wait_window()

    def get_national_condition(self):
        """获取national_flag和业务处室过滤条件（配置驱动）"""
        dept_config = self.get_current_dept_config()
        dept_flag = dept_config["table_flag"]

        condition = f"and c.{dept_flag}='1'"

        # 仅预警处有省标/国标区分；其他处室强制不附加 national_flag 条件
        if dept_config.get("has_national_flag") and self.national_flag_var.get() == "national":
            condition += " and c.national_flag='1'"

        return condition
        
	
            
    # 获取地市州汇总 SQL
    def get_city_state_sql(self):
        """地市州汇总 SQL 分发方法"""
        # 处室存在专属地市汇总 SQL 时优先使用（如应急处(41张表)含2小时列）
        dept_key = self.get_dept_key()
        own_method = getattr(self, f'get_{dept_key}_city_state_sql', None)
        if own_method:
            return own_method()
        variant = self.get_sql_variant()
        if variant == "early_warning": # 预警处
            return self.get_early_warning_city_state_sql()
        elif variant == "emergency_warning": # 应急处（含41张表）
            return self.get_emergency_warning_city_state_sql()
        else: # 药政处
            return self.get_medicine_regulatory_city_state_sql()

    def get_early_warning_city_state_sql(self):
        """预警处地市汇总 SQL"""
        return f"""
        select distinct city,
           org_cnt,
           real_cnt,
           concat(round((real_cnt / org_cnt) * 100, 2), '%') as real_rate,
           hour_cnt,
           concat(round((hour_cnt / org_cnt) * 100, 2), '%') as hour_rate,
           other_cnt,
           concat(round((other_cnt / org_cnt) * 100, 2), '%') as other_rate,
           e_total_records,
           e_notnull_records,
           case when e_total_records >0 then
           concat(round((e_notnull_records / e_total_records) * 100, 2), '%') end as e_notnull_rate,
           f_total_records,
           f_notnull_records,
           case when f_total_records >0 then
           concat(round((f_notnull_records / f_total_records) * 100, 2), '%') end as f_notnull_rate,
           g_total_records,
           g_notnull_records,
           case when g_total_records >0 then
           concat(round((g_notnull_records / g_total_records) * 100, 2), '%') end as g_notnull_rate,
           h_total_records,
           h_notnull_records,
           case when h_total_records >0 then
           concat(round((h_notnull_records / h_total_records) * 100, 2), '%') end as h_notnull_rate,
           i_total_records,
           i_notnull_records,
           case when i_total_records >0 then
           concat(round((i_notnull_records / i_total_records) * 100, 2), '%') end as i_notnull_rate,
           j_total_records,
           j_notnull_records,
           case when j_total_records >0 then
           concat(round((j_notnull_records / j_total_records) * 100, 2), '%') end as j_notnull_rate,
           k_total_records,
           k_notnull_records,
           case when k_total_records >0 then
           concat(round((k_notnull_records / k_total_records) * 100, 2), '%') end as k_notnull_rate,
           association_org_cnt,
           concat(round((association_org_cnt / org_cnt) * 100, 2), '%') as association__rate
        from prov_city_summary a
        union
        select 'Total',
           sum(org_cnt),
           sum(real_cnt),
           concat(round((sum(real_cnt) / sum(org_cnt)) * 100, 2), '%') as real_rate,
           sum(hour_cnt),
           concat(round((sum(hour_cnt) / sum(org_cnt)) * 100, 2), '%') as hour_rate,
           sum(other_cnt),
           concat(round((sum(other_cnt) / sum(org_cnt)) * 100, 2), '%') as other_rate,
           sum(e_total_records),
           sum(e_notnull_records),
           concat(round((sum(e_notnull_records) / sum(e_total_records)) * 100, 2), '%') as e_notnull_rate,
           sum(f_total_records),
           sum(f_notnull_records),
           concat(round((sum(f_notnull_records) / sum(f_total_records)) * 100, 2), '%') as f_notnull_rate,
           sum(g_total_records),
           sum(g_notnull_records),
           concat(round((sum(g_notnull_records) / sum(g_total_records)) * 100, 2), '%') as g_notnull_rate,
           sum(h_total_records),
           sum(h_notnull_records),
           concat(round((sum(h_notnull_records) / sum(h_total_records)) * 100, 2), '%') as h_notnull_rate,
           sum(i_total_records),
           sum(i_notnull_records),
           concat(round((sum(i_notnull_records) / sum(i_total_records)) * 100, 2), '%') as i_notnull_rate,
           sum(j_total_records),
           sum(j_notnull_records),
           concat(round((sum(j_notnull_records) / sum(j_total_records)) * 100, 2), '%') as j_notnull_rate,
           sum(k_total_records),
           sum(k_notnull_records),
           concat(round((sum(k_notnull_records) / sum(k_total_records)) * 100, 2), '%') as k_notnull_rate,
           sum(association_org_cnt),
           concat(round((sum(association_org_cnt) / sum(org_cnt)) * 100, 2), '%') as association__rate 
        from prov_city_summary
        order by city
        """

    def get_emergency_warning_city_state_sql(self):
        """应急处地市汇总 SQL"""
        return f"""
        select distinct city,
           org_cnt,
           real_cnt,
           concat(round((real_cnt / org_cnt) * 100, 2), '%') as real_rate,
           other_cnt,
           concat(round((other_cnt / org_cnt) * 100, 2), '%') as other_rate,
           e_total_records,
           e_notnull_records,
           case when e_total_records >0 then
           concat(round((e_notnull_records / e_total_records) * 100, 2), '%') end as e_notnull_rate,
           f_total_records,
           f_notnull_records,
           case when f_total_records >0 then
           concat(round((f_notnull_records / f_total_records) * 100, 2), '%') end as f_notnull_rate,
           g_total_records,
           g_notnull_records,
           case when g_total_records >0 then
           concat(round((g_notnull_records / g_total_records) * 100, 2), '%') end as g_notnull_rate,
           h_total_records,
           h_notnull_records,
           case when h_total_records >0 then
           concat(round((h_notnull_records / h_total_records) * 100, 2), '%') end as h_notnull_rate,
           j_total_records,
           j_notnull_records,
           case when j_total_records >0 then
           concat(round((j_notnull_records / j_total_records) * 100, 2), '%') end as j_notnull_rate,
           k_total_records,
           k_notnull_records,
           case when k_total_records >0 then
           concat(round((k_notnull_records / k_total_records) * 100, 2), '%') end as k_notnull_rate,
           association_org_cnt,
           concat(round((association_org_cnt / org_cnt) * 100, 2), '%') as association__rate
        from prov_city_summary a
        union
        select 'Total',
           sum(org_cnt),
           sum(real_cnt),
           concat(round((sum(real_cnt) / sum(org_cnt)) * 100, 2), '%') as real_rate,
           sum(other_cnt),
           concat(round((sum(other_cnt) / sum(org_cnt)) * 100, 2), '%') as other_rate,
           sum(e_total_records),
           sum(e_notnull_records),
           concat(round((sum(e_notnull_records) / sum(e_total_records)) * 100, 2), '%') as e_notnull_rate,
           sum(f_total_records),
           sum(f_notnull_records),
           concat(round((sum(f_notnull_records) / sum(f_total_records)) * 100, 2), '%') as f_notnull_rate,
           sum(g_total_records),
           sum(g_notnull_records),
           concat(round((sum(g_notnull_records) / sum(g_total_records)) * 100, 2), '%') as g_notnull_rate,
           sum(h_total_records),
           sum(h_notnull_records),
           concat(round((sum(h_notnull_records) / sum(h_total_records)) * 100, 2), '%') as h_notnull_rate,
           sum(j_total_records),
           sum(j_notnull_records),
           concat(round((sum(j_notnull_records) / sum(j_total_records)) * 100, 2), '%') as j_notnull_rate,
           sum(k_total_records),
           sum(k_notnull_records),
           concat(round((sum(k_notnull_records) / sum(k_total_records)) * 100, 2), '%') as k_notnull_rate,
           sum(association_org_cnt),
           concat(round((sum(association_org_cnt) / sum(org_cnt)) * 100, 2), '%') as association__rate 
        from prov_city_summary
        order by city
        """

    def get_emergency_warning_all_city_state_sql(self):
        """应急处(41张表)地市汇总 SQL（含2小时列，共28列）"""
        return f"""
        select distinct city,
           org_cnt,
           real_cnt,
           concat(round((real_cnt / org_cnt) * 100, 2), '%') as real_rate,
           hour_cnt,
           concat(round((hour_cnt / org_cnt) * 100, 2), '%') as hour_rate,
           other_cnt,
           concat(round((other_cnt / org_cnt) * 100, 2), '%') as other_rate,
           e_total_records,
           e_notnull_records,
           case when e_total_records >0 then
           concat(round((e_notnull_records / e_total_records) * 100, 2), '%') end as e_notnull_rate,
           f_total_records,
           f_notnull_records,
           case when f_total_records >0 then
           concat(round((f_notnull_records / f_total_records) * 100, 2), '%') end as f_notnull_rate,
           g_total_records,
           g_notnull_records,
           case when g_total_records >0 then
           concat(round((g_notnull_records / g_total_records) * 100, 2), '%') end as g_notnull_rate,
           h_total_records,
           h_notnull_records,
           case when h_total_records >0 then
           concat(round((h_notnull_records / h_total_records) * 100, 2), '%') end as h_notnull_rate,
           j_total_records,
           j_notnull_records,
           case when j_total_records >0 then
           concat(round((j_notnull_records / j_total_records) * 100, 2), '%') end as j_notnull_rate,
           k_total_records,
           k_notnull_records,
           case when k_total_records >0 then
           concat(round((k_notnull_records / k_total_records) * 100, 2), '%') end as k_notnull_rate,
           association_org_cnt,
           concat(round((association_org_cnt / org_cnt) * 100, 2), '%') as association__rate
        from prov_city_summary a
        union
        select 'Total',
           sum(org_cnt),
           sum(real_cnt),
           concat(round((sum(real_cnt) / sum(org_cnt)) * 100, 2), '%') as real_rate,
           sum(hour_cnt),
           concat(round((sum(hour_cnt) / sum(org_cnt)) * 100, 2), '%') as hour_rate,
           sum(other_cnt),
           concat(round((sum(other_cnt) / sum(org_cnt)) * 100, 2), '%') as other_rate,
           sum(e_total_records),
           sum(e_notnull_records),
           concat(round((sum(e_notnull_records) / sum(e_total_records)) * 100, 2), '%') as e_notnull_rate,
           sum(f_total_records),
           sum(f_notnull_records),
           concat(round((sum(f_notnull_records) / sum(f_total_records)) * 100, 2), '%') as f_notnull_rate,
           sum(g_total_records),
           sum(g_notnull_records),
           concat(round((sum(g_notnull_records) / sum(g_total_records)) * 100, 2), '%') as g_notnull_rate,
           sum(h_total_records),
           sum(h_notnull_records),
           concat(round((sum(h_notnull_records) / sum(h_total_records)) * 100, 2), '%') as h_notnull_rate,
           sum(j_total_records),
           sum(j_notnull_records),
           concat(round((sum(j_notnull_records) / sum(j_total_records)) * 100, 2), '%') as j_notnull_rate,
           sum(k_total_records),
           sum(k_notnull_records),
           concat(round((sum(k_notnull_records) / sum(k_total_records)) * 100, 2), '%') as k_notnull_rate,
           sum(association_org_cnt),
           concat(round((sum(association_org_cnt) / sum(org_cnt)) * 100, 2), '%') as association__rate 
        from prov_city_summary
        order by city
        """

    def get_medicine_regulatory_city_state_sql(self):
        """药政处地市汇总 SQL"""
        return f"""
        select distinct city,
           org_cnt,
           other_cnt,
           concat(round((other_cnt / org_cnt) * 100, 2), '%') as other_rate,
           e_total_records,
           e_notnull_records,
           case when e_total_records >0 then
           concat(round((e_notnull_records / e_total_records) * 100, 2), '%') end as e_notnull_rate,
           f_total_records,
           f_notnull_records,
           case when f_total_records >0 then
           concat(round((f_notnull_records / f_total_records) * 100, 2), '%') end as f_notnull_rate,
           g_total_records,
           g_notnull_records,
           case when g_total_records >0 then
           concat(round((g_notnull_records / g_total_records) * 100, 2), '%') end as g_notnull_rate,
           h_total_records,
           h_notnull_records,
           case when h_total_records >0 then
           concat(round((h_notnull_records / h_total_records) * 100, 2), '%') end as h_notnull_rate,
           i_total_records,
           i_notnull_records,
           case when i_total_records >0 then
           concat(round((i_notnull_records / i_total_records) * 100, 2), '%') end as i_notnull_rate,
           j_total_records,
           j_notnull_records,
           case when j_total_records >0 then
           concat(round((j_notnull_records / j_total_records) * 100, 2), '%') end as j_notnull_rate,
           k_total_records,
           k_notnull_records,
           case when k_total_records >0 then
           concat(round((k_notnull_records / k_total_records) * 100, 2), '%') end as k_notnull_rate,
           association_org_cnt,
           concat(round((association_org_cnt / org_cnt) * 100, 2), '%') as association__rate
        from prov_city_summary a
        union
        select 'Total',
           sum(org_cnt),
           sum(other_cnt),
           concat(round((sum(other_cnt) / sum(org_cnt)) * 100, 2), '%') as other_rate,
           sum(e_total_records),
           sum(e_notnull_records),
           concat(round((sum(e_notnull_records) / sum(e_total_records)) * 100, 2), '%') as e_notnull_rate,
           sum(f_total_records),
           sum(f_notnull_records),
           concat(round((sum(f_notnull_records) / sum(f_total_records)) * 100, 2), '%') as f_notnull_rate,
           sum(g_total_records),
           sum(g_notnull_records),
           concat(round((sum(g_notnull_records) / sum(g_total_records)) * 100, 2), '%') as g_notnull_rate,
           sum(h_total_records),
           sum(h_notnull_records),
           concat(round((sum(h_notnull_records) / sum(h_total_records)) * 100, 2), '%') as h_notnull_rate,
           sum(i_total_records),
           sum(i_notnull_records),
           concat(round((sum(i_notnull_records) / sum(i_total_records)) * 100, 2), '%') as i_notnull_rate,
           sum(j_total_records),
           sum(j_notnull_records),
           concat(round((sum(j_notnull_records) / sum(j_total_records)) * 100, 2), '%') as j_notnull_rate,
           sum(k_total_records),
           sum(k_notnull_records),
           concat(round((sum(k_notnull_records) / sum(k_total_records)) * 100, 2), '%') as k_notnull_rate,
           sum(association_org_cnt),
           concat(round((sum(association_org_cnt) / sum(org_cnt)) * 100, 2), '%') as association__rate 
        from prov_city_summary
        order by city
        """

        

    # 获取机构汇总 SQL
    def get_org_summary_sql(self):
        """机构汇总 SQL 分发方法"""
        # 处室存在专属机构汇总 SQL 时优先使用（如应急处(41张表)含2小时列）
        dept_key = self.get_dept_key()
        own_method = getattr(self, f'get_{dept_key}_org_summary_sql', None)
        if own_method:
            return own_method()
        variant = self.get_sql_variant()
        if variant == "early_warning":
            return self.get_early_warning_org_summary_sql()
        elif variant == "emergency_warning":
            return self.get_emergency_warning_org_summary_sql()
        else:
            return self.get_medicine_regulatory_org_summary_sql()

    # 获取预警处机构汇总 SQL
    def get_early_warning_org_summary_sql(self):
        """预警处机构汇总 SQL"""
        return f"""
        select distinct a.city, a.org_code, a.org_name,
           b.total_records, b.compliance_records,
           case when b.total_records is null then null when b.total_records = 0 then '-' else concat(b.compliance_rate, '%') end compliance_rate,
           c.total_records, c.compliance_records,
           case when c.total_records is null then null when c.total_records = 0 then '-' else concat(c.compliance_rate, '%') end compliance_rate,
           d.total_records, d.compliance_records,
           case when d.total_records is null then null when d.total_records = 0 then '-' else concat(d.compliance_rate, '%') end compliance_rate,
           e.total_records,
           e.notnull_records,
           case when e.total_records is null then null when e.total_records = 0 then '-' else concat(e.notnull_rate, '%') end notnull_rate,
           f.total_records,
           f.notnull_records,
           case when f.total_records is null then null when f.total_records = 0 then '-' else concat(f.notnull_rate, '%') end notnull_rate,
           g.total_records,
           g.notnull_records,
           case when g.total_records is null then null when g.total_records = 0 then '-' else concat(g.notnull_rate, '%') end notnull_rate,
           h.total_records,
           h.notnull_records,
           case when h.total_records is null then null when h.total_records = 0 then '-' else concat(h.notnull_rate, '%') end notnull_rate,
           i.total_records,
           i.notnull_records,
           case when i.total_records is null then null when i.total_records = 0 then '-' else concat(i.notnull_rate, '%') end notnull_rate,
           j.total_records,
           j.notnull_records,
           case when j.total_records is null then null when j.total_records = 0 then '-' else concat(j.notnull_rate, '%') end notnull_rate,
           k.total_records,
           k.notnull_records,
           case when k.total_records is null then null when k.total_records = 0 then '-' else concat(k.notnull_rate, '%') end notnull_rate,
           l.total_records,
           l.association_records,
           case when l.total_records is null then null when l.total_records = 0 then '-' else concat(l.association_rate, '%') end association_rate,
           m.total_records,
           m.association_records,
           case when m.total_records is null then null when m.total_records = 0 then '-' else concat(m.association_rate, '%') end association_rate,
           n.total_records,
           n.association_records,
           case when n.total_records is null then null when n.total_records = 0 then '-' else concat(n.association_rate, '%') end association_rate
        from org_list a
         left join prov_timeliness_org b on b.org_code = a.org_code and b.table_level = '1'
         left join prov_timeliness_org c on c.org_code = a.org_code and c.table_level = '2'
         left join prov_timeliness_org d on d.org_code = a.org_code and d.table_level = '3'
         left join prov_column_level_org e on e.org_code = a.org_code and e.column_level = '1'
         left join prov_column_level_org f on f.org_code = a.org_code and f.column_level = '2'
         left join prov_column_level_org g on g.org_code = a.org_code and g.column_level = '3'
         left join prov_column_level_org h on h.org_code = a.org_code and h.column_level = 'update_1'
         left join prov_column_level_org i on i.org_code = a.org_code and i.column_level = 'update_3'
         left join prov_column_level_org j on j.org_code = a.org_code and j.column_level = 'version_2_column_level_1'
         left join prov_column_level_org k on k.org_code = a.org_code and k.column_level = 'version_2_column_level_3'
         left join prov_association_org l on l.org_code = a.org_code and l.association_table = 'pro_base_person_ylfw'
         left join prov_association_org m on m.org_code = a.org_code and m.association_table = 'pro_opt_diagnosisbreakdown,pro_ipt_diagnosisbreakdown'
         left join prov_association_org n on n.org_code = a.org_code and n.association_table = 'all'
        where a.is_516_flag = '是'
        order by a.city, a.org_code
        """

    # 获取应急处机构汇总 SQL
    def get_emergency_warning_org_summary_sql(self):
        """应急处机构汇总 SQL"""
        return f"""
        select distinct a.city, a.org_code, a.org_name,
           b.total_records, b.compliance_records,
           case when b.total_records is null then null when b.total_records = 0 then '-' else concat(b.compliance_rate, '%') end compliance_rate,
           d.total_records, d.compliance_records,
           case when d.total_records is null then null when d.total_records = 0 then '-' else concat(d.compliance_rate, '%') end compliance_rate,
           e.total_records,
           e.notnull_records,
           case when e.total_records is null then null when e.total_records = 0 then '-' else concat(e.notnull_rate, '%') end notnull_rate,
           f.total_records,
           f.notnull_records,
           case when f.total_records is null then null when f.total_records = 0 then '-' else concat(f.notnull_rate, '%') end notnull_rate,
           g.total_records,
           g.notnull_records,
           case when g.total_records is null then null when g.total_records = 0 then '-' else concat(g.notnull_rate, '%') end notnull_rate,
           h.total_records,
           h.notnull_records,
           case when h.total_records is null then null when h.total_records = 0 then '-' else concat(h.notnull_rate, '%') end notnull_rate,
           j.total_records,
           j.notnull_records,
           case when j.total_records is null then null when j.total_records = 0 then '-' else concat(j.notnull_rate, '%') end notnull_rate,
           k.total_records,
           k.notnull_records,
           case when k.total_records is null then null when k.total_records = 0 then '-' else concat(k.notnull_rate, '%') end notnull_rate,
           l.total_records,
           l.association_records,
           case when l.total_records is null then null when l.total_records = 0 then '-' else concat(l.association_rate, '%') end association_rate,
           m.total_records,
           m.association_records,
           case when m.total_records is null then null when m.total_records = 0 then '-' else concat(m.association_rate, '%') end association_rate,
           n.total_records,
           n.association_records,
           case when n.total_records is null then null when n.total_records = 0 then '-' else concat(n.association_rate, '%') end association_rate
        from org_list a
         left join prov_timeliness_org b on b.org_code = a.org_code and b.table_level = '1'
         left join prov_timeliness_org d on d.org_code = a.org_code and d.table_level = '3'
         left join prov_column_level_org e on e.org_code = a.org_code and e.column_level = '1'
         left join prov_column_level_org f on f.org_code = a.org_code and f.column_level = '2'
         left join prov_column_level_org g on g.org_code = a.org_code and g.column_level = '3'
         left join prov_column_level_org h on h.org_code = a.org_code and h.column_level = 'update_1'
         left join prov_column_level_org j on j.org_code = a.org_code and j.column_level = 'version_2_column_level_1'
         left join prov_column_level_org k on k.org_code = a.org_code and k.column_level = 'version_2_column_level_3'
         left join prov_association_org l on l.org_code = a.org_code and l.association_table = 'master'
         left join prov_association_org m on m.org_code = a.org_code and m.association_table = 'other'
         left join prov_association_org n on n.org_code = a.org_code and n.association_table = 'all'
        where a.is_516_flag = '是'
        order by a.city, a.org_code
        """

    def get_emergency_warning_all_org_summary_sql(self):
        """应急处(41张表)机构汇总 SQL（含2小时列，共39列）"""
        return f"""
        select distinct a.city, a.org_code, a.org_name,
           b.total_records, b.compliance_records,
           case when b.total_records is null then null when b.total_records = 0 then '-' else concat(b.compliance_rate, '%') end compliance_rate,
           c.total_records, c.compliance_records,
           case when c.total_records is null then null when c.total_records = 0 then '-' else concat(c.compliance_rate, '%') end compliance_rate,
           d.total_records, d.compliance_records,
           case when d.total_records is null then null when d.total_records = 0 then '-' else concat(d.compliance_rate, '%') end compliance_rate,
           e.total_records,
           e.notnull_records,
           case when e.total_records is null then null when e.total_records = 0 then '-' else concat(e.notnull_rate, '%') end notnull_rate,
           f.total_records,
           f.notnull_records,
           case when f.total_records is null then null when f.total_records = 0 then '-' else concat(f.notnull_rate, '%') end notnull_rate,
           g.total_records,
           g.notnull_records,
           case when g.total_records is null then null when g.total_records = 0 then '-' else concat(g.notnull_rate, '%') end notnull_rate,
           h.total_records,
           h.notnull_records,
           case when h.total_records is null then null when h.total_records = 0 then '-' else concat(h.notnull_rate, '%') end notnull_rate,
           j.total_records,
           j.notnull_records,
           case when j.total_records is null then null when j.total_records = 0 then '-' else concat(j.notnull_rate, '%') end notnull_rate,
           k.total_records,
           k.notnull_records,
           case when k.total_records is null then null when k.total_records = 0 then '-' else concat(k.notnull_rate, '%') end notnull_rate,
           l.total_records,
           l.association_records,
           case when l.total_records is null then null when l.total_records = 0 then '-' else concat(l.association_rate, '%') end association_rate,
           m.total_records,
           m.association_records,
           case when m.total_records is null then null when m.total_records = 0 then '-' else concat(m.association_rate, '%') end association_rate,
           n.total_records,
           n.association_records,
           case when n.total_records is null then null when n.total_records = 0 then '-' else concat(n.association_rate, '%') end association_rate
        from org_list a
         left join prov_timeliness_org b on b.org_code = a.org_code and b.table_level = '1'
         left join prov_timeliness_org c on c.org_code = a.org_code and c.table_level = '2'
         left join prov_timeliness_org d on d.org_code = a.org_code and d.table_level = '3'
         left join prov_column_level_org e on e.org_code = a.org_code and e.column_level = '1'
         left join prov_column_level_org f on f.org_code = a.org_code and f.column_level = '2'
         left join prov_column_level_org g on g.org_code = a.org_code and g.column_level = '3'
         left join prov_column_level_org h on h.org_code = a.org_code and h.column_level = 'update_1'
         left join prov_column_level_org j on j.org_code = a.org_code and j.column_level = 'version_2_column_level_1'
         left join prov_column_level_org k on k.org_code = a.org_code and k.column_level = 'version_2_column_level_3'
         left join prov_association_org l on l.org_code = a.org_code and l.association_table = 'master'
         left join prov_association_org m on m.org_code = a.org_code and m.association_table = 'other'
         left join prov_association_org n on n.org_code = a.org_code and n.association_table = 'all'
        where a.is_516_flag = '是'
        order by a.city, a.org_code
        """

    def get_medicine_regulatory_org_summary_sql(self):
        """药政处机构汇总 SQL"""
        return f"""
        select distinct a.city, a.org_code, a.org_name,
           d.total_records, d.compliance_records,
           case when d.total_records is null then null when d.total_records = 0 then '-' else concat(d.compliance_rate, '%') end compliance_rate,
           e.total_records,
           e.notnull_records,
           case when e.total_records is null then null when e.total_records = 0 then '-' else concat(e.notnull_rate, '%') end notnull_rate,
           f.total_records,
           f.notnull_records,
           case when f.total_records is null then null when f.total_records = 0 then '-' else concat(f.notnull_rate, '%') end notnull_rate,
           g.total_records,
           g.notnull_records,
           case when g.total_records is null then null when g.total_records = 0 then '-' else concat(g.notnull_rate, '%') end notnull_rate,
           h.total_records,
           h.notnull_records,
           case when h.total_records is null then null when h.total_records = 0 then '-' else concat(h.notnull_rate, '%') end notnull_rate,
           i.total_records,
           i.notnull_records,
           case when i.total_records is null then null when i.total_records = 0 then '-' else concat(i.notnull_rate, '%') end notnull_rate,
           j.total_records,
           j.notnull_records,
           case when j.total_records is null then null when j.total_records = 0 then '-' else concat(j.notnull_rate, '%') end notnull_rate,
           k.total_records,
           k.notnull_records,
           case when k.total_records is null then null when k.total_records = 0 then '-' else concat(k.notnull_rate, '%') end notnull_rate,
           l.total_records,
           l.association_records,
           case when l.total_records is null then null when l.total_records = 0 then '-' else concat(l.association_rate, '%') end association_rate,
           m.total_records,
           m.association_records,
           case when m.total_records is null then null when m.total_records = 0 then '-' else concat(m.association_rate, '%') end association_rate,
           n.total_records,
           n.association_records,
           case when n.total_records is null then null when n.total_records = 0 then '-' else concat(n.association_rate, '%') end association_rate
        from org_list a
         left join prov_timeliness_org d on d.org_code = a.org_code and d.table_level = '3'
         left join prov_column_level_org e on e.org_code = a.org_code and e.column_level = '1'
         left join prov_column_level_org f on f.org_code = a.org_code and f.column_level = '2'
         left join prov_column_level_org g on g.org_code = a.org_code and g.column_level = '3'
         left join prov_column_level_org h on h.org_code = a.org_code and h.column_level = 'update_1'
         left join prov_column_level_org i on i.org_code = a.org_code and i.column_level = 'update_3'
         left join prov_column_level_org j on j.org_code = a.org_code and j.column_level = 'version_2_column_level_1'
         left join prov_column_level_org k on k.org_code = a.org_code and k.column_level = 'version_2_column_level_3'
         left join prov_association_org l on l.org_code = a.org_code and l.association_table = 'pro_base_person_ylfw'
         left join prov_association_org m on m.org_code = a.org_code and m.association_table = 'pro_opt_diagnosisbreakdown,pro_ipt_diagnosisbreakdown'
         left join prov_association_org n on n.org_code = a.org_code and n.association_table = 'all'
        where a.is_516_flag = '是'
        order by a.city, a.org_code
        """

        
    def get_realtime_detail_sql(self):
        """
        时效性明细 SQL
        """
        condition = self.get_national_condition()
        return f"""
        select a.city,
       a.org_code,
       a.org_name,
       b.table_name,
       b.table_comment,
       b.table_level,
       c.timeliness_comment,
       b.total_records,
       b.compliance_records,
       case
           when total_records is null then null
           when total_records = 0 then '-'
           else
               concat(round((b.compliance_records/b.total_records)*100,2), '%') end compliance_rate,
       c.quality_flag,
       c.responsible_dept_codes
from org_list a
         left join prov_timeliness_detail b on a.org_code = b.org_code and b.table_name not in('pro_dic_department','pro_dic_practitioner') 
         join prov_table_list c on b.table_name = c.table_name {condition}
where a.is_516_flag = '是' 
order by a.city, a.org_code;
        """
        
    def get_column_level1_sql(self):
        """
        必填字段完整性 SQL
        """
        condition = self.get_national_condition()
        return f"""
select a.city,
       a.org_code,
       a.org_name,
       b.table_name,
       c.table_comment table_comment,
       sum(b.total_records) as total_records,
       sum(b.notnull_records) as notnull_records,
       case
           when sum(b.total_records) is null then null
           when sum(b.total_records) = 0 then '-'
           else
               concat(round((sum(b.notnull_records)/sum(b.total_records))*100,2), '%') end notnull_rate,
       c.quality_flag,
       c.responsible_dept_codes
from org_list a
         left join prov_column_level_1_detail b on a.org_code = b.org_code
         join prov_table_list c on b.table_name = c.table_name {condition}
where a.is_516_flag = '是'
group by a.city, a.org_code,a.org_name, b.table_name, c.table_comment,c.quality_flag,c.responsible_dept_codes,c.table_seq
order by a.city, a.org_code,c.table_seq
        """
        
    def get_column_level2_sql(self):
        """
        关键建议填字段完整性 SQL
        """
        condition = self.get_national_condition()
        return f"""
        select a.city,
       a.org_code,
       a.org_name,
       b.table_name,
       c.table_comment table_comment,
       sum(b.total_records) total_records,
       sum(b.notnull_records) notnull_records,
       case
           when sum(b.total_records) is null then null
           when sum(b.total_records) = 0 then '-'
           else
               concat(round((sum(b.notnull_records)/sum(b.total_records))*100,2), '%') end notnull_rate,
       c.quality_flag,
       c.responsible_dept_codes
from org_list a
         left join prov_column_level_2_detail b on a.org_code = b.org_code
         join prov_table_list c on b.table_name = c.table_name {condition}
where a.is_516_flag = '是'
group by a.city, a.org_code,a.org_name, b.table_name, c.table_comment,c.quality_flag,c.responsible_dept_codes,c.table_seq
order by a.city, a.org_code,c.table_seq
        """
    def get_column_level3_sql(self):
        """
        条件必填字段完整性 SQL
        """
        condition = self.get_national_condition()
        return f"""
        select a.city,
       a.org_code,
       a.org_name,
       b.table_name,
       c.table_comment table_comment,
       sum(b.total_records) total_records,
       sum(b.notnull_records) notnull_records,
       case
           when sum(b.total_records) is null then null
           when sum(b.total_records) = 0 then '-'
           else
               concat(round((sum(b.notnull_records)/sum(b.total_records))*100,2), '%') end notnull_rate,
       c.quality_flag,
       c.responsible_dept_codes
from org_list a
         left join prov_column_level_3_detail b on a.org_code = b.org_code
         join prov_table_list c on b.table_name = c.table_name {condition}
where a.is_516_flag = '是'
group by a.city, a.org_code,a.org_name, b.table_name, c.table_comment,c.quality_flag,c.responsible_dept_codes,c.table_seq
order by a.city, a.org_code,c.table_seq
        """

    def get_column_version_2_sql(self):
        """
           条件必填第二批次更新 SQL
           """
        condition = self.get_national_condition()
        return f"""
                select a.city,
       a.org_code,
       a.org_name,
       b.table_name,
       c.table_comment table_comment,
       sum(b.total_records) total_records,
       sum(b.notnull_records) notnull_records,
       case
           when sum(b.total_records) is null then null
           when sum(b.total_records) = 0 then '-'
           else
               concat(round((sum(b.notnull_records)/sum(b.total_records))*100,2), '%') end notnull_rate,
       c.quality_flag,
       c.responsible_dept_codes
from org_list a
         left join prov_update_version_2_detail b on a.org_code = b.org_code
         join prov_table_list c on b.table_name = c.table_name {condition}
where a.is_516_flag = '是'
group by a.city, a.org_code,a.org_name, b.table_name, c.table_comment,c.quality_flag,c.responsible_dept_codes,c.table_seq
order by a.city, a.org_code,c.table_seq
                """
        
    def get_association_sql(self):
        """关联关系明细 SQL 分发方法"""
        variant = self.get_sql_variant()
        if variant == "emergency_warning":
            return self.get_emergency_warning_association_sql()
        else:
            return self.get_early_warning_association_sql()

    def get_early_warning_association_sql(self):
        """预警处关联关系明细 SQL"""
        condition = self.get_national_condition()
        return f"""
        select a.city,a.org_code,a.org_name,
       b.table_name,
       c.table_comment table_comment,
       b.association_table_name,
       d.table_comment   association_table_comment,
       b.total_records,
       b.association_records,
       case when total_records = 0 then '-'
           else
               concat(round((b.association_records/b.total_records)*100,2),'%')
           end association_rate,
       c.quality_flag,
       c.responsible_dept_codes
       from org_list a
    left join  prov_association_detail b on b.org_code = a.org_code
    join prov_table_list c on b.table_name = c.table_name {condition}
    left join prov_table_list d on b.association_table_name = d.table_name
where a.is_516_flag ='是'
order by a.city,a.org_code
        """

    def get_emergency_warning_association_sql(self):
        """应急处关联关系明细 SQL"""
        return f"""
        select a.city,a.org_code,a.org_name,
       b.table_name,
       c.table_comment table_comment,
       b.association_table_name,
       d.table_comment   association_table_comment,
       b.total_records,
       b.association_records,
       case when total_records = 0 then '-'
           else
               concat(round((b.association_records/b.total_records)*100,2),'%')
           end association_rate,
       c.quality_flag,
       IFNULL(e.responsible_dept_codes,c.responsible_dept_codes) as responsible_dept_codes
       from org_list a
    left join prov_association_detail b on b.org_code = a.org_code
    left join prov_table_list c on b.table_name = c.table_name 
    left join prov_table_list d on b.association_table_name = d.table_name
    join emergency_association_config e on e.table_name = b.table_name and e.association_table_name = b.association_table_name and e.enable_status = '1'
where a.is_516_flag ='是'
order by a.city,a.org_code
        """
        
    def get_business_sql(self):
        """
        业务主键唯一率 SQL
        """
        dept_config = self.get_current_dept_config()
        dept_flag = dept_config["table_flag"]
        condition = f"and c.{dept_flag}='1'"
        
        
        return f"""
        select a.city,a.org_code,a.org_name,
       b.table_name,
       c.table_comment table_comment,
       b.total_records,
       b.unique_records,
       case when total_records = 0 then '-'
           else
               concat(round((b.unique_records/b.total_records)*100,2),'%')
           end unique_rate,
       c.responsible_dept_codes
       from org_list a
    left join prov_business_detail b on b.org_code = a.org_code
         join prov_table_list c on b.table_name = c.table_name {condition}
where a.is_516_flag ='是'
order by a.city,a.org_code
        """
        
    def get_chief_sql(self):
        """
        主诉明细 SQL
        """
        condition = self.get_national_condition()
        return f"""
        select a.city,
       a.org_code,
       a.org_name,
       a.station_hospital,
       b.table_name,
       c.table_comment table_comment,
       b.field_name,
       '主诉' field_comment,
       b.total_records,
       b.notnull_records,
       case
       when b.total_records is null then null
           when b.total_records = 0 then '-'
           else
               concat(round((b.notnull_records/b.total_records)*100,2), '%')
           end notnull_rate,
       c.quality_flag,
       c.responsible_dept_codes
from org_list a
         left join prov_chief_detail b on b.org_code = a.org_code and b.field_name in('bzzs', 'chiefcomplaint', 'zs')
         join prov_table_list c on c.table_name = b.table_name {condition}
where a.is_516_flag = '是'
order by a.city, a.org_code
        """
        
    def get_present_sql(self):
        """
        现病史明细 SQL
        """
        condition = self.get_national_condition()
        return f"""
        select a.city,
       a.org_code,
       a.org_name,
       a.station_hospital,
       b.table_name,
        c.table_comment table_comment,
       b.field_name,
       '现病史' field_comment,
       b.total_records,
       b.notnull_records,
       case
       when b.total_records is null then null
           when b.total_records = 0 then '-'
           else
               concat(round((b.notnull_records/b.total_records)*100,2), '%')
           end notnull_rate,
           c.quality_flag,
           c.responsible_dept_codes
from org_list a
         left join prov_chief_detail b on b.org_code = a.org_code and b.field_name in('bzxbs', 'xbs')
         join prov_table_list c on b.table_name = c.table_name {condition}
where a.is_516_flag = '是'
order by a.city, a.org_code;
        """

def main():
    root = tk.Tk()
    app = ReportGeneratorTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
