
<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# local-rag-builder 架构与规范体系文档

> 完整解读最新 v1.1.3 版的架构设计、六阶段流水线（路由 → 检索 → Rerank）、三层切分（GuardStack + 主策略 + 后处理）、下载系统与插件体系
> 更新日期：2026-06-21（v1.1.3）

---

## 一、系统概览

local-rag-builder 是一个**本地 RAG 一键搭建工具集**，当前架构演进为**六阶段流水线**：输入源 → 切分 → 入库（含守卫栈）→ 路由 → 检索 → Rerank（重排序）。

```
用户部署
  → 环境检测（rag_env_setup: Python 版本 / 缺失包 / GPU / 镜像源）
    → 模型管理（embedding_model_manager: 多源下载 / 重试 / 校验 / 路径修正）
      → 文档处理
           → 文本切分（text_splitter: 守卫栈 + 5 策略 + 后处理 + 插件注册）
           → 向量化入库（knowledge_base_manager: 多知识库 / 自动分类规则 / KB 专属嵌入）
      → RAG 查询
           → 路由层（router: 硬编码 → 语义回退 → 广播）
           → 检索（rag_core: 相似度搜索）
           → 重排序（reranker: 模型 / 规则 / 混合）
      → 结果输出
           → 技能模式（rag_skill: 纯检索，供智能体调用）
           → 独立模式（rag_standalone: 检索 + 外部 LLM 全链路）
           → Web 面板（rag_web_ui: 可视化 / 极客模式 / 排序规则编辑器）
```

### 1.1 三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | SKILL.md + references/*.md + CLI + HTML 设置面板 | 人类可读的文档、命令行交互、可视化配置 |
| **业务层** | rag_core / text_splitter / knowledge_base_manager / embedding_model_manager / router / reranker / rag_env_setup / prompt_manager / rag_skill / rag_standalone / rag_setup_orchestrator | RAG 流程的核心逻辑 |
| **数据层** | config.py（配置管理）+ utils.py（工具函数）+ data/ 目录（持久化） | 配置、工具函数、知识库/模型/Prompt 存储 |

### 1.2 目录结构

```
local-rag-builder/
├── SKILL.md                    # 主文件（≤230行，渐进式入口）
├── _meta.json                  # 7 字段元数据
├── references/                 # 渐进式文档
│   ├── guide.md                # 完整使用教程
│   ├── architecture.md         # 架构设计
│   ├── permissions.md          # 权限说明
│   ├── changelog.md            # 版本更新日志
│   ├── examples.md             # 使用示例
│   ├── faq.md                  # 常见问题
│   ├── commands.md             # 命令速查表
│   ├── data-directory.md       # 数据目录结构
│   ├── custom-extensions.md    # 插件注册指南
│   ├── setup-spec.md           # 32 参数 + 6 阶段流水线规范
│   ├── llm-setup.md            # LLM 接入指南（独立模式）
│   └── test-report.md          # 功能测试报告
└── scripts/                    # 核心脚本
    ├── config.py               # 统一配置管理：8+ 个 section 默认值 + 持久化 + 合并
    ├── utils.py                # 工具函数：目录管理、pip 操作、文件安全读写
    ├── rag_core.py             # 共享核心（被其他模块导入，不直接运行）
    ├── text_splitter.py        # 三层切分流水线：5 策略 + GuardStack + 后处理 + 插件注册
    ├── knowledge_base_manager.py  # 知识库管理：创建/删除/切换/自动分类/档案导入/KB 专属嵌入
    ├── embedding_model_manager.py # 嵌入模型管理：多源下载/完整性校验/路径修正/Rerank 模型独立管理
    ├── router.py               # 路由层：硬编码路由 → 语义回退（FallbackRouter）→ 广播 + KB 签名自动归纳
    ├── reranker.py             # 重排序层：ModelReranker / RuleReranker / HybridReranker 统一入口
    ├── rag_env_setup.py        # 环境检测与修复：Python 版本/pip/必需包/GPU/镜像源
    ├── rag_skill.py            # [技能模式] 纯检索接口：供智能体调用，无需 LLM
    ├── rag_standalone.py       # [独立模式] 检索+LLM：全链路 RAG 问答
    ├── rag_web_ui.py           # Web 可视化设置面板：HTTP 服务器 + 内嵌 HTML，11 个设置卡片
    ├── rag_setup_orchestrator.py # 搭建编排器：交互式 SetupHook 钩子系统，引导完成全流程
    └── prompt_manager.py       # Prompt 模板管理：持久化 + 运行时编辑 + 占位符校验
```

