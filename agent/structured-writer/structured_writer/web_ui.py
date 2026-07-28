"""Web UI — HTTP 服务器 + 内联 HTML/CSS/JS 界面"""
import json
import os
import sys
import time
import tempfile
import subprocess
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import socketserver
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

# 批量自动撰写任务跟踪
_batch_tasks = {}
_batch_lock = threading.Lock()

# 停止生成标记 {session_id: "delay"|"immediate"}
_stop_flags = {}
_stop_lock = threading.Lock()


class StructuredWriterHandler(BaseHTTPRequestHandler):
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
            "/favicon.ico": cls._handle_favicon,
            "/api/config": cls._handle_get_config,
            "/api/llm/test": cls._handle_llm_test,
            "/api/llm/models": cls._handle_llm_models,
            "/api/progress": cls._handle_get_progress,
            "/api/result": cls._handle_get_result,
            "/api/sessions": cls._handle_list_sessions,
            "/api/session/load": cls._handle_session_load,
            "/api/rag/status": cls._handle_rag_status,
            "/api/batch_progress": cls._handle_batch_progress,
        }
        cls.ROUTES["POST"] = {
            "/api/config": cls._handle_update_config,
            "/api/plan": cls._handle_plan,
            "/api/generate": cls._handle_generate,
            "/api/session/new": cls._handle_new_session,
            "/api/chat": cls._handle_chat,
            "/api/rag/start": cls._handle_rag_start,
            "/api/rag/stop": cls._handle_rag_stop,
            "/api/batch_auto": cls._handle_batch_auto,
            "/api/session/archive": cls._handle_session_archive,
            "/api/session/restore": cls._handle_session_restore,
            "/api/session/delete": cls._handle_session_delete,
            "/api/stop": cls._handle_stop,
            "/api/gen-template": cls._handle_gen_template,
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

    def _handle_favicon(self):
        self.send_response(204)
        self.end_headers()

    # ---- 配置 API ----

    def _handle_get_config(self):
        cfg = self.config_mgr.get_all()
        self._json_response({"success": True, "config": cfg})

    def _handle_update_config(self):
        data = self._read_body()
        self.config_mgr.update(data)
        self._json_response({"success": True})

    # ---- LLM 客户端工厂（统一创建，一处改处处生效） ----

    @classmethod
    def _create_writer_client(cls):
        wm = cls.config_mgr.get("writer_model", {})
        return LLMClient(
            backend=wm.get("backend", "lmstudio"),
            base_url=wm.get("base_url", "http://localhost:1234"),
            timeout=wm.get("timeout", 300),
            model=wm.get("model", ""),
            max_tokens=wm.get("max_tokens", 8192),
            temperature=wm.get("temperature", 0.7)
        )

    @classmethod
    def _create_planner_client(cls):
        pm = cls.config_mgr.get("planner_model", {})
        return LLMClient(
            backend=pm.get("backend", "lmstudio"),
            base_url=pm.get("base_url", "http://localhost:1234"),
            timeout=pm.get("timeout", 180),
            model=pm.get("model", ""),
            max_tokens=pm.get("max_tokens", 4096),
            temperature=pm.get("temperature", 0.6)
        )

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

        # 获取当前选中的模板
        templates = self.config_mgr.get("templates", {})
        selected = data.get("template_name", "") or self.config_mgr.get("selected_template", "")
        template = templates.get(selected, {})

        # 用户已填的字段值（标题、作者等）
        user_meta = data.get("meta", {})
        plan_hints = data.get("plan_hints", "")

        # 获取规划模型配置
        client = self._create_planner_client()

        try:
            # 兼容旧调用：如果有 meta/content 字段就走新方式
            if isinstance(template, dict) and (template.get("meta") is not None or template.get("content") is not None):
                outline = plan_outline(topic, template=template, user_meta=user_meta, llm_client=client, plan_hints=plan_hints)
            elif isinstance(template, dict) and (template.get("meta") or template.get("content") or template.get("structure")):
                outline = plan_outline(topic, template=template, user_meta=user_meta, llm_client=client, plan_hints=plan_hints)
            else:
                style = template if isinstance(template, str) else ""
                outline = plan_outline(topic, template=style or prompt, llm_client=client)
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

        # 重置停止标记和状态文本
        with _stop_lock:
            _stop_flags.pop(session_id, None)
        try:
            sm = StateManager()
            sm.load(session_id)
            sm.set_status_text("")
        except Exception:
            pass

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

        # 应用子结构排序（阿拉伯数字）
        sub_orders = data.get("sub_orders", {})
        if sub_orders:
            for s in outline.get("sections", []):
                subs = s.get("sub_sections", [])
                def sub_sort_key(ss):
                    ro = sub_orders.get(ss["id"], "")
                    try:
                        return int(ro.lstrip("s"))
                    except (ValueError, TypeError):
                        return 999
                subs.sort(key=sub_sort_key)

        # 应用子结构字数覆盖
        sub_words = data.get("sub_words", {})
        if sub_words:
            for s in outline.get("sections", []):
                for ss in s.get("sub_sections", []):
                    if ss["id"] in sub_words:
                        ss["word_count"] = sub_words[ss["id"]]
                # 重新计算章节总字数
                s["word_count"] = sum(ss.get("word_count", 0) for ss in s.get("sub_sections", []))

        # 应用 leaf 节字数覆盖
        sec_words = data.get("sec_words", {})
        if sec_words:
            for s in outline.get("sections", []):
                if s["id"] in sec_words:
                    s["word_count"] = sec_words[s["id"]]

        # 保存用户排序
        if user_orders:
            sm.set_user_orders(user_orders)

        # 保存过滤后的大纲（使进度计算用正确总数）
        sm2 = StateManager()
        sm2.load(session_id)
        sm2._state["outline"] = outline
        sm2.save()

        # 获取写作模型配置
        client = self._create_writer_client()

        # 获取前文回顾字数配置
        context_review_length = self.config_mgr.get("context_review_length", 800)

        # 获取辅助知识
        aux_knowledge = data.get("aux_knowledge", {})

        # 获取事实自检配置
        fact_check_enabled = self.config_mgr.get("fact_check_enabled", False)

        # 获取当前模板（为 meta 渲染提供 structure）
        templates = self.config_mgr.get("templates", {})
        selected = self.config_mgr.get("selected_template", "")
        current_template = templates.get(selected, {})
        if not isinstance(current_template, dict):
            current_template = {}

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
        tmpl = current_template
        def _run_generation(sid, outline, orders, rag_opt, llm_cli, aux_kn, ctx_len, fc_enabled, tmpl):
            result = {"done": True, "success": False, "output_file": "",
                      "content": "", "word_count": 0, "error": ""}
            try:
                local_sm = StateManager()
                local_sm.load(sid)
                # 停止检测函数
                def _stop_check():
                    with _stop_lock:
                        return _stop_flags.get(sid)
                md_content, output_path = generate_article(
                    outline=outline,
                    user_orders=orders,
                    rag_options=rag_opt,
                    llm_client=llm_cli,
                    state_mgr=local_sm,
                    rag_client=rag_client,
                    aux_knowledge=aux_kn,
                    fact_check_enabled=fc_enabled,
                    context_review_length=ctx_len,
                    stop_check=_stop_check,
                    template=tmpl
                )
                result["success"] = True
                result["output_file"] = output_path
                result["content"] = md_content[:8000] + ("...(截断) 完整文件见" + output_path if len(md_content) > 8000 else "")
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
                # 清理停止标记
                with _stop_lock:
                    _stop_flags.pop(sid, None)
                with _gen_lock:
                    if sid in _generation_tasks:
                        _generation_tasks[sid].update(result)
                        _generation_tasks[sid]["done"] = True

        thread = threading.Thread(
            target=_run_generation,
            args=(session_id, outline, user_orders, rag_options, client, aux_knowledge, context_review_length, fact_check_enabled, current_template),
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

    # ---- 停止 API ----

    def _handle_stop(self):
        data = self._read_body()
        session_id = data.get("session_id", "")
        stop_type = data.get("type", "delay")  # "delay" 或 "immediate"
        if not session_id:
            self._json_response({"success": False, "error": "缺少 session_id"}, 400)
            return
        with _stop_lock:
            _stop_flags[session_id] = stop_type
        self._json_response({"success": True, "type": stop_type})

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
        # 自动归档旧会话（如超过 max_sessions）
        max_s = self.config_mgr.get("max_sessions", 20)
        StateManager.check_session_limit(max_s)
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

    # ---- 会话归档/恢复/删除 ----

    def _handle_session_archive(self):
        data = self._read_body()
        sid = data.get("id", "")
        if not sid:
            self._json_response({"success": False, "error": "缺少 id"}, 400)
            return
        ok = StateManager().archive_session(sid)
        self._json_response({"success": ok})

    def _handle_session_restore(self):
        data = self._read_body()
        sid = data.get("id", "")
        if not sid:
            self._json_response({"success": False, "error": "缺少 id"}, 400)
            return
        ok = StateManager().restore_session(sid)
        self._json_response({"success": ok})

    def _handle_session_delete(self):
        data = self._read_body()
        sid = data.get("id", "")
        if not sid:
            self._json_response({"success": False, "error": "缺少 id"}, 400)
            return
        ok = StateManager().delete_session(sid)
        self._json_response({"success": ok})

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

    # ---- RAG 停止 ----

    def _handle_rag_stop(self):
        global _rag_process, _rag_process_stderr
        # 1. 杀子进程
        with _rag_lock:
            if _rag_process is not None:
                try:
                    _rag_process.terminate()
                    _rag_process.wait(timeout=3)
                except Exception:
                    try:
                        _rag_process.kill()
                    except Exception:
                        pass
                _rag_process = None
                _rag_process_stderr = ""
        # 2. 查 8767 端口上的所有 PID，彻底杀光
        import subprocess as _sp
        try:
            r = _sp.run('netstat -ano', capture_output=True, text=True, shell=True, timeout=5)
            for line in r.stdout.splitlines():
                if '8767' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                    parts = line.strip().split()
                    if parts:
                        pid = parts[-1]
                        if pid.isdigit():
                            _sp.run(['taskkill', '/F', '/T', '/PID', pid],
                                    capture_output=True, timeout=5)
        except Exception:
            pass
        # 3. 等端口释放
        import socket, time
        for _ in range(10):
            try:
                s = socket.socket()
                s.settimeout(0.5)
                s.connect(('127.0.0.1', 8767))
                s.close()
                time.sleep(0.5)
            except Exception:
                break
        # 4. 再测一次端口是否还活着（自动重启检测）
        auto_restart = False
        try:
            s = socket.socket()
            s.settimeout(1)
            s.connect(('127.0.0.1', 8767))
            s.close()
            auto_restart = True
        except Exception:
            pass
        if auto_restart:
            self._json_response({
                "success": False,
                "error": "RAG 有自动重启机制（kill 后端口立即复活），请到独立 CMD 窗口手动关闭，或检查系统进程管理器。"
            })
        else:
            self._json_response({"success": True})

    # ---- 批量自动撰写 API ----

    def _handle_batch_auto(self):
        data = self._read_body()
        topics = data.get("topics", [])
        if not topics:
            self._json_response({"success": False, "error": "主题列表为空"}, 400)
            return

        # 从配置获取 prompt 和模板
        prompt_text = data.get("prompt", "") or self.config_mgr.get("default_prompt", "")
        template_name = data.get("template_name", "") or self.config_mgr.get("selected_template", "")
        templates_dict = self.config_mgr.get("templates", {})
        template = templates_dict.get(template_name, {})
        if not isinstance(template, dict):
            template = {}

        import threading as _thr
        task_id = f"batch_{int(time.time())}"

        def _run_batch():
            fc_enabled = self.config_mgr.get("fact_check_enabled", False)
            ctx_len = self.config_mgr.get("context_review_length", 800)

            writer_client = self._create_writer_client()
            planner_client = self._create_planner_client()

            # 检测 RAG
            rag_client = None
            try:
                probe = self._probe_rag_8767()
                if probe["online"]:
                    from .rag_client import RAGClient
                    rag_client = RAGClient()
            except Exception:
                pass

            results = []
            errors = []

            for topic in topics:
                with _batch_lock:
                    if task_id in _batch_tasks:
                        _batch_tasks[task_id]["current_topic"] = topic

                try:
                    # 批量模式下使用当前选中模板
                    if isinstance(template, dict) and (template.get("meta") or template.get("content") or template.get("structure")):
                        outline = plan_outline(topic, template=template, user_meta={}, llm_client=planner_client)
                    else:
                        outline = plan_outline(topic, prompt=prompt_text, llm_client=planner_client)
                    # 全量RAG：所有节+子结构启用
                    rag_opts = {}
                    for s in outline.get("sections", []):
                        if rag_client:
                            rag_opts[s["id"]] = {"enabled": True, "kb": ""}

                    local_sm = StateManager()
                    local_sm.init_session(self.config_mgr.get_all())
                    local_sm.set_outline(outline)
                    sid = local_sm.session_id

                    md_content, output_path = generate_article(
                        outline=outline,
                        user_orders={},
                        rag_options=rag_opts,
                        llm_client=writer_client,
                        state_mgr=local_sm,
                        rag_client=rag_client,
                        aux_knowledge=None,
                        fact_check_enabled=fc_enabled,
                        template=template if isinstance(template, dict) else None
                    )

                    results.append({
                        "topic": topic,
                        "success": True,
                        "output_file": output_path,
                        "word_count": len(md_content.replace(" ", "").replace("\n", ""))
                    })
                except Exception as e:
                    errors.append({"topic": topic, "error": str(e)})

                with _batch_lock:
                    if task_id in _batch_tasks:
                        _batch_tasks[task_id]["done"] += 1
                        _batch_tasks[task_id]["results"] = list(results)
                        _batch_tasks[task_id]["errors"] = list(errors)

            with _batch_lock:
                if task_id in _batch_tasks:
                    _batch_tasks[task_id]["done_flag"] = True
                    _batch_tasks[task_id]["current_topic"] = ""

        t = _thr.Thread(target=_run_batch, daemon=True)
        with _batch_lock:
            _batch_tasks[task_id] = {
                "total": len(topics), "done": 0,
                "current_topic": "", "results": [],
                "errors": [], "done_flag": False
            }
        t.start()

        self._json_response({"success": True, "task_id": task_id, "total": len(topics)})

    def _handle_batch_progress(self):
        params = urllib.parse.parse_qs(
            urllib.parse.urlparse(self.path).query
        )
        task_id = (params.get("task_id") or [""])[0]
        if not task_id:
            self._json_response({"success": False, "error": "缺少 task_id"}, 400)
            return
        with _batch_lock:
            task = _batch_tasks.get(task_id)
            if task is None:
                self._json_response({"success": False, "error": "任务不存在"}, 404)
                return
            if task["done_flag"]:
                del _batch_tasks[task_id]
            self._json_response({
                "success": True,
                "total": task["total"],
                "done": task["done"],
                "current_topic": task["current_topic"],
                "results": task["results"],
                "errors": task["errors"],
                "done_flag": task["done_flag"]
            })

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

    # ---- LLM 模板生成 API ----

    def _handle_gen_template(self):
        try:
            data = self._read_body()
        except ValueError as e:
            self._json_response({"success": False, "error": str(e)}, 400)
            return
        description = data.get("description", "").strip()
        if not description:
            self._json_response({"success": False, "error": "描述不能为空"}, 400)
            return

        GEN_TEMPLATE_SYSTEM_PROMPT = """你是一个文档模板规划助手。根据用户描述生成模板定义。

输出 JSON：
{
  "name": "模板名称",
  "meta": [
    {"name": "字段名", "show_label": true/false, "desc": "字段意义", "source": "user/llm/auto"}
  ],
  "content": [
    {"name": "字段名", "show_label": true/false, "desc": "写作要点", "type": "leaf/section", "logical_order": 0}
  ],
  "style": "写作风格提示词",
  "logic": "写作顺序提示词（控制LLM的认知流程顺序，不控制文章顺序）"
}

规则：

一、元数据 vs 内容树 —— 严格的二分法：
- 元数据：标识/管理信息（标题、作者、单位、文号、密级、日期等）。
  特征：短（≤100字）、不参与大纲规划、不支持子结构、以键值对渲染。
  位置：放入 meta 数组。
- 内容树：文章正文构成（摘要、引言、正文、结论、参考文献等）。
  特征：长（≥200字）、参与大纲规划、可拆子结构、构成文章主体。
  位置：放入 content 数组。
  互斥：同一个字段不能同时出现在 meta 和 content 中。

二、元数据规则：
- source=user：用户必须填写，LLM不碰（如作者、单位、文号）
- source=auto：用户可填，留空LLM生成（如标题）
- source=llm：由LLM生成（如关键词）——但关键词推荐放入 content 尾部
- show_label=true 输出时带"字段名："前缀，false 不带
- 元数据固定为 leaf（无子结构），不要输出 type 字段

三、内容树规则：
- source 固定为 llm（不输出 source 字段）
- type=leaf：单段内容，不拆子结构（摘要、参考文献、关键词）
- type=section：需要拆 2-4 个子结构（引言、正文各节、结论）
- show_label=true 输出时带"字段名："前缀，false 不带
- desc 写清楚写作要点
- logical_order：可选。不设或留空=按 content[] 顺序写，不需特殊排序。
  需要特殊排序时才设置：0=先写，1=其次，2=最后写（如摘要/关键词需在全文写完后提取）。
  逻辑顺序只控制 LLM 写作时的认知流程，不影响文章最终排列

四、逻辑提示词（logic）规则：
- 控制 LLM 的认知流程顺序，而非文章最终顺序
- 示例："引言和正文优先写，结论在正文完成后写，关键词和摘要在全文写完后从成品中提取"
- 如果用户未指定，根据字段类型推断合理顺序

五、其他规则：
- 字段数量：元数据 0-8 个 + 内容树 3-12 个
- name 用中文
- style 描述文风和语气"""

        client = self._create_planner_client()
        user_name = data.get("name", "").strip()
        user_content = f"模板名称：{user_name}\n" if user_name else ""
        user_content += description
        messages = [
            {"role": "system", "content": GEN_TEMPLATE_SYSTEM_PROMPT},
            {"role": "user", "content": description}
        ]

        # 多轮重试 + 容错解析（仿 planner.py 的 parse_outline）
        result = None
        last_raw = ""
        for attempt in range(3):
            try:
                raw = client.chat(messages, max_tokens=None, temperature=0.3)
                last_raw = raw
            except Exception as e:
                if attempt < 2:
                    # 重试
                    continue
                self._json_response({"success": False, "error": f"LLM 调用失败: {e}"}, 500)
                return

            # 尝试直接解析
            try:
                result = json.loads(raw.strip())
                if result.get("meta") or result.get("content"):
                    break
            except json.JSONDecodeError:
                pass

            # 尝试提取 ```json ... ``` 代码块
            if "```" in raw:
                start = raw.index("```")
                end = raw.index("```", start + 3) if "```" in raw[start + 3:] else len(raw)
                content = raw[start + 3:end].strip()
                if content.startswith("json\n"):
                    content = content[5:]
                try:
                    result = json.loads(content)
                    if result.get("meta") or result.get("content"):
                        break
                except (json.JSONDecodeError, ValueError):
                    pass

            # 尝试找到第一个 { 提取 JSON
            brace = raw.find("{")
            if brace >= 0:
                try:
                    result = json.loads(raw[brace:])
                    if result.get("meta") or result.get("content"):
                        break
                except json.JSONDecodeError:
                    lines = raw[brace:].split("\n")
                    for cut in range(len(lines), 0, -1):
                        try:
                            r = json.loads("\n".join(lines[:cut]))
                            if r.get("meta") or r.get("content"):
                                result = r
                                break
                        except json.JSONDecodeError:
                            continue
                    if result:
                        break

            if attempt < 2:
                error_feedback = (
                    f"【格式错误】输出必须包含非空的 meta 和 content 字段（至少一个有内容）。\n"
                    f"只输出 JSON，不要任何其他文字。\n重新生成："
                )
                messages.append({"role": "assistant", "content": raw[:500]})
                messages.append({"role": "user", "content": error_feedback})

        if result:
            result = _normalize_template(result)
            if result.get("meta") or result.get("content"):
                self._json_response({"success": True, "template": result})
                return
        self._json_response({"success": False, "error": f"模板生成失败，LLM 3 次均未返回正确格式。最后输出：{last_raw[:300]}"}, 500)

    def log_message(self, format, *args):
        """抑制默认日志输出"""
        pass


def _normalize_template(t: dict) -> dict:
    """校验 + 补默认值，确保 gen-template 输出结构正确"""
    # name 兜底
    if not t.get("name"):
        t["name"] = "自定义模板"

    # meta 字段校验
    meta = t.get("meta", [])
    if not isinstance(meta, list):
        meta = []
    cleaned_meta = []
    for f in meta:
        if not isinstance(f, dict):
            continue
        name = str(f.get("name", "")).strip()
        if not name:
            continue
        cleaned_meta.append({
            "name": name,
            "show_label": bool(f.get("show_label", True)),
            "desc": str(f.get("desc", "")),
            "source": f.get("source", "auto") if f.get("source") in ("user", "auto", "llm") else "auto"
        })
    t["meta"] = cleaned_meta

    # content 字段校验
    content = t.get("content", [])
    if not isinstance(content, list):
        content = []
    cleaned_content = []
    for f in content:
        if not isinstance(f, dict):
            continue
        name = str(f.get("name", "")).strip()
        if not name:
            continue
        entry = {
            "name": name,
            "show_label": bool(f.get("show_label", True)),
            "desc": str(f.get("desc", "")),
            "type": f.get("type", "leaf") if f.get("type") in ("leaf", "section") else "leaf"
        }
        lo = f.get("logical_order")
        if lo is not None and lo in (0, 1, 2):
            entry["logical_order"] = lo
        cleaned_content.append(entry)
    t["content"] = cleaned_content

    # style / logic 字符串
    t.setdefault("style", "")
    t.setdefault("logic", "")

    # 清理多余字段
    allowed = {"name", "meta", "content", "style", "logic"}
    for k in list(t.keys()):
        if k not in allowed:
            del t[k]

    return t


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
.btn-danger { background: #c0392b; color: #fff; }
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
.session-item.archived { opacity: 0.5; }
.session-item .s-actions { display: flex; gap: 4px; margin-left: auto; flex-shrink: 0; }
.session-item .s-actions button {
  background: transparent; border: none; cursor: pointer; font-size: 11px; color: var(--text-dim); padding: 2px 4px;
}
.session-item .s-actions button:hover { color: var(--accent); }
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

/* 模态框 */
.modal-overlay {
  display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  z-index: 1000; align-items: center; justify-content: center;
}
.modal-overlay.show { display: flex; }
.modal-box {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius);
  width: 520px; max-width: 90vw; max-height: 80vh; display: flex; flex-direction: column;
}
.modal-header {
  padding: 12px 16px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
}
.modal-header h3 { font-size: 14px; color: var(--accent); font-weight: 500; }
.modal-close { cursor: pointer; color: var(--text-dim); font-size: 18px; background: none; border: none; padding: 0 4px; }
.modal-body { padding: 16px; overflow-y: auto; flex: 1; }
.modal-body textarea {
  width: 100%; min-height: 120px; padding: 8px; background: var(--bg-input);
  border: 1px solid var(--border); border-radius: 4px; color: var(--text);
  font-size: 13px; font-family: inherit; resize: vertical;
}
.modal-body .file-upload-area {
  border: 1px dashed var(--border); border-radius: 4px; padding: 16px;
  text-align: center; margin-top: 12px; cursor: pointer; font-size: 13px; color: var(--text-dim);
}
.modal-body .file-upload-area:hover { border-color: var(--accent); }
.modal-body .file-list { margin-top: 8px; }
.modal-body .file-item {
  display: flex; align-items: center; gap: 8px; padding: 4px 8px;
  background: var(--bg); border-radius: 4px; margin-bottom: 4px; font-size: 12px;
}
.modal-body .file-item .file-del { cursor: pointer; color: var(--accent); font-size: 14px; }
.modal-footer {
  padding: 12px 16px; border-top: 1px solid var(--border);
  display: flex; gap: 8px; justify-content: flex-end;
}
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
        <div class="form-row" style="flex-wrap:nowrap">
          <label style="min-width:auto;white-space:nowrap">超时(s)</label>
          <input type="number" id="planner-timeout" value="180" style="width:100px;flex-shrink:0">
          <label style="min-width:auto;white-space:nowrap">最大Token</label>
          <input type="number" id="planner-max-tokens" value="4096" style="width:120px;flex-shrink:0">
          <label style="min-width:auto;white-space:nowrap">温度</label>
          <input type="number" id="planner-temperature" value="0.6" min="0" max="1" step="0.05" style="width:70px;flex-shrink:0">
        </div>
        <div class="form-row" style="font-size:11px;color:var(--text-dim)">
          <span></span>
          <span>推理模型建议不低于 4096（默认最低值），长文建议 8192 以上。</span>
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
        <div class="form-row" style="flex-wrap:nowrap">
          <label style="min-width:auto;white-space:nowrap">超时(s)</label>
          <input type="number" id="writer-timeout" value="300" style="width:100px;flex-shrink:0">
          <label style="min-width:auto;white-space:nowrap">最大Token</label>
          <input type="number" id="writer-max-tokens" value="8192" style="width:120px;flex-shrink:0">
          <label style="min-width:auto;white-space:nowrap">温度</label>
          <input type="number" id="writer-temperature" value="0.7" min="0" max="1" step="0.05" style="width:70px;flex-shrink:0">
        </div>
        <div class="form-row" style="font-size:11px;color:var(--text-dim)">
          <span></span>
          <span>推理模型建议不低于 4096（默认最低值），长文建议 8192 以上。</span>
        </div>
      </div>

      <div class="config-section">
        <h3>📝 模板管理</h3>
        <div class="form-row">
          <label>模板</label>
          <div style="flex:1;display:flex;gap:4px;align-items:center">
            <div style="position:relative;flex:1">
              <select id="template-select" style="width:100%;padding:4px 6px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:13px" onchange="onTemplateChange()" size="1">
              </select>
            </div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="saveTemplateAs()">另存为</button>
          <button class="btn btn-danger btn-sm" onclick="deleteTemplate()" title="删除当前自定义模板">删除</button>
          <button class="btn btn-success btn-sm" onclick="openGenTemplate()">从对话生成</button>
        </div>

        <div class="form-row">
          <label style="font-weight:600;color:#f39c12">元数据</label>
          <div style="flex:1;font-size:12px;color:var(--text-dim)">
            标识/管理信息，短数据（≤100字），以键值对渲染，不参与大纲规划。每行：名称 | 显示标签 | 字段意义 | 填写者
          </div>
        </div>
        <div id="meta-editor" style="overflow-x:auto;margin-bottom:12px">
          <table style="width:100%;border-collapse:collapse;font-size:12px">
            <thead>
              <tr style="background:var(--bg-input)">
                <th style="padding:4px 6px;text-align:left;min-width:80px">名称</th>
                <th style="padding:4px 6px;text-align:center;width:40px">显</th>
                <th style="padding:4px 6px;text-align:left;min-width:120px">字段意义</th>
                <th style="padding:4px 6px;text-align:center;width:65px">填写</th>
                <th style="padding:4px 6px;text-align:center;width:30px"></th>
              </tr>
            </thead>
            <tbody id="meta-rows">
            </tbody>
          </table>
        </div>
        <div class="form-row">
          <button class="btn btn-secondary btn-sm" onclick="addMetaRow()">+ 添加元数据</button>
        </div>

        <div class="form-row" style="margin-top:4px">
          <label style="font-weight:600;color:#5dade2">内容树</label>
          <div style="flex:1;font-size:12px;color:var(--text-dim)">
            文章主体，长文本（≥200字），参与大纲规划，可拆分子结构。每行：名称 | 显 | 字段意义 | 子结构 | 逻辑顺序 | source 固定为 llm
          </div>
        </div>
        <div id="content-editor" style="overflow-x:auto;margin-bottom:8px">
          <table style="width:100%;border-collapse:collapse;font-size:12px">
            <thead>
              <tr style="background:var(--bg-input)">
                <th style="padding:4px 6px;text-align:left;min-width:80px">名称</th>
                <th style="padding:4px 6px;text-align:center;width:40px">显</th>
                <th style="padding:4px 6px;text-align:left;min-width:120px">字段意义</th>
                <th style="padding:4px 6px;text-align:center;width:65px">子结构</th>
                <th style="padding:4px 6px;text-align:center;width:65px">逻辑顺序</th>
                <th style="padding:4px 6px;text-align:center;width:30px"></th>
              </tr>
            </thead>
            <tbody id="content-rows">
            </tbody>
          </table>
        </div>
        <div class="form-row">
          <button class="btn btn-secondary btn-sm" onclick="addContentRow()">+ 添加内容</button>
        </div>

        <div class="form-row">
          <label>风格提示词</label>
          <div style="display:flex;flex-direction:column;flex:1;gap:4px">
            <textarea id="template-style" rows="3" placeholder="写作风格说明，如：请以学术论文风格撰写..."></textarea>
            <span style="font-size:11px;color:var(--text-dim)">控制文风和语气，注入每一步写作 prompt</span>
          </div>
        </div>
        <div class="form-row">
          <label>逻辑提示词</label>
          <div style="display:flex;flex-direction:column;flex:1;gap:4px">
            <textarea id="template-logic" rows="2" placeholder="写作顺序说明，如：先写引言和正文，再写结论，最后提取关键词和摘要。留空则按文章顺序写。"></textarea>
            <span style="font-size:11px;color:var(--text-dim)">控制 LLM 认知流程顺序（先写什么后写什么），不改变文章最终排列</span>
          </div>
        </div>
        <div style="font-size:12px;color:#e67e22;margin-top:8px;padding:6px 10px;background:rgba(230,126,34,0.1);border-radius:4px">
          ⚠️ 修改表格后必须点「另存为」保存为新模板并重新选择，否则改动不生效。
        </div>
      </div>

      <!-- LLM 生成模板模态框 -->
      <div class="modal-overlay" id="gen-template-modal">
        <div class="modal-box">
          <div class="modal-header">
            <h3>从对话生成模板</h3>
            <button class="modal-close" onclick="closeGenTemplate()">&times;</button>
          </div>
          <div class="modal-body">
            <p style="font-size:13px;color:var(--text-dim);margin-bottom:8px">描述你需要的文档结构，例如：</p>
            <p style="font-size:12px;color:#f39c12;margin-bottom:8px">"我要写技术报告，需要作者、版本号、背景、技术方案、风险评估、下一步计划"</p>
            <div style="display:flex;gap:8px;margin-bottom:8px">
              <input type="text" id="gen-template-name" style="flex:1;padding:6px 8px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:13px" placeholder="模板名称（留空LLM自动生成）">
            </div>
            <textarea id="gen-template-desc" rows="4" placeholder="在这里描述你的文档结构需求..."></textarea>
          </div>
          <div class="modal-footer">
            <span id="gen-template-status" style="font-size:12px;color:var(--text-dim);flex:1"></span>
            <button class="btn btn-secondary" onclick="closeGenTemplate()">取消</button>
            <button class="btn btn-primary" onclick="generateTemplate()">生成并保存</button>
          </div>
        </div>
      </div>

      <!-- 字段意义编辑模态框 -->
      <div class="modal-overlay" id="desc-modal" style="z-index:100">
        <div class="modal-box" style="max-width:500px">
          <div class="modal-header">
            <h3>编辑字段意义</h3>
            <button class="modal-close" onclick="closeDescModal()">&times;</button>
          </div>
          <div class="modal-body">
            <p style="font-size:13px;color:var(--text-dim);margin-bottom:8px">描述字段的写作要点或用途，将展示给 LLM 和用户参考。</p>
            <p style="font-size:12px;color:#f39c12;margin-bottom:8px">如需多级子标题，在描述中写明即可，如："按 章→节→条→款 四级展开，子标题用 ####/#####"</p>
            <textarea id="desc-editor" rows="6" placeholder="输入字段的详细意义..."></textarea>
          </div>
          <div class="modal-footer">
            <span id="desc-modal-status" style="font-size:12px;color:var(--text-dim);flex:1"></span>
            <button class="btn btn-secondary" onclick="closeDescModal()">取消</button>
            <button class="btn btn-primary" onclick="saveDescModal()">确认</button>
          </div>
        </div>
      </div>

      <!-- 另存为模板模态框 -->
      <div class="modal-overlay" id="saveas-modal" style="z-index:100">
        <div class="modal-box" style="max-width:400px">
          <div class="modal-header">
            <h3>另存为模板</h3>
            <button class="modal-close" onclick="closeSaveAsModal()">&times;</button>
          </div>
          <div class="modal-body">
            <p style="font-size:13px;color:var(--text-dim);margin-bottom:8px">输入新模板名称：</p>
            <input type="text" id="saveas-name" style="width:100%;padding:6px 8px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:14px" placeholder="模板名称" autofocus>
          </div>
          <div class="modal-footer">
            <span id="saveas-modal-status" style="font-size:12px;color:var(--text-dim);flex:1"></span>
            <button class="btn btn-secondary" onclick="closeSaveAsModal()">取消</button>
            <button class="btn btn-primary" onclick="confirmSaveAs()">确认保存</button>
          </div>
        </div>
      </div>

      <!-- 重新规划输入模态框 -->
      <div class="modal-overlay" id="replan-modal" style="z-index:100">
        <div class="modal-box" style="max-width:500px">
          <div class="modal-header">
            <h3>调整规划</h3>
            <button class="modal-close" onclick="closeReplanModal()">&times;</button>
          </div>
          <div class="modal-body">
            <p style="font-size:13px;color:var(--text-dim);margin-bottom:8px">输入对当前大纲的调整要求。留空则使用原有规划不变。</p>
            <p style="font-size:12px;color:#f39c12;margin-bottom:8px">例如：第2节加3个子结构、结论改800字、正文分5个部分每部分600字、删除第4节</p>
            <textarea id="replan-hints" rows="6" placeholder="输入调整要求（留空则按原规划重跑）..."></textarea>
          </div>
          <div class="modal-footer">
            <span id="replan-modal-status" style="font-size:12px;color:var(--text-dim);flex:1"></span>
            <button class="btn btn-secondary" onclick="closeReplanModal()">取消</button>
            <button class="btn btn-primary" onclick="confirmReplan()">确认重新规划</button>
          </div>
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
          <button class="btn btn-secondary" id="rag-stop-btn" onclick="stopRag()" disabled style="margin-left:4px">停止 RAG</button>
          <button class="btn btn-secondary btn-sm" onclick="checkRagStatus()">刷新状态</button>
        </div>
        <div class="form-row" id="rag-kb-row" style="display:none">
          <label>可用知识库</label>
          <span id="rag-kb-list" style="font-size:13px;color:var(--text-dim)"></span>
        </div>
      </div>

      <div class="config-section">
        <h3>⚙️ 写作参数</h3>
        <div class="form-row">
          <label>前文回顾字数</label>
          <input type="number" id="context-review-length" value="8000" min="100" max="32000" style="width:100px;">
          <span style="font-size:12px;color:var(--text-dim)">写作时注入前文上下文的最大字符数</span>
        </div>
        <div class="form-row">
          <label>事实自检</label>
          <label style="font-size:13px;cursor:pointer"><input type="checkbox" id="fact-check-enabled" onchange="saveConfig()"> 开启（写作完成后自动标记可疑事实）</label>
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
        <div id="sidebar-archived" style="display:none;border-top:1px solid var(--border);flex-shrink:0">
          <div onclick="toggleArchived()" style="padding:6px 12px;cursor:pointer;font-size:12px;color:var(--text-dim);user-select:none;">
            <span id="archived-toggle">▸</span> 归档会话 (<span id="archived-count">0</span>)
          </div>
          <div id="sidebar-archived-list" style="max-height:200px;overflow-y:auto"></div>
        </div>
      </div>
      <div class="chat-main">
        <div class="chat-messages" id="chat-messages">
          <div class="msg assistant">
            <div class="msg-label">助手</div>
            <div class="msg-content">欢迎使用结构化写作助手。请在下方输入写作主题，我将为您生成大纲并协助完成文章。</div>
          </div>
        </div>
        <div id="meta-inputs-bar" style="display:none;padding:8px 16px;border-top:1px solid var(--border);background:var(--bg-card);font-size:13px">
          <div style="display:flex;flex-wrap:wrap;gap:8px" id="meta-inputs-container"></div>
        </div>
        <div class="chat-input-area">
          <textarea id="chat-input" placeholder="输入写作主题...（多行=批量自动撰写）" rows="2"
            onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage()}"></textarea>
          <button class="btn btn-primary" onclick="sendMessage()">发送</button>
          <button class="btn btn-success" onclick="startAutoGeneration()">自动撰写</button>
        </div>
        <div id="batch-progress" style="display:none;padding:8px 16px;border-top:1px solid var(--border);background:var(--bg-card);font-size:13px;color:var(--text-dim)"></div>
        <div id="stop-bar" style="display:none;padding:4px 16px;border-top:1px solid var(--border);background:var(--bg-card);font-size:12px;text-align:center">
          <button class="btn btn-sm btn-secondary" onclick="stopGeneration('delay')">延时停止</button>
          <button class="btn btn-sm btn-secondary" style="background:var(--accent);color:#fff" onclick="stopGeneration('immediate')">立即停止</button>
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

  // 配置加载完成后刷新 meta 输入框
  setTimeout(() => {
    const sel = document.getElementById('template-select');
    if (sel) renderMetaInputs(sel.value);
  }, 200);

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
    document.getElementById('planner-temperature').value = pm.temperature != null ? pm.temperature : 0.6;
    document.getElementById('writer-backend').value = wm.backend || 'lmstudio';
    document.getElementById('writer-base-url').value = wm.base_url || 'http://localhost:1234';
    document.getElementById('writer-timeout').value = wm.timeout || 300;
    document.getElementById('writer-max-tokens').value = wm.max_tokens || 8192;
    document.getElementById('writer-temperature').value = wm.temperature != null ? wm.temperature : 0.7;
    // 加载模板
    const templates = c.templates || {};
    const selectedTemplate = c.selected_template || '日常写作';
    const sel = document.getElementById('template-select');
    const tmplNames = Object.keys(templates);
    // 字母排序，"自定义"永远最后
    tmplNames.sort((a, b) => a.localeCompare(b, 'zh-CN'));
    const ziDingYiIdx = tmplNames.indexOf('自定义');
    if (ziDingYiIdx >= 0) {
      tmplNames.splice(ziDingYiIdx, 1);
      tmplNames.push('自定义');
    }
    if (tmplNames.length) {
      sel.innerHTML = tmplNames.map(t => `<option value="${t}">${t}</option>`).join('');
    }
    sel.value = selectedTemplate;
    // 加载 meta/content/style/logic
    const tmpl = templates[selectedTemplate] || {};
    if (typeof tmpl === 'object' && (tmpl.meta || tmpl.content)) {
      renderMetaRows(tmpl.meta || []);
      renderContentRows(tmpl.content || []);
      document.getElementById('template-style').value = tmpl.style || '';
      document.getElementById('template-logic').value = tmpl.logic || '';
    } else if (typeof tmpl === 'object' && tmpl.structure) {
      // structure 旧格式 → 转为 meta+content
      const m = [], c = [];
      (tmpl.structure || []).forEach(f => {
        const src = f.source || 'llm';
        if (src === 'user' || src === 'auto') {
          m.push({name: f.name, show_label: f.show_label, desc: f.desc, source: src});
        } else {
          c.push({name: f.name, show_label: f.show_label, desc: f.desc, type: f.type || 'section'});
        }
      });
      renderMetaRows(m);
      renderContentRows(c);
      document.getElementById('template-style').value = tmpl.style || '';
      document.getElementById('template-logic').value = '';
    } else if (typeof tmpl === 'string') {
      renderMetaRows([]);
      renderContentRows([]);
      document.getElementById('template-style').value = tmpl;
      document.getElementById('template-logic').value = '';
    } else {
      renderMetaRows([]);
      renderContentRows([]);
      document.getElementById('template-style').value = '';
      document.getElementById('template-logic').value = '';
    }
    // 加载用户模板
    if (c.user_templates) {
      Object.keys(c.user_templates).forEach(k => {
        if (!templates[k]) {
          const opt = document.createElement('option');
          opt.value = k; opt.textContent = k + ' ★';
          sel.appendChild(opt);
        }
      });
    }
    // 确保选中值有效
    if (!sel.querySelector(`option[value="${selectedTemplate}"]`)) {
      sel.value = sel.options[0]?.value || '';
    }
    // 加载 RAG 路径
    if (c.rag_path) document.getElementById('rag-path').value = c.rag_path;
    if (c.context_review_length) document.getElementById('context-review-length').value = c.context_review_length;
    if (c.fact_check_enabled) document.getElementById('fact-check-enabled').checked = true;
    refreshModels('planner', pm.model);
    refreshModels('writer', wm.model);
  });
}

