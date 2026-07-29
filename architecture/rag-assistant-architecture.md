<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# RAG Assistant 架构文档

> 独立 RAG 智能体 — LLM 驱动的组合式语义检索与多库路由。
> 作者：wUwproject | 许可证：Apache 2.0
> 更新：2026-07-24 (v2.1.0b2) — 新增智能体插件系统 + AI 插件生成器

---

## 一、系统概览

RAG Assistant 是一个**本地知识库问答智能体**，基于 local-rag-builder 技能构建，核心理念是从传统单轮问答升级为 **LLM 驱动的组合式检索** + **用户画像自适应交互**：

```
用户输入
  → [LLM 决策层]
       ├─ 闲聊 → 直接回答
       └─ 知识库查询 → entities/attrs/rel 分词
           → [组合展开器] 穷举 entities × attrs（≥2 entity 时两两配对 + attrs + rel）
           → [多切片检索] 每片独立走完整 RAG 流程
              1. 路由（route_query → 嵌入模型 × KB签名/关键词）
              2. 检索（retrieve_documents → ChromaDB 相似度 + HNSW 自动修复）
              3. (可选) 重排序（reranker：model / rule / hybrid 三模式）
              4. (可选) NLI 三向分类（entailment / neutral / contradiction）
              5. 构建上下文（build_context，含 NLI 标签渲染 + SM3 去重）
           → [SM3 国密去重合并] 按内容哈希去重
           → [插件注入] input_return 插件结果注入上下文（如联网搜索补充）
           → [LLM 综合回答] 基于完整上下文 + 用户画像 + 3插槽 prompt 生成回答
           → [插件副作用] input_output 插件执行（如日志记录）
           → [引用门禁] 校验 LLM 回答中的 [n] 引用是否在资料段落范围内
```

### 1.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **LLM 分词 > 规则分词** | 实体/属性由 LLM 基于语义标注，不依赖关键词规则 |
| **穷举 > 猜测** | 所有 entities × attrs 组合都查一遍，不预判哪组最优。rel 时 entities 两两配对 |
| **去重 > 冗余** | SM3 国密哈希按内容去重，避免重复上下文浪费 token |
| **自修正 > 静默丢弃** | LLM 格式错误时反馈重试（v0.9.5: `chat()` 传 `max_retries=2`），不静默吞掉 |
| **技能完整走 > 绕路** | 每片独立走 route_query → retrieve_documents → reranker → NLI → build_context 全流程，不改造技能内部逻辑 |
| **配置持久化 > 运行时内存** | 所有配置（LLM / 路由 / 重排序 / NLI / 切片 / prompt 插槽）写入 `rag_config.json`，刷新页面不丢 |
| **历史隔离 > 上下文污染** | 第一轮 LLM 决策仅传压缩摘要（不传完整历史），避免上一轮 entities 泄漏到当前决策 |
| **用户画像自适应 > 固定 prompt** | 基于 OCEAN 五维人格 + 语言风格分析的画像系统，自动调整 LLM 交互风格 |

### 1.2 路由开关行为

三开关体系：

| 开关 | 控制 | 开 | 关 |
|------|------|----|----|
| `kb.enabled` | 多知识库主开关 | 允许入库/出库路由工作 | 全部路由失效，全进 default |
| `kb.auto_classify` | 入库路由 | 嵌入模型余弦相似度匹配文档 × 各 KB 关键词，路由到最佳 KB | 纯关键词匹配，无匹配进 default |
| `router.enabled` | 出库路由 | 嵌入模型 × KB 签名关键词做余弦相似度（精排开时），或嵌入模型 × 规则关键词（精排关时）。精排关时不写 KB 签名 | 纯关键词匹配，不写 KB 签名 |

路由方法枚举：

| 路由方法 | 触发条件 |
|---------|---------|
| `hardcoded` | 命中硬编码关键词规则 |
| `embedding_signature` | 精排开：嵌入模型 × KB 签名关键词做余弦相似度。v1.7.0b1 支持多向量路由：有分象限签名列表时各做一次 cosine 取最高分，优于单字符串路由 |
| `embedding_keyword` | 精排关：嵌入模型 × 规则关键词（top-30）做余弦相似度 |
| `default` | 无匹配，路由到 default |
| `direct` | 用户直接指定了知识库 |
| `broadcast` | 语义回退失败后全量广播所有 KB 检索 |

### 1.3 KB 签名生成流程（v1.7.0b1）

```
入库 → 文档 chunks
  → 四分法采样（N<200 全量 / 200≤N<500 全域随机 / N≥500 四分+每份随机）
  → 4 象限各自独立计算 BCE 语义质心
  → 每象限取距质心最近的 20 个 chunk
  → 各象限独立 jieba 候选词提取 + 停用词过滤（含 PDF 分页残留词）
  → 各象限独立 BCE 比对原始关键词排序
  → 四段拼接：Q1[:20] + Q2[:20] + Q3[:20] + Q4[:20] → 上限 80 词
  → 签名同时保存为合并字符串 + 4 个分象限子字符串（多向量路由用）
  → 反哺：(30 - count(originals)) // 4 每象限配额
```

v1.7.0b1 核心改进：
- 四分法从"采样 4 份合 1 质心"改为"4 份各自算质心、各取 20 近邻"
- 签名上限从 12 词扩至 80 词（不强求，取实际值）
- 签名同时保存多段子签名（`signatures` 列表），路由时逐个 cosine 取最高分
- 反哺从全局排序改为四象限均分：`(30 - originals) // 4`
- 停用词扩展 8 个 PDF 分页残留词：接上、转下页、上一页、下一页、上页、下页、翻页、第几页

---

