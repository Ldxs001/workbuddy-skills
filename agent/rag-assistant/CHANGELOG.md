# rag-assistant 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本号遵循语义版本控制（`__init__.py` 唯一源）。

---

## [1.1.0] - 2026-07-15
### 改进
- **query 类型参考全面重写**：4 个内置类型（fact/compare/opposition/analysis）的 entities/attrs 描述从模糊指南改为精确判定规则，明确"什么是主体""什么是维度"的区分标准。analysis 类型改为纯单主体分析示例，比较性分析归入 compare 类型
- **evidence 校验报错分两类反馈**：key 在原文有但 value 不是原句 → 指出 value 问题；key 在原文不存在 → 给出原文摘录供对照选择，LLM 不再盲猜
- **prompt 新增两条防污染规则**：① 一个概念只放一边（不跨 entities/attrs）② 不要太细碎（不拆同义词 key）
- **历史摘要标签强化**：标注"关键词不得用于当前问题的 entities/attrs"，配合 prompt 规则避免历史上下文污染
- **analysis 示例替换为纯单主体**：从"AI如何模仿人类情感、有什么缺陷..."改为"新能源汽车的市场规模、政策环境和消费者态度"，避免 LLM 混淆成比较查询
### 里程碑
- **PyPI 分类器升级为 5 - Production/Stable（正式版）**：pypi-build.py 构建脚本的 `Development Status` 从 `4 - Beta` 改为 `5 - Production/Stable`

## [1.0.2] - 2026-07-14
### 修复
- **web_ui.py BUILTIN_QUERY_TYPES 缺 `analysis` 类型**：v1.0.1 后端 agent.py 已新增"多维度分析"查询类型，但 web_ui.py 的内置类型列表未同步，导致 Web 配置页面"查询类型参考"只显示 3 个老类型。已补全
- **`compare` 类型 attrs 描述误导为单维度**：示例和 attrs 说明暗示只能填单个维度，导致 LLM 不敢填多维度。改为例句展示单维+多维两种场景，attrs 标注"多个用逗号分隔"

## [1.0.1] - 2026-07-14
### 修复
- **Qwen jinja template 连续 role 报错**：`_second_pass()` 中 `reasoning` 行被错标为 `assistant`，导致 messages 出现连续两个 assistant/user，触发 Qwen chat_template 渲染失败（"No user query found"）。修复为跳过 `reasoning` 行，保证 user/assistant 严格交替
- **evidence key 校验反馈不明确**：`"以下词缺少原文出处"` 未指明问题出在 evidence key 必须与 entities/attrs 精确一致，导致 LLM 连续 6 次修错方向（去改 value 而非 key）。修复反馈消息为 `"以下词缺少 evidence key（必须与 entities/attrs 中的写法精确一致，不可改词）"`，同步修正 system prompt 中 evidence 说明

### 新增
- **新增查询类型：多维度分析**：BUILTIN_QUERY_TYPES 新增 `analysis` 类型，覆盖单主体+多分析维度场景（如"AI如何模仿人类情感、有什么缺陷、人类的独一无二性体现在哪里"）。entities=分析主体，attrs=分析维度A,分析维度B,分析维度C，rel=对比分析。不修改算法逻辑

## [1.0.0] - 2026-07-14
### 修复
- **穷举组合算法修复**：单实体+多属性+rel 场景下，rel 的语义值未进入切片（`if len(entity_list) >= 2:` 短路导致 rel 切片完全丢失）。修复为三层泛化规则：
  - 第一层：entity × attr 笛卡尔积（事实块检索，始终执行）
  - 第二层：全实体联合 × attr（多实体时执行）
  - 第三层：rel 驱动两两无重复配对 —— ≥2 entities 时 entity 两两配对 × attr × rel，单实体时 attr 两两配对 × rel（`itertools.combinations`，无对称重复）
- **agent 循环架构明确化**：大循环三阶段（LLM 决策 → Agent 执行 → LLM 第二轮回答），小循环（`_action_validation_loop`）处于大循环第一阶段（模式判定之后、动作执行之前）。小循环从 LLM 第 2 次 attempt 开始（attempt 1 由主流程处理），不从第一步重新执行。小循环内禁止 LLM 降级为 chat/逃逸，5 次失败后拒绝 LLM 自由回答

