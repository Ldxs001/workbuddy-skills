
// 调试：检查 JS 加载
if(window.console) console.log('Orchestrator JS loaded');

var pipelineNodes = [];

// 全局 Toast 通知（无弹窗）
function toast(msg, duration){
  var el = document.getElementById('toast-msg');
  if(!el){
    el = document.createElement('div');
    el.id = 'toast-msg';
    el.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;z-index:9999;opacity:0;transition:opacity .3s';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.style.opacity = '1';
  clearTimeout(el._hide);
  el._hide = setTimeout(function(){ el.style.opacity = '0'; }, duration || 2000);
}

function switchTab(name){
  document.querySelectorAll('.tab-content').forEach(function(e){e.classList.remove('active')});
  var el = document.getElementById('page-'+name);
  if(el) el.classList.add('active');
  document.querySelectorAll('.tab').forEach(function(e){e.classList.remove('active')});
  var tb = document.getElementById('tab-'+name);
  if(tb) tb.classList.add('active');
  if(name==='pipeline'){ loadSkills(); loadSavedPipelines(); }
  if(name==='chat') loadChatPipelines();
}

// 绑定 tab 点击事件（替代 inline onclick）
function bindTabs(){
  var tabs = document.querySelectorAll('[data-tab]');
  for(var i=0; i<tabs.length; i++){
    (function(tab){
      tab.addEventListener('click', function(e){
        var name = tab.getAttribute('data-tab');
        if(name) switchTab(name);
      });
    })(tabs[i]);
  }
}
if(document.readyState === 'loading'){
  document.addEventListener('DOMContentLoaded', bindTabs);
} else {
  bindTabs();
}

// ===== Chat =====
var isStreaming = false;

function sendMessage(){
  if(isStreaming) return;
  var input = document.getElementById('chat-input');
  var msg = input.value.trim();
  if(!msg) return;
  input.value = '';
  addMessage(msg, 'user');
  addMessage('思考中...', 'assistant', 'thinking');
  isStreaming = true;
  document.getElementById('send-btn').disabled = true;
  // 获取 Pipeline 选择 + skill-sub 选项
  var pipeSelect = document.getElementById('chat-pipeline-select');
  var pipelineId = pipeSelect ? pipeSelect.value : '';
  var skillSub = document.getElementById('chat-skillsub') ? document.getElementById('chat-skillsub').checked : false;
  var saveChain = false;
  if(skillSub){
    var radios = document.getElementsByName('skillsub-mode');
    for(var ri=0; ri<radios.length; ri++){
      if(radios[ri].checked && radios[ri].value==='save'){ saveChain = true; break; }
    }
  }
  fetch('/api/chat', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:msg, pipeline_id:pipelineId, skill_sub:skillSub, save_chain:saveChain})
  }).then(function(r){return r.json()}).then(function(d){
    var thinking = document.getElementById('thinking');
    if(thinking) thinking.remove();
    if(d.success){
      if(d.rounds){
        // 多轮次链驱动执行结果
        d.rounds.forEach(function(round){
          var div = document.createElement('div');
          div.className = 'msg assistant';
          var html = '<div style="border-left:3px solid #667eea;padding:8px 12px;margin:4px 0;background:#f8f9fc;border-radius:0 8px 8px 0">';
          html += '<div style="font-weight:500;color:#667eea;font-size:13px;margin-bottom:6px">' + round.title + '</div>';
          if(round.type === 'optimization' && round.steps){
            // 结构化展示优化报告
            html += '<div style="font-size:12px">';
            if(round.cohesion_checks && round.cohesion_checks.length){
              html += '<div style="color:#888;margin:4px 0">黏连点检查:</div>';
              round.cohesion_checks.forEach(function(c){
                var ic = c.compatible ? '✅' : '🔧';
                html += '<div style="padding:2px 0;color:#555">' + ic + ' ' + (c.from||'') + ' → ' + (c.to||'') + ': ' + (c.note||'') + '</div>';
              });
            }
            if(round.milestones && round.milestones.length){
              html += '<div style="color:#888;margin:4px 0">里程碑:</div>';
              round.milestones.forEach(function(m){
                html += '<div style="padding:2px 0;color:#555">🏁 ' + (m.name||'') + '</div>';
              });
            }
            html += '<div style="color:#888;margin:4px 0">步骤:</div>';
            round.steps.forEach(function(s, idx){
              html += '<div style="padding:2px 0;color:#555">' + (idx+1) + '. ' + (s.name||'') + ' (' + (s.skill||'') + ')</div>';
            });
            html += '</div>';
          } else {
            html += '<div style="font-size:13px;color:#333;white-space:pre-wrap">' + (round.content || '') + '</div>';
          }
          html += '</div>';
          div.innerHTML = html;
          document.getElementById('chat-messages').appendChild(div);
        });
        var allMsgs = document.getElementById('chat-messages');
        if(allMsgs.lastChild) allMsgs.lastChild.scrollIntoView({behavior:'smooth', block:'end'});
      } else if(d.chain){
        // 旧格式兼容
        addMessage(d.text, 'assistant', null, d.reasoning);
      } else {
        addMessage(d.text, 'assistant', null, d.reasoning);
      }
    } else {
      addMessage('抱歉，处理出错：'+(d.error||'未知错误'), 'system');
    }
    isStreaming = false;
    document.getElementById('send-btn').disabled = false;
  }).catch(function(e){
    var thinking = document.getElementById('thinking');
    if(thinking) thinking.remove();
    addMessage('网络错误：'+e.message, 'system');
    isStreaming = false;
    document.getElementById('send-btn').disabled = false;
  });
}

