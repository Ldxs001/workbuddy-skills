"""
rag-assistant Web 界面
含配置管理 + 对话窗口，两 Tab 切换
配置 Tab 嵌入 local-rag-builder 的完整配置界面
"""
import os
import sys
import json
import logging
import http.server
import urllib.parse
import socketserver
from typing import Optional
from threading import Thread

from .agent import BUILTIN_QUERY_TYPES as _BUILTIN_QUERY_TYPES

logger = logging.getLogger(__name__)

# ── 使用本地 engine/ 副本（自包含） ─────────────
ENGINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine")
if ENGINE_PATH not in sys.path:
    sys.path.insert(0, ENGINE_PATH)

try:
    from prompt_manager import get_full_prompt, PROMPT_PRESETS
    from config import load_config, save_config
    SKILL_AVAILABLE = True
except ImportError:
    SKILL_AVAILABLE = False
    logger.warning("无法导入 local-rag-builder 配置模块")


class AssistantHandler(http.server.BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    # ── 类变量（由外部注入） ──────────────────────
    agent = None
    main_port = 8765
    rag_port = 8766

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_main_page()
        elif path == "/api/config":
            self._serve_config()
        elif path == "/api/kbs":
            self._serve_kbs()
        elif path == "/api/llm/models":
            self._serve_llm_models(parsed.query)
        elif path == "/api/llm/test":
            self._serve_llm_test()
        elif path == "/api/config/llm":
            self._serve_llm_config_get()
        elif path == "/api/config/search":
            self._serve_search_config_get()
        elif path == "/api/config/query_types":
            self._serve_query_types()
        elif path == "/api/agent/gaps":
            self._serve_agent_gaps()
        elif path.startswith("/api/agent/query"):
            self._handle_agent_query(parsed.query)
        elif path == "/api/chat/history":
            self._handle_chat_history()
        elif path.startswith("/api/chat"):
            self._handle_chat_get(parsed)
        elif path == "/api/session/new":
            self._handle_session_new()
        elif path == "/api/session/list":
            self._handle_session_list()
        elif path == "/api/session/switch":
            self._handle_session_switch()
        elif path == "/api/session/archive":
            self._handle_session_archive()
        elif path == "/api/session/restore":
            self._handle_session_restore()
        elif path == "/api/session/delete":
            self._handle_session_delete()
        elif path == "/api/config/memory":
            self._serve_memory_config()
        elif path == "/api/memory/reset":
            self._reset_memory()
        elif path == "/api/memory/compress":
            self._compress_memory()
        elif path == "/api/memory/clear-context":
            self._clear_context()
        elif path.startswith("/static/"):
            self._serve_static(path)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/chat":
            self._handle_chat_post()
        elif path == "/api/agent/query":
            self._handle_agent_query_post()
        elif path == "/api/agent/import":
            self._handle_agent_import()
        elif path == "/api/agent/upload-files":
            self._handle_agent_upload_files()
        elif path == "/api/memory/inject":
            self._handle_memory_inject()
        elif path == "/api/config/llm":
            self._update_llm_config()
        elif path == "/api/config/search":
            self._update_search_config()
        elif path == "/api/config/memory":
            self._update_memory_config()
        elif path == "/api/search/toggle":
            self._toggle_search()
        elif path == "/api/config/query_types":
            self._update_query_types()
        elif path == "/api/memory/compress":
            self._compress_memory()
        elif path == "/api/memory/clear-context":
            self._clear_context()
        elif path == "/api/session/new":
            self._handle_session_new()
        elif path == "/api/session/switch":
            self._handle_session_switch()
        elif path == "/api/session/archive":
            self._handle_session_archive()
        elif path == "/api/session/restore":
            self._handle_session_restore()
        elif path == "/api/session/delete":
            self._handle_session_delete()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def _send_json(self, data: dict, status: int = 200):
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def _send_html(self, html: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    # ── 页面 ──────────────────────────────────────

    def _serve_static(self, path):
        import mimetypes
        rel_path = path.lstrip("/")
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", rel_path)
        if not os.path.isfile(file_path):
            self.send_response(404)
            self.end_headers()
            return
        ext = os.path.splitext(file_path)[1]
        mime = mimetypes.types_map.get(ext, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "max-age=3600")
        self.end_headers()
        with open(file_path, "rb") as f:
            self.wfile.write(f.read())

    def _serve_main_page(self):
        import time
        rag_port = type(self).rag_port
        config_html = self._render_config_tab() if SKILL_AVAILABLE else "<p>技能模块未加载</p>"
        chat_html = ""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>RAG 智能助手</title>
<link rel="icon" href="data:,">
<script src="/static/marked.min.js"></script>
<link rel="stylesheet" href="/static/katex.min.css">
<script src="/static/katex.min.js"></script>
<script src="/static/auto-render.min.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f6fa; color: #333; }}
.tabs {{ display: flex; background: #fff; border-bottom: 1px solid #e0e0e0; position: sticky; top: 0; z-index: 100; }}
.tab {{ padding: 14px 28px; cursor: pointer; font-size: 14px; font-weight: 500; color: #888; border-bottom: 2px solid transparent; transition: all 0.2s; }}
.tab:hover {{ color: #555; }}
.tab.active {{ color: #667eea; border-bottom-color: #667eea; }}
/* 配置 Tab — display 由 JS 直接控制 style.display，不依赖 class */
#config-content.tab-content {{ display: block; padding: 16px; }}
#chat-content {{ display: none; height: calc(100vh - 48px); }}
/* ── 侧边栏 ── */
#sidebar {{ width: 260px; background: #f8f9fa; border-right: 1px solid #dee2e6; display: flex; flex-direction: column; flex-shrink: 0; }}
#sidebar-header {{ padding: 12px; border-bottom: 1px solid #dee2e6; }}
#sidebar-list {{ flex: 1; overflow-y: auto; padding: 4px; }}
.sidebar-item {{ display: flex; align-items: center; padding: 8px 12px; cursor: pointer; border-radius: 6px; margin: 2px 4px; font-size: 13px; }}
.sidebar-item:hover {{ background: #e9ecef; }}
.sidebar-item.active {{ background: #e8eaf6; color: #283593; }}
.sidebar-item.archived {{ opacity: 0.5; }}
.sidebar-item .preview {{ flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-left: 6px; font-size: 12px; color: #888; }}
.sidebar-item .s-btn {{ padding: 2px 6px; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; flex-shrink: 0; }}
.sidebar-item .archive-btn {{ background: transparent; color: #999; }}
.sidebar-item .archive-btn:hover {{ background: #f0f0f0; color: #d32f2f; }}
.sidebar-item .restore-btn {{ background: transparent; color: #999; }}
.sidebar-item .restore-btn:hover {{ background: #f0f0f0; color: #667eea; }}
/* ── Chat panel（对话容器） ── */
#chat-panel {{ flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }}
.chat-messages {{ flex: 1; overflow-y: auto; padding: 20px; background: #f5f6fa; }}
.msg {{ position: relative; max-width: 80%; margin-bottom: 16px; padding: 12px 16px; border-radius: 12px; line-height: 1.6; font-size: 14px; white-space: pre-wrap; }}
.msg.user {{ background: #667eea; color: #fff; margin-left: auto; border-radius: 12px 12px 4px 12px; }}
.msg.assistant {{ background: #fff; color: #333; border: 1px solid #e0e0e0; margin-right: auto; border-radius: 12px 12px 12px 4px; }}
.msg.assistant p {{ margin: 4px 0; }}
.msg.assistant ul, .msg.assistant ol {{ margin: 4px 0; padding-left: 20px; }}
.msg.assistant code {{ background: #f0f0f5; padding: 1px 4px; border-radius: 3px; font-size: 13px; }}
.msg.assistant pre {{ background: #f5f5f5; padding: 10px; border-radius: 6px; overflow-x: auto; margin: 6px 0; }}
.msg.assistant pre code {{ background: none; padding: 0; }}
.msg.assistant table {{ border-collapse: collapse; margin: 6px 0; font-size: 13px; }}
.msg.assistant th, .msg.assistant td {{ border: 1px solid #ddd; padding: 4px 8px; text-align: left; }}
.msg.assistant th {{ background: #f5f5fa; }}
.msg.assistant blockquote {{ border-left: 3px solid #667eea; margin: 6px 0; padding: 4px 12px; color: #555; }}
.msg.system {{ background: #fff3cd; color: #856404; text-align: center; font-size: 12px; max-width: 100%; }}
.chat-input {{ display: flex; gap: 8px; padding: 12px 20px; background: #fff; border-top: 1px solid #e0e0e0; flex-shrink: 0; }}
.chat-input textarea {{ flex: 1; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; resize: none; font-size: 14px; outline: none; }}
.chat-input textarea:focus {{ border-color: #667eea; }}
.chat-input button {{ padding: 10px 24px; background: #667eea; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }}
.chat-input button:hover {{ background: #5a6fd6; }}
.chat-input button:disabled {{ background: #ccc; cursor: not-allowed; }}
.modal-btn-primary {{ padding:8px 20px;background:#d32f2f;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500; }}
.modal-btn-primary:hover {{ background:#b71c1c; }}
.modal-btn {{ padding:8px 20px;background:#f0f0f0;color:#555;border:none;border-radius:6px;cursor:pointer;font-size:13px; }}
.modal-btn:hover {{ background:#e0e0e0; }}
/* ── 标记渲染 ── */
.msg.assistant h1, .msg.assistant h2, .msg.assistant h3, .msg.assistant h4 {{ margin: 0.5em 0 0.25em; }}
.msg.assistant h1 {{ font-size: 1.3em; }} .msg.assistant h2 {{ font-size: 1.15em; }} .msg.assistant h3 {{ font-size: 1.05em; }}
.msg.assistant p {{ margin: 0.4em 0; }}
.msg.assistant table {{ border-collapse: collapse; margin: 0.5em 0; font-size: 13px; width: 100%; }}
.msg.assistant th, .msg.assistant td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; }}
.msg.assistant th {{ background: #f0f0f5; font-weight: 600; }}
.msg.assistant code {{ background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 0.95em; }}
.msg.assistant pre {{ background: #f5f5f5; padding: 10px; border-radius: 6px; overflow-x: auto; margin: 0.5em 0; }}
.msg.assistant blockquote {{ border-left: 3px solid #667eea; margin: 0.5em 0; padding: 4px 12px; color: #666; }}
.msg.assistant ul, .msg.assistant ol {{ margin: 0.3em 0; padding-left: 1.5em; }}
.msg.assistant li {{ margin: 0.15em 0; }}
/* ── 推理链 ── */
.reasoning-toggle {{ font-size: 12px; color: #888; cursor: pointer; margin-top: 8px; padding: 2px 0; user-select: none; }}
.reasoning-toggle:hover {{ color: #667eea; }}
.reasoning-body {{ font-size: 12px; color: #666; background: #f8f8fc; border-left: 2px solid #667eea; padding: 8px 12px; margin-top: 4px; border-radius: 0 6px 6px 0; white-space: pre-wrap; line-height: 1.5; position: relative; }}
/* ── 复制按钮 ── */
.copy-btn {{ position: absolute; top: 6px; right: 6px; background: transparent; border: none; cursor: pointer; font-size: 12px; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.85); color: #888; }}
.copy-btn:hover {{ color: #667eea; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
.msg.user .copy-btn {{ color: rgba(255,255,255,0.7); background: rgba(255,255,255,0.12); }}
.msg.user .copy-btn:hover {{ color: #fff; background: rgba(255,255,255,0.25); }}
/* ── 公式 ── */
.msg.assistant .katex {{ font-size: 1em; }}
.msg.assistant .katex-display {{ margin: 0.5em 0; overflow-x: auto; overflow-y: hidden; }}
/* ── 加载动画 ── */
@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
</style>
</head>
<body>
<div class="tabs">
  <div class="tab active" onclick="switchTab('config')">⚙️ 配置</div>
  <div class="tab" onclick="switchTab('chat')">💬 对话</div>
</div>
<div id="config-content" class="tab-content" style="display:block;">
  {config_html}
</div>
<div id="chat-content" style="display:none;">
  <div id="sidebar">
    <div id="sidebar-header">
      <button onclick="newSession()" style="width:100%;padding:8px;background:#667eea;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;">➕ 新建对话</button>
    </div>
    <div id="sidebar-list"></div>
    <div id="sidebar-archived" style="display:none;border-top:1px solid #dee2e6;">
      <div onclick="toggleArchived()" style="padding:8px 12px;cursor:pointer;font-size:12px;color:#888;user-select:none;">
        <span id="archived-toggle">▸</span> 归档会话 (<span id="archived-count">0</span>)
      </div>
      <div id="sidebar-archived-list"></div>
    </div>
  </div>
  <div id="chat-panel">
    <div class="chat-messages" id="chat-messages">
      <div class="msg assistant">你好！我是 RAG 知识库助手。<br>输入问题直接问，📄📁 选择文件入库，/import 路径导入。</div>
    </div>
    <div class="chat-input">
      <input type="file" id="file-input" multiple style="display:none" onchange="onFileSelected(this.files)">
      <input type="file" id="folder-input" webkitdirectory style="display:none" onchange="onFolderSelected(this.files)">
      <button onclick="document.getElementById('file-input').click()" style="padding:8px 14px;background:#f0f0f5;border:1px solid #ddd;border-radius:8px;cursor:pointer;font-size:13px;">📄</button>
      <button onclick="document.getElementById('folder-input').click()" style="padding:8px 14px;background:#f0f0f5;border:1px solid #ddd;border-radius:8px;cursor:pointer;font-size:13px;">📁</button>
      <div id="file-status" style="display:none;flex:0 0 auto;max-width:260px;padding:6px 10px;background:#e8f5e9;border:1px solid #c8e6c9;border-radius:6px;font-size:12px;color:#2e7d32;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"></div>
      <textarea id="chat-input" rows="2" placeholder="输入问题或提问文件内容..."></textarea>
      <button id="send-btn" onclick="sendMessage()">发送</button>
    </div>
  </div>
</div>

<!-- 模态弹窗 -->
<div id="modal-overlay" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.45);z-index:9999;align-items:center;justify-content:center;">
  <div id="modal-box" style="background:#fff;border-radius:12px;padding:24px;min-width:320px;max-width:480px;box-shadow:0 8px 32px rgba(0,0,0,0.2);">
    <div id="modal-title" style="font-size:16px;font-weight:600;color:#333;margin-bottom:12px;"></div>
    <div id="modal-msg" style="font-size:14px;color:#555;margin-bottom:20px;line-height:1.5;"></div>
    <div id="modal-buttons" style="display:flex;gap:8px;justify-content:flex-end;"></div>
  </div>
</div>

<script>
// ── Tab 切换：style.display 直接控制，不依赖 CSS class ──
function switchTab(name) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab')[name === 'config' ? 0 : 1].classList.add('active');
  document.getElementById('config-content').style.display = name === 'config' ? 'block' : 'none';
  document.getElementById('chat-content').style.display = name === 'chat' ? 'flex' : 'none';
  if (name === 'chat') setTimeout(function(){{var el=document.getElementById('chat-input');if(el)el.focus();}},100);
}}

// ── 会话管理 ──
function newSession() {{
  fetch('/api/session/new', {{method:'POST'}}).then(function(r){{return r.json()}}).then(function(d){{
    if(d.success) {{
      document.getElementById('chat-messages').innerHTML = '<div class="msg assistant">新建对话「' + d.id + '」</div>';
      loadSessions();
    }}
  }});
}}

function switchSession(id) {{
  fetch('/api/session/switch', {{
    method:'POST', headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{id: id}})
  }}).then(function(r){{return r.json()}}).then(function(d){{
    if(d.success) {{
      var container = document.getElementById('chat-messages');
      container.innerHTML = '';
      if(d.messages && d.messages.length) {{
        d.messages.forEach(function(m){{ addMessage(m.content, m.role, null, m.reasoning || null); }});
      }} else {{
        container.innerHTML = '<div class="msg assistant">空对话。</div>';
      }}
      loadSessions();
    }}
  }});
}}

function archiveSession(id) {{
  showModal('归档确认', '将会话归档？（数据不丢失，可在归档列表恢复）', [
    {{text:'取消',action:function(){{}}}},
    {{text:'归档',primary:true,action:function(){{fetch('/api/session/archive', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:id}})}}).then(function(r){{return r.json()}}).then(function(d){{if(d.success) loadSessions();}});}}}}
  ]);
}}

function restoreSession(id) {{
  fetch('/api/session/restore', {{
    method:'POST', headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{id: id}})
  }}).then(function(r){{return r.json()}}).then(function(d){{
    if(d.success) loadSessions();
  }});
}}

function deleteSession(id) {{
  showModal('删除确认', '确定永久删除此会话？不可恢复！', [
    {{text:'取消',action:function(){{}}}},
    {{text:'删除',primary:true,action:function(){{fetch('/api/session/delete', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:id}})}}).then(function(r){{return r.json()}}).then(function(d){{if(d.success) loadSessions();}});}}}}
  ]);
}}

function loadSessions() {{
  fetch('/api/session/list').then(function(r){{return r.json()}}).then(function(d){{
    if(!d.success) return;
    var list = document.getElementById('sidebar-list');
    var archList = document.getElementById('sidebar-archived-list');
    list.innerHTML = '';
    archList.innerHTML = '';
    var active = 0, archived = 0;
    d.sessions.forEach(function(s){{
      var item = document.createElement('div');
      item.className = 'sidebar-item' + (s.active ? ' active' : '') + (s.archived ? ' archived' : '');
      var label = document.createElement('span');
      label.textContent = s.preview || '(空)';
      label.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;';
      item.appendChild(label);
      item.onclick = function(){{ if(!s.active) switchSession(s.id); }};
      if(s.archived) {{
        var rb = document.createElement('button');
        rb.textContent = '↩';
        rb.className = 's-btn restore-btn';
        rb.title = '恢复';
        rb.onclick = function(e){{ e.stopPropagation(); restoreSession(s.id); }};
        item.appendChild(rb);
        archList.appendChild(item);
        archived++;
      }} else {{
        var ab = document.createElement('button');
        ab.textContent = '📦';
        ab.className = 's-btn archive-btn';
        ab.title = '归档';
        ab.onclick = function(e){{ e.stopPropagation(); archiveSession(s.id); }};
        item.appendChild(ab);
        list.appendChild(item);
        active++;
      }}
    }});
    document.getElementById('archived-count').textContent = archived;
    document.getElementById('sidebar-archived').style.display = archived > 0 ? 'block' : 'none';
  }});
}}

function toggleArchived() {{
  var list = document.getElementById('sidebar-archived-list');
  var toggle = document.getElementById('archived-toggle');
  var hidden = list.style.display === 'none' || list.style.display === '';
  list.style.display = hidden ? 'block' : 'none';
  toggle.textContent = hidden ? '▾' : '▸';
}}

// ── 对话 ──
let isStreaming = false;

function sendMessage() {{
  if (isStreaming) return;
  var input = document.getElementById('chat-input');
  var msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  addMessage(msg, 'user');
  addMessage('思考中...', 'assistant', 'thinking');
  isStreaming = true;
  document.getElementById('send-btn').disabled = true;

  fetch('/api/chat', {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{message: msg}})
  }}).then(function(r){{return r.json()}}).then(function(d){{
    var thinking = document.getElementById('thinking');
    if (thinking) thinking.remove();
    if (d.success) {{
      addMessage(d.text, 'assistant', null, d.reasoning);
    }} else {{
      addMessage('抱歉，处理出错：' + (d.error || '未知错误'), 'system');
    }}
    isStreaming = false;
    document.getElementById('send-btn').disabled = false;
    loadSessions();
  }}).catch(function(e){{
    var thinking = document.getElementById('thinking');
    if (thinking) thinking.remove();
    addMessage('网络错误：' + e.message, 'system');
    isStreaming = false;
    document.getElementById('send-btn').disabled = false;
  }});
}}

function addMessage(text, role, id, reasoning) {{
  var div = document.createElement('div');
  div.className = 'msg ' + role;
  if (id) div.id = id;

  if (role === 'assistant' && window.marked) {{
    div.innerHTML = marked.parse(text);
    if (window.renderMathInElement) {{
      try {{ renderMathInElement(div, {{delimiters:[
        {{left:'$$',right:'$$',display:true}},
        {{left:'$',right:'$',display:false}}
      ]}}); }} catch(e) {{}}
    }}
  }} else {{
    var escaped = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    div.innerHTML = escaped;
    if (window.renderMathInElement) {{
      try {{ renderMathInElement(div, {{delimiters:[
        {{left:'$$',right:'$$',display:true}},
        {{left:'$',right:'$',display:false}}
      ]}}); }} catch(e) {{}}
    }}
  }}

  var copyBtn = document.createElement('button');
  copyBtn.className = 'copy-btn';
  copyBtn.textContent = '📋';
  copyBtn.title = role === 'user' ? '复制问题' : '复制回答';
  copyBtn.onclick = function(e) {{
    e.stopPropagation();
    var txt = text;
    var rb = div.querySelector('.reasoning-body');
    if (rb && rb.style.display === 'block') txt += '\\n\\n' + (typeof reasoning === 'string' ? reasoning : rb.textContent.trim());
    navigator.clipboard.writeText(txt).then(function() {{
      copyBtn.textContent = '✓';
      setTimeout(function() {{ copyBtn.textContent = '📋'; }}, 1500);
    }}).catch(function() {{
      var r = document.createRange(); r.selectNodeContents(div);
      var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
    }});
  }};
  div.appendChild(copyBtn);

  if (reasoning) {{
    var toggle = document.createElement('div');
    toggle.className = 'reasoning-toggle';
    toggle.textContent = '🧠 推理过程 ▸';
    toggle.onclick = function() {{
      var body = div.querySelector('.reasoning-body');
      if (body) {{
        var hidden = body.style.display === 'block';
        body.style.display = hidden ? 'none' : 'block';
        toggle.textContent = hidden ? '🧠 推理过程 ▸' : '🧠 推理过程 ▾';
      }}
    }};
    var body = document.createElement('div');
    body.className = 'reasoning-body';
    body.style.display = 'none';
    var bodyTxt = document.createElement('div');
    bodyTxt.style.whiteSpace = 'pre-wrap';
    bodyTxt.textContent = reasoning;
    var rCopy = document.createElement('button');
    rCopy.className = 'copy-btn';
    rCopy.textContent = '📋';
    rCopy.title = '复制推理';
    rCopy.onclick = function(e) {{
      e.stopPropagation();
      navigator.clipboard.writeText(reasoning).then(function() {{
        rCopy.textContent = '✓';
        setTimeout(function() {{ rCopy.textContent = '📋'; }}, 1500);
      }});
    }};
    body.appendChild(rCopy);
    body.appendChild(bodyTxt);
    div.appendChild(toggle);
    div.appendChild(body);
  }}

  document.getElementById('chat-messages').appendChild(div);
  div.scrollIntoView({{behavior:'smooth', block:'end'}});
}}

document.getElementById('chat-input').addEventListener('keydown', function(e) {{
  if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); sendMessage(); }}
}});

// ── 模态弹窗 ──
function showModal(title, msg, buttons) {{
  var overlay = document.getElementById('modal-overlay');
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-msg').textContent = msg;
  var btns = document.getElementById('modal-buttons');
  btns.innerHTML = '';
  (buttons || [{{text:'确定',primary:true,action:function(){{hideModal();}}}}]).forEach(function(b){{
    var btn = document.createElement('button');
    btn.textContent = b.text;
    btn.className = b.primary ? 'modal-btn-primary' : 'modal-btn';
    btn.onclick = function(){{ if(b.action) b.action(); if(!b.keepOpen) hideModal(); }};
    btns.appendChild(btn);
  }});
  overlay.style.display = 'flex';
}}
function hideModal() {{
  document.getElementById('modal-overlay').style.display = 'none';
}}

// ── 上传 ──
var uploadedPaths = [];

function formatSize(bytes) {{
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}}

function onFileSelected(files) {{
  if (!files.length) return;
  addMessage('正在上传 ' + files.length + ' 个文件到服务器...', 'system', 'uploading');
  uploadToServer(Array.from(files));
}}

function onFolderSelected(files) {{
  if (!files.length) return;
  addMessage('正在上传 ' + files.length + ' 个文件到服务器...', 'system', 'uploading');
  uploadToServer(Array.from(files));
}}

function uploadToServer(files) {{
  var done = 0, total = files.length;
  var uploaded = [];
  function next(i) {{
    if (i >= files.length) {{
      var el = document.getElementById('uploading');
      if (el) el.remove();
      if (uploaded.length) {{
        var msg = '📦 已上传 ' + uploaded.length + ' 个文件到服务器，可以说「入库」批量导入';
        addMessage(msg, 'system');
        fetch('/api/memory/inject', {{
          method:'POST', headers:{{'Content-Type':'application/json'}},
          body:JSON.stringify({{text: uploaded.length + ' 个文件已上传到服务器'}})
        }});
      }}
      updateFileStatus();
      return;
    }}
    var file = files[i];
    var reader = new FileReader();
    reader.onload = function(e) {{
      var base64 = e.target.result.split(',')[1];
      fetch('/api/agent/upload-files', {{
        method:'POST', headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{name: file.name, data: base64}})
      }}).then(function(r){{return r.json()}}).then(function(d){{
        if (d.success && d.path) {{ uploadedPaths.push(d.path); uploaded.push(d.path); }}
        next(i + 1);
      }});
    }};
    reader.readAsDataURL(file);
  }}
  next(0);
}}

function updateFileStatus() {{
  var el = document.getElementById('file-status');
  if (!uploadedPaths.length) {{ el.style.display = 'none'; return; }}
  var names = uploadedPaths.map(function(p){{ return p.split('/').pop() || p.split('\\\\').pop(); }}).slice(0, 3).join(', ');
  el.textContent = '📦 已上传 ' + uploadedPaths.length + ' 个文件: ' + names;
  if (uploadedPaths.length > 3) el.textContent += ' ...';
  el.style.display = 'inline';
}}

// ── 初始化 ──
loadSessions();
(function loadChatHistory() {{
  fetch('/api/chat/history').then(function(r){{return r.json()}}).then(function(d){{
    if(d.success && d.messages && d.messages.length) {{
      var container = document.getElementById('chat-messages');
      container.innerHTML = '';
      d.messages.forEach(function(m){{ addMessage(m.content, m.role, null, m.reasoning || null); }});
    }}
  }});
}})();
</script>
</body>
</html>"""
        self._send_html(html)

    def _render_config_tab(self) -> str:
        """配置 Tab：LLM 设置 + RAG 配置 iframe"""
        import time
        rag_port = type(self).rag_port
        cfg = load_config() if SKILL_AVAILABLE else {}
        llm = cfg.get("llm", {})
        llm_backend = llm.get("backend", "ollama")
        llm_max_tokens = llm.get("max_tokens", 4096)
        llm_timeout = llm.get("timeout", 180)
        llm_model = llm.get("model", "")
        web_search = cfg.get("web_search_enabled", False)
        search = cfg.get("search", {})
        search_backend = search.get("backend", "duckduckgo")
        mem_cfg = cfg.get("memory", {})
        compress_ratio = mem_cfg.get("compress_ratio", 0.7)
        compress_remove_ratio = mem_cfg.get("compress_remove_ratio", 0.4)
        max_sessions = mem_cfg.get("max_sessions", 20)
        return f"""
        <div style="display:flex;flex-direction:column;gap:12px;">
          <!-- LLM 配置卡片 -->
          <div style="border:0.5px solid #e0e0e0;border-radius:10px;background:#fff;">
            <div onclick="togglePanel('llm-panel','llm-arrow')" style="padding:12px 16px;cursor:pointer;font-size:14px;font-weight:500;color:#444;user-select:none;display:flex;align-items:center;gap:6px;">
              <span id="llm-arrow">▾</span> LLM / 联网搜索
            </div>
            <div id="llm-panel" style="padding:0 16px 12px;">
              <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
                <select id="llm-backend" onchange="saveLLM();loadModels()" style="padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;">
                  <option value="ollama" {"selected" if llm_backend=='ollama' else ""}>Ollama</option>
                  <option value="lmstudio" {"selected" if llm_backend=='lmstudio' else ""}>LM Studio</option>
                </select>
                <select id="llm-model" onchange="saveLLM()" style="flex:1;min-width:200px;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;">
                  <option value="">-- 模型 --</option>
                </select>
                <input type="number" id="llm-timeout" value="{llm_timeout}" min="30" max="3600" step="30" onchange="saveLLM()" style="width:70px;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;" title="超时秒数">
                <input type="number" id="llm-maxtokens" value="{llm_max_tokens}" min="512" max="131072" step="1024" onchange="saveLLM()" style="width:90px;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;" title="最大输出token数">
                <button onclick="loadModels()" style="padding:6px 12px;background:#f0f0f5;border:1px solid #ddd;border-radius:6px;cursor:pointer;font-size:12px;">🔄</button>
                <button onclick="testLLM()" style="padding:6px 12px;background:#667eea;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;">测试</button>
                <label style="font-size:13px;display:flex;align-items:center;gap:4px;">
                  <input type="checkbox" id="web-search-enabled" onchange="toggleWebSearch()" {"checked" if web_search else ""} style="accent-color:#667eea;">
                  联网搜索
                </label>
                <span id="llm-status" style="font-size:12px;color:#888;"></span>
              </div>
              <div id="search-config" style="display:{'block' if web_search else 'none'};margin-top:8px;padding:8px 12px;background:#f8f9fc;border:1px solid #e0e0e0;border-radius:8px;">
                <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
                  <select id="search-backend" onchange="onSearchBackendChange()" style="padding:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:12px;">
                    <option value="duckduckgo" {"selected" if search_backend=='duckduckgo' else ""}>DuckDuckGo（免费）</option>
                    <option value="tavily" {"selected" if search_backend=='tavily' else ""}>Tavily（需 API Key）</option>
                    <option value="google" {"selected" if search_backend=='google' else ""}>Google Custom Search</option>
                    <option value="bing" {"selected" if search_backend=='bing' else ""}>Bing Search</option>
                    <option value="custom" {"selected" if search_backend=='custom' else ""}>自定义 API</option>
                  </select>
                  <div id="search-key-group" style="display:{'inline-block' if search_backend in ('tavily','custom') else 'none'};">
                    <input type="password" id="search-api-key" placeholder="API Key" value="{search.get('api_key','')}" onchange="saveSearchConfig()" style="padding:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:12px;width:200px;">
                  </div>
                  <div id="search-google-group" style="display:{'inline-block' if search_backend=='google' else 'none'};">
                    <input type="password" id="search-google-key" placeholder="Google API Key" value="{search.get('google_key','')}" onchange="saveSearchConfig()" style="padding:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:12px;width:160px;">
                    <input type="text" id="search-google-cx" placeholder="Search CX" value="{search.get('google_cx','')}" onchange="saveSearchConfig()" style="padding:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:12px;width:160px;">
                  </div>
                  <div id="search-bing-group" style="display:{'inline-block' if search_backend=='bing' else 'none'};">
                    <input type="password" id="search-bing-key" placeholder="Bing API Key" value="{search.get('bing_key','')}" onchange="saveSearchConfig()" style="padding:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:12px;width:200px;">
                  </div>
                  <div id="search-custom-group" style="display:{'inline-block' if search_backend=='custom' else 'none'};">
                    <input type="text" id="search-custom-url" placeholder="URL，用 {{q}} {{key}} 占位" value="{search.get('custom_url','')}" onchange="saveSearchConfig()" style="padding:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:12px;width:250px;">
                    <input type="password" id="search-custom-key" placeholder="API Key（可选）" value="{search.get('api_key','')}" onchange="saveSearchConfig()" style="padding:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:12px;width:150px;">
                  </div>
                  <span id="search-status" style="font-size:11px;color:#888;"></span>
                </div>
              </div>
            </div>
          </div>
          <!-- 记忆配置卡片 -->
          <div style="border:0.5px solid #e0e0e0;border-radius:10px;background:#fff;">
            <div onclick="togglePanel('mem-panel','mem-arrow')" style="padding:12px 16px;cursor:pointer;font-size:14px;font-weight:500;color:#444;user-select:none;display:flex;align-items:center;gap:6px;">
              <span id="mem-arrow">▾</span> 记忆 / 会话
            </div>
            <div id="mem-panel" style="padding:0 16px 12px;">
              <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:13px;">
                <label>压缩触发比例 <input type="number" id="mem-compress-ratio" value="{compress_ratio}" min="0.1" max="1.0" step="0.05" onchange="saveMemoryConfig()" style="width:64px;padding:4px 6px;border:1px solid #ddd;border-radius:4px;font-size:12px;"></label>
                <label>移出比例 <input type="number" id="mem-remove-ratio" value="{compress_remove_ratio}" min="0.1" max="0.9" step="0.05" onchange="saveMemoryConfig()" style="width:64px;padding:4px 6px;border:1px solid #ddd;border-radius:4px;font-size:12px;"></label>
                <label>最大会话数 <input type="number" id="mem-max-sessions" value="{max_sessions}" min="5" max="100" step="5" onchange="saveMemoryConfig()" style="width:64px;padding:4px 6px;border:1px solid #ddd;border-radius:4px;font-size:12px;"></label>
                <span id="mem-status" style="font-size:11px;color:#888;"></span>
              </div>
            </div>
          </div>
          <!-- 查询类型 -->
          <div style="border:0.5px solid #e0e0e0;border-radius:10px;background:#fff;">
            <div onclick="togglePanel('qt-panel','qt-arrow')" style="padding:12px 16px;cursor:pointer;font-size:14px;font-weight:500;color:#444;user-select:none;display:flex;align-items:center;gap:6px;">
              <span id="qt-arrow">▾</span> 查询类型参考
            </div>
            <div id="qt-panel" style="display:none;padding:0 16px 12px;">
              <div style="margin-bottom:10px;font-size:12px;color:#888;">
                添加或编辑查询类型的填写指引，<code>_system_prompt()</code> 会自动展开。内置类型不可删除。
              </div>
              <div id="query-type-list"></div>
              <button onclick="showAddQueryTypeForm()" style="margin-top:8px;padding:6px 14px;background:#667eea;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;">+ 添加类型</button>
            </div>
          </div>
        </div>
        <div id="rag-iframe-wrap" style="position:relative;width:100%;height:calc(100vh - 100px);margin-top:8px;">
          <div id="rag-iframe-loader" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:12px;background:#fafafa;color:#888;font-size:13px;">
            <div style="width:32px;height:32px;border:3px solid #e0d4f5;border-top-color:#667eea;border-radius:50%;animation:spin 0.8s linear infinite;"></div>
            <div>配置页加载中…（首次启动需探测模型源，耗时约 5-15 秒）</div>
          </div>
          <iframe id="rag-iframe" src="http://localhost:{rag_port}/?_t={int(time.time())}" style="width:100%;height:100%;border:none;" onload="document.getElementById('rag-iframe-loader').style.display='none';"></iframe>
        </div>
        <script>
        function togglePanel(panelId, arrowId) {{
          var panel = document.getElementById(panelId);
          var arrow = document.getElementById(arrowId);
          if (!panel || !arrow) return;
          var hidden = panel.style.display === 'none';
          panel.style.display = hidden ? 'block' : 'none';
          arrow.textContent = hidden ? '▾' : '▸';
          try {{ localStorage.setItem('rag_cfg_' + panelId, hidden ? '0' : '1'); }} catch(e) {{}}
        }}
        (function restorePanelStates() {{
          try {{
            ['llm-panel','mem-panel','qt-panel'].forEach(function(pid) {{
              var val = localStorage.getItem('rag_cfg_' + pid);
              if (val === '1') {{
                var panel = document.getElementById(pid);
                var arrows = document.querySelectorAll('[onclick*="' + pid + '"]');
                if (panel) panel.style.display = 'none';
                arrows.forEach(function(a) {{ var sp = a.querySelector('span'); if(sp) sp.textContent = '▸'; }});
              }}
            }});
          }} catch(e) {{}}
        }})();
        var queryTypes = {{}};
        function loadQueryTypes() {{
          fetch('/api/config/query_types').then(function(r){{return r.json()}}).then(function(d){{ if(d.success) {{ queryTypes = d.types || {{}}; renderQueryTypes(); }} }});
        }}
        function renderQueryTypes() {{
          var list = document.getElementById('query-type-list');
          list.innerHTML = '';
          Object.keys(queryTypes).forEach(function(key) {{
            var t = queryTypes[key];
            var card = document.createElement('div');
            card.style.cssText = 'margin:6px 0;padding:10px 12px;background:#f8f9fc;border-radius:6px;font-size:12px;';
            var hdr = document.createElement('div');
            hdr.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;';
            var st = document.createElement('strong'); st.textContent = t.label || key; hdr.appendChild(st);
            var bg = document.createElement('span');
            bg.style.cssText = 'font-size:11px;color:' + (t.built_in ? '#888' : '#667eea') + ';';
            bg.textContent = t.built_in ? '内置' : '自定义'; hdr.appendChild(bg); card.appendChild(hdr);
            if (t.example) {{
              var ex = document.createElement('div'); ex.style.cssText = 'color:#666;margin-bottom:4px;';
              ex.textContent = '示例: ' + t.example; card.appendChild(ex);
            }}
            if (t.rules) {{
              var gd = document.createElement('div');
              gd.style.cssText = 'color:#555;display:grid;grid-template-columns:auto 1fr;gap:2px 8px;font-size:11px;';
              ['entities','attrs','rel'].forEach(function(k) {{
                var l = document.createElement('span'); l.style.cssText = 'color:#999;'; l.textContent = k; gd.appendChild(l);
                var v = document.createElement('span'); v.textContent = t.rules[k] || '-'; gd.appendChild(v);
              }});
              card.appendChild(gd);
            }}
            if (!t.built_in) {{
              (function(k) {{
                var bw = document.createElement('div'); bw.style.cssText = 'margin-top:6px;text-align:right;';
                var eb = document.createElement('button'); eb.textContent = '编辑';
                eb.style.cssText = 'padding:2px 8px;border:1px solid #ddd;border-radius:4px;cursor:pointer;font-size:11px;background:#fff;margin-right:4px;';
                eb.addEventListener('click', function() {{ editQueryType(k); }}); bw.appendChild(eb);
                var db = document.createElement('button'); db.textContent = '删除';
                db.style.cssText = 'padding:2px 8px;border:1px solid #e55;border-radius:4px;cursor:pointer;font-size:11px;background:#fff;color:#e55;';
                db.addEventListener('click', function() {{ deleteQueryType(k); }}); bw.appendChild(db);
                card.appendChild(bw);
              }})(key);
            }}
            list.appendChild(card);
          }});
        }}
        function showQueryTypeForm(existing, onSave) {{
          var overlay = document.getElementById('modal-overlay');
          var box = document.getElementById('modal-box');
          box.style.maxWidth = '560px';
          document.getElementById('modal-title').textContent = existing ? '编辑查询类型' : '添加查询类型';
          var msg = document.getElementById('modal-msg');
          msg.innerHTML = ''; msg.style.textAlign = 'left'; msg.style.fontSize = '13px';
          msg.style.color = '#444'; msg.style.marginBottom = '16px'; msg.style.maxHeight = '60vh'; msg.style.overflowY = 'auto';
          var addField = function(lbl, help, value) {{
            var wrap = document.createElement('div'); wrap.style.cssText = 'margin-bottom:12px;';
            var l = document.createElement('div'); l.style.cssText = 'font-weight:500;margin-bottom:4px;color:#333;';
            l.textContent = lbl; wrap.appendChild(l);
            var input = document.createElement('input'); input.type = 'text';
            input.style.cssText = 'width:100%;padding:6px 8px;border:1px solid #ddd;border-radius:4px;font-size:13px;box-sizing:border-box;';
            input.value = value || ''; wrap.appendChild(input); wrap._input = input;
            if (help) {{
              var h = document.createElement('div'); h.style.cssText = 'font-size:11px;color:#999;margin-top:3px;line-height:1.4;';
              h.textContent = help; wrap.appendChild(h);
            }}
            msg.appendChild(wrap); return wrap;
          }};
          var existingRules = (existing && existing.rules) ? existing.rules : {{}};
          var labelF = addField('类型名称 *', '内部 key，自动用 custom_<时间戳> 生成', existing ? existing.label : '');
          var exampleF = addField('示例问题', '一个能代表此类问题的问题示例。LLM 通过示例学习模式', existing ? existing.example : '');
          var entitiesF = addField('entities 填写规则', '说明此类问题，entities 应该填什么。例如：取主体/名词，问题涉及的核心事物', existingRules.entities || '');
          var attrsF = addField('attrs 填写规则', '说明此类问题，attrs 应该填什么。例如：目的/属性，用户想查询的维度', existingRules.attrs || '');
          var relF = addField('rel 填写规则', '说明此类问题，rel 应该填什么。例如：留空 / 对比 / 因果', existingRules.rel || '');
          var btns = document.getElementById('modal-buttons'); btns.innerHTML = '';
          var cancelBtn = document.createElement('button'); cancelBtn.textContent = '取消'; cancelBtn.className = 'modal-btn';
          cancelBtn.onclick = function() {{ hideModal(); }}; btns.appendChild(cancelBtn);
          var saveBtn = document.createElement('button'); saveBtn.textContent = '保存'; saveBtn.className = 'modal-btn-primary';
          saveBtn.onclick = function() {{
            var data = {{label: labelF._input.value.trim(), example: exampleF._input.value.trim(), rules: {{entities: entitiesF._input.value.trim(), attrs: attrsF._input.value.trim(), rel: relF._input.value.trim()}}}};
            if (!data.label) {{ showModal('提示', '类型名称不能为空', [{{text:'知道了'}}]); return; }}
            hideModal(); onSave(data);
          }}; btns.appendChild(saveBtn);
          overlay.style.display = 'flex'; labelF._input.focus();
        }}
        function saveQueryType(existing, data) {{
          var body = {{label:data.label, example:data.example, rules:data.rules}};
          if (existing) body.key = existing;
          fetch('/api/config/query_types', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(body)}}).then(function(r){{return r.json()}}).then(function(d){{ if(d.success) loadQueryTypes(); }});
        }}
        function showAddQueryTypeForm() {{ showQueryTypeForm(null, function(data) {{ saveQueryType(null, data); }}); }}
        function editQueryType(key) {{ var t = queryTypes[key]; if(t) showQueryTypeForm(t, function(data) {{ saveQueryType(key, data); }}); }}
        function deleteQueryType(key) {{
          var t = queryTypes[key]; if (!t) return;
          showModal('删除确认', '确定删除查询类型「' + (t.label || key) + '」？', [
            {{text:'取消', action:function(){{}}}},
            {{text:'确定删除', primary:true, action:function(){{fetch('/api/config/query_types', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{action:'delete', key:key}})}}).then(function(r){{return r.json()}}).then(function(d){{ if(d.success) loadQueryTypes(); }});}}}}
          ]);
        }}
        function saveLLM() {{
          fetch('/api/config/llm', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{backend: document.getElementById('llm-backend').value, model: document.getElementById('llm-model').value, timeout: parseInt(document.getElementById('llm-timeout').value) || 180, maxtokens: parseInt(document.getElementById('llm-maxtokens').value) || 4096}})}});
        }}
        function saveMemoryConfig() {{
          var body = {{compress_ratio: parseFloat(document.getElementById('mem-compress-ratio').value) || 0.7, compress_remove_ratio: parseFloat(document.getElementById('mem-remove-ratio').value) || 0.4, max_sessions: parseInt(document.getElementById('mem-max-sessions').value) || 20}};
          fetch('/api/config/memory', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(body)}}).then(function(r){{return r.json()}}).then(function(d){{ document.getElementById('mem-status').textContent = d.success ? '✓ 已保存' : '✗ 保存失败'; }});
        }}
        function loadModels() {{
          var sel = document.getElementById('llm-model');
          var backend = document.getElementById('llm-backend').value;
          sel.innerHTML = '<option value="">加载中...</option>';
          fetch('/api/llm/models?backend=' + encodeURIComponent(backend)).then(function(r){{return r.json()}}).then(function(d){{
            sel.innerHTML = '<option value="">-- 模型 --</option>';
            if(d.models && d.models.length > 0) d.models.forEach(function(m){{ var o=document.createElement('option'); o.value=m; o.textContent=m; sel.appendChild(o); }});
            document.getElementById('llm-status').textContent = (d.models||[]).length + ' 个模型';
          }});
        }}
        setTimeout(loadModels, 500);
        setTimeout(loadQueryTypes, 500);
        setTimeout(function check(){{ var sel = document.getElementById('llm-model'); if(sel.options.length <= 1) {{ setTimeout(check, 500); return; }}
          fetch('/api/config/llm').then(function(r){{return r.json()}}).then(function(cfg){{ if(cfg.model) for(var i=0;i<sel.options.length;i++) if(sel.options[i].value === cfg.model) {{ sel.value = cfg.model; break; }} }});
        }}, 1000);
        function testLLM() {{ document.getElementById('llm-status').textContent = '测试中...';
          fetch('/api/llm/test').then(function(r){{return r.json()}}).then(function(d){{ document.getElementById('llm-status').textContent = d.success ? '✓ 连接正常' : '✖ 连接失败'; }});
        }}
        function toggleWebSearch() {{
          var enabled = document.getElementById('web-search-enabled').checked;
          document.getElementById('search-config').style.display = enabled ? 'block' : 'none';
          fetch('/api/search/toggle', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{enabled: enabled}})}});
        }}
        function onSearchBackendChange() {{
          var v = document.getElementById('search-backend').value;
          document.getElementById('search-key-group').style.display = (v==='tavily' || v==='custom') ? 'inline-block' : 'none';
          document.getElementById('search-google-group').style.display = (v==='google') ? 'inline-block' : 'none';
          document.getElementById('search-bing-group').style.display = (v==='bing') ? 'inline-block' : 'none';
          document.getElementById('search-custom-group').style.display = (v==='custom') ? 'inline-block' : 'none';
          saveSearchConfig();
        }}
        function saveSearchConfig() {{
          var body = {{enabled: document.getElementById('web-search-enabled').checked, backend: document.getElementById('search-backend').value,
            api_key: document.getElementById('search-api-key') ? document.getElementById('search-api-key').value : '',
            google_key: document.getElementById('search-google-key') ? document.getElementById('search-google-key').value : '',
            google_cx: document.getElementById('search-google-cx') ? document.getElementById('search-google-cx').value : '',
            bing_key: document.getElementById('search-bing-key') ? document.getElementById('search-bing-key').value : '',
            custom_url: document.getElementById('search-custom-url') ? document.getElementById('search-custom-url').value : ''}};
          fetch('/api/config/search', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(body)}}).then(function(r){{return r.json()}}).then(function(d){{ document.getElementById('search-status').textContent = d.success ? '✓ 已保存' : '✗ 保存失败'; }});
        }}
        </script>
        """

    # ── Session API ──────────────────────────────

    def _handle_session_new(self):
        if not self.agent:
            self._send_json({"success": False, "error": "智能体未就绪"})
            return
        sid = self.agent.new_session()
        self._send_json({"success": True, "id": sid})

    def _handle_session_list(self):
        if not self.agent:
            self._send_json({"sessions": [], "success": False})
            return
        sessions = self.agent.list_sessions()
        self._send_json({"sessions": sessions, "success": True})

    def _handle_session_switch(self):
        body = self._read_body()
        sid = body.get("id", "")
        if not sid or not self.agent:
            self._send_json({"success": False})
            return
        self.agent.session_id = sid
        raw = self.agent.memory.get_short_term(sid)
        messages = []
        if raw:
            import re
            messages = self._parse_chat_history(raw)
        self._send_json({"success": True, "messages": messages})

    def _handle_session_archive(self):
        body = self._read_body()
        sid = body.get("id", "")
        if not sid or not self.agent:
            self._send_json({"success": False})
            return
        ok = self.agent.archive_session(sid)
        self._send_json({"success": ok})

    def _handle_session_restore(self):
        body = self._read_body()
        sid = body.get("id", "")
        if not sid or not self.agent:
            self._send_json({"success": False})
            return
        try:
            arch_dir = os.path.join(self.agent.data_dir, "archives", "sessions")
            sess_dir = os.path.join(self.agent.data_dir, "sessions")
            os.makedirs(sess_dir, exist_ok=True)
            src = os.path.join(arch_dir, f"{sid}.txt")
            if os.path.exists(src):
                dst = os.path.join(sess_dir, f"{sid}.txt")
                os.rename(src, dst)
            # 也恢复压缩记忆
            mem_arch = os.path.join(self.agent.data_dir, "archives", "memory")
            mem_dst = os.path.join(self.agent.data_dir, "memory", f"compressed_{sid}.txt")
            mem_src = os.path.join(mem_arch, f"compressed_{sid}.txt")
            if os.path.exists(mem_src):
                os.makedirs(os.path.dirname(mem_dst), exist_ok=True)
                os.rename(mem_src, mem_dst)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_session_delete(self):
        body = self._read_body()
        sid = body.get("id", "")
        if not sid or not self.agent:
            self._send_json({"success": False})
            return
        try:
            for base in ["sessions", "archives/sessions"]:
                p = os.path.join(self.agent.data_dir, base, f"{sid}.txt")
                if os.path.exists(p):
                    os.remove(p)
            for base in ["memory", "archives/memory"]:
                p = os.path.join(self.agent.data_dir, base, f"compressed_{sid}.txt")
                if os.path.exists(p):
                    os.remove(p)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _parse_chat_history(self, raw: str) -> list:
        import re
        messages = []
        cur = None
        in_reasoning = False
        ts_prefix = re.compile(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] (user|assistant|reasoning): ')
        for line in raw.split("\n"):
            m = ts_prefix.match(line)
            if m:
                in_reasoning = False
                role = m.group(1)
                if role == "reasoning":
                    if cur and cur["role"] == "assistant":
                        txt = line[m.end():]
                        if txt:
                            cur["reasoning"] = (cur.get("reasoning", "") + "\n" + txt).strip()
                        in_reasoning = True
                    continue
                if cur:
                    cur["content"] = cur["content"].rstrip()
                    if cur["content"]:
                        messages.append(cur)
                cur = {"role": role, "content": line[m.end():]}
            else:
                if cur:
                    if in_reasoning and cur["role"] == "assistant":
                        cur["reasoning"] = (cur.get("reasoning", "") + "\n" + line).strip()
                    else:
                        cur["content"] += "\n" + line
        if cur:
            cur["content"] = cur["content"].rstrip()
            if cur["content"]:
                messages.append(cur)
        return messages

    # ── Config API ───────────────────────────────

    def _serve_config(self):
        cfg = load_config() if SKILL_AVAILABLE else {}
        self._send_json(cfg)

    def _serve_kbs(self):
        if not self.agent or not self.agent.rag.ready:
            self._send_json({"kbs": {}, "success": False})
            return
        self._send_json({"kbs": self.agent.rag.list_kbs(), "success": True})

    def _handle_chat_get(self, parsed):
        msg = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
        if not msg:
            self._send_json({"text": "", "success": False, "error": "参数 'q' 为空"})
            return
        if not self.agent:
            self._send_json({"text": "", "success": False, "error": "智能体未就绪"})
            return
        result = self.agent.chat(msg)
        self._send_json(result)

    def _handle_chat_post(self):
        body = self._read_body()
        msg = body.get("message", "")
        if not msg:
            self._send_json({"text": "", "success": False, "error": "消息为空"})
            return
        if not self.agent:
            self._send_json({"text": "", "success": False, "error": "智能体未就绪"})
            return
        result = self.agent.chat(msg)
        self._send_json(result)

    def _handle_chat_history(self):
        if not self.agent:
            self._send_json({"messages": [], "success": False})
            return
        raw = self.agent.memory.get_short_term(self.agent.session_id)
        if not raw:
            self._send_json({"messages": [], "success": True})
            return
        messages = self._parse_chat_history(raw)
        self._send_json({"messages": messages, "success": True})

    def _update_llm_config(self):
        body = self._read_body()
        cfg = load_config() if SKILL_AVAILABLE else {}
        llm = cfg.setdefault("llm", {})
        llm["backend"] = body.get("backend", llm.get("backend", "ollama"))
        llm["model"] = body.get("model", llm.get("model", ""))
        llm["timeout"] = body.get("timeout", llm.get("timeout", 180))
        llm["max_tokens"] = body.get("maxtokens", llm.get("max_tokens", 4096))
        if SKILL_AVAILABLE:
            save_config(cfg)
        if self.agent:
            self.agent.llm.backend = llm["backend"]
            self.agent.llm.model = llm["model"]
            self.agent.llm.timeout = llm["timeout"]
            self.agent.llm.max_tokens = llm["max_tokens"]
        self._send_json({"success": True})

    def _serve_llm_models(self, query=""):
        if not self.agent:
            self._send_json({"models": [], "success": False})
            return
        params = urllib.parse.parse_qs(query)
        backend = params.get("backend", [None])[0]
        if backend:
            self.agent.llm.backend = backend
            cfg = load_config() if SKILL_AVAILABLE else {}
            cfg.setdefault("llm", {})["backend"] = backend
            if SKILL_AVAILABLE:
                save_config(cfg)
        models = self.agent.llm.list_models()
        self._send_json({"models": models, "success": True})

    def _serve_llm_test(self):
        if not self.agent:
            self._send_json({"success": False, "error": "智能体未就绪"})
            return
        ok = self.agent.llm.check_health()
        self._send_json({"success": ok})

    def _serve_llm_config_get(self):
        if not self.agent:
            self._send_json({"success": False})
            return
        cfg = {
            "backend": self.agent.llm.backend,
            "model": self.agent.llm.model,
            "max_tokens": self.agent.llm.max_tokens,
            "timeout": self.agent.llm.timeout,
        }
        try:
            ok = self.agent.llm.check_health()
            cfg["health_ok"] = ok
            cfg["health_message"] = "连接正常" if ok else "无法连接，请检查服务是否启动"
        except Exception:
            cfg["health_ok"] = False
            cfg["health_message"] = "检查异常"
        self._send_json(cfg)

    def _serve_memory_config(self):
        cfg = load_config() if SKILL_AVAILABLE else {}
        mem = cfg.get("memory", {})
        self._send_json({
            "compress_ratio": mem.get("compress_ratio", 0.7),
            "compress_remove_ratio": mem.get("compress_remove_ratio", 0.4),
            "max_sessions": mem.get("max_sessions", 20),
        })

    def _update_memory_config(self):
        body = self._read_body()
        cfg = load_config() if SKILL_AVAILABLE else {}
        mem = cfg.setdefault("memory", {})
        for k in ("compress_ratio", "compress_remove_ratio", "max_sessions"):
            if k in body:
                mem[k] = body[k]
        if SKILL_AVAILABLE:
            save_config(cfg)
        self._send_json({"success": True})

    def _handle_agent_query(self, query_str: str):
        params = urllib.parse.parse_qs(query_str)
        msg = params.get("q", params.get("message", [""]))[0]
        if not msg:
            self._send_json({"success": False, "error": "缺少参数 q"})
            return
        self._execute_query(msg, params.get("kb", [None])[0])

    def _handle_agent_query_post(self):
        body = self._read_body()
        msg = body.get("message", "")
        if not msg:
            self._send_json({"success": False, "error": "缺少字段 message"})
            return
        self._execute_query(msg, body.get("kb"))

    def _execute_query(self, message: str, kb: str = None):
        if not self.agent:
            self._send_json({"success": False, "error": "智能体未就绪"})
            return
        result = self.agent.chat(message)
        self._send_json(result)

    def _serve_agent_gaps(self):
        if not self.agent or not self.agent.rag.ready:
            self._send_json({"gaps": [], "success": False})
            return
        gaps = self.agent.memory.get_gaps(min_count=1)
        self._send_json({"gaps": gaps, "success": True})

    def _handle_agent_import(self):
        body = self._read_body()
        kb_name = body.get("kb", "default")
        if not self.agent or not self.agent.rag.ready:
            self._send_json({"success": False, "error": "RAG 未就绪"})
            return
        title = body.get("title", "")
        content = body.get("content", "")
        if title and content:
            result = self.agent.rag.import_text(content, kb_name=kb_name, title=title)
            self._send_json(result)
            return
        text = body.get("text", "")
        if text:
            result = self.agent.rag.import_text(text, kb_name=kb_name)
            self._send_json(result)
            return
        file_path = body.get("path", "")
        if not file_path:
            self._send_json({"success": False, "error": "需要提供 path、text 或 title+content"})
            return
        if not os.path.exists(file_path):
            self._send_json({"success": False, "error": f"路径不存在: {file_path}"})
            return
        result = self.agent.rag.import_file(file_path, kb_name)
        self._send_json(result)

    def _handle_agent_upload_files(self):
        body = self._read_body()
        filename = body.get("name", "untitled")
        base64_data = body.get("data", "")
        if not base64_data:
            self._send_json({"success": False, "error": "缺少 data"})
            return
        import base64
        try:
            raw = base64.b64decode(base64_data)
        except Exception as e:
            self._send_json({"success": False, "error": f"base64 解码失败: {e}"})
            return
        import_dir = os.path.join(self.agent.data_dir, "imports")
        os.makedirs(import_dir, exist_ok=True)
        tmp_path = os.path.join(import_dir, filename)
        if os.path.exists(tmp_path):
            base_name, ext = os.path.splitext(filename)
            n = 1
            while os.path.exists(tmp_path):
                tmp_path = os.path.join(import_dir, f"{base_name}_{n}{ext}")
                n += 1
        try:
            with open(tmp_path, "wb") as f:
                f.write(raw)
            try:
                import json as _json
                manifest_path = os.path.join(self.agent.data_dir, "import_manifest.json")
                manifest = []
                if os.path.exists(manifest_path):
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        existing = _json.load(f)
                    existing_paths = {e["path"] for e in existing if isinstance(e, dict)}
                    if tmp_path not in existing_paths:
                        manifest = existing
                manifest = [e for e in manifest if isinstance(e, dict) and os.path.exists(e.get("path", ""))]
                manifest.append({"path": tmp_path, "name": filename})
                with open(manifest_path, "w", encoding="utf-8") as f:
                    _json.dump(manifest, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            self._send_json({"success": True, "path": tmp_path})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_memory_inject(self):
        body = self._read_body()
        text = body.get("text", "")
        if not text or not self.agent:
            self._send_json({"success": False})
            return
        self.agent.memory.append_short_term(self.agent.session_id, "user",
            f"[系统通知] {text}。可输入「入库」使用 path=\"MANIFEST\" 批量导入")
        self._send_json({"success": True})

    def _toggle_search(self):
        body = self._read_body()
        enabled = body.get("enabled", True)
        cfg = load_config() if SKILL_AVAILABLE else {}
        cfg["web_search_enabled"] = enabled
        if SKILL_AVAILABLE:
            save_config(cfg)
        if self.agent:
            self.agent.web_search_enabled = enabled
        self._send_json({"success": True})

    def _serve_search_config_get(self):
        cfg = load_config() if SKILL_AVAILABLE else {}
        search = cfg.get("search", {})
        self._send_json({
            "backend": search.get("backend", "duckduckgo"),
            "api_key": search.get("api_key", ""),
            "google_key": search.get("google_key", ""),
            "google_cx": search.get("google_cx", ""),
            "bing_key": search.get("bing_key", ""),
            "custom_url": search.get("custom_url", ""),
        })

    def _update_search_config(self):
        body = self._read_body()
        cfg = load_config() if SKILL_AVAILABLE else {}
        search = cfg.setdefault("search", {})
        for key in ("backend", "api_key", "google_key", "google_cx", "bing_key", "custom_url"):
            if key in body:
                search[key] = body[key]
        cfg["web_search_enabled"] = body.get("enabled", cfg.get("web_search_enabled", False))
        if SKILL_AVAILABLE:
            save_config(cfg)
        if self.agent and hasattr(self.agent, 'web_search_enabled'):
            self.agent.web_search_enabled = cfg["web_search_enabled"]
        self._send_json({"success": True})

    # ═══════════════ 查询类型管理 ═══════════════
    BUILTIN_QUERY_TYPES = _BUILTIN_QUERY_TYPES

    def _serve_query_types(self):
        types = dict(self.BUILTIN_QUERY_TYPES)
        for t in types.values():
            t["built_in"] = True
        if SKILL_AVAILABLE:
            try:
                cfg = load_config()
                custom = cfg.get("query_types", {})
                if isinstance(custom, dict):
                    for k, v in custom.items():
                        v["built_in"] = False
                        types[k] = v
            except Exception:
                pass
        self._send_json({"types": types, "success": True})

    def _update_query_types(self):
        body = self._read_body()
        action = body.get("action", "save")
        if action == "delete":
            key = body.get("key", "")
            if not key or key in self.BUILTIN_QUERY_TYPES:
                self._send_json({"success": False, "error": "内置类型不可删除"})
                return
            if SKILL_AVAILABLE:
                cfg = load_config()
                types = cfg.get("query_types", {})
                if isinstance(types, dict) and key in types:
                    del types[key]
                    cfg["query_types"] = types
                    save_config(cfg)
            self._send_json({"success": True})
            return
        label = body.get("label", "").strip()
        example = body.get("example", "").strip()
        rules = body.get("rules", {})
        if not label or not rules:
            self._send_json({"success": False, "error": "名称和填写规则不能为空"})
            return
        import time
        key = body.get("key", "") or f"custom_{int(time.time())}"
        entry = {"label": label, "example": example, "rules": rules, "built_in": False}
        if SKILL_AVAILABLE:
            cfg = load_config()
            types = cfg.setdefault("query_types", {})
            types[key] = entry
            save_config(cfg)
        self._send_json({"success": True, "key": key})

    def _reset_memory(self):
        if self.agent:
            self.agent.reset_session()
            self._send_json({"success": True})
        else:
            self._send_json({"success": False, "error": "智能体未就绪"})

    def _compress_memory(self):
        if not self.agent:
            self._send_json({"success": False, "error": "智能体未就绪"})
            return
        sid = self.agent.session_id
        mem = self.agent.memory
        line_count = mem.short_term_line_count(sid)
        if line_count == 0:
            self._send_json({"success": True, "count": 0, "text": "没有可压缩的内容"})
            return
        n = min(40, line_count)
        removed = mem.pop_oldest_lines(sid, n)
        mem.store_compressed(sid, removed)
        self._send_json({"success": True, "count": n})

    def _clear_context(self):
        if not self.agent:
            self._send_json({"success": False, "error": "智能体未就绪"})
            return
        sid = self.agent.session_id
        mem = self.agent.memory
        content = mem.get_short_term(sid)
        if content.strip():
            mem.store_compressed(sid, "[手动清除前]\n" + content)
        mem.clear_short_term(sid)
        saved = len([l for l in content.split("\n") if l.strip()]) if content.strip() else 0
        self._send_json({"success": True, "saved_lines": saved})

    def log_message(self, format, *args):
        logger.debug(f"HTTP: {format % args}")


def _port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def _find_ports(base: int, count: int = 2, max_range: int = 2000) -> list[int]:
    for start in range(base, base + max_range, count):
        ports = list(range(start, start + count))
        if not any(_port_in_use(p) for p in ports):
            return ports
    raise RuntimeError(f"在 {base}~{base+max_range} 范围内无法找到 {count} 个连续可用端口")


def start_web_ui(agent, port: int = 8765, host: str = "0.0.0.0"):
    """启动 Web 界面（自动查找可用端口，启动独立 RAG 配置服务器）"""
    AssistantHandler.agent = agent

    ports = _find_ports(port, count=2)
    main_port, rag_port = ports[0], ports[1]
    AssistantHandler.main_port = main_port
    AssistantHandler.rag_port = rag_port

    print(f"  🌐 主界面: http://{host}:{main_port}")
    print(f"  🔧 配置页: http://{host}:{rag_port}")

    import subprocess, time
    for p in [main_port, rag_port]:
        try:
            result = subprocess.run(
                f'netstat -ano | findstr ":{p}"',
                shell=True, capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in line:
                    pid = parts[-1]
                    if pid and pid != "0":
                        subprocess.run(f'taskkill /F /PID {pid} 2>nul', shell=True, timeout=3)
                        time.sleep(0.5)
                        print(f"  🔫 已杀掉旧进程 (PID {pid})")
        except Exception:
            pass

    try:
        import subprocess
        rag_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine", "rag_web_ui.py")
        subprocess.Popen(
            [sys.executable, rag_script, "--port", str(rag_port)],
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        print(f"  📚 RAG 配置服务器: http://localhost:{rag_port}")
    except Exception as e:
        print(f"  ⚠️ RAG 配置服务器启动失败: {e}")

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    server = socketserver.ThreadingTCPServer((host, main_port), AssistantHandler)
    logger.info(f"Web 界面已启动: http://{host}:{main_port}")
    print(f"  🌐 http://localhost:{main_port}")
    print(f"  ⚙️ 配置 | 💬 对话")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Web 界面已停止")
        server.shutdown()