## [0.10.0] - 2026-07-13
### 新增
- **向量维度显示**：📦 嵌入模型推荐列表中每个模型显示 `| NNN维`（14 个常见映射）
- **本地模型扫描**：`data/models/` 目录自动扫描，手动放置的 sentence-transformers 模型自动出现在 📦 列表和 KB 模型选择器中
- **联网搜索配置**：搜索结果面板可选 DuckDuckGo / Tavily / Google Custom Search / Bing / 自定义 API 五种后端，独立 API Key 输入
- **搜索后端**：`search.py` 新增 Google、Bing、自定义 API 三种后端实现

### 修复
- **多KB路由模型隔离**：`retrieve_context()` 不再传递全局默认 embeddings 给所有 KB，改为每个 KB 自行加载专属模型（`get_embeddings(kb_name=target_kb)`），缓存复用
- **联网搜索checkbox不持久**：`onchange` 从空绑定的 `saveLLM()` 改为独立 `toggleWebSearch()` → `/api/search/toggle`；默认值 `True` → `False`
- **预设选择不持久**：下拉框选项缺少 `selected` 属性；应用预设时未保存 `prompt_selected_preset` key
- **聊天历史推理混入回答**：`_handle_chat_history` 中多行 `reasoning` 的续行被错误追加到 `cur["content"]`，修复为追加到 `cur["reasoning"]`
- **本地模型扫描误报**：`detect_local_embedding_models()` 中 rerank/NLI 路径未加入 `seen_paths`，且检测改用 `modules.json` Pooling 模块判断而非 `HuggingFaceEmbeddings` 硬加载
- **LLM 模型选择器错位**：`saveLLM()` 中 `savedModel` 变量值与循环后赋值重叠，导致模型下拉框在保存后被覆盖为旧值

## [0.9.6] - 2026-07-13
### 新增
- **Web UI 公式渲染**：对话界面支持 KaTeX 渲染 `$$...$$` 和 `$...$` 公式（用户输入和回答均支持）
- **Web UI 复制按钮**：每条消息右上角常显 📋 按钮，复制原始 Markdown 原文（非渲染后文本）；推理内容可独立展开复制
- **推理持久化**：LLM 的 reasoning 内容写入 session 记忆文件，刷新页面后可恢复展开查看

### 修复
- **聊天历史多行解析**：`_handle_chat_history` 改为按时间戳前缀聚合（而非按行匹配），多段落/表格/代码块的助手回答在刷新后不丢失
- **f-string 换行转义**：`\n` 在 Python f-string 中被解释为真换行，导致 JS 字符串跨行语法错误，整个 `<script>` 块挂掉。改为 `\\n` 正确输出 JS 字符串字面量

### 修复
- **README.md 架构图补 NLI**：PyPI 页面架构概览缺少第 4 步「(可选) NLI 三向分类」，修正后重新发布

## [0.9.4] - 2026-07-13
### 修复
- **PyPI 重新发布**：0.9.3 为 rebase 后的残缺版本（缺少根目录文件），0.9.4 重新发布含完整根目录的版本
- **GitHub Actions 修复**：补 `permissions.attestations: write` + `skip-existing: true`

## [0.9.3] - 2026-07-13

### 修复
- **下载进度检测**：改为查磁盘文件大小（huggingface 缓存 + model_downloads 双目录扫），不依赖子进程输出解析
- **NLI 模型探测遍历所有源**：ModelScope 第一个可达但无此模型时，改遍历所有可达源再判定
- **NLI 模型列表**：移除 hf-mirror 无权限的 `mDeBERTa-v3-base-xnli`，保留 `mDeBERTa-v3-base-mnli-xnli`（双源训练质量更好）
- **`showModal` 函数缺失**：补上定义，修复模态框未响应
- **`{true}` JS 语法错误**：`var hasNLIModel={true}` → `var hasNLIModel=true`
- **Prompt preview `\n` 被 Python 转义**：改用 `String.fromCharCode(10)` 拼换行
- **保存预设 API 读错字段**：读取 `data.template` 修复为 `data.slots`