function addMessage(text, role, id, reasoning){
  var div = document.createElement('div');
  div.className = 'msg ' + role;
  if(id) div.id = id;
  // Markdown: assistant 消息渲染，其余纯文本
  if(role === 'assistant' && window.marked){
    div.innerHTML = marked.parse(text);
  } else {
    div.textContent = text;
  }
  if(reasoning){
    var toggle = document.createElement('div');
    toggle.className = 'reasoning-toggle';
    toggle.textContent = '推理过程 ▸';
    toggle.onclick = function(){
      var body = div.querySelector('.reasoning-body');
      if(body){
        var hidden = body.style.display === 'block';
        body.style.display = hidden ? 'none' : 'block';
        toggle.textContent = hidden ? '推理过程 ▸' : '推理过程 ▾';
      }
    };
    var body = document.createElement('div');
    body.className = 'reasoning-body';
    if(window.marked){
      body.innerHTML = marked.parse(reasoning);
    } else {
      body.textContent = reasoning;
    }
    body.style.display = 'none';
    div.appendChild(toggle);
    div.appendChild(body);
  }
  var container = document.getElementById('chat-messages');
  container.appendChild(div);
  div.scrollIntoView({behavior:'smooth', block:'end'});
  // 更新记忆状态
  updateMemoryStats();
}

// 记忆状态更新
function updateMemoryStats(){
  var stats = document.getElementById('memory-stats');
  if(!stats) return;
  var msgs = document.querySelectorAll('#chat-messages .msg');
  var count = 0;
  for(var mi=0; mi<msgs.length; mi++){
    var cls = msgs[mi].className;
    if(cls.indexOf('user')>=0 || cls.indexOf('assistant')>=0) count++;
  }
  stats.textContent = '记忆: ' + count + ' 条消息';
}

function resetChat(){
  fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reset:true})});
  document.getElementById('chat-messages').innerHTML = '<div class="msg assistant">对话已重置。你好！有什么可以帮你？</div>';
  updateMemoryStats();
}

// ===== Config =====
function onBackendChange(){
  var be = document.getElementById('cfg-backend').value;
  document.getElementById('cfg-local-group').style.display = (be==='lmstudio'||be==='ollama') ? '' : 'none';
  document.getElementById('cfg-openai-group').style.display = (be==='openai') ? '' : 'none';
  loadModels();
}

function loadModels(){
  var sel = document.getElementById('cfg-model');
  sel.innerHTML = '<option value="">加载中...</option>';
  fetch('/api/llm/models?t='+Date.now()).then(function(r){return r.json()}).then(function(d){
    sel.innerHTML = '<option value="">-- 选择模型 --</option>';
    if(d.models && d.models.length>0)
      d.models.forEach(function(m){var o=document.createElement('option');o.value=m;o.textContent=m;sel.appendChild(o)});
  });
}