## 二、三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | `web_ui.py` (port 8765) / RAG 配置页 subprocess (port 8766) / CLI (stdin) | Web 界面、LLM 配置面板、聊天界面、模型管理、知识库配置、CLI 交互 |
| **业务层** | `agent.py` / `rag_wrapper.py` / `engine/rag_core.py` / `engine/router.py` / `engine/reranker.py` | 决策循环、组合查询、路由/检索/重排序/NLI、记忆管理、用户画像 |
| **基础设施** | `llm_client.py` / `engine/config.py` / `engine/utils.py` / `data/` / `vendor/` | LLM 通信、配置管理、数据持久化、内嵌第三方依赖 |

### 2.1 完整文件结构

```
rag-assistant/
├── main.py                          # ★ 入口（4 种模式：web / cli / batch / jsonl）
├── setup.bat                        # Windows 一键启动 + 进程管理
├── requirements.txt                 # 依赖清单
├── CHANGELOG.md                     # 版本更新日志
├── PROTOCOL.md                      # 外部接入协议规范（HTTP/CLI/文件交互）
├── llms.txt                         # AI 可读的项目自描述文档（llmstxt.org）
├── blueprint_rag.json               # PyPI 发布蓝图
├── README.md                        # 项目说明
├── LICENSE                          # Apache 2.0
├── server.pid                       # 运行时 PID（setup.bat 管理进程）
├── _test_router_score.py            # 路由评分测试脚本
├── .gitignore
│
├── rag_assistant/                   # ★ 智能体核心层
│   ├── __init__.py                  # 版本号: 0.9.5
│   ├── agent.py                     # Agent 决策循环（~620 行）
│   ├── web_ui.py                    # Web 界面（port 8765，~1300 行）
│   ├── llm_client.py                # LLM 统一客户端
│   ├── rag_wrapper.py               # RAG 封装桥接层
│   ├── search.py                    # 联网搜索
│   ├── memory.py                    # 四层记忆 + 用户画像系统
│   ├── _fix_rag.py                  # 破损数据修复工具
│   │
│   └── engine/                      # ★ local-rag-builder 技能核心（独立副本）
│       ├── __init__.py
│       ├── rag_core.py              # RAG 核心：检索/嵌入/导入
│       ├── router.py                # 两级路由：关键词 + 嵌入 × KB 签名
│       ├── reranker.py              # 三模式重排序 + FallbackRouter
│       ├── nli_classifier.py        # NLI 三向分类器
│       ├── knowledge_base_manager.py# 知识库 CRUD + 自动分类 + SM3 去重 + ChromaDB 容灾
│       ├── config.py                # 配置加载/保存/自动修正模型路径
│       ├── embedding_model_manager.py# 5 源并行模型下载管理
│       ├── prompt_manager.py        # 3 插槽 + 预设管理 + 用户画像扩展点
│       ├── text_splitter.py         # 5 策略 + 5 守卫插件架构
│       ├── rag_skill.py             # 技能接口
│       ├── rag_standalone.py        # 独立模式
│       ├── rag_web_ui.py            # RAG 配置页（完整前端）
│       ├── rag_setup_orchestrator.py# 安装编排
│       ├── rag_env_setup.py         # 环境检测
│       └── utils.py                 # 工具函数 + 数据目录管理
│
├── vendor/                          # ★ 内嵌第三方库（零 pip 也可在受限环境中运行）
│   ├── bs4/                         # BeautifulSoup4
│   ├── pypdf/                       # PDF 解析
│   ├── markdownify/                 # HTML → Markdown
│   └── soupsieve/                   # CSS 选择器（bs4 依赖）
│
└── data/                            # 运行时数据
    ├── config/rag_config.json       # 引擎全量配置（含 llm 子字典、prompt_slots 等）
    ├── kb/
    │   ├── kb_index.json            # 知识库索引
    │   ├── kb_signatures.json       # KB 签名关键词
    │   ├── auto_classify_rules.json # 自动分类规则
    │   └── {name}/                  # 各知识库（13 个，ChromaDB SQLite + HNSW）
    ├── models/
    │   └── model_index.json         # 模型索引
    ├── config/rag_config.json       # LLM 与检索配置
    ├── memory/
    │   ├── compressed_{id}.txt      # LLM 压缩摘要
    │   ├── kb_gaps.json             # 知识缺口（最多 200 条）
    │   └── user_habits.json         # 用户习惯 + OCEAN 人格画像
    ├── sessions/{id}.txt            # 短期对话
    ├── prompts/
    │   ├── custom_presets.json      # 用户自定义 prompt 预设
    │   └── custom_prompt_template.txt
    ├── import_manifest.json         # 待入库文件清单
    ├── imports/                     # 浏览器上传临时目录（入库后自动清理）
    └── cache/                       # 模型下载临时缓存
```

---

## 三、组件详解

### 3.1 决策循环 — `agent.py`

核心是 `_decide_with_retry()` 方法，实现 **LLM 决策 → 解析 → 校验 → 自修正** 闭环。
第一轮决策（`_build_first_pass_messages`）**不传完整历史对话**，仅传压缩摘要作为 system context，避免上一轮查询 entities 泄漏到当前决策：

```
用户输入
  ↓
memory.append_short_term()           # 写入用户输入
  ↓
_decide_with_retry(message, max_retries=2)
  ↓
_build_first_pass_messages(message)
  ├─ system prompt（含动作格式说明）
  ├─ 压缩摘要作为 System context（【历史对话，仅作参考】）
  ├─ 用户画像提示（prompt_manager.build_persona_context()）
  └─ 当前消息作为 user message
  ↓
LLM 首次推理
  ↓
_parse_action(reply)                 # 状态机解析 <<ACTION ...>>
  ├─ (None, None) → 直接聊天回复
  ├─ (None, "错误原因") → 追加到 messages → LLM 修正重试（最多 2 次）
  └─ ({...}, None) → _validate_action()
       ↓ 拒绝同上 → LLM 修正重试
       ↓ 通过 → 执行
  ↓
2 次重试耗尽 → 清上下文，全新 prompt 重新回答（不污染上下文）
```