## [0.9.2] - 2026-07-13

### 修复
- **NLI 模型探测失败**：探测只试第一个可达源（ModelScope），ModelScope 无 MoritzLaurer 模型导致 mDeBERTa 全标不可用。改为遍历所有可达源
- **NLI 模型列表清理**：移除 hf-mirror 无权限的 `mDeBERTa-v3-base-xnli`，保留双源版 `mDeBERTa-v3-base-mnli-xnli`

## [0.9.1] - 2026-07-13

### 修复
- **Web UI JS 语法错误**：`{true}` 改为 `true`（JS 关键词不能做属性名）
- **Prompt 预览 \n 断行**：Python `"""` 转义导致 JS 字符串跨行，改为 `String.fromCharCode(10)` 拼接

## [0.9.0] - 2026-07-12

### 新增
- **NLI 三向分类器**：`engine/nli_classifier.py` — cross-encoder 对 (query, doc) 输出 entailment/neutral/contradiction 概率。独立开关，6 个推荐模型（含多语言 XNLI 和英文 SOTA）。使用 slice 关键词做分类，适配穷举组合查询模式。在 reranker 之后或向量召回之后运行。标签透传：[NLI: entailment, 92%]
- **网络探测**：`embedding_model_manager.probe_all_models()` 先测下载源连通性（ModelScope/HF Mirror/HF Official），再 10 线程并行探测所有 26 个模型，结果 🟢/🔴 实时增量更新到 Web UI
- **Web UI toggle 守卫**：路由/reranker/NLI 无已下载模型时 toggle 灰化 + 红色提示文字
- **Config 自动修正模型路径**：`load_config()` 在配置路径无效时自动指向第一个已下载的同类型模型

### 修复
- **切片中文逗号未识别**：`re.split(r'[,，]', ...)` 支持中英文逗号
- **比较意图词重复**：rel 非空时自动从 attr_list 移除{异同,区别,差别,对比,...}
- **NLI 模型中英文混用 Bug**：多语言 NLI（mDeBERTa）仅 ModelScope 不存 → 改用 cross-encoder/nli-deberta-v3-base（ModelScope 有）
- **NLI 下载线程崩溃**（所有 import 移入 try 块内）
- **探测结果卡住不更新**（clearInterval 过早停止 + 去重统计修复）
- **探测路由 404**（`do_GET` 缺 `/api/availability-status`）
- **KB 数据污染**：221 chunks 跨库迁移（白酒→政经文哲53、白酒→设备条件56、理化检测→生物医疗56、设备条件→生物医疗5、检测技术→天体物理51）
- **Agent system prompt 重写**：entities=取主体/名词, attrs=取目的, rel=取行为
- **"2嵌入模型"计数Bug**：`rag_web_ui.py` 仅过滤 reranker，NLI 模型被计入嵌入模型计数，修复为同时过滤 NLI 模型
- **model_index.json type 字段缺失**：`download_model()` 保存索引时未写入 type，新增 `_get_model_type()` 映射表自动写入；已补全现有 5 个条目的 type 值
- **KB 签名 originals 缺少 kb_name**：`build_kb_signature()` 自动将 kb_name 前置到 originals 列表，防止化学词主导签名。白酒签名首词从"酒体"修复为"白酒"
- **组合查询两两配对**：rel 时 entities 全拼改为 itertools.combinations 两两配对 + attrs + rel
- **Prompt 插槽架构**：系统提示词锁定（不能编造）+ 3 插槽可配（引用格式/输出风格/资料不足时），UI 从单 textarea 改为 3 输入框
- **JS 语法错误**：`{true}` 修复（关键词做属性名）+ `\n` Python 转义修复
- **`_resolve_kb()` 尊重 `kb.auto_classify` 配置**：文本导入路径修复

## [0.8.6] - 2026-07-12