function testLLM(){
  document.getElementById('cfg-status').textContent = '测试中...';
  fetch('/api/llm/test').then(function(r){return r.json()}).then(function(d){
    document.getElementById('cfg-status').textContent = d.success ? '连接正常 '+d.msg : '连接失败: '+d.msg;
    document.getElementById('cfg-status').style.color = d.success ? '#27ae60' : '#e74c3c';
  });
}

setTimeout(function(){
  // 初始加载: 配置 + 模型 + 已保存 Pipeline + 记忆状态
  loadConfig();
  loadModels();
  loadChatPipelines();
  updateMemoryStats();
}, 300);

// ===== Pipeline =====
var pipelineTree = [];
var containerTarget = null;

function loadSkills(){
  fetch('/api/skills').then(function(r){return r.json()}).then(function(d){
    var list = document.getElementById('skill-list');
    if(!d.skills || d.skills.length===0){
      list.innerHTML = '<div style="padding:16px;color:#888;font-size:13px">未发现技能</div>';
      return;
    }
    list.innerHTML = '';
    d.skills.forEach(function(s){
      var item = document.createElement('div');
      item.className = 'skill-item';
      item.ondblclick = function(){addPipelineNode(s.name, s.display_name||s.name)};
      item.innerHTML = '<div class="name">'+(s.display_name||s.name)+'</div><div class="desc">'+(s.description||'').substring(0,60)+'</div>';
      list.appendChild(item);
    });
  });
}

// 添加到选中的容器数组引用；无选中则加到根
// 容器选中状态保持，不自动释放（用户手动点击取消）
function addPipelineNode(name, displayName){
  var target = containerTarget || pipelineTree;
  target.push({name:name, display:displayName||name, mode:'seq', children:[], loop_times:3, params:{}});
  renderPipeline();
}

function addGroup(type){
  var label = type === 'par' ? '并行组' : '循环组';
  var node = {name:'', display:label, mode:type, children:[], loop_times:3};
  pipelineTree.push(node);
  renderPipeline();
}

function renderPipeline(){
  var canvas = document.getElementById('pipeline-canvas');
  if(pipelineTree.length===0){
    canvas.innerHTML = '<span style="color:#aaa;font-size:13px">双击左侧技能 或 点+按钮添加容器</span>';
    return;
  }
  canvas.innerHTML = renderNodes(pipelineTree, 0, '');
}