#### _parse_action — 状态机解析器

从 LLM 输出中提取 `<<ACTION type="..." ...>>` 指令，使用**状态机逐字符扫描**（而非正则表达式）：

1. **Windows 路径兼容**：`C:\Users\...` 中的反斜杠不被当作转义前缀，`\U` 不被解释为 Unicode 序列
2. **文件名含引号**：仅 `\"` 和 `\\` 视为转义，其他 `\X` 保持字面量

返回格式：
- `(None, None)` — 无动作标记，正常聊天
- `(None, "原因")` — 有 `<<ACTION` 但格式错误
- `({...}, None)` — 解析成功

**动作格式校验**：校验 `type` 是否 query/search/import，`entities`/`attrs` 非空，`kb` 必须用户提及，`path` 必须存在等。

#### 组合查询 — 穷举展开

当 LLM 输出 `type="query"` 时触发组合查询。v0.9.0 改进：rel 时 entities 两两配对（itertools.combinations）而非全拼，排除 attrs 中的比较意图词：

```python
# LLM 输出示例
<<ACTION type="query" entities="三个代表重要思想,老子无为而治"
                     attrs="核心观点,相同点,不同点"
                     rel="思想渊源比较">>

# 展开逻辑：
# 1. 每个 entity × 每个 attr（单独）
# 2. 所有 entities 联合 × 每个 attr（全拼，覆盖非对比场景）
# 3. 如果有 rel: itertools.combinations 两两配对 × attrs × rel
slices = [
    "三个代表重要思想 核心观点",          # 单 entity × attr
    "三个代表重要思想 不同点",
    "老子无为而治 核心观点",
    "老子无为而治 不同点",
    "三个代表重要思想 老子无为而治 核心观点",  # 联合 × attr
    "三个代表重要思想 老子无为而治 不同点",
    "三个代表重要思想 老子无为而治 核心观点 思想渊源比较",  # 两两配对 × attr × rel
    "三个代表重要思想 老子无为而治 不同点 思想渊源比较",
    "三个代表重要思想 老子无为而治 思想渊源比较",  # 两两配对 × rel
]
```

组合切片展开后各片独立走 `rag.query()` 完整流程，结果按 SM3 内容哈希去重（`hashlib.new('sm3', ...)`）后合并为单一上下文，交给 LLM 生成最终回答。

**get_embeddings() 缓存优化**（v0.8.5）：组合查询共享同一个嵌入模型实例，避免每片重复加载（18 次 → 1 次）。

### 3.2 LLM 客户端 — `llm_client.py`

支持双后端，统一返回 `{text, reasoning, raw}`。支持流式响应：

| 后端 | 协议 | 接口 | 模型参数 | 默认端口 |
|------|------|------|---------|---------|
| LM Studio | HTTP (OpenAI 兼容) | `/v1/chat/completions` | `max_tokens` / `temperature` | 1234 |
| Ollama | HTTP (Ollama API) | `/api/chat` | `num_predict` / `temperature` | 11434 |

**模型发现**：调用 `/v1/models`（LM Studio）或 `/api/tags`（Ollama）列出可用模型。

**健康检查**：`check_health()` 通过简化 API 调用测试后端连通性。

### 3.3 Web 界面 — `web_ui.py`

基于 Python `http.server` 的单文件 Web 界面（~1300 行），无外部框架依赖。端口自动分配（`_find_ports()` 查找 2 个可用端口）。

**前端**：内嵌单页 HTML + JS，使用 marked CDN（cdn.jsdelivr.net/npm/marked/marked.min.js）渲染 Markdown。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` 或 `/index.html` | GET | 主页面（配置 Tab + 对话 Tab） |
| `/api/config` | GET | 获取完整配置 |
| `/api/kbs` | GET | 知识库列表 |
| `/api/llm/models?backend=xxx` | GET | 扫描模型列表 |
| `/api/llm/test` | GET | 测试 LLM 连接 |
| `/api/config/llm` | GET/POST | 获取/更新 LLM 配置（backend/model/timeout/maxtokens） |
| `/api/chat` | GET/POST | Agent 决策循环聊天 |
| `/api/chat/history` | GET | 聊天历史持久化（v0.8.4） |
| `/api/agent/query` | GET/POST | 直接 RAG 查询（绕过 Agent 决策） |
| `/api/agent/import` | POST | 导入文档（3 种模式：path/text/content） |
| `/api/agent/upload-files` | POST | 浏览器上传文件到服务器临时目录 |
| `/api/agent/gaps` | GET | 知识缺口列表 |
| `/api/memory/reset` | GET | 重置对话 |
| `/api/memory/compress` | GET/POST | 压缩上下文 |
| `/api/memory/clear-context` | GET/POST | 清除上下文 |
| `/api/memory/inject` | POST | 注入系统通知 |
| `/api/search/toggle` | POST | 联网搜索开关 |
| `/api/availability-status` | GET | 模型下载探测状态（v0.9.0） |
| `/api/plugins` | GET | 插件列表（v2.1.0） |
| `/api/plugins/toggle` | POST | 启用/禁用插件（v2.1.0） |
| `/api/plugins/config` | POST | 打开插件配置界面（v2.1.0） |
| `/api/plugins/refresh` | POST | 重新扫描插件目录（v2.1.0） |
| `/api/plugins/generate` | POST | AI 插件生成器（v2.1.0） |

**关键交互细节**：
- `loadModels()` 在页面加载后 500ms 触发，填充模型下拉框
- 配置保存后立即同步到 `self.agent.llm.*` 运行时实例
- `llm_max_tokens` 和 `llm_timeout` 持久化到 `rag_config.json`
- 路由/reranker/NLI toggle 无已下载模型时灰化 + 红色提示文字
- 网络探测结果实时增量更新 🟢/🔴

**文件上传流程**：点击文件选择按钮 → 文件以 base64 二进制上传到服务器 `data/imports/` 目录并记录到 `import_manifest.json`，同时聊天框出现系统通知。用户输入"入库"后 LLM 发出 `path="MANIFEST"` 指令，系统读取清单逐个走完整导入管线。

**PDF 导入**：
- 多页 PDF 合并全部页内容后切分（`"\n\n".join(d.page_content for d in docs)`）
- OCR 回退条件：`total_chars < 50` 无条件触发；`total_chars >= 50` + 中文文件名 + CJK 占比 < 10% 也触发
- 英文正常 PDF 不走 OCR

### 3.4 RAG 封装层 — `rag_wrapper.py`

将 local-rag-builder 的技能接口包装为 Agent 可调用的形式：

```python
rag.query(question, kb_name=None, k=5, score_threshold=0.0)
  → retrieve_context(question, kb_name, k, score_threshold)
    → route_query(question)                 # 路由：两级（关键词 + 嵌入 × KB签名）
      → retrieve_documents(question, kb)    # 检索：取 top-K chunk（HNSW 自动修复）
        → reranker.rerank(docs)             # 可选：精排（model/rule/hybrid）
      → nli_classifier.classify(docs)       # 可选：NLI 三向标注
      → build_context(docs)                 # 构建上下文（含 NLI 标签）
  → return {context, docs, kb, has_context}
