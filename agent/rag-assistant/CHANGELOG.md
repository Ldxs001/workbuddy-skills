# rag-assistant 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本号遵循语义版本控制（`__init__.py` 唯一源）。

---

## [2.2.10] - 2026-07-29
### 新增
- **自动回填检测 + backfill_headers.py 脚本**：`main.py` 启动时自动扫描所有 KB，若缺少 `chunk_seq`/`is_header` 则自动执行回填；支持单独调用 `python backfill_headers.py` 手动执行或 `--dry-run` 预览

---

## [2.2.9] - 2026-07-29
### 新增
- **chunk_seq 溯源链 + is_header 头部块标记**：摄入时每块分配全局递增序号 + 位置兜底(块0-3) + 逐块内容探测标记(作者/单位/期刊/标准头等信息)，检索时 `include_header=True` 回取头部块，合并到 context 供 LLM 直接回答文档元信息（标题/作者/单位等），无需结构化提取
- **对外 API `POST /api/kb/query` 增加 `include_header` 参数**：默认 false 行为不变，true 时返回 `headers` 字段 + context 含 `[文档元数据]===[检索内容]` 分区域格式
### 变更
- `agent.py _exec_query()` 硬编码 `include_header=True`，Web UI 对话可直接问"作者是谁""标题是什么"

---

## [2.2.8] - 2026-07-26
### 新增
- **外部 API 新增 `/api/kb/query` 端点**：支持外部系统（如 Structured Writer）直接调知识库检索，返回上下文和来源。接收 `query`（必填）、`kb`（可选，空=自动路由）、`top_k`、`score_threshold` 参数，调用 `agent.rag.query()` 完整检索管线（路由→检索→精排→NLI→build_context），不额外消耗 LLM token

---

## [2.1.0b2] - 2026-07-24
### 新增
- **web_llm 插件多配置（profile）系统**：插件配置从单组改为多条目管理。Tkinter 配置界面支持添加/编辑/删除多个 API 配置条目，每条包含名称、服务商、API 地址、Key、模型名、温度、Top P、最大 Token。数据存为 `{"profiles": [...]}`，兼容旧格式自动包装
- **LLMClient 按模型名匹配配置**：`_get_web_llm_config(model_name)` 查找对应 profile 的 base_url/api_key/参数，`list_models()` 返回所有已配置模型名，Web UI 模型下拉自动显示全部可选模型
- **AI 插件生成器**（`web_ui.py` 插件 Tab）：左侧新增 AI 对话面板���支持自然语言描述需求 → LLM 二阶段评估可行性 → 确认后生成完整插件代码
  - 评估阶段：LLM 根据 RAG Assistant 上下文（智能体生命周期、正面示例、硬拒绝清单）判断可行性，返回 plugin_name/type/input_fields/依赖等信息
  - 生成阶段：LLM 生成 `plugin.json` + `plugin_xxx.py` → 6 阶段校验管道（JSON 合法性 → Python 语法 ast.parse → 目录规划 builtin/user → tempfile 原子写入 → SM3 签名 → discover_and_register 刷新注册）
  - LLM 调用方式：`temperature=0.3`（确定性代码生成），其余参数（model/max_tokens/timeout）走主配置 `llm_config.json`
  - 新增端点 `POST /api/plugins/generate`，新增 `_PLUGIN_SPEC` 规范常量（RAG Assistant 上下文 + PluginBase 接口 + 字段池 + 硬拒绝规则 + 约束）

### 修复
- **setup.bat HNSW 提示顺序**：将 `estimate_rebuild_time.py`（模型加载测速）从版本检测提示后移到 Y 确认后的 DO_REBUILD 内，避免未确认就加载模型
- **setup.bat 加提示**：`从 1.x 升级到此版本需要重建全部知识库的 HNSW 索引。` 末尾追加 ` 初次使用的非升级用户建议直接跳过(N)。`（单行 echo，不引入新行，避免 chcp 65001 多行中文 CRLF 解析 bug）

---

## [2.1.0b1] - 2026-07-23
### 重大新增 — 插件系统
RAG Assistant 引入标准化插件系统，支持信息补充类（input_return）和外部输出类（input_output）两种插件类型。智能体完全掌握决策权，插件为纯执行者，不做判断不主动触发。