### 1.3 数据目录结构

```
skills/.standardization/local-rag-builder/data/
├── kb/                         # 向量知识库目录
│   ├── default/                # 默认知识库
│   ├── <kb_name>/              # 各知识库（自动/手动创建）
│   ├── kb_index.json           # 知识库索引
│   ├── kb_signatures.json      # KB 语义签名（路由层使用）
│   ├── kb_models.json          # KB 专属嵌入模型配置
│   └── auto_classify_rules.json # 自动分类规则
├── models/                     # 下载的嵌入模型（按模型 ID 子目录）
│   └── model_index.json        # 模型索引
├── model_downloads/            # 下载中间缓存（三源共用的下载目标）
├── prompts/                    # Prompt 模板
│   └── custom_prompt_template.txt
├── config/                     # 运行时配置
│   └── rag_config.json
├── output/                     # 导出产物
├── cache/                      # 下载缓存（HF Hub / ModelScope）
├── logs/                       # 执行日志（含 pip 安装日志）
└── config_templates/           # 用户保存的配置模板
```

---

## 二、十大核心模块

### 2.1 模块 A：环境检测与修复（rag_env_setup.py）

**职责**：检测运行环境并自动修复缺失的依赖。

| 功能 | 实现 | 说明 |
|------|------|------|
| Python 版本检测 | `check_python_version()` | 建议 3.8-3.11 |
| pip 可用性检查 | `check_pip()` | bool |
| 已安装包列表 | `list_installed()` | dict[package_name → version]，统一 `_`→`-` |
| 缺失包检测 | `check_missing()` | (required_missing, optional_missing) |
| 自动安装 | `install_packages(packages)` | 流式输出进度，自动 `--no-deps` 防 chromadb 锁死 |
| 虚拟环境创建 | `create_venv(path)` | venv python 路径 或 None |
| GPU 检测 | `check_torch_gpu()` | (cuda_available, gpu_name) |
| pip 锁清理 | `cleanup_pip_locks()` | 自动清理 stale pip 锁文件 |
| 镜像选择 | `--mirror` | 支持 aliyun/tencent/tsinghua/ustc |

**依赖检测范围**：
- **必需包（9 个）**：langchain, langchain-community, langchain-huggingface, langchain-chroma, langchain-text-splitters, chromadb, sentence-transformers, huggingface-hub, modelscope
- **可选包（6 个）**：unstructured, pdfplumber, openai, torch, fastapi, uvicorn

### 2.2 模块 B：嵌入模型管理（embedding_model_manager.py）

**职责**：嵌入模型与 Rerank 模型的完整生命周期管理，两类模型独立管理。

#### 多源下载优先级

| 优先级 | 源名称 | 方法 | 说明 |
|:------:|:------:|:----:|------|
| 1 | modelscope | `_download_with_modelscope()` | ModelScope 国内镜像，snapshot_download |
| 2 | hf_mirror | `_download_with_hf_mirror()` | HuggingFace 国内镜像 hf-mirror.com |
| 3 | hf_official | `_download_with_hf_official()` | HuggingFace 官方源 huggingface.co |
| 4 | hf_direct | `_download_with_hf_direct()` | 逐文件 hf_hub_download，避免子进程 \r 死锁 |

**说明**：
- 三源自动轮换，每个源最多 3 次重试，30 分钟硬超时
- 0KB 持续 3 分钟自动切换下一源
- 断点续传：`.incomplete` 标记 + blobs 缓存检测，下载前自动清理残留
- 后台下载线程：旋转动画 + 实时下载速度显示

#### 推荐嵌入模型列表