function saveConfig() {
  const data = {
    planner_model: {
      backend: document.getElementById('planner-backend').value,
      base_url: document.getElementById('planner-base-url').value,
      model: document.getElementById('planner-model').value,
      timeout: parseInt(document.getElementById('planner-timeout').value) || 180,
      max_tokens: parseInt(document.getElementById('planner-max-tokens').value) || 4096,
      temperature: parseFloat(document.getElementById('planner-temperature').value) || 0.6
    },
    writer_model: {
      backend: document.getElementById('writer-backend').value,
      base_url: document.getElementById('writer-base-url').value,
      model: document.getElementById('writer-model').value,
      timeout: parseInt(document.getElementById('writer-timeout').value) || 300,
      max_tokens: parseInt(document.getElementById('writer-max-tokens').value) || 8192,
      temperature: parseFloat(document.getElementById('writer-temperature').value) || 0.7
    },
    selected_template: document.getElementById('template-select').value,
    context_review_length: parseInt(document.getElementById('context-review-length').value) || 8000,
    fact_check_enabled: document.getElementById('fact-check-enabled').checked,
    templates: {}  // 在下面通过 templData 更新
  };
    // 读取元数据表格
    const metaRows = document.querySelectorAll('#meta-rows tr');
    const meta = [];
    metaRows.forEach(tr => {
      const inputs = tr.querySelectorAll('input, select');
      if (inputs.length < 3) return;
      const name = inputs[0].value.trim();
      if (!name) return;
      const descSpan = tr.querySelector('.desc-preview');
      meta.push({name, show_label: inputs[1].checked, desc: descSpan ? (descSpan.dataset.fullDesc || '') : '', source: inputs[2].value});
    });
    // 读取内容树表格
    const contentRows = document.querySelectorAll('#content-rows tr');
    const content = [];
    contentRows.forEach(tr => {
      const inputs = tr.querySelectorAll('input, select');
      if (inputs.length < 4) return;
      const name = inputs[0].value.trim();
      if (!name) return;
      const descSpan = tr.querySelector('.desc-preview');
      content.push({name, show_label: inputs[1].checked, desc: descSpan ? (descSpan.dataset.fullDesc || '') : '', type: inputs[2].value, logical_order: inputs[3].value !== '' ? parseInt(inputs[3].value) : null});
    });
    const style = document.getElementById('template-style').value;
    const logic = document.getElementById('template-logic').value;
    const selTmpl = document.getElementById('template-select').value;
    const tmplObj = {};
    tmplObj[selTmpl] = {meta, content, style, logic};
    // 保留其他模板
      fetch('/api/config').then(r => r.json()).then(cfg => {
        if (!cfg.success) return;
        const existing = cfg.config.templates || {};
        // 合并：保留未选中的模板，更新当前选中的
        Object.keys(existing).forEach(k => {
          if (k !== selTmpl) {
            const v = existing[k];
            if (typeof v === 'object' && (v.meta || v.content)) {
              tmplObj[k] = v;  // 新格式 meta+content
            } else if (typeof v === 'object' && v.structure) {
              // structure 旧格式 → 转为 meta+content
              const m = [], c = [];
              (v.structure || []).forEach(f => {
                const src = f.source || 'llm';
                if (src === 'user' || src === 'auto') {
                  m.push({name: f.name, show_label: f.show_label, desc: f.desc, source: src});
                } else {
                  c.push({name: f.name, show_label: f.show_label, desc: f.desc, type: f.type || 'section'});
                }
              });
              tmplObj[k] = {meta: m, content: c, style: v.style || '', logic: ''};
            }
          }
        });
        data.templates = tmplObj;
      data.default_prompt = style || (tmplObj[selTmpl] && tmplObj[selTmpl].style) || '';

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
  fetch('/api/config', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({selected_template: tmplName})
  }).catch(() => {});
  fetch('/api/config').then(r => r.json()).then(d => {
    if (!d.success) return;
    const templates = d.config.templates || {};
    const tmpl = templates[tmplName] || {};
    if (typeof tmpl === 'object' && (tmpl.meta || tmpl.content)) {
      renderMetaRows(tmpl.meta || []);
      renderContentRows(tmpl.content || []);
      document.getElementById('template-style').value = tmpl.style || '';
      document.getElementById('template-logic').value = tmpl.logic || '';
    } else if (typeof tmpl === 'object' && tmpl.structure) {
      const m = [], c = [];
      (tmpl.structure || []).forEach(f => {
        const src = f.source || 'llm';
        if (src === 'user' || src === 'auto') { m.push({name: f.name, show_label: f.show_label, desc: f.desc, source: src}); }
        else { c.push({name: f.name, show_label: f.show_label, desc: f.desc, type: f.type || 'section'}); }
      });
      renderMetaRows(m); renderContentRows(c);
      document.getElementById('template-style').value = tmpl.style || '';
      document.getElementById('template-logic').value = '';
    } else if (typeof tmpl === 'string') {
      renderMetaRows([]); renderContentRows([]);
      document.getElementById('template-style').value = tmpl;
      document.getElementById('template-logic').value = '';
    } else {
      renderMetaRows([]); renderContentRows([]);
      document.getElementById('template-style').value = '';
      document.getElementById('template-logic').value = '';
    }
  });
}

// ===== 结构表格编辑器（元数据 + 内容树） =====

function renderMetaRows(meta) {
  const tbody = document.getElementById('meta-rows');
  tbody.innerHTML = '';
  (meta || []).forEach(f => addMetaRow(f));
  if (!meta || !meta.length) {
    addMetaRow({name:'标题',show_label:false,desc:'文章标题',source:'auto'});
  }
}

function renderContentRows(content) {
  const tbody = document.getElementById('content-rows');
  tbody.innerHTML = '';
  (content || []).forEach(f => addContentRow(f));
  if (!content || !content.length) {
    addContentRow({name:'正文',show_label:false,desc:'文章主体内容',type:'section'});
  }
}

function addMetaRow(field) {
  field = field || {name:'',show_label:true,desc:'',source:'auto'};
  const tr = document.createElement('tr');
  tr.style.borderBottom = '1px solid var(--border)';
  tr.innerHTML = [
    '<td style="padding:3px 6px"><input type="text" value="' + escHtml(field.name) + '" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;padding:3px 4px;color:var(--text);font-size:12px" placeholder="字段名"></td>',
    '<td style="padding:3px 6px;text-align:center"><input type="checkbox" ' + (field.show_label ? 'checked' : '') + ' style="accent-color:var(--accent)"></td>',
    '<td style="padding:3px 6px"><span class="desc-preview" onclick="openDescModal(this)" data-full-desc="' + escHtml(field.desc) + '" style="display:block;padding:3px 4px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;cursor:pointer;color:var(--text-dim);font-size:12px;min-height:16px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:140px" title="' + escHtml(field.desc) + '">' + escHtml(field.desc ? field.desc.substring(0,12)+(field.desc.length>12?'...':'') : '点击输入...') + '</span></td>',
    '<td style="padding:3px 6px"><select style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;padding:3px 4px;color:var(--text);font-size:12px"><option value="user" ' + (field.source==='user'?'selected':'') + '>用户</option><option value="llm" ' + (field.source==='llm'?'selected':'') + '>LLM</option><option value="auto" ' + (field.source==='auto'?'selected':'') + '>自动</option></select></td>',
    '<td style="padding:3px 6px;text-align:center"><button onclick="this.closest(\'tr\').remove()" title="删除此行" style="background:none;border:none;color:#e74c3c;cursor:pointer;font-size:15px;line-height:1">&times;</button></td>'
  ].join('');
  document.getElementById('meta-rows').appendChild(tr);
}

function addContentRow(field) {
  field = field || {name:'',show_label:true,desc:'',type:'section',logical_order:0};
  const lo = field.logical_order !== undefined ? field.logical_order : 0;
  const tr = document.createElement('tr');
  tr.style.borderBottom = '1px solid var(--border)';
  tr.innerHTML = [
    '<td style="padding:3px 6px"><input type="text" value="' + escHtml(field.name) + '" style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;padding:3px 4px;color:var(--text);font-size:12px" placeholder="字段名"></td>',
    '<td style="padding:3px 6px;text-align:center"><input type="checkbox" ' + (field.show_label ? 'checked' : '') + ' style="accent-color:var(--accent)"></td>',
    '<td style="padding:3px 6px"><span class="desc-preview" onclick="openDescModal(this)" data-full-desc="' + escHtml(field.desc) + '" style="display:block;padding:3px 4px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;cursor:pointer;color:var(--text-dim);font-size:12px;min-height:16px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:140px" title="' + escHtml(field.desc) + '">' + escHtml(field.desc ? field.desc.substring(0,12)+(field.desc.length>12?'...':'') : '点击输入...') + '</span></td>',
    '<td style="padding:3px 6px"><select style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;padding:3px 4px;color:var(--text);font-size:12px"><option value="leaf" ' + (field.type==='leaf'?'selected':'') + '>无</option><option value="section" ' + (field.type==='section'?'selected':'') + '>有</option></select></td>',
    '<td style="padding:3px 6px"><select style="width:100%;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;padding:3px 4px;color:var(--text);font-size:12px"><option value="" ' + (!lo && lo!==0?'selected':'') + '>自动</option><option value="0" ' + (lo===0?'selected':'') + '>先写</option><option value="1" ' + (lo===1?'selected':'') + '>其次</option><option value="2" ' + (lo===2?'selected':'') + '>最后</option></select></td>',
    '<td style="padding:3px 6px;text-align:center"><button onclick="this.closest(\'tr\').remove()" title="删除此行" style="background:none;border:none;color:#e74c3c;cursor:pointer;font-size:15px;line-height:1">&times;</button></td>'
  ].join('');
  document.getElementById('content-rows').appendChild(tr);
}

function escHtml(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function saveTemplateAs() {
  document.getElementById('saveas-name').value = '';
  document.getElementById('saveas-modal-status').textContent = '';
  document.getElementById('saveas-modal').classList.add('show');
  setTimeout(() => document.getElementById('saveas-name').focus(), 100);
}

function closeSaveAsModal() {
  document.getElementById('saveas-modal').classList.remove('show');
}

function confirmSaveAs() {
  const name = document.getElementById('saveas-name').value.trim();
  if (!name) { document.getElementById('saveas-modal-status').textContent = '名称不能为空'; return; }
  closeSaveAsModal();
  // 读元数据表
  const meta = [];
  document.querySelectorAll('#meta-rows tr').forEach(tr => {
    const inputs = tr.querySelectorAll('input, select');
    if (inputs.length < 3) return;
    const n = inputs[0].value.trim();
    if (!n) return;
    const descSpan = tr.querySelector('.desc-preview');
    meta.push({name:n, show_label:inputs[1].checked, desc:descSpan ? (descSpan.dataset.fullDesc || '') : '', source:inputs[2].value});
  });
  // 读内容树表
  const content = [];
  document.querySelectorAll('#content-rows tr').forEach(tr => {
    const inputs = tr.querySelectorAll('input, select');
    if (inputs.length < 4) return;
    const n = inputs[0].value.trim();
    if (!n) return;
    const descSpan = tr.querySelector('.desc-preview');
    content.push({name:n, show_label:inputs[1].checked, desc:descSpan ? (descSpan.dataset.fullDesc || '') : '', type:inputs[2].value, logical_order: inputs[3].value !== '' ? parseInt(inputs[3].value) : null});
  });
  const style = document.getElementById('template-style').value;
  const logic = document.getElementById('template-logic').value;
  fetch('/api/config').then(r => r.json()).then(cfg => {
    if (!cfg.success) return;
    const templates = Object.assign({}, cfg.config.templates || {});
    templates[name] = {meta, content, style, logic};
    const userTemplates = Object.assign({}, cfg.config.user_templates || {});
    userTemplates[name] = true;
    fetch('/api/config', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({templates, user_templates: userTemplates})
    }).then(r => r.json()).then(d => {
      if (d.success) { loadConfig(); document.getElementById('template-select').value = name; onTemplateChange(); }
    });
  });
}

// ===== 删除自定义模板 =====
const _delTplPending = {pending: false, name: '', timer: null};

function deleteTemplate() {
  if (_delTplPending.pending) {
    // 双击确认
    const name = _delTplPending.name;
    clearTimeout(_delTplPending.timer);
    _delTplPending.pending = false;
    const btn = document.querySelector('.btn-danger');
    if (btn) { btn.textContent = '删除'; btn.style.background = '#c0392b'; }
    fetch('/api/config').then(r => r.json()).then(cfg => {
      if (!cfg.success) return;
      const userTpls = cfg.config.user_templates || {};
      if (!userTpls[name]) return;
      const templates = Object.assign({}, cfg.config.templates || {});
      delete templates[name];
      const newUserTpls = Object.assign({}, userTpls);
      delete newUserTpls[name];
      fetch('/api/config', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({templates, user_templates: newUserTpls})
      }).then(r => r.json()).then(d => { if (d.success) loadConfig(); });
    });
    return;
  }
  const sel = document.getElementById('template-select');
  const name = sel.value;
  fetch('/api/config').then(r => r.json()).then(cfg => {
    if (!cfg.success) return;
    const userTpls = cfg.config.user_templates || {};
    if (!userTpls[name]) return;
    const btn = document.querySelector('.btn-danger');
    if (btn) { btn.textContent = '确认?'; btn.style.background = '#e74c3c'; btn.style.color = '#fff'; }
    _delTplPending.pending = true;
    _delTplPending.name = name;
    _delTplPending.timer = setTimeout(() => {
      _delTplPending.pending = false;
      if (btn) { btn.textContent = '删除'; btn.style.background = '#c0392b'; btn.style.color = '#fff'; }
    }, 2500);
  });
}