### 新增
- **插件框架**：`rag_assistant/plugins/base.py` — PluginBase 抽象基类，定义 `execute()` 和 `open_config_ui()` 接口
- **插件管理器**：`rag_assistant/plugins/manager.py` — 插件发现/注册/生命周期/配置持久化/超时熔断/文件沙箱/输出校验
- **内置联网搜索插件**：`rag_assistant/plugins/builtin/web_search/` — 首个内置插件，支持 DuckDuckGo/Tavily/Google/Bing/自定义 五种后端，含 Tkinter 配置界面。前 3 个搜索结果自动抓取页面正文（content 字段优先，snippet 兜底，不足 100 字自动 urllib 抓取），Tavily 的 `content` 字段正确映射
- **插件 Web UI 管理面板**：Web 界面新增"🔌 插件"Tab，支持查看/启用/禁用/配置插件，刷新按钮重新扫描
- **插件引用标注**：LLM 回答中引用插件信息时标注 `[插件名称]`（如 `[联网搜索]`），与知识库 `[n]` 编号引用共存
- **SM3 签名工具**：`tools/sign_plugin.py` + `tools/verify_plugin.py`，对插件代码文件和 plugin.json 计算 SM3 国密哈希（已修复 plugin.json 自引用问题，签名时自动排除 sm3_hash 字段）
- **SM3 校验修复**：`manager.py` 的 `_compute_hash()` 在读取 plugin.json 时先去除 sm3_hash 字段，与签名工具计算方式一致

### 插件系统设计要点
- **标准化接口**：6字段池（question/answer_draft/thinking/rag_context/session_id/plugin_dir）→ 插件按需声明 → 智能体裁剪传递
- **标准化返回**：`{type, content, priority, execution_error}`，支持 markdown/json/csv/plain_text
- **mandatory 机制**：mandatory=true 时智能体必须调用（适合输出类插件），false 时智能体自主判断（搜索类）
- **错误分级**：无 execution_error → 只报"xxx调用失败"；有 execution_error → 报"xxx调用失败：原因"
- **5 道安全防线**：信息隔离（只给声明字段）→ 文件沙箱（仅 data/plugins/<name>/）→ 超时熔断（连续 3 次失败自动禁用）→ 输出校验（schema 非法丢弃）→ SM3 签名（可选）
- **最小入侵**：不修改 agent.py 决策循环/动作解析/RAG 检索核心，只在 chat() 返回链路插入 2 个钩子点（before_response + after_response）

### 修复
- **联网搜索字段映射错误**：Tavily 返回 `content`（全文）而非 `snippet`，插件 `execute()` 改为优先取 `content`，其次 `snippet`，不足 100 字自动抓取页面

### 变更
- **Agent 启动流程**：插件管理器从延迟加载（首次 chat() 时）改为 `Agent.__init__()` 立即初始化，确保 Web UI 在首次对话前即可展示插件列表
- **配置页移除旧搜索 UI**：原 LLM 配置卡片的"联网搜索"checkbox 和搜索后端配置已移除（由插件系统接管），移除对应 3 个 JS 函数和 3 个 Python 模板变量

---

## [2.0.0b1] - 2026-07-22
### 重大变更 — 1.x → 2.x 迁移警告
**HNSW 管理重构：ChromaDB 内置 HNSW → hnswlib 独立索引**
- ChromaDB Rust 后端的 HNSW compactor 在 Windows 上存在持久化 bug，导致索引反复损坏
- 2.x 将向量搜索改为 **hnswlib 独立管理**，ChromaDB 仅用于 metadata 存储
- **从 1.x 升级到 2.x 必须重建 HNSW 索引**（启动时自动懒重建，或手动点击 🔨 HNSW）
- hnswlib 索引文件存储位置：`data/_hnsw/{sm3_hash}/`（ASCII 路径，避免中文路径 bug）

### 新增
- **懒重建机制**：`retrieve_documents()` 检测到 hnswlib 为空但 ChromaDB SQLite 有数据时，自动触发 `rebuild_kb_hnsw()` 重建索引，用户不感知
- **`estimate_rebuild_time.py`**：启动时加载嵌入模型 + 采样 10 条真实文档 chunk 测速，精确预估全库重建耗时。显示模型名称、每文档耗时 ms、预计分钟数
- **`rebuild_all_hnsw.py`**：批量重建全部 KB 的 HNSW 索引，跳过已有有效索引的 KB 和空 KB，供 `setup.bat` 调用
- **`setup.bat` Y/N/K 三选项**：Y 全量重建、N 跳过（后续懒重建或手动）、K 写入 `data/.no_hnsw_prompt` 永久跳过，再次部署 2.x 不再提示
- **`kb_index.json` 启动对齐**：自动删除目录已不存在的残留条目
- **懒重建控制台醒目标记**：重建开始/结束用 `===` 包围 + `⏳`/`✅` 标记，区分于普通输出
- **导入后自动删除源文件**：`data/imports/` 下已入库文件自动 `os.unlink()`