function renderNodes(nodes, depth, parentPath){
  return nodes.map(function(n,i){
    var isContainer = (n.mode==='par' || n.mode==='loop');
    var modeColor = n.mode==='par' ? '#27ae60' : (n.mode==='loop' ? '#e67e22' : '#667eea');
    var selBg = n.mode==='par' ? 'rgba(39,174,96,0.18)' : 'rgba(230,126,34,0.18)';
    var selOutline = n.mode==='par' ? 'rgba(39,174,96,0.4)' : 'rgba(230,126,34,0.4)';
    // BUGFIX: 检查当前节点自身的 children 是否被选中，而非检查父层数组
    var isSelected = isContainer ? (n.children === containerTarget) : false;
    // 路径: 支持嵌套容器选中 (用于 selectContainerByRef)
    var path = parentPath ? parentPath+'-'+i : ''+i;
    
    var extra = '';
    if(n.mode==='loop'){
      extra = ' <span style="font-size:11px;color:#888">x</span> <input type="number" value="'+n.loop_times+'" min="1" max="99" style="width:36px;padding:2px 4px;border:1px solid #ddd;border-radius:4px;font-size:11px" oninput="this._val=this.value" onchange="setLoopTimes('+i+',this.value)" onclick="event.stopPropagation()">';
    }
    
    var childrenHtml = '';
    var groupWarn = '';  // 组校验
    if(isContainer){
      var childCount = (n.children||[]).length;
      if(childCount < 2 && childCount > 0){
        groupWarn = '<div style="margin-left:24px;font-size:11px;color:#e67e22;padding:2px 0">⚠️ 仅 '+childCount+' 个成员，不足 2 个将降级为串行</div>';
      } else if(childCount === 0){
        groupWarn = '<div style="margin-left:24px;font-size:11px;color:#aaa;padding:2px 0">双击左侧技能加入组</div>';
      }
    }
    if(n.children && n.children.length > 0){
      childrenHtml = '<div style="margin-left:24px;margin-top:4px">'+renderNodes(n.children, depth+1, path)+'</div>';
    }
    
    // 容器节点: 点击选中, 再点取消 (使用路径支持嵌套)
    var clickHandler = '';
    if(isContainer){
      clickHandler = ' onclick="selectContainerByRef(\''+path+'\')"';
    }
    // 选中态: 粗实框 + 厚色条 + 深底色 + 外描绘边 + 发光 (暴增视觉差异)
    // 非选中: 灰色虚线 + 半透明 (一眼不活跃)
    var selStyle = isSelected
      ? 'border:3px solid '+modeColor+';border-left:8px solid '+modeColor+';background:'+selBg+';box-shadow:0 0 20px '+modeColor+'77;outline:2px solid '+selOutline
      : 'border:1.5px dashed #bbb;background:#f5f5f5;opacity:0.75';
    
    // 容器节点: 模式切换 + 选中提示
    if(isContainer){
      extra += ' <select style="font-size:11px;padding:2px 4px;border:1px solid #ddd;border-radius:4px" onchange="changeContainerMode('+i+',this.value)" onclick="event.stopPropagation()">'+
        '<option value="par" '+(n.mode==='par'?'selected':'')+'>par</option>'+
        '<option value="loop" '+(n.mode==='loop'?'selected':'')+'>loop</option>'+
        '</select>';
      if(isSelected) extra += ' <span style="display:inline-block;font-size:12px;color:#fff;background:'+modeColor+';padding:3px 12px;border-radius:4px;font-weight:600;letter-spacing:1px">● 接受中 — 双击左侧技能加入</span>';
    }
    
    return '<div style="margin:4px 0">'+
      '<div class="pipeline-node" style="'+selStyle+'" '+clickHandler+' ondblclick="event.stopPropagation();openNodeParams('+i+')" title="双击编辑参数">'+
        '<span style="color:'+modeColor+';font-weight:500;font-size:11px">['+n.mode+']</span> '+
        '<span>'+(n.display||n.name)+'</span>'+
        extra+
        '<span class="remove" onclick="event.stopPropagation();removeNode('+i+')" style="margin-left:8px">x</span>'+
      '</div>'+
      groupWarn+
      childrenHtml+
      '</div>';
  }).join('');
}

// 点击容器: 通过路径遍历找到节点, 存其 children 引用到 containerTarget
function selectContainerByRef(pathStr){
  var parts = pathStr.split('-').map(Number);
  var target = pipelineTree;
  for(var j = 0; j < parts.length; j++){
    target = target[parts[j]];
    if(!target || typeof target === 'number') return;
  }
  // target 现在是节点对象
  if(!target.children) return;
  containerTarget = (containerTarget === target.children) ? null : target.children;
  renderPipeline();
}

function changeContainerMode(idx, mode){
  if(idx >= 0 && idx < pipelineTree.length){
    pipelineTree[idx].mode = mode;
  }
  renderPipeline();
}

function setLoopTimes(idx, val){
  if(idx >= 0 && idx < pipelineTree.length && pipelineTree[idx]){
    pipelineTree[idx].loop_times = parseInt(val) || 3;
  }
}

function removeNode(idx){
  pipelineTree.splice(idx, 1);
  containerTarget = null;
  renderPipeline();
}

function clearPipeline(){
  pipelineTree = [];
  containerTarget = null;
  renderPipeline();
  document.getElementById('pipeline-result').style.display = 'none';
}

// ===== 节点参数编辑 =====
var _editingNodeIdx = -1;

function openNodeParams(idx){
  var n = pipelineTree[idx];
  if(!n) return;
  _editingNodeIdx = idx;
  document.getElementById('node-params-display').value = n.display || n.name || '';
  document.getElementById('node-params-mode').value = n.mode || 'seq';
  var rows = document.getElementById('node-params-rows');
  rows.innerHTML = '';
  var params = n.params || {};
  var keys = Object.keys(params);
  if(keys.length === 0){
    rows.innerHTML = '<div style="font-size:12px;color:#aaa;padding:4px 0">暂无参数，点击下方添加</div>';
  } else {
    keys.forEach(function(k){
      addParamRowUI(k, params[k]);
    });
  }
  document.getElementById('node-params-modal').classList.add('active');
  setTimeout(function(){ document.getElementById('node-params-display').focus(); }, 100);
}

