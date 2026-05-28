#!/usr/bin/env python3
# template_generator.py - Generate standard HTML templates
# Usage: python template_generator.py --output <path> --type <promo|product|tech|flow>

import argparse
import json
import sys
from pathlib import Path

TEMPLATE_TYPES = {
    "promo": {
        "title": "活动宣传",
        "primary": "#6C63FF",
        "secondary": "#FF6584",
        "bg": "#f5f7fa",
        "gradient": "linear-gradient(135deg, #6C63FF 0%, #3F51B5 100%)",
        "grid": "repeat(auto-fit, minmax(280px, 1fr))",
    },
    "product": {
        "title": "产品介绍",
        "primary": "#00B894",
        "secondary": "#FDCB6E",
        "bg": "#ffffff",
        "gradient": "linear-gradient(135deg, #00B894 0%, #00CEC9 100%)",
        "grid": "1fr 1fr",
    },
    "tech": {
        "title": "技术说明",
        "primary": "#2D3436",
        "secondary": "#636E72",
        "bg": "#f8f9fa",
        "gradient": "linear-gradient(135deg, #2D3436 0%, #636E72 100%)",
        "grid": "1fr",
    },
    "flow": {
        "title": "流程明白纸",
        "primary": "#E17055",
        "secondary": "#FDCB6E",
        "bg": "#fffde7",
        "gradient": "linear-gradient(135deg, #E17055 0%, #FDCB6E 100%)",
        "grid": "repeat(auto-fit, minmax(200px, 1fr))",
    },
}


def gen_css(config):
    """Generate CSS block with .format() to avoid f-string brace issues"""
    css = """\
:root {{
  --pc: {primary};
  --sc: {secondary};
  --bg: {bg};
  --gradient: {gradient};
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; background: {bg}; color: #333; }}
.template-container {{
  max-width: 1200px; margin: 0 auto; padding: 20px;
  background: white; border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}}
.template-header {{
  text-align: center; padding: 40px 20px;
  background: {gradient}; border-radius: 12px 12px 0 0;
  color: white; margin: -20px -20px 30px -20px;
}}
.template-header h1 {{ font-size: 2.2em; margin: 0; }}
.template-header p  {{ opacity: 0.9; margin-top: 10px; font-size: 1.1em; }}
.template-body {{ display: grid; grid-template-columns: {grid}; gap: 20px; padding: 0 10px; }}
.card {{ background: #f8f9fa; padding: 24px; border-radius: 10px; border-top: 3px solid var(--pc); }}
.card h2, .card h3 {{ color: var(--pc); margin-bottom: 12px; }}
.card img {{ width: 100%; border-radius: 8px; margin-top: 12px; }}
.template-footer {{ text-align: center; padding: 20px; margin-top: 30px; border-top: 1px solid #eee; color: #999; font-size: 0.9em; }}

/* Editable regions - highlighted on hover */
.edit-text  {{ border: 1px dashed transparent; padding: 2px 4px; min-height: 1em; outline: none; }}
.edit-text:hover  {{ border-color: #aaa; background: rgba(108,99,255,0.05); }}
.edit-text:focus {{ border-color: var(--pc); background: white; }}

/* Image styles */
.img-circle  {{ border-radius: 50%; object-fit: cover; }}
.img-logo   {{ position: absolute; top: 12px; left: 12px; width: 80px; }}
.img-cover  {{ width: 100%; height: 200px; object-fit: cover; border-radius: 8px; }}
.img-contain {{ width: 100%; height: auto; border-radius: 8px; }}

/* Animation classes */
.anim-fade  {{ animation: fadeIn 0.6s ease-out; }}
.anim-slide {{ animation: slideIn 0.5s ease-out; }}
.hover-scale:hover {{ transform: scale(1.03); transition: transform 0.3s; }}

@keyframes fadeIn {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
@keyframes slideIn {{ from {{ opacity:0; transform:translateX(-30px); }} to {{ opacity:1; transform:translateX(0); }} }}

/* Opacity utilities */
.op-90 {{ opacity: 0.9; }}  .op-70 {{ opacity: 0.7; }}
.op-50 {{ opacity: 0.5; }}  .op-30 {{ opacity: 0.3; }}

/* Module placeholders */
.mod-color   {{ width: 40px; height: 24px; display: inline-block; border-radius: 4px; vertical-align: middle; }}
.mod-spacer  {{ height: 20px; }}
.mod-divider {{ border-top: 1px solid #eee; margin: 16px 0; }}

@media (max-width: 768px) {{
  .template-body {{ grid-template-columns: 1fr; }}
  .template-header h1 {{ font-size: 1.6em; }}
}}
""".format(
        primary=config["primary"],
        secondary=config["secondary"],
        bg=config["bg"],
        gradient=config["gradient"],
        grid=config["grid"],
    )
    return css