### 修复
- **HNSW 重建 ID 映射错误（关键修复）**：`rebuild_kb_hnsw()` 原来用 SQLite `embedding_metadata.id` 行号作为 ChromaDB ID 存入 hnswlib 的 `_id_map`，但 ChromaDB 的文档 ID 是 SM3 哈希值（64 位十六进制串）。搜索时 hnswlib 返回 SQLite 行号，`chroma_coll.get(ids=[...])` 全部空命中。修复为 `JOIN embeddings` 表读取真实 `embedding_id`，重建后搜索正常返回结果
- **`main.py` KB 扫描 `index` 未定义**：第 311 行 `index.get(entry, {})` 中 `index` 变量不存在导致 `NameError` → `except Exception: pass` 静默吞掉，输出"知识库: 无"。新增 `_load_index()` 导入 + `kb_index` 变量
- **启动扫描触发全量懒重建**：`main.py` 扫描每个 KB 时调用 `retrieve_documents("test")`，内部检测到 hnswlib 为空触发 `rebuild_kb_hnsw()`，19 个 KB 全部重建，启动卡死数小时。改为只创建 Chroma adapter 验证可访问性，不触发重建
- **`setup.bat` 括号内标签 + `else if` 语法**：`:ASK_HNSW` 标签位于 `if (...) { ... }` 块内 + `else if` 非标准 cmd.exe 语法，导致整个版本检测块被跳过，不弹交互、不启动浏览器。重写为纯 `goto` 流，无嵌套块
- **`setup.bat` 杀进程静默失败**：`Get-CimInstance` + `Get-NetTCPConnection` PowerShell 命令用 `>nul 2>&1` 隐藏所有错误，权限不足时旧进程不杀、新进程起不来。改为 `server.pid` PID 文件精确杀 + 端口兜底
- **`setup.bat` `[!]` 被延迟展开吃掉**：`setlocal enabledelayedexpansion` 下 `!` 触发变量展开，`[!]` 输出为 `[]`。改用 `***` 替代
- **`__pycache__` 缓存旧 `_hnsw_storage_dir`**：`chroma_adapter.py` 代码已改但运行的 Python 进程加载旧 `.pyc`，`_hnsw_storage_dir` 仍返回 `data/kb/_hnsw/`，导致懒重建写到旧位置、Chroma adapter 从新位置读不到 → 反复触发懒重建。清除后解决
- **`estimate_rebuild_time.py` 测速不准确**：用 `"测试文本" * 10` 测速（极短文本，12ms/条），实际文档 chunk 长 100-500 字（100ms+/条），预估偏差 8 倍。改为从 SQLite 随机取真实 chunk 测速
- **`rebuild_kb_hnsw` 中 `encode()` 进度条被 `2>&1` 隐藏**：SentenceTransformer 默认 `show_progress_bar=True` 但 tqdm 在非 TTY 输出下自动隐藏。加显式 `show_progress_bar=True` 强制显示
- **`kb_index.json` 残留已删除 KB 条目**：手动删 KB 目录后索引未更新显示旧 KB。启动时自动遍历索引检查目录是否存在，不存在则移除
- **`default` 空 KB 每次启动报 `HNSW 损坏`**：扫描器跳过空 KB，不调用 `retrieve_documents`，无 warning 噪音
- **导入后源文件未删除**：`agent.py` 第 895-901 行已有删除逻辑，但因之前 `UnboundLocalError` 导致导入函数抛异常退出，`success=True` 路径未走到。修复后导入成功自动 `os.unlink(pp)`

### 变更
- **彻底移除 langchain 依赖**：`langchain`, `langchain-community`, `langchain-huggingface`, `langchain-chroma`, `langchain-text-splitters`, `openai` 全部移除
- **5 种切分策略手写替代**：fixed/recursive/headers/sentence/semantic，含 5 种守卫栈
- **ChromaDB 降级为 metadata-only**：列式向量搜索走 hnswlib，ChromaDB 只存文本+键值对
- **`count()` 改为 SQLite 实时查询**：不再依赖 hnswlib 或 ChromaDB API

## [1.8.0] - 2026-07-21
### 修复
- **PDF 导入 UnboundLocalError**：`import_documents_to_kb()` 中 `from utils import Document` 位于 OCR 回退分支内导致 Python 局部变量提前引用崩溃，所有 PDF 入库均报"文档加载失败"。提升至函数顶层解决

### 变更
- **版本号**：`1.8.0b1` → `1.8.0`（正式版）

---

