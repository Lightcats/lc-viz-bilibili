# -*- coding: utf-8 -*-
# 文件名: main_gui.py
# B站知识区分析工具箱 - 主程序入口
# Tkinter 图形界面，控制数据采集→预处理→可视化→建模→看板 全流程

import os
import sys
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import pandas as pd
import numpy as np

# ── 项目模块导入 ────────────────────────────────────────────
from src.analyzer import preprocess_data, train_model
from src.visualizer import generate_plots
from src.scraper import fetch_and_save
from assets.app_template import APP_TEMPLATE


# ── 工具常量 ────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

RAW_DATA = os.path.join(DATA_DIR, "raw_data.csv")
PROCESSED_DATA = os.path.join(DATA_DIR, "processed_data.csv")
MODEL_PATH = os.path.join(DATA_DIR, "model.pkl")
VIZ_PATH = os.path.join(DATA_DIR, "visualization.png")
APP_SCRIPT = os.path.join(PROJECT_ROOT, "app.py")

BTN_LABELS = [
    "1. 数据采集",
    "2. 数据预处理",
    "3. 多维度可视化",
    "4. 数据建模",
    "5. 启动Streamlit应用",
]

BTN_DONE_LABELS = [
    "✅ 1. 数据采集 ✓",
    "✅ 2. 数据预处理 ✓",
    "✅ 3. 多维度可视化 ✓",
    "✅ 4. 数据建模 ✓",
    "✅ 5. 启动Streamlit应用 ✓",
]


# ============================================================
#  GUI 应用程序
# ============================================================

