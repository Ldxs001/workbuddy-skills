"""
gui_agent.py — Skill Pipeline Orchestrator
左栏技能列表 | 右栏编排画布 | 底部 LLM 输入+控制
"""

import os, sys, json, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from datetime import datetime
from typing import Optional

# 支持直接运行 (python gui_agent.py) 和模块运行 (python -m local_agent.gui_agent)
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from chain_model import SkillInfo, Pipeline, PipelineNode
from skill_scanner import scan_skills, search_skills
from chain_engine import execute_pipeline, OUTPUT_DIR
from llm_client import LLMClient

CHAINS_DIR = os.path.join(_DIR, "chains")
SETTINGS_PATH = os.path.join(_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "skill_dirs": [os.path.expanduser("~/.workbuddy/skills")],
    "llm_timeout": 600,
    "script_timeout": 1800,
    "max_tokens": 16384,
    "auto_continue": True,
    "continuation_tokens": 16384,
    "max_continuations": 5,
    "semantic_split": False,
    "triphasic": False,
}

# ============================================================
# 全局 LLM 客户端（重用了旧代码的 LLMClient）
# ============================================================
_llm: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        from agent_config import AgentConfig
        cfg_path = os.path.join(_DIR, "working_memory.json")
        cfg = AgentConfig.load(cfg_path) if os.path.isfile(cfg_path) else AgentConfig()
        _llm = LLMClient(cfg)  # LLMClient 接受 AgentConfig 对象
    return _llm