function closeNodeParams(){
  document.getElementById('node-params-modal').classList.remove('active');
  _editingNodeIdx = -1;
}

function addParamRowUI(key, val){
  var rows = document.getElementById('node-params-rows');
  var div = document.createElement('div');
  div.className = 'param-row';
  div.innerHTML = '<input type="text" class="param-key" placeholder="key" value="'+key.replace(/"/g,'&quot;')+'">'+
    '<span class="sep">=</span>'+
    '<input type="text" class="param-val" placeholder="value" value="'+(val||'').replace(/"/g,'&quot;')+'">'+
    '<span class="del" onclick="this.parentNode.remove()">x</span>';
  rows.appendChild(div);
  // 移除"暂无参数"占位
  var placeholder = rows.querySelector('div[style*="color:#aaa"]');
  if(placeholder) placeholder.remove();
}

function addParamRow(){
  addParamRowUI('', '');
}

function saveNodeParams(){
  var n = pipelineTree[_editingNodeIdx];
  if(!n){ closeNodeParams(); return; }
  // 显示名称
  var display = document.getElementById('node-params-display').value.trim();
  if(display) n.display = display;
  // 模式
  n.mode = document.getElementById('node-params-mode').value;
  // 参数
  var rows = document.getElementById('node-params-rows');
  var paramRows = rows.querySelectorAll('.param-row');
  var params = {};
  for(var i=0; i<paramRows.length; i++){
    var k = paramRows[i].querySelector('.param-key').value.trim();
    var v = paramRows[i].querySelector('.param-val').value.trim();
    if(k) params[k] = v;
  }
  n.params = params;
  closeNodeParams();
  renderPipeline();
}

// 拍平树为执行格式，附带组效验
function flattenTree(nodes, warnings){
  if(!warnings) warnings = [];
  var result = [];
  nodes.forEach(function(n, i){
    if(n.mode === 'par' || n.mode === 'loop'){
      var kids = flattenTree(n.children||[], warnings);
      var label = n.mode === 'par' ? '并行组' : '循环组';
      if(kids.length < 2){
        warnings.push('⚠️ ['+label+'] 仅 '+kids.length+' 个成员，降级为串行');
        result = result.concat(kids);  // 降级
      } else {
        if(n.mode === 'loop'){
          result.push({mode:'loop', times:n.loop_times||3, children:kids});
        } else {
          result.push({mode:'par', children:kids});
        }
      }
    } else if(n.name){
      result.push({mode:'seq', name:n.name, display:n.display});
    }
  });
  return result;
}

function savePipeline(){
  // 使用模态框替代 prompt
  document.getElementById('save-modal-name').value = 'pipeline_' + new Date().toISOString().slice(0,10);
  document.getElementById('save-modal').classList.add('active');
  setTimeout(function(){ document.getElementById('save-modal-name').focus(); }, 100);
}

function closeSaveModal(){
  document.getElementById('save-modal').classList.remove('active');
}

function confirmSavePipeline(){
  var name = document.getElementById('save-modal-name').value.trim();
  if(!name){ toast('名称不能为空'); return; }
  closeSaveModal();
  fetch('/api/pipelines', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name:name, nodes:flattenTree(pipelineTree), tree:pipelineTree, action:'save'})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      loadSavedPipelines();
      loadChatPipelines();
    } else {
      toast('保存失败: '+(d.error||'未知错误'));
    }
  });
}

// 加载已保存的 Pipeline 列表 (Pipeline 侧栏)
function loadSavedPipelines(){
  fetch('/api/pipelines').then(function(r){return r.json()}).then(function(d){
    var list = document.getElementById('saved-pipeline-list');
    if(!list) return;
    var pipes = d.pipelines || [];
    if(pipes.length === 0){
      list.innerHTML = '<div class="empty">暂无已保存的 Pipeline</div>';
      return;
    }
    list.innerHTML = pipes.map(function(n){
      return '<div class="saved-item">'+
        '<span class="name" onclick="loadPipeline(\''+n+'\')">'+n+'</span>'+
        '<span class="del" onclick="event.stopPropagation();confirmDelete(\''+n+'\',this)" title="删除">x</span>'+
        '</div>';
    }).join('');
  });
}