```

### 3.5 搜索模块 — `search.py`

| 引擎 | 方式 | API Key |
|------|------|---------|
| DuckDuckGo | `requests.get(html.duckduckgo.com/html/)` | 无需 Key |
| Tavily | `POST api.tavily.com/search` | 需配置 Key |
| urllib fallback | 纯 HTML 解析回退 | 无需 Key |

通过 `web_search_enabled` + `web_search_api_key` + `web_search_engine` 配置。

### 3.6 引用门禁 — `agent.py`

v0.8.0 新增：LLM 回答后校验引用编号。`_second_pass()` 中的引用校验逻辑：
- 系统提示强制要求每个具体事实/数字后面标注来源段落编号 `[n]`
- LLM 回答后提取所有 `[n]` 引用，检查编号是否在资料段落范围内
- 不存在的段落编号 → 告警追加到回答尾部
- 无引用 → 记录日志（不作为错误）

### 3.7 KB 暂停写入

v0.8.0 新增：配置页自动分类规则表格每行增加暂停/恢复按钮。

| 场景 | 行为 |
|------|------|
| 自动路由入库 | `auto_classify()` 从 rules 中过滤掉 `kb_paused` 列表中的 KB，文件自动路由到次高分的非暂停 KB |
| 用户指定入库 | `add_documents_to_kb()` 拒绝写入，提示"已暂停，请恢复或选其他 KB" |
| 查询/检索 | 完全不受影响 |
| 恢复暂停 | 再次点击按钮，KB 恢复为可写入 |

### 3.8 重排序 — `engine/reranker.py`

三模式重排序 + FallbackRouter（v0.7.0 从 router.py 迁入）：

| 组件 | 职责 |
|------|------|
| `ModelReranker` | transformer cross-encoder 打分排序 |
| `RuleReranker` | 规则引擎（score_weight / recency / source_weight / boost_keywords） |
| `HybridReranker` | 模型打分 + 规则微调 |
| `FallbackRouter` | 语义回退路由（cross-encoder 对 query × KB 签名打分）+ KB 签名生成阶段的文档片段打分 |

重排序不再参与路由决策（v0.5.0 解耦）。路由改用嵌入模型余弦相似度。

### 3.9 NLI 三向分类器 — `engine/nli_classifier.py`

v0.9.0 新增，cross-encoder 3-class 模型（contradiction / neutral / entailment）。

| 模型 | 语言 |
|------|------|
| `cross-encoder/nli-deberta-v3-base` | 英文（SOTA） |
| `MoritzLaurer/mDeBERTa-v3-base-xnli` | 多语言 XNLI |
| `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` | 多语言（双源训练） |
| `BAAI/bge-reranker-v2-minicpm-layerwise` | 多任务 |
| `cross-encoder/nli-MiniLM2-L6-H768` | 英文（轻量） |
| `cross-encoder/nli-roberta-base` | 英文 |

标签输出格式：`[NLI: entailment, 92%]`
在 reranker 之后（reranker 开时）或向量召回之后（reranker 关时）运行。

---

## 四、记忆系统 — `memory.py`

四层记忆 + 用户画像系统，统一管理短期对话、压缩摘要、知识缺口和用户习惯性格画像。

### 4.1 短期记忆

| 方法 | 功能 | 存储 |
|------|------|------|
| `append_short_term(session_id, role, content)` | 追加一条对话记录（超 2000 字符截断） | `data/sessions/{session_id}.txt` |
| `get_short_term(session_id)` | 读取完整对话历史 | 返回 `str` |
| `clear_short_term(session_id)` | 清空对话历史 | 删除文件 |
| `pop_oldest_lines(session_id, n)` | 弹出最旧的 N 行（默认 40） | 返回被移除的文本 |
| `short_term_line_count(session_id)` | 当前行数 | 返回 `int` |
| `needs_compression(session_id)` | 行数 > 100 触发压缩开关 | 返回 `bool` |

### 4.2 长时记忆（压缩摘要）

| 方法 | 功能 | 存储 |
|------|------|------|
| `store_compressed(session_id, summary)` | 追加一条压缩摘要 | `data/memory/compressed_{session_id}.txt` |
| `get_compressed(session_id, limit=3)` | 返回最近 N 条摘要 | 返回 `str`（多摘要拼接） |

**压缩触发**（`_compress_if_needed()`）：当 `short_term_line_count() > 100`（约 50 轮对话）时触发：
1. `pop_oldest_lines()` 取出最旧 40 行对话
2. 调 LLM 压缩为摘要（结构化指令要求保留核心需求、已得结论、追问方向、最近 3 条原文，200 字以内）
3. `store_compressed()` 存入长时记忆

### 4.3 知识缺口记录

记录检索不到答案的查询，分析知识库覆盖盲区。保留最近 200 条，相同 query 自动累加计数。

```json
{
  "query": "三个代表与老子无为而治的相同点",
  "kb": "政经文哲",
  "count": 3,
  "first_seen": "2026-07-08T04:20:13",
  "last_seen": "2026-07-08T04:25:27"
}
```

### 4.4 用户习惯与性格画像（v0.6.0）

**三层分析体系**：

| 层级 | 方法 | 输出 |
|------|------|------|
| **规则级语言分析** | `_classify_sentence(msg)` | 句式（statement/question/imperative/rhetorical）+ 语气（neutral/critical/curious/sarcastic/terse/enthusiastic）+ 深度（shallow/medium/deep） |
| **OCEAN 五维人格** | `_ocean_delta()` → 衰减更新（`PERSONALITY_DECAY=0.98`） | openness / conscientiousness / extraversion / agreeableness / neuroticism（0-1，默认 0.5） |
| **合成画像** | `get_persona()` → `build_persona_context()` | 语言风格统计占比 + 人格标签 + 行为偏好文本 |

**人格更新机制**：

```python
# 衰减 + 新样本加权
new_val = old * decay + delta * (1 - decay)  # decay=0.98
personality[dim] = clamp(new_val, 0.0, 1.0)
```

**人格标签映射**（`get_persona()` 中的 `_dim_label`）：

| 维度 | < 0.55 | ≥ 0.55 |
|------|--------|--------|
| openness | 守成型 | 探索型 |
| conscientiousness | 随性型 | 严谨型 |
| extraversion | 内敛型 | 外放型 |
| agreeableness | 对抗型 | 亲和型 |
| neuroticism | 稳定型（< 0.45） | 敏感型（≥ 0.45） |

### 4.5 与 Agent 的集成

```python
chat(message)
  ↓
