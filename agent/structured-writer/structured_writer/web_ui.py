"""Web UI — HTTP 服务器 + 内联 HTML/CSS/JS 界面"""
import json
import os
import sys
import time
import tempfile
import subprocess
import threading
import http.server
import urllib.parse
import urllib.request
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config_manager import ConfigManager
from .llm_client import LLMClient, LLMClientError
from .state_manager import StateManager
from .planner import plan_outline
from .writer import generate_article

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# 后台生成任务跟踪 {session_id: {"thread": Thread, "done": bool, "result": dict|None, "error": str|None}}
_generation_tasks = {}
_gen_lock = threading.Lock()

# RAG 子进程管理
_rag_process = None
_rag_process_stderr = ""
_rag_lock = threading.Lock()
_rag_starting = False  # True while cold start is in progress


class StructuredWriterHandler(http.server.BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    config_mgr = None
    _lock = threading.Lock()

    # ---- 路由表 ----
    ROUTES = {
        "GET": {},
        "POST": {},
        "PUT": {}
    }

    @classmethod
    def _init_routes(cls):
        if cls.ROUTES["GET"]:
            return
        cls.ROUTES["GET"] = {
            "/": cls._handle_index,
            "/api/config": cls._handle_get_config,
            "/api/llm/test": cls._handle_llm_test,
            "/api/llm/models": cls._handle_llm_models,
            "/api/progress": cls._handle_get_progress,
            "/api/result": cls._handle_get_result,
            "/api/sessions": cls._handle_list_sessions,
            "/api/session/load": cls._handle_session_load,
            "/api/rag/status": cls._handle_rag_status,
        }
        cls.ROUTES["POST"] = {
            "/api/config": cls._handle_update_config,
            "/api/plan": cls._handle_plan,
            "/api/generate": cls._handle_generate,
            "/api/session/new": cls._handle_new_session,
            "/api/chat": cls._handle_chat,
            "/api/rag/start": cls._handle_rag_start,
        }

    def do_GET(self):
        self._init_routes()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        handler = self.ROUTES["GET"].get(path)
        if handler:
            handler(self)
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def do_POST(self):
        self._init_routes()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        handler = self.ROUTES["POST"].get(path)
        try:
            if handler:
                handler(self)
            else:
                self._json_response({"error": "Not found"}, 404)
        except Exception as e:
            try:
                self._json_response({"success": False, "error": str(e)}, 500)
            except Exception:
                pass

    # ---- 辅助方法 ----

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        # 容错：先 utf-8，失败则 latin-1（保 byte 不变）
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # 返回错误信息并让调用方处理
            raise ValueError(f"JSON 解析失败: {e}, 原始内容: {text[:200]}")

    def _json_response(self, data: dict, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _html_response(self, html: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    # ---- 首页 ----

    def _handle_index(self):
        self._html_response(INDEX_HTML)

    # ---- 配置 API ----

    def _handle_get_config(self):
        cfg = self.config_mgr.get_all()
        self._json_response({"success": True, "config": cfg})

    def _handle_update_config(self):
        data = self._read_body()
        self.config_mgr.update(data)
        self._json_response({"success": True})

    # ---- LLM API ----

    def _handle_llm_test(self):
        params = urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query
        )
        backend = (params.get("backend") or ["lmstudio"])[0]
        base_url = (params.get("base_url") or ["http://localhost:1234"])[0]
        client = LLMClient(backend=backend, base_url=base_url)
        ok, msg = client.test_connection()
        self._json_response({"success": ok, "message": msg})

    def _handle_llm_models(self):
        params = urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query
        )
        backend = (params.get("backend") or ["lmstudio"])[0]
        base_url = (params.get("base_url") or ["http://localhost:1234"])[0]
        client = LLMClient(backend=backend, base_url=base_url)
        models = client.list_models()
        self._json_response({"success": True, "models": models})

    # ---- 大纲 API ----

    def _handle_plan(self):
        data = self._read_body()
        topic = data.get("topic", "").strip()
        if not topic:
            self._json_response({"success": False, "error": "主题不能为空"}, 400)
            return

        prompt = data.get("prompt", "") or self.config_mgr.get("default_prompt", "")
        session_id = data.get("session_id", "")

        # 获取规划模型配置
        pm = self.config_mgr.get("planner_model", {})
        client = LLMClient(
            backend=pm.get("backend", "lmstudio"),
            base_url=pm.get("base_url", "http://localhost:1234"),
            timeout=pm.get("timeout", 180),
            model=pm.get("model", ""),
            max_tokens=pm.get("max_tokens", 4096)
        )

        try:
            outline = plan_outline(topic, prompt=prompt, llm_client=client)
        except (ValueError, LLMClientError) as e:
            self._json_response({"success": False, "error": str(e)}, 500)
            return

        # 保存到状态
        sm = StateManager(session_id) if session_id else StateManager()
        sm.init_session(self.config_mgr.get_all())
        sm.set_outline(outline)

        self._json_response({
            "success": True,
            "outline": outline,
            "session_id": sm.session_id
        })

    # ---- 生成 API（异步后台） ----

    def _handle_generate(self):
        data = self._read_body()
        session_id = data.get("session_id", "")
        if not session_id:
            self._json_response({"success": False, "error": "缺少 session_id"}, 400)
            return

        # 检查是否已存在正在进行的生成任务
        with _gen_lock:
            if session_id in _generation_tasks:
                existing = _generation_tasks[session_id]
                if not existing["done"]:
                    self._json_response({"success": False, "error": "该会话正在生成中"}, 409)
                    return

        try:
            sm = StateManager()
            sm.load(session_id)
        except FileNotFoundError:
            self._json_response({"success": False, "error": "会话不存在"}, 404)
            return

        state = sm.get_state()
        outline = state.get("outline", {})
        user_orders = data.get("orders", {}) or state.get("user_orders", {})
        rag_options = data.get("rag", {})

        # 应用用户的重点覆盖
        key_sections = data.get("key_sections", {})
        if key_sections:
            for s in outline.get("sections", []):
                if s["id"] in key_sections:
                    s["is_key"] = key_sections[s["id"]]

        # 应用勾选状态：过滤掉未选中的节和子结构
        checked = data.get("checked", {})
        if checked:
            sections = outline.get("sections", [])
            # 从后往前删，避免索引问题
            for i in range(len(sections) - 1, -1, -1):
                s = sections[i]
                sec_checked = checked.get(s["id"], True)
                if not sec_checked:
                    sections.pop(i)
                    continue
                # 过滤子结构
                subs = s.get("sub_sections", [])
                s["sub_sections"] = [ss for ss in subs if checked.get(ss["id"], True)]

        # 应用子结构排序
        sub_orders = data.get("sub_orders", {})
        if sub_orders:
            roman_to_int = {"i":1,"ii":2,"iii":3,"iv":4,"v":5,"vi":6,"vii":7,"viii":8,"ix":9,"x":10}
            for s in outline.get("sections", []):
                subs = s.get("sub_sections", [])
                def sub_sort_key(ss):
                    ro = sub_orders.get(ss["id"], "")
                    return roman_to_int.get(ro, 999)
                subs.sort(key=sub_sort_key)

        # 保存用户排序
        if user_orders:
            sm.set_user_orders(user_orders)

        # 获取写作模型配置
        wm = self.config_mgr.get("writer_model", {})
        client = LLMClient(
            backend=wm.get("backend", "lmstudio"),
            base_url=wm.get("base_url", "http://localhost:1234"),
            timeout=wm.get("timeout", 300),
            model=wm.get("model", ""),
            max_tokens=wm.get("max_tokens", 8192)
        )

        # 如果 8767 在线，创建 RAG 客户端
        rag_client = None
        try:
            probe = self._probe_rag_8767()
            if probe["online"]:
                from .rag_client import RAGClient
                rag_client = RAGClient()
        except Exception:
            pass

        # 在后台线程中运行生成
        def _run_generation(sid, outline, orders, rag_opt, llm_cli):
            result = {"done": True, "success": False, "output_file": "",
                      "content": "", "word_count": 0, "error": ""}
            try:
                local_sm = StateManager()
                local_sm.load(sid)
                md_content, output_path = generate_article(
                    outline=outline,
                    user_orders=orders,
                    rag_options=rag_opt,
                    llm_client=llm_cli,
                    state_mgr=local_sm,
                    rag_client=rag_client
                )
                result["success"] = True
                result["output_file"] = output_path
                result["content"] = md_content[:2000] + ("..." if len(md_content) > 2000 else "")
                result["word_count"] = len(md_content.replace(" ", "").replace("\n", ""))
            except Exception as e:
                result["error"] = f"{type(e).__name__}: {e}"
                traceback.print_exc()
                # 更新状态为错误
                try:
                    local_sm = StateManager()
                    local_sm.load(sid)
                    local_sm.set_phase("error")
                except Exception:
                    pass
            finally:
                with _gen_lock:
                    if sid in _generation_tasks:
                        _generation_tasks[sid].update(result)
                        _generation_tasks[sid]["done"] = True

        thread = threading.Thread(
            target=_run_generation,
            args=(session_id, outline, user_orders, rag_options, client),
            daemon=True
        )
        with _gen_lock:
            _generation_tasks[session_id] = {
                "thread": thread, "done": False,
                "success": None, "output_file": "",
                "content": "", "word_count": 0, "error": ""
            }
        thread.start()

        self._json_response({
            "success": True,
            "task_id": session_id,
            "message": "生成任务已启动"
        })

    # ---- 获取生成结果（轮询后拉取） ----

    def _handle_get_result(self):
        params = urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query
        )
        session_id = (params.get("session_id") or [""])[0]
        if not session_id:
            self._json_response({"success": False, "error": "缺少 session_id"}, 400)
            return
        with _gen_lock:
            task = _generation_tasks.get(session_id)
            if task is None:
                self._json_response({"success": False, "error": "没有生成任务"}, 404)
                return
            if not task["done"]:
                self._json_response({"success": False, "error": "生成中", "done": False}, 200)
                return
            # 任务完成，清除任务记录
            result = {
                "success": task.get("success", False),
                "output_file": task.get("output_file", ""),
                "content": task.get("content", ""),
                "word_count": task.get("word_count", 0),
                "error": task.get("error", ""),
                "done": True
            }
            del _generation_tasks[session_id]
        self._json_response(result)

    # ---- 进度 API ----

    def _handle_get_progress(self):
        params = urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query
        )
        session_id = (params.get("session_id") or [""])[0]
        if not session_id:
            self._json_response({"success": False, "error": "缺少 session_id"}, 400)
            return
        try:
            sm = StateManager()
            sm.load(session_id)
            progress = sm.get_progress()
            self._json_response({"success": True, "progress": progress})
        except FileNotFoundError:
            self._json_response({"success": False, "error": "会话不存在"}, 404)

    # ---- 会话 API ----

    def _handle_new_session(self):
        sm = StateManager()
        sm.init_session(self.config_mgr.get_all())
        self._json_response({
            "success": True,
            "session_id": sm.session_id
        })

    def _handle_list_sessions(self):
        sm = StateManager()
        sessions = sm.list_sessions()
        self._json_response({"success": True, "sessions": sessions})

    # ---- 会话恢复（断线重连） ----

    def _handle_session_load(self):
        params = urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query
        )
        session_id = (params.get("session_id") or [""])[0]
        if not session_id:
            self._json_response({"success": False, "error": "缺少 session_id"}, 400)
            return
        try:
            sm = StateManager()
            sm.load(session_id)
            state = sm.get_state()
            progress = sm.get_progress()
            self._json_response({
                "success": True,
                "session": {
                    "session_id": state["session_id"],
                    "phase": state.get("phase", ""),
                    "outline": state.get("outline", {}),
                    "user_orders": state.get("user_orders", {}),
                    "output_file": state.get("output_file", ""),
                    "created_at": state.get("created_at", "")
                },
                "progress": progress
            })
        except FileNotFoundError:
            self._json_response({"success": False, "error": "会话不存在"}, 404)

    # ---- RAG 状态探测 ----

    @classmethod
    def _probe_rag_8767(cls) -> dict:
        """探测 :8767 是否在线，返回 (status, kbs)"""
        RAG_PORT = 8767
        try:
            req = urllib.request.Request(f"http://localhost:{RAG_PORT}/api/health")
            with urllib.request.urlopen(req, timeout=3) as resp:
                health = json.loads(resp.read().decode("utf-8"))
            # 获取 KB 列表（API 返回 {kbs: {name: {...}}, stats: {...}}）
            kbs = []
            try:
                req2 = urllib.request.Request(f"http://localhost:{RAG_PORT}/api/kb/list")
                with urllib.request.urlopen(req2, timeout=3) as resp2:
                    kb_data = json.loads(resp2.read().decode("utf-8"))
                    kbs_raw = kb_data.get("kbs", kb_data.get("data", []))
                    if isinstance(kbs_raw, dict):
                        kbs = list(kbs_raw.keys())  # dict → KB 名称列表
                    elif isinstance(kbs_raw, list):
                        kbs = [k if isinstance(k, str) else k.get("name", "") for k in kbs_raw]
                    else:
                        kbs = []
            except Exception:
                pass
            return {"online": True, "health": health, "kbs": kbs}
        except Exception:
            return {"online": False, "health": None, "kbs": []}

    def _handle_rag_status(self):
        result = self._probe_rag_8767()
        # 检查本地子进程状态
        with _rag_lock:
            proc_alive = False
            if _rag_process is not None:
                proc_alive = _rag_process.poll() is None
        result["local_process"] = proc_alive
        result["starting"] = _rag_starting
        result["stderr"] = _rag_process_stderr[:500] if _rag_process_stderr else ""
        self._json_response({"success": True, **result})

    # ---- RAG 冷启动（异步） ----

    def _handle_rag_start(self):
        global _rag_starting
        data = self._read_body()
        path = data.get("path", "").strip()
        if not path or not os.path.isdir(path):
            self._json_response({"success": False, "error": "路径无效或不存在"}, 400)
            return

        # 先检查是否已经在线
        probe = self._probe_rag_8767()
        if probe["online"]:
            self._json_response({"success": False, "error": "8767 已在运行，无需启动"}, 400)
            return

        # 检查是否正在启动中
        with _rag_lock:
            if _rag_starting:
                self._json_response({"success": False, "error": "正在启动中，请稍候"}, 400)
                return
            _rag_starting = True

        main_py = os.path.join(path, "main.py")
        if not os.path.isfile(main_py):
            with _rag_lock:
                _rag_starting = False
            self._json_response({"success": False, "error": f"路径下未找到 main.py: {main_py}"}, 400)
            return

        try:
            # 用临时文件接 stderr，避免 pipe 缓冲区满卡死子进程
            stderr_tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix='.log', prefix='rag_', mode='w', encoding='utf-8'
            )
            stderr_path = stderr_tmp.name
            # 强制子进程使用 UTF-8 输出（防止 emoji/中文在 GBK 下报错）
            rag_env = os.environ.copy()
            rag_env["PYTHONIOENCODING"] = "utf-8"
            proc = subprocess.Popen(
                [sys.executable, main_py, "--port", "18765", "--api-port", "8767"],
                cwd=path,
                env=rag_env,
                stdout=subprocess.DEVNULL,
                stderr=stderr_tmp
            )
            stderr_tmp.close()
            with _rag_lock:
                global _rag_process, _rag_process_stderr
                _rag_process = proc
                _rag_process_stderr = ""

            # 后台线程轮询等待就绪
            def _poll_rag_ready():
                global _rag_starting, _rag_process_stderr
                stderr_path_local = stderr_path
                try:
                    for _ in range(45):
                        time.sleep(2)
                        p = self._probe_rag_8767()
                        if p["online"]:
                            return
                        # 检查子进程是否还活着
                        if proc.poll() is not None:
                            # 进程挂了！读临时文件找 Traceback
                            err = ""
                            try:
                                with open(stderr_path_local, "r", encoding="utf-8", errors="replace") as ef:
                                    full = ef.read()
                                # 找 Traceback 或最后的 Python 异常
                                idx = full.rfind("Traceback (most recent call last)")
                                if idx >= 0:
                                    err = full[idx:][:2000]
                                else:
                                    err = full[-2000:]
                            except Exception:
                                err = "(无法读取输出)"
                            with _rag_lock:
                                _rag_process_stderr = err
                            return
                finally:
                    with _rag_lock:
                        _rag_starting = False
                    # 清理临时文件
                    try:
                        os.unlink(stderr_path_local)
                    except Exception:
                        pass

            t = threading.Thread(target=_poll_rag_ready, daemon=True)
            t.start()

            self._json_response({
                "success": True,
                "message": "RAG 启动中，请稍候..."
            })
        except Exception as e:
            with _rag_lock:
                _rag_starting = False
            self._json_response({"success": False, "error": f"启动失败: {e}"})

    # ---- 聊天 API (Phase 2 增强) ----

    def _handle_chat(self):
        try:
            data = self._read_body()
        except ValueError as e:
            self._json_response({"success": False, "error": str(e)}, 400)
            return
        message = data.get("message", "").strip()
        if not message:
            self._json_response({"success": False, "error": "消息不能为空"}, 400)
            return
        # Phase 1 基础版：简单回显 + 尝试规划
        # 检测是否是写作请求
        if any(kw in message for kw in ["写", "生成", "创作", "撰写", "起草"]):
            self._json_response({
                "success": True,
                "type": "writing_request",
                "text": "请确认：是否需要为此主题生成大纲？点击下方按钮开始规划。\n\n主题：" + message,
                "topic": message
            })
        else:
            self._json_response({
                "success": True,
                "type": "chat",
                "text": f"已收到消息。如需撰写结构化文章，请直接说明主题和写作要求。\n\n您说：{message[:100]}"
            })

    def log_message(self, format, *args):
        """抑制默认日志输出"""
        pass


