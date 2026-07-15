import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import duckdb
import pandas as pd
import os
import threading
import warnings
from datetime import datetime
from copy import copy
from tkcalendar import Calendar

# 忽略 pandas 的 DBAPI2 警告
warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')


VERSION = "V1.7"
BUILD_DATE = "2026-07-15"

class ReportGeneratorTool:
    def __init__(self, root):
        self.root = root
        self.root.title(f"疾控中心下发报告生成辅助工具 {VERSION} ({BUILD_DATE})")
        
        # 设置窗口大小并居中
        window_width = 700
        window_height = 700
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.root.resizable(False, False)

        # 全局滚动条样式：加宽所有滚动条
        style = ttk.Style()
        style.configure("Vertical.TScrollbar", width=32, arrowsize=24)
        style.configure("Horizontal.TScrollbar", width=32, arrowsize=24)
        
        self.db_path = "prov_report.db"
        self.template_path = None
        self.export_path = None
        self.data_dir = None
        self.quality_date = tk.StringVar()
        self.quality_date.set("")  # 初始化为空
        self.national_flag_var = tk.StringVar(value="national")  # 默认国标
        self.data_imported = False  # 是否已导入数据

        # 绑定切换类别时的检查回调
        self.national_flag_var.trace_add('write', self.on_flag_change)

        self.create_main_interface()

    def on_flag_change(self, *args):
        """切换质控报告生成类别时的回调：已导入数据则强制切换到数据加工并提示"""
        if self.data_imported:
            flag_name = "全部" if self.national_flag_var.get() == "all" else "国标"
            # 强制切换到"3. 数据加工"选项卡（索引为2）
            if hasattr(self, 'notebook'):
                self.notebook.select(2)
            messagebox.showwarning(
                "提示",
                f"已切换为【{flag_name}】，需要重新执行数据加工操作。\n\n请点击【执行数据加工SQL】按钮。"
            )

    def create_main_interface(self):
        """创建主界面"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
              
        # 国标/全部选择框
        flag_frame = ttk.Frame(main_frame)
        flag_frame.grid(row=0, column=0, sticky=tk.W, pady=5)

        flag_label = ttk.Label(flag_frame, text="质控报告生成类别：", font=('微软雅黑', 10, 'bold'))
        flag_label.pack(side=tk.LEFT, padx=5)

        national_radio = ttk.Radiobutton(flag_frame, text="国标", variable=self.national_flag_var, value="national")
        national_radio.pack(side=tk.LEFT, padx=5)

        all_radio = ttk.Radiobutton(flag_frame, text="全部", variable=self.national_flag_var, value="all")
        all_radio.pack(side=tk.LEFT, padx=5)
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        tab1 = ttk.Frame(self.notebook, padding="10")
        tab2 = ttk.Frame(self.notebook, padding="10")
        tab3 = ttk.Frame(self.notebook, padding="10")
        tab4 = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(tab1, text="1. 数据库测试")
        self.notebook.add(tab2, text="2. 数据导入")
        self.notebook.add(tab3, text="3. 数据加工")
        self.notebook.add(tab4, text="4. 数据导出")

        tab5 = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab5, text="5. 机构管理")

        self.create_db_test_tab(tab1)
        self.create_data_import_tab(tab2)
        self.create_data_process_tab(tab3)
        self.create_data_export_tab(tab4)
        self.create_org_management_tab(tab5)
        
    def create_db_test_tab(self, parent):
        """创建数据库测试 Tab"""
        frame = ttk.LabelFrame(parent, text="DuckDB 数据库连接测试", padding="5")
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
        frame = ttk.LabelFrame(parent, text="数据导入", padding="5")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        # 创建日期选择框架
        date_frame = ttk.Frame(frame)
        date_frame.grid(row=0, column=0, sticky=tk.W, pady=2)

        date_label = ttk.Label(date_frame, text="质控日期:", font=('微软雅黑', 10, 'bold'))
        date_label.grid(row=0, column=0, padx=5)

        # 设置初始日期为今天
        today = datetime.now().strftime('%Y-%m-%d')
        self.quality_date.set(today)

        # 日期显示框（只读）
        date_entry = ttk.Entry(date_frame, textvariable=self.quality_date, width=15, font=('微软雅黑', 10), state='readonly')
        date_entry.grid(row=0, column=1, padx=5)

        # 日历选择按钮
        calendar_btn = ttk.Button(date_frame, text="📅", width=3, command=lambda: self.popup_calendar())
        calendar_btn.grid(row=0, column=2, padx=2)

        # 绑定鼠标点击事件，点击文本框也弹出日历
        date_entry.bind('<Button-1>', lambda e: self.popup_calendar())

        select_btn = ttk.Button(frame, text="选择数据文件目录", command=self.select_data_directory)
        select_btn.grid(row=1, column=0, sticky=tk.W, pady=2)

        self.dir_label = ttk.Label(frame, text="当前目录：未选择")
        self.dir_label.grid(row=2, column=0, sticky=tk.W, pady=2)

        # 导入按钮框架（居中显示）
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, pady=5)
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
        
    def popup_calendar(self):
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
        current_date = self.quality_date.get()
        if current_date:
            cal.selection_set(current_date)
        
        # 确认选择函数
        def on_confirm():
            selected_date = cal.get_date()
            self.quality_date.set(selected_date)
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
        """根据国标/全部选择返回对应的基础文件名"""
        flag = getattr(self, 'national_flag_var', None)
        if flag and flag.get() == "all":
            return "疾控下发汇总报告(省标表41张表)_质控日期："
        else:
            return "疾控下发汇总报告(省标对照国标)_质控日期："

    def update_export_filename(self):
        """更新导出文件名中的质控日期"""
        date_str = self.quality_date.get()
        if date_str and hasattr(self, 'export_name_var'):
            base_name = self.get_base_name()
            new_name = f"{base_name}{date_str}.xlsx"
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
        frame = ttk.LabelFrame(parent, text="数据加工", padding="5")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        sql_label = ttk.Label(frame, text="执行 加工数据 SQL 脚本")
        sql_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.process_status_label = ttk.Label(frame, text="加工状态：未开始")
        self.process_status_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        process_btn = ttk.Button(frame, text="执行数据加工 SQL", command=self.process_data)
        process_btn.grid(row=2, column=0, pady=2)
        
        # 创建带滚动条的文本框
        text_frame = ttk.Frame(frame)
        text_frame.grid(row=3, column=0, pady=(2, 10), sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1)
        
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
                
                # 从 qzrj_generate_data.sql 文件读取 SQL
                sql_file = 'prov_generate_data.sql'
                if not os.path.exists(sql_file):
                    raise Exception(f"找不到 SQL 文件：{sql_file}")
                
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                # 根据选择动态修改SQL
                if self.national_flag_var.get() == "all":
                    # 选择"全部"时，移除所有 national_flag='1' 的条件
                    sql_content = sql_content.replace("and a.national_flag = '1'", "")
                    sql_content = sql_content.replace("and c.national_flag = '1'", "")
                    sql_content = sql_content.replace("and b.national_flag = '1'", "")
                    sql_content = sql_content.replace("and c.national_flag='1'", "")
                
                self.process_text.insert(tk.END, f"执行 SQL 脚本：{sql_file}\n\n")
                
                conn = duckdb.connect(self.db_path)
                
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
        
    def create_data_export_tab(self, parent):
        """创建数据导出 Tab"""
        frame = ttk.LabelFrame(parent, text="数据导出", padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 模板文件区域
        template_frame = ttk.LabelFrame(frame, text="模板文件", padding="5")
        template_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        frame.columnconfigure(0, weight=1)
        
        self.template_label = ttk.Label(template_frame, text="模板文件：未选择")
        self.template_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        select_template_btn = ttk.Button(template_frame, text="选择模板文件", command=self.select_template)
        select_template_btn.grid(row=0, column=1, padx=5)
        
        # 导出设置区域
        export_frame = ttk.LabelFrame(frame, text="导出设置", padding="5")
        export_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        frame.columnconfigure(0, weight=1)
        
        # 使用当前质控日期作为默认文件名，根据国标/全部选择动态设置
        default_date = datetime.now().strftime('%Y-%m-%d')
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
        
        # 添加路径显示
        self.export_path_var = tk.StringVar(value=os.path.abspath(default_name))
        export_path_label = ttk.Label(export_frame, text="完整路径:")
        export_path_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        export_path_entry = ttk.Entry(export_frame, textvariable=self.export_path_var, width=80)
        export_path_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)
        export_frame.columnconfigure(1, weight=1)
        
        # 文件名变化时更新路径
        def update_path(*args):
            filename = self.export_name_var.get()
            self.export_path_var.set(os.path.abspath(filename))
        
        self.export_name_var.trace('w', update_path)
        
        # 导出按钮（两个按钮放在同一行，独立按钮框架）
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, pady=5)

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
        frame = ttk.LabelFrame(parent, text="机构管理", padding="5")
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
        search_entry = ttk.Entry(search_frame, textvariable=self.org_search_var, width=50)
        search_entry.pack(side=tk.LEFT, padx=5)

        # 点击搜索框自动清空
        search_entry.bind('<Button-1>', lambda e: self.org_search_var.set(''))

        search_btn = ttk.Button(search_frame, text="查询", command=self.refresh_org_tree)
        search_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = ttk.Button(search_frame, text="刷新", command=self.refresh_org_tree)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # 操作按钮区域
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, pady=5)

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
        # 获取导出文件所在目录
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

        # 在 Windows 上：先检查是否已有资源管理器窗口打开了该目录
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
        except Exception as e:
            # 兜底方案：直接用资源管理器打开
            try:
                os.startfile(directory)
            except Exception:
                import subprocess
                subprocess.Popen(['explorer', directory])

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
                
                export_sheets = {
                    '地市(州)': self.get_city_state_sql(),
                    '机构汇总': self.get_org_summary_sql(),
                    '时效性明细': self.get_realtime_detail_sql(),
                    '必填字段完整性': self.get_column_level1_sql(),
                    '重要建议填字段完整性': self.get_column_level2_sql(),
                    '条件必填字段完整性': self.get_column_level3_sql(),
                    '关联关系明细': self.get_association_sql(),
                    # '值域一致性': self.get_dict_sql(),
                    '业务主键唯一率': self.get_business_sql(),
                    '主诉明细': self.get_chief_sql(),
                    '现病史明细': self.get_present_sql()
                }
                
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
                
                export_path = self.export_name_var.get()
                full_path = os.path.abspath(export_path)
                self.log_message(f"\n保存文件到：{full_path}...\n")
                wb.save(export_path)
                
                self.export_progress.stop()
                self.export_status_label.config(text="导出状态：完成", foreground="green")
                self.log_message(f"\n✓ 报告已成功导出到：{full_path}\n")
                self.log_message(f"✓ 共处理 {processed}/{total_sheets} 个 Sheet 页\n")
                
                # 显示带滚动条的消息框
                messagebox.showinfo("报告生成","导出成功！")
                
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
        """获取national_flag条件"""
        if self.national_flag_var.get() == "national":
            return "and c.national_flag='1'"
        return ""
            
    def get_city_state_sql(self):
        """
        地市州汇总 SQL
        """
        return """
        select city,
       org_cnt,
       real_cnt,
       concat(round((real_cnt / org_cnt) * 100, 2), '%')                  as real_rate,
       hour_cnt,
       concat(round((hour_cnt / org_cnt) * 100, 2), '%')                  as hour_rate,
       other_cnt,
       concat(round((other_cnt / org_cnt) * 100, 2), '%')                 as other_rate,
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
       association_org_cnt,
       concat(round((association_org_cnt / org_cnt) * 100, 2), '%')       as association__rate