append_short_term("default", message)    # 写入用户输入
  ↓
_build_first_pass_messages(message)      # 第一轮决策：不传完整历史
  ├─ system prompt（含动作格式说明）
  ├─ 压缩摘要作为 system context（【历史对话，仅作参考】）
  ├─ 用户画像提示（方案 C：prompt_manager.build_persona_prompt()）
  └─ 当前消息作为 user message
  ↓
LLM 决策（query/search/import/直接回答）
  ↓
执行动作 → _second_pass(message, context, action)  # 第二轮：带上下文 + 历史
  ↓
append_short_term("default", reply)      # 写入助手回复（自动剥离 <<ACTION>> 标签）
record_habit(message, is_rag, ..., kb)   # 记录习惯 + 语言分析 + OCEAN 更新
↓ 如果检索结果为空
record_gap(query, kb)                    # 记录知识缺口
```

**历史隔离**（v0.8.0）：第一轮决策不传完整历史对话，仅传压缩摘要作为 system context。第二轮 `_second_pass()` 仍携带带 `[历史对话]` 前缀的历史消息，保证跨轮追问的上下文连贯性。

**ACTION 剥离**（v0.8.0）：写入记忆时自动使用 `re.sub(r'<{1,2}\s*ACTION\s+.*?>{1,2}', '', content, flags=re.DOTALL|re.IGNORECASE)` 剥离内部指令标签。

---

## 五、外部接口

### 5.1 Python 编程接口（API）

| 类 | 入口方法 | 返回格式 |
|----|---------|---------|
| `Agent` | `.chat(message) → dict` | `{"text", "success", "reasoning", "kb", ...}` |
| | `.reset_session()` | 无返回值 |
| `Memory` | `.get_short_term(id) → str` | 对话历史文本 |
| | `.append_short_term(id, role, content)` | 无返回值 |
| | `.get_gaps(min_count) → list[dict]` | `[{"query", "kb", "count", ...}]` |
| | `.get_habits() → dict` | `{"total_queries", "chat_ratio", "personality", ...}` |
| | `.get_persona() → dict` | `{"linguistic_summary", "personality", "behavior"}` |
| `LLMClient` | `.chat(messages) → dict` | `{"text", "reasoning", "raw"}` |
| | `.list_models() → list[str]` | 模型名列表 |
| | `.check_health() → bool` | 连接状态 |
| `RAGWrapper` | `.query(question, kb_name) → dict` | `{"context", "docs", "kb", "has_context"}` |
| | `.import_file(path, kb_name) → dict` | `{"success", "doc_count", "kb"}` |
| | `.import_text(text, kb_name, title) → dict` | `{"success", "doc_count", "kb"}` |
| | `.list_kbs() → dict` | 知识库字典 |
| `WebSearch` | `.search(query, max_results) → dict` | `{"results": [{"title", "url", "snippet"}], "success"}` |

### 5.2 技能依赖接口

| 技能模块 | 导入函数 | 用途 |
|---------|---------|------|
| `rag_core` | `retrieve_context` | 检索主入口（路由→检索→reranker→NLI→build） |
| `rag_core` | `get_embeddings` | 嵌入模型管理（单例缓存） |
| `rag_core` | `build_context` | 上下文构建（含 NLI 标签渲染） |
| `knowledge_base_manager` | `list_knowledge_bases` | 知识库枚举 |
| `knowledge_base_manager` | `_load_rules` / `auto_classify` | 入库路由 |
| `knowledge_base_manager` | `sm3` | SM3 国密哈希去重 |
| `config` | `load_config / save_config` | 配置持久化 + 模型路径自动修正 |
| `prompt_manager` | `build_second_pass_prompt` | 3 插槽 prompt 构建 |
| `prompt_manager` | `build_persona_prompt` | 用户画像注入 |
| `nli_classifier` | `NLIClassifier.classify` | NLI 三向分类 |

### 5.3 Agent 动作协议（LLM ↔ Agent 通信）

LLM 在回复中嵌入 `<<ACTION ...>>` 标记控制 Agent 行为：

```python
<<ACTION type="query" entities="实体1,实体2" attrs="属性A,属性B" rel="关系词" kb="知识库名">>
<<ACTION type="search" query="搜索词">>
<<ACTION type="import" content="入库的完整文本内容">
<<ACTION type="import" path="MANIFEST">        # 批量导入所有待入库文件
```

**LLM 分词语义规则**（v0.9.0 重写）：
- `entities`：取主体/名词。问题中涉及的核心事物、人物、概念
- `attrs`：取目的。用户想查询的目标/用途/对象。注意排除比较意图词（异同、区别、对比等）
- `rel`：取行为。实体间的动作/关系。当有多个 entities 且存在动作关系时填写

### 5.4 Prompt 3 插槽架构 + 自定义预设 — `prompt_manager.py`

系统提示词框架锁定不可改，暴露 3 个插槽由用户配置：

| 插槽 | 默认值 | 作用 |
|------|--------|------|
| `cite_format` | "每个结论后面用 [n] 标注来源的段落编号" | 控制引用标注格式 |
| `output_style` | "用 Markdown 格式输出" | 控制输出风格 / 格式 |
| `fallback` | "如果资料中没有明确结论，可以结合资料进行分析推理，但不能编造不存在的内容" | 控制无资料时的处理策略 |

**预设管理**：4 个内置预设（标准模式 / 深度分析 / 对比分析 / 友好对话）+ 用户自定义预设 CRUD。RAG 配置页 UI 中以下拉 `<optgroup>` 分区显示，内置预设不可删除。

---

## 六、流程详解

### 6.1 完整请求生命周期

```
用户发送消息
  ↓
