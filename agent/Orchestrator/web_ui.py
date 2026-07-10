"""
web_ui.py — Orchestrator Web 界面
含对话 + 配置 + Pipeline 编排，三 Tab 切换
自包含 HTTP 服务器，纯 HTML/CSS/JS 内联
"""
import os, sys, json, logging, http.server, urllib.parse, socketserver, threading
from typing import Optional

logger = logging.getLogger(__name__)

# 包内路径（不加入 sys.path，避免相对 import 冲突）
_DIR = os.path.dirname(os.path.abspath(__file__))

from orchestrator.agent_config import AgentConfig
from orchestrator.agent_loop import Agent
from orchestrator.llm_client import LLMClient
from orchestrator.tool_base import BaseTool, ToolResult
from orchestrator.tools.file_tool import ReadFileTool, WriteFileTool, ListDirTool
from orchestrator.tools.web_tool import WebFetchTool, WebSearchTool, PythonExecuteTool
from orchestrator.tools.skill_loader import LoadSkillTool
try:
    from orchestrator.skill_scanner import scan_skills, search_skills
    from orchestrator.chain_model import SkillInfo, Pipeline, PipelineNode
    SKILL_AVAILABLE = True
except ImportError:
    SKILL_AVAILABLE = False


class OrchestratorHandler(http.server.BaseHTTPRequestHandler):
    """HTTP 请求处理器"""
    agent = None
    config = None
    llm = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            self._serve_main_page()
        elif path == "/api/chat":
            self._handle_chat_get()
        elif path == "/api/config":
            self._serve_config()
        elif path == "/api/llm/models":
            self._serve_llm_models()
        elif path == "/api/llm/test":
            self._serve_llm_test()
        elif path == "/api/skills":
            self._serve_skills()
        elif path == "/api/pipelines":
            self._serve_pipelines()
        elif path.startswith("/api/pipelines/"):
            name = path.split("/api/pipelines/")[1]
            self._serve_pipeline(name)
        elif path.startswith("/static/"):
            self._serve_static(path)
        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/api/chat":
            self._handle_chat_post()
        elif path == "/api/config":
            self._handle_config_post()
        elif path == "/api/pipelines":
            self._handle_pipeline_save()
        elif path == "/api/pipelines/delete":
            self._handle_pipeline_delete()
        elif path == "/api/pipelines/run":
            self._handle_pipeline_run()
        else:
            self._send_json({"error": "Not Found"}, 404)

    def _send_json(self, data: dict, status: int = 200):
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def _send_html(self, html: str):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    # ==================================================================
    # 主页
    # ==================================================================
    def _serve_main_page(self):
        html = self._build_html()
        self._send_html(html)

    def _serve_static(self, path: str):
        """提供静态文件"""
        rel = path.lstrip("/")
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)
        if not os.path.isfile(file_path):
            self._send_json({"error": "Not Found"}, 404)
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            ext = os.path.splitext(file_path)[1]
            mime = {"": "text/plain"}
            if ext == ".js": mime[""] = "application/javascript"
            elif ext == ".css": mime[""] = "text/css"
            elif ext == ".html": mime[""] = "text/html"
            self.send_response(200)
            self.send_header("Content-Type", mime[""] + "; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _build_html(self) -> str:
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Orchestrator Web UI</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f6fa;color:#333;height:100vh;display:flex;flex-direction:column}
.tab-bar{display:flex;background:#2d2d44;padding:0 8px;flex-shrink:0}
.tab{padding:12px 20px;color:#aaa;cursor:pointer;font-size:14px;border-bottom:2px solid transparent;transition:all .2s}
.tab:hover{color:#fff;background:rgba(255,255,255,.05)}
.tab.active{color:#fff;border-bottom-color:#667eea;background:rgba(102,126,234,.1)}
.tab-content{flex:1;display:none;overflow:auto}
.tab-content.active{display:flex;flex-direction:column}
/* Chat */
#chat-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px}
.msg{max-width:85%;padding:10px 14px;border-radius:12px;font-size:14px;line-height:1.6;word-break:break-word}
.msg.user{align-self:flex-end;background:#667eea;color:#fff;border-bottom-right-radius:4px}
.msg.assistant{align-self:flex-start;background:#fff;color:#333;border:1px solid #e0e0e0;border-bottom-left-radius:4px}
.msg.system{align-self:center;background:#fff3cd;color:#856404;font-size:13px;border:1px solid #ffc107}
.msg.thinking{background:#f0f0f5;color:#888;font-style:italic}
/* Markdown 渲染 */
.msg.assistant code{background:#f0f0f5;padding:2px 6px;border-radius:4px;font-size:13px;font-family:'Consolas','Monaco',monospace}
.msg.assistant pre{background:#f5f5f5;padding:12px;border-radius:8px;overflow-x:auto;margin:8px 0;border:1px solid #e0e0e0}
.msg.assistant pre code{background:transparent;padding:0;border-radius:0}
.msg.assistant table{border-collapse:collapse;margin:8px 0;font-size:13px;width:auto;max-width:100%}
.msg.assistant th,.msg.assistant td{border:1px solid #ddd;padding:6px 10px;text-align:left}
.msg.assistant th{background:#f5f5ff;font-weight:600}
.msg.assistant blockquote{border-left:3px solid #667eea;padding:6px 12px;margin:8px 0;background:#f8f9fc;color:#555}
.msg.assistant ul,.msg.assistant ol{padding-left:20px;margin:4px 0}
.msg.assistant p{margin:4px 0}
.msg.assistant h1,.msg.assistant h2,.msg.assistant h3,.msg.assistant h4{margin:8px 0 4px;color:#2d2d44}
.msg.assistant a{color:#667eea;text-decoration:none}
.msg.assistant a:hover{text-decoration:underline}
.msg.assistant img{max-width:100%;border-radius:6px;margin:4px 0}
/* 记忆状态 */
.memory-stats{font-size:11px;color:#aaa;padding:2px 16px;background:#fafbfc;border-bottom:1px solid #f0f0f0;flex-shrink:0}
.chat-input{display:flex;gap:8px;padding:12px 16px;background:#fff;border-top:1px solid #e0e0e0;flex-shrink:0}
.chat-input textarea{flex:1;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:14px;resize:none;outline:none;font-family:inherit}
.chat-input textarea:focus{border-color:#667eea}
.chat-input button{padding:10px 24px;background:#667eea;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500}
.chat-input button:hover{background:#5a6fd6}
.chat-input button:disabled{background:#999;cursor:not-allowed}
.status-bar{display:flex;gap:16px;padding:8px 16px;background:#f8f9fc;border-bottom:1px solid #e0e0e0;font-size:12px;color:#888;flex-shrink:0}
.status-item{display:flex;align-items:center;gap:4px}
/* Config */
.config-page{padding:24px;max-width:720px;margin:0 auto;width:100%}
.config-section{background:#fff;border-radius:12px;padding:20px;margin-bottom:16px;border:1px solid #e0e0e0}
.config-section h3{font-size:15px;font-weight:500;margin-bottom:12px;color:#2d2d44}
.config-row{display:flex;gap:12px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
.config-row label{font-size:13px;color:#666;min-width:80px}
.config-row select,.config-row input{padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;outline:none}
.config-row select:focus,.config-row input:focus{border-color:#667eea}
.config-row select{min-width:140px}
.config-row input[type=text]{flex:1;min-width:180px}
.config-row input[type=number]{width:80px}
.config-row input[type=password]{flex:1;min-width:180px}
.btn{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500}
.btn-primary{background:#667eea;color:#fff}
.btn-primary:hover{background:#5a6fd6}
.btn-secondary{background:#f0f0f5;color:#333;border:1px solid #ddd}
.btn-secondary:hover{background:#e0e0e8}
/* Pipeline page */
.pipeline-page{display:flex;height:100%;gap:0}
.pipeline-left{width:220px;background:#fff;border-right:1px solid #e0e0e0;flex-shrink:0;display:flex;flex-direction:column;overflow:hidden}
.pipeline-left h4,.pipeline-right h4{padding:12px 16px;font-size:13px;font-weight:500;color:#888;border-bottom:1px solid #e0e0e0;flex-shrink:0}
.skill-item{padding:10px 16px;cursor:pointer;border-bottom:1px solid #f0f0f0;font-size:13px}
.skill-item:hover{background:#f0f0ff}
.skill-item .name{font-weight:500;color:#333}
.skill-item .desc{font-size:12px;color:#888;margin-top:2px}
.pipeline-main{flex:1;padding:20px;overflow-y:auto}
.pipeline-canvas{background:#fff;border-radius:8px;border:1px solid #e0e0e0;min-height:200px;padding:16px}
.pipeline-node{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;background:#f8f9fc;border:1px solid #667eea;border-radius:8px;margin:4px;font-size:13px;cursor:pointer;flex-wrap:wrap;transition:all .2s}
.pipeline-node:hover{background:#eef0f6;border-color:#667eea}
.pipeline-node .remove{color:#e74c3c;cursor:pointer;font-size:16px;line-height:1;font-weight:bold;opacity:.6}
.pipeline-node .remove:hover{opacity:1;color:#c0392b}
/* Pipeline right panel: saved chains */
.pipeline-right{width:220px;background:#fff;border-left:1px solid #e0e0e0;flex-shrink:0;display:flex;flex-direction:column;overflow:hidden}
.pipeline-right .saved-list{flex:1;overflow-y:auto}
.pipeline-right .saved-list .empty{padding:24px 16px;font-size:12px;color:#aaa;text-align:center}
.saved-item{display:flex;align-items:center;padding:10px 16px;font-size:13px;border-bottom:1px solid #f0f0f0;gap:6px}
.saved-item:hover{background:#f8f8ff}
.saved-item .name{flex:1;cursor:pointer;color:#333;font-weight:500}
.saved-item .name:hover{color:#667eea}
.saved-item .del{cursor:pointer;color:#e74c3c;font-size:16px;opacity:.5}
.saved-item .del:hover{opacity:1}
/* reasoning toggle (恢复) */
.reasoning-toggle{font-size:12px;color:#667eea;cursor:pointer;margin-top:6px;user-select:none}
.reasoning-body{border-left:3px solid #667eea;padding:8px 12px;margin:6px 0;background:#f8f9fc;font-size:12px;color:#555;white-space:pre-wrap;border-radius:0 6px 6px 0}
/* 旧的 saved-pipeline-item (已弃用) */
.chat-input-panel{flex-shrink:0;background:#fff;border-top:1px solid #e0e0e0}
.chat-input-tools{display:flex;gap:8px;padding:6px 16px;align-items:center;flex-wrap:wrap;border-bottom:1px solid #f0f0f0;background:#fafbfc}
.chat-input-tools select{padding:4px 8px;border:1px solid #ddd;border-radius:6px;font-size:12px;background:#fff;min-width:140px}
.chat-input-tools label{font-size:12px;color:#555;display:flex;align-items:center;gap:4px;cursor:pointer;user-select:none}
.chat-input-tools input[type=checkbox]{margin:0}
.chat-input-tools input[type=radio]{margin:0 2px 0 8px}
.chat-input-row{display:flex;gap:8px;padding:8px 16px}
.chat-input-row textarea{flex:1;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:14px;resize:none;outline:none;font-family:inherit}
.chat-input-row textarea:focus{border-color:#667eea}
.chat-input-row button{padding:10px 24px;background:#667eea;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500}
.chat-input-row button:hover{background:#5a6fd6}
.chat-input-row button:disabled{background:#999;cursor:not-allowed}
/* Saved pipeline list */
/* Modal */
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);z-index:999;justify-content:center;align-items:center}
.modal-overlay.active{display:flex}
.modal-box{background:#fff;border-radius:12px;padding:24px;min-width:360px;max-width:480px;box-shadow:0 8px 32px rgba(0,0,0,0.2)}
.modal-box h3{font-size:16px;margin-bottom:16px;color:#2d2d44}
.modal-box input[type=text]{width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:14px;outline:none;margin-bottom:16px}
.modal-box input[type=text]:focus{border-color:#667eea}
.modal-actions{display:flex;gap:8px;justify-content:flex-end}
/* 参数编辑行 */
.param-row{display:flex;gap:6px;align-items:center;margin-bottom:6px}
.param-row input[type=text]{flex:1;padding:6px 8px;border:1px solid #ddd;border-radius:6px;font-size:12px;outline:none;min-width:0}
.param-row input[type=text]:focus{border-color:#667eea}
.param-row .del{color:#e74c3c;cursor:pointer;font-size:16px;opacity:.5;flex-shrink:0}
.param-row .del:hover{opacity:1}
.param-row .sep{color:#888;font-size:12px;flex-shrink:0}
</style>
</head>
<body>
<div class="tab-bar">
  <div class="tab active" data-tab="chat" id="tab-chat">对话</div>
  <div class="tab" data-tab="config" id="tab-config" onclick="switchTab('config')">配置</div>
  <div class="tab" data-tab="pipeline" id="tab-pipeline" onclick="switchTab('pipeline')">Pipeline</div>
</div>

<!-- Chat Tab -->
<div class="tab-content active" id="page-chat">
  <div class="status-bar">
    <span class="status-item">模型: <span id="llm-info">-</span></span>
    <span class="status-item"><a href="#" onclick="switchTab('config');return false" style="color:#667eea;">设置</a></span>
    <span class="status-item"><a href="#" onclick="resetChat()" style="color:#667eea;">重置对话</a></span>
  </div>
  <div class="memory-stats" id="memory-stats">记忆: 0 条消息</div>
  <div id="chat-messages">
    <div class="msg assistant">你好！我是 Orchestrator 智能体。<br>输入问题，我会调用工具来回答。</div>
  </div>
  <div class="chat-input-panel">
    <div class="chat-input-tools">
      <select id="chat-pipeline-select"><option value="">-- 选择 Pipeline --</option></select>
      <label><input type="checkbox" id="chat-skillsub" onchange="onSkillSubToggle()"> skill-sub 优化</label>
      <label id="chat-skillsub-save-group" style="display:none;font-size:12px;color:#888">
        <label style="cursor:pointer"><input type="radio" name="skillsub-mode" value="single" checked> 单次执行</label>
        <label style="cursor:pointer"><input type="radio" name="skillsub-mode" value="save"> 保存到 Pipeline</label>
      </label>
      <span style="flex:1"></span>
      <div id="chat-search-presets" style="display:flex;gap:4px;flex-wrap:wrap;align-items:center"></div>
    </div>
    <div class="chat-input-row">
      <textarea id="chat-input" rows="2" placeholder="输入消息...（支持自然语言+文件选择）" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage()}"></textarea>
      <button id="send-btn" onclick="sendMessage()">发送</button>
    </div>
  </div>
</div>

<!-- Config Tab -->
<div class="tab-content" id="page-config">
  <div class="config-page">
    <div class="config-section">
      <h3>LLM 后端</h3>
      <div class="config-row">
        <label>后端类型</label>
        <select id="cfg-backend" onchange="onBackendChange()">
          <option value="lmstudio">LM Studio</option>
          <option value="ollama">Ollama</option>
          <option value="openai">OpenAI 兼容 (云端)</option>
        </select>
      </div>
      <div id="cfg-local-group">
        <div class="config-row">
          <label>地址</label>
          <input type="text" id="cfg-local-url" value="http://localhost:1234" onchange="onBackendChange()">
        </div>
      </div>
      <div id="cfg-openai-group" style="display:none">
        <div class="config-row">
          <label>Base URL</label>
          <input type="text" id="cfg-base-url" placeholder="https://api.openai.com" onchange="onBackendChange()">
        </div>
        <div class="config-row">
          <label>API Key</label>
          <input type="password" id="cfg-api-key" placeholder="sk-..." onchange="onBackendChange()">
        </div>
      </div>
      <div class="config-row">
        <label>模型</label>
        <select id="cfg-model" style="flex:1;min-width:200px">
          <option value="">-- 选择模型 --</option>
        </select>
        <button class="btn btn-secondary" onclick="loadModels()">刷新</button>
      </div>
      <div class="config-row">
        <label>超时(秒)</label>
        <input type="number" id="cfg-timeout" value="180" min="30" max="1800" step="30">
        <span style="font-size:12px;color:#888">链步执行超时</span>
        <label style="margin-left:16px">Max Tokens</label>
        <input type="number" id="cfg-maxtokens" value="4096" min="256" max="131072" step="1024">
        <span style="font-size:12px;color:#888">每步最大输出</span>
      </div>
      <div class="config-row">
        <button class="btn btn-primary" onclick="testLLM()">测试连接</button>
        <button class="btn btn-primary" onclick="saveConfig()">保存配置</button>
        <span id="cfg-status" style="font-size:12px;color:#888;margin-left:8px"></span>
      </div>
    </div>
    <!-- 搜索配置 -->
    <div class="config-section">
      <h3>联网搜索</h3>
      <div style="font-size:12px;color:#888;margin-bottom:12px">
        配置搜索后端，智能体会在对话中使用。用户可在对话框中输入"搜索 XXX"让 LLM 调用搜索。
        也可添加搜索预设，在对话输入栏快速选用。
      </div>
      <div class="config-row">
        <label>搜索后端</label>
        <select id="cfg-search-backend" onchange="onSearchBackendChange()">
          <option value="duckduckgo">DuckDuckGo (免费，无需 Key)</option>
          <option value="google">Google Custom Search (需 API Key + CX)</option>
          <option value="bing">Bing Search (需 API Key)</option>
          <option value="custom">自定义 API</option>
        </select>
      </div>
      <!-- Google 配置 -->
      <div id="cfg-search-google-group" style="display:none">
        <div class="config-row">
          <label>API Key</label>
          <input type="password" id="cfg-search-google-key" placeholder="Google API Key" onchange="onSearchBackendChange()">
        </div>
        <div class="config-row">
          <label>Search CX</label>
          <input type="text" id="cfg-search-google-cx" placeholder="Custom Search Engine ID (cx)" onchange="onSearchBackendChange()">
        </div>
      </div>
      <!-- Bing 配置 -->
      <div id="cfg-search-bing-group" style="display:none">
        <div class="config-row">
          <label>API Key</label>
          <input type="password" id="cfg-search-bing-key" placeholder="Bing Search API Key" onchange="onSearchBackendChange()">
        </div>
      </div>
      <!-- 自定义 API 配置 -->
      <div id="cfg-search-custom-group" style="display:none">
        <div class="config-row">
          <label>搜索 URL</label>
          <input type="text" id="cfg-search-url" placeholder="https://api.example.com/search?q={q}&key={key}" onchange="onSearchBackendChange()">
        </div>
        <div class="config-row">
          <label>API Key</label>
          <input type="password" id="cfg-search-key" placeholder="可选" onchange="onSearchBackendChange()">
        </div>
      </div>
      <!-- 搜索预设 (快速搜索) -->
      <div style="margin-top:12px;padding-top:12px;border-top:1px solid #eee">
        <div style="font-size:13px;font-weight:500;color:#2d2d44;margin-bottom:8px">搜索预设</div>
        <div style="font-size:12px;color:#888;margin-bottom:8px">
          预设搜索词会出现在对话输入栏的快速搜索按钮中，点击即可搜索。支持在对话框中输入"搜索 XXX"让 LLM 自动生成搜索命令。
        </div>
        <div class="config-row">
          <input type="text" id="cfg-search-preset-input" placeholder="输入预设搜索词（如：今日AI新闻）" style="flex:1;min-width:180px">
          <button class="btn btn-secondary" onclick="addSearchPreset()">添加预设</button>
        </div>
        <div id="cfg-search-presets" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px"></div>
      </div>
    </div>
    <!-- 提示词 -->
    <div class="config-section">
      <h3>提示词</h3>
      <div class="config-row" style="flex-direction:column;align-items:stretch">
        <label style="margin-bottom:4px">系统提示词（只读）</label>
        <textarea id="cfg-system-prompt" rows="6" readonly style="width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:12px;font-family:monospace;background:#f8f8f8;color:#555;resize:vertical;outline:none;line-height:1.6"></textarea>
      </div>
      <div class="config-row" style="flex-direction:column;align-items:stretch;margin-top:12px">
        <label style="margin-bottom:4px">用户提示词（可编辑，追加到系统提示词末尾）</label>
        <textarea id="cfg-user-prompt" rows="3" placeholder="输入自定义指令，如：用中文回答、输出简洁、优先提供代码示例等。" style="width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:13px;resize:vertical;outline:none;font-family:inherit;line-height:1.6"></textarea>
      </div>
    </div>
    <!-- 技能路径 -->
    <div class="config-section">
      <h3>技能路径</h3>
      <div style="font-size:12px;color:#888;margin-bottom:8px">
        默认扫描自包含 skills/ 目录。可添加自定义路径，留空则使用默认路径。
      </div>
      <div id="cfg-skill-dirs-list" style="margin-bottom:8px"></div>
      <div class="config-row">
        <input type="text" id="cfg-skill-dir-input" placeholder="输入技能目录路径..." style="flex:1;min-width:180px">
        <button class="btn btn-secondary" onclick="addSkillDir()">添加路径</button>
      </div>
    </div>
  </div>
</div>

<!-- Pipeline Tab -->
<div class="tab-content" id="page-pipeline">
  <div class="pipeline-page">
    <!-- 左栏: 可用技能 -->
    <div class="pipeline-left">
      <h4>可用技能</h4>
      <div id="skill-list" style="flex:1;overflow-y:auto">加载中...</div>
    </div>
    <!-- 中栏: 编排区 -->
    <div class="pipeline-main">
      <div style="display:flex;gap:8px;margin-bottom:12px;align-items:center;flex-wrap:wrap">
        <h3 style="font-size:15px;font-weight:500;flex:1">当前 Pipeline</h3>
        <button class="btn btn-secondary" onclick="addGroup('par')">+ 并行组</button>
        <button class="btn btn-secondary" onclick="addGroup('loop')">+ 循环组</button>
        <button class="btn btn-secondary" onclick="savePipeline()">保存</button>
        <button class="btn btn-primary" onclick="runPipeline()">运行</button>
        <button class="btn btn-secondary" onclick="clearPipeline()">清空</button>
      </div>
      <div style="font-size:12px;color:#888;margin-bottom:8px">
        双击左侧技能添加 | 节点模式可切换: <span style="color:#667eea">seq</span> 串行 / <span style="color:#27ae60">par</span> 并行 / <span style="color:#e67e22">loop</span> 循环
      </div>
      <div class="pipeline-canvas" id="pipeline-canvas">
        <span style="color:#aaa;font-size:13px">点击左侧技能添加到此</span>
      </div>
      <div id="pipeline-result" style="margin-top:12px;display:none">
        <h4 style="font-size:14px;font-weight:500;margin-bottom:8px">运行结果</h4>
        <pre id="pipeline-output" style="background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:16px;font-size:12px;max-height:300px;overflow:auto;white-space:pre-wrap"></pre>
      </div>
    </div>
    <!-- 右栏: 已保存 Pipeline -->
    <div class="pipeline-right">
      <h4>已保存 Pipeline</h4>
      <div class="saved-list" id="saved-pipeline-list">
        <div class="empty">暂无已保存的 Pipeline</div>
      </div>
    </div>
  </div>
</div>

<!-- 保存 Pipeline 模态框 -->
<div class="modal-overlay" id="save-modal">
  <div class="modal-box">
    <h3>保存 Pipeline</h3>
    <input type="text" id="save-modal-name" placeholder="输入 Pipeline 名称..." autofocus>
    <div class="modal-actions">
      <button class="btn btn-secondary" onclick="closeSaveModal()">取消</button>
      <button class="btn btn-primary" onclick="confirmSavePipeline()">保存</button>
    </div>
  </div>
</div>

<!-- 节点参数编辑模态框 -->
<div class="modal-overlay" id="node-params-modal">
  <div class="modal-box" style="min-width:400px;max-width:520px">
    <h3>节点参数</h3>
    <div style="margin-bottom:12px">
      <label style="font-size:13px;color:#666;display:block;margin-bottom:4px">显示名称</label>
      <input type="text" id="node-params-display" style="width:100%;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;outline:none">
    </div>
    <div style="margin-bottom:12px">
      <label style="font-size:13px;color:#666;display:block;margin-bottom:4px">模式</label>
      <select id="node-params-mode" style="padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;outline:none">
        <option value="seq">seq — 串行</option>
        <option value="par">par — 并行组</option>
        <option value="loop">loop — 循环组</option>
      </select>
    </div>
    <div style="margin-bottom:8px">
      <label style="font-size:13px;color:#666;display:block;margin-bottom:4px">
        参数（key=value，可选）
        <span style="font-size:11px;color:#aaa"> — skill-sub 优化或执行时使用</span>
      </label>
      <div id="node-params-rows"></div>
      <button class="btn btn-secondary" onclick="addParamRow()" style="font-size:12px;margin-top:4px">+ 添加参数</button>
    </div>
    <div class="modal-actions">
      <button class="btn btn-secondary" onclick="closeNodeParams()">取消</button>
      <button class="btn btn-primary" onclick="saveNodeParams()">确定</button>
    </div>
  </div>
</div>

<script src="/static/web_ui.js"></script>
</body>
</html>"""

    # ==================================================================
    # API Handlers
    # ==================================================================

    def _get_skill_dirs(self) -> list:
        """从配置获取自定义技能扫描目录"""
        return self.config.data.get("skills", {}).get("dirs", []) if self.config else []

    def _handle_chat_post(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        if body.get("reset"):
            if self.agent:
                self.agent.reset()
            self._send_json({"success": True})
            return
        msg = body.get("message", "")
        pipeline_id = body.get("pipeline_id", "")
        skill_sub = body.get("skill_sub", False)
        save_chain = body.get("save_chain", False)

        # 没有链 → 回退到原始 ReAct（零闲聊）
        if not pipeline_id:
            try:
                answer = self.agent.run(msg) if self.agent else "Agent 未初始化"
                self._send_json({"success": True, "text": answer, "kb": ""})
            except Exception as e:
                logger.exception("chat error")
                self._send_json({"success": False, "error": str(e)})
            return

        # ================================================================
        # 有链 → 链驱动执行（多轮次输出）
        # ================================================================
        pipe_path = os.path.join(_DIR, "chains", pipeline_id + ".json")
        if not os.path.isfile(pipe_path):
            self._send_json({"success": False, "error": f"Pipeline '{pipeline_id}' 未找到"})
            return

        try:
            with open(pipe_path, "r", encoding="utf-8") as f:
                pipeline = json.load(f)
        except Exception as e:
            self._send_json({"success": False, "error": f"读取 Pipeline 失败: {e}"})
            return

        tree = pipeline.get("tree", pipeline.get("nodes", []))
        if not tree:
            self._send_json({"success": False, "error": "Pipeline 为空，请先编排技能"})
            return

        rounds = []

        # ─── Round 1: 需求分析 ───
        analysis = self._round_analysis(tree, msg, pipeline_id)
        rounds.append({"type": "analysis", "title": "需求分析", "content": analysis})

        # ─── Round 2 (if skill-sub): 优化 ───
        optimized_steps = []
        cohesion_checks = []
        milestones = []
        if skill_sub:
            opt_result = self._skill_sub_optimize(tree, msg, pipeline_id)
            optimized_steps = opt_result.get("steps", [])
            cohesion_checks = opt_result.get("cohesion_checks", [])
            milestones = opt_result.get("milestones", [])
            opt_content = self._format_optimization_report(optimized_steps, cohesion_checks, milestones)
            rounds.append({"type": "optimization", "title": "skill-sub 优化", "content": opt_content,
                           "steps": optimized_steps, "cohesion_checks": cohesion_checks, "milestones": milestones})

        # ─── Round 3+: 执行 ───
        if optimized_steps:
            # 按优化步骤逐步执行
            step_results, exec_content = self._execute_optimized_steps(optimized_steps, cohesion_checks, milestones, msg)
        else:
            # 直接用 _execute_tree（支持 seq/par/loop）
            output_lines = []
            step_count = [0]
            self._execute_tree(tree, output_lines, 0, step_count, prev_output=msg)
            exec_content = "\n".join(output_lines)
            step_results = []

        rounds.append({"type": "execution", "title": "执行结果", "content": exec_content, "steps": step_results})

        # ─── 组装响应 ───
        self._send_json({
            "success": True,
            "rounds": rounds,
            "chain": {"pipeline": pipeline_id},
        })

        # ---------- step 4: 保存优化链 ----------
        if save_chain:
            try:
                # 将优化结果保存到 extra 字段
                enriched_tree = self._enrich_tree_with_optimization(tree, optimized_steps, cohesion_checks, milestones)
                pipeline["tree"] = enriched_tree
                pipeline["nodes"] = optimized_steps
                with open(pipe_path, "w", encoding="utf-8") as f:
                    json.dump(pipeline, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"保存优化链失败: {e}")

        self._send_json({
            "success": True,
            "text": full_output,
            "chain": chain_info,
            "kb": "",
        })

    def _handle_chat_get(self):
        self._send_json({"success": True, "messages": []})

    def _serve_config(self):
        cfg = self.config.data if self.config else {}
        # 合并搜索配置
        result = {}
        llm = cfg.get("llm", {})
        for k in ("backend","model","timeout","max_tokens","api_key","base_url","local_url"):
            if k in llm:
                result[k] = llm[k]
        search = cfg.get("search", {})
        result["search_backend"] = search.get("backend", "duckduckgo")
        result["search_url"] = search.get("url", "")
        result["search_key"] = search.get("api_key", "")
        result["search_google_key"] = search.get("google_key", "")
        result["search_google_cx"] = search.get("google_cx", "")
        result["search_bing_key"] = search.get("bing_key", "")
        result["search_presets"] = search.get("presets", [])
        # 提示词
        result["user_prompt"] = cfg.get("prompt", {}).get("user", "")
        result["system_prompt_raw"] = "核心工作方式：执行技能链（Pipeline），按步骤逐一执行直到完成。\n[完整提示词请查看 agent_loop.py 中的 REACT_SYSTEM_PROMPT]"
        # 技能路径
        skill_dirs = cfg.get("skills", {}).get("dirs", [])
        result["skill_dirs"] = skill_dirs if skill_dirs else []
        self._send_json(result)

    def _handle_config_post(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        if self.config and body:
            llm = self.config.data["llm"]
            if "backend" in body:
                llm["backend"] = body["backend"]
            if "model" in body:
                llm["model_name"] = body["model"]
            if "timeout" in body:
                llm["timeout"] = int(body["timeout"])
            if "maxtokens" in body:
                llm["max_tokens"] = int(body["maxtokens"])
            if "api_key" in body:
                llm["api_key"] = body["api_key"]
            if "base_url" in body:
                llm["base_url"] = body["base_url"]
            if "local_url" in body:
                u = body["local_url"].rstrip("/")
                if llm["backend"] == "ollama":
                    llm["ollama_url"] = u
                else:
                    llm["lmstudio_url"] = u
            # 搜索配置
            search = self.config.data.get("search", {})
            if "search_backend" in body:
                search["backend"] = body["search_backend"]
            if "search_url" in body:
                search["url"] = body["search_url"]
            if "search_key" in body:
                search["api_key"] = body["search_key"]
            if "search_google_key" in body:
                search["google_key"] = body["search_google_key"]
            if "search_google_cx" in body:
                search["google_cx"] = body["search_google_cx"]
            if "search_bing_key" in body:
                search["bing_key"] = body["search_bing_key"]
            if "search_presets" in body:
                search["presets"] = body["search_presets"]
            self.config.data["search"] = search
            # 提示词
            if "user_prompt" in body:
                if "prompt" not in self.config.data:
                    self.config.data["prompt"] = {}
                self.config.data["prompt"]["user"] = body["user_prompt"]
            # 技能路径
            if "skill_dirs" in body:
                if "skills" not in self.config.data:
                    self.config.data["skills"] = {}
                self.config.data["skills"]["dirs"] = body["skill_dirs"]
            cfg_path = os.path.join(os.path.dirname(_DIR), "data", "config", "settings.json")
            try:
                os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(self.config.data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            self._recreate_llm()
        self._send_json({"success": True})

    def _serve_llm_models(self):
        if not self.llm:
            self._send_json({"models": []})
            return
        models = self.llm.list_models()
        self._send_json({"models": models})

    def _serve_llm_test(self):
        if not self.llm:
            self._send_json({"success": False, "msg": "LLM 未初始化"})
            return
        ok, msg = self.llm.check_connection()
        self._send_json({"success": ok, "msg": msg})

    def _serve_skills(self):
        if not SKILL_AVAILABLE:
            self._send_json({"skills": []})
            return
        try:
            from orchestrator.skill_scanner import scan_skills
            # 使用配置的自定义路径，否则用默认
            custom_dirs = self._get_skill_dirs()
            skills = scan_skills(*custom_dirs) if custom_dirs else scan_skills()
            data = []
            for s in skills:
                data.append({
                    "name": s.name, "display_name": s.display_name,
                    "description": s.description, "version": s.version,
                })
            self._send_json({"skills": data})
        except Exception as e:
            self._send_json({"skills": [], "error": str(e)})

    def _skill_scan_with_config(self) -> list:
        """统一用配置路径扫描技能"""
        from orchestrator.skill_scanner import scan_skills
        custom_dirs = self._get_skill_dirs()
        return scan_skills(*custom_dirs) if custom_dirs else scan_skills()

    def _serve_pipelines(self):
        chains_dir = os.path.join(_DIR, "chains")
        pipelines = []
        if os.path.isdir(chains_dir):
            for f in sorted(os.listdir(chains_dir)):
                if f.endswith(".json"):
                    pipelines.append(f.replace(".json", ""))
        self._send_json({"pipelines": pipelines})

    def _serve_pipeline(self, name):
        path = os.path.join(_DIR, "chains", name + ".json")
        if not os.path.isfile(path):
            self._send_json({"error": "not found"}, 404)
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._send_json(data)

    def _handle_pipeline_save(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        name = body.get("name", "").strip()
        if not name:
            self._send_json({"success": False, "error": "名称不能为空"})
            return
        chains_dir = os.path.join(_DIR, "chains")
        os.makedirs(chains_dir, exist_ok=True)
        # 同时保存扁平 nodes 和完整 tree 结构
        data = {"name": name, "nodes": body.get("nodes", []), "tree": body.get("tree", [])}
        path = os.path.join(chains_dir, name + ".json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_pipeline_delete(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        name = body.get("name", "").strip()
        if not name:
            self._send_json({"success": False, "error": "名称不能为空"})
            return
        path = os.path.join(_DIR, "chains", name + ".json")
        try:
            if os.path.isfile(path):
                os.remove(path)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)})

    def _handle_pipeline_run(self):
        import time
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        # 优先用 tree（完整结构），回退到 nodes（扁平）
        nodes = body.get("tree", body.get("nodes", []))
        if not nodes:
            self._send_json({"output": "", "error": "没有节点"})
            return
        start = time.time()
        output_lines = []
        step_count = [0]
        self._execute_tree(nodes, output_lines, 0, step_count)
        elapsed = int((time.time() - start) * 1000)
        self._send_json({
            "output": "\n".join(output_lines),
            "steps": step_count[0],
            "latency_ms": elapsed,
        })

    def _execute_tree(self, nodes, output: list, depth: int, step_counter: list = None,
                      prev_output: str = "", indent: str = None):
        """执行 Pipeline 树。技能节点通过 LLM 真实调用。"""
        import concurrent.futures
        indent = indent or ("  " * depth)
        for i, node in enumerate(nodes):
            mode = node.get("mode", "seq")
            name = node.get("name", "")
            display = node.get("display", name)
            children = node.get("children", [])
            params = node.get("params", {})

            if mode == "par":
                names = [c.get("display", c.get("name","(unnamed)")) for c in children]
                output.append(f"{indent}[并行组] {' | '.join(names)}")
                # 真正的并行执行
                par_results = [None] * len(children)
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(children)) as executor:
                    future_map = {}
                    for ci, child in enumerate(children):
                        cn = child.get("name","")
                        if cn:
                            cp = child.get("params", {})
                            cd = child.get("display", cn)
                            future = executor.submit(self._execute_single_skill, cn, cd, cp, prev_output)
                            future_map[future] = ci
                    for future in concurrent.futures.as_completed(future_map):
                        ci = future_map[future]
                        try:
                            par_results[ci] = future.result()
                        except Exception as e:
                            par_results[ci] = f"（并行错误: {e}）"
                for ci, r in enumerate(par_results):
                    if r:
                        if step_counter is not None: step_counter[0] += 1
                        output.append(f"{indent}  [{names[ci]}] {r[:300]}")
                output.append(f"{indent}[并行组] 完成")

            elif mode == "loop":
                times = node.get("loop_times", 3) or node.get("times", 3)
                output.append(f"{indent}[循环组] {display} ×{times}")
                loop_input = prev_output
                for t in range(times):
                    output.append(f"{indent}  第 {t+1} 次:")
                    # 循环体：输出不回传（避免指数增长），但可以为每个循环设置独立上下文
                    self._execute_tree(children, output, depth + 1, step_counter,
                                       prev_output=loop_input, indent=indent + "    ")

            else:  # seq
                if step_counter is not None: step_counter[0] += 1
                step_num = step_counter[0] if step_counter else i + 1
                output.append(f"{indent}[{step_num}] {display}")
                if name:
                    result = self._execute_single_skill(name, display, params, prev_output)
                    output.append(f"{indent}  结果: {result[:500]}")
                    prev_output = result  # 传递到下一步
                else:
                    prev_output = ""

    def _execute_single_skill(self, name: str, display: str, params: dict, prev_output: str) -> str:
        """通过 LLM 直接执行单个技能节点。不走 agent.run() 的 ReAct 循环。"""
        if not self.llm:
            raise RuntimeError(f"LLM 未初始化，无法执行 Pipeline")

        # 从配置读取超时和 max_tokens
        llm_cfg = self.config.data.get("llm", {}) if self.config else {}
        exec_timeout = int(llm_cfg.get("timeout", 180))
        exec_max_tokens = int(llm_cfg.get("max_tokens", 4096))

        # 读 SKILL.md 摘要，注入到 prompt
        skill_desc = self._read_skill_summary(name)

        param_str = ""
        if params:
            param_str = "\n".join(f"  {k}: {v}" for k, v in params.items())

        context = ""
        if prev_output and prev_output.strip():
            context = f"\n前一步骤输出作为输入:\n{prev_output[:2000]}"

        prompt = (
            f"你正在执行步骤「{display}」。\n\n"
            f"技能说明:\n{skill_desc or '（无详细说明）'}"
            f"{'参数:\n' + param_str if param_str else ''}"
            f"{context}\n\n"
            f"请直接输出该步骤的执行结果。不要解释过程，不要输出 JSON。"
        )

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            fut = pool.submit(lambda: self.llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=exec_max_tokens
            ))
            response = fut.result(timeout=exec_timeout)

        return (response or "").strip()[:3000] or "（空结果）"

    def _read_skill_summary(self, name: str) -> str:
        """读取技能的 SKILL.md 摘要"""
        try:
            skills = self._skill_scan_with_config()
            for s in skills:
                if s.name == name and s.path:
                    md_path = os.path.join(s.path, "SKILL.md")
                    if os.path.isfile(md_path):
                        with open(md_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        # 提取前 500 字摘要
                        lines = content.split("\n")
                        summary_lines = []
                        in_front = False
                        for line in lines:
                            if line.strip() == "---":
                                if not in_front:
                                    in_front = True
                                    continue
                                else:
                                    break
                        after_front = False
                        for line in lines:
                            if line.strip() == "---":
                                if not after_front:
                                    after_front = True
                                    continue
                            if after_front and line.strip():
                                summary_lines.append(line)
                                if len("\n".join(summary_lines)) > 500:
                                    break
                        if summary_lines:
                            return "\n技能说明:\n" + "\n".join(summary_lines[:10])
            return ""
        except Exception:
            return ""

    # ==================================================================
    # skill-sub 优化 + 链驱动执行
    # ==================================================================

    def _default_plan(self, tree):
        """无 skill-sub 时的默认执行计划：扁平化为串行步骤"""
        steps = []
        def _flatten(nodes, depth=0):
            for node in nodes:
                mode = node.get("mode", "seq")
                name = node.get("name", "")
                display = node.get("display", name)
                children = node.get("children", [])
                if mode == "par":
                    for c in children:
                        _flatten([c], depth)
                elif mode == "loop":
                    times = node.get("loop_times", 3) or node.get("times", 3)
                    for t in range(times):
                        _flatten(children, depth)
                else:
                    steps.append({
                        "name": display,
                        "skill": name,
                        "params": node.get("params", {}),
                        "input_spec": "",
                        "output_spec": "",
                    })
        _flatten(tree)
        return steps, [], []

    def _skill_sub_optimize(self, tree, task, pipeline_id):
        """
        真正的 skill-sub 优化：读 SKILL.md → 算法比较输入输出 → 自动黏连点/里程碑。
        LLM 只在格式模糊时做回退判断。
        """
        # ── step 1: 读取链中所有技能的 SKILL.md frontmatter ──
        skills_specs = {}  # {skill_name: {"triggers":[],"tags":[],"desc":"","display":"","params":{}}}
        def _collect_skills(nodes, depth=0):
            for n in nodes:
                name = n.get("name", "")
                if name and name not in skills_specs:
                    spec = self._extract_skill_spec(name)
                    skills_specs[name] = spec
                for c in n.get("children", []):
                    _collect_skills([c], depth+1)
        _collect_skills(tree)

        # ── step 2: 展开树为扁平步骤 ──
        raw_steps = []
        def _flatten(nodes, depth=0):
            for n in nodes:
                mode = n.get("mode", "seq")
                name = n.get("name", "")
                display = n.get("display", name)
                children = n.get("children", [])
                params = n.get("params", {})
                if mode == "par":
                    raw_steps.append({"type":"par","display":display,"children_names":[c.get("display",c.get("name","")) for c in children]})
                    for c in children:
                        cn = c.get("name","")
                        if cn:
                            raw_steps.append({"type":"seq","name":cn,"display":c.get("display",cn),"params":c.get("params",{}),"skill_spec":skills_specs.get(cn,{})})
                elif mode == "loop":
                    times = n.get("loop_times", 3) or n.get("times", 3)
                    raw_steps.append({"type":"loop","display":display,"times":times})
                    for t in range(times):
                        _flatten(children, depth+1)
                else:
                    raw_steps.append({"type":"seq","name":name,"display":display,"params":params,"skill_spec":skills_specs.get(name,{})})
        _flatten(tree)

        # ── step 3: 算法级步骤间黏连检查 ──
        cohesion_checks = []
        optimized_steps = []

        for i, step in enumerate(raw_steps):
            if step.get("type") == "par":
                optimized_steps.append({"name": step["display"], "skill": "", "params": {}, "input_spec": "并行", "output_spec": "并行"})
                continue
            if step.get("type") == "loop":
                optimized_steps.append({"name": step["display"], "skill": "", "params": {}, "input_spec": "循环", "output_spec": "循环"})
                continue

            # 纯算法：比较当前技能的 tags/triggers 和上一步的 output
            prev_step = optimized_steps[-1] if optimized_steps else None
            spec = step.get("skill_spec", {})
            prev_spec = prev_step.get("_skill_spec", {}) if prev_step else {}

            check = {
                "from": prev_step["name"] if prev_step else "(开始)",
                "to": step["display"],
                "compatible": True,
                "transform": "",
                "note": "",
            }

            # 算法规则 1: tags 匹配检查
            cur_tags = set(spec.get("tags", []))
            prev_tags = set(prev_spec.get("tags", []))
            if prev_tags and cur_tags:
                # 如果前一步是"分析"类，当前是"生成"类 → 需要转换
                analysis_tags = {"analysis","analyze","统计","分析","计算","检测","test","check"}
                generation_tags = {"generate","create","write","生成","创建","写作","report"}
                if prev_tags & analysis_tags and cur_tags & generation_tags:
                    check["compatible"] = False
                    check["transform"] = f"将上一步的分析结果格式化为当前步骤可用的输入格式"
                    check["note"] = f"分析→生成 格式转换"

            # 算法规则 2: 名称推断
            if not check["compatible"]:
                prev_name = (prev_step["name"] if prev_step else "").lower()
                cur_name = step["display"].lower()
                if ("json" in prev_name or "csv" in prev_name or "数据" in prev_name) and \
                   ("plot" in cur_name or "chart" in cur_name or "图" in cur_name or "report" in cur_name):
                    # 数据→图表，不需要转换（数据本身就是输入）
                    check["compatible"] = True
                    check["note"] = "数据可直接作为输入"

            # 算法规则 3: 模糊 → 回退 LLM 做补充判断（限 1 次 LLM 调用）
            if i > 0 and prev_step and not prev_step.get("_llm_checked"):
                # 只在真实不确定时才问 LLM
                prev_desc = prev_spec.get("description", "")
                cur_desc = spec.get("description", "")
                if prev_desc and cur_desc and not check.get("_forced"):
                    try:
                        llm_check = self._llm_cohesion_check(prev_step["name"], prev_desc, step["display"], cur_desc)
                        if llm_check:
                            check["compatible"] = llm_check.get("compatible", True)
                            check["transform"] = llm_check.get("transform", "")
                            check["note"] = llm_check.get("note", check["note"])
                            step["_llm_checked"] = True
                    except Exception:
                        pass

            cohesion_checks.append(check)

            # 如果黏连不兼容 → 插入转换步骤
            if not check["compatible"] and check["transform"]:
                transform_step = {
                    "name": f"转换: {check['from']} → {check['to']}",
                    "skill": "",
                    "params": {"transform": check["transform"], "input": check["from"], "output": check["to"]},
                    "input_spec": prev_step["name"] if prev_step else "",
                    "output_spec": step["display"],
                    "_is_transform": True,
                }
                optimized_steps.append(transform_step)

            optimized_steps.append({
                "name": step["display"],
                "skill": step.get("name", ""),
                "params": step.get("params", {}),
                "input_spec": spec.get("description", "")[:200],
                "output_spec": spec.get("description", "")[:200],
                "_skill_spec": spec,
            })

        # ── step 4: 自动里程碑 ──
        milestones = []
        boundary_keywords = ["完成", "结果", "输出", "报告", "final", "output", "result", "总结", "汇总"]
        for i, step in enumerate(optimized_steps):
            name = step.get("name", "").lower()
            for kw in boundary_keywords:
                if kw in name:
                    milestones.append({"name": f"{step['name']}", "at": step["name"]})
                    break

        # ── step 5: 清除内部字段 ──
        for s in optimized_steps:
            s.pop("_skill_spec", None)
            s.pop("_llm_checked", None)
            s.pop("_is_transform", None)

        return {"steps": optimized_steps, "cohesion_checks": cohesion_checks, "milestones": milestones}

    def _extract_skill_spec(self, name: str) -> dict:
        """读取 SKILL.md 提取技能规格（触发词、标签、描述）"""
        try:
            content = self._read_skill_summary(name)
            # 也尝试从 skill_scanner 获取结构化的 SkillInfo
            skills = self._skill_scan_with_config()
            for s in skills:
                if s.name == name or s.display_name == name:
                    return {
                        "name": s.name,
                        "display": s.display_name,
                        "description": s.description,
                        "tags": s.tags,
                        "triggers": s.triggers,
                        "version": s.version,
                    }
        except Exception:
            pass
        return {"name": name, "display": name, "description": content, "tags": [], "triggers": []}

    def _llm_cohesion_check(self, prev_name, prev_desc, cur_name, cur_desc) -> dict:
        """LLM 补充判断：仅当算法无法确定时调用"""
        if not self.llm:
            return {"compatible": True, "transform": "", "note": "（未检查）"}
        try:
            prompt = (
                f"判断两个技能步骤之间的兼容性。\n\n"
                f"上一步: {prev_name} — {prev_desc[:300]}\n"
                f"下一步: {cur_name} — {cur_desc[:300]}\n\n"
                f"问题：下一步能否直接使用上一步的输出作为输入？\n"
                f"如果可以直接使用，输出: compatible\n"
                f"如果需要转换，输出: transform:xxx, note:xxx\n"
                f"只输出结论，不要解释。"
            )
            resp = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=256)
            text = (resp or "").strip().lower()
            if "transform" in text:
                return {"compatible": False, "transform": text.replace("transform:","").split(",")[0].strip(), "note": text}
            return {"compatible": True, "transform": "", "note": "LLM 判断兼容"}
        except Exception:
            return {"compatible": True, "transform": "", "note": ""}

    def _llm_transform(self, prev_output, transform_desc):
        """LLM 执行黏连点转换"""
        if not self.llm:
            return prev_output
        try:
            prompt = f"请执行以下数据转换：\n\n转换要求: {transform_desc}\n\n输入数据:\n{prev_output[:2000]}\n\n请直接输出转换后的结果，不要解释。"
            response = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=2048)
            return (response or "").strip()[:3000] or prev_output
        except Exception:
            return prev_output

    def _execute_chain_step(self, step, prev_output, step_idx):
        """执行链中的单个步骤。用 llm.chat() 直接输出，不走 ReAct。"""
        if not self.llm:
            raise RuntimeError("LLM 未初始化，无法执行")

        llm_cfg = self.config.data.get("llm", {}) if self.config else {}
        exec_max_tokens = int(llm_cfg.get("max_tokens", 4096))

        step_name = step.get("name", step.get("skill", f"步骤{step_idx}"))
        skill_name = step.get("skill", step.get("name", ""))
        params = step.get("params", {})
        input_spec = step.get("input_spec", "")

        skill_desc = self._read_skill_summary(skill_name)
        param_str = ""
        if params:
            param_str = "\n".join(f"  {k}: {v}" for k, v in params.items())
        context = ""
        if prev_output and prev_output.strip():
            context = f"\n前一步输出:\n{prev_output[:2000]}"
        spec = ""
        if input_spec:
            spec = f"\n期望输入格式: {input_spec}"

        prompt = (
            f"执行步骤「{step_name}」\n\n"
            f"技能: {skill_name}\n"
            f"{skill_desc}"
            f"{'参数:\n' + param_str if param_str else ''}"
            f"{spec}{context}\n\n"
            f"输出该步骤的执行结果。不要解释。"
        )
        response = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=exec_max_tokens)
        return {"name": step_name, "success": True, "output": (response or "").strip()[:5000]}

    def _enrich_tree_with_optimization(self, tree, steps, cohesion_checks, milestones):
        """将优化结果写入 tree 节点的 extra 字段"""
        enriched = list(tree)
        for step in steps:
            skill = step.get("skill", "")
            for node in enriched:
                if node.get("name") == skill:
                    node.setdefault("extra", {})
                    node["extra"]["skill_sub_step"] = step.get("name", "")
                    node["extra"]["input_spec"] = step.get("input_spec", "")
                    node["extra"]["output_spec"] = step.get("output_spec", "")
                    node["extra"]["params"] = step.get("params", {})
                    node["extra"]["cohesion_checks"] = cohesion_checks
                    node["extra"]["milestones"] = milestones
        return enriched

    # ==================================================================
    # 链驱动对话：轮次方法
    # ==================================================================

    def _round_analysis(self, tree, task, pipeline_id) -> str:
        """Round 1: LLM 分析任务需求"""
        skill_names = []
        def _collect(nodes):
            for n in nodes:
                if n.get("name"):
                    skill_names.append(n.get("display", n["name"]))
                for c in n.get("children", []):
                    _collect([c])
        _collect(tree)
        skills_str = " → ".join(skill_names) if skill_names else "（空链）"

        if not self.llm:
            raise RuntimeError("LLM 未初始化，无法分析任务")

        try:
            prompt = (
                f"分析以下任务和技能链。\n\n"
                f"## 用户任务\n{task}\n\n"
                f"## Pipeline 名称\n{pipeline_id}\n\n"
                f"## 技能链\n{skills_str}\n\n"
                f"请分析：\n"
                f"1. 这个任务需要哪些步骤来完成？\n"
                f"2. 每个步骤对应链中的哪个技能？\n"
                f"3. 预期的最终输出是什么？\n\n"
                f"用简洁的语言描述。"
            )
            resp = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=1024)
            return (resp or "").strip()[:2000] or skills_str
        except Exception as e:
            return f"任务: {task}\n技能链: {skills_str}\n（分析异常: {e}）"

    def _format_optimization_report(self, steps, checks, milestones) -> str:
        """格式化为可读的优化报告"""
        lines = [f"优化完成: {len(steps)} 个步骤"]
        for c in checks:
            icon = "✅" if c.get("compatible") else "🔧"
            lines.append(f"{icon} {c.get('from','')} → {c.get('to','')}: {c.get('note','')}")
        if milestones:
            lines.append("")
            lines.append("🏁 里程碑:")
            for m in milestones:
                lines.append(f"   · {m.get('name','')} (在 {m.get('at','')})")
        lines.append("")
        for i, s in enumerate(steps):
            name = s.get("name", f"步骤{i+1}")
            skill = s.get("skill", "")
            params = s.get("params", {})
            p_str = ""
            if params:
                p_str = " [" + ", ".join(f"{k}={v}" for k, v in params.items()) + "]"
            lines.append(f"  {i+1}. {name}{p_str} ({skill})")
        return "\n".join(lines)

    def _execute_optimized_steps(self, steps, cohesion_checks, milestones, initial_input):
        """执行优化后的步骤链，返回 (step_results, content_text)"""
        step_results = []
        prev_output = initial_input
        lines = []

        for i, step in enumerate(steps):
            step_name = step.get("name", step.get("skill", f"步骤{i+1}"))
            skill_name = step.get("skill", step.get("name", ""))

            # 黏连点检查
            for check in cohesion_checks:
                if check.get("to") == step_name and not check.get("compatible", True):
                    transform = check.get("transform", "")
                    if transform:
                        conversion = self._llm_transform(prev_output, transform)
                        prev_output = conversion
                        lines.append(f"  🔧 黏连转换: {check.get('from','')} → {step_name}")

            # 执行
            sr = self._execute_chain_step(step, prev_output, i)
            step_results.append(sr)

            if sr.get("success"):
                prev_output = sr.get("output", "")
                out = sr.get("output", "")[:200]
                lines.append(f"  ✅ {step_name}")
                if out:
                    lines.append(f"     {out}")
            else:
                lines.append(f"  ❌ {step_name}: {sr.get('error', '失败')}")
                break

            # 里程碑
            for ms in milestones:
                if ms.get("at") == step_name:
                    lines.append(f"  🏁 里程碑: {ms.get('name', '')}")

        return step_results, "\n".join(lines)

    def _recreate_llm(self):
        if self.config:
            self.llm = LLMClient(self.config)


def start_web_ui(agent: "Agent" = None, config: "AgentConfig" = None,
                 host: str = "0.0.0.0", port: int = 8765):
    """启动 Web UI 服务器"""
    OrchestratorHandler.agent = agent
    OrchestratorHandler.config = config
    OrchestratorHandler.llm = LLMClient(config) if config else None

    server = socketserver.TCPServer((host, port), OrchestratorHandler)
    logger.info(f"Orchestrator Web UI 启动: http://{host}:{port}")
    print(f"  Web UI: http://localhost:{port}")
    print(f"  Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止")
        server.shutdown()