### 修复
- **KB签名算法重写**：四分法采样（小KB全量→中KB全域随机→大KB四分+每份内随机）
- **BCE排序修复**：候选词与每个原始关键词单独算相似度取最大值，防通用词蹭分
- **入库路由语义化**：`_resolve_kb()` 改为 cross-encoder 语义路由，尊重 `kb.auto_classify` 配置
- **生物医疗KB恢复**：225篇真实医学文档，签名、规则清零重建

## [0.8.5] - 2026-07-12

### 修复
- **入库路由改为语义分类**：`_resolve_kb()` 从关键词硬匹配改为 cross-encoder 语义路由，`use_semantic=True`
- **`_resolve_kb()` 尊重 `kb.auto_classify` 配置**：修复 HTML 开关与代码脱节
- **生物医疗 KB 恢复**：从旧 skill 目录恢复 225 篇真实医学文档，清除党建污染
- **KB 签名重算**：从真实医学内容重算为 `biomedical · aetiology · pathogenesis · clinical · medical`
- **`get_embeddings()` 缓存**：组合查询不再重复加载模型（18 次→1 次）
- **setup.bat 自适应等待**：轮询端口取代硬编码秒数，chcp 65001 修复中文乱码
- **启动 KB 探测改为阻塞并显示详细状态**：每库 ✅/❌ 状态 + 总数

### 重构
- **LLM 配置统一到 `llm` 子字典**：极客模式、配置面板、LLMClient 读取同一数据源
- **Web UI 标记渲染**：marked CDN 加载，markdown 真正生效
- **Web UI 模态弹窗**：confirm() 替换为自定义模态

### 新增
- **聊天历史持久化**：刷新页面不丢对话
- **压缩上下文 / 清除上下文 按钮**

## [0.8.4] - 2026-07-12

### 修复
- **Web UI 刷新丢聊天记录**：`_render_chat_tab()` 每次生成空白对话页，浏览器刷新后历史消失。新增 `GET /api/chat/history` 接口读取持久化会话文件，前端 `loadChatHistory()` 初始化时自动加载历史消息

## [0.8.3] - 2026-07-11

### 重构
- **极客模式分区适配当前架构**：从 5 区扩展到 8 区——分离重排序独立面板、新增知识库区（入库路由×自动分类）、新增 LLM 配置区（之前完全未暴露）、路由层标签修正为出库路由×KB签名

### 文档
- **架构概览图补全入库流程**：README 中架构图新增完整入库管道——文档加载 → 入库路由 → 切片流水线 → ChromaDB 写入 → KB 签名更新

## [0.8.1] - 2026-07-11

### 修复
- **修复 PyPI 元数据缺少 long_description**：之前 0.8.0 的 wheel 因构建时缺少 `pyproject.toml`，setuptools>=61 将 `Description` 标记为 `Dynamic`，导致 PyPI 页面不显示项目说明。本次通过 Trusted Publisher 重新构建发布

## [0.8.0] - 2026-07-11

### 修复
- **PDF 只导入第 1 页**：`import_documents_to_kb` 使用 `docs[0].page_content` 只取 PyPDFLoader 第 1 页，多页 PDF 丢失 90%+ 内容。改为 `"\n\n".join(d.page_content for d in docs)` 合并全部页
- **OCR 触发条件依赖文件名**：英文扫描版 PDF（无中文文件名、0 字符提取）被跳过 OCR。改为 `total_chars < 50` 无条件走 OCR，不再检查文件名
- **英文 PDF 误触发 OCR**：去掉了 `has_chinese_filename` 条件后所有英文论文走了 OCR。恢复为中文文件名 + CJK < 10% 才触发，0 字符独立走 OCR
- **LM Studio 超时**（未改动代码，需在 LM Studio 侧调大请求超时）

### 新增
- **KB 暂停写入**：配置页自动分类规则每行增加暂停/恢复按钮，暂停期间自动路由跳过该 KB，指定导入拒绝，查询不受影响

### 重构
- **历史对话隔离**：第一轮 LLM 决策不再传完整对话历史（仅压缩摘要），第二轮生成回答时仍带完整历史。写入记忆时自动剥离 `<<ACTION>>` 标签。历史消息加 `[历史对话]` 前缀
- **引用校验**：第二轮系统提示强制要求回答标注 `[n]` 引用，生成后校验引用编号是否在资料段落范围内