web_ui.py → POST /api/chat
  ↓
agent.chat(message)
  ↓
记忆写入 → _compress_if_needed()
  ↓
_build_first_pass_messages(message)
  ├─ system prompt（含 entities/attrs/rel 格式说明）
  ├─ 压缩摘要
  ├─ 用户画像提示
  └─ user message
  ↓
LLM 首次推理
  ↓
_parse_action(reply)
  ├─ 无 <<ACTION → 直接聊天回复 ✅
  └─ 解析成功 → _validate_action()
       ↓
       ↓ 通过
       ↓
       → type == "query"
         → _exec_query(entities, attrs, rel, kb)
           → 展开组合切片（单×全×两两配对）
           → for each slice:
                rag.query(slice, kb_name)
                  → retrieve_context(slice, ...)
                    → route_query → retrieve_documents → reranker → NLI → build_context
           → SM3 去重合并
           → [插件] pm.run_before_response() — input_return 插件注入上下文
           → return {context, docs, kb}
         → _second_pass(message, context, action)
           → build_second_pass_prompt(context, question, kb)  # 3 插槽
           → LLM 基于上下文生成回答
           → [插件] pm.run_after_response() — input_output 插件副作用
           → 引用门禁校验
           → 记忆写入 → record_habit() → record_gap()
       → type == "search"
         → search.search(query)
         → _second_pass(...)
       → type == "import"
         → path == "MANIFEST" → 批量导入
         → path == 具体路径 → import_file()
         → 含 content → import_text()
       ↓
回答返回前端（含插件注入内容）
```

### 6.2 导入生命周期 — 完整管道

```
用户上传文件 (Web UI drag & drop)
  ↓
POST /api/agent/upload-files → 保存到 data/imports/ + 写入 import_manifest.json
  ↓
用户说"入库" → LLM 输出 <<ACTION type="import" path="MANIFEST">>
  ↓
_exec_import() → 读取 manifest → 逐个文件:
  1. _do_import(path, kb)
  2. 入库路由（auto_classify 决定目标 KB）
  3. RAGWrapper.import_file() → import_documents_to_kb()
     ├─ 文档加载（PDF: PyPDFLoader + OCR 回退; 其他: TextLoader）
     ├─ 三层切分流水线（守卫栈 → 主策略 → 后处理）
     ├─ ChromaDB 写入（SM3 去重 + SQLite+HNSW 写入前备份 + 写入失败自动回滚）
     └─ KB 签名自动更新（BCE 语义质心 → jieba → 停用词过滤 → BCE 排序 → top-12）
  ↓
manifest try/finally 清空 + 临时文件清理
  ↓
返回各 KB 分布明细
```

### 6.3 SM3 去重策略

```python
import hashlib
seen = set()
for doc in all_docs:
    content = doc.page_content
    h = hashlib.new('sm3', content.encode("utf-8")).hexdigest()
    if h not in seen:
        seen.add(h)
        unique_docs.append(doc)
```

### 6.4 ChromaDB 容灾（v0.7.0+）

| 场景 | 行为 |
|------|------|
| 写入前 | `_backup_kb()` 备份 chroma.sqlite3 + HNSW 索引 |
| 写入失败 | `_restore_kb()` 自动回滚到备份 |
| 查询 HNSW 损坏 | `_try_repair_kb()` 自动清理损坏索引并重建 |
| 配置路径无效 | `load_config()` 自动指向第一个已下载的同类型模型 |

### 6.5 文本切分架构 — `engine/text_splitter.py`

**插件注册架构**：

```
文本输入
  ↓
守卫栈（多选：mermaid / code / math / table / html）
  ↓
主策略（单选：fixed / recursive / headers / sentence / semantic）
  ↓
后处理（单选/不选）
  ↓
chunks 输出
```

通过 `register_strategy()` / `register_guard()` 扩展自定义策略。

### 6.6 智能体插件系统 — `plugins/`（v2.1.0+）

针对应答链路的**可扩展旁路增强**，不侵入核心决策循环。

**插件在智能体生命周期中的位置：**

```
用户提问 → LLM 决策 → RAG 检索 → [input_return 插件注入] → LLM 生成回答 → [input_output 插件副作用] → 返回
                                  ↑ 回答前注入上下文                        ↑ 回答后执行副作用