| 模型 ID | 大小 | 说明 |
|---------|:----:|------|
| BAAI/bge-small-zh-v1.5 | 130MB | 轻量中文嵌入（推荐） |
| BAAI/bge-base-zh-v1.5 | 400MB | 中等中文嵌入 |
| shibing624/text2vec-base-chinese | 400MB | CPU 友好中文嵌入 |
| maidalun1020/bce-embedding-base_v1 | 800MB | 网易 BCEmbedding |
| sentence-transformers/all-MiniLM-L6-v2 | 80MB | 英文嵌入（超轻量） |
| BAAI/bge-large-zh-v1.5 | 1300MB | 高精度中文嵌入（大） |

#### 推荐 Rerank / 路由模型列表（v1.1 新增）

| 模型 ID | 大小 | 说明 |
|---------|:----:|------|
| BAAI/bge-reranker-v2-m3 | 1136MB | 多语言通用路由/rerank（推荐） |
| BAAI/bge-reranker-large | 1120MB | 中英通用 rerank |
| BAAI/bge-reranker-base | 556MB | 轻量 rerank（CPU 友好） |

#### 通用路径查找机制（嵌入 + Rerank 共用）

内容感知 + 名称相似度评分，不依赖特定变形模式：

```python
def _find_actual_model_path(model_id, download_dir):
    """通用模型路径查找。不依赖任何固定变形模式"""
    target_norm = _normalize(model_id)
    for root, dirs, _ in os.walk(download_dir):
        for d in dirs:
            dir_norm = _normalize(d)
            score = _name_similarity(target_norm, dir_norm)
            if score > best_score and _is_model_dir(candidate_path):
                best_match = candidate_path
    return best_match
```

**关键函数**：

| 函数 | 说明 | 返回 |
|------|------|------|
| `_normalize(s)` | 去除非字母数字字符，归一小写 | str |
| `_name_similarity(a, b)` | 名称相似度评分（0-100） | float |
| `_is_model_dir(path)` | 内容感知：检查目录是否包含模型标志文件 | bool |
| `_check_integrity(path)` | 验证模型文件完整性 | (ok, detail) |
| `download_model(model_id, model_type)` | 四源下载 + 重试 + 校验 + 路径修正；model_type 区分 embedding/rerank | dict |
| `verify_model(path)` | 验证模型可用性 | (ok, detail) |
| `list_downloaded_models()` | 列出已下载模型 | list |
| `remove_model(model_id)` | 删除模型 | (ok, msg) |
| `get_model_path(model_id)` | 通用路径查找 | path 或 None |

### 2.3 模块 C：文本切分（text_splitter.py）

**职责**：三层切分流水线架构，将文档切割为语义完整的块。

#### 三层流水线架构

```
原始文本 → [守卫栈(多选)] → [主策略(单选)] → [后处理(单选/不选)] → 最终 chunks
```

| 阶段 | 可选项 | 数量 |
|:----:|--------|:----:|
| **GuardStack 守卫栈** | mermaid / code / math / table / html | 可链式选多个，通过插件注册可扩展 |
| **主策略** | fixed / recursive / headers / sentence / semantic | 单选，通过 `StrategyPlugin` 可扩展 |
| **后处理子切** | recursive / fixed / semantic | 单选或不选，metadata 白名单继承 |

#### 五种主策略

| 策略 | 函数 | 原理 | 适用场景 |
|:----:|:----:|:----:|:--------:|
| **固定窗口** | `split_fixed_size()` | 按固定字符数切分，可设重叠 | 长度均匀的清洗文本 |
| **递归切分** | `split_recursive()` | 按优先级尝试不同分隔符 | 未知/混合格式文档（默认） |
| **层级/标题切分** | `split_by_headers()` | 基于 Markdown 标题切分，保留结构元数据 | Markdown 结构化文档 |
| **按句切分** | `split_by_sentence()` | 以句子为单位，支持 `language` 参数及自定义分隔符 | 短句文档、证据抽取 |
| **语义切分** | `split_semantic()` | 计算相邻句子相似度，在主题边界处切分 | 长叙述性文本 |

#### 守卫栈（GuardStack）

5 个内置守卫，链式保护与还原，唯一前缀 `__GUARD_NAME_X__` 防止冲突：