# ============================================================
# 内联 HTML 页面
# ============================================================

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Structured Writer · 结构化写作</title>
<style>
:root {
  --bg: #1a1a2e;
  --bg-card: #16213e;
  --bg-panel: #0f3460;
  --bg-input: #1a1a3e;
  --text: #e0e0e0;
  --text-dim: #8899aa;
  --accent: #e94560;
  --accent2: #533483;
  --green: #00b894;
  --border: #2a2a4e;
  --radius: 8px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  overflow: hidden;
}

/* 顶栏 */
.topbar {
  height: 48px;
  background: linear-gradient(135deg, var(--accent2), var(--accent));
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 8px;
  flex-shrink: 0;
}
.topbar .logo { font-weight: 700; font-size: 16px; }
.topbar .tag { font-size: 11px; opacity: 0.7; }

/* Tab 导航 */
.tab-bar {
  display: flex;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.tab-btn {
  padding: 10px 24px;
  cursor: pointer;
  color: var(--text-dim);
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  font-size: 14px;
  background: none;
  border-top: none; border-left: none; border-right: none;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

/* 主容器 */
.main-container {
  display: flex;
  height: calc(100vh - 48px - 41px);
  overflow: hidden;
}
.tab-content { display: none; flex: 1; overflow: auto; }
.tab-content.active { display: flex; }

/* ===== 配置 Tab ===== */
.config-panel {
  padding: 24px;
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
  overflow-y: auto;
}
.config-section {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  margin-bottom: 16px;
}
.config-section h3 {
  font-size: 14px;
  color: var(--accent);
  margin-bottom: 12px;
}
.form-row {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.form-row label {
  font-size: 13px;
  min-width: 80px;
  color: var(--text-dim);
}
.form-row input, .form-row select, .form-row textarea {
  flex: 1;
  min-width: 120px;
  padding: 6px 10px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  font-size: 13px;
}
.form-row textarea {
  min-height: 80px;
  resize: vertical;
  font-family: inherit;
}
.form-row input:focus, .form-row select:focus, .form-row textarea:focus {
  outline: none;
  border-color: var(--accent);
}
.btn {
  padding: 6px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: opacity 0.2s;
}
.btn:hover { opacity: 0.85; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-secondary { background: var(--bg-panel); color: var(--text); border: 1px solid var(--border); }
.btn-success { background: var(--green); color: #fff; }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.status-msg {
  font-size: 12px;
  padding: 4px 0;
  color: var(--text-dim);
}
.status-msg.success { color: var(--green); }
.status-msg.error { color: var(--accent); }

/* ===== 对话 Tab ===== */
.chat-container {
  display: flex;
  flex: 1;
  height: 100%;
}
.chat-sidebar {
  width: 220px;
  background: var(--bg-card);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.chat-sidebar .sidebar-header {
  padding: 12px;
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 8px;
}
.chat-sidebar .sidebar-header button {
  flex: 1;
}
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}
.session-item {
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  border-left: 3px solid transparent;
  transition: all 0.15s;
}
.session-item:hover { background: rgba(255,255,255,0.05); }
.session-item.active {
  background: rgba(233, 69, 96, 0.1);
  border-left-color: var(--accent);
}
.session-item .s-title { color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.session-item .s-meta { font-size: 11px; color: var(--text-dim); margin-top: 2px; }

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.msg {
  margin-bottom: 16px;
  max-width: 85%;
}
.msg.user {
  margin-left: auto;
}
.msg-content {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}
.msg.user .msg-content {
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg.assistant .msg-content {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}
.msg-label {
  font-size: 11px;
  color: var(--text-dim);
  margin-bottom: 4px;
  padding: 0 4px;
}
.chat-input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  background: var(--bg-card);
  display: flex;
  gap: 8px;
}
.chat-input-area textarea {
  flex: 1;
  padding: 8px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 14px;
  resize: none;
  min-height: 40px;
  max-height: 120px;
  font-family: inherit;
}
.chat-input-area textarea:focus { outline: none; border-color: var(--accent); }
.chat-input-area button {
  padding: 8px 20px;
  align-self: flex-end;
}

/* 交互大纲卡片 */
.outline-card {
  background: var(--bg-card);
  border: 1px solid var(--accent);
  border-radius: var(--radius);
  padding: 16px;
  margin: 8px 0;
}
.outline-card .oc-title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--accent);
}
.section-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.section-card .sc-label {
  font-weight: 600;
  font-size: 13px;
  flex: 1;
  min-width: 120px;
}
.section-card .sc-meta {
  font-size: 12px;
  color: var(--text-dim);
}
.section-card select, .section-card input[type=number] {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  padding: 3px 6px;
  font-size: 12px;
}
.section-card .sc-rag {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}
.section-card .sc-rag input[type=checkbox] { accent-color: var(--accent); }
.section-card .sc-key {
  color: #f39c12;
  font-size: 12px;
}
.outline-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

/* 进度条 */
.progress-bar {
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  margin: 8px 0;
  overflow: hidden;
}
.progress-bar .fill {
  height: 100%;
  background: var(--green);
  transition: width 0.3s;
  border-radius: 2px;
}

/* Markdown 基础样式 */
.msg-content h1, .msg-content h2, .msg-content h3 {
  margin: 8px 0 4px;
}
.msg-content p { margin: 4px 0; }
.msg-content ul, .msg-content ol { padding-left: 20px; }
.msg-content code {
  background: rgba(255,255,255,0.1);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 13px;
}
.msg-content pre code {
  display: block;
  padding: 8px;
  overflow-x: auto;
}
.msg-content a { color: #5dade2; }
</style>
</head>
<body>

<div class="topbar">
  <span class="logo">✎ Structured Writer</span>
  <span class="tag">结构化写作</span>
</div>

<div class="tab-bar">
  <button class="tab-btn active" data-tab="config">配置</button>
  <button class="tab-btn" data-tab="chat">对话</button>
</div>

<div class="main-container">

  <!-- ===== 配置面板 ===== -->
  <div class="tab-content active" id="tab-config">
    <div class="config-panel">
      <div class="config-section">
        <h3>🔧 规划模型</h3>
        <div class="form-row">
          <label>后端</label>
          <select id="planner-backend"><option value="lmstudio" selected>LM Studio</option><option value="ollama">Ollama</option></select>
        </div>
        <div class="form-row">
          <label>地址</label>
          <input type="text" id="planner-base-url" value="http://localhost:1234">
        </div>
        <div class="form-row">
          <label>模型</label>
          <select id="planner-model" style="flex:2"><option value="">(请选择)</option></select>
          <button class="btn btn-secondary btn-sm" onclick="refreshModels('planner')">刷新</button>
        </div>
        <div class="form-row">
          <label>超时(s)</label>
          <input type="number" id="planner-timeout" value="180" style="width:100px;">
          <label>最大Token</label>
          <input type="number" id="planner-max-tokens" value="4096" style="width:120px;">
        </div>
        <div class="form-row" style="font-size:11px;color:var(--text-dim)">
          <span></span>
          <span>推理模型建议不低于 4096，长文建议 8192 以上</span>
        </div>
      </div>

      <div class="config-section">
        <h3>✍️ 写作模型</h3>
        <div class="form-row">
          <label>后端</label>
          <select id="writer-backend"><option value="lmstudio" selected>LM Studio</option><option value="ollama">Ollama</option></select>
        </div>
        <div class="form-row">
          <label>地址</label>
          <input type="text" id="writer-base-url" value="http://localhost:1234">
        </div>
        <div class="form-row">
          <label>模型</label>
          <select id="writer-model" style="flex:2"><option value="">(请选择)</option></select>
          <button class="btn btn-secondary btn-sm" onclick="refreshModels('writer')">刷新</button>
        </div>
        <div class="form-row">
          <label>超时(s)</label>
          <input type="number" id="writer-timeout" value="300" style="width:100px;">
          <label>最大Token</label>
          <input type="number" id="writer-max-tokens" value="8192" style="width:120px;">
        </div>
        <div class="form-row" style="font-size:11px;color:var(--text-dim)">
          <span></span>
          <span>推理模型建议不低于 4096，长文建议 8192 以上</span>
        </div>
      </div>

      <div class="config-section">
        <h3>📝 写作提示词模板</h3>
        <div class="form-row">
          <label>模板</label>
          <select id="template-select" style="flex:1" onchange="onTemplateChange()">
            <option value="通用公文">通用公文</option>
            <option value="新闻报道">新闻报道</option>
            <option value="论文综述">论文综述</option>
            <option value="技术报告">技术报告</option>
            <option value="自定义">自定义</option>
          </select>
        </div>
        <div class="form-row">
          <textarea id="template-content" rows="4"></textarea>
        </div>
        <div class="form-row" style="font-size:12px;color:var(--text-dim)">
          提示：切换模板后可在编辑框中修改。规划时将使用当前选中模板的内容指导大纲生成和写作。
        </div>
      </div>

      <div class="config-section">
        <h3>🔗 RAG 知识库</h3>
        <div class="form-row">
          <label>RAG 路径</label>
          <input type="text" id="rag-path" value="" placeholder="C:\Users\sm001\WorkBuddy\rag-assistant" style="flex:2">
          <button class="btn btn-secondary btn-sm" onclick="saveRagPath()">保存路径</button>
        </div>
        <div class="form-row">
          <label>状态</label>
          <span id="rag-status-indicator" style="font-weight:600">检测中...</span>
        </div>
        <div class="form-row">
          <label>操作</label>
          <button class="btn btn-success" id="rag-start-btn" onclick="startRag()" disabled>启动 RAG</button>
          <button class="btn btn-secondary btn-sm" onclick="checkRagStatus()">刷新状态</button>
        </div>
        <div class="form-row" id="rag-kb-row" style="display:none">
          <label>可用知识库</label>
          <span id="rag-kb-list" style="font-size:13px;color:var(--text-dim)"></span>
        </div>
      </div>

      <div class="form-row">
        <button class="btn btn-success" onclick="testConnection()">测试连接</button>
        <button class="btn btn-primary" onclick="saveConfig()">保存配置</button>
        <span id="config-status" class="status-msg"></span>
      </div>
    </div>
  </div>

  <!-- ===== 对话面板 ===== -->
  <div class="tab-content" id="tab-chat">
    <div class="chat-container">
      <div class="chat-sidebar">
        <div class="sidebar-header">
          <button class="btn btn-sm btn-primary" onclick="newSession()">新建</button>
        </div>
        <div class="session-list" id="session-list"></div>
      </div>
      <div class="chat-main">
        <div class="chat-messages" id="chat-messages">
          <div class="msg assistant">
            <div class="msg-label">助手</div>
            <div class="msg-content">欢迎使用结构化写作助手。请在下方输入写作主题，我将为您生成大纲并协助完成文章。</div>
          </div>
        </div>
        <div class="chat-input-area">
          <textarea id="chat-input" placeholder="输入写作主题..." rows="2"
            onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage()}"></textarea>
          <button class="btn btn-primary" onclick="sendMessage()">发送</button>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
// ===== 全局状态 =====
let currentSessionId = '';
let currentOutline = null;
let isGenerating = false;
let ragOnline = false;
let ragKbs = [];

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', () => {
  loadConfig();
  loadSessions();
  checkRagStatus();

  // Tab 切换
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
  });

  // 后端切换触发模型刷新
  document.getElementById('planner-backend').addEventListener('change', () => refreshModels('planner'));
  document.getElementById('writer-backend').addEventListener('change', () => refreshModels('writer'));
});