## [1.8.0b1] - 2026-07-21
### 重大变更
- **彻底脱 langchain**：移除全部 6 个 langchain 依赖（langchain, langchain-community, langchain-huggingface, langchain-chroma, langchain-text-splitters, openai），替换为原生调用
- **自定 Document 数据类**（`utils.py`）：替代 `langchain_core.documents.Document`，全项目 12 处替换
- **SentenceTransformer 嵌入包装器**（`embeddings.py`）：替代 `langchain_huggingface.HuggingFaceEmbeddings`，支持 embed_query/embed_documents 接口
- **ChromaDB 原生适配器**（`chroma_adapter.py`）：替代 `langchain_chroma.Chroma`，直接在 chromadb PersistentClient 上封装 similarity_search/as_retriever/from_documents/add_documents 等接口
- **手写切分器**（`text_splitter.py`）：5 种策略（fixed/recursive/headers/sentence/semantic）+ 3 种子切全部手写，零 langchain-text-splitters 依赖
- **PyPDFLoader → pypdf.PdfReader**：`rag_core.py`, `agent.py`, `rag_skill.py` 三处 PDF 加载改用 vendor/pypdf
- **TextLoader → open().read()**：全部文本文件读取改用原生文件操作
- **OpenAI LLM → requests.post()**：`rag_standalone.py` 的 `get_llm()` 和 `rag_web_ui.py` 的 LLM 推荐改用 OpenAI 兼容 API 直调

### 新增
- **HNSW 管理系统**：M 值可调（4-256）、自动重建开关、手动重建按钮，每 KB 独立配置
  - `knowledge_base_manager.py`: `get_kb_hnsw_config()`, `set_kb_hnsw_config()`, `rebuild_kb_hnsw()`
  - `rag_web_ui.py`: KB 列表每行加入 M 输入框 + 自动重建开关 + 🔨 HNSW 按钮 + JS 处理函数 + API 端点
  - `external_api.py`: `GET /api/kb/hnsw-config`, `POST /api/kb/hnsw-config`, `POST /api/kb/rebuild-hnsw`
- **模型路径自动解析**（`embedding_model_manager.py`）：`_resolve_actual_model_path()` 处理 HuggingFace Git LFS 结构的 snapshot 目录发现，写入索引时自动指向真文件位置
- **vendor 目录加入 sys.path**（`__init__.py`）：使 `from pypdf import PdfReader` 在所有子模块中可用

### 修复
- **NLI 模型加载失败**：`model_index.json` 中 `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` 路径指向 git-lfs root 而非 snapshot 子目录 → 修正为 snapshot 路径
- **HNSW 自动重建后召回率异常**：多 KB 因 UUID 目录清理后 ChromaDB 自动重建的 HNSW 索引质量差 → 新增全量重建机制（删 collection + 重新 embed + 写入），召回率从 0/5 恢复至 3/5
- **ChromaDB collection 命名不兼容**：新适配器用目录名作 collection 名 → 修正为 `"langchain"`（与原 langchain_chroma 默认一致）

### 变更
- **依赖精简**：`requirements.txt` 移除 `langchain`, `langchain-community`, `langchain-huggingface`, `langchain-chroma`, `langchain-text-splitters`, `openai`；保留 `chromadb`, `sentence-transformers`, `huggingface-hub`, `modelscope`
- **版本号**：`1.7.0` → `1.8.0b1`

## [1.7.0] - 2026-07-21
### 新增
- **外部接入 API（port 8767）**：`rag_assistant/external_api.py` 独立服务，6 个能力域 27 个 REST 端点，与 Web UI 完全隔离
- **功能开关运行态切换**：`POST /api/feature/toggle` + `GET /api/feature/status`，运行态切换 router/reranker/nli/web_search/auto_classify/geek_mode，持久化到 config.json，免重启
- **模型直接调用**：`POST /api/model/embed` 嵌入、`/api/model/rerank` 重排序、`/api/model/nli` 三向分类，绕过完整 RAG 流程独立调模型
- **KB 管理 API**：`POST /api/kb/create` / `/delete` / `/move` + `GET /api/kb/list` / `/sources` / `/backups` + `POST /api/kb/backup` / `/restore`
- **KB 签名管理**：`GET /api/kb/signatures` + `POST /api/kb/signature/build` + `POST /api/kb/signature/rebuild-all`
- **提示词管理 API**：模板读写/重置（`/api/prompt/template`）、插槽读写（`/api/prompt/slots`）、预设 CRUD+应用（`/api/prompt/presets` / `preset` / `preset/delete` / `preset/apply`）、系统前缀（`/api/prompt/system-prefix`）
- **输入管理 API**：文本切分（`POST /api/input/split`，透传 5 种切分策略 + 5 种守卫）、问题组合切片展开（`POST /api/input/query-slices`，entities×attrs 穷举）、策略列表（`GET /api/input/strategies`）
- **CLI 参数**：`--api-port` 指定端口启动外部 API（默认不启动，兼容旧用法）