def gen_body_promo(config):
    return """\
  <div class="template-header anim-fade">
    <h1 class="edit-text" data-field="title">🎉 活动宣传标题</h1>
    <p class="edit-text" data-field="subtitle">在这里填写活动的副标题或简短描述</p>
  </div>
  <div class="template-body">
    <div class="card">
      <h2>活动亮点</h2>
      <p class="edit-text" data-field="highlight">请填写活动的主要亮点...</p>
      <img class="img-cover hover-scale" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='600' height='200'%3E%3Crect fill='%23e0e0e0' width='600' height='200'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999' font-size='16'%3E点击替换图片%3C/text%3E%3C/svg%3E" alt="cover">
    </div>
    <div class="card">
      <h3>活动时间</h3>
      <p class="edit-text" data-field="time">请填写活动时间...</p>
      <h3 style="margin-top:16px;">活动地点</h3>
      <p class="edit-text" data-field="location">请填写活动地点...</p>
    </div>
    <div class="card" style="grid-column: 1 / -1;">
      <h2>详细介绍</h2>
      <p class="edit-text" data-field="detail">在这里填写活动的详细介绍...</p>
    </div>
  </div>
  <div class="template-footer">
    <span class="edit-text" data-field="footer">© 2026 活动主办方 | 联系我们</span>
  </div>"""


def gen_body_product(config):
    return """\
  <div class="template-header anim-fade">
    <h1 class="edit-text" data-field="name">📦 产品名称</h1>
  </div>
  <div class="template-body">
    <div class="card" style="border-top-color: var(--sc);">
      <h2>产品图片</h2>
      <img class="img-contain hover-scale" style="max-height:350px;" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='500' height='350'%3E%3Crect fill='%23e0e0e0' width='500' height='350'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999'%3E产品图片%3C/text%3E%3C/svg%3E" alt="product">
    </div>
    <div class="card">
      <h2>产品介绍</h2>
      <p class="edit-text" data-field="desc">请填写产品核心卖点...</p>
      <h3 style="margin-top:16px;">技术参数</h3>
      <ul class="edit-text" data-field="specs" style="padding-left:20px;"><li>参数一：值</li><li>参数二：值</li></ul>
    </div>
    <div class="card" style="grid-column: 1 / -1; text-align:center;">
      <button style="background:var(--pc);color:white;border:none;padding:14px 48px;border-radius:8px;font-size:1.1em;cursor:pointer;">立即咨询</button>
    </div>
  </div>
  <div class="template-footer">
    <span class="edit-text" data-field="footer">© 2026 产品介绍 | 详情咨询</span>
  </div>"""


