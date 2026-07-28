# Structured Writer 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本号遵循语义版本控制（`structured_writer/__init__.py` 唯一源）。

---

## [1.1.0b4] - 2026-07-29
### 修复
- **leaf 节 continue 跳过 parts_by_sid**：leaf 路径末尾的 `continue` 使得 `parts_by_sid[sid]` 赋值永远不执行，leaf 节（关键词/摘要/参考文献）有字数记录但内容不进 .md 文件 → 在 `continue` 前补充 parts_by_sid 写入
- **show_label if/else 嵌套导致 LLM 调用错位**：sec_show_label 的 if/else 把 `if s_type == "leaf":`（LLM 调用）包进了 else 分支，导致 show_label=true 的节完全不调 LLM → 将 LLM 调用移出 if/else
- **section["show_label"] 无 fallback**：从模板直读 `section["show_label"]`，LLM 输出的节不包含该字段 → planner _normalize_outline 传播 show_label 到所有 section
- **gen-template 验收逻辑过松**：`result.get("meta") is not None` 通过 `[]`（空数组非 None）→ 改为 `if result.get("meta") or result.get("content")`（truthiness 判断）
- **saveConfig/confirmSaveAs 表格索引错位**：meta 行 querySelectorAll 返回 3 个元素但代码读 inputs[3]；content 行预期 5 个元素实际 4 个（button 非 input/select）
- **planner JSON 示例硬编码用户名**：示例值改为通用占位符

### 新增
- **style_hint 注入**：`_build_context_section_prompt` 加 `style_hint` 参数，将模板 `style` 注入每节 prompt 作为"写作风格要求"
- **学术论文 引用规则**：style + 参考文献 desc 分开放（行为规则在 style，格式规则在 desc），含正文[1][2]标注、RAG 条件引用、引用一致性
- **_normalize_outline 兜底补缺**：对比 content_fields 所有 name 和现有 sections title，缺失的自动补入
- **is_key 自动标记恢复**：planner prompt 加 `is_key: true = 重点节，字数上浮50%`，JSON 示例每个 section 恢复 is_key 字段
- **_normalize_template 校验**：gen-template 后端校验，清理非法类型、补默认值、删多余字段
- **另存为模态框**：替换 `prompt()` 浏览器弹窗

### 变更
- **logical_order 语义修正**：0=先写（存模板），自动=不设（不参与逻辑排序）。UI 四选项一一对应：自动/先写(0)/其次(1)/最后(2)
- **context 传递策略**：leaf 节 `_logical_order=2` 传全文，其他节（含所有子结构）截取 `context_review_length` 字（默认 800，可调，0=不截断）
- **所有章节统一 `##` 级别**：去掉 `_first_leaf_rendered → #` 的 H1 污染
- **学术论文/论文综述 show_label**：摘要/引言/结论打勾显示标题，正文不打勾
- **关键词 desc**：改为"3-5个关键词，以分号分隔，不要成段描述"
- **默认 context_review_length**：800→8000→恢复为 800（子结构只用尾巴），leaf order=2 传全文
- **样式规则**：要求只在 RAG 开启时才引用，RAG 关闭时不标注
### 修复
- topic 注入 meta 导致 auto 标题被覆盖 → 彻底删除两处注入，LLM 自主生成标题
- meta 块 show_label=true 空值整行跳过 → 改为显示标签占位" > 名称："
- ConfigManager.update 对 templates 用合并而非替换 → 改为全量替换，删除后生效

### 新增
- plan_hints 模态框：重新规划时可输入章节/字数要求，留空按默认
- planner 层级规则 + 用户要求优先规则注入 prompt
- 8 个内置模板 logic 字段（写作顺序提示词）

### 变更
- 配置 tab 拆 meta[] + content[] + style + logic 四区，去掉"渲染为"列
### 架构变更
- **模板格式重大重构**：从平面五元组拆分为 meta[] + content[] + style + logic 四部分
  - 元数据（meta）：标识/管理信息，短数据（≤100字），source=user/auto/llm，固定 leaf
  - 内容树（content）：文章主体，长文本（≥200字），source 固定 llm，type=leaf/section
  - 逻辑提示词（logic）：控制 LLM 认知流程顺序，不改变文章最终排列
- **GEN_TEMPLATE_SYSTEM_PROMPT 重写**：明确定义元数据 vs 内容树的严格二分法

### 新增
- 8 个内置模板全部配置逻辑提示词
- 两个表格列描述 + 逻辑/风格提示词说明文字