| 守卫 | 正则 | 保护内容 |
|:----:|:----:|----------|
| mermaid | ```mermaid\n...\n``` | Mermaid 流程图 |
| code | ```\n...\n``` | 通用代码块 |
| math | $$...$$ / $...$ | LaTeX 公式 |
| table | Markdown 表格 | 表格结构 |
| html | `<...>` 标签 | HTML 标签 |

#### 插件注册

```python
from text_splitter import register_strategy, register_guard, StrategyPlugin, GuardPlugin, Guard

# 自定义切分策略
def my_splitter(text, my_param=100, **kwargs):
    from langchain_core.documents import Document
    return [Document(page_content=text)]

register_strategy(StrategyPlugin(
    "my_split", "我的自定义切分", my_splitter,
    config_schema={
        "my_param": {"type": "int", "label": "参数名", "default": 100, "min": 1, "max": 1000},
    },
    default_config={"my_param": 100},
))

# 自定义守卫
my_guard = Guard("my_guard", re.compile(r'```special\n[\s\S]*?\n```'))
register_guard(GuardPlugin("my_guard", "保护特殊代码块", my_guard))
```

注册后自动出现在 Web UI 的下拉列表中，配置表单根据 `config_schema` 动态渲染。

### 2.4 模块 D：知识库管理（knowledge_base_manager.py）

**职责**：多知识库的创建、删除、切换、文档入库、自动分类规则、KB 专属嵌入模型。

| 函数 | 说明 |
|------|------|
| `list_knowledge_bases()` | 列出所有知识库（名称/描述/文档数） |
| `create_knowledge_base(name, desc)` | 创建新知识库 |
| `delete_knowledge_base(name)` | 删除知识库（含向量化数据） |
| `get_kb_vectorstore(kb_name, embeddings)` | 获取知识库向量存储 |
| `add_documents_to_kb(kb_name, docs, embeddings)` | 文档入库（向量化 + 持久化） |
| `auto_classify(content, rules)` | 根据规则自动分类到知识库 |
| `set_classify_rule(kb_name, keywords, desc)` | 设置自动分类规则 |
| `remove_classify_rule(kb_name)` | 移除分类规则 |
| `get_kb_stats()` | 获取知识库统计信息 |
| `load_documents_from_file(filepath)` | 从文件加载文档 |
| `load_documents_from_directory(dirpath)` | 从目录批量加载文档 |
| `get_kb_model(kb_name)` | 获取知识库专属嵌入模型路径 |
| `set_kb_model(kb_name, model_id)` | 设置知识库专属嵌入模型 |

#### 自动分类规则

支持**关键词匹配 + 扩展名匹配**双模式，Web UI 提供可视化管理（添加/编辑/删除/重置）。v1.1 增强：路由层会复用 KB 的 auto_classify 规则进行硬编码路由。

#### KB 专属嵌入模型（v1.0 新增）

每个知识库可独立选择嵌入模型，未指定时回退全局默认。Web UI 知识库管理面板新增模型下拉选择器。

### 2.5 模块 E：路由层（router.py）【v1.1 新增】

**职责**：用户查询自动路由到最相关的知识库，三阶段决策。

```
用户查询
  ↓
① hardcoded_route(query)
  → 遍历 KB 自动分类规则，关键词命中 → 直接路由到该 KB
  ↓（未命中）
② FallbackRouter.route(query × KB 签名)
  → BGE-Reranker 模型对 query 和每个 KB 的语义签名打分
  → 最高分 ≥ threshold（默认 0.3）→ 路由到最佳 KB
  ↓（未命中或模型未就绪）
③ broadcast_route(query, all_kbs)
  → 全量广播到所有有数据的 KB
```

#### 核心类和方法

| 组件 | 说明 |
|:----|:-----|
| `hardcoded_route(question)` | 硬编码路由：复用 KB 的 auto_classify 规则，关键词匹配 |
| `FallbackRouter(model_path)` | 语义回退路由：加载 CrossEncoder 模型，query × KB 签名打分 |
| `FallbackRouter.score(query, signatures)` | 对每个 KB 签名打分 |
| `FallbackRouter.route(query, signatures, threshold)` | 选择最高分 KB（≥ threshold 才返回） |
| `broadcast_route(question, kb_names)` | 全量广播 |
| `route_query(question)` | **主入口**：自动执行①→②→③，返回 `{kb_names, method, kb_scores}` |