// ===== 配置操作 =====
function loadConfig() {
  fetch('/api/config').then(r => r.json()).then(data => {
    if (!data.success) return;
    const c = data.config;
    const pm = c.planner_model || {};
    const wm = c.writer_model || {};
    document.getElementById('planner-backend').value = pm.backend || 'lmstudio';
    document.getElementById('planner-base-url').value = pm.base_url || 'http://localhost:1234';
    document.getElementById('planner-timeout').value = pm.timeout || 180;
    document.getElementById('planner-max-tokens').value = pm.max_tokens || 4096;
    document.getElementById('writer-backend').value = wm.backend || 'lmstudio';
    document.getElementById('writer-base-url').value = wm.base_url || 'http://localhost:1234';
    document.getElementById('writer-timeout').value = wm.timeout || 300;
    document.getElementById('writer-max-tokens').value = wm.max_tokens || 8192;
    // 加载模板
    const templates = c.templates || {};
    const selectedTemplate = c.selected_template || '通用公文';
    const sel = document.getElementById('template-select');
    // 更新下拉选项（保留已有选项，确保与 config 一致）
    const tmplNames = Object.keys(templates);
    if (tmplNames.length) {
      sel.innerHTML = tmplNames.map(t => `<option value="${t}">${t}</option>`).join('');
    }
    sel.value = selectedTemplate;
    document.getElementById('template-content').value = templates[selectedTemplate] || '';
    // 加载 RAG 路径
    if (c.rag_path) document.getElementById('rag-path').value = c.rag_path;
    if (pm.model) document.getElementById('planner-model').value = pm.model;
    if (wm.model) document.getElementById('writer-model').value = wm.model;
    refreshModels('planner');
    refreshModels('writer');
  });
}