from prov_city_summary a
union
select 'Total'                                                                            city,
       sum(org_cnt),
       sum(real_cnt),
       concat(round((sum(real_cnt) / sum(org_cnt)) * 100, 2), '%')                  as real_rate,
       sum(hour_cnt)                                                                   hour_cnt,
       concat(round((sum(hour_cnt) / sum(org_cnt)) * 100, 2), '%')                  as hour_rate,
       sum(other_cnt)                                                                  other_cnt,
       concat(round((sum(other_cnt) / sum(org_cnt)) * 100, 2), '%')                 as other_rate,
       sum(e_total_records)                                                            e_total_records,
       sum(e_notnull_records)                                                          e_notnull_records,
       concat(round((sum(e_notnull_records) / sum(e_total_records)) * 100, 2), '%') as e_notnull_rate,
       sum(f_total_records)                                                            f_total_records,
       sum(f_notnull_records)                                                          f_notnull_records,
       concat(round((sum(f_notnull_records) / sum(f_total_records)) * 100, 2), '%') as f_notnull_rate,
       sum(g_total_records) g_total_records,
       sum(g_notnull_records)  g_notnull_records,
       concat(round((sum(g_notnull_records) / sum(g_total_records)) * 100, 2), '%') as g_notnull_rate,
       sum(h_total_records) h_total_records,
       sum(h_notnull_records) h_notnull_records,
       concat(round((sum(h_notnull_records) / sum(h_total_records)) * 100, 2), '%') as h_notnull_rate,
       sum(i_total_records)                                                            i_total_records,
       sum(i_notnull_records)                                                          i_notnull_records,
       concat(round((sum(i_notnull_records) / sum(i_total_records)) * 100, 2), '%')  i_not_notnull_rate,
       sum(association_org_cnt)                                                        association_org_cnt,
       concat(round((sum(association_org_cnt) / sum(org_cnt)) * 100, 2), '%')       as association__rate