### 修复
- **`llms.txt` 全面过时**：版本从 v0.1.0→v1.7.0，修复自修正重试次数（2→5）、压缩阈值（40行→token-based）、API端点数（13→30+）、路由模型角色混淆、文件名引用错误等全部过时信息
- **`PROTOCOL.md` 版本滞后**：v0.1→v1.0，补充外部 API 交叉引用
- **`rag-assistant-architecture.md` 多处过时**：版本 v0.9.0→v1.7.0b1→v1.7.0，修复 `RAG_PROTOCOL.md`→`PROTOCOL.md` 文件名错误、端点列表从 16 个补全到 32 个、新增 5.2b 外部 API 节、压缩阈值描述修正（行数→token比例）、搜索引擎列表从 2 种补全到 5 种

### 变更
- 版本从 `1.7.0b1` 升级为 `1.7.0`（正式版，去掉 beta 标记）
- README.md 全面更新：文件结构对齐当前架构、新增外部 API 说明、新增协议文档导航
- `main.py` +`--api-port` 参数，daemon 线程启动外部 API
### 重大变更
- **KB 签名生成机制重构**：四分法采样后 4 象限各算独立质心 → 各取近 20 个 chunk → 各象限独立 jieba + 停用词 + BCE 排序 → 四段拼接（每象限前 20 直接拼），签名上限 12→80 词。`router.py` `build_kb_signature()` 重写
- **多向量路由**：`kb_signatures.json` 新增 `signatures` 字段存储各象限签名，`route_query()` 区分多向量（逐个 cosine 取最高分）与单向量（fallback），数据驱动不再硬编码
- **反哺策略改为四象限均分**：`(30 - count(originals)) // 4` 每象限配额，取代全局 top-30 竞争，`router.py:343-377`

### 新增
- **签名重建控制**：`config.py` 新增 `signature_auto_rebuild: False` 配置项，`knowledge_base_manager.py:658-667` 入库时根据开关决定全量/增量更新
- **Web UI 签名管理**：KB 签名区新增"入库全量重建"开关 toggle，KB 列表每行新增"重建签名"按钮，JS 添加 `rebuildOneSig()` + `toggleAutoRebuild()` API
- **单 KB 重建 API**：`rag_web_ui.py` 新增 `POST /api/router/rebuild-one` 和 `POST /api/router/toggle-auto-rebuild`
- **查询类型参考修复**：`web_ui.py` 补上 `setTimeout(loadQueryTypes, 500)` 页面初始化调用，4 个内置类型正常显示
- **停用词扩展**：`router.py:167` 新增 `接上、转下页、上一页、下一页、上页、下页、翻页、第几页` 8 个 PDF 分页残留词

### 修复
- **`_originals` 持久化缺陷**：`_save_rules()` 入口自动补齐 `_originals`（`knowledge_base_manager.py:72-77`），不再依赖反哺阶段的条件保存
- **`rag_core.py` 死代码**：删除第 505-513 行引用不存在的 `update_kb_signature` 的多余代码
- **`update_kb_signature` 缺失导入**：`rag_web_ui.py:23` 补上 `build_kb_signature` 导入
- **签名预览截断**：Web UI 签名行显示从 `[:80]` → `[:120]`，鼠标悬停看全文
- **签名重建无反馈**：按钮重建过程禁用 + loading 态，完成后立即执行 `location.reload()`
- **查询切片缺失 entity 单独层**：`agent.py` 补上 `_slices.add(e)`，对齐三层策略
- **多实体 rel 切片缺失宽匹配**：`agent.py` 多实体时同时生成 `e1 e2 rel` 和 `e1 e2 attr rel` 两种
- **空 evidence 值绕过校验**：`agent.py:510` 增加 `not v.strip()` 检查，空值不再因 Python 的 `"" in src` 特性放行
- **LLM entities 拆碎修饰域**：system prompt 第 184 行加"不要将修饰域拆为独立 entity"，第 185 行 attrs 允许复合短语，第 190 行加"凝缩而非泛化"规则

### 变更
- 路由截断 `[:200]` → `[:512]`（适配长签名）
- 清理死常量 `SIGNATURE_MAX_WORDS = 12`
- 保留 `idf: dict = None` 参数兼容（TF-IDF 恢复待后续）

---
### 重大变更
- **多会话管理**：替换"重置对话"为"新建会话"，侧边栏列出所有历史会话，支持切换/归档/恢复。`agent.py` 新增 `new_session()`、`list_sessions()`、`archive_session()`、`delete_session()`、`_generate_session_id()`
- **压缩阈值改为 token 比例**：删除硬编码 100 行阈值，改为 `max_tokens × compress_ratio`（默认 4096×0.7=2867 token）。`memory.py` 新增 `estimate_token_count()`，可配置压缩触发比例和移出比例