---

## [0.7.0] - 2026-07-11

### 修复
- **导入计数不准**：`_exec_import` 导入统计与 ChromaDB 实际数据不一致。根因是 manifest 残留旧路径（`try/finally` 修复）和 `add_documents_to_kb` 用 `max(chroma, accumulated)` 漂移（改为直接取 chroma 真实值）
- **语义子切被跳过**：`_run_secondary_without_inherit` 缺少 `secondary="semantic"` 分支，`recursive→semantic` 子切被 `else: return chunks` 静默吞掉
- **reranker 路径解析错**：`FallbackRouter._load_model()` 未通过 `model_index.json` 解析 HuggingFace ID→本地路径，fallback 到 `find_model_dirs` 随机选模型
- **签名反哺毒化关键词**：reranker 加载失败时降级为垃圾词频签名并反哺进 `auto_classify_rules`，修复为返回空签名不反哺
- **Web UI 端口不准确**：`_render_config_tab` 硬编码 8766，`start_web_ui` 算出的 `rag_port` 没传进去。改为 `_find_ports()` 自动查找 + 类变量传递
- **manifest 异常残留**：导入后清空 manifest 代码在 for 循环尾部，异常跳出时跳过。改为 `try/finally` 包裹

### 重构
- **KB 签名生成新流程**：BCE 语义质心提取 → jieba 候选词 → 停用词过滤 → BCE vs 原始关键词排序 → top-12 签名 / top-30 反哺。不再依赖 reranker
- **精排/路由解耦**：`FallbackRouter` 从 `router.py` 迁入 `reranker.py`，路由层不再引用 reranker 模块
- **kb_index.json 路径修正**：12 个 KB 的 `path` 从旧 `local-rag-builder` 位置改指向 `rag-assistant/data/kb/`

---

## [0.6.2] - 2026-07-10

### 修复
- **LLM 混淆历史指令和当前请求**：`<<ACTION>>` 标签在历史中多次出现时，LLM 把旧 query 动作（如 `entities="AI,社会,宗教"`）当成当前用户意图的一部分，与"入库"指令混合执行。系统提示新增"只对最新消息做决策"规则，明确最后一条 user 消息才是当前问题，历史中的 `<<ACTION>>` 已执行完毕不可重复。

---

## [0.6.1] - 2026-07-10

### 修复
- **main.py 启动崩溃**：`SCRIPTS_PATH` 未定义 → `NameError`。变量已改名 `ENGINE_PATH` 但引用未同步改，两处修正为 `ENGINE_PATH`。
- **Web UI 配置页空白**：`web_ui.py` 中 ENGINE_PATH 和子进程 rag_script 路径均多了一层 `dirname`，导致引擎模块 `from config import load_config` 找不到，`SKILL_AVAILABLE=False`，配置 Tab 显示"技能模块未加载"。修复路径计算
- **testLLM 未定义**：`</script>` 提前闭合将 `testLLM()` 函数抛到 HTML 文本中，浏览器作为标签解析不执行。修复 script 块边界
- **测试按钮无响应**：`_serve_llm_test()` 方法体只有 agent 空检查，缺少实际 LLM 测试调用。补上 `agent.llm.check_health()` 逻辑
- **数据目录双路径**：`engine/utils.py` 中 `DATA_ROOT` 通过两层 `dirname` 计算出 `rag_assistant/data/`，但真实数据在项目根 `data/`，导致 RAG 配置子进程读不到知识库。改为三层 `dirname` 统一到项目根目录

---

## [0.6.0] - 2026-07-09

