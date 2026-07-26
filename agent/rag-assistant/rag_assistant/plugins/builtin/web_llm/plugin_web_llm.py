"""
网络 API 大模型插件 — 内置插件（配置壳）

非 input_return / input_output，不参与对话流程。
支持多组配置（profile），每组含 name + base_url + api_key + model + 参数。
LLMClient 在运行时按模型名匹配对应的配置调用。

配置存储格式（data/plugins/web_llm/config.json）:
{
  "profiles": [
    { "name": "...", "base_url": "...", "api_key": "...", "model": "...",
      "temperature": 0.7, "top_p": 1.0, "max_tokens": 4096 },
    ...
  ]
}
兼容旧格式（无 profiles 字段的单 dict）：读取时自动包装为 profiles[0]。
"""
import json
import logging
import sys
import os

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    tk = None
    ttk = None
    messagebox = None

from rag_assistant.plugins.base import PluginBase

logger = logging.getLogger(__name__)

# ── 服务商预设 ──────────────────────────────────────────
PRESETS = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model_hint": "gpt-4o / gpt-4o-mini / o3-mini",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model_hint": "deepseek-chat / deepseek-reasoner",
    },
    "qwen": {
        "label": "通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_hint": "qwen-max / qwen-plus / qwen-turbo",
    },
    "zhipu": {
        "label": "智谱",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model_hint": "glm-4-plus / glm-4-flash / glm-4-air",
    },
    "custom": {
        "label": "自定义",
        "base_url": "",
        "model_hint": "输入你的模型名",
    },
}

# ═══════════════ 公共工具 ═══════════════

def _detect_preset(config: dict) -> str:
    """根据 base_url 检测匹配的服务商预设名"""
    url = config.get("base_url", "").rstrip("/")
    for key, info in PRESETS.items():
        if key == "custom":
            continue
        if info["base_url"] and url == info["base_url"].rstrip("/"):
            return info["label"]
    for key, info in PRESETS.items():
        if key == "custom":
            continue
        if info["base_url"] and info["base_url"].rstrip("/") in url:
            return info["label"]
    return "自定义"


def _build_profile_form(parent, config: dict, on_save):
    """在 parent frame 中构建单条 profile 的编辑表单，返回 (frame, getter)"""
    fields = {}

    row = ttk.Frame(parent)
    row.pack(fill="x", pady=1)

    # 名称
    ttk.Label(row, text="配置名称：", font=("", 10, "bold")).pack(anchor="w")
    name_var = tk.StringVar(value=config.get("name", ""))
    ttk.Entry(row, textvariable=name_var, width=50).pack(fill="x", pady=(0, 6))
    fields["name"] = name_var

    # 服务商预设
    ttk.Label(row, text="服务商：").pack(anchor="w")
    preset_var = tk.StringVar(value=_detect_preset(config))
    preset_combo = ttk.Combobox(row, textvariable=preset_var, state="readonly", width=40)
    preset_combo["values"] = [v["label"] for v in PRESETS.values()]
    preset_combo.pack(fill="x", pady=(0, 6))
    fields["preset_var"] = preset_var

    # API 地址
    ttk.Label(row, text="API 地址：").pack(anchor="w")
    base_url_var = tk.StringVar(value=config.get("base_url", "https://api.openai.com/v1"))
    ttk.Entry(row, textvariable=base_url_var, width=50).pack(fill="x", pady=(0, 6))
    fields["base_url_var"] = base_url_var

    # API Key
    ttk.Label(row, text="API Key：").pack(anchor="w")
    key_frame = ttk.Frame(row)
    key_frame.pack(fill="x", pady=(0, 6))
    api_key_var = tk.StringVar(value=config.get("api_key", ""))
    api_key_entry = ttk.Entry(key_frame, textvariable=api_key_var, width=46, show="*")
    api_key_entry.pack(side="left")
    show_key_var = tk.BooleanVar(value=False)
    def toggle_key():
        api_key_entry.config(show="" if show_key_var.get() else "*")
    ttk.Checkbutton(key_frame, text="显示", variable=show_key_var, command=toggle_key).pack(side="left", padx=(4, 0))
    fields["api_key_var"] = api_key_var

    # 模型名
    ttk.Label(row, text="模型名：").pack(anchor="w")
    model_var = tk.StringVar(value=config.get("model", "gpt-4o"))
    ttk.Entry(row, textvariable=model_var, width=50).pack(fill="x", pady=(0, 6))
    fields["model_var"] = model_var

    # 预设切换 → 自动填 API 地址 + 模型提示
    def on_preset_change(*_):
        label = preset_var.get()
        for key, info in PRESETS.items():
            if info["label"] == label:
                base_url_var.set(info["base_url"])
                hint_label.config(text=info["model_hint"])
                break
    preset_var.trace_add("write", on_preset_change)

    hint_label = ttk.Label(row, text="gpt-4o / gpt-4o-mini / o3-mini",
                           foreground="#888", font=("", 9))
    hint_label.pack(anchor="w", pady=(0, 8))

    ttk.Separator(row, orient="horizontal").pack(fill="x", pady=4)

    # 温度
    temp_frame = ttk.Frame(row)
    temp_frame.pack(fill="x", pady=2)
    temp_var = tk.DoubleVar(value=config.get("temperature", 0.7))
    ttk.Label(temp_frame, text="温度：").pack(side="left")
    temp_scale = ttk.Scale(temp_frame, from_=0.0, to=2.0, orient="horizontal",
                           variable=temp_var, length=200)
    temp_scale.pack(side="left", padx=(6, 4))
    temp_label = ttk.Label(temp_frame, text=f"{temp_var.get():.1f}", width=4)
    temp_label.pack(side="left")
    def upd_temp(*_):
        temp_label.config(text=f"{temp_var.get():.1f}")
    temp_var.trace_add("write", upd_temp)
    fields["temp_var"] = temp_var

    # Top P
    topp_frame = ttk.Frame(row)
    topp_frame.pack(fill="x", pady=2)
    topp_var = tk.DoubleVar(value=config.get("top_p", 1.0))
    ttk.Label(topp_frame, text="Top P：").pack(side="left")
    topp_scale = ttk.Scale(topp_frame, from_=0.0, to=1.0, orient="horizontal",
                           variable=topp_var, length=200)
    topp_scale.pack(side="left", padx=(6, 4))
    topp_label = ttk.Label(topp_frame, text=f"{topp_var.get():.2f}", width=4)
    topp_label.pack(side="left")
    def upd_topp(*_):
        topp_label.config(text=f"{topp_var.get():.2f}")
    topp_var.trace_add("write", upd_topp)
    fields["topp_var"] = topp_var

    # 最大输出 Token
    mt_frame = ttk.Frame(row)
    mt_frame.pack(fill="x", pady=2)
    mt_var = tk.IntVar(value=config.get("max_tokens", 4096))
    ttk.Label(mt_frame, text="Token：").pack(side="left")
    ttk.Spinbox(mt_frame, from_=256, to=131072, increment=1024,
                textvariable=mt_var, width=10).pack(side="left", padx=(6, 4))
    ttk.Label(mt_frame, text="(256~131072)", foreground="#888",
              font=("", 9)).pack(side="left")
    fields["mt_var"] = mt_var

    return row, fields