### 修复
- renderMetaInputs 读旧格式 tmpl.structure → grid 消失
- deleteTemplate 删不掉（ConfigManager.update 浅合并问题）
- batch_auto template 未定义变量
- _handle_plan 未识别新格式 template
- 温度行因 min-width 溢出

### 变更
- 配置 tab 拆元数据 4列表 + 内容树 4列表 + 逻辑 textarea，去掉"渲染为"列
### 新增
- **五元组结构化模板系统**：模板从纯文本提示词升级为 `{name, show_label, desc, source, type}` 五元组结构，一份数据结构同时定义元数据（标题/作者/单位等）和内容树（引言/正文/结论/参考文献等），覆盖日常写作/学术论文/正式公文/新闻报道/技术报告全部类型
- **动态 Planner prompt 生成**：`plan_outline()` 根据五元组按 `source=user/llm/auto` 分类处理，user 字段不碰、llm 字段必生成、auto 字段用户可填留空 LLM 兜底
- **type:leaf 节支持**：无子结构的扁平节（标题/关键词/摘要/参考文献等），渲染跳过 `###` 标题，直接写内容在 `##` 下
- **meta 块输出**：文章全文前插入 `> 名称：值` 元数据块，按 `show_label` 控制前缀显隐
- **结构表格编辑器**：配置 tab 新增五列可编辑表格（名称/显示/字段意义/填写者/子结构类型）+ 纯展示"渲染"列（自动推导字段出现在聊天输入框还是大纲节）
- **字段意义模态框**：点击表格行中的"字段意义"预览文字弹出 modal textarea，支持长文本编辑，表格中显示截断预览
- **LLM 对话生成模板**：配置 tab "从对话生成" 按钮 → 弹窗输入描述 + 可选模板名称 → LLM 自动生成五元组结构 + 风格提示词 → 保存为自定义模板
- **动态 meta 输入框**：根据模板 `source=user/auto` 的字段，在聊天气泡下方按 4 列 grid 动态渲染输入框，值自动传给 Planner
- **模板搜索排序**：下拉框按拼音字母排序，"自定义"永远在最后
- **内置模板元数据字段**：学术论文/正式公文等新模板预置作者/单位/文号/关键词等字段
- **模板选择持久化**：切换模板时自动保存 `selected_template` 到 config.json，重启后恢复
- **ThreadingHTTPServer**：从单线程 `HTTPServer` 升级为多线程，LLM 请求不阻塞其他 API（归档/配置/进度）
- **删除会话双击确认**：归档会话的删除按钮，第一次单击变红显示"确认?"，2.5 秒内再点执行删除，替代 `confirm()` 浏览器弹窗
- **favicon 静默处理**：返回 `204 No Content`，消除控制台 404

### 变更
- `config.json` 模板格式重构：`templates` 从 `{"名": "字符串"}` 升级为 `{"名": {"structure": [五元组], "style": "字符串"}}`
- `planner.py` 接口变更：`plan_outline()` 新增 `template` 和 `user_meta` 参数，旧字符串调用兼容
- `writer.py` 接口变更：`generate_article()` 新增 `template` 参数（用于 meta 渲染），默认 `None` 兼容旧调用
- `web_ui.py` 路由表新增 `/api/gen-template` 和 `/favicon.ico`
- `config_manager.py` 新增旧格式自动迁移 + "自定义"模板硬保护