// 加载已保存的 Pipeline 列表 (对话下拉框)
function loadChatPipelines(){
  fetch('/api/pipelines').then(function(r){return r.json()}).then(function(d){
    var sel = document.getElementById('chat-pipeline-select');
    if(!sel) return;
    var pipes = d.pipelines || [];
    sel.innerHTML = '<option value="">-- 选择 Pipeline --</option>' +
      pipes.map(function(n){ return '<option value="'+n+'">'+n+'</option>'; }).join('');
  });
}

// 从已保存列表加载 Pipeline 到编辑器
function loadPipeline(name){
  fetch('/api/pipelines/'+encodeURIComponent(name)).then(function(r){return r.json()}).then(function(d){
    if(d.error){ toast('加载失败'); return; }
    // 优先使用 tree 结构，回退到 nodes
    if(d.tree && d.tree.length > 0){
      pipelineTree = d.tree;
    } else if(d.nodes && d.nodes.length > 0){
      // 从扁平 nodes 重建 tree (无嵌套结构则变为串行列表)
      pipelineTree = d.nodes.map(function(node){ return {name:node.name||'', display:node.display||node.name||'', mode:node.mode||'seq', children:[], loop_times:3, params:node.params||{}}; });
    }
    containerTarget = null;
    renderPipeline();
    switchTab('pipeline');
  });
}

// 删除已保存 Pipeline — 二次点击确认（无弹窗）
var _pendingDelete = null;

function confirmDelete(name, el){
  // 如果已有待删除项且不是当前点击 → 重置
  if(_pendingDelete && _pendingDelete !== el){
    _pendingDelete.style.background = '';
    _pendingDelete.style.color = '#e74c3c';
    _pendingDelete.opacity = '0.5';
    _pendingDelete.textContent = 'x';
  }
  // 如果点击的是同一个待删除项 → 执行删除
  if(_pendingDelete === el){
    _pendingDelete = null;
    fetch('/api/pipelines/delete', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:name})
    }).then(function(r){return r.json()}).then(function(d){
      if(d.success){
        loadSavedPipelines();
        loadChatPipelines();
      }
    });
    return;
  }
  // 第一次点击 → 进入待确认状态
  _pendingDelete = el;
  el.style.background = '#e74c3c';
  el.style.color = '#fff';
  el.style.borderRadius = '10px';
  el.style.padding = '2px 6px';
  el.textContent = '确认?';
}

// 点击页面其他地方重置待删除状态
document.addEventListener('click', function(e){
  if(_pendingDelete && !e.target.classList.contains('del')){
    _pendingDelete.style.background = '';
    _pendingDelete.style.color = '#e74c3c';
    _pendingDelete.style.borderRadius = '';
    _pendingDelete.style.padding = '';
    _pendingDelete.textContent = 'x';
    _pendingDelete = null;
  }
});

// skill-sub 切换事件: 勾选时显示保存选项
function onSkillSubToggle(){
  var group = document.getElementById('chat-skillsub-save-group');
  if(!group) return;
  group.style.display = document.getElementById('chat-skillsub').checked ? 'inline' : 'none';
}

// ===== 搜索配置 =====
function onSearchBackendChange(){
  var v = document.getElementById('cfg-search-backend').value;
  document.getElementById('cfg-search-custom-group').style.display = (v==='custom') ? 'block' : 'none';
  document.getElementById('cfg-search-google-group').style.display = (v==='google') ? 'block' : 'none';
  document.getElementById('cfg-search-bing-group').style.display = (v==='bing') ? 'block' : 'none';
}

function addSearchPreset(){
  var input = document.getElementById('cfg-search-preset-input');
  var cmd = input.value.trim();
  if(!cmd) return;
  input.value = '';
  // 从页面获取当前 presets
  var container = document.getElementById('cfg-search-presets');
  var presets = [];
  var tags = container.querySelectorAll('.search-preset-tag');
  for(var ti=0; ti<tags.length; ti++) presets.push(tags[ti].textContent.replace('x','').trim());
  presets.push(cmd);
  renderSearchPresets(presets);
}