function saveConfig() {
  const data = {
    planner_model: {
      backend: document.getElementById('planner-backend').value,
      base_url: document.getElementById('planner-base-url').value,
      model: document.getElementById('planner-model').value,
      timeout: parseInt(document.getElementById('planner-timeout').value) || 180,
      max_tokens: parseInt(document.getElementById('planner-max-tokens').value) || 4096
    },
    writer_model: {
      backend: document.getElementById('writer-backend').value,
      base_url: document.getElementById('writer-base-url').value,
      model: document.getElementById('writer-model').value,
      timeout: parseInt(document.getElementById('writer-timeout').value) || 300,
      max_tokens: parseInt(document.getElementById('writer-max-tokens').value) || 8192
    },
    selected_template: document.getElementById('template-select').value,
    templates: {}  // 在下面通过 templData 更新
  };
  // 先读取当前所有模板，更新当前选中模板的内容
  fetch('/api/config').then(r => r.json()).then(cfg => {
    if (!cfg.success) return;
    const templates = Object.assign({}, cfg.config.templates || {});
    const selTmpl = document.getElementById('template-select').value;
    templates[selTmpl] = document.getElementById('template-content').value;
    data.templates = templates;
    data.default_prompt = templates[selTmpl] || '';

    fetch('/api/config', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) })
      .then(r => r.json()).then(d => {
        document.getElementById('config-status').textContent = d.success ? '✓ 已保存' : '✗ 保存失败';
        document.getElementById('config-status').className = 'status-msg ' + (d.success ? 'success' : 'error');
      });
  });
}