#### KB 签名系统

| 函数 | 说明 |
|:----|:-----|
| `induce_kb_signature(kb_name, chunks)` | 从文档内容自动归纳签名（词频统计 + 代表性片段） |
| `update_kb_signature(kb_name, chunks)` | 入库时自动更新签名 |
| `rebuild_all_signatures()` | 重建所有 KB 签名 |
| `list_kb_signatures()` | 列出所有 KB 签名 |

签名以 `data/kb/kb_signatures.json` 持久化，入库时自动更新。

### 2.6 模块 F：重排序层（reranker.py）【v1.1 新增】

**职责**：对检索结果进行二次排序，三种模式可选。

#### 三种模式

| 模式 | 类 | 原理 |
|:----:|:---|:-----|
| **model** | `ModelReranker` | 加载 CrossEncoder 对 query 和每个文档打分排序 |
| **rule** | `RuleReranker` | 按排序规则（权重/时效/来源/关键词）计算综合得分排序 |
| **hybrid** | `HybridReranker` | 模型先打分 → 规则再微调排序，双分叠加 |

#### 统一入口

```python
class Reranker:
    """根据 config.reranker.mode 自动选择 ModelReranker / RuleReranker / HybridReranker"""
    def rerank(self, query, docs, top_k=None) -> list[(doc, score)]
```

出错时自动降级为原序返回（保底策略）。

#### 排序规则类型（RuleReranker）

| 规则类型 | 参数 | 说明 |
|:--------:|:----|:-----|
| `score_weight` | embedding_score, rerank_score | 嵌入检索分和重排分的权重叠加 |
| `recency` | field, days_halflife | 基于时间衰减（半衰期天数）的时效性加分 |
| `source_weight` | sources: {pattern: weight} | 来源优先级加权 |
| `boost_keywords` | keywords, boost | 内容含关键词时加分 |

规则通过 Web UI 覆盖层弹窗管理（新增/编辑/删除），以 `config.reranker.sort_rules` 持久化。

### 2.7 模块 G：共享核心（rag_core.py）

**职责**：嵌入模型初始化、向量检索、路由集成、Rerank 集成，被 `rag_skill.py` / `rag_standalone.py` 调用。

| 函数 | 说明 | 关键参数 |
|------|------|----------|
| `get_embeddings(model_path, device, kb_name)` | 获取嵌入模型实例，支持 KB 专属模型 | device: auto/cpu/cuda |
| `retrieve_documents(query, kb_name, k, score_threshold, embeddings)` | 检索相似文档 | k=3, score_threshold 可选 |
| `build_context(docs)` | 从检索结果构建上下文 | 含引用来源标记 |
| `retrieve_context(question, kb_name, ...)` | **核心入口**：路由 → 检索 → Rerank 全链路 | 自动集成 `router.route_query()` 和 `Reranker.rerank()` |
| `format_skill_output(question, kb_name, ...)` | 格式化 JSON 输出（技能模式用） | 含 context + source_docs + routing_info |
| `import_documents_to_kb(file_path, kb_name, embeddings, splitter_config)` | 文档切分 + 入库 | 自动合并元数据 + 更新 KB 签名 |

#### 查询数据流（v1.1）

```
用户问题
  ↓
路由层: route_query(question)
  → {kb_names, method, kb_scores}
  ↓
检索: embeddings.encode(question) → Chroma.similarity_search(k=...)
  ↓
Rerank: Reranker.rerank(question, docs, top_k)
  ↓
build_context(reranked_docs) → context 字符串
  ↓
prompt_template.format(context=context, question=question)
  ↓
LLM.invoke(prompt) → 原始回答（独立模式）
```

### 2.8 模块 H：Prompt 管理（prompt_manager.py）

**职责**：Prompt 模板的持久化、自定义、重置、占位符校验。

| 函数 | 说明 |
|------|------|
| `load_template()` | 加载持久化模板，不存在则返回默认 |
| `save_template(content)` | 保存自定义模板（原子写入） |
| `reset_template()` | 重置为默认模板 |
| `get_default_template()` | 获取默认模板 |
| `build_prompt(context, question, template)` | 构建最终 Prompt |
| `list_saved_templates()` | 列出所有已保存模板 |