// ===== LLM 模板生成 =====

function openGenTemplate() {
  document.getElementById('gen-template-modal').classList.add('show');
  document.getElementById('gen-template-desc').value = '';
  document.getElementById('gen-template-status').textContent = '';
}

function closeGenTemplate() {
  document.getElementById('gen-template-modal').classList.remove('show');
}

function generateTemplate() {
  const nameInput = document.getElementById('gen-template-name').value.trim();
  const desc = document.getElementById('gen-template-desc').value.trim();
  if (!desc) { document.getElementById('gen-template-status').textContent = '请输入描述'; return; }
  const status = document.getElementById('gen-template-status');
  status.textContent = '⏳ 生成中...';
  fetch('/api/gen-template', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({description: desc, name: nameInput || undefined})
  }).then(r => r.json()).then(d => {
    if (d.success && d.template && (d.template.meta || d.template.content)) {
      const templateName = d.template.name || nameInput || '自定义模板';
      fetch('/api/config').then(r => r.json()).then(cfg => {
        if (!cfg.success) return;
        const templates = Object.assign({}, cfg.config.templates || {});
        templates[templateName] = {meta: d.template.meta || [], content: d.template.content || [], style: d.template.style || '', logic: d.template.logic || ''};
        const userTemplates = Object.assign({}, cfg.config.user_templates || {});
        userTemplates[templateName] = true;
        fetch('/api/config', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({templates, user_templates: userTemplates})
        }).then(r2 => r2.json()).then(d2 => {
          if (d2.success) {
            loadConfig();
            document.getElementById('template-select').value = templateName;
            onTemplateChange();
            status.textContent = `✓ 已创建模板「${templateName}」`;
          } else {
            status.textContent = '✗ 保存失败';
          }
        });
        closeGenTemplate();
      });
    } else {
      status.textContent = '✗ ' + (d.error || '生成失败');
    }
  }).catch(e => {
    status.textContent = '✗ 请求失败';
  });
}