### 新增
- **用户习惯画像系统**：`memory.py` 新增三阶层级分析——规则级语言风格分类（句式/语气/深度）、OCEAN 五维人格衰减更新、`get_persona()` 合成画像输出
- **记忆注入**：`agent.py` 将用户画像作为 system role 消息注入 LLM prompt（方案 C，`prompt_manager.build_persona_prompt()` 扩展点）
- **kbs_used 修复**：路由层（`router.route_query()`）每轮返回实际路由 KB，`_exec_query()`/`_exec_import()` 捕获并传入 `record_habit(kb=...)`，`kbs_used` 不再为空
- **Prompt 自定义预设**：`prompt_manager.py` 新增 `save_custom_preset()` / `delete_custom_preset()` / `get_all_presets()`；`rag_web_ui.py` 新增"保存为预设"按钮 + "删除预设"按钮 + 对应 API 端点

### 变更
- `memory.py` `record_habit()` 新增 `kb` 参数，新增语言分析和 OCEAN 更新逻辑
- `rag_web_ui.py` 预设下拉改用 `<optgroup>` 分区（内置/自定义），选项带 `data-builtin` 属性
- 旧 `user_habits.json` 无画像字段时自动补默认值，向后兼容

---



### 新增
- **TF-IDF 签名生成**：`rebuild_all_signatures()` 两轮扫描——第一轮收集所有 KB 词频算 IDF，第二轮用 TF-IDF 重排签名词，消除跨 KB 通用词干扰。单次入库用纯频率（无 IDF 上下文）
- **动态反哺**：每次反哺将签名词 + 现有规则词与签名做嵌入相似度，取 top-30 写入规则。原始关键词标记 `_originals` 永不被移除，新词仅在剩余空位中按相似度排序填充
- **jieba 依赖声明**：`requirements.txt` 添加 jieba≥0.42；代码加 `ImportError` 兜底，无 jieba 时降级正则分词

### 变更
- 反哺从重新处理 chunks 改为直接复用签名关键词，避免重复计算
- `update_kb_signature`, `induce_kb_signature`, `_build_signature_from_texts` 新增 `idf` 参数透传

---

## [0.5.2] - 2026-07-09

### 变更
- **反哺移除 reranker 逻辑**：取消无效的 reranker.score(词, "keyword") 过滤（跨语言场景好词负分、垃圾词正分，完全不可用）。改为纯频率统计 + 停用词过滤 + 嵌入去重
- **签名关键词提取过滤加强**：英文词最短长度从 2 提至 4，消除 PDF 提取碎片（phi、ous、app）；停用词表补充 60+ 常见连接词/代词

### 文档
- `rag-assistant-architecture.md`、`RAG_PROTOCOL.md`、`rag_web_ui.py` 描述全部对齐当前架构

---

## [0.5.1] - 2026-07-09

### 变更
- **KB 签名格式改为纯关键词**：去掉 `【摘要】` 前缀和 `| 摘录句子` 后缀，签名内容为纯关键词列表（`kw1 · kw2 · kw3`），更适配嵌入模型路由
- **反哺流程重构**：三步流水线——reranker.score(词, "keyword") 过滤垃圾词 → 频率统计排序（语言无关）→ 嵌入相似度 vs 现有关键词去重（>0.6 跳过），上限 30 条/库
- **HTML 路由层 UI 描述对齐**：入库侧标注"始终用嵌入模型"，出库侧说明"精排开→嵌入×签名 / 精排关→嵌入×关键词"

### 文档
- `architecture/rag-assistant-architecture.md`：系统概览路由描述、路由开关表、技能依赖表全部对齐
- `RAG_PROTOCOL.md`：`route_method` 枚举更新、模型角色对照表移除 `router.fallback.model_path` 字段

---

## [0.5.0] - 2026-07-09

### 变更
- **出库路由彻底弃用 reranker 模型**：原 `route_query` 使用 FallbackRouter（reranker）对问题×关键词打分，但 reranker 在多语言混合场景（中文问题×英文关键词/中文关键词）下得分不稳定甚至全负，路由经常失效。改为与入库路由一致的**嵌入模型路径**——嵌入.encode(问题) × 嵌入.encode(KB签名关键词) 做余弦相似度，稳定且跨语言友好
- **出库路由数据源切换**：从 `auto_classify_rules.json` 的关键词规则改为读取 `kb_signatures.json` 的签名关键词。签名由 reranker 在入库时自动从文档 chunks 中提炼，内容更贴近实际库内容，且随文档入库自动更新，无需手动维护
- **KB 签名反哺关键词规则**：每次签名更新后，用嵌入模型比对新签名词与 `auto_classify_rules.json` 现有关键词的相似度。低于 0.7 的视为新词，自动追加到规则中，上限 30 条/库。关键词以用户原始规则为基础不变，避免了自动跑偏