// ===== 模板切换 =====
function onTemplateChange() {
  const sel = document.getElementById('template-select');
  const tmplName = sel.value;
  fetch('/api/config').then(r => r.json()).then(d => {
    if (!d.success) return;
    const templates = d.config.templates || {};
    document.getElementById('template-content').value = templates[tmplName] || '';
  });
}

// ===== RAG 状态管理 =====

function onRagToggle(cb, sectionId) {
  // 显示/隐藏 KB 下拉框
  const card = cb.closest('.section-card');
  const kbSelect = card?.querySelector('.sc-kb');
  if (kbSelect) kbSelect.style.display = cb.checked ? '' : 'none';
  collectOutlineData();
}

function checkRagStatus() {
  fetch('/api/rag/status').then(r => r.json()).then(d => {
    const indicator = document.getElementById('rag-status-indicator');
    const btn = document.getElementById('rag-start-btn');
    const kbRow = document.getElementById('rag-kb-row');
    const kbList = document.getElementById('rag-kb-list');

    if (d.online) {
      ragOnline = true;
      ragKbs = Array.isArray(d.kbs) ? d.kbs : [];
      indicator.innerHTML = '<span style="color:#00b894;font-weight:600">RAG 运行中 (port 8767)</span>';
      btn.disabled = true;
      btn.textContent = 'RAG 已运行';
      kbRow.style.display = '';
      kbList.textContent = ragKbs.length ? ragKbs.join('、') : '(无知识库)';
      // 如果之前是在轮询中检测到上线，停止轮询
      if (window._ragPollTimer) {
        clearInterval(window._ragPollTimer);
        window._ragPollTimer = null;
      }
    } else if (d.starting) {
      ragOnline = false;
      indicator.innerHTML = '<span style="color:#f39c12;font-weight:600">RAG 启动中...</span>';
      btn.disabled = true;
      btn.textContent = '启动中...';
      kbRow.style.display = 'none';
    } else if (d.stderr) {
      // 子进程挂了，显示错误
      ragOnline = false;
      indicator.innerHTML = '<span style="color:#e94560;font-weight:600">RAG 启动失败</span>';
      btn.disabled = false;
      btn.textContent = '冷启动 RAG';
      kbRow.style.display = 'none';
      document.getElementById('config-status').textContent = '子进程错误: ' + d.stderr.substring(0, 1000);
      document.getElementById('config-status').className = 'status-msg error';
    } else {
      ragOnline = false;
      ragKbs = [];
      indicator.innerHTML = '<span style="color:#e94560;font-weight:600">RAG 离线</span>';
      btn.disabled = false;
      btn.textContent = '冷启动 RAG';
      kbRow.style.display = 'none';
    }
  }).catch(() => {
    document.getElementById('rag-status-indicator').innerHTML = '<span style="color:#e94560">RAG 检测失败</span>';
  });
}

