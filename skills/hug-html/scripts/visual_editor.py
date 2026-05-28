#!/usr/bin/env python3
# visual_editor.py - Generate standalone visual editor HTML
# Usage: python visual_editor.py --template <template.html> --output <editor.html>

import argparse
import sys
from pathlib import Path
from html.parser import HTMLParser

EDITOR_JS = r"""
// === Visual Editor Core ===
let editorOpen = false;
let currentEditable = null;

function initEditor() {
  // Make all [data-field] elements editable
  document.querySelectorAll('[data-field]').forEach(el => {
    el.classList.add('ve-editable');
    el.addEventListener('click', () => openFieldEditor(el));
    el.style.outline = '2px dashed #6C63FF';
    el.style.cursor = 'pointer';
    el.style.padding = '4px 6px';
    el.style.borderRadius = '4px';
    el.style.minHeight = '1.2em';
  });

  // Make all .editable-img clickable
  document.querySelectorAll('.editable-img, [data-field="image"]').forEach(img => {
    img.style.cursor = 'pointer';
    img.addEventListener('click', (e) => { e.stopPropagation(); openImagePicker(img); });
    img.style.outline = '2px dashed #FF6584';
    img.style.outlineOffset = '2px';
  });

  // Make all [data-module] elements highlightable
  document.querySelectorAll('[data-module]').forEach(el => {
    el.style.outline = '1px dashed #00B894';
    el.style.outlineOffset = '2px';
    el.style.cursor = 'grab';
  });

  showToolbar();
  editorOpen = true;
  console.log('[Editor] ✅ 编辑模式已启动 — 点击可编辑区域开始修改');
}

function openFieldEditor(el) {
  currentEditable = el;
  const val = el.innerText || el.textContent || '';
  const bar = document.getElementById('ve-toolbar');
  bar.style.display = 'flex';
  document.getElementById('ve-field-name').textContent = el.getAttribute('data-field') || '(选中元素)';
  el.focus();
}

function openImagePicker(imgEl) {
  const url = prompt('输入图片 URL（留空使用占位图）：', imgEl.src || '');
  if (url === null) return;
  if (url.trim() === '') {
    imgEl.src = 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27600%27 height=%27200%27%3E%3Crect fill=%27%23ddd%27 width=%27600%27 height=%27200%27/%3E%3Ctext x=%2750%25%27 y=%2750%25%27 dominant-baseline=%27middle%27 text-anchor=%27middle%27 fill=%27%23999%27%3E点击上传图片%3C/text%3E%3C/svg%3E';
  } else {
    imgEl.src = url;
  }
  // Apply image style from select
  const style = document.getElementById('ve-img-style').value;
  applyImageStyle(imgEl, style);
}

function applyImageStyle(img, style) {
  img.className = img.className.replace(/img-\\w+/g, '').trim();
  if (style === 'circle') img.classList.add('img-circle');
  else if (style === 'cover') img.classList.add('img-cover');
  else if (style === 'logo') img.classList.add('img-logo');
  else if (style === 'contain') img.classList.add('img-contain');
  // Size
  const w = document.getElementById('ve-img-w').value;
  const h = document.getElementById('ve-img-h').value;
  if (w) img.style.width = w;
  if (h && h !== 'auto') img.style.height = h;
}

function applyColor() {
  const f = document.getElementById('ve-field-name').textContent;
  const c = document.getElementById('ve-color-picker').value;
  if (f && f !== '(选中元素)') {
    const el = document.querySelector('[data-field="' + f + '"]');
    if (el) el.style.color = c;
  } else if (currentEditable) {
    currentEditable.style.color = c;
  }
}

function applyBgColor() {
  const f = document.getElementById('ve-field-name').textContent;
  const c = document.getElementById('ve-bg-picker').value;
  if (f && f !== '(选中元素)') {
    const el = document.querySelector('[data-field="' + f + '"]');
    if (el) el.style.backgroundColor = c;
  } else if (currentEditable) {
    currentEditable.style.backgroundColor = c;
  }
}

function applyFontSize() {
  const s = document.getElementById('ve-font-size').value;
  if (currentEditable && s) currentEditable.style.fontSize = s + 'px';
}

function applyOpacity() {
  const v = document.getElementById('ve-opacity').value;
  if (currentEditable) currentEditable.style.opacity = v;
}

function toggleBold()  { document.execCommand('bold'); }
function toggleItalic()  { document.execCommand('italic'); }
function toggleUnderline() { document.execCommand('underline'); }

function exportFinalHTML() {
  // Clone and clean
  const container = document.querySelector('.template-container') || document.body;
  const clone = container.cloneNode(true);

  // Remove editor UI
  clone.querySelectorAll('.ve-editable,.ve-toolbar,.ve-overlay').forEach(el => el.remove());
  clone.querySelectorAll('[contenteditable]').forEach(el => el.removeAttribute('contenteditable'));
  clone.querySelectorAll('style').forEach(s => {
    s.textContent = s.textContent.replace(/\.ve-[\s\S]*?}/g, ''); // strip editor styles
  });

  const finalHTML = '<!DOCTYPE html>\n' + clone.outerHTML;
  const blob = new Blob([finalHTML], {type: 'text/html;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'final-' + Date.now() + '.html';
  a.click();
  URL.revokeObjectURL(a.href);
  alert('✅ 最终 HTML 已下载！');
}

function previewHTML() {
  const container = document.querySelector('.template-container') || document.body;
  const clone = container.cloneNode(true);
  clone.querySelectorAll('.ve-editable,.ve-toolbar,.ve-overlay').forEach(el => el.remove());
  const w = window.open('', '_blank');
  w.document.write('<!DOCTYPE html>\n' + clone.outerHTML);
  w.document.close();
}

function closeEditor() {
  document.querySelectorAll('.ve-editable').forEach(el => {
    el.style.outline = '';
    el.style.cursor = '';
  });
  document.getElementById('ve-toolbar').style.display = 'none';
  editorOpen = false;
}

// Keyboard shortcut
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.key === 'e') { e.preventDefault(); editorOpen ? closeEditor() : initEditor(); }
  if (e.ctrlKey && e.key === 's') { e.preventDefault(); exportFinalHTML(); }
});
"""