def gen_body_tech(config):
    return """\
  <div class="template-container" style="max-width:960px;">
  <div class="template-header anim-fade" style="background: """ + config["gradient"] + """;">
    <h1 class="edit-text" data-field="title" style="font-family:Consolas,'Courier New',monospace;">⚙️ 技术说明文档</h1>
  </div>
  <div class="template-body">
    <div class="card" style="font-family:Consolas,'Courier New',monospace; background:#f0f0f0;">
      <h2 style="font-family:'Microsoft YaHei';">核心原理</h2>
      <p class="edit-text" data-field="principle">请填写技术核心原理...</p>
      <pre style="background:#2d3436;color:#dfe6e9;padding:16px;border-radius:6px;overflow-x:auto;margin-top:12px;"><code class="edit-text" data-field="code"># 代码示例
def solve():
    return "solution"</code></pre>
    </div>
    <div class="card">
      <h2>性能参数</h2>
      <table style="width:100%;border-collapse:collapse;margin-top:8px;">
        <tr style="background:var(--pc);color:white;"><th style="padding:8px;">指标</th><th style="padding:8px;">数值</th></tr>
        <tr style="border-bottom:1px solid #eee;"><td style="padding:8px;" class="edit-text" data-field="m1">指标1</td><td style="padding:8px;" class="edit-text" data-field="v1">值1</td></tr>
        <tr style="border-bottom:1px solid #eee;"><td style="padding:8px;" class="edit-text" data-field="m2">指标2</td><td style="padding:8px;" class="edit-text" data-field="v2">值2</td></tr>
      </table>
    </div>
  </div>
  <div class="template-footer">
    <span class="edit-text" data-field="footer">技术文档 © 2026</span>
  </div>
  </div>"""


def gen_body_flow(config):
    return """\
  <div class="template-header anim-fade">
    <h1 class="edit-text" data-field="title">📋 流程说明</h1>
  </div>
  <div class="template-body">
    <div class="card anim-slide" style="border-top-color:var(--pc);text-align:center;">
      <div style="background:var(--pc);color:white;width:36px;height:36px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-weight:bold;margin-bottom:12px;">1</div>
      <h3 class="edit-text" data-field="s1_title">第一步：准备</h3>
      <p class="edit-text" data-field="s1_desc">描述第一步内容...</p>
    </div>
    <div class="card anim-slide" style="border-top-color:var(--sc);text-align:center;">
      <div style="background:var(--sc);color:white;width:36px;height:36px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-weight:bold;margin-bottom:12px;">2</div>
      <h3 class="edit-text" data-field="s2_title">第二步：执行</h3>
      <p class="edit-text" data-field="s2_desc">描述第二步内容...</p>
    </div>
    <div class="card anim-slide" style="border-top-color:var(--pc);text-align:center;">
      <div style="background:var(--pc);color:white;width:36px;height:36px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-weight:bold;margin-bottom:12px;">3</div>
      <h3 class="edit-text" data-field="s3_title">第三步：验收</h3>
      <p class="edit-text" data-field="s3_desc">描述第三步内容...</p>
    </div>
    <div class="card" style="grid-column:1/-1;text-align:center;">
      <h2>注意事项</h2>
      <p class="edit-text" data-field="notes">填写注意事项...</p>
    </div>
  </div>
  <div class="template-footer">
    <span class="edit-text" data-field="footer">流程明白纸 © 2026</span>
  </div>"""


def generate(template_type, output_path, content=None):
    config = TEMPLATE_TYPES.get(template_type, TEMPLATE_TYPES["promo"])
    css = gen_css(config)

    body_map = {
        "promo": gen_body_promo,
        "product": gen_body_product,
        "tech": gen_body_tech,
        "flow": gen_body_flow,
    }
    body = body_map.get(template_type, gen_body_promo)(config)

    # Fill content if provided
    if content:
        for field, value in content.items():
            body = body.replace(
                'class="edit-text" data-field="' + field + '"',
                'class="edit-text" data-field="' + field + '">' + value,
                1
            )

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="template-container">
{body}
</div>

