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
        elif path == "/api/agent/gaps":
            self._serve_agent_gaps()
        elif path.startswith("/api/agent/query"):
            self._handle_agent_query(parsed.query)
        elif path == "/api/chat/history":
            self._handle_chat_history()
        elif path.startswith("/api/chat"):
            self._handle_chat_get(parsed)
        elif path == "/api/memory/reset":
            self._reset_memory()
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
        elif path == "/api/search/toggle":
            self._toggle_search()
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
            pass  # 客户端提前断开，忽略

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

    def _serve_main_page(self):
        """主页面：Tab 切换（配置 + 对话）"""
        config_html = self._render_config_tab() if SKILL_AVAILABLE else "<p>技能模块未加载</p>"
        chat_html = self._render_chat_tab()

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>RAG 智能助手</title>
<link rel="icon" href="data:,">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f6fa; color: #333; }}
.tabs {{ display: flex; background: #fff; border-bottom: 1px solid #e0e0e0; position: sticky; top: 0; z-index: 100; }}
.tab {{ padding: 14px 28px; cursor: pointer; font-size: 14px; font-weight: 500; color: #888; border-bottom: 2px solid transparent; transition: all 0.2s; }}
.tab:hover {{ color: #555; }}
.tab.active {{ color: #667eea; border-bottom-color: #667eea; }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}
#config-content {{ padding: 16px; }}
#chat-content {{ display: none; height: calc(100vh - 48px); }}
#chat-content.active {{ display: flex; flex-direction: column; }}
/* ── Chat ── */
.chat-messages {{ flex: 1; overflow-y: auto; padding: 20px; background: #f5f6fa; }}
.msg {{ max-width: 80%; margin-bottom: 16px; padding: 12px 16px; border-radius: 12px; line-height: 1.6; font-size: 14px; white-space: pre-wrap; }}
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
.chat-input {{ display: flex; gap: 8px; padding: 12px 20px; background: #fff; border-top: 1px solid #e0e0e0; }}
.chat-input textarea {{ flex: 1; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; resize: none; font-size: 14px; outline: none; }}
.chat-input textarea:focus {{ border-color: #667eea; }}
.chat-input button {{ padding: 10px 24px; background: #667eea; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }}
.chat-input button:hover {{ background: #5a6fd6; }}
.chat-input button:disabled {{ background: #ccc; cursor: not-allowed; }}
/* ── 推理链 ── */
.reasoning-toggle {{ font-size: 12px; color: #888; cursor: pointer; margin-top: 8px; padding: 2px 0; user-select: none; }}
.reasoning-toggle:hover {{ color: #667eea; }}
.reasoning-body {{ font-size: 12px; color: #666; background: #f8f8fc; border-left: 2px solid #667eea; padding: 8px 12px; margin-top: 4px; border-radius: 0 6px 6px 0; white-space: pre-wrap; line-height: 1.5; }}
/* ── 状态栏 ── */
.status-bar {{ display: flex; gap: 16px; padding: 6px 20px; background: #f0f0f5; font-size: 12px; color: #888; border-bottom: 1px solid #e0e0e0; }}
.status-item {{ display: flex; align-items: center; gap: 4px; }}
.status-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
.status-dot.on {{ background: #4caf50; }}
.status-dot.off {{ background: #f44336; }}
</style>
</head>
<body>
<div class="tabs">
  <div class="tab active" onclick="switchTab('config')">⚙️ 配置</div>
  <div class="tab" onclick="switchTab('chat')">💬 对话</div>
</div>
<div id="config-content" class="tab-content active">
  {config_html}
</div>
<div id="chat-content" class="tab-content">{chat_html}</div>

<script>
function switchTab(name) {{
  var map = {{config:0, chat:1}};
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab')[map[name] || 0].classList.add('active');
  document.getElementById(name + '-content').classList.add('active');
  if (name === 'chat') document.getElementById('chat-input').focus();
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
      document.getElementById('kb-status').textContent = d.kb || '-';
    }} else {{
      addMessage('抱歉，处理出错：' + (d.error || '未知错误'), 'system');
    }}
    isStreaming = false;
    document.getElementById('send-btn').disabled = false;
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
  }} else {{
    div.textContent = text;
  }}

  // 推理链（可折叠）
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
    body.textContent = reasoning;
    body.style.display = 'none';
    div.appendChild(toggle);
    div.appendChild(body);
  }}

  document.getElementById('chat-messages').appendChild(div);
  div.scrollIntoView({{behavior:'smooth', block:'end'}});
}}

document.getElementById('chat-input').addEventListener('keydown', function(e) {{
  if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); sendMessage(); }}
}});
</script>
</body>
</html>"""
        self._send_html(html)

    def _render_config_tab(self) -> str:
        """配置 Tab：LLM 设置 + RAG 配置 iframe"""
        import time
        rag_port = type(self).rag_port  # 通过类变量读取真实端口
        cfg = load_config() if SKILL_AVAILABLE else {}
        llm_backend = cfg.get("llm_backend", "ollama")
        llm_max_tokens = cfg.get("llm_max_tokens", 4096)
        llm_timeout = cfg.get("llm_timeout", 180)
        web_search = cfg.get("web_search_enabled", True)
        return f"""
        <div style="padding:12px 16px;background:#f5f6fa;border-bottom:1px solid #e0e0e0;">
          <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;">
            <select id="llm-backend" onchange="saveLLM();loadModels()" style="padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;">
              <option value="ollama" {"selected" if llm_backend=='ollama' else ""}>Ollama</option>
              <option value="lmstudio" {"selected" if llm_backend=='lmstudio' else ""}>LM Studio</option>
            </select>
            <select id="llm-model" onchange="saveLLM()" style="flex:1;min-width:200px;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;">
              <option value="">-- 模型 --</option>
            </select>
            <input type="number" id="llm-timeout" value="{llm_timeout}" min="30" max="600" step="30" onchange="saveLLM()" style="width:70px;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;" title="超时秒数">
            <input type="number" id="llm-maxtokens" value="{llm_max_tokens}" min="512" max="131072" step="1024" onchange="saveLLM()" style="width:90px;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;" title="最大输出token数">
            <button onclick="loadModels()" style="padding:6px 12px;background:#f0f0f5;border:1px solid #ddd;border-radius:6px;cursor:pointer;font-size:12px;">🔄</button>
            <button onclick="testLLM()" style="padding:6px 12px;background:#667eea;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;">测试</button>
            <label style="font-size:13px;display:flex;align-items:center;gap:4px;">
              <input type="checkbox" id="web-search" onchange="saveLLM()" {"checked" if web_search else ""} style="accent-color:#667eea;">
              联网搜索
            </label>
            <span id="llm-status" style="font-size:12px;color:#888;"></span>
          </div>
        </div>
        <iframe src="http://localhost:{rag_port}/?_t={int(time.time())}" style="width:100%;height:calc(100vh - 100px);border:none;"></iframe>
        <script>
        function saveLLM() {{
          var savedModel = document.getElementById('llm-model').value;
          fetch('/api/config/llm', {{
            method:'POST', headers:{{'Content-Type':'application/json'}},
            body:JSON.stringify({{
              backend: document.getElementById('llm-backend').value,
              model: document.getElementById('llm-model').value,
              timeout: parseInt(document.getElementById('llm-timeout').value) || 180,
              maxtokens: parseInt(document.getElementById('llm-maxtokens').value) || 4096
            }})
          }}).then(function(){{
            if(savedModel) document.getElementById('llm-model').value = savedModel;
          }});
        }}
        function loadModels() {{
          var sel = document.getElementById('llm-model');
          var backend = document.getElementById('llm-backend').value;
          sel.innerHTML = '<option value="">加载中...</option>';
          fetch('/api/llm/models?backend=' + encodeURIComponent(backend))
            .then(function(r){{return r.json()}})
            .then(function(d){{
              sel.innerHTML = '<option value="">-- 模型 --</option>';
              if(d.models && d.models.length > 0)
                d.models.forEach(function(m){{
                  var o=document.createElement('option'); o.value=m; o.textContent=m; sel.appendChild(o);
                }});
              document.getElementById('llm-status').textContent = (d.models||[]).length + ' 个模型';
              document.getElementById('llm-config').textContent = (d.models||[]).length + ' 个模型';
            }});
        }}
        setTimeout(loadModels, 500);
        // 等模型加载完后恢复配置
        setTimeout(function check(){{
          var sel = document.getElementById('llm-model');
          if(sel.options.length <= 1) {{ setTimeout(check, 500); return; }}
          fetch('/api/config/llm').then(function(r){{return r.json()}}).then(function(cfg){{
            if(cfg.model) for(var i=0;i<sel.options.length;i++)
              if(sel.options[i].value === cfg.model) {{ sel.value = cfg.model; break; }}
            document.getElementById('llm-config').textContent = (cfg.model || '-') + ' / ' + (cfg.max_tokens || '?') + ' tok';
          }});
        }}, 1000);

        function testLLM() {{
          document.getElementById('llm-status').textContent = '测试中...';
          fetch('/api/llm/test').then(function(r){{return r.json()}}).then(function(d){{
            document.getElementById('llm-status').textContent = d.success ? '✓ 连接正常' : '✖ 连接失败';
          }});
        }}
        setTimeout(loadModels, 500);
        </script>
        """

    def _render_chat_tab(self) -> str:
        return f"""
        <div class="status-bar">
          <span class="status-item">📚 知识库: <span id="kb-status">-</span></span>
          <span class="status-item">⚙️ <span id="llm-config">-</span></span>
          <span class="status-item">🧠 <a href="#" onclick="resetMemory()" style="color:#667eea;">重置对话</a></span>
        </div>
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
        <script>
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
                // 注入 session，不传具体路径（由 manifest 管理）
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

        function resetMemory() {{
          if(!confirm('确定重置当前对话？')) return;
          fetch('/api/memory/reset', {{method:'GET'}}).then(function(r){{return r.json()}}).then(function(d){{
            if(d.success) {{ document.getElementById('chat-messages').innerHTML = '<div class=\\"msg assistant\\">对话已重置。</div>'; }}
          }});
        }}

        // 页面加载时恢复聊天历史
        function loadChatHistory() {{
          fetch('/api/chat/history').then(function(r){{return r.json()}}).then(function(d){{
            if(d.success && d.messages && d.messages.length) {{
              var container = document.getElementById('chat-messages');
              container.innerHTML = '';
              d.messages.forEach(function(m){{
                addMessage(m.content, m.role);
              }});
            }}
          }});
        }}
        setTimeout(loadChatHistory, 200);
        </script>
        """

    # ── API ──────────────────────────────────────

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
        """返回当前 session 的聊天历史"""
        if not self.agent:
            self._send_json({"messages": [], "success": False})
            return
        raw = self.agent.memory.get_short_term(self.agent.session_id)
        if not raw:
            self._send_json({"messages": [], "success": True})
            return
        messages = []
        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if "] user: " in line:
                content = line.split("] user: ", 1)[1]
                messages.append({"role": "user", "content": content})
            elif "] assistant: " in line:
                content = line.split("] assistant: ", 1)[1]
                messages.append({"role": "assistant", "content": content})
        self._send_json({"messages": messages, "success": True})

    def _update_llm_config(self):
        body = self._read_body()
        cfg = load_config() if SKILL_AVAILABLE else {}
        backend = body.get("backend", cfg.get("llm_backend", "ollama"))
        model = body.get("model", cfg.get("llm_model", ""))
        timeout = body.get("timeout", cfg.get("llm_timeout", 180))
        maxtokens = body.get("maxtokens", cfg.get("llm_max_tokens", 4096))
        cfg["llm_backend"] = backend
        cfg["llm_model"] = model
        cfg["llm_timeout"] = timeout
        cfg["llm_max_tokens"] = maxtokens
        if SKILL_AVAILABLE:
            save_config(cfg)
        if self.agent:
            self.agent.llm.backend = backend
            self.agent.llm.model = model
            self.agent.llm.timeout = timeout
            self.agent.llm.max_tokens = maxtokens
        self._send_json({"success": True})

    def _serve_llm_models(self, query=""):
        """返回可用模型列表"""
        if not self.agent:
            self._send_json({"models": [], "success": False})
            return
        params = urllib.parse.parse_qs(query)
        backend = params.get("backend", [None])[0]
        if backend:
            self.agent.llm.backend = backend
            cfg = load_config() if SKILL_AVAILABLE else {}
            cfg["llm_backend"] = backend
            if SKILL_AVAILABLE:
                save_config(cfg)
        models = self.agent.llm.list_models()
        self._send_json({"models": models, "success": True})

    def _serve_llm_test(self):
        """测试 LLM 连接"""
        if not self.agent:
            self._send_json({"success": False, "error": "智能体未就绪"})
            return
        ok = self.agent.llm.check_health()
        self._send_json({"success": ok})

    def _serve_llm_config_get(self):
        """返回当前 LLM 配置"""
        if not self.agent:
            self._send_json({"success": False})
            return
        self._send_json({
            "backend": self.agent.llm.backend,
            "model": self.agent.llm.model,
            "max_tokens": self.agent.llm.max_tokens,
            "timeout": self.agent.llm.timeout,
        })
        ok = self.agent.llm.check_health()
        self._send_json({"success": ok, "message": "连接正常" if ok else "无法连接，请检查服务是否启动"})

    def _handle_agent_query(self, query_str: str):
        """GET /api/agent/query?q=xxx&kb=xxx"""
        params = urllib.parse.parse_qs(query_str)
        msg = params.get("q", params.get("message", [""]))[0]
        if not msg:
            self._send_json({"success": False, "error": "缺少参数 q"})
            return
        self._execute_query(msg, params.get("kb", [None])[0])

    def _handle_agent_query_post(self):
        """POST /api/agent/query {"message":"xxx","kb":"xxx"}"""
        body = self._read_body()
        msg = body.get("message", "")
        if not msg:
            self._send_json({"success": False, "error": "缺少字段 message"})
            return
        self._execute_query(msg, body.get("kb"))

    def _execute_query(self, message: str, kb: str = None):
        """执行查询（共用的内部逻辑）"""
        if not self.agent:
            self._send_json({"success": False, "error": "智能体未就绪"})
            return
        cfg = {}
        if kb:
            cfg["session_id"] = f"api_{kb}"
        result = self.agent.chat(message)
        self._send_json(result)

    def _serve_agent_gaps(self):
        """GET /api/agent/gaps — 返回知识缺口"""
        if not self.agent or not self.agent.rag.ready:
            self._send_json({"gaps": [], "success": False})
            return
        gaps = self.agent.memory.get_gaps(min_count=1)
        self._send_json({"gaps": gaps, "success": True})

    def _handle_agent_import(self):
        """POST /api/agent/import — 导入文件/文本/知识到知识库
        支持三种模式：
          {"path":"...", "kb":"白酒"}                     ← 文件/文件夹
          {"text":"...", "kb":"白酒"}                       ← 纯文本
          {"title":"酱香型标准", "content":"...", "kb":"白酒"}  ← 结构化知识
        """
        body = self._read_body()
        kb_name = body.get("kb", "default")
        if not self.agent or not self.agent.rag.ready:
            self._send_json({"success": False, "error": "RAG 未就绪"})
            return

        # 模式1: 结构化知识 (title + content)
        title = body.get("title", "")
        content = body.get("content", "")
        if title and content:
            result = self.agent.rag.import_text(content, kb_name=kb_name, title=title)
            self._send_json(result)
            return

        # 模式2: 纯文本
        text = body.get("text", "")
        if text:
            result = self.agent.rag.import_text(text, kb_name=kb_name)
            self._send_json(result)
            return

        # 模式3: 文件/文件夹路径
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
        """POST /api/agent/upload-files {name, data( base64)} — 上传到服务器临时目录，不导入"""
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
            # 写入清单供 LLM 用 path="MANIFEST" 批量导入
            try:
                import json as _json
                manifest_path = os.path.join(self.agent.data_dir, "import_manifest.json")
                manifest = []
                if os.path.exists(manifest_path):
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = _json.load(f)
                manifest.append({"path": tmp_path, "name": filename})
                with open(manifest_path, "w", encoding="utf-8") as f:
                    _json.dump(manifest, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            self._send_json({"success": True, "path": tmp_path})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_memory_inject(self):
        """注入消息到 session（不触发 LLM）"""
        body = self._read_body()
        text = body.get("text", "")
        if not text or not self.agent:
            self._send_json({"success": False})
            return
        # 文件路径单独存 manifest，session 里只通知有文件待入库
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

    def _reset_memory(self):
        if self.agent:
            self.agent.reset_session()
            self._send_json({"success": True})
        else:
            self._send_json({"success": False, "error": "智能体未就绪"})

    def log_message(self, format, *args):
        logger.debug(f"HTTP: {format % args}")


def _port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def _find_ports(base: int, count: int = 2, max_range: int = 2000) -> list[int]:
    """在 [base, base+max_range) 范围内找 count 个连续可用端口"""
    for start in range(base, base + max_range, count):
        ports = list(range(start, start + count))
        if not any(_port_in_use(p) for p in ports):
            return ports
    raise RuntimeError(f"在 {base}~{base+max_range} 范围内无法找到 {count} 个连续可用端口")


def start_web_ui(agent, port: int = 8765, host: str = "0.0.0.0"):
    """启动 Web 界面（自动查找可用端口，启动独立 RAG 配置服务器）"""
    AssistantHandler.agent = agent

    # 在 2000 端口范围内找两个连续可用端口
    ports = _find_ports(port, count=2)
    main_port, rag_port = ports[0], ports[1]
    AssistantHandler.main_port = main_port
    AssistantHandler.rag_port = rag_port

    print(f"  🌐 主界面: http://{host}:{main_port}")
    print(f"  🔧 配置页: http://{host}:{rag_port}")

    # 自动杀掉占用端口的旧进程
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

    # 启动 RAG 配置服务器（独立子进程，避免库初始化冲突）
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
