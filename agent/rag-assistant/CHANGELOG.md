# rag-assistant 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本号遵循语义版本控制（`__init__.py` 唯一源）。

---

## [0.6.1] - 2026-07-10

### 修复
- **main.py 启动崩溃**：`SCRIPTS_PATH` 未定义 → `NameError`。变量已改名 `ENGINE_PATH` 但引用未同步改，两处修正为 `ENGINE_PATH`。

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