function renderSearchPresets(presets){
  var container = document.getElementById('cfg-search-presets');
  if(!container) return;
  container.innerHTML = presets.map(function(c){
    return '<span class="search-preset-tag" style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;background:#eef0ff;color:#667eea;border-radius:12px;font-size:12px">'+
      c+' <span style="cursor:pointer;opacity:.5" onclick="removeSearchPreset(this)">x</span></span>';
  }).join('');
  // 同步到对话栏
  renderChatSearchPresets(presets);
}

function removeSearchPreset(el){
  var tag = el.parentNode;
  var container = tag.parentNode;
  tag.remove();
  var presets = [];
  var tags = container.querySelectorAll('.search-preset-tag');
  for(var ti=0; ti<tags.length; ti++) presets.push(tags[ti].textContent.replace('x','').trim());
  renderChatSearchPresets(presets);
}

// 在对话输入栏显示预设搜索按钮
function renderChatSearchPresets(presets){
  var container = document.getElementById('chat-search-presets');
  if(!container) return;
  if(!presets || presets.length===0){
    container.innerHTML = '';
    return;
  }
  container.innerHTML = '<span style="font-size:11px;color:#888">🔍</span> ' +
    presets.map(function(c){
      return '<span style="cursor:pointer;padding:2px 8px;background:#eef0ff;color:#667eea;border-radius:10px;font-size:11px" onclick="quickSearch(\''+c.replace(/'/g,"\\'")+'\')">'+c+'</span>';
    }).join('');
}

// 点击搜索预设: 填充到输入框并发送
function quickSearch(query){
  var input = document.getElementById('chat-input');
  if(input){
    input.value = '搜索 ' + query;
    input.focus();
    sendMessage();
  }
}

// 扩展 saveConfig: 包含所有搜索配置
function saveConfig(){
  // 收集搜索预设
  var container = document.getElementById('cfg-search-presets');
  var presets = [];
  if(container){
    var tags = container.querySelectorAll('.search-preset-tag');
    for(var ti=0; ti<tags.length; ti++) presets.push(tags[ti].textContent.replace('x','').trim());
  }
  var body = {
    backend: document.getElementById('cfg-backend').value,
    model: document.getElementById('cfg-model').value,
    timeout: document.getElementById('cfg-timeout').value,
    maxtokens: document.getElementById('cfg-maxtokens').value,
    api_key: document.getElementById('cfg-api-key').value,
    base_url: document.getElementById('cfg-base-url').value,
    local_url: document.getElementById('cfg-local-url').value,
    search_backend: document.getElementById('cfg-search-backend').value,
    search_url: document.getElementById('cfg-search-url').value,
    search_key: document.getElementById('cfg-search-key').value,
    search_google_key: document.getElementById('cfg-search-google-key') ? document.getElementById('cfg-search-google-key').value : '',
    search_google_cx: document.getElementById('cfg-search-google-cx') ? document.getElementById('cfg-search-google-cx').value : '',
    search_bing_key: document.getElementById('cfg-search-bing-key') ? document.getElementById('cfg-search-bing-key').value : '',
    search_presets: presets,
    user_prompt: document.getElementById('cfg-user-prompt') ? document.getElementById('cfg-user-prompt').value : '',
    skill_dirs: getSkillDirs()
  };
  var status = document.getElementById('cfg-status');
  if(status) status.textContent = '保存中...';
  fetch('/api/config', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)
  }).then(function(r){return r.json()}).then(function(d){
    if(status) status.textContent = d.success ? '已保存' : '保存失败';
  });
}