```

**两种插件类型：**

| 类型 | 时机 | 用途 | 示例 |
|------|------|------|------|
| `input_return` | 回答生成**前** | 结果注入 LLM 上下文 | 联网搜索补充、股票行情查询 |
| `input_output` | 回答生成**后** | 副作用（不注入上下文） | 日志记录、结果缓存 |

**6 字段池（智能体裁剪传递）：**
`question` / `answer_draft` / `thinking` / `rag_context` / `session_id` / `plugin_dir`

**安全层级（5 道防线）：**

| 防线 | 机制 |
|------|------|
| 信息隔离 | 只传插件声明的 `input_fields`，其余字段不可见 |
| 文件沙箱 | 运行时数据仅限 `data/plugins/<name>/` |
| 超时熔断 | 每个插件独立 timeout，连续 3 次失败自动禁用 |
| 输出校验 | 返回 `type` 非 `markdown/json/csv/plain_text` 则丢弃 |
| SM3 签名 | 可选国密哈希校验插件代码完整性 |

**标准化接口：**

```python
class PluginBase(abc.ABC):
    async def execute(self, inputs: dict) -> dict:
        # 返回: {"type":"markdown|json|csv|plain_text","content":"...","priority":0}
```

**目录结构：**

```
rag_assistant/plugins/              ← 插件框架代码
├── base.py                         ← PluginBase 基类
├── manager.py                      ← 发现/注册/生命周期/熔断
└── builtin/                        ← 内置插件（随系统发布）
    ├── web_search/                 ← 联网搜索
    └── web_llm/                    ← 远程大模型调用

data/plugins/                       ← 运行时数据目录
├── <builtin_plugin>/config.json    ← 内置插件运行时配置
└── <user_plugin>/                  ← 用户安装插件（代码 + 数据）
    ├── plugin.json
    ├── plugin_xxx.py
    └── config.json
```

**AI 插件生成器（Web UI 插件 Tab）：**

插件 Tab 采用左右分栏布局——左侧 LLM 对话面板生成插件，右侧插件管理面板（启用/禁用/配置）。生成流程为二阶段 + 7 步校验：

```
用户描述需求 → 阶段1: LLM 评估可行性 → 确认 → 阶段2: LLM 生成代码
→ ① plugin.json 合法性 → ② Python 语法 (ast.parse)
→ ③ AST 结构检查（防 PluginBase 重定义）
→ ④ 目录规划（user→data/plugins/）→ ⑤ 原子写入 (tempfile+rename)
→ ⑥ SM3 签名 → ⑦ discover_and_register 刷新注册
```

**配置项（`llm_config.json`）：**

插件生成调用与主智能体共享 LLM 配置（model / max_tokens / timeout），仅 `temperature=0.3` 固定用于代码生成确定性。

---

## 七、部署与启动流程

### 7.1 启动模式

| 模式 | 命令 | 说明 |
|------|------|------|
| Web 界面 | `python main.py` | 默认 port 8765，自动分配 RAG 配置子进程端口 |
| CLI 对话 | `python main.py --no-web` | stdin 交互，支持 `/reset` 指令 |
| 批量处理 | `python main.py --batch --input q.json --output r.json` | 结构化输入输出 |
| 管道 JSONL | `cat queries.jsonl \| python main.py --jsonl` | 逐行处理 |
| 数据迁移 | `python main.py migrate` | 从 local-rag-builder 技能迁移知识库/模型 |

### 7.2 Windows 一键启动 — `setup.bat`

```
setup.bat
  ↓
1. 检测 Python 3.9+（缺失则自动下载安装 Python 3.11）
2. pip install -r requirements.txt（首次装依赖）
3. 通过 server.pid 杀掉旧进程
4. 启动服务器（chcp 65001 修复中文乱码）
5. 轮询端口等待就绪（自适应等待，非硬编码秒数）
6. 自动打开浏览器 http://localhost:8765
```

### 7.3 PyPI 发布

- **蓝图文件**：`blueprint_rag.json` 定义发布时包含/排除的文件
- **版本号**：`rag_assistant/__init__.py` 唯一源
- **GitHub Actions**：`permissions.attestations: write` + `skip-existing: true`

### 7.4 CLI 参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--port` | int | 8765 | Web 端口 |
| `--host` | string | 0.0.0.0 | 监听地址 |
| `--data-dir` | string | `./data` | 数据目录 |
| `--config` | string | — | 覆盖配置文件 |
| `--no-web` | flag | false | CLI 对话模式 |
| `--batch` | flag | false | 批量处理模式 |
| `--input` | string | — | JSON 输入文件 |
| `--output` | string | — | JSON 输出文件 |
| `--jsonl` | flag | false | 管道 JSONL 模式 |
| `--pidfile` | string | — | PID 文件路径 |
| `migrate` | subcommand | — | 数据迁移 |

### 7.5 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 全部成功 |
| 1 | 部分失败 |
| 2 | 严重错误 |

---

## 八、依赖与存储

### 8.1 Python 包依赖

```
langchain>=0.1                    # LangChain 框架
langchain-community>=0.3          # 社区加载器（PyPDFLoader, TextLoader）
langchain-huggingface>=0.1        # HuggingFace 嵌入
langchain-chroma>=0.1             # ChromaDB 向量存储
langchain-text-splitters>=0.3     # 文本切分
chromadb>=0.5                     # 向量数据库
sentence-transformers>=3.0        # 句子嵌入
huggingface-hub>=0.20             # HF 模型下载
modelscope>=1.15                  # ModelScope 模型下载（国内源）
openai>=1.0                       # OpenAI 兼容 API（LM Studio）
easyocr>=1.7                      # OCR（扫描版 PDF）
requests>=2.28                    # HTTP 客户端
duckduckgo_search>=4.0            # 联网搜索（可选）
jieba>=0.42                       # 中文分词（KB 签名关键词提取，v0.5.x 新增）
numpy>=1.24                       # 向量余弦相似度计算
```