def _collect_profile(fields: dict) -> dict:
    """从 fields 中收集 profile 数据"""
    return {
        "name": fields["name"].get().strip(),
        "base_url": fields["base_url_var"].get().strip().rstrip("/"),
        "api_key": fields["api_key_var"].get().strip(),
        "model": fields["model_var"].get().strip(),
        "temperature": round(fields["temp_var"].get(), 2),
        "top_p": round(fields["topp_var"].get(), 2),
        "max_tokens": fields["mt_var"].get(),
    }


# ═══════════════ 插件主类 ═══════════════

class WebLLMPlugin(PluginBase):
    """网络 API 大模型配置插件 — 支持多组配置"""

    def __init__(self):
        super().__init__()

    async def execute(self, inputs: dict) -> dict:
        """不执行任何操作——此插件仅为配置壳"""
        return {"type": "plain_text", "content": "", "priority": 0}

    def open_config_ui(self):
        """打开多配置文件管理主界面"""
        if tk is None:
            logger.error("Tkinter 不可用，无法打开配置界面")
            return

        self._profiles = self._load_profiles()
        self._main_win = tk.Tk()
        self._main_win.title(f"网络 API 大模型配置 — {self.display_name}")
        self._main_win.geometry("620x420")
        self._main_win.resizable(False, False)
        self._build_main_ui()
        self._main_win.mainloop()

    # ── 主界面 ──

    def _build_main_ui(self):
        win = self._main_win
        main = ttk.Frame(win, padding=12)
        main.pack(fill="both", expand=True)

        # 标题
        ttk.Label(main, text="已配置的 API 模型", font=("", 11, "bold")).pack(anchor="w")

        # 列表
        list_frame = ttk.Frame(main)
        list_frame.pack(fill="both", expand=True, pady=(6, 8))

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self._profile_listbox = tk.Listbox(
            list_frame, yscrollcommand=scrollbar.set,
            font=("", 10), height=10,
            selectmode="single", activestyle="none",
        )
        scrollbar.config(command=self._profile_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self._profile_listbox.pack(side="left", fill="both", expand=True)

        # 填充列表
        self._refresh_listbox()

        # 按钮行
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(0, 4))
        ttk.Button(btn_frame, text="添加配置 +", command=self._on_add).pack(side="left", padx=(0, 6))
        ttk.Button(btn_frame, text="编辑", command=self._on_edit).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="删除", command=self._on_delete).pack(side="left", padx=6)

        # 提示
        ttk.Label(main, text="添加后，在 LLM 配置中选择「Web API」后端并刷新模型列表即可看到已配置的模型。",
                  foreground="#888", font=("", 9), wraplength=580).pack(anchor="w", pady=(4, 0))

    def _refresh_listbox(self):
        self._profile_listbox.delete(0, "end")
        for i, p in enumerate(self._profiles):
            label = f"{p.get('name', '未命名')}  →  {p.get('model', '?')}"
            self._profile_listbox.insert("end", label)

    def _get_selected_index(self) -> int:
        sel = self._profile_listbox.curselection()
        return sel[0] if sel else -1

    # ── 增删改 ──

    def _on_add(self):
        self._open_editor(index=None)

    def _on_edit(self):
        idx = self._get_selected_index()
        if idx < 0:
            messagebox.showwarning("提示", "请先选择一个配置")
            return
        self._open_editor(index=idx)

    def _on_delete(self):
        idx = self._get_selected_index()
        if idx < 0:
            return
        profile = self._profiles[idx]
        if messagebox.askyesno("确认删除", f"确定删除配置\n{profile.get('name', '未命名')}？"):
            del self._profiles[idx]
            self._save_profiles()
            self._refresh_listbox()

    # ── 编辑器窗口 ──

    def _open_editor(self, index):
        """打开单条 profile 的编辑窗口（新建/编辑共用）"""
        is_new = index is None
        config_data = {} if is_new else dict(self._profiles[index])

        editor = tk.Toplevel(self._main_win)
        editor.title("添加配置" if is_new else "编辑配置")
        editor.geometry("600x500")
        editor.resizable(False, False)
        editor.transient(self._main_win)
        editor.grab_set()

        canvas = tk.Canvas(editor)
        scrollbar = ttk.Scrollbar(editor, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)

        form_frame, fields = _build_profile_form(scroll_frame, config_data, None)

        status_var = tk.StringVar()
        ttk.Label(scroll_frame, textvariable=status_var, foreground="green").pack(pady=(4, 0))

        def do_save():
            profile = _collect_profile(fields)
            if not profile["name"]:
                status_var.config(text="配置名称不能为空", foreground="red")
                return
            if not profile["base_url"]:
                status_var.config(text="API 地址不能为空", foreground="red")
                return
            if not profile["model"]:
                status_var.config(text="模型名不能为空", foreground="red")
                return
            # 检查名称唯一性
            for i, p in enumerate(self._profiles):
                if i != index and p.get("name") == profile["name"]:
                    status_var.config(text=f"配置名称「{profile['name']}」已存在", foreground="red")
                    return

            if is_new:
                self._profiles.append(profile)
            else:
                self._profiles[index] = profile
            self._save_profiles()
            self._refresh_listbox()
            status_var.config(text="已保存", foreground="green")
            editor.after(800, editor.destroy)

        btn_row = ttk.Frame(scroll_frame)
        btn_row.pack(pady=(10, 0))
        ttk.Button(btn_row, text="保存", command=do_save).pack(side="left", padx=4)
        ttk.Button(btn_row, text="取消", command=editor.destroy).pack(side="left", padx=4)

    # ═══════════════ 配置持久化 ═══════════════

    def _load_profiles(self) -> list:
        """加载所有 profile，兼容旧格式"""
        from pathlib import Path
        base = Path(self.data_dir) if self.data_dir else Path()
        config_file = base / "config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if "profiles" in raw:
                    return raw["profiles"]
                if isinstance(raw, dict) and "base_url" in raw:
                    return [raw]
            except Exception as e:
                logger.error(f"加载 web_llm 配置失败: {e}")
        return []

    def _save_profiles(self):
        """保存所有 profile"""
        from pathlib import Path
        base = Path(self.data_dir) if self.data_dir else Path()
        config_file = base / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"profiles": self._profiles}, f, ensure_ascii=False, indent=2)
        logger.info(f"web_llm 配置已保存: {len(self._profiles)} 个 profile")

    def get_all_models(self) -> list:
        """返回所有已配置的模型名列表（供 LLMClient 调用）"""
        return [p.get("model", "") for p in self._profiles if p.get("model")]

    def get_profile_by_model(self, model_name: str) -> dict:
        """按模型名查找对应的配置"""
        for p in self._profiles:
            if p.get("model") == model_name:
                return p
        return self._profiles[0] if self._profiles else {}