### 架构调整
- 路由架构最终确定为：

  | 环节 | 模型 | 比对对象 |
  |------|------|---------|
  | 入库路由 | 嵌入模型 | 文档正文 × 关键词 |
  | 出库路由 | 嵌入模型 | 问题 × KB 签名关键词 |
  | 精排 | reranker | query × 检索结果 |
  | 签名生成 | reranker | 文档 chunks → 关键词 |

- `FallbackRouter` 保留，仅用于签名生成阶段的文档片段打分，不再参与路由决策

---

## [0.4.0] - 2026-07-08

### 新增
- **入库路由独立化**：从原有路由层分离为独立体系，受 `kb.auto_classify` 控制。启用时使用向量模型（`get_embeddings()`）对文档正文×各KB关键词做余弦相似度匹配，路由到最佳知识库；关闭时走纯关键词匹配
- **HTML 路由层 UI 重构**：卡片拆分为 📥入库路由 + 📤出库路由左右两栏，各自显示当前模型和开关状态。出库路由模型跟随精排，移除独立选择器
- **多知识库主开关 `kb.enabled`**：关闭时入库路由（`_do_import`）和出库路由均不生效，全进 default

### 变更
- **KB 签名写入**：`rag_core.py` 中 `update_kb_signature()` 增加 `router.enabled` 检查，关闭时跳过签名写入，避免无意义加载
- **`FallbackRouter` 模型源**：`router.py` 优先读 `reranker.model_path`，兼容旧 `fallback.model_path` 作为回退
- **`_exec_import` 返回增强**：MANIFEST 批量导入后返回各 KB 分布明细，LLM 可据此告知用户路由结果

### 修复
- **空 KB 名 bug**：`_resolve_kb` 对不可分类文件返回 "" 时，更早降级为 `"default"`
- **`knowledge_base_manager.py` 恢复原始**：hybrid 模式的降级改动已还原，不污染技能代码

---

## [0.3.0] - 2026-07-08

### 修复
- **ChromaDB 入库崩溃**：`knowledge_base_manager.py` 中 `vectorstore.upsert()` → `add_documents()`。`langchain-chroma` v1.1.0 未封装 `upsert` 方法，导致每次写入均抛出 `AttributeError` 并触发 recovery 回滚，所有 PDF 实际从未入库
- **`rag_wrapper.import_file()` 谎报成功**：底层 `add_documents_to_kb()` 返回 `False"` 但 wrapper 无视返回值，永远返回 `{"success": True}`，误导用户以为导入成功
- **`_parse_action()` 正则断裂**：原 regex 将 Windows 路径中的 `\U` 当作 Unicode 转义、文件名中的 `"` 当作 value 结束符，导致路径截断和无限重试循环。重写为状态机解析，仅 `\"` 和 `\\` 为转义，`\X` 原样保留
- **`_build_first_pass_messages()` 丢路径**：session 文件多行注入后按行解析，后换行路径被 `.+` 丢弃，LLM 看不到上传的文件路径。改为单行注入 + 文件路径走 `import_manifest.json` 独立管理
- **`_validate_action()` import 校验**：LLM 用逗号分隔多文件路径时 `os.path.exists()` 检查整个字符串必然失败，现支持逗号拆分逐个校验
- **`_exec_import()` 多文件支持**：逗号分隔路径拆分为逐个导入，清理临时文件

### 新增
- **`path="MANIFEST"` 批量导入**：上传文件路径写入 `data/import_manifest.json`，LLM 只需输出 `path="MANIFEST"` 即可触发批量导入，彻底规避路径转义问题
- **`POST /api/agent/upload-files`**：浏览器文件上传端点，接收 base64 二进制保存到 `data/imports/` 并写入 manifest
- **`POST /api/memory/inject`**：向 session 注入系统通知而不触发 LLM 决策循环
- **Web UI 文件上传状态条**：显示上传的文件数量、大小和文件名

