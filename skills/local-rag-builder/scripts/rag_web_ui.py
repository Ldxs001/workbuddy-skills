"""
local-rag-builder Web 可视化设置界面
v0.2.0
内嵌 HTML 面板，可直接修改 Python 核心配置
支持：输入源配置、GuardStack、文档切片三层流水线、策略级覆盖、AI 推荐
"""

import os
import sys
import json
import http.server
import socketserver
import urllib.parse
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, save_config, reset_config, DEFAULT_CONFIG
from prompt_manager import load_template, save_template, reset_template, get_system_prefix, get_full_prompt, PROMPT_PRESETS
from embedding_model_manager import list_downloaded_models, RECOMMENDED_MODELS, download_model
from knowledge_base_manager import list_knowledge_bases, get_kb_stats, get_kb_model, set_kb_model
from router import list_kb_signatures, rebuild_all_signatures
from rag_standalone import verify_llm_connection
from text_splitter import STRATEGY_REGISTRY, GUARD_REGISTRY, get_all_strategies_info, SECONDARY_STRATEGIES
from utils import cfg_dir, run_command

# 下载状态跟踪 {model_id: {"status":"downloading"|"done"|"failed"|"retrying", "source":"...", "attempt":1, "message":"..."}}
_download_tasks = {}

PORT = 8765
HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_settings.html")
TEMPLATES_DIR = os.path.join(os.path.dirname(cfg_dir), "config_templates")


# ==================== 输入源依赖检测 ====================

_DEP_MODULES = {
    "enable_pdf": ["pypdf", "pdfplumber"],
    "enable_ocr": ["paddleocr", "easyocr"],
    "enable_html2md": ["html2text"],
}

def _check_dep(key):
    """检查输入源依赖是否已安装，返回 'ready' 或 'missing'"""
    modules = _DEP_MODULES.get(key, [])
    for mod in modules:
        try:
            __import__(mod)
            return "ready"
        except ImportError:
            continue
    return "missing"


# ==================== 配置模板管理 ====================