class BilibiliAnalyzerApp:
    """B站知识区分析工具箱 主窗口"""

    def __init__(self, root):
        self.root = root
        self.root.title("B站知识区分析工具箱")
        self.root.geometry("820x620")
        self.root.minsize(720, 520)

        # 状态追踪
        self.step_done = [False] * 5
        self.streamlit_process = None
        self.crawling = False       # 爬虫是否正在运行

        self._build_ui()

    # ── UI 构建 ─────────────────────────────────────────────

    def _build_ui(self):
        """构建界面布局"""
        self.root.grid_columnconfigure(0, weight=0, minsize=180)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # ── 左侧按钮面板 ──
        left_frame = tk.Frame(self.root, padx=12, pady=12)
        left_frame.grid(row=0, column=0, sticky="nsew")

        tk.Label(left_frame, text="操作流程",
                 font=("Microsoft YaHei", 11, "bold")).pack(pady=(0, 10))

        self.buttons = []
        commands = [
            self._step1_choose_method,
            self._step2_preprocess,
            self._step3_visualize,
            self._step4_model,
            self._step5_streamlit,
        ]
        for i in range(5):
            btn = tk.Button(
                left_frame,
                text=BTN_LABELS[i],
                command=commands[i],
                width=22,
                height=2,
                font=("Microsoft YaHei", 9),
                state=tk.NORMAL if i == 0 else tk.DISABLED,
                bg="#4A90D9" if i == 0 else "#E0E0E0",
                fg="white" if i == 0 else "#666666",
                activebackground="#5AA0E9",
                relief=tk.RAISED,
                bd=2,
            )
            btn.pack(pady=5, fill=tk.X)
            self.buttons.append(btn)

        # 重置按钮
        tk.Frame(left_frame, height=20).pack()
        self.reset_btn = tk.Button(
            left_frame,
            text="🔄 重置流程",
            command=self._reset,
            width=22,
            height=1,
            font=("Microsoft YaHei", 9),
            bg="#E8E8E8",
            fg="#333333",
            relief=tk.RAISED,
            bd=2,
        )
        self.reset_btn.pack(pady=5, fill=tk.X)

        # ── 右侧日志面板 ──
        right_frame = tk.Frame(self.root, padx=12, pady=12)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.grid_rowconfigure(0, weight=0)
        right_frame.grid_rowconfigure(1, weight=1)

        tk.Label(right_frame, text="运行日志",
                 font=("Microsoft YaHei", 11, "bold"),
                 anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.log_area = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            width=60,
            height=32,
            font=("Consolas", 10),
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="white",
            bd=2,
            relief=tk.SUNKEN,
        )
        self.log_area.grid(row=1, column=0, sticky="nsew")
        self.log_area.tag_config("info", foreground="#D4D4D4")
        self.log_area.tag_config("success", foreground="#4EC9B0")
        self.log_area.tag_config("error", foreground="#F44747",
                                 font=("Consolas", 10, "bold"))
        self.log_area.tag_config("warning", foreground="#CE9178")

        self._log("B站知识区分析工具箱 v1.0 已启动", "info")
        self._log("请点击「1. 数据采集」选择采集方式开始 ...", "info")

    # ── 日志工具 ─────────────────────────────────────────────

    def _log(self, msg, tag="info"):
        self.log_area.insert(tk.END, msg + "\n", tag)
        self.log_area.see(tk.END)
        self.root.update_idletasks()

    def _log_separator(self):
        self._log("-" * 60, "info")

    # ── 按钮状态管理 ────────────────────────────────────────

    def _enable_step(self, idx):
        if 0 <= idx < len(self.buttons):
            self.buttons[idx].config(
                state=tk.NORMAL, bg="#4A90D9", fg="white",
            )

    def _mark_done(self, idx):
        self.step_done[idx] = True
        self.buttons[idx].config(
            text=BTN_DONE_LABELS[idx],
            state=tk.DISABLED,
            bg="#27AE60",
            fg="white",
            disabledforeground="white",
        )
        if idx + 1 < len(self.buttons):
            self._enable_step(idx + 1)

    # ── 步骤 1: 数据采集（两种方式） ────────────────────────

    def _step1_choose_method(self):
        """弹出选择窗口：爬虫采集 / 导入本地文件"""
        if self.crawling:
            self._log("[!] 爬虫正在运行中，请等待 ...", "warning")
            return

        # 创建模式选择弹窗
        dialog = tk.Toplevel(self.root)
        dialog.title("数据采集方式")
        dialog.geometry("420x280")
        dialog.resizable(False, False)
        dialog.grab_set()  # 模态
        dialog.configure(bg="#F0F0F0")

        # 窗口居中
        self._center_window(dialog, 420, 280)

        tk.Label(dialog, text="请选择数据采集方式",
                 font=("Microsoft YaHei", 13, "bold"),
                 bg="#F0F0F0", fg="#333333").pack(pady=(25, 15))

        btn_frame = tk.Frame(dialog, bg="#F0F0F0")
        btn_frame.pack(expand=True)

        # 方式 A: 爬虫采集
        btn_crawl = tk.Button(
            btn_frame,
            text="🕷️  爬虫采集",
            command=lambda: self._step1_crawl(dialog),
            width=22,
            height=3,
            font=("Microsoft YaHei", 11),
            bg="#3498DB",
            fg="white",
            activebackground="#2980B9",
            relief=tk.RAISED,
            bd=2,
        )
        btn_crawl.pack(pady=8)

        tk.Label(btn_frame,
                 text="调用B站API采集知识区热门视频，自动保存到 data/ 目录",
                 font=("Microsoft YaHei", 8),
                 bg="#F0F0F0", fg="#888888").pack()

        # 分隔
        tk.Frame(btn_frame, height=10, bg="#F0F0F0").pack()

        # 方式 B: 导入本地文件
        btn_import = tk.Button(
            btn_frame,
            text="📂  导入本地文件",
            command=lambda: self._step1_import_file(dialog),
            width=22,
            height=3,
            font=("Microsoft YaHei", 11),
            bg="#2ECC71",
            fg="white",
            activebackground="#27AE60",
            relief=tk.RAISED,
            bd=2,
        )
        btn_import.pack(pady=8)

        tk.Label(btn_frame,
                 text="从本机选择已准备好的 .csv 或 .xlsx 文件导入",
                 font=("Microsoft YaHei", 8),
                 bg="#F0F0F0", fg="#888888").pack()

    def _center_window(self, win, w, h):
        """将窗口居中显示"""
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _crawl_worker(self, pages, callback):
        """爬虫后台线程：采集、验证、回调（无 dialog 参数，dialog 在此之前已销毁）"""
        self.crawling = True
        try:
            os.makedirs(DATA_DIR, exist_ok=True)

            df = fetch_and_save(filename=RAW_DATA, pages=pages)
            self.root.after(0, lambda d=df: self._log(
                f"[爬虫] 采集完成！共 {len(d)} 条视频", "success"))
            self.root.after(0, lambda: self._log(
                f"[爬虫] 已保存到 {RAW_DATA}", "success"))
            self.root.after(0, callback)
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda m=err_msg: self._log(
                f"[错误] 爬虫采集失败: {m}", "error"))
            self.root.after(0, lambda m=err_msg: messagebox.showerror(
                "采集失败", f"爬虫异常:\n{m}"))
        finally:
            self.crawling = False

    def _step1_crawl(self, mode_dialog):
        """启动爬虫采集（在后台线程中执行）"""
        mode_dialog.destroy()
        self._log_separator()
        self._log("[数据采集] 选择方式: 爬虫采集", "info")
        self._log("[爬虫] 正在连接B站API采集知识区视频 ...", "info")

        # 弹窗询问采集页数
        pages_win = tk.Toplevel(self.root)
        pages_win.title("采集设置")
        pages_win.geometry("320x200")
        pages_win.resizable(False, False)
        pages_win.grab_set()
        self._center_window(pages_win, 320, 200)
        pages_win.configure(bg="#F0F0F0")

        tk.Label(pages_win, text="每源采集页数",
                 font=("Microsoft YaHei", 11, "bold"),
                 bg="#F0F0F0").pack(pady=(20, 5))
        tk.Label(pages_win,
                 text="每页约 40~50 条，两源合计约 pages×100 条\n建议 3~5 页即可",
                 font=("Microsoft YaHei", 9),
                 bg="#F0F0F0", fg="#888888").pack()

        pages_var = tk.IntVar(value=5)

        def on_pages_confirm():
            p = pages_var.get()
            if p < 1 or p > 50:
                messagebox.showwarning("提示", "页数范围 1~50")
                return
            pages_win.destroy()
            self._log(f"[爬虫] 开始采集 {p} 页数据，请稍候 ...", "info")
            # 启动后台线程
            t = threading.Thread(
                target=self._crawl_worker,
                args=(p, lambda: self._finish_step1()),
                daemon=True,
            )
            t.start()

        # Spinbox + 确认
        spin = tk.Spinbox(pages_win, from_=1, to=50, textvariable=pages_var,
                          width=10, font=("Consolas", 12),
                          justify=tk.CENTER, bd=2)
        spin.pack(pady=10)

        btn = tk.Button(pages_win, text="开始采集", command=on_pages_confirm,
                        width=15, height=1, font=("Microsoft YaHei", 10),
                        bg="#3498DB", fg="white")
        btn.pack(pady=5)

    def _step1_import_file(self, dialog):
        """打开文件选择对话框，导入 CSV / XLSX 数据"""
        dialog.destroy()
        file_path = filedialog.askopenfilename(
            title="选择数据文件（B站知识区视频数据）",
            filetypes=[("CSV 文件", "*.csv"), ("Excel 文件", "*.xlsx")],
        )
        if not file_path:
            messagebox.showwarning("警告", "未选择文件，请重新上传")
            self._log("[!] 用户取消了文件选择", "warning")
            return

        self._log_separator()
        self._log("[数据采集] 选择方式: 导入本地文件", "info")
        self._log(f"[数据采集] 选择文件: {file_path}", "info")

        # 确保 data 目录存在
        os.makedirs(DATA_DIR, exist_ok=True)

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".csv":
                shutil.copy2(file_path, RAW_DATA)
                self._log(f"[数据采集] CSV 已复制到 {RAW_DATA}", "success")
            elif ext == ".xlsx":
                self._log("[数据采集] 正在转换 Excel -> CSV ...", "info")
                df = pd.read_excel(file_path, engine="openpyxl")
                df.to_csv(RAW_DATA, index=False, encoding="utf-8-sig")
                self._log(f"[数据采集] Excel 已转换保存到 {RAW_DATA}", "success")
            else:
                messagebox.showerror("错误", "不支持的文件格式，请选择 .csv 或 .xlsx")
                self._log(f"[错误] 不支持的格式: {ext}", "error")
                return

            # 验证
            df_check = pd.read_csv(RAW_DATA, encoding="utf-8-sig")
            self._log(f"[数据采集] 导入数据: {len(df_check)} 行, "
                      f"{len(df_check.columns)} 列", "success")
            self._log(f"[数据采集] 列名: {list(df_check.columns)}", "info")
            self._finish_step1()

        except Exception as e:
            self._log(f"[错误] 数据导入失败: {e}", "error")
            messagebox.showerror("导入失败", f"无法读取文件:\n{e}")

    def _finish_step1(self):
        """完成数据采集后的公共处理"""
        # 二次验证文件存在并可读
        if not os.path.exists(RAW_DATA):
            self._log("[错误] RAW_DATA 文件不存在，导入失败", "error")
            return
        try:
            df_check = pd.read_csv(RAW_DATA, encoding="utf-8-sig")
            rows = len(df_check)
        except Exception:
            self._log("[错误] 无法读取 RAW_DATA，文件可能损坏", "error")
            return

        self._mark_done(0)
        messagebox.showinfo("成功", f"数据采集成功！共 {rows} 条记录\n\n"
                            f"数据文件: data/raw_data.csv")

    # ── 步骤 2: 数据预处理 ──────────────────────────────────

    def _step2_preprocess(self):
        """调用 analyzer.preprocess_data 执行清洗"""
        self._log_separator()
        self._log("[数据预处理] 开始 ...", "info")

        try:
            before, after = preprocess_data(
                input_path=RAW_DATA,
                output_path=PROCESSED_DATA,
            )
            self._log("[数据预处理] 完成！", "success")
            self._log(f"  清洗前: {before} 行", "info")
            self._log(f"  清洗后: {after} 行", "info")
            self._log(f"  删除:   {before - after} 行", "warning")
            self._mark_done(1)
            messagebox.showinfo("预处理完成",
                                f"数据清洗完成\n清洗前: {before} 行\n清洗后: {after} 行")

        except Exception as e:
            self._log(f"[错误] 数据预处理失败: {e}", "error")
            messagebox.showerror("预处理失败", str(e))

    # ── 步骤 3: 多维度可视化 ────────────────────────────────

    def _step3_visualize(self):
        """调用 visualizer.generate_plots 生成图表"""
        self._log_separator()
        self._log("[可视化] 开始生成图表 ...", "info")

        try:
            path = generate_plots(
                data_path=PROCESSED_DATA,
                output_path=VIZ_PATH,
            )
            self._log(f"[可视化] 图表已生成: {path}", "success")

            # 尝试用系统默认图片查看器打开
            try:
                if sys.platform == "win32":
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])
                self._log("[可视化] 已打开图片查看器", "info")
            except Exception:
                self._log("[可视化] 图片已保存，请手动打开查看", "info")

            self._mark_done(2)
            messagebox.showinfo("可视化完成", f"图表已生成:\n{path}")

        except Exception as e:
            self._log(f"[错误] 可视化失败: {e}", "error")
            messagebox.showerror("可视化失败", str(e))

    # ── 步骤 4: 数据建模 ────────────────────────────────────

    def _step4_model(self):
        """调用 analyzer.train_model 训练线性回归模型"""
        self._log_separator()
        self._log("[数据建模] 开始训练 LinearRegression ...", "info")

        try:
            r2, features = train_model(
                input_path=PROCESSED_DATA,
                model_path=MODEL_PATH,
            )
            self._log("[数据建模] ✅ 模型训练完成！", "success")
            self._log(f"  决定系数 R² = {r2:.4f}", "success")
            self._log(f"  特征数量: {len(features)}", "info")
            self._log(f"  特征列表: {features}", "info")
            self._mark_done(3)
            messagebox.showinfo("建模完成",
                                f"线性回归模型训练完成\nR² = {r2:.4f}\n共 {len(features)} 个特征")

        except Exception as e:
            self._log(f"[错误] 数据建模失败: {e}", "error")
            messagebox.showerror("建模失败", str(e))

    # ── 步骤 5: 启动 Streamlit 应用 ─────────────────────────

    def _step5_streamlit(self):
        """动态生成 app.py 并启动 Streamlit 看板"""
        self._log_separator()
        self._log("[Streamlit] 正在生成看板脚本 ...", "info")

        try:
            with open(APP_SCRIPT, "w", encoding="utf-8") as f:
                f.write(APP_TEMPLATE)
            self._log(f"[Streamlit] 已生成 {APP_SCRIPT}", "success")

            try:
                import streamlit
                self._log(f"[Streamlit] 检测到 streamlit 版本: "
                          f"{streamlit.__version__}", "info")
            except ImportError:
                self._log("[Streamlit] ⚠️ 未找到 streamlit，请在终端执行: "
                          "pip install streamlit", "warning")
                messagebox.showwarning(
                    "缺少依赖",
                    "未检测到 streamlit，请执行:\n\n"
                    "  pip install streamlit\n\n"
                    "或使用本项目的 requirements.txt 安装所有依赖。"
                )
                self._mark_done(4)
                return

            self._log("[Streamlit] 正在启动看板 (新终端窗口) ...", "info")

            if sys.platform == "win32":
                self.streamlit_process = subprocess.Popen(
                    ["streamlit", "run", APP_SCRIPT],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=PROJECT_ROOT,
                )
            else:
                terminal_cmd = None
                for term in ["x-terminal-emulator", "gnome-terminal", "xterm"]:
                    if subprocess.run(["which", term], capture_output=True,
                                      text=True).returncode == 0:
                        terminal_cmd = term
                        break

                if terminal_cmd:
                    self.streamlit_process = subprocess.Popen(
                        [terminal_cmd, "-e",
                         f"streamlit run '{APP_SCRIPT}'"],
                        cwd=PROJECT_ROOT,
                    )
                else:
                    self.streamlit_process = subprocess.Popen(
                        ["streamlit", "run", APP_SCRIPT],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        cwd=PROJECT_ROOT,
                    )

            self._log(f"[Streamlit] 进程 PID: "
                      f"{self.streamlit_process.pid}", "info")
            self._log("[Streamlit] 请在浏览器中访问显示的 URL", "success")
            self._mark_done(4)
            messagebox.showinfo(
                "启动成功",
                "Streamlit 看板已在新窗口中启动！\n\n"
                "请在浏览器中访问终端显示的 URL\n"
                "（通常为 http://localhost:8501）"
            )

        except Exception as e:
            self._log(f"[错误] Streamlit 启动失败: {e}", "error")
            messagebox.showerror("启动失败", f"Streamlit 启动失败:\n{e}")

    # ── 重置流程 ────────────────────────────────────────────

    def _reset(self):
        """重置所有按钮状态，清空日志，保留中间文件"""
        confirm = messagebox.askyesno(
            "确认重置",
            "重置将清空日志并恢复初始状态。\n\n"
            "data/ 目录下的 .csv / .pkl / .png 文件不会被删除。\n"
            "确认继续？"
        )
        if not confirm:
            return

        self._log_separator()
        self._log("[重置] 正在重置流程状态 ...", "warning")

        for i, btn in enumerate(self.buttons):
            btn.config(
                text=BTN_LABELS[i],
                state=tk.NORMAL if i == 0 else tk.DISABLED,
                bg="#4A90D9" if i == 0 else "#E0E0E0",
                fg="white" if i == 0 else "#666666",
                disabledforeground="#666666",
            )

        self.step_done = [False] * 5

        if self.streamlit_process and self.streamlit_process.poll() is None:
            self._log("[重置] 提示: Streamlit 进程仍在运行，建议手动关闭", "warning")
            self.streamlit_process = None

        self._log("[重置] 重置完成，请从第一步开始。", "info")
        self._log_separator()

    # ── 窗口关闭处理 ───────────────────────────────────────

    def on_closing(self):
        if self.streamlit_process and self.streamlit_process.poll() is None:
            if messagebox.askyesno("确认退出", "Streamlit 进程仍在运行，是否终止？"):
                self.streamlit_process.terminate()
                self.streamlit_process.wait(timeout=5)
        self.root.destroy()


# ============================================================
#  程序入口
# ============================================================

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    root = tk.Tk()
    app = BilibiliAnalyzerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