from prov_city_summary
order by city;
        """
        
    def get_org_summary_sql(self):
        """
        机构汇总 SQL
        """
        return """
         select a.city,
       a.org_code,
       a.org_name,
       b.total_records,
       b.compliance_records,
       case
           when b.total_records is null then null
           when b.total_records = 0 then '-'
           else concat(b.compliance_rate, '%') end  compliance_rate,
       c.total_records,
       c.compliance_records,
       case
           when c.total_records is null then null
           when c.total_records = 0 then '-'
           else concat(c.compliance_rate, '%') end  compliance_rate,
       d.total_records,
       d.compliance_records,
       case
           when d.total_records is null then null
           when d.total_records = 0 then '-'
           else concat(d.compliance_rate, '%') end  compliance_rate,
       e.total_records,
       e.notnull_records,
       case
           when e.total_records is null then null
           when e.total_records = 0 then '-'
           else concat(e.notnull_rate, '%') end     notnull_rate,
       f.total_records,
       f.notnull_records,
       case
           when f.total_records is null then null
           when f.total_records = 0 then '-'
           else concat(f.notnull_rate, '%') end     notnull_rate,
       g.total_records,
       g.notnull_records,
       case
           when g.total_records is null then null
           when g.total_records = 0 then '-'
           else concat(g.notnull_rate, '%') end     notnull_rate,
       h.total_records,
       h.notnull_records,
       case
           when h.total_records is null then null
           when h.total_records = 0 then '-'
           else concat(h.notnull_rate, '%') end     notnull_rate,
       i.total_records,
       i.notnull_records,
       case
           when i.total_records is null then null
           when i.total_records = 0 then '-'
           else concat(i.notnull_rate, '%') end     notnull_rate,
       j.total_records,
       j.association_records,
       case
           when j.total_records is null then null
           when j.total_records = 0 then '-'
           else concat(j.association_rate, '%') end association_rate,
       k.total_records,
       k.association_records,
       case
           when k.total_records is null then null
           when k.total_records = 0 then '-'
           else concat(k.association_rate, '%') end association_rate,
       l.total_records,
       l.association_records,
       case
           when l.total_records is null then null
           when l.total_records = 0 then '-'
           else concat(l.association_rate, '%') end association_rate