def list_templates():
    """列出所有已保存的配置模板"""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    templates = []
    for fname in sorted(os.listdir(TEMPLATES_DIR)):
        if fname.endswith(".json"):
            path = os.path.join(TEMPLATES_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                templates.append({
                    "name": fname[:-5],
                    "label": data.get("_label", fname[:-5]),
                    "size": os.path.getsize(path),
                    "mtime": os.path.getmtime(path),
                })
            except (json.JSONDecodeError, OSError):
                continue
    return templates


def save_template_config(name, label, config):
    """保存当前配置为模板"""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    data = dict(config)
    data["_label"] = label
    data["_name"] = name
    path = os.path.join(TEMPLATES_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_template_config(name):
    """加载模板配置"""
    path = os.path.join(TEMPLATES_DIR, f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 移除内部元字段
    data.pop("_label", None)
    data.pop("_name", None)
    return data


def delete_template_config(name):
    """删除模板"""
    path = os.path.join(TEMPLATES_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False



_JS_SCRIPTS = """<script>
window.PROMPT_SYSTEM_PREFIX = '基于以下资料回答问题。如果资料中没有相关信息，请说"不知道"。\\n\\n资料：\\n{context}\\n\\n问题：\\n{question}\\n\\n回答：';

function toast(msg, type) { type = type || 'success'; const t = document.createElement('div'); t.className = 'toast'; t.style.background = type==='success' ? '#51cf66' : type==='error' ? '#ff6b6b' : '#fcc419'; t.textContent = msg; document.body.appendChild(t); setTimeout(function(){t.remove()}, 2500); }

function setMode(mode) {
  fetch('/api/mode', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({mode})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) { toast('已切换'); setTimeout(function(){location.reload()}, 300); }
    else { toast(d.error, 'error'); }
  }).catch(function(e){toast('请求失败', 'error')});
}

function updateConfig(section, key, value) {
  fetch('/api/config', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({section: section, key: key, value: value})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) toast('已更新');
    else toast(d.error, 'error');
  }).catch(function(e){toast('请求失败', 'error')});
}

function setKbModel(kbName, modelId) {
  fetch('/api/kb-model', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({kb_name: kbName, model_id: modelId})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) toast('知识库模型已更新: ' + d.message);
    else toast(d.error, 'error');
  }).catch(function(e){toast('请求失败', 'error')});
}

function updateOverride(strategy, key, value) {
  fetch('/api/override', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({strategy: strategy, key: key, value: value})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) toast('已更新');
    else toast(d.error, 'error');
  }).catch(function(e){toast('请求失败', 'error')});
}

function toggleInputSource(key) { onToggleInputSource(key); }

function onStrategyChange(strategy) {
  updateConfig('splitting','strategy',strategy);
  updateAdvView();
}

function togglePreproc(checked) {
  fetch('/api/preprocess/toggle', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({enabled: checked})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) {
      toast(checked ? '已启用预处理' : '已禁用预处理');
    }
  });
  for(var l = 1; l <= 4; l++) {
    var cb = document.getElementById('h' + l + '-enable');
    var sel = document.getElementById('h' + l + '-preset');
    if(cb) {
      cb.disabled = !checked;
      if(!checked) cb.checked = false;
      togglePreprocLevel(l, cb.checked);
    }
    if(sel) { sel.disabled = !checked; }
  }
  if(checked) {
    var sel = document.getElementById('strategy-select');
    if(sel) { sel.value = 'headers'; sel.disabled = true; }
  } else {
    var sel = document.getElementById('strategy-select');
    if(sel) { sel.disabled = false; }
  }
}

function updatePresetList(level) {
  var presetMap = {
    1: ["自定义", "中文章节: 第X章 XXX", "英文章节: Chapter X", "数字标题: 1. XXX", "英文字句标题"],
    2: ["自定义", "中文数字: 一、XXX", "数字编号: 1.1 XXX", "字母编号: A. XXX", "括号编号: (1) XXX"],
    3: ["自定义", "数字编号: 1.1.1 XXX", "短横编号: 1-1 XXX"],
    4: ["自定义", "括号编号: (a) XXX"]
  };
  var sel = document.getElementById('h' + level + '-preset');
  if(!sel) return;
  var current = sel.value;
  sel.innerHTML = '';
  var items = presetMap[level] || [];
  for(var i = 0; i < items.length; i++) {
    var opt = document.createElement('option');
    opt.value = (i === 0) ? '' : items[i];
    opt.textContent = items[i];
    sel.appendChild(opt);
  }
  sel.value = current || '';
}

function applyPreset(level, presetLabel) {
  var presetRegex = {
    "中文章节: 第X章 XXX": "^第[一二三四五六七八九十]+[章节篇]\\\\s+(.*)$",
    "英文章节: Chapter X": "^Chapter\\\\s+\\\\d+\\\\s*[.:]\\\\s*(.*)$",
    "数字标题: 1. XXX": "^\\\\d+\\\\s*[.．、]\\\\s*(.*)$",
    "英文字句标题": "^[A-Z][A-Za-z\\\\s]{10,}$",
    "中文数字: 一、XXX": "^[一二三四五六七八九十]+[、\\\\.]\\\\s*(.*)$",
    "数字编号: 1.1 XXX": "^\\\\d+\\\\.\\\\d+\\\\s+(.*)$",
    "字母编号: A. XXX": "^[A-Z]\\\\.\\\\s*(.*)$",
    "括号编号: (1) XXX": "^(\\\\d+)\\\\s+(.*)$",
    "数字编号: 1.1.1 XXX": "^\\\\d+\\\\.\\\\d+\\\\.\\\\d+\\\\s+(.*)$",
    "短横编号: 1-1 XXX": "^\\\\d+-\\\\d+\\\\s+(.*)$",
    "括号编号: (a) XXX": "^([a-z])\\\\s+(.*)$"
  };
  var ta = document.getElementById('h' + level + '-patterns');
  if(!ta) return;
  if(!presetLabel || presetLabel === '自定义' || presetLabel === '') {
    ta.value = '';
  } else {
    var regex = presetRegex[presetLabel];
    if(regex) { ta.value = regex; }
  }
  var cb = document.getElementById('h' + level + '-enable');
  if(cb && !cb.checked && ta.value) {
    cb.checked = true;
    cb.disabled = false;
    togglePreprocLevel(level, true);
  }
  if(cb && cb.checked && !ta.value) {
    cb.checked = false;
    togglePreprocLevel(level, false);
  }
  savePreprocConfig();
}

function togglePreprocLevel(level, checked) {
  var ta = document.getElementById('h' + level + '-patterns');
  if(checked) {
    if(ta) { ta.disabled = false; ta.style.background = ''; ta.style.color = ''; }
  } else {
    if(ta) { ta.disabled = true; ta.style.background = '#f5f5f5'; ta.style.color = '#bbb'; }
  }
  savePreprocConfig();
}

function togglePreprocLevel(level, checked) {
  var ta = document.getElementById('h' + level + '-patterns');
  if(checked) {
    if(ta) { ta.disabled = false; ta.style.background = ''; ta.style.color = ''; }
  } else {
    if(ta) { ta.disabled = true; ta.style.background = '#f5f5f5'; ta.style.color = '#bbb'; }
  }
  savePreprocConfig();
}

function savePreprocConfig() {
  var enabled = document.getElementById('preproc-enable').checked;
  var config = {enabled: enabled, h1_patterns: [], h2_patterns: [], h3_patterns: [], h4_patterns: []};
  for(var level = 1; level <= 4; level++) {
    var cb = document.getElementById('h' + level + '-enable');
    var ta = document.getElementById('h' + level + '-patterns');
    if(cb && cb.checked && ta) {
      config['h' + level + '_patterns'] = ta.value.split('\\n').filter(function(l){return l.trim() !== '';});
    }
  }
  fetch('/api/preprocess/save', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify(config)
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) toast('已保存');
  });
}

function onSecondaryChange(val) {
  fetch('/api/config', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({section: 'splitting', key: 'secondary_strategy', value: val || null})
  });
  updateAdvView();
}

function toggleAdvanced() {
  var content = document.getElementById('adv-content');
  var arrow = document.getElementById('adv-arrow');
  var on = content.style.display === 'block';
  content.style.display = on ? 'none' : 'block';
  arrow.textContent = on ? '\u25b6' : '\u25bc';
}

function savePrompt(content) {
  fetch('/api/prompt', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({content: content})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) { document.getElementById('prompt-status').textContent = '\u2713 \u5df2\u4fdd\u5b58'; toast('\u6a21\u677f\u5df2\u4fdd\u5b58'); }
    else toast('\u4fdd\u5b58\u5931\u8d25', 'error');
  }).catch(function(e){toast('\u8bf7\u6c42\u5931\u8d25', 'error')});
}

function resetPrompt() {
  fetch('/api/prompt/reset', {method:'POST'})
  .then(function(r){return r.json()}).then(function(d){
    if(d.success) { document.getElementById('prompt-template').value = d.template; toast('\u5df2\u91cd\u7f6e'); }
  });
}

function verifyLLM() {
  fetch('/api/verify-llm').then(function(r){return r.json()}).then(function(d){
    var el = document.getElementById('llm-status');
    el.innerHTML = d.success ? '<span class="status status-ok">\u2713 \u8fde\u63a5\u6b63\u5e38</span>' : '<span class="status status-err">\u2717 '+d.message+'</span>';
  });
}

function toggleGuard(name) {
  fetch('/api/guard/toggle', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({name: name})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) { toast('\u5df2\u66f4\u65b0'); setTimeout(function(){location.reload()}, 200); }
    else toast('\u64cd\u4f5c\u5931\u8d25', 'error');
  }).catch(function(e){toast('\u8bf7\u6c42\u5931\u8d25', 'error')});
}

function updateStrategyParam(strategy, key, value) {
  // int 字段转数字
  if (value === '' || value === null) value = null;
  else if (!isNaN(value) && value !== true && value !== false) value = parseInt(value);
  fetch('/api/override', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({strategy: strategy, key: key, value: value})
  });
}

function updateStrategyMulti(strategy, key, cb) {
  // strategy 参数可能是 "strategy_headers"，去掉前缀
  var clean = strategy.replace(/^strategy_/, '');
  var checks = document.querySelectorAll('#form-strategy-' + clean + ' input[type=checkbox][value]');
  var values = [];
  checks.forEach(function(c) { if(c.checked) values.push(c.value); });
  fetch('/api/override', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({strategy: clean, key: key, value: values})
  });
}

function toggleGeekEdit(on) {
  var areas = document.querySelectorAll('[id^="geek-editor-"]');
  for(var i = 0; i < areas.length; i++) {
    areas[i].readOnly = !on;
    areas[i].style.background = on ? '#fff' : '#f5f5f5';
  }
  document.getElementById('geek-edit-hint').textContent = on ? '编辑模式下可修改 JSON' : '只读模式，可加载已保存模板';
  document.getElementById('geek-btn-apply').disabled = !on;
  document.getElementById('geek-btn-save').disabled = !on;
  document.getElementById('geek-btn-overwrite').disabled = !on;
  document.getElementById('geek-btn-new').disabled = !on;
  // 持久化到 config.json
  fetch('/api/geekedit/toggle', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({enabled: on})
  });
}

function _mergeGeekSections() {
  var a = ['prompt','embedding','splitter','router','other'];
  var m = {};
  for(var i = 0; i < a.length; i++) {
    var ta = document.getElementById('geek-editor-' + a[i]);
    if(!ta) continue;
    try { Object.assign(m, JSON.parse(ta.value)); } catch(e) { return {error: '\u5206\u6bb5 ['+a[i]+'] JSON \u9519\u8bef: '+e.message}; }
  }
  return m;
}

function applyGeekConfig() {
  var m = _mergeGeekSections();
  if(m.error) { toast(m.error, 'error'); return; }
  fetch('/api/config/raw', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify(m, null, 2)
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) { document.getElementById('geek-status').textContent = '\u2713 \u5df2\u5e94\u7528'; toast('\u914d\u7f6e\u5df2\u66f4\u65b0'); }
    else { toast(d.error, 'error'); }
  }).catch(function(e){toast('\u8bf7\u6c42\u5931\u8d25', 'error')});
}

function newGeekTemplate() {
  var ta = document.getElementById('geek-template-name');
  ta.value = '\u9ed8\u8ba4\u6a21\u677f_' + new Date().toISOString().slice(0,10);
  toast('\u5df2\u751f\u6210\u65b0\u6a21\u677f\u540d\u79f0\uff0c\u7f16\u8f91\u540e\u70b9\u4fdd\u5b58');
}

function saveGeekTemplate() {
  var name = document.getElementById('geek-template-name').value.trim();
  if(!name) { toast('\u8bf7\u5148\u586b\u5199\u6a21\u677f\u540d\u79f0', 'error'); return; }
  var m = _mergeGeekSections();
  if(m.error) { toast(m.error, 'error'); return; }
  fetch('/api/template/list', {method:'POST'}).then(function(r){return r.json()}).then(function(d){
    if(d.templates && d.templates.some(function(t){ return t.name === name; })) {
      toast('\u6a21\u677f "'+name+'" \u5df2\u5b58\u5728\uff0c\u8bf7\u7528\u8986\u76d6', 'error');
      return;
    }
    fetch('/api/template/save', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({name: name, label: name, config: m})
    }).then(function(r){return r.json()}).then(function(d){
      if(d.success) { toast('\u5df2\u4fdd\u5b58\uff1a'+name); document.getElementById('geek-status').textContent = '\u2713 \u5df2\u4fdd\u5b58'; refreshGeekTemplates(); }
      else toast(d.error, 'error');
    }).catch(function(e){toast('\u8bf7\u6c42\u5931\u8d25', 'error')});
  });
}

function overwriteGeekTemplate() {
  var name = document.getElementById('geek-template-name').value.trim();
  if(!name) { toast('\u8bf7\u5148\u586b\u5199\u6a21\u677f\u540d\u79f0', 'error'); return; }
  var m = _mergeGeekSections();
  if(m.error) { toast(m.error, 'error'); return; }
  showConfirm('\u8986\u76d6\u6a21\u677f', '\u786e\u5b9a\u8986\u76d6\u6a21\u677f "'+name+'"\uff1f', function(ok){
    if(!ok) return;
    fetch('/api/template/save', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({name: name, label: name, config: m})
    }).then(function(r){return r.json()}).then(function(d){
      if(d.success) { toast('\u5df2\u8986\u76d6\uff1a'+name); document.getElementById('geek-status').textContent = '\u2713 \u5df2\u8986\u76d6'; refreshGeekTemplates(); }
      else toast(d.error, 'error');
    }).catch(function(e){toast('\u8bf7\u6c42\u5931\u8d25', 'error')});
  });
}

function editGeekTemplate(name) {
  fetch('/api/template/load', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({name: name})
  }).then(function(r){return r.json()}).then(function(d){
    if(!d.success) { toast(d.error, 'error'); return; }
    var cfg = d.config || {};
    var edit = document.getElementById('geek-edit-toggle').checked;
    document.getElementById('geek-editor-prompt').value = JSON.stringify({prompt: cfg.prompt || {}}, null, 2);
    document.getElementById('geek-editor-embedding').value = JSON.stringify({embedding: cfg.embedding || {}, retrieval: cfg.retrieval || {}, reranker: cfg.reranker || {}}, null, 2);
    document.getElementById('geek-editor-splitter').value = JSON.stringify({splitting: cfg.splitting || {}}, null, 2);
    document.getElementById('geek-editor-router').value = JSON.stringify({router: cfg.router || {}, guard: cfg.guard || {}}, null, 2);
    document.getElementById('geek-editor-other').value = JSON.stringify({mode: cfg.mode, input_sources: cfg.input_sources, preprocess: cfg.preprocess, kb: cfg.kb}, null, 2);
    document.getElementById('geek-template-name').value = name;
    toast(edit ? '\u5df2\u52a0\u8f7d\u6a21\u677f\uff08\u53ef\u7f16\u8f91\uff09\uff1a'+name : '\u5df2\u52a0\u8f7d\u6a21\u677f\uff08\u53ea\u8bfb\uff09\uff1a'+name);
  }).catch(function(e){toast('\u8bf7\u6c42\u5931\u8d25', 'error')});
}

function loadGeekTemplate(name) {
  showConfirm('\u52a0\u8f7d\u6a21\u677f', '\u786e\u5b9a\u52a0\u8f7d\u6a21\u677f "'+name+'" \u5e76\u8986\u76d6\u5f53\u524d\u914d\u7f6e\uff1f', function(ok) {
    if(!ok) return;
    fetch('/api/template/load', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({name: name})
    }).then(function(r){return r.json()}).then(function(d){
      if(d.success) { toast('\u5df2\u52a0\u8f7d\u6a21\u677f\uff1a'+name); setTimeout(function(){location.reload()}, 300); }
      else toast(d.error, 'error');
    }).catch(function(e){toast('\u8bf7\u6c42\u5931\u8d25', 'error')});
  });
}

function deleteGeekTemplate(name) {
  showConfirm('\u5220\u9664\u6a21\u677f', '\u786e\u5b9a\u5220\u9664\u6a21\u677f "'+name+'"\uff1f', function(ok) {
    if(!ok) return;
    fetch('/api/template/delete', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({name: name})
    }).then(function(r){return r.json()}).then(function(d){
      if(d.success) { toast('\u5df2\u5220\u9664'); refreshGeekTemplates(); }
      else toast(d.error, 'error');
    }).catch(function(e){toast('\u8bf7\u6c42\u5931\u8d25', 'error')});
  });
}

function refreshGeekTemplates() {
  var el = document.getElementById('template-items');
  if(!el) return;
  el.innerHTML = '\u52a0\u8f7d\u4e2d...';
  fetch('/api/template/list', {method:'POST'}).then(function(r){return r.json()}).then(function(d){
    if(!d.templates || d.templates.length === 0) {
      el.innerHTML = '\u6682\u65e0\u4fdd\u5b58\u7684\u6a21\u677f\u3002';
      return;
    }
    el.innerHTML = d.templates.map(function(t) {
      return '<div style=\"display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #eee;\">' +
        '<span><strong>' + t.label + '</strong> <span style=\"color:#aaa;font-size:11px;\">(' + t.name + ')</span></span>' +
        '<span>' +
        '<button class=\"btn btn-primary\" style=\"padding:4px 10px;font-size:11px;margin-right:4px;\" onclick=\"editGeekTemplate(\\'' + t.name + '\\')\">\u7f16\u8f91</button>' +
        '<button class=\"btn btn-secondary\" style=\"padding:4px 10px;font-size:11px;margin-right:4px;\" onclick=\"loadGeekTemplate(\\'' + t.name + '\\')\">\u52a0\u8f7d</button>' +
        '<button class=\"btn btn-danger\" style=\"padding:4px 10px;font-size:11px;\" onclick=\"deleteGeekTemplate(\\'' + t.name + '\\')\">\u5220\u9664</button>' +
        '</span></div>';
    }).join('');
  });
}

function refreshRules() {
  Promise.all([
    fetch('/api/rules/list', {method:'POST'}).then(function(r){return r.json()}),
    fetch('/api/kb-models', {method:'POST'}).then(function(r){return r.json()})
  ]).then(function(results) {
    var d = results[0], kbData = results[1];
    var el = document.getElementById('rules-list');
    var rules = d.rules || {};
    var kbModels = (kbData && kbData.kb_models) || {};
    var names = Object.keys(rules);
    if (names.length === 0) {
      el.innerHTML = '\u6682\u65e0\u81ea\u5b9a\u4e49\u89c4\u5219\uff0c\u70b9\u201c\u91cd\u7f6e\u9ed8\u8ba4\u201d\u521b\u5efa\u9ed8\u8ba4\u89c4\u5219\u3002';
      return;
    }
    el.innerHTML = names.map(function(name) {
      var r = rules[name];
      var kws = (r.keywords || []).join(', ');
      var exts = (r.extensions || []).join(', ');
      var modelLabel = '\u9ed8\u8ba4\u6a21\u578b';
      if (kbModels[name]) {
        var p = kbModels[name];
        // 从路径提取模型目录名（跨平台兼容 \ 和 /）
        var sep = p.indexOf('\\\\') >= 0 ? '\\\\' : '/';
        var parts = p.split(sep);
        var dirName = parts[parts.length-1] || p;
        // 模型目录名含 _ 连接 org_name → org/name 显示
        var idx = dirName.indexOf('_');
        if (idx > 0) {
          modelLabel = dirName.slice(0, idx) + '/' + dirName.slice(idx + 1);
        } else {
          modelLabel = dirName;
        }
      }
      var modelHtml = '<br><span style=\"font-size:11px;color:#667eea;\">\u25b6 \u6a21\u578b: ' + modelLabel + '</span>';
      return '<div style=\"display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #eee;\">' +
        '<div style=\"flex:1;\"><strong>' + name + '</strong> ' +
        (r.description ? '<span style=\"color:#888;font-size:11px;\">(' + r.description + ')</span>' : '') +
        '<br><span style=\"font-size:11px;color:#aaa;\">\u5173\u952e\u8bcd: ' + (kws || '\u2014') + ' | \u6269\u5c55\u540d: ' + (exts || '\u2014') + '</span>' +
        modelHtml + '</div>' +
        '<span>' +
        '<button class=\"btn btn-secondary\" style=\"padding:3px 10px;font-size:11px;margin-right:4px;\" onclick=\"editRule(\\'' + name + '\\')\">\u7f16\u8f91</button>' +
        '<button class=\"btn btn-danger\" style=\"padding:3px 10px;font-size:11px;\" onclick=\"deleteRule(\\'' + name + '\\')\">\u5220\u9664</button>' +
        '</span></div>';
    }).join('');
  });
}

function showRuleEditor(editName) {
  document.getElementById('rule-editor-overlay').style.display = 'flex';
  document.getElementById('rule-editor-title').textContent = editName ? '\u7f16\u8f91\u89c4\u5219' : '\u6dfb\u52a0\u89c4\u5219';
}

function hideRuleEditor() {
  document.getElementById('rule-editor-overlay').style.display = 'none';
  document.getElementById('rule-name').value = '';
  document.getElementById('rule-name').readOnly = false;
  document.getElementById('rule-keywords').value = '';
  document.getElementById('rule-extensions').value = '';
  document.getElementById('rule-desc').value = '';
  document.getElementById('rule-model').value = '';
}

function editRule(name) {
  Promise.all([
    fetch('/api/rules/list', {method:'POST'}).then(function(r){return r.json()}),
    fetch('/api/kb-models', {method:'POST'}).then(function(r){return r.json()})
  ]).then(function(results) {
    var d = results[0], kbData = results[1];
    var r = (d.rules || {})[name];
    if (!r) { toast('\u89c4\u5219\u4e0d\u5b58\u5728', 'error'); return; }
    document.getElementById('rule-name').value = name;
    document.getElementById('rule-name').readOnly = true;
    document.getElementById('rule-keywords').value = (r.keywords || []).join(', ');
    document.getElementById('rule-extensions').value = (r.extensions || []).join(', ');
    document.getElementById('rule-desc').value = r.description || '';
    document.getElementById('rule-editor-title').textContent = '\u7f16\u8f91\u89c4\u5219: ' + name;
    // 设置模型下拉
    var kbModels = (kbData && kbData.kb_models) || {};
    var sel = document.getElementById('rule-model');
    if (kbModels[name]) {
      sel.value = kbModels[name];
    } else {
      sel.value = '';
    }
    document.getElementById('rule-editor-overlay').style.display = 'flex';
  });
}

function saveRule() {
  var name = document.getElementById('rule-name').value.trim();
  if (!name) { toast('\u8bf7\u8f93\u5165\u77e5\u8bc6\u5e93\u540d', 'error'); return; }
  var kws = document.getElementById('rule-keywords').value.split(',').map(function(s){return s.trim()}).filter(function(s){return s});
  var exts = document.getElementById('rule-extensions').value.split(',').map(function(s){return s.trim()}).filter(function(s){return s});
  var desc = document.getElementById('rule-desc').value.trim();
  var modelId = document.getElementById('rule-model').value;
  // 先保存规则，再设置 KB 模型
  fetch('/api/rules/save', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({name: name, keywords: kws, extensions: exts, description: desc})
  }).then(function(r){return r.json()}).then(function(d) {
    if (!d.success) { toast(d.error, 'error'); return; }
    // 设置 KB 模型
    fetch('/api/kb-model', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({kb_name: name, model_id: modelId})
    }).then(function(r){return r.json()}).then(function(d2) {
      toast(d2.success ? '\u89c4\u5219\u5df2\u4fdd\u5b58\uff0c\u6a21\u578b\u5df2\u66f4\u65b0' : '\u89c4\u5219\u5df2\u4fdd\u5b58\uff0c\u6a21\u578b\u8bbe\u7f6e\u5931\u8d25');
      hideRuleEditor();
      refreshRules();
    });
  });
}

function deleteRule(name) {
  if (!confirm('\u786e\u5b9a\u5220\u9664\u89c4\u5219 "' + name + '"\uff1f')) return;
  fetch('/api/rules/delete', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({name: name})
  }).then(function(r){return r.json()}).then(function(d) {
    if (d.success) { toast('\u5df2\u5220\u9664'); refreshRules(); }
    else toast(d.error, 'error');
  });
}

function resetRules() {
  fetch('/api/rules/reset', {method:'POST'})
  .then(function(r){return r.json()}).then(function(d) {
    if (d.success) { toast('\u89c4\u5219\u5df2\u91cd\u7f6e'); refreshRules(); }
    else toast(d.error, 'error');
  });
}

function updateAdvView() {
  var s = document.getElementById('strategy-select').value;
  var d2 = document.getElementById('secondary-select').value;
  // 隐藏所有策略和后处理表单
  document.querySelectorAll('.strategy-form').forEach(function(f) { f.style.display = 'none'; });
  document.querySelectorAll('.secondary-form').forEach(function(f) { f.style.display = 'none'; });
  // 显示当前策略表单
  var cur = document.getElementById('form-strategy-' + s);
  if (cur) cur.style.display = 'block';
  // 显示后处理表单
  var secContainer = document.getElementById('secondary-forms-container');
  if (d2) {
    secContainer.style.display = 'block';
    var secForm = document.getElementById('form-secondary-' + d2);
    if (secForm) secForm.style.display = 'block';
  } else {
    secContainer.style.display = 'none';
  }
}

function resetAll() {
  fetch('/api/reset', {method:'POST'})
  .then(function(r){return r.json()}).then(function(d){
    if(d.success) { toast('已重置'); setTimeout(function(){location.reload()}, 500); }
  });
}

function downloadModel(id){
  var el = document.createElement('div');
  el.id = 'dl-status';
  el.style.cssText = 'position:fixed;bottom:20px;left:20px;right:20px;max-width:500px;z-index:9999;background:white;border-radius:12px;padding:16px 20px;box-shadow:0 4px 20px rgba(0,0,0,0.2);font-size:13px;border-left:4px solid #667eea;';
  el.innerHTML = '<div style=\"display:flex;align-items:center;gap:10px;\"><div style=\"width:20px;height:20px;border:3px solid #e0d4f5;border-top-color:#667eea;border-radius:50%;animation:spin 0.8s linear infinite;\"></div><div style=\"flex:1;\"><strong>下载 ' + id.split('/').pop() + '</strong><br><span id=\"dl-msg\" style=\"color:#888;font-size:12px;\">准备中...</span></div><button onclick=\"this.parentElement.parentElement.remove()\" style=\"background:none;border:none;font-size:18px;cursor:pointer;color:#aaa;\">x</button></div>';
  document.body.appendChild(el);
  // 启动下载
  fetch('/api/download-model',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model_id:id})});
  // 轮询状态
  var poll = setInterval(function(){
    fetch('/api/download-status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model_id:id})})
    .then(function(r){return r.json()}).then(function(d){
      var msg = document.getElementById('dl-msg');
      if(!msg){clearInterval(poll);return}
      if(d.status==='starting') msg.textContent = '准备中...';
      else if(d.status==='downloading'){msg.innerHTML = (d.message||'下载中...') + '<br><span style=\"color:#aaa;font-size:11px;\">' + (d.size_mb||0) + ' MB | ' + (d.speed||'') + '</span>';}
      else if(d.status==='done'){msg.textContent = '完成';el.style.borderLeftColor='#3B6D11';clearInterval(poll);setTimeout(function(){el.remove();location.reload()},1000);}
      else if(d.status==='failed'){msg.textContent = '失败: ' + d.message;el.style.borderLeftColor='#ff6b6b';clearInterval(poll);}
    });
  },2000);
}
function toggleKB(){fetch('/api/kb/toggle',{method:'POST'}).then(function(r){return r.json()}).then(function(d){if(d.success){toast('\u591a\u77e5\u8bc6\u5e93\u8def\u7531:'+(d.enabled?'\u542f\u7528':'\u7981\u7528'));setTimeout(function(){location.reload()},200)}else toast(d.error,'error')});}
function onFallbackModelChange(v){updateConfig('router','model_path_fallback',v)}
function toggleRouter(){fetch('/api/router/toggle',{method:'POST'}).then(function(r){return r.json()}).then(function(d){if(d.success){toast('\u8def\u7531:'+(d.enabled?'\u542f\u7528':'\u7981\u7528'));setTimeout(function(){location.reload()},200)}else toast(d.error,'error')});}
function toggleReranker(){fetch('/api/reranker/toggle',{method:'POST'}).then(function(r){return r.json()}).then(function(d){if(d.success){toast('Rerank:'+(d.enabled?'\u542f\u7528':'\u7981\u7528'));setTimeout(function(){location.reload()},200)}else toast(d.error,'error')});}
function toggleAdvSig(){var e=document.getElementById('adv-sig-content'),a=document.getElementById('adv-sig-arrow'),o=e.style.display==='block';e.style.display=o?'none':'block';a.textContent=o?'\u25b6':'\u25bc';}
function rebuildSigs(){fetch('/api/router/rebuild-signatures',{method:'POST'}).then(function(r){return r.json()}).then(function(d){if(d.success){toast('\u5df2\u91cd\u5efa');setTimeout(function(){location.reload()},500)}else toast(d.error,'error')});}
function toggleSortRules(){var e=document.getElementById('adv-rules-content'),a=document.getElementById('adv-rules-arrow'),o=e.style.display==='block';e.style.display=o?'none':'block';a.textContent=o?'\u25b6':'\u25bc';if(!o)refreshSortRules();}
function refreshSortRules(){fetch('/api/reranker/rules',{method:'POST'}).then(function(r){return r.json()}).then(function(d){var e=document.getElementById('sort-rules-list'),rules=d.rules||[];if(!rules.length){e.innerHTML='<span style=\"color:#aaa;\">\u6682\u65e0</span>';return}e.innerHTML=rules.map(function(r,i){return'<div style=\"display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid #eee;\"><div style=\"flex:1;font-size:12px;\">#'+(i+1)+' '+JSON.stringify(r)+'</div><button class=\"btn btn-danger\" style=\"padding:2px 8px;font-size:11px;\" onclick=\"deleteSortRule('+i+')\">x</button></div>'}).join('')});}
function deleteSortRule(i){if(!confirm('\u5220\u9664\u89c4\u5219 #'+(i+1)+'?'))return;fetch('/api/reranker/rules/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index:i})}).then(function(r){return r.json()}).then(function(d){if(d.success){toast('\u5df2\u5220\u9664');refreshSortRules()}else toast(d.error,'error')});}
function setSrcDot(key, cls) {var el=document.getElementById('dot-'+key);if(el){el.className='src-dot '+cls;}}
function refreshSrcStatus() {
  fetch('/api/dep-check',{method:'POST'}).then(function(r){return r.json()}).then(function(d){if(!d.success)return;var map=d.status||{};['enable_pdf','enable_ocr','enable_html2md'].forEach(function(k){var st=map[k]||'missing';setSrcDot(k,st);});});
}
function onToggleInputSource(key) {
  setSrcDot(key,'checking');
  fetch('/api/input-source',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({key:key})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){setSrcDot(key,d.dep||'missing');toast('\u5df2\u66f4\u65b0');setTimeout(function(){location.reload()},500);}
    else{setSrcDot(key,d.dep||'missing');toast(d.error||'\u64cd\u4f5c\u5931\u8d25','error');}
  }).catch(function(e){setSrcDot(key,'missing');toast('\u8bf7\u6c42\u5931\u8d25','error');});
}
function addSortRule(){showSortRuleEditor()}
function showSortRuleEditor(){document.getElementById('sort-rule-editor-overlay').style.display='flex';onSortRuleTypeChange();}
function hideSortRuleEditor(){document.getElementById('sort-rule-editor-overlay').style.display='none';document.getElementById('sort-rule-params').style.display='none';}
function onSortRuleTypeChange(){var t=document.getElementById("sort-rule-type").value;var e=document.getElementById("sort-rule-params-fields");var p=document.getElementById("sort-rule-params");if(!t){p.style.display="none";return}var html="";if(t==="score_weight")html='<div class=\"form-group\"><label>嵌入分权重 (embedding_score)</label><input id=\"sr-emb\" type=\"number\" value=\"0.6\" min=\"0\" max=\"1\" step=\"0.05\" style=\"width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;\"></div><div class=\"form-group\"><label>Rerank分权重 (rerank_score)</label><input id=\"sr-rer\" type=\"number\" value=\"0.4\" min=\"0\" max=\"1\" step=\"0.05\" style=\"width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;\"></div>';else if(t==="recency")html='<div class=\"form-group\"><label>半衰期天数 (days_halflife)</label><input id=\"sr-days\" type=\"number\" value=\"30\" min=\"1\" style=\"width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;\"></div>';else if(t==="source_weight")html='<div class=\"form-group\"><label>来源加权 JSON</label><textarea id=\"sr-sources\" rows=\"3\" style=\"width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;\" placeholder=\"例: {legal_gov:1.5, baike:1.0}\"></textarea></div>';else if(t==="boost_keywords")html='<div class=\"form-group\"><label>关键词（逗号分隔）</label><input id=\"sr-keys\" type=\"text\" style=\"width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;\" placeholder=\"例: python,api,definitive\"></div><div class=\"form-group\"><label>提升倍数 (boost)</label><input id=\"sr-boost\" type=\"number\" value=\"1.2\" min=\"0\" step=\"0.1\" style=\"width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;\"></div>';e.innerHTML=html;p.style.display="block";}
function saveSortRule(){var t=document.getElementById('sort-rule-type').value;if(!t){toast('\u8bf7\u9009\u62e9\u89c4\u5219\u7c7b\u578b','error');return}var p={type:t};if(t==='score_weight'){p.embedding_score=parseFloat(document.getElementById('sr-emb').value||0.6);p.rerank_score=parseFloat(document.getElementById('sr-rer').value||0.4)}else if(t==='recency'){p.days_halflife=parseInt(document.getElementById('sr-days').value||30)}else if(t==='source_weight'){try{var v=JSON.parse(document.getElementById('sr-sources').value||'{}');Object.assign(p,v)}catch(e){toast('\u89e3\u6790\u5931\u8d25','error');return}}else if(t==='boost_keywords'){var k=document.getElementById('sr-keys').value.split(',').map(function(s){return s.trim()}).filter(function(s){return s});if(!k.length){toast('\u8bf7\u8f93\u5165\u5173\u952e\u8bcd','error');return}p.keywords=k;p.boost=parseFloat(document.getElementById('sr-boost').value||1.2)}fetch('/api/reranker/rules/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rule:p})}).then(function(r){return r.json()}).then(function(d){if(d.success){toast('\u5df2\u6dfb\u52a0');hideSortRuleEditor();refreshSortRules()}else toast(d.error,'error')});}
function initPreproc() {
  var cb = document.getElementById('preproc-enable');
  if(cb) {
    var checked = cb.checked;
    for(var l = 1; l <= 4; l++) {
      var lcb = document.getElementById('h' + l + '-enable');
      var lsel = document.getElementById('h' + l + '-preset');
      if(lcb) { lcb.disabled = !checked; }
      if(lsel) { lsel.disabled = !checked; }
    }
    if(checked) {
      var sel = document.getElementById('strategy-select');
      if(sel) { sel.value = 'headers'; sel.disabled = true; }
    }
  }
}
// ===== 模态框（替代 prompt/confirm） =====
var _modalCb = null;
var _modalType = '';

function showPrompt(title, placeholder, cb) {
  _modalCb = cb; _modalType = 'prompt';
  document.getElementById('modal-title').textContent = title;
  var inp = document.getElementById('modal-input');
  inp.style.display = 'block'; inp.value = ''; inp.placeholder = placeholder || '';
  document.getElementById('modal-msg').style.display = 'none';
  document.getElementById('modal-overlay').style.display = 'flex';
  setTimeout(function(){inp.focus();}, 100);
}

function showConfirm(title, msg, cb) {
  _modalCb = cb; _modalType = 'confirm';
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-input').style.display = 'none';
  document.getElementById('modal-msg').style.display = 'block';
  document.getElementById('modal-msg').textContent = msg;
  document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
  if(_modalType === 'prompt' && _modalCb) _modalCb(null);
  _modalCb = null;
}

function confirmModal() {
  document.getElementById('modal-overlay').style.display = 'none';
  if(_modalCb) {
    if(_modalType === 'prompt') _modalCb(document.getElementById('modal-input').value);
    else _modalCb(true);
  }
  _modalCb = null;
}
// ===== 模态框结束 =====

window.onload = function() { updateAdvView(); refreshGeekTemplates(); refreshRules(); refreshSrcStatus(); initPreproc(); initPrompt(); toggleGeekEdit(document.getElementById('geek-edit-toggle').checked); };

// ----- Prompt 模板相关函数 -----
var _prompt_save_timer = null;

function initPrompt() {
  var sel = document.getElementById('prompt-preset');
  if (!sel) return;
  loadPreset(sel.value);
  sel.addEventListener('change', function() { loadPreset(this.value); });
}

function loadPreset(key) {
  var sel = document.getElementById('prompt-preset');
  var opt = sel && sel.options[sel.selectedIndex];
  var tpl = opt && opt.getAttribute('data-template');
  if (!tpl) return;
  document.getElementById('prompt-template').value = tpl;
  renderVariables(tpl);
  onPromptChange(tpl);
}

function renderVariables(tpl) {
  var vars = tpl.match(/\{(\w+)\}/g) || [];
  var uniq = {};
  vars.forEach(function(v) { uniq[v] = true; });
  var placeholders = {
    dim: '如：价格/性能/质量',
    role: '如：化学分析师/技术专家',
    alt: '如：其他品牌/替代方法',
  };
  var html = '';
  for (var v in uniq) {
    var name = v.slice(1, -1);
    var hint = placeholders[name] || '请输入' + name;
    html += '<span style="display:inline-block;margin-right:10px;margin-bottom:4px;">' +
      name + ': <input type="text" data-var="' + name + '" placeholder="' + hint + '" style="width:140px;padding:2px 6px;border:1px solid #ddd;border-radius:4px;font-size:12px;vertical-align:middle;"> </span>';
  }
  document.getElementById('prompt-variables').innerHTML = html;
  document.querySelectorAll('#prompt-variables input').forEach(function(el) {
    el.addEventListener('change', function() {
      onPromptChange(document.getElementById('prompt-template').value);
    });
  });
}

function onPromptChange(content) {
  document.getElementById('prompt-status').textContent = '\u23f3 保存中...';
  if (_prompt_save_timer) clearTimeout(_prompt_save_timer);
  _prompt_save_timer = setTimeout(function() {
    fetch('/api/prompt', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({content: content})
    }).then(function(r){return r.json()}).then(function(d){
      if(d.success) {
        document.getElementById('prompt-status').textContent = '\u2713 已保存';
      }
    });
  }, 400);
  // 更新完整预览
  var prefix = window.PROMPT_SYSTEM_PREFIX || '';
  var preview = document.getElementById('full-prompt-preview');
  if (preview) preview.textContent = prefix + content;
}
</script>"""

def generate_html():
    """生成自包含 HTML 设置界面"""
    cfg = load_config()
    kbs = list_knowledge_bases()
    all_models = list_downloaded_models()
    template = load_template()
    full_prompt_preview = get_full_prompt()
    def _html_attr(s):
        return s.replace("&","&amp;").replace('"',"&quot;").replace("<","&lt;").replace(">","&gt;").replace("\n","&#10;")
    preset_options = ""
    for key, p in PROMPT_PRESETS.items():
        selected = " selected" if p["template"] == template else ""
        dt = _html_attr(p["template"])
        preset_options += f'<option value="{key}" data-template="{dt}"{selected}>{p["label"]}</option>'

    router_cfg = cfg.get("router", {})
    fb_cfg = router_cfg.get("fallback", {})
    rerank_cfg = cfg.get("reranker", {})
    kb_cfg = cfg.get("kb", {})
    kb_sigs = list_kb_signatures()
    # Build model lists
    from embedding_model_manager import RECOMMENDED_MODELS, RECOMMENDED_RERANK_MODELS
    dl = list_downloaded_models()
    dl_ids = {m.get("model_id","").lower() for m in dl}
    # 过滤掉重排序模型，只保留真正的嵌入模型（供 KB 嵌入模型选择器使用）
    reranker_ids = {m["id"].lower() for m in RECOMMENDED_RERANK_MODELS}
    models = [m for m in all_models if m.get("model_id","").lower() not in reranker_ids]
    Q = "'"
    def _mlist(role, models_def, current_path=""):
        """生成模型列表：role=embedding|rerank|fb, models_def=模型定义列表"""
        rows = []
        default_id = models_def[0]["id"] if models_def else ""
        for m in models_def:
            mid=m["id"]
            # 无配置时默认选中列表第一个
            checked='checked' if (current_path==mid or (not current_path and mid==default_id)) else ""
            ok=mid.lower() in dl_ids
            st="\u5df2\u4e0b\u8f7d" if ok else "\u672a\u4e0b\u8f7d"
            bt="" if ok else f'<button class="btn btn-primary" style="padding:4px 10px;font-size:11px;white-space:nowrap;" onclick="downloadModel({Q}{mid}{Q})">\u4e0b\u8f7d</button>'
            if role=="fb":
                hdl = f'onchange=onFallbackModelChange({Q}{mid}{Q})'
            elif role=="rerank":
                hdl = f'onchange=updateConfig("reranker","model_path",this.value)'
            else:
                hdl = f'onchange=updateConfig("embedding","model_path",this.value)'
            rows.append(f'<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #eee;"><input type="radio" name="{role}-model" value="{mid}" id="{role[:3]}-{mid}" {checked} {hdl} style="flex-shrink:0;"><label for="{role[:3]}-{mid}" style="flex:1;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{mid}">{"[嵌入] " if role=="embedding" else "[重排序] " if role=="rerank" else "[路由] "}{mid} <span style="color:#888;font-size:11px;">({m["size_mb"]}MB)</span></label><span style="font-size:11px;flex-shrink:0;color:{"#3B6D11" if ok else "#888"};">{st}</span>{bt}</div>')
        return "\n".join(rows)
    emb_model_html = _mlist("embedding", RECOMMENDED_MODELS, cfg.get("embedding",{}).get("model_path",""))
    rr_model_html = _mlist("rerank", RECOMMENDED_RERANK_MODELS, rerank_cfg.get("model_path",""))
    fb_model_html = _mlist("fb", RECOMMENDED_RERANK_MODELS, fb_cfg.get("model_path",""))
    guard_labels = {"mermaid": "🧜 Mermaid", "code": "💻 代码块", "math": "∑ LaTeX公式", "table": "📊 表格", "html": "🌐 HTML结构"}
    active_guards = cfg.get("splitting", {}).get("guards", ["code"])
    guard_card_html = ""
    for g in ["mermaid", "code", "math", "table", "html"]:
        active = g in active_guards
        border = "#667eea" if active else "#ddd"
        bg = "#f0f4ff" if active else "#fafafa"
        fg = "#667eea" if active else "#555"
        checked = "checked" if active else ""
        guard_card_html += f'<label style="display:flex;align-items:center;gap:6px;padding:8px 14px;border:2px solid {border};border-radius:10px;cursor:pointer;background:{bg};transition:all 0.2s;" onclick="toggleGuard(\'{g}\')">'
        guard_card_html += f'<input type="checkbox" {checked} style="accent-color:#667eea;">'
        guard_card_html += f'<span style="font-size:13px;font-weight:600;color:{fg};">{guard_labels[g]}</span></label>'
    guard_card_html += ""
    input_src = cfg.get("input_sources", {})
    def _src_dot_class(key):
        """计算输入源状态点的初始 CSS 类：关→off(黄), 开且依赖就绪→ready(绿), 开且缺依赖→missing(红)"""
        if not input_src.get(key, False):
            return "off"
        return _check_dep(key)

    # 预设正则选项
    PRESET_PATTERNS = {
        1: [  # h1
            ("自定义", ""),
            ("中文章节: 第X章 XXX", "^第[一二三四五六七八九十]+[章节篇]\\s+(.*)$"),
            ("英文章节: Chapter X", "^Chapter\\s+\\d+\\s*[.:]\\s*(.*)$"),
            ("数字标题: 1. XXX", "^\\d+\\s*[.．、]\\s*(.*)$"),
            ("英文字句标题", "^[A-Z][A-Za-z\\s]{10,}$"),
        ],
        2: [  # h2
            ("自定义", ""),
            ("中文数字: 一、XXX", "^[一二三四五六七八九十]+[、\\.]\\s*(.*)$"),
            ("数字编号: 1.1 XXX", "^\\d+\\.\\d+\\s+(.*)$"),
            ("字母编号: A. XXX", "^[A-Z]\\.\\s*(.*)$"),
            ("括号编号: (1) XXX", "^\\(\\d+\\)\\s+(.*)$"),
        ],
        3: [  # h3
            ("自定义", ""),
            ("数字编号: 1.1.1 XXX", "^\\d+\\.\\d+\\.\\d+\\s+(.*)$"),
            ("短横编号: 1-1 XXX", "^\\d+-\\d+\\s+(.*)$"),
        ],
        4: [  # h4
            ("自定义", ""),
            ("括号编号: (a) XXX", "^\\([a-z]\\)\\s+(.*)$"),
        ],
    }

    def _preproc_level_html(preproc_cfg, master_enabled=False):
        """Generate preprocessor 4-level heading config UI"""
        labels = ["#", "##", "###", "####"]
        hints = ["h1", "h2", "h3", "h4"]
        html_out = ""
        for idx in range(4):
            level = idx + 1
            patterns = preproc_cfg.get(f"h{level}_patterns", []) if preproc_cfg else []
            cb_checked = len(patterns) > 0
            text_val = chr(10).join(patterns) if patterns else ""
            # 透明度只受总开关控制，不受是否有模式影响
            card_opacity = "1" if master_enabled else "0.45"
            html_out += f'<div style="border:0.5px solid #ddd;border-radius:8px;padding:10px 12px;opacity:{card_opacity};">'
            # checkbox row
            html_out += f'<div style="display:grid;grid-template-columns:auto auto 1fr auto;align-items:center;gap:6px;margin-bottom:4px;">'
            html_out += f'<input type="checkbox" id="h{level}-enable" onchange="togglePreprocLevel({level},this.checked)" {"checked" if cb_checked else ""}{" disabled" if not master_enabled else ""}>'
            html_out += f'<label for="h{level}-enable" style="font-size:13px;font-weight:500;font-family:monospace;white-space:nowrap;">{labels[idx]}</label>'
            html_out += f'<span style="font-size:12px;color:#888;white-space:nowrap;">{hints[idx]}</span>'
            # preset dropdown
            presets = PRESET_PATTERNS.get(level, [])
            html_out += f'<select id="h{level}-preset" style="font-size:13px;padding:4px 8px;border:0.5px solid #aaa;border-radius:4px;width:180px;" onchange="applyPreset({level},this.value)"{" disabled" if not master_enabled else ""}>'
            for label, _ in presets:
                val = "" if label == "自定义" else label
                html_out += f'<option value="{val}">{label}</option>'
            html_out += f'</select>'
            html_out += f'</div>'
            # textarea
            disabled_ta = not (master_enabled and cb_checked)
            html_out += f'<textarea id="h{level}-patterns" rows="2" style="width:100%;font-family:monospace;font-size:12px;padding:6px 8px;border:0.5px solid #ddd;border-radius:4px;resize:vertical;box-sizing:border-box;line-height:1.5;{"background:#f5f5f5;color:#bbb;" if disabled_ta else ""}"{" disabled" if disabled_ta else ""}>{text_val}</textarea>'
            html_out += f'</div>'
        return html_out
    _dot_cls_pdf = _src_dot_class("enable_pdf")
    _dot_cls_ocr = _src_dot_class("enable_ocr")
    _dot_cls_html = _src_dot_class("enable_html2md")
    split_cfg = cfg.get("splitting", {})
    overrides = split_cfg.get("strategy_overrides", {})

    # 策略配置表单（根据 config_schema 动态生成）
    def _render_field(name, schema, prefix="primary"):
        ftype = schema.get("type", "text")
        default = schema.get("default", "")
        label = schema.get("label", name)
        fid = f"{prefix}_{name}"
        if ftype == "int":
            mn = schema.get("min", "")
            mx = schema.get("max", "")
            return f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;"><span style="font-size:13px;font-weight:600;color:#555;white-space:nowrap;">{label}:</span><input id="{fid}" type="number" min="{mn}" max="{mx}" value="{default}" style="flex:1;max-width:120px;padding:6px 8px;border:1.5px solid #ddd;border-radius:6px;font-size:13px;" onchange="updateStrategyParam(\'{prefix}\',\'{name}\',this.value||null)"></div>'
        elif ftype == "select":
            opts = "".join(f'<option value="{o}"{" selected" if o==default else ""}>{o}</option>' for o in schema.get("options", []))
            return f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;"><span style="font-size:13px;font-weight:600;color:#555;white-space:nowrap;">{label}:</span><select id="{fid}" style="flex:1;max-width:160px;padding:6px 8px;border:1.5px solid #ddd;border-radius:6px;font-size:13px;" onchange="updateStrategyParam(\'{prefix}\',\'{name}\',this.value)">{opts}</select></div>'
        elif ftype == "multi-select":
            opts = "".join(
                f'<label style="display:inline-flex;align-items:center;gap:3px;margin:0 4px 0 0;font-size:13px;cursor:pointer;white-space:nowrap;">'
                f'<input type="checkbox" value="{o}" checked style="accent-color:#667eea;width:14px;height:14px;" '
                f'onchange="updateStrategyMulti(\'{prefix}\',\'{name}\',this)">{o}</label>'
                for o in schema.get("options", [])
            )
            return f'<div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;"><span style="font-size:13px;font-weight:600;color:#555;margin-right:4px;">{label}:</span>{opts}</div>'
        elif ftype == "bool":
            chk = 'checked' if default else ''
            return f'<label style="display:inline-flex;align-items:center;gap:4px;cursor:pointer;font-size:13px;margin-top:4px;"><input type="checkbox" id="{fid}" {chk} style="accent-color:#667eea;" onchange="updateStrategyParam(\'{prefix}\',\'{name}\',this.checked)">{label}</label>'
        elif ftype == "text":
            return f'<div class="form-group"><label>{label}</label><input id="{fid}" type="text" value="{default}" style="width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:13px;" onchange="updateStrategyParam(\'{prefix}\',\'{name}\',this.value)"></div>'
        return ""

    strategy_forms = {}
    for sname, splugin in STRATEGY_REGISTRY.items():
        fields = "".join(_render_field(k, v, f"strategy_{sname}") for k, v in splugin.config_schema.items())
        # headers 策略：标题级别和去除标题放在一行
        if sname == "headers":
            fields = (f'<div style="display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap;">'
                      f'<div style="flex:1;min-width:200px;">{_render_field("headers_to_split_on", splugin.config_schema["headers_to_split_on"], "strategy_headers")}</div>'
                      f'<div style="padding-top:2px;">{_render_field("strip_headers", splugin.config_schema["strip_headers"], "strategy_headers")}</div>'
                      f'</div>')
        strategy_forms[sname] = f'<div id="form-strategy-{sname}" class="strategy-form" style="display:none;">{fields}</div>'
    strategy_forms_html = "".join(strategy_forms.values())

    # 后处理配置表单（复用主策略 schema + 默认 chunk_size 覆盖）
    secondary_forms_html = ""
    for sname in ["recursive", "fixed", "semantic"]:
        plugin = STRATEGY_REGISTRY.get(sname)
        if not plugin:
            continue
        if sname in ("fixed", "recursive"):
            fields = _render_field("chunk_size", {"type": "int", "label": "子切块大小", "default": 250, "min": 50, "max": 2000}, f"sec_{sname}")
            fields += _render_field("chunk_overlap", {"type": "int", "label": "子切重叠", "default": 25, "min": 0, "max": 500}, f"sec_{sname}")
        else:
            fields = _render_field("breakpoint_type", {"type": "select", "label": "断点算法", "options": ["percentile", "gradient", "stddev"], "default": "percentile"}, f"sec_{sname}")
        secondary_forms_html += f'<div id="form-secondary-{sname}" class="secondary-form" style="display:none;">{fields}</div>'

    # 原始 JSON 配置（极客模式）— 分段
    cfg.setdefault("prompt", {})["user_template"] = template
    cfg["prompt"]["system_prefix"] = get_system_prefix()

    def _section_json(*keys):
        sub = {}
        for k in keys:
            if k in cfg:
                sub[k] = cfg[k]
        return json.dumps(sub, ensure_ascii=False, indent=2)

    config_prompt_json = _section_json("prompt")
    config_embedding_json = _section_json("embedding", "retrieval", "reranker")
    config_splitter_json = _section_json("splitting")
    config_router_json = _section_json("router", "guard")
    config_other_json = _section_json("mode", "input_sources", "preprocess", "kb")
    geek_edit_enabled = cfg.get("geek_mode", {}).get("edit_enabled", False)
    config_json_str = json.dumps(cfg, ensure_ascii=False, indent=2)
    STRATEGY_LABELS = {
        "fixed": "固定窗口", "recursive": "递归切分", "headers": "层级/标题切",
        "sentence": "按句切", "semantic": "语义切",
    }

    html_out = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
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
.form-row-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }}
.btn {{ padding: 10px 24px; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
.btn-secondary {{ background: #e8e8e8; color: #555; }}
.btn-secondary:hover {{ background: #ddd; }}
.btn-danger {{ background: #ff6b6b; color: white; }}
.btn-danger:hover {{ background: #ee5a5a; }}
.btn-success {{ background: #51cf66; color: white; }}
.btn-success:hover {{ background: #40c057; }}
.btn-ai {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; }}
.btn-ai:hover {{ opacity: 0.9; transform: translateY(-1px); }}
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
@keyframes spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
.collapsible {{ background: #f0f4ff; border-radius: 10px; padding: 12px 16px; margin-top: 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-size: 14px; font-weight: 600; color: #5a3e8a; user-select: none; }}
.collapsible:hover {{ background: #e0d4f5; }}
.collapsible-content {{ display: none; padding: 16px 0 0; }}
.override-row {{ display: grid; grid-template-columns: 1fr 80px 80px; gap: 10px; align-items: center; padding: 6px 0; border-bottom: 1px solid #eee; }}
.override-row:last-child {{ border: none; }}
.override-row span {{ font-size: 13px; font-weight: 600; color: #555; }}
.override-row input {{ width: 100%; padding: 6px 8px; border: 1.5px solid #ddd; border-radius: 6px; font-size: 13px; text-align: center; }}
.override-row input:focus {{ border-color: #667eea; outline: none; }}
.combo-warn {{ background: #fff3bf; border: 1px solid #fcc419; border-radius: 8px; padding: 8px 12px; font-size: 12px; color: #e67700; margin-top: 8px; display: none; }}
.toggle-switch {{ position: relative; display: inline-block; width: 40px; height: 22px; }}
.toggle-switch input {{ opacity: 0; width: 0; height: 0; }}
.toggle-slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: #ccc; transition: 0.3s; border-radius: 22px; }}
.toggle-slider:before {{ position: absolute; content: ""; height: 16px; width: 16px; left: 3px; bottom: 3px; background: white; transition: 0.3s; border-radius: 50%; }}
input:checked + .toggle-slider {{ background: #667eea; }}
input:checked + .toggle-slider:before {{ transform: translateX(18px); }}
.src-dot {{ transition: color 0.3s; }}
.src-dot.ready {{ color: #2b8a3e; }}
.src-dot.missing {{ color: #c92a2a; }}
.src-dot.checking {{ color: #e67700; }}
.src-dot.off {{ color: #e67700; }}
</style>
</head>
<body>
<div class="container">
  <h1 style="color:white;margin-bottom:20px;font-weight:300;font-size:28px;">🛠️ RAG 系统设置面板</h1>

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

  <div class="card">
    <h2>📂 输入源 <span style="font-weight:400;color:#888;font-size:12px;">⬤ 黄=未开/检测中 绿=可用 红=依赖缺失</span></h2>
    <div class="form-row-3">
      <div class="form-group">
        <label>PDF 解析 <span class="src-dot {_dot_cls_pdf}" id="dot-enable_pdf" style="font-size:12px;">⬤</span></label>
        <label class="toggle-switch" onclick="toggleInputSource('enable_pdf')">
          <input type="checkbox" onclick="event.stopPropagation();" {"checked" if input_src.get("enable_pdf", False) else ""}>
          <span class="toggle-slider"></span>
        </label>
        <div style="font-size:11px;color:#888;margin-top:4px;">pypdf / pdfplumber</div>
      </div>
      <div class="form-group">
        <label>OCR 图片提取 <span class="src-dot {_dot_cls_ocr}" id="dot-enable_ocr" style="font-size:12px;">⬤</span></label>
        <label class="toggle-switch" onclick="toggleInputSource('enable_ocr')">
          <input type="checkbox" onclick="event.stopPropagation();" {"checked" if input_src.get("enable_ocr", False) else ""}>
          <span class="toggle-slider"></span>
        </label>
        <div style="font-size:11px;color:#888;margin-top:4px;">paddleocr (CPU: paddleocr / GPU: paddleocr-gpu) / easyocr</div>
      </div>
      <div class="form-group">
        <label>HTML→MD 转换 <span class="src-dot {_dot_cls_html}" id="dot-enable_html2md" style="font-size:12px;">⬤</span></label>
        <label class="toggle-switch" onclick="toggleInputSource('enable_html2md')">
          <input type="checkbox" onclick="event.stopPropagation();" {"checked" if input_src.get("enable_html2md", False) else ""}>
          <span class="toggle-slider"></span>
        </label>
        <div style="font-size:11px;color:#888;margin-top:4px;">html2text</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>📝 Prompt 模板</h2>
    <div style="font-size:13px;color:#888;margin-bottom:8px;">
      系统层（固化）：基于资料回答 + 资料/问题占位符 + 回答前缀
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>预设模板</label>
        <select id="prompt-preset" onchange="loadPreset(this.value)">
          {preset_options}
        </select>
      </div>
      <div class="form-group">
        <label>状态</label>
        <span id="prompt-status" style="line-height:32px;font-size:13px;color:#888;">—</span>
      </div>
    </div>
    <div class="form-group">
      <textarea id="prompt-template" rows="6" oninput="onPromptChange(this.value)" placeholder="用户层 Prompt，如输出格式要求" style="width:100%;font-family:monospace;font-size:12px;padding:6px 8px;border:0.5px solid #ddd;border-radius:4px;resize:vertical;box-sizing:border-box;line-height:1.5;">{template}</textarea>
    </div>
    <div id="prompt-variables" style="margin-bottom:8px;"></div>
    <details style="margin-top:10px;font-size:12px;color:#aaa;border-top:1px solid #eee;padding-top:8px;">
      <summary style="cursor:pointer;font-weight:bold;">完整 Prompt 预览（系统层+用户层）</summary>
      <pre id="full-prompt-preview" style="background:#f8f8f8;border:1px solid #eee;border-radius:4px;padding:8px;margin-top:4px;font-size:12px;white-space:pre-wrap;max-height:300px;overflow-y:auto;">{full_prompt_preview}</pre>
    </details>
  </div>

  <div class="card">
    <h2>📦 嵌入模型</h2>
    <div style="max-height:300px;width:100%;overflow-y:auto;border:1px solid #eee;border-radius:6px;padding:8px;">
      {emb_model_html}
    </div>
    <div class="form-row" style="margin-top:14px;">
      <div class="form-group">
        <label>设备</label>
        <select onchange="updateConfig('embedding','device',this.value)">
          <option value="auto" {"selected" if cfg.get("embedding",{}).get("device","auto")=="auto" else ""}>自动检测</option>
          <option value="cuda" {"selected" if cfg.get("embedding",{}).get("device")=="cuda" else ""}>GPU (CUDA)</option>
          <option value="cpu" {"selected" if cfg.get("embedding",{}).get("device")=="cpu" else ""}>CPU</option>
        </select>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>🛡️ 守卫栈 <span style="font-weight:400;color:#888;font-size:12px;">— 预处理，保护特殊内容不被切碎（多选）</span></h2>
    <div style="display:flex;flex-wrap:wrap;gap:10px;">
      {guard_card_html}
    </div>
  </div>

  <!-- Markdown 标题预处理 -->
  <div class="card">
    <h2>🏷️ Markdown 标题预处理 <span style="font-weight:400;color:#888;font-size:12px;"> — 注入标题标记后使用层级切分</span></h2>
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;padding:8px 12px;background:#f5f5f5;border-radius:8px;">
      <label class="toggle-switch" onclick="togglePreproc(!this.querySelector('input').checked)">
        <input type="checkbox" id="preproc-enable" onclick="event.stopPropagation();togglePreproc(this.checked)" {'checked' if cfg.get('preprocess',{}).get('enabled') else ''}>
        <span class="toggle-slider"></span>
      </label>
      <span style="font-size:13px;font-weight:500;">启用标题预处理 <span style="font-weight:400;color:#e74c3c;font-size:12px;">（启用后主策略强制为「层级/标题切分」）</span></span>
    </div>
    <div id="preproc-levels" style="display:grid;gap:10px;">
      {_preproc_level_html(cfg.get('preprocess',{}), cfg.get('preprocess',{}).get('enabled', False))}
    </div>
  </div>

  <div class="card">
    <h2>✂️ 文档切片</h2>
    <div class="form-row">
      <div class="form-group">
        <label>主策略</label>
        <select id="strategy-select" onchange="onStrategyChange(this.value)">
          <option value="recursive" {"selected" if split_cfg.get("strategy","recursive")=="recursive" else ""}>递归切分（推荐）</option>
          <option value="fixed" {"selected" if split_cfg.get("strategy")=="fixed" else ""}>固定窗口</option>
          <option value="headers" {"selected" if split_cfg.get("strategy")=="headers" else ""}>层级/标题切分</option>
          <option value="sentence" {"selected" if split_cfg.get("strategy")=="sentence" else ""}>按句切分</option>
          <option value="semantic" {"selected" if split_cfg.get("strategy")=="semantic" else ""}>语义切分</option>
        </select>
      </div>
      <div class="form-group">
        <label>后处理子切</label>
        <select id="secondary-select" onchange="onSecondaryChange(this.value)">
          <option value="">不处理</option>
          <option value="recursive" {"selected" if split_cfg.get("secondary_strategy")=="recursive" else ""}>递归子切</option>
          <option value="fixed" {"selected" if split_cfg.get("secondary_strategy")=="fixed" else ""}>固定窗口子切</option>
          <option value="semantic" {"selected" if split_cfg.get("secondary_strategy")=="semantic" else ""}>语义子切</option>
        </select>
      </div>
    </div>
    <div class="collapsible" onclick="toggleAdvanced()" id="adv-toggle">
      <span>⚙️ 切片参数（动态，依主策略+后处理组合）</span>
      <span id="adv-arrow">▶</span>
    </div>
    <div class="collapsible-content" id="adv-content">
      <div style="font-size:12px;color:#888;margin-bottom:8px;">当前策略配置</div>
      {strategy_forms_html}
      <div id="secondary-forms-container" style="margin-top:10px;padding-top:10px;border-top:1px dashed #ddd;display:none;">
        <div style="font-size:12px;color:#888;margin-bottom:8px;">后处理配置</div>
        {secondary_forms_html}
      </div>
      <div style="font-size:11px;color:#aaa;margin-top:8px;">
        💡 在对话中描述文档类型，系统将自动推荐切片配置。
      </div>
    </div>
  </div>

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

  <div class="card">
    <h2>🤖 LLM 模式</h2>
    <div class="form-group" style="margin-bottom:16px;">
      <label>运行模式 <span style="font-weight:400;color:#888;font-size:12px;">— 决定系统行为路径</span></label>
      <div style="display:flex;gap:12px;margin-top:8px;">
        <label style="flex:1;padding:14px 16px;border:2px solid {'#667eea' if cfg.get('mode','integrated')=='integrated' else '#ddd'};border-radius:12px;cursor:pointer;background:{'#f0f4ff' if cfg.get('mode','integrated')=='integrated' else '#fafafa'};transition:all 0.2s;" onclick="setMode('integrated')">
          <input type="radio" name="mode" value="integrated" {'checked' if cfg.get('mode','integrated')=='integrated' else ''} style="display:none;">
          <div style="font-size:16px;font-weight:600;color:{'#667eea' if cfg.get('mode','integrated')=='integrated' else '#555'};">🔌 集成模式</div>
          <div style="font-size:12px;color:#888;margin-top:4px;">无 LLM，纯检索。智能体根据检索到的 context 自行回答。</div>
          <div style="font-size:11px;color:#aaa;margin-top:2px;">无需配置 LLM，不产生额外推理成本</div>
        </label>
        <label style="flex:1;padding:14px 16px;border:2px solid {'#667eea' if cfg.get('mode','standalone')=='standalone' else '#ddd'};border-radius:12px;cursor:pointer;background:{'#f0f4ff' if cfg.get('mode','standalone')=='standalone' else '#fafafa'};transition:all 0.2s;" onclick="setMode('standalone')">
          <input type="radio" name="mode" value="standalone" {'checked' if cfg.get('mode','standalone')=='standalone' else ''} style="display:none;">
          <div style="font-size:16px;font-weight:600;color:{'#667eea' if cfg.get('mode','standalone')=='standalone' else '#555'};">🤖 独立模式</div>
          <div style="font-size:12px;color:#888;margin-top:4px;">检索 + LLM 全链路。系统自行完成检索→生成回答。</div>
          <div style="font-size:11px;color:#aaa;margin-top:2px;">需要配置下方 LLM 连接</div>
        </label>
      </div>
    </div>
    <div id="llm-settings" style="{'display:none' if cfg.get('mode','integrated')=='integrated' else 'block'};">
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
  </div>

  <div class="card">
    <h2>📚 知识库 & 分类规则</h2>
    <div class="form-row" style="margin-bottom:8px;">
      <div class="form-group">
        <label>启用多知识库路由 <span style="font-weight:400;color:#888;font-size:11px;">（关闭则路由层自动禁用）</span></label>
        <label class="toggle-switch" onclick="toggleKB()">
          <input type="checkbox" onclick="event.stopPropagation();" {"checked" if kb_cfg.get("enabled", True) else ""}><span class="toggle-slider"></span>
        </label>
      </div>
    </div>
    <div id="kb-list" style="margin-bottom:8px;">
      {' '.join(f'''<div style="display:flex;justify-content:space-between;align-items:center;padding:8px;border-bottom:1px solid #eee;">
        <div style="flex:1;"><strong>{name}</strong> - {info.get("description","")} [{info.get("doc_count",0)} 文档]</div>
        <div style="color:#888;font-size:11px;">模型编辑在下方「自动分类规则」中</div>
      </div>''' for name, info in kbs.items())}
    </div>
    <div style="margin-top:12px;padding-top:12px;border-top:1px solid #eee;">
      <div style="font-size:13px;font-weight:600;color:#555;margin-bottom:6px;">📋 自动分类规则 <span style="font-weight:400;color:#888;font-size:11px;">（关键词 + 扩展名匹配）</span></div>
      <div id="rules-list" style="font-size:13px;color:#888;">加载中...</div>
      <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;">
        <button class="btn btn-secondary" style="padding:6px 14px;font-size:12px;" onclick="refreshRules()">🔄 刷新规则</button>
        <button class="btn btn-primary" style="padding:6px 14px;font-size:12px;" onclick="showRuleEditor()">➕ 添加规则</button>
        <button class="btn btn-danger" style="padding:6px 14px;font-size:12px;" onclick="if(confirm('重置所有分类规则为默认？'))resetRules()">↺ 重置默认</button>
      </div>
    </div>
  </div>

  <!-- 规则编辑弹窗 -->
  <div id="rule-editor-overlay" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);z-index:1000;align-items:center;justify-content:center;" onclick="if(event.target===this)hideRuleEditor()">
    <div style="background:white;border-radius:16px;padding:28px;max-width:480px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.2);">
      <h3 id="rule-editor-title" style="font-size:18px;color:#5a3e8a;margin-bottom:16px;">添加分类规则</h3>
      <div class="form-group"><label>知识库名</label><input id="rule-name" type="text" style="width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;"></div>
      <div class="form-group"><label>关键词（逗号分隔）</label><input id="rule-keywords" type="text" style="width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;" placeholder="例: 代码,API,编程"></div>
      <div class="form-group"><label>扩展名（逗号分隔）</label><input id="rule-extensions" type="text" style="width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;" placeholder="例: .py,.js,.ts"></div>
      <div class="form-group"><label>描述</label><input id="rule-desc" type="text" style="width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;" placeholder="可选"></div>
      <div class="form-group"><label>知识库嵌入模型</label>
        <select id="rule-model" style="width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;">
          <option value="">— 默认模型 ({models[0].get("model_id","") if models else "无"}) —</option>
          {''.join(f'<option value="{m.get("model_id","")}">[嵌入] {m.get("model_id","")}</option>' for m in models)}
        </select>
        <div style="font-size:11px;color:#888;margin-top:4px;">选空=回退到全局默认模型。已有文档的知识库切换模型后需重新导入。</div>
      </div>
      <div style="display:flex;gap:10px;margin-top:16px;justify-content:flex-end;">
        <button class="btn btn-secondary" onclick="hideRuleEditor()">取消</button>
        <button class="btn btn-primary" onclick="saveRule()">💾 保存</button>
      </div>
    </div>
  </div>

  <!-- 路由层 -->
  <div class="card">
    <h2>🌐 路由层 <span style="font-weight:400;color:#888;font-size:12px;">— 硬编码(来自KB规则)→语义回退→全量广播</span></h2>
    <div class="form-row">
      <div class="form-group">
        <label>启用路由 <span style="font-weight:400;color:#888;font-size:11px;">（KB路由关闭时自动禁用）</span></label>
        <label class="toggle-switch" onclick="toggleRouter()">
          <input type="checkbox" onclick="event.stopPropagation();" {"checked" if router_cfg.get("enabled", True) else ""}><span class="toggle-slider"></span>
        </label>
      </div>
      <div class="form-group">
        <label>最低得分阈值</label>
        <input type="number" value="{fb_cfg.get('min_score_threshold', 0.3)}" min="0" max="1" step="0.05" onchange="updateConfig('router','fallback_threshold',parseFloat(this.value))">
      </div>
      <div class="form-group">
        <label>语义分类阈值</label>
        <input type="number" value="{router_cfg.get('classify_threshold', 0.3)}" min="0" max="1" step="0.05" onchange="updateConfig('router','classify_threshold',parseFloat(this.value))">
        <span style="color:#888;font-size:11px;margin-left:4px;">（入库/出库时 reranker 关键词锚点匹配）</span>
      </div>
    </div>
    <div style="margin-top:12px;">
      <div style="font-size:13px;font-weight:600;color:#555;margin-bottom:6px;">回退语义路由模型 <span style="font-weight:400;color:#888;font-size:11px;">（每个模型独立下载，选中即生效）</span></div>
      <div style="max-height:200px;width:100%;overflow-y:auto;border:1px solid #eee;border-radius:6px;padding:8px;">
        {fb_model_html}
      </div>
    </div>
    <div class="collapsible" onclick="toggleAdvSig()" style="margin-top:8px;">
      <span>📋 KB 签名（入库时自动归纳）</span>
      <span id="adv-sig-arrow">▶</span>
    </div>
    <div class="collapsible-content" id="adv-sig-content">
      <div style="font-size:12px;color:#888;">
        {"".join(f'<div style="padding:4px 0;border-bottom:1px solid #eee;"><strong>{name}</strong>: <span style="color:#aaa;">{(info.get("signature","") if isinstance(info, dict) else info)[:80]}...</span></div>' for name, info in kb_sigs.items()) if kb_sigs else '暂无签名'}
      </div>
      <button class="btn btn-secondary" style="padding:6px 14px;font-size:12px;margin-top:8px;" onclick="rebuildSigs()">🔄 重建所有签名</button>
    </div>
  </div>

  <!-- Rerank 层 -->
  <div class="card">
    <h2>🔀 Rerank 层 <span style="font-weight:400;color:#888;font-size:12px;">— 检索完成后对结果重排序（默认关闭）</span></h2>
    <div class="form-row">
      <div class="form-group">
        <label>启用 Rerank</label>
        <label class="toggle-switch" onclick="toggleReranker()">
          <input type="checkbox" onclick="event.stopPropagation();" {"checked" if rerank_cfg.get("enabled", False) else ""}><span class="toggle-slider"></span>
        </label>
      </div>
      <div class="form-group">
        <label>模式</label>
        <select onchange="updateConfig('reranker','mode',this.value)">
          <option value="model" {"selected" if rerank_cfg.get("mode","model")=="model" else ""}>模型排序</option>
          <option value="rule" {"selected" if rerank_cfg.get("mode")=="rule" else ""}>规则排序</option>
          <option value="hybrid" {"selected" if rerank_cfg.get("mode")=="hybrid" else ""}>混合（模型+规则）</option>
        </select>
      </div>
      <div class="form-group">
        <label>输出数量</label>
        <input type="number" min="1" max="50" value="{rerank_cfg.get("top_k", 5)}"
               onchange="updateConfig('reranker','top_k',parseInt(this.value)||5)"
               style="width:70px;padding:6px 10px;border:1px solid #ddd;border-radius:4px;font-size:13px;">
        <span style="color:#888;font-size:11px;margin-left:4px;">（精排后取前 N 条）</span>
      </div>
    </div>
    <div style="margin-top:12px;">
      <div style="font-size:13px;font-weight:600;color:#555;margin-bottom:6px;">Rerank 模型</div>
      <div style="max-height:200px;width:100%;overflow-y:auto;border:1px solid #eee;border-radius:6px;padding:8px;">
        {rr_model_html}
      </div>
    </div>
    <div class="collapsible" onclick="toggleSortRules()" style="margin-top:8px;">
      <span>📏 排序规则 <span style="font-weight:400;color:#888;font-size:11px;">（规则/混合模式下生效）</span></span>
      <span id="adv-rules-arrow">▶</span>
    </div>
    <div class="collapsible-content" id="adv-rules-content">
      <div id="sort-rules-list" style="font-size:13px;color:#888;">加载中...</div>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <button class="btn btn-secondary" style="padding:6px 14px;font-size:12px;" onclick="refreshSortRules()">🔄 刷新</button>
        <button class="btn btn-secondary" style="padding:6px 14px;font-size:12px;" onclick="addSortRule()">➕ 添加规则</button>
      </div>
    </div>
  </div>

  <!-- 排序规则编辑器弹窗 -->
  <div id="sort-rule-editor-overlay" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);z-index:1000;align-items:center;justify-content:center;" onclick="if(event.target===this)hideSortRuleEditor()">
    <div style="background:white;border-radius:16px;padding:28px;max-width:480px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.2);">
      <h3 id="sort-rule-editor-title" style="font-size:18px;color:#5a3e8a;margin-bottom:16px;">添加排序规则</h3>
      <div class="form-group"><label>规则类型</label>
        <select id="sort-rule-type" style="width:100%;padding:8px 10px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;" onchange="onSortRuleTypeChange()">
          <option value="">-- 请选择 --</option>
          <option value="score_weight">score_weight — 分数加权</option>
          <option value="recency">recency — 时间衰减</option>
          <option value="source_weight">source_weight — 来源加权</option>
          <option value="boost_keywords">boost_keywords — 关键词提升</option>
        </select>
      </div>
      <div id="sort-rule-params" style="display:none;">
        <div id="sort-rule-params-fields"></div>
      </div>
      <div style="display:flex;gap:10px;margin-top:16px;justify-content:flex-end;">
        <button class="btn btn-secondary" onclick="hideSortRuleEditor()">取消</button>
        <button class="btn btn-primary" onclick="saveSortRule()">💾 保存</button>
      </div>
    </div>
  </div>

  <!-- 极客模式：JSON 全量编辑器（分块折叠 + 编辑开关 + 模板管理） -->
  <div class="card" style="margin-bottom: 12px;">
    <h2>⚡ 极客模式 <span style="font-weight:400;color:#888;font-size:12px;">— JSON 全量编辑/保存/覆盖</span></h2>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;flex-wrap:wrap;">
      <label style="font-size:13px;color:#555;display:flex;align-items:center;gap:6px;cursor:pointer;">
        <input type="checkbox" id="geek-edit-toggle" onchange="toggleGeekEdit(this.checked)" {"checked" if geek_edit_enabled else ""}>
        启用编辑
      </label>
      <span style="font-size:12px;color:#888;" id="geek-edit-hint">编辑模式下可修改 JSON</span>
      <input type="text" id="geek-template-name" placeholder="模板名称" style="flex:1;min-width:120px;padding:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:13px;">
    </div>
    <details open id="geek-section-prompt" style="margin-bottom:6px;">
      <summary style="cursor:pointer;font-weight:600;font-size:13px;color:#555;padding:3px 0;">📝 Prompt 模板</summary>
      <textarea id="geek-editor-prompt" rows="3" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;font-family:'Courier New',monospace;font-size:12px;margin-top:4px;resize:vertical;box-sizing:border-box;">{config_prompt_json}</textarea>
    </details>
    <details id="geek-section-embedding" style="margin-bottom:6px;">
      <summary style="cursor:pointer;font-weight:600;font-size:13px;color:#555;padding:3px 0;">📦 嵌入模型 & 检索</summary>
      <textarea id="geek-editor-embedding" rows="5" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;font-family:'Courier New',monospace;font-size:12px;margin-top:4px;resize:vertical;box-sizing:border-box;">{config_embedding_json}</textarea>
    </details>
    <details id="geek-section-splitter" style="margin-bottom:6px;">
      <summary style="cursor:pointer;font-weight:600;font-size:13px;color:#555;padding:3px 0;">✂️ 切片策略</summary>
      <textarea id="geek-editor-splitter" rows="5" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;font-family:'Courier New',monospace;font-size:12px;margin-top:4px;resize:vertical;box-sizing:border-box;">{config_splitter_json}</textarea>
    </details>
    <details id="geek-section-router" style="margin-bottom:6px;">
      <summary style="cursor:pointer;font-weight:600;font-size:13px;color:#555;padding:3px 0;">🔀 路由 & Guard & 重排序</summary>
      <textarea id="geek-editor-router" rows="5" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;font-family:'Courier New',monospace;font-size:12px;margin-top:4px;resize:vertical;box-sizing:border-box;">{config_router_json}</textarea>
    </details>
    <details id="geek-section-other" style="margin-bottom:6px;">
      <summary style="cursor:pointer;font-weight:600;font-size:13px;color:#555;padding:3px 0;">⚙️ 其他（模式/输入源/预处理）</summary>
      <textarea id="geek-editor-other" rows="5" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;font-family:'Courier New',monospace;font-size:12px;margin-top:4px;resize:vertical;box-sizing:border-box;">{config_other_json}</textarea>
    </details>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;align-items:center;">
      <button class="btn btn-secondary" id="geek-btn-apply" onclick="applyGeekConfig()">💾 应用全部</button>
      <button class="btn btn-secondary" id="geek-btn-new" onclick="newGeekTemplate()">📄 新建</button>
      <button class="btn btn-secondary" id="geek-btn-save" onclick="saveGeekTemplate()">💿 保存</button>
      <button class="btn btn-secondary" id="geek-btn-overwrite" onclick="overwriteGeekTemplate()">📝 覆盖</button>
      <button class="btn btn-success" id="geek-btn-refresh" onclick="refreshGeekTemplates()">🔄 刷新模板</button>
      <span id="geek-status" style="font-size:13px;color:#888;margin-left:4px;"></span>
    </div>
    <div id="template-list" style="margin-top:10px;padding-top:10px;border-top:1px solid #eee;">
      <div style="font-size:13px;font-weight:600;color:#555;margin-bottom:6px;">已保存模板</div>
      <div id="template-items" style="font-size:13px;color:#888;">加载中...</div>
    </div>
  </div>

  <div class="card" style="display:flex;gap:12px;flex-wrap:wrap;">
    <button class="btn btn-danger" onclick="if(confirm('\u786e\u5b9a\u91cd\u7f6e\u6240\u6709\u914d\u7f6e\uff1f'))resetAll()">&#x1f5d1;&#xfe0f; \u91cd\u7f6e\u914d\u7f6e</button>
    <button class="btn btn-success" onclick="window.location.reload()">&#x1f504; \u5237\u65b0</button>
  </div>
</div>


<!-- 自定义模态框 HTML -->
<div id="modal-overlay" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.35);z-index:9999;align-items:center;justify-content:center;">
  <div style="background:#fff;border-radius:12px;padding:24px 28px;min-width:360px;max-width:480px;box-shadow:0 8px 30px rgba(0,0,0,0.2);">
    <div id="modal-title" style="font-size:15px;font-weight:500;margin-bottom:14px;">输入</div>
    <input id="modal-input" type="text" style="width:100%;padding:8px 12px;border:1.5px solid #ddd;border-radius:6px;font-size:14px;box-sizing:border-box;display:none;" placeholder="">
    <div id="modal-msg" style="font-size:14px;color:#555;line-height:1.5;display:none;"></div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:16px;">
      <button class="btn btn-secondary" onclick="closeModal()">取消</button>
      <button class="btn btn-success" onclick="confirmModal()">确定</button>
    </div>
  </div>
</div>
</body>
</html>
"""
    html_out += _JS_SCRIPTS
    return html_out


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
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
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
                if section == "router":
                    rt = cfg.setdefault("router", {}); fb = rt.setdefault("fallback", {})
                    if key == "model_path_fallback": fb["model_path"] = value
                    elif key == "fallback_threshold": fb["min_score_threshold"] = value
                    else: rt[key] = value
                elif section == "reranker":
                    cfg.setdefault("reranker", {})[key] = value
                else:
                    if section not in cfg: cfg[section] = {}
                    cfg[section][key] = value
                save_config(cfg)
                self._send_json({"success": True})

            elif path == "/api/preprocess/toggle":
                data = self._read_body()
                cfg = load_config()
                cfg.setdefault("preprocess", {})["enabled"] = data.get("enabled", False)
                save_config(cfg)
                self._send_json({"success": True})

            elif path == "/api/preprocess/save":
                data = self._read_body()
                cfg = load_config()
                cfg["preprocess"] = {
                    "enabled": data.get("enabled", False),
                    "h1_patterns": data.get("h1_patterns", []),
                    "h2_patterns": data.get("h2_patterns", []),
                    "h3_patterns": data.get("h3_patterns", []),
                    "h4_patterns": data.get("h4_patterns", []),
                }
                save_config(cfg)
                self._send_json({"success": True})

            elif path == "/api/mode":
                data = self._read_body()
                mode = data.get("mode")
                if mode not in ("integrated", "standalone"):
                    self._send_json({"success": False, "error": "无效模式，可选: integrated, standalone"})
                    return
                cfg = load_config()
                cfg["mode"] = mode
                save_config(cfg)
                self._send_json({"success": True, "mode": mode})

            elif path == "/api/override":
                data = self._read_body()
                strategy = data.get("strategy")
                key = data.get("key")
                value = data.get("value")
                cfg = load_config()
                if "splitting" not in cfg:
                    cfg["splitting"] = {}
                if "strategy_overrides" not in cfg["splitting"]:
                    cfg["splitting"]["strategy_overrides"] = {}
                if strategy not in cfg["splitting"]["strategy_overrides"]:
                    cfg["splitting"]["strategy_overrides"][strategy] = {}
                cfg["splitting"]["strategy_overrides"][strategy][key] = value
                save_config(cfg)
                self._send_json({"success": True})

            elif path == "/api/input-source":
                data = self._read_body()
                key = data.get("key", "")
                if key not in ("enable_pdf", "enable_ocr", "enable_html2md"):
                    self._send_json({"success": False, "error": f"未知输入源: {key}"})
                    return
                cfg = load_config()
                if "input_sources" not in cfg:
                    cfg["input_sources"] = {}
                new_state = not cfg["input_sources"].get(key, False)

                # 开启时自动检测并安装依赖
                if new_state:
                    _DEP_MAP = {
                        "enable_pdf": {"modules": ["pypdf", "pdfplumber"], "pip": "pypdf"},
                        "enable_ocr": {"modules": ["paddleocr", "easyocr"], "pip": ["paddleocr", "easyocr"]},
                        "enable_html2md": {"modules": ["html2text"], "pip": "html2text"},
                    }
                    info = _DEP_MAP[key]
                    found = False
                    pip_targets = info["pip"]
                    if not isinstance(pip_targets, list):
                        pip_targets = [pip_targets]
                    for mod in info["modules"]:
                        try:
                            __import__(mod)
                            found = True
                            break
                        except ImportError:
                            continue
                    if not found:
                        for pip_pkg in pip_targets:
                            print(f"  依赖未安装，自动安装 {pip_pkg}...")
                            py = sys.executable
                            r = run_command([py, "-m", "pip", "install", pip_pkg, "-q"], timeout=120)
                            if r["success"]:
                                print(f"  [OK] {pip_pkg} 安装成功")
                                found = True
                                break
                            print(f"  [!] {pip_pkg} 安装失败，尝试下一候选")
                        if not found:
                            self._send_json({"success": False, "error": f"所有候选依赖均安装失败", "dep": "missing"})
                            return

                dep_status = _check_dep(key)
                cfg["input_sources"][key] = new_state
                save_config(cfg)
                self._send_json({"success": True, "active": new_state, "dep": dep_status})

            elif path == "/api/dep-check":
                dep_status = {k: _check_dep(k) for k in ("enable_pdf", "enable_ocr", "enable_html2md")}
                self._send_json({"success": True, "status": dep_status})

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

            elif path == "/api/guard/toggle":
                data = self._read_body()
                name = data.get("name", "")
                if name not in ("mermaid", "code", "math", "table", "html"):
                    self._send_json({"success": False, "error": f"未知守卫: {name}"})
                    return
                cfg = load_config()
                guards = cfg.get("splitting", {}).get("guards", ["code"])
                if name in guards:
                    guards = [g for g in guards if g != name]
                    active = False
                else:
                    guards = list(guards) + [name]
                    active = True
                if "splitting" not in cfg:
                    cfg["splitting"] = {}
                cfg["splitting"]["guards"] = guards
                save_config(cfg)
                self._send_json({"success": True, "active": active})

            elif path == "/api/mode-check":
                cfg = load_config()
                self._send_json({"mode": cfg.get("mode", "integrated")})

            elif path == "/api/config/raw":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                try:
                    new_cfg = json.loads(body)
                except json.JSONDecodeError:
                    self._send_json({"success": False, "error": "JSON 格式错误"})
                    return
                if save_config(new_cfg):
                    self._send_json({"success": True})
                else:
                    self._send_json({"success": False, "error": "写入失败"})

            elif path == "/api/template/list":
                self._send_json({"success": True, "templates": list_templates()})

            elif path == "/api/template/save":
                data = self._read_body()
                name = data.get("name", "").strip()
                if not name:
                    self._send_json({"success": False, "error": "模板名不能为空"})
                    return
                label = data.get("label", name)
                config = data.get("config", {})
                save_template_config(name, label, config)
                self._send_json({"success": True})

            elif path == "/api/template/load":
                data = self._read_body()
                name = data.get("name", "")
                tpl = load_template_config(name)
                if tpl is None:
                    self._send_json({"success": False, "error": "模板不存在"})
                    return
                # 合并到当前配置
                cfg = load_config()
                for k, v in tpl.items():
                    if isinstance(v, dict) and k in cfg and isinstance(cfg[k], dict):
                        cfg[k].update(v)
                    else:
                        cfg[k] = v
                save_config(cfg)
                self._send_json({"success": True})

            elif path == "/api/template/delete":
                data = self._read_body()
                name = data.get("name", "")
                ok = delete_template_config(name)
                self._send_json({"success": ok})

            # 知识库分类规则 API
            elif path == "/api/rules/list":
                from knowledge_base_manager import _load_rules
                self._send_json({"success": True, "rules": _load_rules()})

            elif path == "/api/rules/delete":
                data = self._read_body()
                name = data.get("name", "")
                from knowledge_base_manager import remove_classify_rule
                ok, msg = remove_classify_rule(name)
                self._send_json({"success": ok, "message": msg})

            elif path == "/api/rules/save":
                data = self._read_body()
                name = data.get("name", "").strip()
                if not name:
                    self._send_json({"success": False, "error": "知识库名不能为空"})
                    return
                from knowledge_base_manager import set_classify_rule
                ok, msg = set_classify_rule(
                    name,
                    keywords=data.get("keywords", []),
                    extensions=data.get("extensions", []),
                    description=data.get("description", ""),
                )
                self._send_json({"success": ok, "message": msg})

            elif path == "/api/rules/reset":
                from knowledge_base_manager import reset_classify_rules
                ok, msg = reset_classify_rules()
                self._send_json({"success": ok, "message": msg})

            elif path == "/api/kb-model":
                data = self._read_body()
                kb_name = data.get("kb_name", "")
                model_id = data.get("model_id", "")
                if not kb_name:
                    self._send_json({"success": False, "error": "知识库名不能为空"})
                    return
                from knowledge_base_manager import set_kb_model, create_knowledge_base
                # 如果知识库不存在，自动创建（规则编辑器中保存模型时触发）
                from knowledge_base_manager import list_knowledge_bases
                if kb_name not in list_knowledge_bases():
                    c_ok, c_msg = create_knowledge_base(kb_name)
                    if not c_ok and "已存在" not in c_msg:
                        self._send_json({"success": False, "error": f"自动创建知识库失败: {c_msg}"})
                        return
                ok, msg = set_kb_model(kb_name, model_id)
                self._send_json({"success": ok, "message": msg})

            elif path == "/api/kb-models":
                """返回所有知识库的模型配置 + 下载的嵌入模型列表"""
                from knowledge_base_manager import list_knowledge_bases, get_kb_model
                from embedding_model_manager import list_downloaded_models, RECOMMENDED_RERANK_MODELS
                kbs = list_knowledge_bases()
                kb_models = {name: get_kb_model(name) for name in kbs}
                all_models = list_downloaded_models()
                reranker_ids = {m["id"].lower() for m in RECOMMENDED_RERANK_MODELS}
                models = [m for m in all_models if m.get("model_id","").lower() not in reranker_ids]
                self._send_json({"success": True, "kb_models": kb_models, "models": models})

            elif path == "/api/recommend":
                data = self._read_body()
                cfg = load_config()
                if "description" in data:
                    # LLM 模式：构造 prompt 调用外部 LLM
                    desc = data["description"]
                    try:
                        from langchain_community.llms import OpenAI
                        llm = OpenAI(
                            base_url=cfg.get("llm", {}).get("base_url", "http://localhost:1234/v1"),
                            api_key="not-needed",
                            temperature=0.1,
                            max_tokens=256,
                        )
                        prompt = f"""根据以下用户描述，推荐 RAG 切片配置。

用户描述：{desc}

可选策略：fixed(固定窗口), recursive(递归切分), headers(层级/标题切), sentence(按句切), semantic(语义切)
可选守卫：mermaid, code, math, table, html
可选后处理：recursive(递归子切), fixed(固定窗口子切), semantic(语义子切)

请返回 JSON 格式推荐，包含 strategy, guards(数组), secondary(或null), chunk_size(或null)：
"""
                        raw = llm.invoke(prompt).strip()
                        # 提取 JSON
                        import re as _re
                        json_match = _re.search(r'\{.*\}', raw, _re.DOTALL)
                        if json_match:
                            rec = json.loads(json_match.group(0))
                        else:
                            rec = {"strategy": "recursive", "guards": ["code"], "secondary": None, "chunk_size": 500}
                    except Exception:
                        rec = {"strategy": "recursive", "guards": ["code"], "secondary": None, "chunk_size": 500}

                    if "splitting" not in cfg:
                        cfg["splitting"] = {}
                    cfg["splitting"]["strategy"] = rec.get("strategy", "recursive")
                    cfg["splitting"]["guards"] = rec.get("guards", ["code"])
                    cfg["splitting"]["secondary_strategy"] = rec.get("secondary")
                    if rec.get("chunk_size"):
                        cfg["splitting"]["chunk_size"] = rec["chunk_size"]
                    save_config(cfg)
                    self._send_json({"success": True})

                elif "preset" in data:
                    # 预设模式
                    p = data["preset"]
                    if "splitting" not in cfg:
                        cfg["splitting"] = {}
                    cfg["splitting"]["strategy"] = p.get("strategy", "recursive")
                    cfg["splitting"]["guards"] = p.get("guards", ["code"])
                    cfg["splitting"]["secondary_strategy"] = p.get("secondary")
                    if p.get("cs"):
                        cfg["splitting"]["chunk_size"] = p["cs"]
                    save_config(cfg)
                    self._send_json({"success": True})
                else:
                    self._send_json({"success": False, "error": "缺少 description 或 preset 参数"})

            elif path == "/api/reset":
                reset_config()
                reset_template()
                self._send_json({"success": True})

            elif path == "/api/kb/toggle":
                cfg = load_config(); kb = cfg.setdefault("kb", {}); kb["enabled"] = not kb.get("enabled", True)
                save_config(cfg); self._send_json({"success": True, "enabled": kb["enabled"]})
            elif path == "/api/download-model":
                d = self._read_body(); mid = d.get("model_id","")
                if not mid:
                    self._send_json({"success": False, "error": "empty"})
                    return
                # 启动后台线程下载
                def _dl_thread(mid):
                    def _run():
                        from embedding_model_manager import DOWNLOAD_SOURCES, download_model
                        from utils import cache_directory
                        try:
                            _download_tasks[mid] = {"status": "starting", "source": "准备中", "attempt": 0, "message": "", "size_mb": 0, "speed": ""}
                            # 搜集有效源
                            sources = [s["name"] for s in DOWNLOAD_SOURCES[:4] if s["name"] != "llm_find"]
                            _download_tasks[mid]["status"] = "downloading"
                            _download_tasks[mid]["source"] = sources[0] if sources else "?"
                            _download_tasks[mid]["message"] = f"正在从 {sources[0] if sources else '?'} 下载..."

                            # 启动下载子线程
                            dl_ok = [False]
                            def _do_dl():
                                try:
                                    r = download_model(mid, sources=sources)
                                    dl_ok[0] = r.get("success", False)
                                except Exception as e:
                                    _download_tasks[mid]["message"] = str(e)
                                if not dl_ok[0]:
                                    _download_tasks[mid]["status"] = "failed"
                                    _download_tasks[mid]["message"] = "所有源均失败"
                            t = threading.Thread(target=_do_dl, daemon=True)
                            t.start()

                            # 监控进度 — 扫描 model_downloads 下该模型的所有缓存文件
                            last_size = 0
                            # HuggingFace 格式: models--BAAI--bge-m3
                            hf_prefix = f"models--{mid.replace('/', '--')}"
                            # ModelScope 格式: BAAI/bge-m3（直接在 cache_dir 下创建 org/name 目录）
                            ms_prefix = mid.replace("/", os.sep)
                            while t.is_alive():
                                time.sleep(5)
                                cur_size = 0
                                dl_dir = os.path.join(cache_directory, "model_downloads")
                                if os.path.isdir(dl_dir):
                                    for root, _, fns in os.walk(dl_dir):
                                        # 同时匹配 HF 和 ModelScope 两种缓存目录格式
                                        if hf_prefix not in root and ms_prefix not in root:
                                            continue
                                        for fn in fns:
                                            if fn.endswith('.incomplete') or fn.endswith('.lock'):
                                                continue
                                            fp = os.path.join(root, fn)
                                            try:
                                                if os.path.isfile(fp):
                                                    cur_size += os.path.getsize(fp)
                                            except:
                                                pass
                                size_mb = cur_size / (1024*1024)
                                spd = (cur_size - last_size) / 5
                                if spd >= 1024*1024:
                                    spd_str = f"{spd/1024/1024:.1f} MB/s"
                                elif spd >= 1024:
                                    spd_str = f"{spd/1024:.0f} KB/s"
                                else:
                                    spd_str = f"{spd:.0f} B/s"
                                _download_tasks[mid].update({
                                    "size_mb": round(size_mb, 1),
                                    "speed": spd_str,
                                })
                                last_size = cur_size

                            # 下载完成
                            if dl_ok[0]:
                                _download_tasks[mid] = {"status": "done", "source": "", "attempt": 0,
                                                        "message": "下载完成", "size_mb": _download_tasks[mid].get("size_mb", 0), "speed": ""}
                            elif _download_tasks[mid]["status"] != "failed":
                                _download_tasks[mid] = {"status": "failed", "source": "", "attempt": 0,
                                                        "message": "下载失败", "size_mb": _download_tasks[mid].get("size_mb", 0), "speed": ""}
                        except Exception as e:
                            _download_tasks[mid] = {"status": "failed", "source": "", "attempt": 0,
                                                    "message": str(e), "size_mb": 0, "speed": ""}
                    t = threading.Thread(target=_run, daemon=True)
                    t.start()
                _dl_thread(mid)
                self._send_json({"success": True, "message": "下载已启动"})

            elif path == "/api/download-status":
                d = self._read_body(); mid = d.get("model_id","")
                if mid in _download_tasks:
                    t = _download_tasks[mid]
                    self._send_json({"success": True, "status": t.get("status",""),
                                     "source": t.get("source",""),
                                     "attempt": t.get("attempt",0),
                                     "message": t.get("message",""),
                                     "size_mb": t.get("size_mb",0),
                                     "speed": t.get("speed","")})
                else:
                    self._send_json({"success": False, "status": "unknown"})
            elif path == "/api/geekedit/toggle":
                d = self._read_body()
                on = d.get("enabled", False)
                cfg = load_config()
                cfg.setdefault("geek_mode", {})["edit_enabled"] = on
                save_config(cfg)
                self._send_json({"success": True})
            elif path == "/api/router/toggle":
                cfg = load_config(); rc = cfg.setdefault("router", {}); rc["enabled"] = not rc.get("enabled", True)
                save_config(cfg); self._send_json({"success": True, "enabled": rc["enabled"]})
            elif path == "/api/router/rebuild-signatures":
                try: rebuild_all_signatures(); self._send_json({"success": True})
                except Exception as e: self._send_json({"success": False, "error": str(e)})
            elif path == "/api/reranker/toggle":
                cfg = load_config(); rr = cfg.setdefault("reranker", {})
                new_enabled = not rr.get("enabled", False)
                rr["enabled"] = new_enabled
                # 联动：开启 rerank 时检索更多候选（K=20），关闭时恢复 K=3
                ret = cfg.setdefault("retrieval", {})
                if new_enabled:
                    ret["k"] = 20
                else:
                    ret["k"] = 3
                save_config(cfg); self._send_json({"success": True, "enabled": new_enabled})
            elif path == "/api/reranker/rules":
                cfg = load_config(); rules = cfg.get("reranker", {}).get("sort_rules", [])
                self._send_json({"success": True, "rules": rules})
            elif path == "/api/reranker/rules/add":
                d = self._read_body(); rule = d.get("rule", {})
                if rule: cfg = load_config(); rr = cfg.setdefault("reranker", {}); rr.setdefault("sort_rules", []).append(rule); save_config(cfg)
                self._send_json({"success": True})
            elif path == "/api/reranker/rules/delete":
                d = self._read_body(); idx = d.get("index", -1)
                cfg = load_config(); rules = cfg.get("reranker", {}).get("sort_rules", [])
                if 0 <= idx < len(rules): rules.pop(idx); save_config(cfg)
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
    with socketserver.ThreadingTCPServer(("", port), handler) as httpd:
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