function saveRagPath() {
  const path = document.getElementById('rag-path').value.trim();
  fetch('/api/config', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({rag_path: path})
  }).then(r => r.json()).then(d => {
    document.getElementById('config-status').textContent = d.success ? '✓ RAG 路径已保存' : '✗ 保存失败';
    document.getElementById('config-status').className = 'status-msg ' + (d.success ? 'success' : 'error');
  });
}

function startRag() {
  const path = document.getElementById('rag-path').value.trim();
  if (!path) {
    document.getElementById('config-status').textContent = '请先填写 RAG 路径';
    document.getElementById('config-status').className = 'status-msg error';
    return;
  }
  const btn = document.getElementById('rag-start-btn');
  btn.disabled = true;
  btn.textContent = '启动中...';
  document.getElementById('rag-status-indicator').innerHTML = '<span style="color:#f39c12;font-weight:600">RAG 启动中...</span>';

  fetch('/api/rag/start', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({path: path})
  }).then(r => r.json()).then(d => {
    if (d.success) {
      document.getElementById('config-status').textContent = '已提交启动请求，等待就绪...';
      document.getElementById('config-status').className = 'status-msg';
      // 启动轮询检测上线
      if (window._ragPollTimer) clearInterval(window._ragPollTimer);
      window._ragPollTimer = setInterval(checkRagStatus, 3000);
    } else {
      document.getElementById('config-status').textContent = d.error || '启动失败';
      document.getElementById('config-status').className = 'status-msg error';
      checkRagStatus();
    }
  }).catch(err => {
    document.getElementById('config-status').textContent = '请求失败';
    document.getElementById('config-status').className = 'status-msg error';
    checkRagStatus();
  });
}

function testConnection() {
  const backend = document.getElementById('planner-backend').value;
  const base_url = document.getElementById('planner-base-url').value;
  const el = document.getElementById('config-status');
  el.textContent = '⏳ 测试中...';
  el.className = 'status-msg';
  fetch(`/api/llm/test?backend=${encodeURIComponent(backend)}&base_url=${encodeURIComponent(base_url)}`)
    .then(r => r.json()).then(d => {
      el.textContent = d.success ? '✓ ' + d.message : '✗ ' + d.message;
      el.className = 'status-msg ' + (d.success ? 'success' : 'error');
    });
}

function refreshModels(prefix) {
  const backend = document.getElementById(prefix + '-backend').value;
  const base_url = document.getElementById(prefix + '-base-url').value;
  const sel = document.getElementById(prefix + '-model');
  const currentVal = sel.value;
  sel.innerHTML = '<option value="">(加载中...)</option>';
  sel.disabled = true;
  fetch(`/api/llm/models?backend=${encodeURIComponent(backend)}&base_url=${encodeURIComponent(base_url)}`)
    .then(r => r.json()).then(d => {
      sel.innerHTML = '<option value="">(请选择)</option>';
      if (d.success && d.models) {
        d.models.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m;
          opt.textContent = m;
          sel.appendChild(opt);
        });
      }
      if (currentVal) sel.value = currentVal;
      sel.disabled = false;
    }).catch(() => {
      sel.innerHTML = '<option value="">(获取失败)</option>';
      sel.disabled = false;
    });
}

// ===== 会话操作 =====
function loadSessions() {
  fetch('/api/sessions').then(r => r.json()).then(d => {
    if (!d.success) return;
    const list = document.getElementById('session-list');
    list.innerHTML = '';
    (d.sessions || []).forEach(s => {
      const item = document.createElement('div');
      item.className = 'session-item' + (s.id === currentSessionId ? ' active' : '');
      item.innerHTML = `<div class="s-title">${s.title || '未命名'}</div><div class="s-meta">${s.phase} · ${s.created_at?.slice(0,10) || ''}</div>`;
      item.onclick = () => loadSession(s.id);
      list.appendChild(item);
    });
  });
}

function newSession() {
  fetch('/api/session/new', { method: 'POST' }).then(r => r.json()).then(d => {
    if (d.success) {
      currentSessionId = d.session_id;
      currentOutline = null;
      const msgs = document.getElementById('chat-messages');
      msgs.innerHTML = `<div class="msg assistant"><div class="msg-label">助手</div><div class="msg-content">已创建新会话。请输入写作主题开始。</div></div>`;
      msgs.scrollTop = msgs.scrollHeight;
      loadSessions();
    }
  });
}

function loadSession(sid) {
  currentSessionId = sid;
  currentOutline = null;
  // 清除旧消息，切换到该会话
  document.getElementById('chat-messages').innerHTML = '';
  loadSessions();

  // 加载会话状态，恢复大纲
  fetch(`/api/session/load?session_id=${sid}`)
    .then(r => r.json()).then(d => {
      if (!d.success) {
        addAssistantMsg('会话 ' + sid + ' 加载失败');
        return;
      }
      const s = d.session;
      const p = d.progress;
      currentOutline = s.outline;

      if (s.phase === 'done' || s.phase === 'error') {
        // 已完成的会话
        let msg = '恢复会话：' + (s.outline?.title || '未命名') + '\n';
        msg += '状态：' + (s.phase === 'done' ? '已完成' : '失败') + '\n';
        msg += '进度：' + p.done + '/' + p.total + ' 节，' + p.total_words + ' 字\n';
        if (s.output_file) {
          msg += '\n输出文件：' + (s.output_file.split('/').pop() || s.output_file.split('\\').pop());
        }
        addAssistantMsg(msg);
        if (s.outline?.sections?.length) {
          renderOutline(s.outline, true);
        }
      } else if (s.phase === 'writing') {
        let msg = '恢复写作中的会话：' + (s.outline?.title || '未命名') + '\n';
        msg += '进度：' + p.done + '/' + p.total + ' 节已完成';
        addAssistantMsg(msg);
        if (s.outline?.sections?.length) {
          renderOutline(s.outline, true);
        }
        startProgressPolling(sid);
      } else if (s.phase === 'reviewing') {
        addAssistantMsg('恢复会话：大纲已准备，请确认或修改后开始生成');
        if (s.outline?.sections?.length) {
          renderOutline(s.outline);
        }
      } else {
        addAssistantMsg('已切换到会话 ' + sid);
      }
    });
}

// ===== 消息处理 =====
function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';

  addUserMsg(text);

  // 检查是否是大纲规划请求
  const isWritingReq = /写|生成|创作|撰写|起草/.test(text);
  if (isWritingReq) {
    startPlanning(text);
  } else {
    fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({message: text, session_id: currentSessionId})
    }).then(r => r.json()).then(d => {
      if (d.type === 'writing_request') {
        addOutlineProposal(d.topic, d.text);
      } else {
        addAssistantMsg(d.text || '(无响应)');
      }
    });
  }
}