from org_list a
         left join prov_timeliness_org b on b.org_code = a.org_code and b.table_level = '1'
         left join prov_timeliness_org c on c.org_code = a.org_code and c.table_level = '2'
         left join prov_timeliness_org d on d.org_code = a.org_code and d.table_level = '3'
         left join prov_column_level_org e on e.org_code = a.org_code and e.column_level = '1'
         left join prov_column_level_org f on f.org_code = a.org_code and f.column_level = '2'
         left join prov_column_level_org g on g.org_code = a.org_code and g.column_level = '3'
         left join prov_column_level_org h on h.org_code = a.org_code and h.column_level = 'update_1'
         left join prov_column_level_org i on i.org_code = a.org_code and i.column_level = 'update_3'
         left join prov_association_org j on j.org_code = a.org_code and j.association_table = 'pro_base_person_ylfw'
         left join prov_association_org k on k.org_code = a.org_code and k.association_table = 'pro_opt_diagnosisbreakdown,pro_ipt_diagnosisbreakdown'
         left join prov_association_org l on l.org_code = a.org_code and l.association_table = 'all'
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
               concat(round(b.compliance_rate*100,2), '%') end compliance_rate,
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
               concat(round(sum(b.notnull_records)/sum(b.total_records)*100,2), '%') end notnull_rate,
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
               concat(round(sum(b.notnull_records)/sum(b.total_records)*100,2), '%') end notnull_rate,
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
               concat(round(sum(b.notnull_records)/sum(b.total_records)*100,2), '%') end notnull_rate,
       c.quality_flag,
       c.responsible_dept_codes
from org_list a
         left join prov_column_level_3_detail b on a.org_code = b.org_code
         join prov_table_list c on b.table_name = c.table_name {condition}
where a.is_516_flag = '是'
group by a.city, a.org_code,a.org_name, b.table_name, c.table_comment,c.quality_flag,c.responsible_dept_codes,c.table_seq
order by a.city, a.org_code,c.table_seq
        """    
        
    def get_association_sql(self):
        """
        关联关系明细 SQL
        """
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
               concat(round(b.association_rate*100,2),'%')
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
        
    def get_business_sql(self):
        """
        业务主键唯一率 SQL
        """
        return """
        select a.city,a.org_code,a.org_name,
       b.table_name,
       c.table_comment table_comment,
       b.total_records,
       b.unique_records,
       case when total_records = 0 then '-'
           else
               concat(round(b.unique_rate*100,2),'%')
           end unique_rate,
       c.responsible_dept_codes
       from org_list a
    left join prov_business_detail b on b.org_code = a.org_code
         join prov_table_list c on b.table_name = c.table_name
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
               concat(round(b.notnull_rate*100,2), '%')
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
               concat(round(b.notnull_rate*100,2), '%')
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