### 新增
- **聊天侧边栏**：左栏 260px 宽，列出所有会话（含最近消息预览）。每个会话右侧 📦 归档按钮，归档会话灰显，点击 `↩` 可恢复。底部显示归档数量展开按钮
- **会话归档系统**：归档将会话文件移入 `data/archives/sessions/`，压缩记忆移入 `data/archives/memory/`，不删除数据。`max_sessions` 配置（默认 20）控制非活跃会话上限，超出自动归档最旧的
- **配置折叠**：配置 tab 的 LLM/记忆/搜索卡片可点击 `▾` 折叠，状态存入 localStorage
- **`memory.compress_ratio`/`compress_remove_ratio`/`max_sessions` 配置**：在 8765 配置行中与 LLM 设置同排显示，支持实时修改
- **KaTeX 字体文件**：复制 60 个字体文件到 `static/fonts/` + NOTICE.md 许可证声明
- **PCR/CT值 路由到生物医疗**：`auto_classify_rules.json` 中生物医疗 `_originals` 新增 PCR、聚合酶链式反应、CT值、核酸、基因检测等 10 个关键词

### 修复
- **Tab 切换 8766 泄漏**：消除 `.tab-content.active { display: block }` 与 `#chat-content.active { display: flex }` 的 CSS 冲突，改 JS 直接设置 `style.display`（block/none/flex），不再依赖 CSS class 控制显隐。CSS 中 `#config-content.tab-content { display: block }` 只作默认值，JS inline style 优先级更高，切换时绝对覆盖
- **`web_ui.py` 重建**：因 git checkout 误操作丢弃未提交改动，据 CHANGELOG + agent.py/memory.py API 重构 web_ui.py。侧边栏/会话管理/配置折叠/压缩比例全部恢复
- **双滚动条**：chat-messages 与 chat-content 高度溢出导致 body 额外滚动，`#chat-panel` 加 `overflow: hidden` + flex 子项最小高度 0 修复
- **`kb-status` / `llm-config` Null 报错**：删除 status-bar 后残留 JS 引用加 null 守卫
- **Enter 键未绑定**：从 `addEventListener`（注册时机问题）改为 textarea `onkeydown` 内联属性
- **setup.bat 杀不掉旧进程**：`netstat|find|tokens=5` 因 Windows 版本列偏移失效。改为 PowerShell `Get-CimInstance Win32_Process` 按命令行查杀 + `Get-NetTCPConnection` 按端口兜底
- **MiniCPM 语义判断方向错误**：原为 value 在 sources 中搜索，改为 key vs value 语义一致性判断

### 变更
- `agent.py` 所有 Memory 方法从固定 `"default"` session_id 改为动态生成
- 配置 tab 从原水平带状改为两张独立卡片（LLM + 记忆），统一 grid 布局 + border-radius:10px
- 删除 `status-bar`（kb-status、llm-config、压缩/清除/重置按钮）
- `memory.py` 删除 `COMPRESS_THRESHOLD`、`COMPRESS_REMOVE` 硬编码，新增 `COMPRESS_REMOVE_RATIO`
- `pop_oldest_lines()` 参数从 `n=int` 改为 `ratio=float`

### 移除
- 重置对话按钮、清除上下文按钮（由新建会话 + 归档替代）
- `status-bar` 相关元素及 JS 引用

## [1.5.0b1] - 2026-07-17
### 重大变更
- **删除 MiniCPM evidence 校验，统一 NLI**：移除 `_minicpm_check()`（~100行 + 2处 monkey patch）、`_minicpm_evidence_enabled` 配置、`minicpm_model_id` 配置、MiniCPM 模型选择器/checkbox/JS/API 路由。evidence 语义验证改为复用已有的 NLI cross-encoder 模型（mDeBERTa），`nli_classifier.py` 新增 `verify(key, value)` 方法 + `get_nli_classifier()` 单例供 agent 和 rag_core 共享
- **NLI 配置拆分**：`nli.output_enabled` 独立控制输出证据校验，与输入 NLI（`nli.enabled`）互不依赖

### 新增
- **evidence value 格式校验**：禁止 `/`、`、`、`|`、`·` 等拼接分隔符，value 必须是原文单个连续子串
- **entities/attrs 格式校验**：每个 entity/attr 必须是单个概念，禁止内部拼接分隔符
- **evidence 额外 key 过滤**：只校验 entities/attrs 中出现的 key，LLM 多塞的额外 key 自动忽略
- **value 尾缀清洗**：子串校验前自动去除 `...` 尾缀（LLM 常自己加）
- **子串包含自动通过**：key in value 或 value in key → 直接通过，跳过 NLI 判断
- **NLI 输入/输出双开关 HTML 面板**：左右分栏，同路由层风格
- **sentencepiece 依赖**：加入 requirements.txt，NLI 模型 tokenizer 必需