function startPlanning(topic) {
  const statusEl = addAssistantMsg('⏳ 正在生成大纲...');
  // 使用当前选中模板的内容作为 prompt
  const promptText = document.getElementById('template-content')?.value || '';
  fetch('/api/plan', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      topic: topic,
      session_id: currentSessionId,
      prompt: promptText
    })
  }).then(r => r.json()).then(d => {
    // 移除状态消息
    statusEl.remove();
    if (d.success) {
      currentSessionId = d.session_id;
      currentOutline = d.outline;
      renderOutline(d.outline);
      loadSessions();
    } else {
      addAssistantMsg('❌ 大纲生成失败：' + (d.error || '未知错误'));
    }
  }).catch(err => {
    statusEl.remove();
    addAssistantMsg('❌ 请求失败：' + err.message);
  });
}

// ===== 罗马数字转换 =====
function toRoman(n) {
  return ['i','ii','iii','iv','v','vi','vii','viii','ix','x'][n-1] || String(n);
}

// ===== 交互式大纲渲染 =====
function renderOutline(outline, readOnly) {
  readOnly = readOnly || false;
  const html = buildOutlineHTML(outline, readOnly);
  addAssistantMsg(html);
}

function buildOutlineHTML(outline, readOnly) {
  const sections = outline.sections || [];
  let secHTML = '';
  sections.forEach((s, i) => {
    const orderOpts = ['', ...Array.from({length: sections.length}, (_, i) => String(i+1))]
      .map(v => `<option value="${v}" ${i===0 && v==='' ? 'selected' : ''}>${v || '自动'}</option>`).join('');
    const statusIcon = s.status === 'done' ? '✅' : (s.status === 'in_progress' ? '⏳' : '');

    // 子结构行
    const subs = s.sub_sections || [];
    const subCount = subs.length;
    let subHTML = '';
    subs.forEach(ss => {
      const romOpts = ['', ...Array.from({length: subCount}, (_, i) => toRoman(i+1))]
        .map(v => `<option value="${v}" ${ss.id.endsWith('_1') && v==='' ? 'selected' : ''}>${v || '自动'}</option>`).join('');
      subHTML += `
        <div class="sub-card" data-sid="${ss.id}" style="margin-left:24px;padding:4px 8px;border-left:2px solid var(--border);margin-bottom:4px;">
          <div style="display:flex;align-items:center;gap:8px;">
            ${readOnly ? '' : `<input type="checkbox" class="sc-sub-cb" ${ss._checked !== false ? 'checked' : ''} onchange="onSubToggle(this, '${s.id}')">`}
            ${readOnly ? '' : `<select class="sc-sub-order" style="width:48px;font-size:11px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);padding:2px" onchange="collectOutlineData()">${romOpts}</select>`}
            <span style="font-size:13px;flex:1;color:var(--text-dim)">${ss.title}</span>
            <span style="font-size:11px;color:var(--text-dim)">${ss.word_count || ''}字</span>
            ${ss.status === 'done' ? '<span style="font-size:11px;color:var(--green)">✓</span>' : ''}
          </div>
          ${ss.summary ? `<div style="font-size:11px;color:var(--text-dim);margin-left:80px;margin-top:2px;line-height:1.3">${ss.summary}</div>` : ''}
        </div>`;
    });

    secHTML += `
      <div class="section-card" data-sid="${s.id}">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;width:100%">
          ${readOnly ? '' : `<input type="checkbox" class="sc-section-cb" ${s._checked !== false ? 'checked' : ''} onchange="onSectionToggle(this, '${s.id}')" style="flex-shrink:0">`}
          <div class="sc-label" style="flex:1">${s.title}${readOnly ? (s.is_key ? ' <span class="sc-key">⭐重点</span>' : '') : ''} ${statusIcon}</div>
          <div class="sc-meta">${s.subtitle || ''}</div>
          ${readOnly ? `<span style="font-size:12px;color:var(--text-dim)">${s.status === 'done' ? s.actual_word_count + '字' : (s.status === 'in_progress' ? '写作中...' : '')}</span>` : ''}
          ${readOnly ? '' : `<label style="font-size:12px;color:var(--sc-key);cursor:pointer"><input type="checkbox" class="sc-key-cb" ${s.is_key ? 'checked' : ''} onchange="collectOutlineData()"> ⭐重点</label>`}
          ${readOnly ? '' : `<select class="sc-order" onchange="collectOutlineData()">${orderOpts}</select>`}
          ${readOnly ? '' : `<input type="number" class="sc-words" value="${s.word_count}" style="width:70px" min="100" max="5000" onchange="collectOutlineData()">`}
          ${readOnly ? '' : `<label class="sc-rag"><input type="checkbox" class="sc-rag-cb" onchange="onRagToggle(this, '${s.id}')"> RAG</label>` + (ragOnline && Array.isArray(ragKbs) ? `<select class="sc-kb" style="display:none;width:120px;font-size:12px" onchange="collectOutlineData()">${'<option value=\"\">自动KB</option>' + ragKbs.map(k => '<option value=\"' + k + '\">' + k + '</option>').join('')}</select>` : '')}
        </div>
        ${readOnly ? '' : subHTML}
      </div>`;
  });

  let actionsHTML = '';
  if (!readOnly) {
    actionsHTML = `
      <div class="progress-bar" id="progress-bar"><div class="fill" style="width:0%"></div></div>
      <div class="outline-actions">
        <button class="btn btn-primary" onclick="startGeneration()">开始生成</button>
        <button class="btn btn-secondary" onclick="replanOutline()">重新规划</button>
        <div id="rag-status-text" style="font-size:11px;color:var(--text-dim);margin-top:6px"></div>
      </div>`;
  } else {
    const allSubs = sections.flatMap(s => s.sub_sections || []);
    const doneSubs = allSubs.filter(ss => ss.status === 'done').length;
    const pct = allSubs.length > 0 ? Math.round(doneSubs / allSubs.length * 100) : 0;
    actionsHTML = `
      <div class="progress-bar"><div class="fill" style="width:${pct}%"></div></div>
      <div style="font-size:12px;color:var(--text-dim);margin-top:4px">${doneSubs}/${allSubs.length} 子结构已完成</div>`;
  }

  return `<div class="outline-card" id="outline-card">
    <div class="oc-title" style="display:flex;align-items:center;gap:8px">
      <span>大纲：${outline.title}</span>
      <span style="font-size:11px;color:var(--text-dim);font-weight:normal">☑ 勾选 = 写入，取消 = 跳过</span>
    </div>
    ${secHTML}
    ${actionsHTML}
  </div>`;
}

function collectOutlineData() {
  // 收集用户操作数据（用于生成时提交）
  return true;
}