### 变更
- 压缩阈值：`COMPRESS_THRESHOLD` 40 → 100，`COMPRESS_REMOVE` = 40
- `_build_first_pass_messages`：历史对话解析为真实 user/assistant 角色消息对，而非塞入 System Message
- `_second_pass`：带上历史对话上下文

---

## [0.2.0] - 2026-07-08

### 新增
- **`RAG_PROTOCOL.md`** — 完整的外部接入协议规范，覆盖：
  - HTTP API 契约：13 个端点，全量请求/响应 JSON Schema
  - 配置契约：`rag_config.json` 完整字段说明 + 功能开关总表
  - 文件交互契约：`query.json` / `queries.jsonl` / `result.json` 格式定义
  - CLI 契约：参数清单 + 退出码
  - 模型调用契约：嵌入/reranker/LLM/路由四类模型对照表
- **`llms.txt`** — 遵循 llmstxt.org 标准的 AI 可读项目自描述文档，平台无关
- **`--batch` CLI 模式** — `python main.py --batch --input q.json --output r.json`，结构化输入输出
- **`--jsonl` 管道模式** — `cat queries.jsonl | python main.py --jsonl`，逐行处理
- **`_execute_structured()`** — 绕过 Agent 决策循环的直接 RAG 查询函数，支持 `rag_only` / `search_only` / `auto` 三种模式
- **`--pidfile` 参数** — 进程管理用 PID 文件写入

### 文档
- `main.py` 参数列表扩充（`--batch` / `--input` / `--output` / `--jsonl` / `--pidfile`）
- 开发目录与发布目录的 3 文件差分同步完成

---

## [0.1.0] - 2026-07-07

从 `local-rag-builder` v1.5.0 技能抽取为独立智能体应用。
所有 `rag_assistant/` 模块均为 07-07 新建，基于技能能力重新设计上层架构。

### 架构（自包容技能副本）
- `engine/` — local-rag-builder 完整技能引擎（rag_core / router / reranker / text_splitter / KB 管理 / 嵌入模型管理 / prompt 管理）
- `vendor/` — 嵌入第三方依赖（bs4 / pypdf / markdownify / soupsieve）
- `rag_assistant/agent.py` — LLM 自主决策循环（query / search / import 三动作 + 自修正 + 穷举组合查询）
- `rag_assistant/rag_wrapper.py` — 技能封装桥接层，保持技能完整流程
- `rag_assistant/llm_client.py` — Ollama（/api/chat） + LM Studio（OpenAI 兼容）双后端
- `rag_assistant/memory.py` — 三层记忆：短期对话 / LLM 压缩摘要 / 知识缺口 / 用户习惯统计
- `rag_assistant/search.py` — 联网搜索回退（DuckDuckGo / Tavily / urllib fallback）
- `rag_assistant/web_ui.py` — 自包含 HTTP 服务器 + 双 Tab（配置 iframe + 对话），文件拖拽导入

### 功能
- Web 界面（默认 8765 端口），支持 LLM 配置切换、模型列表、知识库浏览、文件拖拽导入
- CLI 交互模式（`--no-web`），支持 `/reset` 记忆重置
- `migrate` 子命令从 local-rag-builder 技能迁移已有知识库和模型
- 13 个知识库（白酒 / 啤酒 / 理化检测 / 生物医疗 / 量子物理 / LLM 理论 / 神经科学 / 政经文哲 / 设备条件 / τ scaling / 其他酒 / 诸子百家 / default）
- 双后端 LLM 支持 + 两级路由 + Reranker 重排序
- setup.bat 一键启动

---

## 版本来源

rag-assistant 从以下技能/版本演化而来（详见对应 skills 仓库的 changelog）：

| 来源 | 版本范围 | 时期 |
|------|---------|------|
| `local-rag-builder` | v0.1.0 → v1.5.0 | 2026-06-06 → 2026-07-07 |
| `rag-assistant`（独立） | v0.1.0 → 当前 | 2026-07-07 → 至今 |