### 修复
- `const label` 重复声明导致 JS 加载失败 → 删掉重复行
- 从对话生成模板 `max_tokens=4096` 导致 JSON 截断 → 改为 `None`（走配置值）加 3 次重试 + 多级 JSON 容错解析
- `HTTPServer` 单线程阻塞 UI → 替换为 `ThreadingHTTPServer`
- `onTemplateChange()` 未持久化 `selected_template` → 切换时自动保存
- 模板下拉框排序混乱 → 拼音字母排序 + "自定义"永远最后
- 旧纯字符串模板格式迁移 → `config_manager.py` `load()` 自动检测+转换
### 新增
- **每子结构字数可编辑**：章节字数改为子结构字数之和（自动实时求和），子结构字数输入框直接可改；取消勾选的子结构不计入章节字数
- **进度条按过滤后子结构总数计算**：取消勾选的子结构不再计入进度分母
- **RAG 离线时复选框禁用**：8767 未上线时 RAG 复选框 disabled＋title 提示；上线后自动同步 KB 下拉框
- **子结构辅助知识模态框**：每个子结构 "+" 按钮 → 弹窗支持文本输入 + .txt/.md 文件上传（FileReader 前端读取）
- **RAG 与辅助知识 Prompt 分离注入**：`【RAG 参考资料】` 和 `【辅助知识】` 两段独立标注
- **前文回顾字数可配置**：配置页 "写作参数" 新增输入框，`context_review_length` 写入 config.json
- **配置项自动合并**：`config_manager.load()` 深层合并（嵌套 dict 中新 key 自动补上）；`update()` 支持写入新增键
- **LLM 模型自动检测**：`_build_payload` 中 model 为空时自动调 `list_models()` 取第一个已加载模型
- **批量自动撰写**：输入框写入多行（每行一个主题）→ 后端 `/api/batch_auto` 逐篇规划+RAG+生成 → 前端轮询批量进度
- **单篇自动撰写**：输入框旁 "自动撰写" 按钮 → 前端 chain `plan→generate`，全量自动 RAG
- **事实自检系统**：配置页 "事实自检" 开关 → 写作 prompt 末尾内嵌 `【事实待核查】` 标记 → LLM 在同一 response 中自检 → 解析标记收集 → 文章末尾编号列表汇总。**零额外 LLM 调用**
- **无问题时也输出自检段落**：即使所有子结构都返回"无"，文章末尾也输出 `## 建议人工复审` + `未发现需标记的问题`
- **会话归档/恢复/删除**：侧边栏每项 "🗂 归档" 按钮 → `data/archives/sessions/` 折叠区 → "↩ 恢复" + "✕ 删除"（`confirm()` 确认）
- **自动会话限额**：`max_sessions`（默认 20）→ 新建会话超出时自动归档最旧非当前会话
- **停止生成**：聊天区底部 "延时停止"（当前子结构写完停）+ "立即停止"（续写边界停）→ 保留已写内容输出 .md
- **规划器优先遵循用户指令**：约束前加 "优先遵循用户明确指定的结构要求"，`sections 数量` 改为 "如用户未指定"
- **规划/写作模型温度可配置**：配置页新增 "温度" 输入框（0-1，step=0.05），规划默认 0.6、写作默认 0.7，持久化到 config.json
- **LLM 客户端 temperature 参数**：`LLMClient.__init__` 加 `temperature`，`chat`/`chat_detailed`/`_build_payload` 默认值改为 `None`（走 `self.temperature`）
- **模型下拉框始终显示已保存的模型**：`refreshModels` 接受 `savedValue` 参数，配置模型不在 API 返回列表时追加 `xxx（已配置）` option
- **RAG 停止按钮**：配置页新增 "停止 RAG" 按钮 → 后端 `_handle_rag_stop` → `taskkill /F /T` 杀进程树 + `netstat` 查 8767 + 等端口释放 + auto-restart 检测
- **RAG 停止后不再显示"运行中"**：`_ragManuallyStopped` 标记阻止轮询跳回运行中状态，直到用户手动点击"冷启动 RAG"
- **RAG 状态轮询加速**：cache-buster 防缓存，间隔 3s→1.5s，启动后立即查一次

### 变更
- **自检从额外 LLM 调用改为内嵌标记**：删除 `FACT_CHECK_PROMPT` 和独立 `SELF_CHECK_SYSTEM_PROMPT`，改为在写作 prompt 末尾追加 `【事实待核查】` 标注要求，response 里直接解析
- **规划器 `max_tokens` 从配置读**：删除硬编码 4096，改用 `max(4096, llm_client.max_tokens)`
- **写作器/规划器 LLM 客户端统一工厂**：`_create_writer_client()` / `_create_planner_client()` 传 `temperature`
- **Planner/writer temperature 硬编码删除**：`planner.py` `temperature=0.6` → `None`；`writer.py` `temperature=0.7` → `None`（走客户端配置）
- **`status_text` 仅 writing 阶段返回**：`get_progress()` 非 writing 阶段返回空字符串，防止加载旧会话显示脏数据
- **状态文本生成时自动清空**：`_handle_generate` 入口调用 `set_status_text("")`
- **配置页提示文案更新**：改为 "推理模型建议不低于 4096（默认最低值），长文建议 8192 以上"