// ===== 字段意义模态框 =====
let _descModalTarget = null;

function openDescModal(span) {
  _descModalTarget = span;
  const fullDesc = span.dataset.fullDesc || (span.textContent === '点击输入...' ? '' : span.textContent);
  document.getElementById('desc-editor').value = fullDesc;
  document.getElementById('desc-modal-status').textContent = '';
  document.getElementById('desc-modal').classList.add('show');
}

function closeDescModal() {
  document.getElementById('desc-modal').classList.remove('show');
  _descModalTarget = null;
}

function saveDescModal() {
  if (!_descModalTarget) return;
  const value = document.getElementById('desc-editor').value.trim();
  const display = value ? value.substring(0, 12) + (value.length > 12 ? '...' : '') : '点击输入...';
  _descModalTarget.textContent = display;
  _descModalTarget.dataset.fullDesc = value;
  _descModalTarget.title = value || '点击编辑字段意义';
  _descModalTarget.dataset.fullDesc = value;
  closeDescModal();
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
  // 加 cache-buster 防止浏览器缓存 GET 响应
  fetch('/api/rag/status?_=' + Date.now()).then(r => r.json()).then(d => {
    const indicator = document.getElementById('rag-status-indicator');
    const btn = document.getElementById('rag-start-btn');
    const stopBtn = document.getElementById('rag-stop-btn');
    const kbRow = document.getElementById('rag-kb-row');
    const kbList = document.getElementById('rag-kb-list');

    if (d.online) {
      // 用户已点击停止：不再显示"运行中"，直到手动重新启动
      if (window._ragManuallyStopped) {
        indicator.innerHTML = '<span style="color:#e94560;font-weight:600">RAG 离线（端口被占用）</span>';
        syncRagOutlineState();
        return;
      }
      ragOnline = true;
      ragKbs = Array.isArray(d.kbs) ? d.kbs : [];
      indicator.innerHTML = '<span style="color:#00b894;font-weight:600">RAG 运行中 (port 8767)</span>';
      btn.disabled = true;
      btn.textContent = 'RAG 已运行';
      stopBtn.disabled = false;
      stopBtn.textContent = '停止 RAG';
      kbRow.style.display = '';
      kbList.textContent = ragKbs.length ? ragKbs.join('、') : '(无知识库)';
      // 清除"等待就绪"等旧状态文本
      const cs = document.getElementById('config-status');
      if (cs) { cs.textContent = ''; cs.className = ''; }
      // 如果之前是在轮询中检测到上线，停止轮询
      if (window._ragPollTimer) {
        clearInterval(window._ragPollTimer);
        window._ragPollTimer = null;
      }
    } else if (d.starting) {
      window._ragManuallyStopped = false;
      window._ragStoppedAt = 0;
      ragOnline = false;
      indicator.innerHTML = '<span style="color:#f39c12;font-weight:600">RAG 启动中...</span>';
      btn.disabled = true;
      btn.textContent = '启动中...';
      stopBtn.disabled = true;
      stopBtn.textContent = '停止 RAG';
      kbRow.style.display = 'none';
      const cs = document.getElementById('config-status');
      if (cs && cs.textContent === '已提交启动请求，等待就绪...') { cs.textContent = '等待 RAG 上线...'; }
    } else if (d.stderr) {
      // 子进程挂了，显示错误
      window._ragManuallyStopped = false;
      window._ragStoppedAt = 0;
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
      window._ragManuallyStopped = false;
      window._ragStoppedAt = 0;
      btn.disabled = false;
      btn.textContent = '冷启动 RAG';
      stopBtn.disabled = true;
      stopBtn.textContent = '停止 RAG';
      kbRow.style.display = 'none';
      const cs = document.getElementById('config-status');
      if (cs) { cs.textContent = ''; cs.className = ''; }
    }
    // 同步已渲染大纲卡片上的 RAG 控件状态
    syncRagOutlineState();
  }).catch(() => {
    document.getElementById('rag-status-indicator').innerHTML = '<span style="color:#e94560">RAG 检测失败</span>';
  });
}