**默认模板**：
```
基于以下资料回答问题。如果资料中没有相关信息，请说"不知道"。

资料：
{context}

问题：{question}

请用 Markdown 格式输出，并在末尾附上引用片段编号。

回答：
```

**必需占位符**：`{context}`（检索上下文）、`{question}`（用户问题）

### 2.9 模块 I：统一配置管理（config.py）

**职责**：集中管理所有运行时配置，支持 CLI 和 Web 面板修改。

**8 个配置 Section**（v1.1 增为 8+）：

| Section | 关键参数 | 默认值 |
|:-------:|----------|:------:|
| `embedding` | model_name, model_path, device, normalize_embeddings | bge-small-zh-v1.5, auto, true |
| `input_sources` | enable_pdf, enable_ocr, enable_html2md, pdf_backend | 全 false, pypdf |
| `splitting` | strategy, chunk_size, chunk_overlap, separators, guards, postprocess, strategy_overrides | recursive, 500, 50 |
| `router` | enabled, fallback.enabled, fallback.model_path, fallback.min_score_threshold, fallback.auto_update_signatures | 全开启, 0.3 |
| `reranker` | enabled, mode, model_path, top_k, sort_rules | mode=model, top_k=5 |
| `retrieval` | k, score_threshold, search_type | 3, null, similarity |
| `llm` | base_url, api_key, temperature, max_tokens, model_name | localhost:1234, 0.1, 512 |
| `kb` | active_kb, auto_classify | default, false |
| `prompt` | template_file | default_template.txt |

### 2.10 模块 J：双模式入口

#### 技能模式（rag_skill.py）

纯检索接口，供智能体调用，**不需要 LLM 服务**。

```bash
# 检索知识库
python scripts/rag_skill.py --query "问题"
python scripts/rag_skill.py --query "问题" --json
python scripts/rag_skill.py --query "问题" --kb art
```

#### 独立模式（rag_standalone.py）

检索 + 外部 LLM 全链路，需自行部署 LLM 服务（LM Studio / Ollama / vLLM）。

```bash
# 交互式 CLI
python scripts/rag_standalone.py

# 单次问答
python scripts/rag_standalone.py --query "问题"
python scripts/rag_standalone.py --query "问题" --json

# 文档入库
python scripts/rag_standalone.py --import-file doc.md

# 查看 LLM 接入指南
python scripts/rag_standalone.py --llm-help
```

#### 搭建编排器（rag_setup_orchestrator.py）【v1.1 新增】

交互式钩子系统，引导用户逐步完成 RAG 搭建全流程（环境 → 模型 → 文档 → 检索验证），每个阶段可插拔。

---

## 三、核心设计原则

### D1: 双模式架构（技能模式 vs 独立模式）

本 skill 设计为两种运行模式，核心理念是 **技能模式只做检索，生成归调用方**：

| 模式 | 入口 | 谁生成回答 | 外部 LLM | 适用场景 |
|:----:|:----:|:---------:|:--------:|:--------:|
| **技能模式**（默认） | `rag_skill.py` | 智能体根据 context 自行回答 | 不需要 | 在智能体平台内使用 |
| **独立模式** | `rag_standalone.py` | 外部 LLM 服务 | 需用户部署 | 单独跑 Python 脚本 |

**技能模式下**，`rag_skill.py --query "问题"` → 返回 context + source_docs，智能体根据检索结果组织回答。

**独立模式下**，`rag_standalone.py --query "问题"` → 检索 + 调用外部 LLM 全链路。

**LLM 推荐（独立模式）**：
- **LM Studio**（图形界面，适合新手）→ 下载 lmstudio.ai，加载模型后 Start Server
- **Ollama**（命令行，适合开发者）→ `ollama run qwen2.5:7b`
- **vLLM**（生产高性能）→ `python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen-7B`

### D2: 三阶段路由决策

查询流程采用「硬编码 → 语义回退 → 全量广播」三阶段：

```
hardcoded (关键词规则) → 命中 → 单 KB 精确路由
        ↓ 未命中
fallback (语义模型 × KB 签名) → 命中 → 最佳 KB 路由
        ↓ 未命中或模型异常
broadcast → 全量广播
```