// ===== 大纲勾选/取消 =====
function onSectionToggle(cb, sectionId) {
  const card = cb.closest('.section-card');
  const checked = cb.checked;
  // 同步所有子结构 checkbox
  card.querySelectorAll('.sc-sub-cb').forEach(subCb => {
    subCb.checked = checked;
  });
  collectOutlineData();
}

function onSubToggle(cb, sectionId) {
  // 子结构取消不影响节
  collectOutlineData();
}

function getOutlineData() {
  const card = document.getElementById('outline-card');
  if (!card) return null;
  const orders = {};
  const rag = {};
  const keySections = {};
  const checked = {};  // {sectionId: bool, subId: bool}
  const subOrders = {}; // {subId: roman_str}
  card.querySelectorAll('.section-card').forEach(sc => {
    const sid = sc.dataset.sid;
    const secCb = sc.querySelector('.sc-section-cb');
    if (secCb) checked[sid] = secCb.checked;

    const orderVal = sc.querySelector('.sc-order')?.value;
    if (orderVal) orders[sid] = parseInt(orderVal);
    const keyChecked = sc.querySelector('.sc-key-cb')?.checked;
    if (keyChecked !== undefined) keySections[sid] = keyChecked;
    const ragChecked = sc.querySelector('.sc-rag-cb')?.checked;
    const kb = sc.querySelector('.sc-kb')?.value || '';
    if (ragChecked) rag[sid] = {enabled: true, kb: kb};

    // 子结构 checkbox + 排序
    sc.querySelectorAll('.sub-card').forEach(sub => {
      const subCb = sub.querySelector('.sc-sub-cb');
      if (subCb) checked[sub.dataset.sid] = subCb.checked;
      const subOrder = sub.querySelector('.sc-sub-order')?.value;
      if (subOrder) subOrders[sub.dataset.sid] = subOrder;
    });
  });
  return {orders, rag, keySections, checked, subOrders};
}

function startGeneration() {
  if (isGenerating) return;
  if (!currentSessionId || !currentOutline) {
    addAssistantMsg('❌ 请先生成大纲');
    return;
  }
  isGenerating = true;

  const data = getOutlineData();
  const msgEl = addAssistantMsg('⏳ 正在启动生成任务...');

  fetch('/api/generate', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      session_id: currentSessionId,
      orders: data?.orders || {},
      rag: data?.rag || {},
      key_sections: data?.keySections || {},
      checked: data?.checked || {},
      sub_orders: data?.subOrders || {}
    })
  }).then(r => r.json()).then(d => {
    if (d.success) {
      msgEl.querySelector('.msg-content').innerHTML = '⏳ 生成任务已启动，正在写作...';
      // 开始轮询进度
      startProgressPolling(currentSessionId);
    } else {
      msgEl.querySelector('.msg-content').innerHTML = '❌ 启动失败：' + (d.error || '未知错误');
      isGenerating = false;
    }
  }).catch(err => {
    msgEl.querySelector('.msg-content').innerHTML = '❌ 请求失败：' + err.message;
    isGenerating = false;
  });
}

function replanOutline() {
  const topic = currentOutline?.title || '';
  if (topic) startPlanning(topic);
}

function showFileContent(filepath) {
  // 简单提示
  addAssistantMsg(`📎 文件已保存至：${filepath}`);
}

function addOutlineProposal(topic, text) {
  addAssistantMsg(text + '\n\n<button class="btn btn-sm btn-primary" onclick="startPlanning(\'' + topic.replace(/'/g, "\\'") + '\')">📋 生成大纲</button>');
}

// ===== UI 辅助 =====
function addUserMsg(text) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg user';
  div.innerHTML = `<div class="msg-label">我</div><div class="msg-content">${escapeHtml(text)}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function addAssistantMsg(html) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg assistant';
  div.innerHTML = `<div class="msg-label">助手</div><div class="msg-content">${html}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

// ===== 轮询进度（实时） =====
let progressInterval = null;

function startProgressPolling(sid) {
  const sessionId = sid || currentSessionId;
  if (!sessionId) return;
  if (progressInterval) clearInterval(progressInterval);

  progressInterval = setInterval(() => {
    fetch(`/api/progress?session_id=${sessionId}`)
      .then(r => r.json()).then(d => {
        if (!d.success) {
          stopProgressPolling();
          return;
        }
        const p = d.progress;

        // 更新进度条
        const fill = document.querySelector('.progress-bar .fill');
        if (fill && p.total > 0) {
          const pct = Math.round(p.done / p.total * 100);
          fill.style.width = Math.min(pct, 100) + '%';
        }

        // 更新状态文本
        const statusEl = document.getElementById('rag-status-text');
        if (statusEl && p.status_text) {
          statusEl.textContent = p.status_text;
        }

        // 更新卡片上的状态图标
        document.querySelectorAll('.section-card').forEach(card => {
          // 状态轮询：重新加载session获取最新状态
        });

        // 检查是否完成
        if (p.phase === 'done' || p.phase === 'error') {
          stopProgressPolling();
          fetchResult(sessionId);
        }
      }).catch(() => {});
  }, 1500);
}

function stopProgressPolling() {
  if (progressInterval) { clearInterval(progressInterval); progressInterval = null; }
}

function fetchResult(sessionId) {
  fetch(`/api/result?session_id=${sessionId}`)
    .then(r => r.json()).then(d => {
      // 重新加载会话以获取最新状态
      fetch(`/api/session/load?session_id=${sessionId}`)
        .then(r2 => r2.json()).then(d2 => {
          if (d2.success) {
            // 刷新大纲卡片状态
            const oldCard = document.getElementById('outline-card');
            if (oldCard) {
              const container = oldCard.closest('.msg');
              if (container) {
                // 用只读模式刷新大纲显示完成状态
                const readOnlyHTML = buildOutlineHTML(d2.session.outline, true);
                container.querySelector('.msg-content').innerHTML = readOnlyHTML;
              }
            }
          }
        });

      // 显示结果
      let resultMsg = '';
      if (d.success) {
        resultMsg = `✅ 写作完成！总字数：${d.word_count || 0} 字`;
        if (d.output_file) {
          const fname = d.output_file.split('/').pop() || d.output_file.split('\\\\').pop();
          resultMsg += `\n📎 文件：${fname}`;
        }
        if (d.content) {
          resultMsg += `\n\n--- 预览 ---\n${d.content}`;
        }
      } else {
        resultMsg = '❌ 写作失败：' + (d.error || '');
      }
      addAssistantMsg(resultMsg);
      isGenerating = false;
      loadSessions();
    });
}
</script>
</body>
</html>"""


def run_server(host="0.0.0.0", port=8770):
    """启动 HTTP 服务器"""
    cfg = ConfigManager()
    StructuredWriterHandler.config_mgr = cfg
    server = http.server.HTTPServer((host, port), StructuredWriterHandler)
    print(f"[Structured Writer] 服务启动: http://{host}:{port}")
    print(f"[Structured Writer] 配置面板: http://localhost:{port} (配置Tab)")
    print(f"[Structured Writer] 写作界面: http://localhost:{port} (对话Tab)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Structured Writer] 服务停止")
        server.server_close()