TOOLBAR_HTML = """\
<div id="ve-toolbar" style="display:none;position:fixed;top:0;left:0;right:0;z-index:99999;background:#1e1e2e;color:#fff;padding:8px 16px;display:flex;align-items:center;gap:10px;font-size:13px;box-shadow:0 2px 12px rgba(0,0,0,0.3);">
  <span id="ve-field-name" style="color:#6C63FF;font-weight:bold;min-width:80px;">(选中元素)</span>
  <div style="width:1px;height:20px;background:#555;"></div>
  <button onclick="toggleBold()" title="加粗" style="background:#333;color:#fff;border:1px solid #666;padding:4px 8px;border-radius:4px;cursor:pointer;font-weight:bold;">B</button>
  <button onclick="toggleItalic()" title="斜体" style="background:#333;color:#fff;border:1px solid #666;padding:4px 8px;border-radius:4px;cursor:pointer;font-style:italic;">I</button>
  <button onclick="toggleUnderline()" title="下划线" style="background:#333;color:#fff;border:1px solid #666;padding:4px 8px;border-radius:4px;cursor:pointer;text-decoration:underline;">U</button>
  <div style="width:1px;height:20px;background:#555;"></div>
  <label style="color:#ccc;font-size:12px;">🎨字色</label>
  <input type="color" id="ve-color-picker" value="#6C63FF" onchange="applyColor()" style="width:28px;height:28px;border:none;cursor:pointer;">
  <label style="color:#ccc;font-size:12px;">🖌️背景</label>
  <input type="color" id="ve-bg-picker" value="#ffffff" onchange="applyBgColor()" style="width:28px;height:28px;border:none;cursor:pointer;">
  <label style="color:#ccc;font-size:12px;">🔤字号</label>
  <select id="ve-font-size" onchange="applyFontSize()" style="background:#333;color:#fff;border:1px solid #666;padding:2px 4px;border-radius:4px;">
    <option value="">--</option>
    <option value="12">12px</option>
    <option value="14">14px</option>
    <option value="16">16px</option>
    <option value="18">18px</option>
    <option value="24">24px</option>
    <option value="32">32px</option>
  </select>
  <label style="color:#ccc;font-size:12px;">👁️透明</label>
  <select id="ve-opacity" onchange="applyOpacity()" style="background:#333;color:#fff;border:1px solid #666;padding:2px 4px;border-radius:4px;">
    <option value="1">100%</option>
    <option value="0.9">90%</option>
    <option value="0.7">70%</option>
    <option value="0.5">50%</option>
    <option value="0.3">30%</option>
  </select>
  <div style="width:1px;height:20px;background:#555;"></div>
  <label style="color:#ccc;font-size:12px;">🖼️图样</label>
  <select id="ve-img-style" style="background:#333;color:#fff;border:1px solid #666;padding:2px 4px;border-radius:4px;">
    <option value="">默认</option>
    <option value="circle">圆形裁剪</option>
    <option value="cover">覆盖填充</option>
    <option value="logo">Logo（左上）</option>
    <option value="contain">完整显示</option>
  </select>
  <input type="text" id="ve-img-w" placeholder="宽" value="" style="width:48px;background:#333;color:#fff;border:1px solid #666;padding:2px 4px;border-radius:4px;font-size:12px;">
  <input type="text" id="ve-img-h" placeholder="高" value="" style="width:48px;background:#333;color:#fff;border:1px solid #666;padding:2px 4px;border-radius:4px;font-size:12px;">
  <div style="flex:1;"></div>
  <button onclick="previewHTML()" title="预览" style="background:#3F51B5;color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;">👁️ 预览</button>
  <button onclick="exportFinalHTML()" title="生成最终HTML" style="background:#00B894;color:#fff;border:none;padding:8px 18px;border-radius:6px;cursor:pointer;font-weight:bold;">✅ 生成最终HTML</button>
  <button onclick="closeEditor()" title="退出编辑" style="background:#E17055;color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;">❌ 退出</button>
</div>
"""