路由 + 检索 + Rerank 构成完整查询流水线，可在配置中分别启用/关闭。

### D3: 松耦合模块

十大核心模块各司其职，模块间通过 `config.py` + 函数参数传递数据，无循环依赖。每个模块可独立升级/替换，互不影响。

### D4: 自包含输出

Web 设置面板、CLI 交互、HTML 报表均为自包含，无外部依赖。无需部署服务器，打开即用。

### D5: 结构化接口

所有脚本支持 `--json` 参数输出标准 JSON，供智能体集成调用。

### D6: 路径修正通用化

嵌入模型路径查找使用内容感知方案，不依赖特定变形模式。

### D7: 可扩展插件体系

切分策略和守卫通过 `StrategyPlugin`/`GuardPlugin` 注册，config_schema 声明配置表单。Web UI 根据已注册的插件动态渲染下拉列表和配置表单。

### D8: 模型分类管理

嵌入模型与 Rerank 模型独立管理，各有独立推荐列表和下载入口，Web UI 分在下拉选择器中展示。

---

## 四、交互方式

### 4.1 命令行接口

| 脚本 | 功能 | 核心参数 |
|------|------|----------|
| `rag_env_setup.py` | 环境检测与修复 | `--auto-install`, `--check-only`, `--cleanup-locks`, `--mirror`, `--dry-run` |
| `embedding_model_manager.py` | 嵌入模型管理 | `--download`, `--list`, `--check`, `--remove` |
| `text_splitter.py` | 文本切分（三层流水线） | `--strategy`, `--guard`, `--secondary`, `--chunk-size`, `--input`, `--list-strategies` |
| `router.py` | 路由层管理 | `--route`, `--signatures`, `--rebuild-signatures`, `--update-signature`, `--json` |
| `reranker.py` | Rerank 测试 | `--query`, `--docs`, `--mode`, `--top-k`, `--list-rules`, `--json` |
| `rag_skill.py` | **[技能模式] 纯检索** | `--query`, `--kb`, `--json`, `--no-router`, `--no-reranker`, `--show-routing` |
| `rag_standalone.py` | **[独立模式] 检索+LLM** | `--query`, `--kb`, `--llm-help`, `--json`, `--no-router`, `--no-reranker` |
| `rag_web_ui.py` | Web 配置界面 | `--port`, `--gen-html` |
| `rag_setup_orchestrator.py` | 搭建编排器 | 交互式 SetupHook 引导 |
| `prompt_manager.py` | Prompt 管理 | `--set`, `--show`, `--reset` |
| `knowledge_base_manager.py` | 知识库管理 | `--create`, `--import`, `--list`, `--delete`, `--set-rule`, `--classify`, `--kb-list`, `--import-file` |

### 4.2 Web 可视化面板（rag_web_ui.py）

面板按以下顺序排列 11 个设置卡片：

| 面板区域 | 可调参数 |
|:--------:|----------|
| 状态卡片 | 嵌入模型数、知识库数、文档块数 |
| 输入源 | PDF/OCR/HTML→MD 开关 + 后端选择 |
| Prompt 模板 | 完整模板编辑区（含重置按钮） |
| 嵌入模型 | 推荐嵌入模型列表 → 单选下拉 + 下载状态 |
| GuardStack 守卫栈 | 5 守卫开关卡片，链式保护 |
| 文本切分主策略 | 5 策略动态表单（根据所选策略展示对应参数） + 后处理子切 |
| 检索参数 | K 值、相似度阈值 |
| LLM 设置 | 模式选择器（技能/独立）+ API 地址 + 温度 + 连接验证 |
| 知识库概览 | 列表 + 文档数 + 自动分类规则编辑器（覆盖层弹窗） |
| 路由层 | 启用开关 + 回退语义路由模型下拉 + 最低分 threshold + KB 签名管理 |
| Rerank 层 | 启用开关 + 模式选择 + 模型下拉 + top_k + 排序规则编辑器（覆盖层弹窗） |
| 极客模式 | 原始配置 JSON 编辑器 + 配置模板保存/加载/删除 |

### 4.3 API 端点