<!-- Editor toolbar (shown when opened via openEditor()) -->
<div id="editor-bar" style="display:none;position:fixed;top:0;left:0;right:0;background:#333;color:white;padding:10px 20px;z-index:9999;display:flex;gap:12px;align-items:center;font-size:14px;">
  <span>🛠️ 编辑模式</span>
  <button onclick="toggleBold()" style="background:#555;color:white;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;">B</button>
  <button onclick="toggleColor()" style="background:#555;color:white;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;">🎨颜色</button>
  <button onclick="toggleFontSize()" style="background:#555;color:white;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;">🔤字号</button>
  <button onclick="replaceImage(this)" style="background:#555;color:white;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;">🖼️换图</button>
  <button onclick="exportHTML()" style="background:#00B894;color:white;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;margin-left:auto;">✅ 生成最终HTML</button>
  <button onclick="closeEditor()" style="background:#E17055;color:white;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;">❌ 退出</button>
</div>

<script>
let editMode = false;
function enableEditor() {{
  editMode = true;
  document.getElementById('editor-bar').style.display = 'flex';
  document.querySelectorAll('.edit-text').forEach(el => {{
    el.setAttribute('contenteditable', 'true');
    el.style.borderColor = '#6C63FF';
    el.style.background = 'rgba(108,99,255,0.05)';
  }});
}}
function closeEditor() {{
  editMode = false;
  document.getElementById('editor-bar').style.display = 'none';
  document.querySelectorAll('.edit-text').forEach(el => {{
    el.removeAttribute('contenteditable');
    el.style.borderColor = 'transparent';
    el.style.background = '';
  }});
}}
function toggleBold() {{
  document.execCommand('bold');
}}
function toggleColor() {{
  const c = prompt('输入颜色（如 #FF6584 或 red）：', '#FF6584');
  if (c) document.execCommand('foreColor', false, c);
}}
function toggleFontSize() {{
  const s = prompt('输入字号（如 18px）：', '18px');
  if (s) document.execCommand('fontSize', false, '7');  // then fix via insertHTML
}}
function replaceImage(btn) {{
  const url = prompt('输入图片URL（或留空使用默认占位图）：', '');
  if (url !== null) {{
    document.querySelectorAll('.card img').forEach(img => {{
      if (url) img.src = url;
      // If user cancels, do nothing
    }});
  }}
}}
function exportHTML() {{
  // Collect all editable field values
  const data = {{}};
  document.querySelectorAll('.edit-text').forEach(el => {{
    const f = el.getAttribute('data-field');
    if (f) data[f] = el.innerHTML;
  }});
  // Generate clean HTML (strip editing UI)
  const clone = document.querySelector('.template-container').cloneNode(true);
  clone.querySelectorAll('.edit-text').forEach(el => {{
    el.removeAttribute('contenteditable');
    el.style.borderColor = '';
    el.style.background = '';
  }});
  const cleanHtml = '<!DOCTYPE html>\\n' + document.documentElement.outerHTML.replace(
    document.querySelector('.template-container').outerHTML, clone.outerHTML
  ).replace(/<script[\\s\\S]*?<\\/script>/g, '');
  // Download
  const blob = new Blob([cleanHtml], {{type:'text/html'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'final.html';
  a.click();
  alert('✅ 最终HTML已生成并下载！');
  closeEditor();
}}
// Keyboard shortcut: Ctrl+E to toggle editor
document.addEventListener('keydown', e => {{
  if (e.ctrlKey && e.key === 'e') {{ e.preventDefault(); editMode ? closeEditor() : enableEditor(); }}
}});
console.log('💡 提示：按 Ctrl+E 进入/退出编辑模式');
</script>
</body>
</html>""".format(title=config["title"], css=css, body=body)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print("[OK] Template generated: " + str(out))
    return str(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--type", required=True, choices=["promo", "product", "tech", "flow"])
    ap.add_argument("--content", help="JSON file to fill content")
    args = ap.parse_args()

    content_data = None
    if args.content:
        with open(args.content, "r", encoding="utf-8") as f:
            content_data = json.load(f)

    generate(args.type, args.output, content_data)