### 修复
- **NoneType 崩溃**：evidence value 为 `null` 时 `v in src` 炸 `TypeError`，加 `v is None` 守卫
- **拒绝提示词不分上下文**：`found_sources` 和 `else` 分支均按 MiniCPM/NLI 开启/关闭/None 三路分叉提示
- **MiniCPM 语义判断方向错误**：原为 value 在 sources 中搜索，改为 key vs value 语义一致性判断

### 移除
- `_minicpm_check()`、`_minicpm_evidence_enabled()`、`self._minicpm_llm`
- 配置项 `minicpm_evidence_enabled`、`minicpm_model_id`
- HTML 中 MiniCPM checkbox、模型选择器、toggle/select JS 函数、minicpm-toggle/minicpm-select API 路由
- 顶栏 `gguf_count` 统计卡片

## [1.3.0-beta] - 2026-07-16
### 新增
- **Evidence 语义验证系统**：出库路由第一步校验后增加 MiniCPM/Qwen 语义二次判断。硬编码 evidence 校验不通过时，若 toggle 开启且有模型，走 LLM 语义验证（支持"存在"/"不存在"二元输出），降低错误拒绝率
- **双模型选择**：evidence 验证面板支持两个模型互斥选择——Qwen2.5-0.5B-Instruct（默认，标准架构，1.2GB）和 MiniCPM5-1B（2.1GB，更高精度）。各模型独立下载按钮+状态显示，radio 互斥切换，未下载自动灰化
- **KB 计数更正按钮**：KB 列表下方新增 `🔧 计数更正` 按钮，调用 `/api/kb/tech-recount` 后端 API 遍历每个 KB→ChromaDB `.count()` 读真实行数→写入 kb_index.json→自动 reload。兜底修复任何原因导致的计数偏差
- **顶部 stat 卡片分类**：从单"嵌入模型"拆分为 4+2 共 6 卡片（向量模型 / Ranker 模型 / NLI 模型 / 推理模型 / 知识库 / 文档块），按 RECOMMENDED_*_MODELS ID 精确匹配计数
- **GGUF 下载停滞检测**：`/api/download-status` 连续 3 轮轮询（~6秒）缓存大小无变化时自动标记 `status=failed` 并提示"下载卡死"，不再静默卡 450MB
- **NOTICE.md 全量补全**：vendor/NOTICE.md "Pre-downloaded Model Weights" 从 11 个模型补全到 26 个，按嵌入/reranker/NLI/推理模型四类分表

### 修复
- **KB 移动计数不更新**：`move_kb_documents()` 从 ChromaDB 物理删除文档后未更新源 KB 的 `doc_count`，导致源库计数虚高、总计数偏离。修复为 delete 后立即 `vs_src._collection.count()` 读真实行数并写入索引
- **GGUF 下载重复触发**：多次点击"下载"创建 N 个并行下载线程互相打架。修复为 `/api/download-model` 入口增加 `_download_tasks` 活跃检查，已有下载则拒绝
- **GGUF 下载进度显示**：`/api/download-status` 轮询扫描缓存目录累计所有文件大小，断点续传场景下正确显示缓存总量（由 450MB 增长到 989MB），不扣除基线
- **MiniCPM evidence transformers 5.x 兼容性**（三连洞）：
  - `is_torch_fx_available` 被 transformers 5.x 移除 → monkey-patch `lambda: False`
  - `get_expanded_tied_weights_keys` 期望 dict 但 MiniCPM remote code 传 list → monkey-patch 自动 list→dict 转换
  - `GenerationMixin` 从 `PreTrainedModel` 剥离后 `model.generate()` 报 `'list' object has no attribute 'keys'` → 改用原始 forward pass + argmax 逐 token 生成，彻底绕过 `generate()`
- **Evidence 模型切换**：MiniCPM4-0.5B 的 remote code 与 transformers 5.x 深度不兼容（remote code 依赖撤掉的老 API，修不完）。替换为 Qwen/Qwen2.5-0.5B-Instruct（标准 LlamaForCausalLM 架构，`trust_remote_code=False`，零兼容问题）
- **Evidence 验证面板布局**：模型选择 radio 误塞进出库路由窄列导致 flex 竖排。拆为独立整行（浅灰底色，margin-top+padding+ronded），标签清晰
- **Qwen instruct 模型纯文本失效**：Qwen2.5-0.5B-Instruct 是指令微调版，直接喂纯文本不识别指令，永远输出"不存在"。修复为优先走 `tokenizer.apply_chat_template()`，失败才降级纯文本