function syncRagOutlineState() {
  document.querySelectorAll('.sc-rag-cb').forEach(cb => {
    cb.disabled = !ragOnline;
    cb.title = ragOnline ? '' : 'RAG未连接';
    if (!ragOnline) cb.checked = false;
    // 同步 KB 下拉框
    const card = cb.closest('.section-card');
    if (card) {
      let kbSelect = card.querySelector('.sc-kb');
      if (ragOnline) {
        if (!kbSelect && ragKbs.length) {
          const newKb = document.createElement('select');
          newKb.className = 'sc-kb';
          newKb.style.cssText = 'display:none;width:120px;font-size:12px';
          newKb.onchange = () => collectOutlineData();
          const kbLabel = card.querySelector('.sc-rag');
          if (kbLabel) {
            const opts = '<option value="">自动KB</option>' + ragKbs.map(k => `<option value="${k}">${k}</option>`).join('');
            newKb.innerHTML = opts;
            kbLabel.after(newKb);
          }
        }
        if (kbSelect) kbSelect.style.display = cb.checked ? '' : 'none';
      } else {
        if (kbSelect) kbSelect.style.display = 'none';
      }
    }
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
  window._ragManuallyStopped = false;  // 允许再次显示"RAG 运行中"
  window._ragStoppedAt = 0;
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
      window._ragPollTimer = setInterval(checkRagStatus, 1500);
      checkRagStatus();  // 立即查一次，不等 interval
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

function stopRag() {
  window._ragManuallyStopped = true;  // 不再显示"RAG 运行中"
  window._ragStoppedAt = Date.now();
  const stopBtn = document.getElementById('rag-stop-btn');
  const startBtn = document.getElementById('rag-start-btn');
  stopBtn.disabled = true;
  stopBtn.textContent = '停止中...';
  startBtn.disabled = true;
  startBtn.textContent = '停止中...';
  document.getElementById('rag-status-indicator').innerHTML = '<span style="color:#f39c12;font-weight:600">正在停止 RAG...</span>';

  fetch('/api/rag/stop', { method: 'POST' })
    .then(r => r.json()).then(d => {
      if (d.success) {
        document.getElementById('rag-status-indicator').innerHTML = '<span style="color:#e94560;font-weight:600">RAG 离线</span>';
        document.getElementById('rag-stop-btn').disabled = true;
        document.getElementById('rag-stop-btn').textContent = '停止 RAG';
        document.getElementById('rag-start-btn').disabled = false;
        document.getElementById('rag-start-btn').textContent = '冷启动 RAG';
        document.getElementById('rag-kb-row').style.display = 'none';
      } else if (d.error) {
        document.getElementById('config-status').textContent = d.error;
        document.getElementById('config-status').className = 'status-msg error';
        document.getElementById('rag-stop-btn').disabled = false;
        document.getElementById('rag-stop-btn').textContent = '停止 RAG';
        document.getElementById('rag-start-btn').disabled = false;
        document.getElementById('rag-start-btn').textContent = '冷启动 RAG';
      }
    })
    .catch(() => {});
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

function refreshModels(prefix, savedValue) {
  const backend = document.getElementById(prefix + '-backend').value;
  const base_url = document.getElementById(prefix + '-base-url').value;
  const sel = document.getElementById(prefix + '-model');
  const currentVal = sel.value || savedValue;
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
      // 用 currentVal（来自 select 或 savedValue）恢复选择
      const restoreVal = currentVal || savedValue;
      if (restoreVal) {
        const exists = Array.from(sel.options).some(o => o.value === restoreVal);
        if (!exists) {
          const opt = document.createElement('option');
          opt.value = restoreVal;
          opt.textContent = restoreVal + '（已配置）';
          sel.appendChild(opt);
        }
        sel.value = restoreVal;
      }
      sel.disabled = false;
    }).catch(() => {
      sel.innerHTML = '<option value="">(获取失败)</option>';
      // 获取失败时也尝试恢复保存值
      if (savedValue) {
        const opt = document.createElement('option');
        opt.value = savedValue;
        opt.textContent = savedValue + '（已配置）';
        sel.appendChild(opt);
        sel.value = savedValue;
      }
      sel.disabled = false;
    });
}

// ===== 会话操作 =====
function loadSessions() {
  fetch('/api/sessions').then(r => r.json()).then(d => {
    if (!d.success) return;
    const list = document.getElementById('session-list');
    const archList = document.getElementById('sidebar-archived-list');
    const archSection = document.getElementById('sidebar-archived');
    list.innerHTML = '';
    archList.innerHTML = '';
    let active = 0, archived = 0;
    (d.sessions || []).forEach(s => {
      const item = document.createElement('div');
      item.className = 'session-item' + (s.id === currentSessionId && s.active ? ' active' : '') + (s.active ? '' : ' archived');
      const actions = s.active
        ? `<div class="s-actions"><button onclick="event.stopPropagation();archiveSession('${s.id}')" title="归档">🗂</button></div>`
        : `<div class="s-actions"><button onclick="event.stopPropagation();restoreSession('${s.id}')" title="恢复">↩</button><button id="del-${s.id}" onclick="event.stopPropagation();deleteSession('${s.id}')" title="单击确认，再单击删除" style="transition:all 0.2s">✕</button></div>`;
      item.innerHTML = `<div style="display:flex;align-items:center;width:100%"><div style="flex:1;min-width:0"><div class="s-title">${s.title || '未命名'}</div><div class="s-meta">${s.phase} · ${s.created_at?.slice(0,10) || ''}</div></div>${actions}</div>`;
      item.onclick = () => { if (s.active) loadSession(s.id); };
      if (s.active) {
        list.appendChild(item);
        active++;
      } else {
        archList.appendChild(item);
        archived++;
      }
    });
    document.getElementById('archived-count').textContent = archived;
    archSection.style.display = archived > 0 ? 'block' : 'none';
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

function archiveSession(id) {
  fetch('/api/session/archive', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({id: id}) })
    .then(r => r.json()).then(d => { if (d.success) loadSessions(); });
}

function restoreSession(id) {
  fetch('/api/session/restore', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({id: id}) })
    .then(r => r.json()).then(d => { if (d.success) loadSessions(); });
}

const _delPending = {};

function deleteSession(id) {
  // 清理其他待确认（避免多个按钮同时处于待确认状态）
  for (const pid in _delPending) {
    if (pid !== id) {
      clearTimeout(_delPending[pid]);
      delete _delPending[pid];
      const oldBtn = document.getElementById('del-' + pid);
      if (oldBtn) { oldBtn.textContent = '✕'; oldBtn.style.background = ''; oldBtn.style.color = ''; oldBtn.style.padding = ''; }
    }
  }
  const btn = document.getElementById('del-' + id);
  if (_delPending[id]) {
    // 双击确认
    clearTimeout(_delPending[id]);
    delete _delPending[id];
    if (btn) { btn.textContent = ''; btn.style.background = ''; btn.style.color = ''; btn.style.padding = ''; }
    fetch('/api/session/delete', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({id: id}) })
      .then(r => r.json()).then(d => { if (d.success) loadSessions(); });
  } else {
    // 第一次单击：进入待确认状态
    if (btn) { btn.textContent = '确认?'; btn.style.background = '#c0392b'; btn.style.color = '#fff'; btn.style.borderRadius = '3px'; btn.style.padding = '2px 6px'; }
    _delPending[id] = setTimeout(() => {
      delete _delPending[id];
      if (btn) { btn.textContent = '✕'; btn.style.background = ''; btn.style.color = ''; btn.style.padding = ''; }
    }, 2500);
  }
}

function toggleArchived() {
  const list = document.getElementById('sidebar-archived-list');
  const toggle = document.getElementById('archived-toggle');
  if (list.style.display === 'none') {
    list.style.display = '';
    toggle.textContent = '▾';
  } else {
    list.style.display = 'none';
    toggle.textContent = '▸';
  }
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

// ===== 元数据输入框渲染 =====

function renderMetaInputs(templateName) {
  const bar = document.getElementById('meta-inputs-bar');
  const container = document.getElementById('meta-inputs-container');
  container.innerHTML = '';
  fetch('/api/config').then(r => r.json()).then(d => {
    if (!d.success) return;
    const templates = d.config.templates || {};
    const tmpl = templates[templateName] || {};
    const metaFields = tmpl.meta || [];
    if (!metaFields.length) {
      bar.style.display = 'none';
      return;
    }
    const userFields = metaFields.filter(f => f.source === 'user' || f.source === 'auto');
    if (!userFields.length) { bar.style.display = 'none'; return; }
    bar.style.display = '';
    // 使用 grid 布局，每行最多 4 个
    container.style.display = 'grid';
    container.style.gridTemplateColumns = 'repeat(4, 1fr)';
    container.style.gap = '8px';
    userFields.forEach(f => {
      const wrap = document.createElement('div');
      wrap.style.cssText = 'display:flex;align-items:center;gap:4px;min-width:0';
      const label = document.createElement('label');
      label.textContent = f.name + (f.source === 'auto' ? '(可选)' : '');
      label.style.cssText = 'font-size:12px;color:var(--text-dim);white-space:nowrap;min-width:50px';
      const input = document.createElement('input');
      input.type = 'text';
      input.className = 'meta-field-input';
      input.dataset.fieldName = f.name;
      input.placeholder = f.desc + (f.source === 'auto' ? '（留空LLM生成）' : '');
      input.style.cssText = 'flex:1;padding:4px 6px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:12px';
      wrap.appendChild(label);
      wrap.appendChild(input);
      container.appendChild(wrap);
    });
  });
}

// Also update onTemplateChange to refresh meta inputs
const _origOnTemplateChange = onTemplateChange;
onTemplateChange = function() {
  if (_origOnTemplateChange) _origOnTemplateChange();
  const sel = document.getElementById('template-select');
  renderMetaInputs(sel.value);
};

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
  // 收集 meta 字段（用户/auto 已填的值）
  const meta = {};
  document.querySelectorAll('#meta-inputs-container .meta-field-input').forEach(el => {
    const val = el.value.trim();
    if (val) meta[el.dataset.fieldName] = val;
  });
  // topic 不作为 meta 注入，让 LLM 根据主题自动生成 auto 字段
  // 继续保留 topic 本身的上下文
  // 当前选中模板名
  const templateName = document.getElementById('template-select').value;
  fetch('/api/plan', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      topic: topic,
      session_id: currentSessionId,
      template_name: templateName,
      meta: meta
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
      const subOpts = ['', ...Array.from({length: subCount}, (_, i) => `s${i+1}`)]
        .map(v => `<option value="${v}" ${ss.id.endsWith('_1') && v==='' ? 'selected' : ''}>${v === '' ? '自动' : v}</option>`).join('');
      subHTML += `
        <div class="sub-card" data-sid="${ss.id}" style="margin-left:24px;padding:4px 8px;border-left:2px solid var(--border);margin-bottom:4px;">
          <div style="display:flex;align-items:center;gap:8px;">
            ${readOnly ? '' : `<input type="checkbox" class="sc-sub-cb" ${ss._checked !== false ? 'checked' : ''} onchange="onSubToggle(this, '${s.id}')">`}
            ${readOnly ? '' : `<select class="sc-sub-order" style="width:48px;font-size:11px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);padding:2px" onchange="collectOutlineData()">${subOpts}</select>`}
            <span style="font-size:13px;flex:1;color:var(--text-dim)">${ss.title}</span>
            ${readOnly ? '' : `<input type="number" class="sub-words" value="${ss.word_count || 400}" style="width:58px;font-size:11px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);padding:2px" min="100" max="2000" onchange="onSubWordChange(this, '${ss.id}', '${s.id}')"><span style="font-size:11px;color:var(--text-dim)">字</span>`}
            ${readOnly ? `<span style="font-size:11px;color:var(--text-dim)">${ss.word_count || ''}字</span>` : ''}
            ${ss.status === 'done' ? '<span style="font-size:11px;color:var(--green)">✓</span>' : ''}
            ${readOnly ? '' : `<button class="btn btn-sm btn-secondary" style="font-size:10px;padding:2px 6px" onclick="openAuxModal('${ss.id}')" title="辅助知识">+</button>`}
          </div>
          ${ss.summary ? `<div style="font-size:11px;color:var(--text-dim);margin-left:80px;margin-top:2px;line-height:1.3">${ss.summary}</div>` : ''}
        </div>`;
    });

    secHTML += `
      <div class="section-card" data-sid="${s.id}">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;width:100%">
          ${readOnly ? '' : `<input type="checkbox" class="sc-section-cb" ${s._checked !== false ? 'checked' : ''} onchange="onSectionToggle(this, '${s.id}')" style="flex-shrink:0">`}
          <div class="sc-label" style="flex:1">${s.title} ${s.type === 'leaf' ? '<span style="font-size:10px;color:#f39c12;background:rgba(243,156,18,0.15);padding:1px 5px;border-radius:3px;margin-left:4px">LEAF</span>' : '<span style="font-size:10px;color:#5dade2;background:rgba(93,173,226,0.15);padding:1px 5px;border-radius:3px;margin-left:4px">SEC</span>'}${readOnly ? (s.is_key ? ' <span class="sc-key">⭐重点</span>' : '') : ''} ${statusIcon}</div>
          <div class="sc-meta">${s.subtitle || ''}</div>
          ${readOnly ? `<span style="font-size:12px;color:var(--text-dim)">${s.status === 'done' ? s.actual_word_count + '字' : (s.status === 'in_progress' ? '写作中...' : '')}</span>` : ''}
          ${readOnly ? '' : `<label style="font-size:12px;color:var(--sc-key);cursor:pointer"><input type="checkbox" class="sc-key-cb" ${s.is_key ? 'checked' : ''} onchange="collectOutlineData()"> ⭐重点</label>`}
          ${readOnly ? '' : `<select class="sc-order" onchange="collectOutlineData()">${orderOpts}</select>`}
          ${readOnly ? '' : (s.type === 'leaf'
            ? `<input type="number" class="sec-word-input" data-sid="${s.id}" value="${s.word_count || 800}" style="width:58px;font-size:11px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--text);padding:2px" min="50" max="5000" onchange="onLeafWordChange(this, '${s.id}')"><span style="font-size:13px;color:var(--text-dim)">字</span>`
            : `<span class="sec-word-sum" data-sid="${s.id}" style="font-size:13px;color:var(--text-dim)">${s.word_count}</span><span style="font-size:13px;color:var(--text-dim)">字</span>`)}
          ${readOnly ? '' : `<label class="sc-rag"><input type="checkbox" class="sc-rag-cb" onchange="onRagToggle(this, '${s.id}')" ${!ragOnline ? 'disabled title="RAG未连接"' : ''}> RAG</label>` + (ragOnline && Array.isArray(ragKbs) ? `<select class="sc-kb" style="display:none;width:120px;font-size:12px" onchange="collectOutlineData()">${'<option value=\"\">自动KB</option>' + ragKbs.map(k => '<option value=\"' + k + '\">' + k + '</option>').join('')}</select>` : '')}
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
  // 重新计算章节字数
  recalcSectionWordSum(sectionId);
  collectOutlineData();
}

function onSubToggle(cb, sectionId) {
  // 重新计算章节字数（取消的子结构不计入）
  recalcSectionWordSum(sectionId);
  collectOutlineData();
}

function recalcSectionWordSum(secId) {
  const card = document.getElementById('outline-card');
  if (!card || !currentOutline) return;
  const sec = currentOutline.sections.find(s => s.id === secId);
  if (!sec) return;
  const sc = card.querySelector(`.section-card[data-sid="${secId}"]`);
  if (!sc) return;
  let sum = 0;
  sc.querySelectorAll('.sub-card').forEach(sub => {
    const subCb = sub.querySelector('.sc-sub-cb');
    if (subCb && !subCb.checked) return;  // 未勾选的子结构不计入
    const wordEl = sub.querySelector('.sub-words');
    sum += parseInt(wordEl?.value) || 0;
  });
  sec.word_count = sum;
  const sumEl = sc.querySelector('.sec-word-sum');
  if (sumEl) sumEl.textContent = sum;
}

// ===== 子结构字数编辑 =====
function onSubWordChange(el, subId, secId) {
  const val = parseInt(el.value) || 400;
  if (currentOutline) {
    const sec = currentOutline.sections.find(s => s.id === secId);
    if (sec) {
      const sub = sec.sub_sections.find(ss => ss.id === subId);
      if (sub) sub.word_count = val;
    }
  }
  recalcSectionWordSum(secId);
  collectOutlineData();
}

// ===== 辅助知识模态框 =====
let _auxModalSubId = null;

function openAuxModal(subId) {
  _auxModalSubId = subId;
  const overlay = document.getElementById('aux-modal');
  const textarea = document.getElementById('aux-text-input');
  const fileList = document.getElementById('aux-file-list');
  textarea.value = '';
  fileList.innerHTML = '';
  if (currentOutline) {
    for (const sec of currentOutline.sections) {
      for (const ss of sec.sub_sections || []) {
        if (ss.id === subId && ss.aux_knowledge) {
          textarea.value = ss.aux_knowledge.text || '';
          if (ss.aux_knowledge.files) {
            ss.aux_knowledge.files.forEach((f, i) => {
              fileList.innerHTML += `<div class="file-item"><span>${f.name}</span><span class="file-del" onclick="removeAuxFile(${i})">&times;</span></div>`;
            });
          }
          break;
        }
      }
    }
  }
  overlay.classList.add('show');
}

function closeAuxModal() {
  document.getElementById('aux-modal').classList.remove('show');
  _auxModalSubId = null;
}

function onAuxFilesSelected(event) {
  const fileList = document.getElementById('aux-file-list');
  Array.from(event.target.files).forEach(file => {
    if (!file.name.endsWith('.txt') && !file.name.endsWith('.md')) return;
    const reader = new FileReader();
    reader.onload = function(e) {
      if (currentOutline && _auxModalSubId) {
        for (const sec of currentOutline.sections) {
          for (const ss of sec.sub_sections || []) {
            if (ss.id === _auxModalSubId) {
              if (!ss.aux_knowledge) ss.aux_knowledge = {text: '', files: []};
              if (!ss.aux_knowledge.files) ss.aux_knowledge.files = [];
              const idx = ss.aux_knowledge.files.findIndex(f => f.name === file.name);
              if (idx >= 0) ss.aux_knowledge.files[idx].content = e.target.result;
              else ss.aux_knowledge.files.push({name: file.name, content: e.target.result});
              break;
            }
          }
        }
      }
      fileList.innerHTML += `<div class="file-item"><span>${file.name}</span><span class="file-del" onclick="removeAuxFile(${document.querySelectorAll('#aux-file-list .file-item').length})">&times;</span></div>`;
    };
    reader.readAsText(file);
  });
  event.target.value = '';
}

function removeAuxFile(idx) {
  if (currentOutline && _auxModalSubId) {
    for (const sec of currentOutline.sections) {
      for (const ss of sec.sub_sections || []) {
        if (ss.id === _auxModalSubId && ss.aux_knowledge && ss.aux_knowledge.files) {
          ss.aux_knowledge.files.splice(idx, 1);
          break;
        }
      }
    }
  }
  const fileList = document.getElementById('aux-file-list');
  const items = fileList.querySelectorAll('.file-item');
  if (items[idx]) items[idx].remove();
}

function saveAuxModal() {
  const text = document.getElementById('aux-text-input').value.trim();
  if (!currentOutline || !_auxModalSubId) { closeAuxModal(); return; }
  for (const sec of currentOutline.sections) {
    for (const ss of sec.sub_sections || []) {
      if (ss.id === _auxModalSubId) {
        if (!ss.aux_knowledge) ss.aux_knowledge = {text: '', files: []};
        ss.aux_knowledge.text = text;
        break;
      }
    }
  }
  closeAuxModal();
}

function collectAuxKnowledge() {
  const result = {};
  if (!currentOutline) return result;
  for (const sec of currentOutline.sections) {
    for (const ss of sec.sub_sections || []) {
      if (ss.aux_knowledge && (ss.aux_knowledge.text || (ss.aux_knowledge.files && ss.aux_knowledge.files.length))) {
        result[ss.id] = ss.aux_knowledge;
      }
    }
  }
  return result;
}

// ===== 停止生成 =====
function stopGeneration(type) {
  if (!currentSessionId) return;
  fetch('/api/stop', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({session_id: currentSessionId, type: type})
  }).then(r => r.json()).then(d => {
    if (d.success) {
      document.getElementById('stop-bar').style.display = 'none';
      addAssistantMsg('⏹ 已请求' + (type === 'immediate' ? '立即' : '延时') + '停止，等待当前段落完成后生效...');
    }
  });
}

function getOutlineData() {
  const card = document.getElementById('outline-card');
  if (!card) return null;
  const orders = {};
  const rag = {};
  const keySections = {};
  const checked = {};  // {sectionId: bool, subId: bool}
  const subOrders = {}; // {subId: int}
  const subWords = {}; // {subId: word_count}
  const secWords = {}; // {sectionId: word_count} for leaf sections
  const auxKnowledge = currentOutline ? collectAuxKnowledge() : {};
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

    // 子结构 checkbox + 排序 + 字数 + 辅助知识
    sc.querySelectorAll('.sub-card').forEach(sub => {
      const subCb = sub.querySelector('.sc-sub-cb');
      if (subCb) checked[sub.dataset.sid] = subCb.checked;
      const subOrder = sub.querySelector('.sc-sub-order')?.value;
      if (subOrder) subOrders[sub.dataset.sid] = subOrder;
      const subWord = sub.querySelector('.sub-words')?.value;
      if (subWord) subWords[sub.dataset.sid] = parseInt(subWord) || 400;
    });
    // leaf 节字数（允许 0 = 不做字数限制）
    const secWord = sc.querySelector('.sec-word-input')?.value;
    if (secWord !== undefined && secWord !== '') secWords[sid] = parseInt(secWord) || 0;
  });
  return {orders, rag, keySections, checked, subOrders, subWords, secWords, auxKnowledge};
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
      sub_orders: data?.subOrders || {},
      sub_words: data?.subWords || {},
      sec_words: data?.secWords || {},
      aux_knowledge: data?.auxKnowledge || {}
    })
  }).then(r => r.json()).then(d => {
    if (d.success) {
      msgEl.querySelector('.msg-content').innerHTML = '⏳ 生成任务已启动，正在写作...';
      document.getElementById('stop-bar').style.display = '';
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

// ===== 自动撰写 + 批量撰写 =====
function startAutoGeneration() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  const lines = text.split('\n').map(l => l.trim()).filter(l => l);
  if (lines.length === 0) return;

  if (lines.length === 1) {
    // 单篇自动：plan → 全量RAG → generate → 轮询
    input.value = '';
    const statusEl = addAssistantMsg('⏳ 自动撰写中（规划中...）');
    // 带 RAG 状态发 plan
    const meta = {};
    document.querySelectorAll('#meta-inputs-container .meta-field-input').forEach(el => {
      const val = el.value.trim();
      if (val) meta[el.dataset.fieldName] = val;
    });
    const templateName = document.getElementById('template-select').value;
    fetch('/api/plan', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({topic: text, session_id: currentSessionId, template_name: templateName, meta: meta})
    }).then(r => r.json()).then(d => {
      if (!d.success) {
        statusEl.querySelector('.msg-content').innerHTML = '❌ 规划失败：' + (d.error || '');
        return;
      }
      currentSessionId = d.session_id;
      currentOutline = d.outline;
      // 全量自动 RAG：所有节+子结构启用
      const autoRag = {};
      (d.outline.sections || []).forEach(s => {
        autoRag[s.id] = {enabled: ragOnline, kb: ''};
      });
      statusEl.querySelector('.msg-content').innerHTML = '⏳ 自动撰写中（写作中...）';
      fetch('/api/generate', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          session_id: currentSessionId,
          rag: autoRag,
          sub_words: {},
          aux_knowledge: {}
        })
      }).then(r2 => r2.json()).then(d2 => {
        if (d2.success) {
          startProgressPolling(currentSessionId);
          loadSessions();
        } else {
          statusEl.querySelector('.msg-content').innerHTML = '❌ 生成失败：' + (d2.error || '');
        }
      });
    }).catch(err => {
      statusEl.querySelector('.msg-content').innerHTML = '❌ 请求失败：' + err.message;
    });
  } else {
    // 批量自动：发到后端逐个处理
    input.value = '';
    addAssistantMsg('⏳ 批量自动撰写已启动（共 ' + lines.length + ' 篇）...');
    document.getElementById('batch-progress').style.display = '';
    document.getElementById('batch-progress').innerHTML = '批量进度：0/' + lines.length;
    const templateName = document.getElementById('template-select').value;
    const meta = {};
    document.querySelectorAll('#meta-inputs-container .meta-field-input').forEach(el => {
      const val = el.value.trim();
      if (val) meta[el.dataset.fieldName] = val;
    });
    fetch('/api/batch_auto', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({topics: lines, prompt: '', template_name: templateName, meta: meta})
    }).then(r => r.json()).then(d => {
      if (d.success) {
        const batchId = d.task_id;
        startBatchPolling(batchId, lines.length);
      } else {
        document.getElementById('batch-progress').innerHTML = '❌ 批量启动失败：' + (d.error || '');
      }
    });
  }
}

function startBatchPolling(batchId, totalCount) {
  if (window._batchPollTimer) clearInterval(window._batchPollTimer);
  window._batchPollTimer = setInterval(() => {
    fetch(`/api/batch_progress?task_id=${batchId}`)
      .then(r => r.json()).then(d => {
        if (!d.success) { clearInterval(window._batchPollTimer); return; }
        const done = d.done || 0;
        const progEl = document.getElementById('batch-progress');
        if (progEl) {
          let html = `批量进度：${done}/${d.total}`;
          if (d.current_topic) html += ` &nbsp; 当前：${d.current_topic}`;
          if (d.errors && d.errors.length) html += ` &nbsp; <span style="color:var(--accent)">错误：${d.errors.length}</span>`;
          progEl.innerHTML = html;
        }
        if (d.done_flag) {
          clearInterval(window._batchPollTimer);
          window._batchPollTimer = null;
          // 显示结果
          let resultMsg = `✅ 批量完成！${d.done}/${d.total} 篇成功`;
          const errors = d.errors || [];
          if (errors.length) {
            resultMsg += `\n❌ ${errors.length} 篇失败：\n` + errors.map(e => `  - ${e.topic}: ${e.error}`).join('\n');
          }
          addAssistantMsg(resultMsg);
          if (d.results && d.results.length) {
            d.results.forEach(r => {
              if (r.output_file) {
                const fname = r.output_file.split('/').pop() || r.output_file.split('\\').pop();
                addAssistantMsg(`📄 ${r.topic || '文章'} → ${fname}（${r.word_count || 0}字）`);
              }
            });
          }
          const progEl2 = document.getElementById('batch-progress');
          if (progEl2) progEl2.style.display = 'none';
          loadSessions();
        }
      }).catch(() => {});
  }, 1500);
}

function replanOutline() {
  document.getElementById('replan-hints').value = '';
  document.getElementById('replan-modal-status').textContent = '';
  document.getElementById('replan-modal').classList.add('show');
}

function onLeafWordChange(input, sid) {
  const val = parseInt(input.value);
  if (isNaN(val)) return;
  if (!currentOutline) return;
  const sec = (currentOutline.sections || []).find(s => s.id === sid);
  if (sec) { sec.word_count = val; }
  collectOutlineData();
}

function closeReplanModal() {
  document.getElementById('replan-modal').classList.remove('show');
}

function confirmReplan() {
  const hints = document.getElementById('replan-hints').value.trim();
  closeReplanModal();
  const topic = currentOutline?.title || '';
  if (!topic) return;
  addAssistantMsg(hints ? '⏳ 正在按新要求重新规划...' : '⏳ 正在重新规划...');
  const meta = {};
  document.querySelectorAll('#meta-inputs-container .meta-field-input').forEach(el => {
    const val = el.value.trim();
    if (val) meta[el.dataset.fieldName] = val;
  });
  const templateName = document.getElementById('template-select').value;
  fetch('/api/plan', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({topic, session_id: currentSessionId, template_name: templateName, meta, plan_hints: hints})
  }).then(r => r.json()).then(d => {
    if (d.success) {
      currentSessionId = d.session_id;
      currentOutline = d.outline;
      renderOutline(d.outline);
      loadSessions();
    } else {
      addAssistantMsg('❌ 重新规划失败：' + (d.error || ''));
    }
  }).catch(err => {
    addAssistantMsg('❌ 请求失败：' + err.message);
  });
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
  const bar = document.getElementById('stop-bar');
  if (bar) bar.style.display = 'none';
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

<!-- 辅助知识模态框 -->
<div class="modal-overlay" id="aux-modal">
  <div class="modal-box">
    <div class="modal-header">
      <h3>辅助知识</h3>
      <button class="modal-close" onclick="closeAuxModal()">&times;</button>
    </div>
    <div class="modal-body">
      <label style="font-size:12px;color:var(--text-dim);display:block;margin-bottom:4px">文本内容：</label>
      <textarea id="aux-text-input" placeholder="输入参考文本，或上传 .txt/.md 文件..."></textarea>
      <div class="file-upload-area" onclick="document.getElementById('aux-file-input').click()">
        + 上传文件（.txt / .md）
      </div>
      <input type="file" id="aux-file-input" accept=".txt,.md" style="display:none" multiple onchange="onAuxFilesSelected(event)">
      <div class="file-list" id="aux-file-list"></div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeAuxModal()">取消</button>
      <button class="btn btn-primary" onclick="saveAuxModal()">保存</button>
    </div>
  </div>
</div>

</body>
</html>"""


def run_server(host="0.0.0.0", port=8770):
    """启动 HTTP 服务器"""
    cfg = ConfigManager()
    StructuredWriterHandler.config_mgr = cfg
    server = ThreadingHTTPServer((host, port), StructuredWriterHandler)
    print(f"[Structured Writer] 服务启动: http://{host}:{port}")
    print(f"[Structured Writer] 配置面板: http://localhost:{port} (配置Tab)")
    print(f"[Structured Writer] 写作界面: http://localhost:{port} (对话Tab)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Structured Writer] 服务停止")
        server.server_close()
