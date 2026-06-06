"""
local-rag-builder Web 可视化设置界面
v0.1.0
内嵌 HTML 面板，可直接修改 Python 核心配置
"""

import os
import sys
import json
import http.server
import socketserver
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, save_config, reset_config, DEFAULT_CONFIG
from prompt_manager import load_template, save_template, reset_template
from embedding_model_manager import list_downloaded_models, RECOMMENDED_MODELS
from knowledge_base_manager import list_knowledge_bases, get_kb_stats
from rag_core import verify_llm_connection

PORT = 8765
HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_settings.html")


def generate_html():
    """生成自包含 HTML 设置界面"""
    cfg = load_config()
    kbs = list_knowledge_bases()
    models = list_downloaded_models()
    template = load_template()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RAG 系统设置面板</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; color: #333; }}
.container {{ max-width: 1000px; margin: 0 auto; }}
.card {{ background: rgba(255,255,255,0.95); border-radius: 16px; padding: 28px; margin-bottom: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.15); backdrop-filter: blur(10px); }}
.card h2 {{ font-size: 18px; margin-bottom: 16px; color: #5a3e8a; border-bottom: 2px solid #e0d4f5; padding-bottom: 8px; }}
.form-group {{ margin-bottom: 14px; }}
.form-group label {{ display: block; font-size: 13px; font-weight: 600; color: #555; margin-bottom: 4px; }}
.form-group input, .form-group select, .form-group textarea {{ width: 100%; padding: 10px 12px; border: 1.5px solid #ddd; border-radius: 8px; font-size: 14px; transition: border 0.2s; }}
.form-group input:focus, .form-group select:focus, .form-group textarea:focus {{ border-color: #667eea; outline: none; box-shadow: 0 0 0 3px rgba(102,126,234,0.15); }}
.form-group textarea {{ min-height: 80px; font-family: 'Courier New', monospace; font-size: 13px; }}
.form-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
.btn {{ padding: 10px 24px; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
.btn-primary {{ background: #667eea; color: white; }}
.btn-primary:hover {{ background: #5a6fd6; transform: translateY(-1px); }}
.btn-secondary {{ background: #e8e8e8; color: #555; }}
.btn-secondary:hover {{ background: #ddd; }}
.btn-danger {{ background: #ff6b6b; color: white; }}
.btn-danger:hover {{ background: #ee5a5a; }}
.btn-success {{ background: #51cf66; color: white; }}
.btn-success:hover {{ background: #40c057; }}
.status {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
.status-ok {{ background: #d3f9d8; color: #2b8a3e; }}
.status-warn {{ background: #fff3bf; color: #e67700; }}
.status-err {{ background: #ffe3e3; color: #c92a2a; }}
.grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
.stat-card {{ background: #f8f9fa; border-radius: 12px; padding: 16px; text-align: center; }}
.stat-card .num {{ font-size: 28px; font-weight: 700; color: #5a3e8a; }}
.stat-card .label {{ font-size: 12px; color: #888; margin-top: 4px; }}
.toast {{ position: fixed; bottom: 24px; right: 24px; padding: 14px 24px; border-radius: 10px; color: white; font-weight: 600; z-index: 999; animation: slideIn 0.3s ease; }}
@keyframes slideIn {{ from {{ transform: translateY(20px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
.strategy-tag {{ display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 11px; background: #e0d4f5; color: #5a3e8a; margin: 2px; }}
</style>
</head>
<body>
<div class="container">
  <h1 style="color:white;margin-bottom:20px;font-weight:300;font-size:28px;">🛠️ RAG 系统设置面板</h1>

  <!-- 状态卡片 -->
  <div class="card">
    <div class="grid-3">
      <div class="stat-card">
        <div class="num">{len(models)}</div>
        <div class="label">嵌入模型</div>
      </div>
      <div class="stat-card">
        <div class="num">{len(kbs)}</div>
        <div class="label">知识库</div>
      </div>
      <div class="stat-card">
        <div class="num">{sum(k.get('doc_count',0) for k in kbs.values())}</div>
        <div class="label">文档块</div>
      </div>
    </div>
  </div>

  <!-- 嵌入模型设置 -->
  <div class="card">
    <h2>📦 嵌入模型</h2>
    <div class="form-group">
      <label>当前模型</label>
      <select id="model-select" onchange="updateConfig('embedding','model_path',this.value)">
        <option value="">-- 选择模型 --</option>
        {''.join(f'<option value="{m["path"]}" {"selected" if m["path"]==cfg.get("embedding",{}).get("model_path","") else ""}>{m.get("model_id",m["path"].split(os.sep)[-1])}</option>' for m in models)}
      </select>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>设备</label>
        <select id="device-select" onchange="updateConfig('embedding','device',this.value)">
          <option value="auto" {"selected" if cfg.get("embedding",{}).get("device","auto")=="auto" else ""}>自动检测</option>
          <option value="cuda" {"selected" if cfg.get("embedding",{}).get("device")=="cuda" else ""}>GPU (CUDA)</option>
          <option value="cpu" {"selected" if cfg.get("embedding",{}).get("device")=="cpu" else ""}>CPU</option>
        </select>
      </div>
      <div class="form-group">
        <label>推荐模型</label>
        <select onchange="if(this.value)window.open('https://huggingface.co/'+this.value)">
          <option value="">查看推荐模型</option>
          {''.join(f'<option value="{m["id"]}">{m["id"]} ({m["desc"]})</option>' for m in RECOMMENDED_MODELS)}
        </select>
      </div>
    </div>
  </div>

  <!-- 切分设置 -->
  <div class="card">
    <h2>✂️ 文本切分</h2>
    <div class="form-row">
      <div class="form-group">
        <label>主策略</label>
        <select id="strategy-select" onchange="updateConfig('splitting','strategy',this.value)">
          <option value="recursive" {"selected" if cfg.get("splitting",{}).get("strategy","recursive")=="recursive" else ""}>递归切分（推荐）</option>
          <option value="fixed" {"selected" if cfg.get("splitting",{}).get("strategy")=="fixed" else ""}>固定窗口</option>
          <option value="headers" {"selected" if cfg.get("splitting",{}).get("strategy")=="headers" else ""}>层级/标题切分</option>
          <option value="sentence" {"selected" if cfg.get("splitting",{}).get("strategy")=="sentence" else ""}>按句切分</option>
          <option value="semantic" {"selected" if cfg.get("splitting",{}).get("strategy")=="semantic" else ""}>语义切分</option>
          <option value="mermaid" {"selected" if cfg.get("splitting",{}).get("strategy")=="mermaid" else ""}>代码块保护切分</option>
        </select>
      </div>
      <div class="form-group">
        <label>二次策略</label>
        <select onchange="updateConfig('splitting','secondary_strategy',this.value||null)">
          <option value="">无</option>
          <option value="recursive" {"selected" if cfg.get("splitting",{}).get("secondary_strategy")=="recursive" else ""}>递归</option>
          <option value="fixed" {"selected" if cfg.get("splitting",{}).get("secondary_strategy")=="fixed" else ""}>固定窗口</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>块大小 (chunk_size)</label>
        <input type="number" id="chunk-size" value="{cfg.get('splitting',{}).get('chunk_size',500)}" min="100" max="2000" onchange="updateConfig('splitting','chunk_size',parseInt(this.value))">
      </div>
      <div class="form-group">
        <label>重叠 (chunk_overlap)</label>
        <input type="number" id="chunk-overlap" value="{cfg.get('splitting',{}).get('chunk_overlap',50)}" min="0" max="500" onchange="updateConfig('splitting','chunk_overlap',parseInt(this.value))">
      </div>
    </div>
  </div>

  <!-- 检索设置 -->
  <div class="card">
    <h2>🔍 检索参数</h2>
    <div class="form-row">
      <div class="form-group">
        <label>检索文档数 (K)</label>
        <input type="number" id="k-value" value="{cfg.get('retrieval',{}).get('k',3)}" min="1" max="20" onchange="updateConfig('retrieval','k',parseInt(this.value))">
      </div>
      <div class="form-group">
        <label>相似度阈值</label>
        <input type="number" id="threshold-value" value="{cfg.get('retrieval',{}).get('score_threshold') or ''}" min="0" max="1" step="0.05" placeholder="不启用" onchange="updateConfig('retrieval','score_threshold',this.value?parseFloat(this.value):null)">
      </div>
    </div>
  </div>

  <!-- LLM 设置 -->
  <div class="card">
    <h2>🤖 LLM 设置</h2>
    <div class="form-group">
      <label>API 地址</label>
      <input type="text" id="llm-url" value="{cfg.get('llm',{}).get('base_url','http://localhost:1234/v1')}" onchange="updateConfig('llm','base_url',this.value)">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Temperature</label>
        <input type="number" id="llm-temp" value="{cfg.get('llm',{}).get('temperature',0.1)}" min="0" max="2" step="0.05" onchange="updateConfig('llm','temperature',parseFloat(this.value))">
      </div>
      <div class="form-group">
        <label>Max Tokens</label>
        <input type="number" id="llm-tokens" value="{cfg.get('llm',{}).get('max_tokens',512)}" min="64" max="4096" step="64" onchange="updateConfig('llm','max_tokens',parseInt(this.value))">
      </div>
    </div>
    <button class="btn btn-secondary" onclick="verifyLLM()" style="margin-top:8px;">🔗 验证连接</button>
    <span id="llm-status"></span>
  </div>

  <!-- Prompt 模板 -->
  <div class="card">
    <h2>📝 Prompt 模板</h2>
    <div class="form-group">
      <textarea id="prompt-template" rows="8" onchange="savePrompt(this.value)">{template}</textarea>
    </div>
    <button class="btn btn-secondary" onclick="resetPrompt()">↺ 重置为默认</button>
    <span id="prompt-status" style="margin-left:12px;font-size:13px;color:#888;"></span>
  </div>

  <!-- 知识库管理 -->
  <div class="card">
    <h2>📚 知识库</h2>
    <div id="kb-list">
      {''.join(f'<div style="display:flex;justify-content:space-between;padding:8px;border-bottom:1px solid #eee;"><span><strong>{name}</strong> - {info.get("description","")} [{info.get("doc_count",0)} 文档]</span></div>' for name, info in kbs.items())}
    </div>
  </div>

  <!-- 操作 -->
  <div class="card" style="display:flex;gap:12px;flex-wrap:wrap;">
    <button class="btn btn-danger" onclick="if(confirm('确定重置所有配置？'))resetAll()">🗑️ 重置配置</button>
    <button class="btn btn-success" onclick="window.location.reload()">🔄 刷新</button>
  </div>
</div>

<script>
function toast(msg, type='success') {{
  const t = document.createElement('div');
  t.className = 'toast';
  t.style.background = type==='success' ? '#51cf66' : type==='error' ? '#ff6b6b' : '#fcc419';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2500);
}}

function updateConfig(section, key, value) {{
  fetch('/api/config', {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{section, key, value}})
  }}).then(r=>r.json()).then(d=>{{
    if(d.success) toast('已更新: '+section+'.'+key+' = '+JSON.stringify(value));
    else toast('失败: '+d.error, 'error');
  }}).catch(e=>toast('请求失败: '+e.message, 'error'));
}}

function savePrompt(content) {{
  fetch('/api/prompt', {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{content}})
  }}).then(r=>r.json()).then(d=>{{
    if(d.success) {{ document.getElementById('prompt-status').textContent = '✓ 已保存'; toast('模板已保存'); }}
    else toast('保存失败', 'error');
  }}).catch(e=>toast('请求失败', 'error'));
}}

function resetPrompt() {{
  fetch('/api/prompt/reset', {{method:'POST'}})
  .then(r=>r.json()).then(d=>{{
    if(d.success) {{ document.getElementById('prompt-template').value = d.template; toast('已重置'); }}
  }});
}}

function verifyLLM() {{
  fetch('/api/verify-llm').then(r=>r.json()).then(d=>{{
    const el = document.getElementById('llm-status');
    el.innerHTML = d.success ? '<span class="status status-ok">✓ 连接正常</span>' : '<span class="status status-err">✗ '+d.message+'</span>';
  }});
}}

function resetAll() {{
  fetch('/api/reset', {{method:'POST'}})
  .then(r=>r.json()).then(d=>{{
    if(d.success) {{ toast('已重置，正在刷新...'); setTimeout(()=>location.reload(), 500); }}
  }});
}}
</script>
</body>
</html>"""


class RAGHandler(http.server.BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(generate_html().encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/config":
                data = self._read_body()
                section = data.get("section")
                key = data.get("key")
                value = data.get("value")
                cfg = load_config()
                if section not in cfg:
                    cfg[section] = {}
                cfg[section][key] = value
                save_config(cfg)
                self._send_json({"success": True})

            elif path == "/api/prompt":
                data = self._read_body()
                content = data.get("content", "")
                save_template(content)
                self._send_json({"success": True})

            elif path == "/api/prompt/reset":
                tpl = reset_template()
                self._send_json({"success": True, "template": tpl})

            elif path == "/api/verify-llm":
                ok, msg = verify_llm_connection()
                self._send_json({"success": ok, "message": msg})

            elif path == "/api/reset":
                reset_config()
                reset_template()
                self._send_json({"success": True})

            else:
                self._send_json({"error": "unknown endpoint"}, 404)

        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def log_message(self, format, *args):
        pass


def start_server(port=PORT):
    """启动 HTTP 服务器"""
    handler = RAGHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"[OK] RAG 设置面板: http://localhost:{port}")
        print(f"  在浏览器中打开即可可视化配置")
        print(f"  按 Ctrl+C 停止服务器")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG Web 设置界面")
    parser.add_argument("--port", type=int, default=PORT, help="端口号")
    parser.add_argument("--gen-html", action="store_true", help="仅生成 HTML 文件，不启动服务器")
    parser.add_argument("--output", type=str, help="HTML 输出路径")

    args = parser.parse_args()

    if args.gen_html:
        html = generate_html()
        output = args.output or HTML_FILE
        with open(output, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[OK] HTML 文件已生成: {output}")
    else:
        start_server(args.port)