### 变更
- `RECOMMENDED_GGUF_MODELS`：`openbmb/MiniCPM4-0.5B` → `Qwen/Qwen2.5-0.5B-Instruct`（默认，1.2GB）
- 默认 evidence 模型 ID：配置新增 `nli.minicpm_model_id`，默认 `Qwen/Qwen2.5-0.5B-Instruct`
- `has_minicpm` 从只检查第一个模型改为 `any(is_gguf_downloaded(m["id"]) for m in RECOMMENDED_GGUF_MODELS)`
- 旧配置残留模型 ID 不在推荐列表时自动回退到第一个模型并写回配置
- Stat 卡片 label "推理模型 (MiniCPM)" → "推理模型"

---

## [1.2.0] - 2026-07-15
### 新增
- **知识库备份系统**：RAG 配置页新增备份卡片，支持手动备份/恢复/删除，及入库前自动备份（最多保留3个版本，按KB独立管理）
- **入库路由最低阈值**：`min_import_score: 0.4`，低于阈值的文档不回路由到任何KB，回退到default（HTML可配置，与出库阈值并列）
- **KB文档浏览与移动**：每个KB旁新增"浏览"按钮，模态框显示按source文件分组的文档列表（附内容预览），支持勾选移动到其他KB（自动校验向量模型一致性+重建签名反哺）
- **反哺语义阈值**：新增 `MIN_FEEDBACK_SIMILARITY: 0.3`，候选词必须与原始关键词的BCE语义相似度超过此值才考虑收录
### 修复
- **反哺满30词后只删不补**：原逻辑满30词后新候选词无法进入。改为满30后按语义分数替换最差的旧反馈词（原始词永久保留）
- **自动备份每文件触发**：原每文件入库各备份一次，批量导入5文件后所有自动备份被污染。改为每批次每KB只备份一次（`_AUTO_BACKUP_DONE`追踪器）
- **web_ui.py `_serve_llm_config_get` 双发JSON**：同一个GET请求调了两次 `_send_json()`，导致响应体拼接HTTP头，前端JSON解析失败（`position 94`报错）
- **JS反斜杠转义问题**：`split('\\')` 在Python→JS渲染时被错误转义，导致整个script块语法错误。改用 `replace(/\\\\/g,'/')` 及事件委托规避
- **JS正则语法错误**：`refreshBackups` 中使用 `/regex/ + variable` 语法错误导致整个脚本块不执行
### 变更
- **反哺算法**：从不低于阈值则按top-30收录 改为 加阈值+满30择优替换（原始词永久保留、新词需 ≥0.3、替换最低分旧词）
### 修复
- **追问场景 evidence 校验死锁**：用户追问元批评（如"太泛化了，没有给出具体的数值等"）时，旧规则要求 entities/attrs/evidence 只从当前用户消息提取，但追问消息本身不含概念实体词（杂醇油、浓度、血管扩张等），导致 LLM 自造词或从历史偷概念 → evidence 校验 5 次拒绝死锁。修复为：
  - `_get_previous_turns()` 新增方法，从短期记忆文件解析上一轮问题原文和 AI 回答原文
  - system prompt 规则改为：**entities 从问题原文提取**（当前问题或上一轮问题均可），**attrs 可从问题或回答内容提取**（当前和上一轮均可），**evidence 三源（当前消息/上一轮问题/上一轮回答）均可作为原文出处**
  - `_build_first_pass_messages()` 新增 `【上一轮问题】` 和 `【上一轮回答】` 作为 system context 供 LLM 引用
  - `_validate_action()` evidence 校验从单源（original_msg）改为三源（original_msg + prev_question + prev_reply），key/value 在任一源存在即放行。拒绝反馈改为按词粒度定位所属源，仅展示对应源的上下文片段（key 前 30 字 + key 后 80 字），不再粗暴拼接三源截取 300 字
- **evidence 拒绝反馈措辞诚实化**：原提示"请从以下原文中复制完整原句"与下方实际显示的字符级截断切片矛盾。改为"以下为定位参考（字符级切片），请对照系统提示中的原文复制完整原句"

## [1.1.1] - 2026-07-15
### 修复
- **web_ui.py 与 agent.py 的 BUILTIN_QUERY_TYPES 解除重复**：web_ui.py 改用 `from .agent import BUILTIN_QUERY_TYPES`，消除两份副本不一致问题。以后修改 agent.py 的类型描述会自动同步到 Web 配置页面

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