// 扩展 loadConfig: 包含所有搜索配置
function loadConfig(){
  fetch('/api/config').then(function(r){return r.json()}).then(function(d){
    if(d.backend){
      document.getElementById('cfg-backend').value = d.backend;
      onBackendChange();
    }
    if(d.model){
      var sel = document.getElementById('cfg-model');
      if(!sel.querySelector('option[value="'+d.model+'"]')){
        var opt = document.createElement('option');
        opt.value = d.model; opt.textContent = d.model;
        sel.appendChild(opt);
      }
      sel.value = d.model;
    }
    if(d.timeout) document.getElementById('cfg-timeout').value = d.timeout;
    if(d.max_tokens) document.getElementById('cfg-maxtokens').value = d.max_tokens;
    if(d.api_key) document.getElementById('cfg-api-key').value = d.api_key;
    if(d.base_url) document.getElementById('cfg-base-url').value = d.base_url;
    if(d.local_url) document.getElementById('cfg-local-url').value = d.local_url;
    // 搜索配置
    if(d.search_backend){
      document.getElementById('cfg-search-backend').value = d.search_backend;
      onSearchBackendChange();
    }
    if(d.search_url) document.getElementById('cfg-search-url').value = d.search_url;
    if(d.search_key) document.getElementById('cfg-search-key').value = d.search_key;
    if(d.search_google_key) document.getElementById('cfg-search-google-key').value = d.search_google_key || '';
    if(d.search_google_cx) document.getElementById('cfg-search-google-cx').value = d.search_google_cx || '';
    if(d.search_bing_key) document.getElementById('cfg-search-bing-key').value = d.search_bing_key || '';
    if(d.search_presets && d.search_presets.length){
      renderSearchPresets(d.search_presets);
    } else {
      renderChatSearchPresets([]);
    }
    // 更新 LLM 信息
    var info = document.getElementById('llm-info');
    if(info) info.textContent = (d.model || '-') + ' / ' + (d.backend || '-');
    // 提示词
    var sysPromptEl = document.getElementById('cfg-system-prompt');
    if(sysPromptEl && d.system_prompt_raw){
      sysPromptEl.value = d.system_prompt_raw;
    }
    var userPromptEl = document.getElementById('cfg-user-prompt');
    if(userPromptEl && d.user_prompt !== undefined){
      userPromptEl.value = d.user_prompt || '';
    }
    // 技能路径
    if(d.skill_dirs && d.skill_dirs.length){
      renderSkillDirs(d.skill_dirs);
    }
  });
}

// ===== 技能路径管理 =====
function getSkillDirs(){
  var container = document.getElementById('cfg-skill-dirs-list');
  if(!container) return [];
  var items = container.querySelectorAll('.skill-dir-item');
  var dirs = [];
  for(var di=0; di<items.length; di++) dirs.push(items[di].textContent.replace('x','').trim());
  return dirs;
}

function renderSkillDirs(dirs){
  var container = document.getElementById('cfg-skill-dirs-list');
  if(!container) return;
  if(!dirs || dirs.length===0){
    container.innerHTML = '<span style="font-size:12px;color:#aaa">使用默认路径（自包含 skills/）</span>';
    return;
  }
  container.innerHTML = dirs.map(function(d){
    return '<div class="skill-dir-item" style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;background:#eef0ff;color:#667eea;border-radius:12px;font-size:12px;margin:2px">'+
      d+' <span style="cursor:pointer;opacity:.5" onclick="removeSkillDir(this)">x</span></div>';
  }).join('');
}

function addSkillDir(){
  var input = document.getElementById('cfg-skill-dir-input');
  var dir = input.value.trim();
  if(!dir) return;
  input.value = '';
  var dirs = getSkillDirs();
  if(dirs.indexOf(dir) >= 0){ toast('路径已存在'); return; }
  dirs.push(dir);
  renderSkillDirs(dirs);
}

function removeSkillDir(el){
  var tag = el.parentNode;
  var container = document.getElementById('cfg-skill-dirs-list');
  tag.remove();
  var dirs = getSkillDirs();
  if(dirs.length === 0) renderSkillDirs([]);
}

function runPipeline(){
  var warnings = [];
  var flat = flattenTree(pipelineTree, warnings);
  if(flat.length===0 && warnings.length===0){toast('请先添加技能');return;}
  document.getElementById('pipeline-output').textContent = '';
  document.getElementById('pipeline-result').style.display = 'block';
  // 先显示效验警告
  var output = warnings.join('\\n') + (warnings.length ? '\\n\\n---\\n' : '');
  output += '运行中...\\n';
  document.getElementById('pipeline-output').textContent = output;
  fetch('/api/pipelines/run', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({nodes:flat, tree:pipelineTree})
  }).then(function(r){return r.json()}).then(function(d){
    var steps = d.steps ? ' ('+d.steps+'步, '+(d.latency_ms||0)+'ms)' : '';
    document.getElementById('pipeline-output').textContent = (warnings.length ? warnings.join('\\n')+'\\n\\n' : '') + (d.output || d.error || '(无输出)') + (steps ? '\\n\\n---\\n' + steps : '');
  });
}