OVERLAY_HTML = """\
<div id="ve-overlay" style="display:none;position:fixed;inset:0;z-index:99998;background:rgba(0,0,0,0.3);" onclick="closeEditor()"></div>
<div id="ve-init-hint" style="position:fixed;bottom:20px;right:20px;z-index:99999;background:#6C63FF;color:white;padding:12px 20px;border-radius:8px;cursor:pointer;font-size:14px;box-shadow:0 4px 12px rgba(108,99,255,0.4);" onclick="initEditor();this.style.display='none';">
  🛠️ 点击启动可视化编辑
</div>
"""


def inject_editor(html_str):
    """Inject editor toolbar + JS into HTML string"""
    # Append before </body>
    editor_block = TOOLBAR_HTML + OVERLAY_HTML + '<script>' + EDITOR_JS + '</script>'
    if '</body>' in html_str:
        html_str = html_str.replace('</body>', editor_block + '\n</body>', 1)
    else:
        html_str = html_str + editor_block
    return html_str


def generate_standalone_editor(template_path, output_path):
    """Generate a standalone editor HTML wrapping the template"""
    tpl = Path(template_path)
    if not tpl.exists():
        print('[X] Template not found: ' + str(tpl))
        sys.exit(1)

    html = tpl.read_text(encoding='utf-8')
    html = inject_editor(html)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    print('[OK] Visual editor generated: ' + str(out))
    print('     Open in browser and press Ctrl+E to toggle editor')
    return str(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', required=True, help='Input template HTML path')
    ap.add_argument('--output', required=True, help='Output editor HTML path')
    args = ap.parse_args()
    generate_standalone_editor(args.template, args.output)