# ============================================================
# 主窗口
# ============================================================
class Orchestrator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Skill Pipeline Orchestrator")
        self.root.geometry("1100x680")
        self.root.configure(bg="#1a1a2e")
        self.root.minsize(800, 500)

        self.skills: list[SkillInfo] = []
        self.pipeline = Pipeline()
        self._node_counter = 0  # 用于编号
        self.settings = dict(DEFAULT_SETTINGS)
        self._load_settings()

        os.makedirs(CHAINS_DIR, exist_ok=True)

        self._build_ui()
        self._scan_skills()

    # ==================== 设置 ====================

    def _load_settings(self):
        if os.path.isfile(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    user = json.load(f)
                d = dict(DEFAULT_SETTINGS)
                d.update(user)
                self.settings = d
            except Exception:
                pass

    def _save_settings(self):
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _show_settings(self):
        """设置对话框（左：设置项 | 右：使用手册）"""
        win = tk.Toplevel(self.root)
        win.title("设置")
        win.geometry("760x520")
        win.configure(bg="#1a1a2e")
        win.resizable(False, False)

        # ── 主布局：左设置 + 右手册 ──
        pw = tk.PanedWindow(win, orient=tk.HORIZONTAL, bg="#1a1a2e",
                             sashrelief=tk.FLAT, sashwidth=2)
        pw.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # ========== 左栏：设置内容 ==========
        left = tk.Frame(pw, bg="#1a1a2e")
        pw.add(left, width=500, minsize=420)

        # ---- 技能目录 ----
        tk.Label(left, text="技能扫描目录", bg="#1a1a2e", fg="#7f77dd",
                 font=("微软雅黑", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 2))

        dir_frame = tk.Frame(left, bg="#1a1a2e")
        dir_frame.pack(fill=tk.X, padx=12, pady=(0, 6))

        self._settings_dir_listbox = tk.Listbox(dir_frame, bg="#16213e", fg="#e0e0e0",
                                                  font=("微软雅黑", 9), height=4,
                                                  relief=tk.FLAT, highlightthickness=0)
        self._settings_dir_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for d in self.settings.get("skill_dirs", []):
            self._settings_dir_listbox.insert(tk.END, d)

        dir_btn_frame = tk.Frame(dir_frame, bg="#1a1a2e")
        dir_btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))

        def add_dir():
            d = filedialog.askdirectory(title="选择技能目录")
            if d:
                self._settings_dir_listbox.insert(tk.END, d)

        def remove_dir():
            sel = self._settings_dir_listbox.curselection()
            if sel:
                self._settings_dir_listbox.delete(sel[0])

        tk.Button(dir_btn_frame, text="+ 添加", bg="#2a2a4e", fg="#e0e0e0",
                  font=("微软雅黑", 9), relief=tk.FLAT, command=add_dir).pack(pady=2)
        tk.Button(dir_btn_frame, text="× 删除", bg="#2a2a4e", fg="#e0e0e0",
                  font=("微软雅黑", 9), relief=tk.FLAT, command=remove_dir).pack(pady=2)

        # ---- 超时设置 ----
        tk.Label(left, text="超时设置（秒）", bg="#1a1a2e", fg="#7f77dd",
                 font=("微软雅黑", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 2))

        timeout_frame = tk.Frame(left, bg="#1a1a2e")
        timeout_frame.pack(fill=tk.X, padx=12, pady=(0, 6))

        tk.Label(timeout_frame, text="LLM 请求超时:", bg="#1a1a2e", fg="#e0e0e0",
                 font=("微软雅黑", 10)).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._settings_llm_timeout = tk.Entry(timeout_frame, bg="#16213e", fg="#e0e0e0",
                                                font=("微软雅黑", 10), width=10,
                                                relief=tk.FLAT, highlightthickness=0)
        self._settings_llm_timeout.insert(0, str(self.settings.get("llm_timeout", 600)))
        self._settings_llm_timeout.grid(row=0, column=1, sticky="w", ipady=2)
        tk.Label(timeout_frame, text="建议 600~3600（10分钟~1小时）", bg="#1a1a2e", fg="#666",
                 font=("微软雅黑", 8)).grid(row=0, column=2, sticky="w", padx=8)

        tk.Label(timeout_frame, text="脚本执行超时:", bg="#1a1a2e", fg="#e0e0e0",
                 font=("微软雅黑", 10)).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        self._settings_script_timeout = tk.Entry(timeout_frame, bg="#16213e", fg="#e0e0e0",
                                                   font=("微软雅黑", 10), width=10,
                                                   relief=tk.FLAT, highlightthickness=0)
        self._settings_script_timeout.insert(0, str(self.settings.get("script_timeout", 1800)))
        self._settings_script_timeout.grid(row=1, column=1, sticky="w", pady=(4, 0), ipady=2)
        tk.Label(timeout_frame, text="建议 1800~86400（30分钟~24小时）", bg="#1a1a2e", fg="#666",
                 font=("微软雅黑", 8)).grid(row=1, column=2, sticky="w", padx=8, pady=(4, 0))

        # ---- max_tokens ----
        tk.Label(left, text="LLM max_tokens（最大输出 token 数）", bg="#1a1a2e", fg="#7f77dd",
                 font=("微软雅黑", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 2))

        mt_frame = tk.Frame(left, bg="#1a1a2e")
        mt_frame.pack(fill=tk.X, padx=12, pady=(0, 6))
        tk.Label(mt_frame, text="max_tokens:", bg="#1a1a2e", fg="#e0e0e0",
                 font=("微软雅黑", 10)).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._settings_max_tokens = tk.Entry(mt_frame, bg="#16213e", fg="#e0e0e0",
                                               font=("微软雅黑", 10), width=10,
                                               relief=tk.FLAT, highlightthickness=0)
        self._settings_max_tokens.insert(0, str(self.settings.get("max_tokens", 16384)))
        self._settings_max_tokens.grid(row=0, column=1, sticky="w", ipady=2)
        tk.Label(mt_frame, text="模型含推理 token，建议 8192~32768", bg="#1a1a2e", fg="#666",
                 font=("微软雅黑", 8)).grid(row=0, column=2, sticky="w", padx=8)

        # ---- 自动续接设置 ----
        tk.Label(left, text="自动续接（finish_reason=length 时自动追加请求）", bg="#1a1a2e", fg="#7f77dd",
                 font=("微软雅黑", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 2))

        cont_frame = tk.Frame(left, bg="#1a1a2e")
        cont_frame.pack(fill=tk.X, padx=12, pady=(0, 6))

        self._settings_auto_continue = tk.BooleanVar(value=self.settings.get("auto_continue", True))
        tk.Checkbutton(cont_frame, text="启用续接", variable=self._settings_auto_continue,
                       bg="#1a1a2e", fg="#e0e0e0", selectcolor="#16213e",
                       font=("微软雅黑", 10),
                       activebackground="#1a1a2e", activeforeground="#7f77dd"
                       ).grid(row=0, column=0, sticky="w", padx=(0, 20))

        tk.Label(cont_frame, text="续接 token 数:", bg="#1a1a2e", fg="#e0e0e0",
                 font=("微软雅黑", 10)).grid(row=0, column=1, sticky="w")
        self._settings_cont_tokens = tk.Entry(cont_frame, bg="#16213e", fg="#e0e0e0",
                                               font=("微软雅黑", 10), width=8,
                                               relief=tk.FLAT, highlightthickness=0)
        self._settings_cont_tokens.insert(0, str(self.settings.get("continuation_tokens", 16384)))
        self._settings_cont_tokens.grid(row=0, column=2, sticky="w", padx=4, ipady=2)

        tk.Label(cont_frame, text="续接次数:", bg="#1a1a2e", fg="#e0e0e0",
                 font=("微软雅黑", 10)).grid(row=0, column=3, sticky="w", padx=(8, 0))
        self._settings_max_cont = tk.Entry(cont_frame, bg="#16213e", fg="#e0e0e0",
                                            font=("微软雅黑", 10), width=5,
                                            relief=tk.FLAT, highlightthickness=0)
        self._settings_max_cont.insert(0, str(self.settings.get("max_continuations", 5)))
        self._settings_max_cont.grid(row=0, column=4, sticky="w", padx=4, ipady=2)

        # ---- 功能勾选 ----
        tk.Label(left, text="可选功能（勾选启用）", bg="#1a1a2e", fg="#7f77dd",
                 font=("微软雅黑", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 2))

        feat_frame = tk.Frame(left, bg="#1a1a2e")
        feat_frame.pack(fill=tk.X, padx=12, pady=(0, 6))

        self._settings_semantic = tk.BooleanVar(value=self.settings.get("semantic_split", False))
        tk.Checkbutton(feat_frame, text="语义拆分（semantic-split）",
                       variable=self._settings_semantic,
                       bg="#1a1a2e", fg="#e0e0e0", selectcolor="#16213e",
                       font=("微软雅黑", 10),
                       activebackground="#1a1a2e", activeforeground="#7f77dd"
                       ).pack(side=tk.LEFT, padx=(0, 16))

        self._settings_triphasic = tk.BooleanVar(value=self.settings.get("triphasic", False))
        tk.Checkbutton(feat_frame, text="三步自审（triphasic）",
                       variable=self._settings_triphasic,
                       bg="#1a1a2e", fg="#e0e0e0", selectcolor="#16213e",
                       font=("微软雅黑", 10),
                       activebackground="#1a1a2e", activeforeground="#7f77dd"
                       ).pack(side=tk.LEFT)

        # ---- 底部按钮 ----
        btn_frame = tk.Frame(left, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, padx=12, pady=(10, 10))

        def save_settings():
            dirs = list(self._settings_dir_listbox.get(0, tk.END))
            if not dirs:
                messagebox.showwarning("警告", "至少需要一个技能目录")
                return
            self.settings["skill_dirs"] = dirs
            try:
                self.settings["llm_timeout"] = int(self._settings_llm_timeout.get())
                self.settings["script_timeout"] = int(self._settings_script_timeout.get())
                self.settings["max_tokens"] = int(self._settings_max_tokens.get())
                self.settings["auto_continue"] = self._settings_auto_continue.get()
                self.settings["continuation_tokens"] = int(self._settings_cont_tokens.get())
                self.settings["max_continuations"] = int(self._settings_max_cont.get())
                self.settings["semantic_split"] = self._settings_semantic.get()
                self.settings["triphasic"] = self._settings_triphasic.get()
            except ValueError:
                messagebox.showerror("错误", "超时、max_tokens 和续接设置必须是数字")
                return
            self._save_settings()
            win.destroy()
            self._scan_skills()

        tk.Button(btn_frame, text="保存", bg="#7f77dd", fg="white",
                  font=("微软雅黑", 10), relief=tk.FLAT,
                  command=save_settings).pack(side=tk.RIGHT, padx=2)
        tk.Button(btn_frame, text="取消", bg="#2a2a4e", fg="#e0e0e0",
                  font=("微软雅黑", 10), relief=tk.FLAT,
                  command=win.destroy).pack(side=tk.RIGHT, padx=2)

        # ========== 右栏：使用手册 ==========
        right = tk.Frame(pw, bg="#16213e")
        pw.add(right, width=230, minsize=200)

        tk.Label(right, text="📖 使用手册", bg="#16213e", fg="#7f77dd",
                 font=("微软雅黑", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 4))

        manual_text = tk.Text(right, bg="#16213e", fg="#c0c0c0",
                               font=("微软雅黑", 9), wrap=tk.WORD,
                               relief=tk.FLAT, highlightthickness=0,
                               padx=8, pady=4, state=tk.NORMAL)
        manual_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        manual = """▸ 主界面

左栏搜索添加技能到流水线，右栏编排步骤顺序（+顺序/+并行/+循环），底部输入任务描述后运行。

▸ skill-sub 优化
勾选后自动分析流水线结构：连续同技能→循环，独立步骤→并行，重复→去重。

▸ 语义拆分
勾选后自动用 5W2H 分析用户意图，拆解为子步骤再执行。

▸ 三步自审
勾选后每步执行→审查→推进循环。审查包括 HTML 校验、颜色对比度检查、LLM 深度审查。失败自动重试最多 3 次。

▸ 自动续接
LLM 输出截断（finish_reason=length）时自动追加"继续"请求。续接 token 数可独立设置。

▸ max_tokens
含推理 token 的模型时，注意上下文限制（如 32K/96K/128K）。

▸ 超时
复杂流水线建议 LLM 超时≥600s，脚本超时≥1800s。

▸ 内置工具（常驻）
文件原子读写、颜色校验、Python 自动装包、HTML 校验均内置于执行引擎，无需勾选。"""
        manual_text.insert("1.0", manual)
        manual_text.config(state=tk.DISABLED)

    # ==================== UI 构建 ====================

    def _build_ui(self):
        # 主布局：左 + 右，grid 双列
        self.root.grid_rowconfigure(0, weight=1)   # 主区域
        self.root.grid_rowconfigure(1, weight=0)   # 底部
        self.root.grid_columnconfigure(0, weight=0, minsize=260)  # 左栏 260px
        self.root.grid_columnconfigure(1, weight=1)  # 右栏吃剩余

        # ========== 左栏：技能列表 ==========
        left = tk.Frame(self.root, bg="#16213e")
        left.grid(row=0, column=0, sticky="nsew", padx=(6, 3), pady=6)
        for r in (0, 2, 3):
            left.grid_rowconfigure(r, weight=0)
        left.grid_rowconfigure(1, weight=1)  # treeview 吃剩余
        left.grid_columnconfigure(0, weight=1)

        # 标题 + 搜索框同一行（与右栏对齐）
        lf = tk.Frame(left, bg="#16213e")
        lf.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 4))
        tk.Label(lf, text="技能列表", bg="#16213e", fg="#7f77dd",
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *_: self._filter_skills())
        tk.Entry(lf, textvariable=self.search_var,
                 bg="#1a1a2e", fg="#e0e0e0", insertbackground="#7f77dd",
                 relief=tk.FLAT, font=("微软雅黑", 10)
                 ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), ipady=2)

        # 技能列表（三列）
        self.skill_tree = ttk.Treeview(left, columns=("ver", "desc"),
                                       show="tree headings", selectmode="browse")
        for col, w in (("#0", 120), ("ver", 55), ("desc", 180)):
            self.skill_tree.column(col, width=w, minwidth=w, stretch=True)
        self.skill_tree.heading("#0", text="技能名")
        self.skill_tree.heading("ver", text="版本")
        self.skill_tree.heading("desc", text="简介")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1a1a2e", fieldbackground="#1a1a2e",
                        foreground="#e0e0e0", font=("微软雅黑", 10), rowheight=22)
        style.configure("Treeview.Heading", background="#16213e",
                        foreground="#7f77dd", font=("微软雅黑", 10, "bold"))
        style.map("Treeview", background=[("selected", "#2a2a4e")])

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.skill_tree.yview)
        self.skill_tree.configure(yscrollcommand=vsb.set)
        self.skill_tree.grid(row=1, column=0, sticky="nsew", padx=(6, 0), pady=6)
        vsb.grid(row=1, column=1, sticky="ns", pady=6)

        self.skill_tree.bind("<Double-1>", lambda e: self._add_selected_skill())
        self.skill_tree.bind("<<TreeviewSelect>>", lambda e: self._show_skill_desc())

        # 底部固定区域：描述 + 按钮（不受 treeview 大小影响）
        self._skill_desc_var = tk.StringVar()
        tk.Label(left, textvariable=self._skill_desc_var, bg="#16213e", fg="#666",
                 font=("微软雅黑", 8), wraplength=240, anchor="w", justify="left",
                 height=2
                 ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 0))

        bf = tk.Frame(left, bg="#16213e")
        bf.grid(row=3, column=0, columnspan=2, sticky="ew", padx=6, pady=4)
        bf.grid_columnconfigure(0, weight=0)
        bf.grid_columnconfigure(1, weight=1)
        tk.Button(bf, text="刷新", bg="#2a2a4e", fg="#e0e0e0",
                  font=("微软雅黑", 9), relief=tk.FLAT,
                  command=self._scan_skills).grid(row=0, column=0, padx=2)
        tk.Button(bf, text="添加到流水线", bg="#7f77dd", fg="white",
                  font=("微软雅黑", 9), relief=tk.FLAT,
                  command=self._add_selected_skill).grid(row=0, column=1, sticky="e", padx=2)

        # ========== 右栏：编排画布 ==========
        right = tk.Frame(self.root, bg="#16213e")
        right.grid(row=0, column=1, sticky="nsew", padx=(3, 6), pady=6)
        for r in (0, 2):
            right.grid_rowconfigure(r, weight=0)
        right.grid_rowconfigure(1, weight=1)  # pipe treeview 吃剩余
        right.grid_columnconfigure(0, weight=1)

        # 标题 + 流水线名称
        tf = tk.Frame(right, bg="#16213e")
        tf.grid(row=0, column=0, sticky="ew", padx=6, pady=(0, 4))
        tk.Label(tf, text="编排画布", bg="#16213e", fg="#7f77dd",
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.pipeline_name_var = tk.StringVar(value="未命名")
        tk.Entry(tf, textvariable=self.pipeline_name_var,
                 bg="#1a1a2e", fg="#e0e0e0", insertbackground="#7f77dd",
                 relief=tk.FLAT, font=("微软雅黑", 10), width=20
                 ).pack(side=tk.LEFT, padx=10, ipady=2)

        # 流水线 Treeview
        pf = tk.Frame(right, bg="#16213e")
        pf.grid(row=1, column=0, sticky="nsew")
        pf.grid_rowconfigure(0, weight=1)
        pf.grid_columnconfigure(0, weight=1)

        self.pipe_tree = ttk.Treeview(pf, columns=("mode",), show="tree")
        self.pipe_tree.column("#0", width=380, minwidth=250)
        self.pipe_tree.heading("#0", text="步骤")
        self.pipe_tree.column("mode", width=70, anchor="center")
        self.pipe_tree.heading("mode", text="模式")

        pvsb = ttk.Scrollbar(pf, orient="vertical", command=self.pipe_tree.yview)
        self.pipe_tree.configure(yscrollcommand=pvsb.set)
        self.pipe_tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        pvsb.grid(row=0, column=1, sticky="ns", pady=6)

        # 底部固定按钮
        cf = tk.Frame(right, bg="#16213e")
        cf.grid(row=2, column=0, sticky="ew", padx=6, pady=4)
        for spec in (
            ("+顺序", self._add_seq),
            ("+并行", self._wrap_par),
            ("+循环", self._wrap_loop),
            ("×删除", self._delete_selected),
            ("↑上移", self._move_up),
            ("↓下移", self._move_down),
        ):
            tk.Button(cf, text=spec[0], bg="#2a2a4e", fg="#e0e0e0",
                      font=("微软雅黑", 9), relief=tk.FLAT,
                      command=spec[1]).pack(side=tk.LEFT, padx=2)

        self.optimize_var = tk.BooleanVar(value=False)
        tk.Checkbutton(cf, text="skill-sub 优化", variable=self.optimize_var,
                       bg="#16213e", fg="#e0e0e0", selectcolor="#16213e",
                       font=("微软雅黑", 9),
                       activebackground="#16213e", activeforeground="#7f77dd"
                       ).pack(side=tk.RIGHT, padx=6)

        # ========== 底部 LLM 输入 + 控制 ==========
        self._build_bottom()

    def _build_bottom(self):
        """底部栏：LLM 输入 + 文件选择 + 操作按钮"""
        bottom = tk.Frame(self.root, bg="#16213e")
        bottom.grid(row=1, column=0, columnspan=2, sticky="nsew",
                     padx=6, pady=(0, 6))
        bottom.grid_rowconfigure(0, weight=0)
        bottom.grid_rowconfigure(1, weight=1)
        bottom.grid_columnconfigure(1, weight=1)  # 输入框列吃剩余

        # ---- 行0: 文件选择 + 按钮 ----
        row0 = tk.Frame(bottom, bg="#16213e")
        row0.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(4, 2))

        tk.Button(row0, text="📎 选文件", bg="#2a2a4e", fg="#e0e0e0",
                  font=("微软雅黑", 9), relief=tk.FLAT,
                  command=self._pick_file).pack(side=tk.LEFT, padx=2)
        tk.Button(row0, text="📁 选文件夹", bg="#2a2a4e", fg="#e0e0e0",
                  font=("微软雅黑", 9), relief=tk.FLAT,
                  command=self._pick_folder).pack(side=tk.LEFT, padx=2)
        tk.Button(row0, text="⚙ 设置", bg="#2a2a4e", fg="#e0e0e0",
                  font=("微软雅黑", 9), relief=tk.FLAT,
                  command=self._show_settings).pack(side=tk.LEFT, padx=2)

        # 操作按钮
        for btn_spec in [
            ("▶ 立即运行", "#7f77dd", self._run_pipeline),
            ("💾 保存链", "#2a2a4e", self._save_chain),
            ("📂 加载链", "#2a2a4e", self._load_chain),
        ]:
            tk.Button(row0, text=btn_spec[0], bg=btn_spec[1], fg="white",
                      font=("微软雅黑", 9), relief=tk.FLAT,
                      command=btn_spec[2]).pack(side=tk.RIGHT, padx=2)

        # ---- 行1: 输入框 ----
        self.input_text = tk.Text(bottom, bg="#1a1a2e", fg="#e0e0e0",
                                   insertbackground="#7f77dd",
                                   font=("微软雅黑", 10), relief=tk.FLAT,
                                   height=3, padx=8, pady=6,
                                   highlightthickness=0, wrap=tk.WORD)
        self.input_text.grid(row=1, column=0, columnspan=4, sticky="nsew",
                             padx=6, pady=(0, 4))
        self.input_text.insert("1.0", "输入自然语言、文件路径...")

        # ---- 行2: 进度条 ----
        self.progress_var = tk.StringVar(value="就绪")
        self.progress_label = tk.Label(bottom, textvariable=self.progress_var,
                                       bg="#16213e", fg="#888888",
                                       font=("微软雅黑", 9))
        self.progress_label.grid(row=2, column=0, columnspan=4, sticky="w",
                                 padx=8, pady=(0, 4))

    # ==================== 技能扫描 ====================

    def _scan_skills(self):
        self.skill_tree.delete(*self.skill_tree.get_children())
        self.skills = scan_skills(*self.settings.get("skill_dirs", []))
        for s in self.skills:
            self.skill_tree.insert("", "end", iid=s.name,
                                   text=s.display_name or s.name,
                                   values=(s.version or "", (s.description or "")[:50]))
        if self.skills:
            self._skill_desc_var.set(f"共 {len(self.skills)} 个技能")
        self._show_skill_desc()

    def _filter_skills(self):
        q = self.search_var.get()
        self.skill_tree.delete(*self.skill_tree.get_children())
        filtered = search_skills(self.skills, q)
        for s in filtered:
            self.skill_tree.insert("", "end", iid=s.name,
                                   text=s.display_name or s.name,
                                   values=(s.version or "", (s.description or "")[:50]))
        self._skill_desc_var.set(f"共 {len(filtered)} 个技能（搜索: {q}）")

    def _show_skill_desc(self):
        """选中技能时显示完整描述"""
        sel = self.skill_tree.selection()
        if not sel:
            self._skill_desc_var.set("点击技能查看详情")
            return
        name = sel[0]
        skill = next((s for s in self.skills if s.name == name), None)
        if not skill:
            return
        desc = skill.description or "(无描述)"
        tags = ", ".join(skill.tags[:5]) if skill.tags else ""
        self._skill_desc_var.set(f"{desc[:80]}\n标签: {tags}" if tags else desc[:80])

    # ==================== 技能 → 流水线 ====================

    def _add_selected_skill(self):
        sel = self.skill_tree.selection()
        if not sel:
            return
        name = sel[0]
        skill = next((s for s in self.skills if s.name == name), None)
        if not skill:
            return
        self._node_counter += 1
        display = skill.display_name or skill.name
        node = PipelineNode(
            skill_name=skill.name,
            display_name=display,
            mode="seq",
        )
        self.pipeline.nodes.append(node)
        self._refresh_pipe_tree()

    def _add_seq(self):
        """添加一个空顺序节点（用于手动指定步骤名）"""
        name = simpledialog.askstring("添加步骤", "步骤名称（或技能名）:", parent=self.root)
        if not name:
            return
        self._node_counter += 1
        node = PipelineNode(skill_name=name, display_name=name, mode="seq")
        self.pipeline.nodes.append(node)
        self._refresh_pipe_tree()

    def _wrap_par(self):
        """将选中的节点包裹为并行"""
        selected = self.pipe_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先在流水线中选择要并行执行的步骤")
            return
        self._wrap_selected(selected, "par")

    def _wrap_loop(self):
        """将选中的节点包裹为循环"""
        selected = self.pipe_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择一个步骤作为循环体")
            return
        r = simpledialog.askstring("循环范围", "输入循环次数或范围 (如: 3 或 1-5):",
                                    parent=self.root)
        if not r:
            return
        times = None
        start, end = None, None
        try:
            if "-" in r:
                parts = r.split("-")
                start, end = int(parts[0]), int(parts[1])
                times = end - start + 1
            else:
                times = int(r)
        except ValueError:
            messagebox.showerror("错误", "格式不对，请输数字或 1-5")
            return
        self._wrap_selected(selected, "loop", times=times,
                            loop_start=start, loop_end=end)

    def _wrap_selected(self, selected: list, mode: str,
                       times=None, loop_start=None, loop_end=None):
        """将选中的 Treeview 节点转为容器节点的子节点"""
        # 找到选中的节点在 pipeline.nodes 中的索引
        ids_to_parent = {item: self.pipe_tree.parent(item) for item in selected}
        # 选中的必须是同级的
        parents = set(ids_to_parent.values())
        if len(parents) > 1:
            messagebox.showerror("错误", "只能包裹同一层级的节点")
            return

        parent_iid = list(parents)[0]
        # 收集选中的节点对象
        children = []
        for item in selected:
            node = self._treeitem_to_node(item)
            if node:
                children.append(node)
            self._remove_node_from_pipeline(item)

        container = PipelineNode(
            display_name="并行" if mode == "par" else f"循环 {loop_start or 1}→{loop_end or times or 1}",
            mode=mode,
            children=children,
            loop_times=times,
            loop_start=loop_start,
            loop_end=loop_end,
        )
        if parent_iid:
            # 找到父节点，把 container 加为兄弟
            parent_node = self._treeitem_to_node(parent_iid)
            if parent_node and hasattr(parent_node, 'children'):
                parent_node.children.append(container)
        else:
            # 根层级
            # 找到第一个选中项的位置
            first_item = selected[0]
            idx = self._find_node_index(first_item)
            if idx >= 0:
                self.pipeline.nodes.insert(idx, container)
            else:
                self.pipeline.nodes.append(container)
        self._refresh_pipe_tree()

    # ==================== 删除/移动 ====================

    def _delete_selected(self):
        sel = self.pipe_tree.selection()
        if not sel:
            return
        for item in sel:
            self._remove_node_from_pipeline(item)
        self._refresh_pipe_tree()

    def _move_up(self):
        sel = self.pipe_tree.selection()
        if not sel or len(sel) != 1:
            return
        item = sel[0]
        parent = self.pipe_tree.parent(item)
        if parent:
            parent_node = self._treeitem_to_node(parent)
            if parent_node and hasattr(parent_node, 'children'):
                children = parent_node.children
            else:
                return
        else:
            children = self.pipeline.nodes
        idx = self._find_node_index(item)
        if idx > 0:
            children[idx], children[idx-1] = children[idx-1], children[idx]
            self._refresh_pipe_tree()

    def _move_down(self):
        sel = self.pipe_tree.selection()
        if not sel or len(sel) != 1:
            return
        item = sel[0]
        parent = self.pipe_tree.parent(item)
        if parent:
            parent_node = self._treeitem_to_node(parent)
            if parent_node and hasattr(parent_node, 'children'):
                children = parent_node.children
            else:
                return
        else:
            children = self.pipeline.nodes
        idx = self._find_node_index(item)
        if idx < len(children) - 1:
            children[idx], children[idx+1] = children[idx+1], children[idx]
            self._refresh_pipe_tree()

    # ==================== 树 ↔ 数据模型 ====================

    def _treeitem_to_node(self, item_iid: str) -> Optional[PipelineNode]:
        """根据 Treeview item iid 找到对应的 PipelineNode"""
        # iid 格式: "node_{hash}" — 在 _node_to_treeitem 中设置
        # 遍历所有节点查找
        return self._find_node_in_list(self.pipeline.nodes, item_iid)

    def _find_node_in_list(self, nodes: list, iid: str) -> Optional[PipelineNode]:
        for n in nodes:
            if getattr(n, '_iid', None) == iid:
                return n
            if n.children:
                found = self._find_node_in_list(n.children, iid)
                if found:
                    return found
        return None

    def _find_node_index(self, item_iid: str) -> int:
        """在父级 list 中找到该节点的索引"""
        node = self._treeitem_to_node(item_iid)
        if not node:
            return -1
        parent = self.pipe_tree.parent(item_iid)
        if parent:
            parent_node = self._treeitem_to_node(parent)
            if parent_node and hasattr(parent_node, 'children'):
                lst = parent_node.children
            else:
                return -1
        else:
            lst = self.pipeline.nodes
        for i, n in enumerate(lst):
            if getattr(n, '_iid', None) == item_iid:
                return i
        return -1

    def _remove_node_from_pipeline(self, item_iid: str):
        node = self._treeitem_to_node(item_iid)
        if not node:
            return
        parent = self.pipe_tree.parent(item_iid)
        if parent:
            parent_node = self._treeitem_to_node(parent)
            if parent_node and hasattr(parent_node, 'children'):
                children = parent_node.children
            else:
                return
        else:
            children = self.pipeline.nodes
        for i, n in enumerate(children):
            if getattr(n, '_iid', None) == item_iid:
                children.pop(i)
                return

    def _refresh_pipe_tree(self):
        """刷新流水线 Treeview"""
        self.pipe_tree.delete(*self.pipe_tree.get_children())
        self._render_nodes(self.pipeline.nodes, parent="")

    def _render_nodes(self, nodes: list, parent: str = ""):
        """递归渲染节点到 Treeview"""
        for i, n in enumerate(nodes):
            # 生成显示文本
            if n.mode == "par":
                label = f"[并行 {len(n.children)}个]"
            elif n.mode == "loop":
                label = f"[循环 {n.loop_start or 1}→{n.loop_end or n.loop_times or 1}]"
            else:
                label = f"{i+1}. {n.display_name or n.skill_name or '(空)'}"

            mode_tag = n.mode.upper()
            iid = f"node_{id(n)}"
            n._iid = iid  # 绑定到对象

            item = self.pipe_tree.insert(parent, "end", iid=iid,
                                          text=label, values=(mode_tag,))
            if n.children:
                self._render_nodes(n.children, parent=iid)

    # ==================== LLM 输入 ====================

    def _pick_file(self):
        path = filedialog.askopenfilename(title="选择文件")
        if path:
            current = self.input_text.get("1.0", "end-1c")
            if current.strip() and current.strip() != "输入自然语言、文件路径...":
                self.input_text.insert("end", f"\n{path}")
            else:
                self.input_text.delete("1.0", "end")
                self.input_text.insert("1.0", path)

    def _pick_folder(self):
        path = filedialog.askdirectory(title="选择文件夹")
        if path:
            current = self.input_text.get("1.0", "end-1c")
            if current.strip() and current.strip() != "输入自然语言、文件路径...":
                self.input_text.insert("end", f"\n{path}")
            else:
                self.input_text.delete("1.0", "end")
                self.input_text.insert("1.0", path)

    # ==================== 保存/加载 ====================

    def _save_chain(self):
        name = self.pipeline_name_var.get().strip() or "未命名"
        self.pipeline.name = name
        self.pipeline.optimize = self.optimize_var.get()
        self.pipeline.updated = datetime.now().strftime("%Y-%m-%d %H:%M")
        fname = name.replace(" ", "_").replace("/", "_") + ".json"
        fpath = os.path.join(CHAINS_DIR, fname)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(self.pipeline.to_json())
            self._set_progress(f"已保存: {fname}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _load_chain(self):
        fpath = filedialog.askopenfilename(
            title="加载流水线",
            initialdir=CHAINS_DIR,
            filetypes=[("Pipeline JSON", "*.json"), ("All", "*.*")]
        )
        if not fpath:
            return
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                self.pipeline = Pipeline.from_json(f.read())
            self.pipeline_name_var.set(self.pipeline.name)
            self.optimize_var.set(self.pipeline.optimize)
            self._refresh_pipe_tree()
            self._set_progress(f"已加载: {os.path.basename(fpath)}")
        except Exception as e:
            messagebox.showerror("加载失败", str(e))

    # ==================== 执行 ====================

    def _run_pipeline(self):
        if not self.pipeline.nodes:
            messagebox.showinfo("提示", "流水线为空，请先添加技能步骤")
            return

        self.pipeline.name = self.pipeline_name_var.get().strip() or "未命名"
        self.pipeline.optimize = self.optimize_var.get()
        self.pipeline.semantic_split = self.settings.get("semantic_split", False)
        self.pipeline.triphasic = self.settings.get("triphasic", False)

        user_input = self.input_text.get("1.0", "end-1c").strip()
        if user_input == "输入自然语言、文件路径...":
            user_input = ""

        def run():
            self.root.after(0, lambda: self._set_progress("执行中..."))
            try:
                llm = get_llm()
                # 应用设置中的超时和 max_tokens
                llm.set_timeout(self.settings.get("llm_timeout", 600))
                llm.set_max_tokens(self.settings.get("max_tokens", 16384))
                # 续接设置
                llm.continuation_enabled = self.settings.get("auto_continue", True)
                llm.set_max_continuations(self.settings.get("max_continuations", 5))
                llm.set_continuation_tokens(self.settings.get("continuation_tokens", 16384))
                result = execute_pipeline(
                    self.pipeline, llm,
                    user_intent=user_input or self.pipeline.name,
                    script_timeout=self.settings.get("script_timeout", 1800),
                    progress_callback=lambda msg: self.root.after(
                        0, lambda: self._set_progress(msg)
                    ),
                )
                self.root.after(0, lambda: self._show_result(result))
                self.root.after(0, lambda: self._set_progress("执行完成"))
            except Exception as e:
                self.root.after(0, lambda: self._set_progress(f"错误: {e}"))
                self.root.after(0, lambda: messagebox.showerror("执行失败", str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _show_result(self, text: str):
        """弹窗显示执行结果"""
        win = tk.Toplevel(self.root)
        win.title("执行结果")
        win.geometry("780x560")
        win.configure(bg="#1a1a2e")

        tk.Label(win, text="流水线执行结果", bg="#1a1a2e", fg="#7f77dd",
                 font=("微软雅黑", 12, "bold")).pack(pady=(8, 2))

        # 操作按钮行
        btn_row = tk.Frame(win, bg="#1a1a2e")
        btn_row.pack(fill=tk.X, padx=10, pady=(0, 4))

        # 保存结果文本
        result_path = None
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_path = os.path.join(OUTPUT_DIR, f"result_{ts}.txt")
            with open(result_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception:
            pass

        if result_path:
            def open_output():
                os.startfile(OUTPUT_DIR)
            tk.Button(btn_row, text="📂 打开 output 目录", bg="#2a2a4e", fg="#e0e0e0",
                      font=("微软雅黑", 9), relief=tk.FLAT,
                      command=open_output).pack(side=tk.LEFT, padx=2)

            def open_result():
                os.startfile(result_path)
            tk.Button(btn_row, text="📄 打开结果文件", bg="#2a2a4e", fg="#e0e0e0",
                      font=("微软雅黑", 9), relief=tk.FLAT,
                      command=open_result).pack(side=tk.LEFT, padx=2)

        def copy_text():
            win.clipboard_clear()
            win.clipboard_append(text)
        tk.Button(btn_row, text="📋 复制到剪贴板", bg="#2a2a4e", fg="#e0e0e0",
                  font=("微软雅黑", 9), relief=tk.FLAT,
                  command=copy_text).pack(side=tk.RIGHT, padx=2)

        # 结果文本框
        txt = tk.Text(win, bg="#16213e", fg="#e0e0e0",
                       font=("微软雅黑", 10), wrap=tk.WORD,
                       padx=10, pady=10, relief=tk.FLAT)
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        txt.insert("1.0", text)
        txt.config(state=tk.DISABLED)

    def _set_progress(self, msg: str):
        self.progress_var.set(msg)

    # ==================== 入口 ====================

    def run(self):
        self.root.mainloop()


def main():
    app = Orchestrator()
    app.run()


if __name__ == "__main__":
    main()