### 修复
- `planner.py` 硬编码 `max_tokens=4096` 导致推理模型 thinking 吃掉全部 token → JSON 输出为空
- `config_manager.py` `update()` 无法写入新增配置键 → `fact_check_enabled` 等不持久化
- `config_manager.py` `load()` 不合并 DEFAULT_CONFIG 缺失项 → 旧 config.json 没有新字段
- 自检 `max_tokens` 各值（2048/8192/512）导致推理模型 thinking 吃光 → 改为 `None`（走配置的 81920）
- 自检使用独立 system prompt → LLM 混淆角色 → 改为共享 `WRITER_SYSTEM_PROMPT`
- 自检额外 LLM 调用导致额外 token 消耗 → 改为内嵌标记法，零额外调用
- 加载旧会话时 `_status_text` 脏数据被轮询读出并显示
- 章节字数 input 可编辑但子结构字数不变 → 数据不一致
- 子结构取消勾选后章节字数不减 → 重算函数忽略未勾选
- 模型下拉框加载时显示"(请选择)"而非已保存模型 → `refreshModels` 接受 `savedValue` 回退
- RAG 冷启动后无法关闭 → 新增停止按钮 + 后端进程树 kill + 端口释放等待
- RAG 停止后轮询仍跳回"运行中" → `_ragManuallyStopped` 标记保护
- RAG 状态检测被浏览器缓存 → 加 `?_=Date.now()` cache-buster

---

## [0.9.0] - 2026-07-27
### 新增
- **事实自检系统上线**：配置页开关 → 每子结构写后自检 → 文章末尾汇总置信度分级列表
- **停止生成**：延时停止 / 立即停止，保留已写内容

### 变更
- 自检系统 Prompt 统一为 `WRITER_SYSTEM_PROMPT`

---

## [0.8.0] - 2026-07-27
### 新增
- **会话归档/恢复/删除**：侧边栏 UI + `/api/session/archive|restore|delete`
- **自动会话限额**：`max_sessions=20`，超出自动归档最旧非活跃会话
- **批量自动撰写**：后端 `/api/batch_auto` + 前端批量进度轮询
- **单篇自动撰写**：前端 chain 按钮，全量自动 RAG

### 变更
- 写作器/规划器 LLM 客户端工厂抽取，消除重复代码
- 配置项默认值系统：`load()` 合并 DEFAULT_CONFIG

---

## [0.7.0] - 2026-07-27
### 新增
- **子结构字数可编辑**：章节字数改为子结构实时的和
- **RAG 离线禁用** + **辅助知识模态框**（文本/文件上传）
- **前文回顾字数可配置**
- **RAG／辅助知识 Prompt 分离注入**

### 修复
- `_status_text` 脏数据跨会话显示 → 仅 writing 阶段返回
- 配置新增项不持久化 → `update()` 支持写新键
- `planner.py` `max_tokens=4096` 硬编码 → 从配置读 + 保底 4096
- LLM 模型名为空时调 `list_models()` 自动填充
- 自检 `max_tokens=2048` → 512（子结构级）降低推理 thinking 挤压

---

## [0.6.0] - 2026-07-27
### 新增
- **子结构字数输入框** + **章节字数自动求和**
- **RAG 复选框离线 disabled** + **在线同步 KB 下拉**
- **辅助知识模态框**（文本 + .txt/.md 上传）
- **前文回顾字数配置化**

---

## [0.5.0] - 2026-07-26
### 新增
- **会话归档/恢复/删除 UI**
- **自动清理旧会话**（max_sessions 限制）
- **大纲过滤同步进度**：取消勾选的子结构不计入进度分母

---

## [0.4.0] - 2026-07-26
### 新增
- **自动撰写入口**：发送区 "自动撰写" 按钮（单篇 chain / 批量提交）
- **全量自动 RAG**：8767 在线时所有子结构自动启用

---

## [0.3.0] - 2026-07-26
### 新增
- **日志系统**：串行写作状态持久化 `_status_text`
- **子结构写作要点显示**
- **蓝图文档**：`blueprint.json`

---

## [0.2.5b4] - 2026-07-26
### 修复
- PyPI long_description 缺失更新日志

## [0.2.5b3] - 2026-07-26
### 新增
- PyPI 发布准备：目录改名、LICENSE、README、blueprint.json
- GitHub Actions 检测支持

## [0.2.5b2] - 2026-07-26
### 新增
- 两级 RAG 查询、实时状态文本、子结构 summary 显示
- `state_manager.set_status_text()`

## [0.2.5b1] - 2026-07-26
### 新增
- RAG 知识库对接、冷启动、KB 下拉联动
- 提示词模板系统（5 套模板）
- 子结构系统、大纲勾选/取消、双级排序
- 续写机制（finish_reason=length 自动续写）
- LLM 客户端 `chat_detailed()`、max_tokens 从 config 传入

### 变更
- 端口 8770、LLMClient 存储 max_tokens

## [0.1.0] - 2026-07-26
### 新增
- 项目骨架、LLM 统一客户端、会话管理、大纲规划器、串行写作器
- 异步生成 + 进度轮询、会话恢复、setup.bat