### 8.2 外部服务

| 服务 | 用途 | 备注 |
|------|------|------|
| LM Studio | LLM 推理（localhost:1234） | OpenAI 兼容 API |
| Ollama | LLM 推理（localhost:11434） | /api/chat 接口 |
| ModelScope | 模型下载源（国内首选） | 外部 API |
| HuggingFace Mirror | 模型下载源（国内备用） | 外部 API |
| HuggingFace Official | 模型下载源（国际备用） | 外部 API |
| HuggingFace Direct | 模型下载源（最后兜底） | 外部 API |
| DuckDuckGo | 联网搜索 | 免费 API，无需 Key |
| Tavily | 联网搜索（备选） | 需配置 API Key |

### 8.3 存储依赖

| 存储 | 路径 | 说明 |
|------|------|------|
| ChromaDB | `data/kb/{name}/` | 向量知识库（每库一个 SQLite + HNSW 索引） |
| JSON 文件 | `data/config/rag_config.json` | 引擎配置（含 llm 子字典、prompt_slots、kb_paused） |
| JSON 文件 | `data/kb/kb_index.json` | 知识库索引 |
| JSON 文件 | `data/kb/kb_signatures.json` | KB 签名关键词 |
| JSON 文件 | `data/kb/auto_classify_rules.json` | 自动分类规则 |
| JSON 文件 | `data/models/model_index.json` | 模型索引（含 type 字段：embedding/reranker/nli） |
| JSON 文件 | `data/memory/kb_gaps.json` | 知识缺口（最多 200 条） |
| JSON 文件 | `data/memory/user_habits.json` | 用户习惯 + OCEAN 人格画像 |
| JSON 文件 | `data/prompts/custom_presets.json` | 自定义 prompt 预设 |
| TXT 文件 | `data/sessions/{id}.txt` | 短期对话 |
| TXT 文件 | `data/memory/compressed_{id}.txt` | LLM 压缩摘要 |

### 8.4 配置机制

- **配置文件**：`data/config/rag_config.json`
- **默认配置**：在 `engine/config.py` 的 `DEFAULT_CONFIG` 中硬编码
- **配置加载顺序**：
  1. `DEFAULT_CONFIG` 默认值
  2. `rag_config.json` 实际值（合并到默认上）
  3. 旧版 LLM key 自动迁移到 `llm` 子字典
  4. 模型路径自动修正（失效路径 → 第一个已下载的同类型模型）
- **极客模式**（v0.8.3）：8 区块分区编辑（Prompt / 嵌入模型&检索 / 重排序 / 切片 / 路由层 / 知识库 / LLM / 其他）

---

## 九、安全与隐私

- **无外部调用**：所有 LLM 请求发向本地 LM Studio / Ollama，不上传数据
- **本地知识库**：ChromaDB 向量库存储在本地 `data/kb/`，不离开用户机器
- **联网搜索可选**：默认关闭，需用户手动启用
- **模型本地加载**：所有模型（嵌入/路由/reranker/NLI）通过本地磁盘加载，`local_files_only=True`
- **自包含 vendor**：`vendor/` 嵌入 bs4 / pypdf / markdownify 等第三方库，零外部 pip 安装也可运行

---

## 十、版本演进要点

| 版本 | 新增/变更要点 |
|------|-------------|
| v2.1.0b2 | AI 插件生成器（二阶段 LLM + 7 阶段校验管道）；web_llm 多 profile 配置系统；setup.bat HNSW 修复 |
| v2.1.0b1 | 智能体插件系统（PluginBase + PluginManager + 5 道防线）；内置联网搜索插件；插件 Web UI 管理面板 |
| v2.0.0b1 | 1.x → 2.x HNSW 索引引擎更换；Chroma 适配器重构；setup.bat 全量重建提示 |
| v1.8.0 | 外部 API 端口独立（8767）；引擎独立化（engine/ 副本自包含） |
| v1.7.0 | PROTOCOL 协议升级；KB 签名多向量路由 |
| v1.5.0b1 | Web 配置页面内嵌（iframe 模式）；双端口架构 |
| v1.3.0-beta | 双面板 Web UI（配置 + 对话） |
| v1.2.0 | 组合检索（LLM 分词 + entities × attrs 穷举展开） |
| v1.1.0 | 四层记忆系统（短时/压缩/习惯/缺口） |
| v1.0.0 | 从 local-rag-builder 仓库外项目独立为正式版 |
| v0.9.5 | README 架构图补 NLI；NLI 模型探测遍历所有源修复 |
| v0.9.0 | NLI 三向分类器；网络探测并行化；Config 自动修正模型路径；组合查询两两配对 + 中文逗号 |
| v0.8.0 | KB 暂停写入；历史对话隔离；引用校验；OCR 触发条件修复 |
| v0.7.0 | KB 签名新流程（BCE→jieba→停用词→BCE排序）；精排/路由解耦；ChromaDB 容灾 |
| v0.6.0 | 用户习惯画像系统（OCEAN + 语言分析）；Prompt 自定义预设 |
| v0.5.0 | 出库路由彻底弃用 reranker，改用嵌入模型余弦相似度；KB 签名反哺 |
| v0.4.0 | 入库路由独立（kb.auto_classify）；多知识库主开关（kb.enabled）|
| v0.3.0 | ChromaDB 崩溃修复；状态机解析器重写；MANIFEST 批量导入 |
| v0.2.0 | PROTOCOL.md；llms.txt；--batch / --jsonl 模式 |
| v0.1.0 | 从 local-rag-builder v1.5.0 抽取为独立智能体 |