| 端点 | 方法 | 说明 |
|:----:|:----:|------|
| `/api/override` | POST | 策略级参数覆盖 |
| `/api/input-source` | POST | 输入源配置 |
| `/api/config/raw` | GET/POST | 原始配置 JSON |
| `/api/template/*` | GET/POST/DELETE | 配置模板管理 |
| `/api/rules/*` | GET/POST/DELETE | 自动分类规则管理 |
| `/api/mode` | GET/POST | 模式切换 |
| `/api/kb-model` | POST | 设置 KB 专属嵌入模型 |
| `/api/kb-models` | GET | 列出可用嵌入模型 |
| `/api/router/config` | GET/POST | 路由层配置 |
| `/api/reranker/config` | GET/POST | Rerank 层配置 |
| `/api/reranker/rules` | GET/POST/DELETE | 排序规则管理 |
| `/api/reranker/status` | GET | Rerank 状态查询 |

### 4.4 结构化 JSON 接口

```bash
# 环境检测
python scripts/rag_env_setup.py --json

# 嵌入模型列表
python scripts/embedding_model_manager.py --list --json

# 路由层签名
python scripts/router.py --signatures --json

# 路由测试
python scripts/router.py --route "问题" --json

# Rerank 测试
python scripts/reranker.py --query "问题" --docs "doc1" "doc2" --mode hybrid --json

# 知识库列表
python scripts/knowledge_base_manager.py --list --json

# 技能模式检索
python scripts/rag_skill.py --query "问题" --json

# 独立模式问答
python scripts/rag_standalone.py --query "问题" --json

# 切分结果
python scripts/text_splitter.py --input doc.md --strategy headers --json
```

---

## 五、对外依赖

| 包 | 用途 | 必需？ |
|:--:|:----:|:------:|
| langchain | RAG 流程编排 | 必需 |
| langchain-community | 文档加载器 / LLM 封装 | 必需 |
| langchain-huggingface | HuggingFace 嵌入模型接口 | 必需 |
| langchain-chroma | Chroma 向量数据库 | 必需 |
| langchain-text-splitters | 文本切分器 | 必需 |
| chromadb | 向量数据库核心 | 必需 |
| sentence-transformers | BGE 等嵌入模型 | 必需 |
| huggingface-hub | 模型下载（hf_hub_download） | 必需 |
| modelscope | ModelScope 国内下载 | 必需 |
| transformers | Rerank 模型加载（AutoModelForSequenceClassification） | 必需（路由+Rerank） |
| torch | PyTorch 后端（GPU 加速） | 推荐 |
| openai | OpenAI 兼容 API 连接 | 可选（独立模式） |
| unstructured[pdf] | PDF 文档加载 | 可选 |
| pdfplumber | 精确 PDF 表格提取 | 可选 |
| fastapi + uvicorn | API 服务封装 | 可选 |

---

## 六、版本历史

| 版本 | 日期 | 核心变化 |
|:----:|:----:|:--------|
| 0.1.0 | 2026-06-06 | 初始版本：环境检测 / 模型下载 / 切分 / 知识库 / Prompt / Web UI / CLI |
| 0.2.0 | 2026-06-06 | 模型路径查找通用化、exception 加固 |
| 0.3.0 | 2026-06-06 | rag_core 缺失修复、双模式支持 |
| 0.4.0 | 2026-06-06 | pip 锁自动清理、镜像选择、流式输出、反锁死策略 |
| 0.5.0 | 2026-06-06 | 模式切换配置、pip 流水线全面加固 |
| 1.0.0 | 2026-06-07 | 三层切分流水线重写、GuardStack + 后处理、插件注册、Web UI 大改、双入口、KB 专属嵌入 |
| **1.1.0** | **2026-06-21** | **路由层（HardcodedRouter + FallbackRouter + Broadcast）、Rerank 层（Model + Rule + Hybrid）、三源下载系统 + 断点续传、排序规则编辑器、Web UI 重排、KB 签名自动归纳** |
| 1.1.3 | 2026-06-21 | 文档描述与实际代码对齐、changelog 补充 rerank 记录 |

---

> 本文档基于 local-rag-builder v1.1.3 的 SKILL.md + references/ + 核心脚本综合分析整理。
