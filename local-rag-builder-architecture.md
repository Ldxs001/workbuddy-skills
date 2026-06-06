# local-rag-builder 架构与规范体系文档

> 完整解读 v0.2.0 版的架构设计、6 种切分策略、多知识库管理与嵌入模型管理
> 生成时间：2026-06-06（v0.2.0 最新更新）

---

## 一、系统概览

local-rag-builder 是一个 **本地 RAG 一键搭建工具集**，围绕以下闭环运行：

```
用户部署
  → 环境检测（rag_env_setup: Python 版本 / 缺失包 / GPU）
    → 嵌入模型管理（embedding_model_manager: 多源下载 / 重试 / 校验 / 路径修正）
      → 文档处理
           → 文本切分（text_splitter: 6 种策略 + 组合）
           → 向量化入库（knowledge_base_manager: 多知识库 / 自动分类）
      → RAG 问答（rag_core: embeddings + Chroma 检索 + LLM 调用）
        → 结果输出（rag_interface: CLI 交互 / rag_web_ui: 可视化面板）
```

### 1.1 三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | SKILL.md + references/*.md + CLI + HTML 设置面板 | 人类可读的文档、命令行交互、可视化配置 |
| **业务层** | rag_core / text_splitter / knowledge_base_manager / embedding_model_manager / rag_env_setup / prompt_manager | RAG 流程的核心逻辑 |
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
│   └── antipatterns.md         # 反模式
└── scripts/                    # 核心脚本
    ├── config.py               # 统一配置管理：6 个 section 默认值 + 持久化 + 合并
    ├── utils.py                # 工具函数：目录管理、pip 操作、文件安全读写
    ├── rag_core.py             # RAG 核心引擎：嵌入→检索→LLM 调用
    ├── text_splitter.py        # 文本切分引擎：6 种策略 + 组合切分
    ├── knowledge_base_manager.py  # 知识库管理：创建/删除/切换/自动分类/档案导入
    ├── embedding_model_manager.py # 嵌入模型管理：多源下载/完整性校验/路径修正
    ├── rag_env_setup.py        # 环境检测与修复：Python 版本/pip/必需包/GPU
    ├── rag_interface.py        # 交互式 CLI：支持 /prompt、/kb、/model 等命令
    ├── rag_web_ui.py           # Web 可视化设置面板：HTTP 服务器 + 内嵌 HTML
    └── prompt_manager.py       # Prompt 模板管理：持久化 + 运行时编辑 + 占位符校验
```

### 1.3 数据目录结构

```
skills/.standardization/local-rag-builder/data/
├── kb/                         # 向量知识库目录
│   ├── default/                # 默认知识库
│   ├── art/                    # 艺术类资料（自动分类）
│   ├── politics/               # 政治类资料（自动分类）
│   └── kb_index.json           # 知识库索引
├── models/                     # 下载的嵌入模型
│   └── model_index.json        # 模型索引
├── prompts/                    # Prompt 模板
│   └── custom_prompt_template.txt
├── config/                     # 运行时配置
│   └── rag_config.json
├── output/                     # 导出产物
├── cache/                      # 下载缓存
└── logs/                       # 执行日志
```

---

## 二、七大核心模块

### 2.1 模块 A：环境检测与修复（rag_env_setup.py）

**职责**：检测运行环境并自动修复缺失的依赖。

| 功能 | 实现 | 输出 |
|------|------|------|
| Python 版本检测 | `check_python_version()` | (ok, version, message) — 建议 3.8-3.11 |
| pip 可用性检查 | `check_pip()` | bool |
| 已安装包列表 | `list_installed()` | dict[package_name → version] |
| 缺失包检测 | `check_missing()` | (required_missing, optional_missing) |
| 自动安装 | `install_packages(packages)` | dict[package → success/fail] |
| 虚拟环境创建 | `create_venv(path)` | venv python 路径 或 None |
| GPU 检测 | `check_torch_gpu()` | (cuda_available, gpu_name) |

**依赖检测范围**：
- **必需包（10 个）**：langchain, langchain-community, langchain-huggingface, langchain-chroma, langchain-text-splitters, chromadb, sentence-transformers, huggingface-hub, modelscope, openai
- **可选包（6 个）**：unstructured, pdfplumber, transformers, pillow, fastapi, uvicorn

**环境检测报告输出示例**：
```
==================================================
  本地 RAG 环境检测
==================================================
[OK] Python 版本: 3.11.8 — OK
[OK] Pip: 可用
已安装包: 85 个
[OK] 所有必需包已安装
[i] 可选包未安装 (2): fastapi, uvicorn
[i] GPU: 未检测到 CUDA (将使用 CPU)
```

### 2.2 模块 B：嵌入模型管理（embedding_model_manager.py）

**职责**：嵌入模型的完整生命周期管理。

#### 多源下载优先级

| 优先级 | 源名称 | 方法 | 说明 |
|:------:|:------:|:----:|------|
| 1 | modelscope | `_download_with_modelscope()` | ModelScope 国内镜像，最稳定 |
| 2 | hf_mirror | `_download_with_hf_mirror()` | HuggingFace 国内镜像 |
| 3 | hf_official | `_download_with_hf_official()` | HuggingFace 官方源 |
| 4 | llm_find | LLM 搜索 | LLM 自动查找可用源 |

#### 通用路径查找机制

不再依赖特定变形模式（如 `1___5`），而是使用**内容感知 + 名称相似度评分**：

```python
def _find_actual_model_path(model_id, download_dir):
    """通用模型路径查找。不依赖任何固定变形模式"""
    target_norm = _normalize(model_id)  # 去除非字母数字
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
| `download_model(model_id)` | 多源下载 + 重试 + 校验 + 路径修正 | 字典 |
| `verify_model(path)` | 验证模型可用性 | (ok, detail) |
| `list_downloaded_models()` | 列出已下载模型 | list |
| `remove_model(model_id)` | 删除模型 | (ok, msg) |
| `get_model_path(model_id)` | 通用路径查找 | path 或 None |

#### 推荐模型列表

| 模型 ID | 大小 | 说明 |
|---------|:----:|------|
| BAAI/bge-small-zh-v1.5 | 130MB | 轻量中文嵌入（推荐） |
| BAAI/bge-base-zh-v1.5 | 400MB | 中等中文嵌入 |
| shibing624/text2vec-base-chinese | 400MB | CPU 友好中文嵌入 |
| maidalun1020/bce-embedding-base_v1 | 800MB | 网易 BCEmbedding |
| sentence-transformers/all-MiniLM-L6-v2 | 80MB | 英文嵌入（超轻量） |
| BAAI/bge-large-zh-v1.5 | 1300MB | 高精度中文嵌入（大） |

### 2.3 模块 C：文本切分（text_splitter.py）

**职责**：6 种切分策略 + 组合切分，将文档切割为语义完整的块。

#### 六种切分策略

| 策略 | 函数 | 原理 | 适用场景 | 参数 |
|:----:|:----:|:----:|:--------:|:----:|
| **固定窗口** | `split_fixed_size()` | 按固定字符数切分，可设重叠 | 长度均匀的清洗文本 | chunk_size, chunk_overlap |
| **递归切分** | `split_recursive()` | 按优先级尝试不同分隔符 | 未知/混合格式文档（默认） | chunk_size, chunk_overlap, separators |
| **层级/标题切分** | `split_by_headers()` | 基于 Markdown 标题切分，保留结构元数据 | Markdown 结构化文档 | headers_to_split_on, strip_headers |
| **按句切分** | `split_by_sentence()` | 以句子为单位 | 短句文档、证据抽取 | — |
| **语义切分** | `split_semantic()` | 计算相邻句子相似度，在主题边界处切分 | 长叙述性文本 | embeddings, breakpoint_type |
| **代码块保护切分** | `split_with_mermaid_preserve()` | 先保护 mermaid 代码块，再按标题切，最后还原 | 含流程图/代码块的文档 | headers_to_split_on, strip_headers |

#### 组合切分

`combo_split()` 支持主策略 + 二次策略组合：

```python
# 示例：先用标题切分保留结构，再递归切分细化
chunks = combo_split(text,
    primary_strategy="headers",
    secondary_strategy="recursive",
    chunk_size=500, chunk_overlap=50)
```

**切分效果自检清单**：
- [ ] 每个块能否在 500 字符内表达相对完整的主题？
- [ ] 标题块是否包含所属章节的标题路径（元数据）？
- [ ] 代码块（如 mermaid）是否完整保留，没有被切断？
- [ ] 中英文混合内容是否没有出现乱码或异常换行？

### 2.4 模块 D：知识库管理（knowledge_base_manager.py）

**职责**：多知识库的创建、删除、切换、文档入库、自动分类。

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

#### 自动分类规则

```
规则: {"艺术": {"keywords": ["美术", "绘画", "雕塑", "设计"], "description": "艺术类资料"},
       "政治": {"keywords": ["政策", "法规", "政府", "选举"], "description": "政治类资料"},
       "娱乐": {"keywords": ["电影", "音乐", "综艺", "明星"], "description": "娱乐新闻"}}
```

用户提供资料 → LLM 判断关键词匹配 → 自动归入指定知识库。
也支持新建库指令："新建一个知识库 D，以后这种科研资料都放这里面。"

### 2.5 模块 E：RAG 核心引擎（rag_core.py）

**职责**：嵌入模型初始化、向量检索、LLM 调用、问答流程编排。

| 函数 | 说明 | 关键参数 |
|------|------|----------|
| `get_embeddings(model_path, device)` | 获取嵌入模型实例 | device: auto/cpu/cuda |
| `get_vectorstore(kb_name, embeddings)` | 获取 Chroma 向量存储 | 自动创建不存在的库 |
| `retrieve_documents(query, kb_name, k, threshold)` | 检索相似文档 | k=3, score_threshold |
| `get_llm(base_url, temperature, max_tokens)` | 获取 LLM 实例 | 默认 localhost:1234 |
| `build_context(docs)` | 从检索结果构建上下文 | 含引用来源标记 |
| `answer_question(question, kb_name, template)` | 完整 RAG 问答 | 返回 answer + source_docs + context |
| `import_documents_to_kb(file_path, kb_name)` | 文档切分 + 入库 | 自动合并元数据 |
| `verify_llm_connection()` | 验证 LLM 连接 | 调用 /v1/models |

#### 问答数据流

```
用户问题
  ↓
embeddings.encode(question) → 查询向量
  ↓
Chroma.similarity_search(query_vector, k=3)
  ↓
检索结果 → build_context(docs) → context 字符串
  ↓
prompt_template.format(context=context, question=question)
  ↓
LLM.invoke(prompt) → 原始回答
  ↓
re.sub(r'<think>.*?</think>', '', answer) → 清理推理标签
  ↓
最终回答 + 引用片段
```

### 2.6 模块 F：Prompt 管理（prompt_manager.py）

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

### 2.7 模块 G：统一配置管理（config.py）

**职责**：集中管理所有运行时配置，支持 CLI 和 Web 面板修改。

**6 个配置 Section**：

| Section | 关键参数 | 默认值 |
|:-------:|----------|:------:|
| `embedding` | model_name, model_path, device, normalize_embeddings | bge-small-zh-v1.5, auto, true |
| `splitting` | strategy, chunk_size, chunk_overlap, separators | recursive, 500, 50 |
| `retrieval` | k, score_threshold, search_type | 3, null, similarity |
| `llm` | base_url, api_key, temperature, max_tokens | localhost:1234, 0.1, 512 |
| `kb` | active_kb, auto_classify | default, false |
| `prompt` | template_file | default_template.txt |

**R-12 合规路径模式**：
```python
DEFAULT_DATA_DIR_RAW = "skills/.standardization/local-rag-builder/data/"
_data_dir_abs = os.path.normpath(os.path.join(SKILL_ROOT, "..", "..", DEFAULT_DATA_DIR_RAW))
```

---

## 三、核心设计原则

### D1: 无需 LM Studio
本技能自身替代 LLM 角色，无需额外部署 LLM 服务。LM Studio 配置作为可选指南。

### D2: 松耦合模块
七个核心模块各司其职，模块间通过 `config.py` + 函数参数传递数据，无循环依赖。
**目的**：每个模块可独立升级/替换，互不影响。

### D3: 自包含输出
Web 设置面板、CLI 交互、HTML 报表均为自包含，无外部依赖。
**目的**：无需部署服务器，打开即用。

### D4: 结构化接口
所有脚本支持 `--json` 参数输出标准 JSON，供智能体集成调用。
**目的**：不仅人类可用，AI 也可编程调用。

### D5: 路径修正通用化
嵌入模型路径查找使用内容感知方案，不依赖特定变形模式。
**目的**：无论 ModelScope / HuggingFace 下载后的目录名如何变形，都能正确找到。

---

## 四、交互方式

### 4.1 CLI 交互（rag_interface.py）

**支持的交互命令**：

| 命令 | 说明 | 示例 |
|:----:|------|:----:|
| `/help` | 显示帮助 | — |
| `/prompt show\|set\|reset` | Prompt 模板操作 | `/prompt set` |
| `/kb list\|create\|use\|delete` | 知识库管理 | `/kb create art` |
| `/model list\|use` | 嵌入模型切换 | `/model use BAAI/bge-large-zh` |
| `/config show\|set` | 配置查看/修改 | `/config set retrieval.k 5` |
| `/reset` | 重置所有配置 | — |
| `/import <file>` | 导入文档 | `/import doc.md` |
| `/verify-llm` | 验证 LLM 连接 | — |
| `/exit` | 退出 | — |
| 直接输入文本 | 问答模式 | "什么是 RAG？" |

### 4.2 Web 可视化面板（rag_web_ui.py）

| 面板区域 | 可调参数 |
|:--------:|----------|
| 状态卡片 | 嵌入模型数、知识库数、文档块数 |
| 嵌入模型 | 当前模型选择、设备（auto/cuda/cpu）、推荐模型查看 |
| 文本切分 | 主策略、二次策略、chunk_size、chunk_overlap |
| 检索参数 | K 值、相似度阈值 |
| LLM 设置 | API 地址、Temperature、Max Tokens（含连接验证按钮） |
| Prompt 模板 | 完整模板编辑区（含重置按钮） |
| 知识库概览 | 所有知识库列表 + 文档数 |
| 全局操作 | 重置配置、刷新 |

### 4.3 结构化 JSON 接口

所有脚本支持 `--json` 输出：

```bash
# 环境检测
python scripts/rag_env_setup.py --json

# 嵌入模型列表
python scripts/embedding_model_manager.py --list --json

# 知识库列表
python scripts/knowledge_base_manager.py --list --json

# 单次问答
python scripts/rag_interface.py --non-interactive "问题" --json

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
| huggingface-hub | 模型下载 | 必需 |
| modelscope | ModelScope 国内下载 | 必需 |
| openai | OpenAI 兼容 API 连接 | 必需 |
| torch | PyTorch 后端（GPU 加速） | 推荐 |
| unstructured[pdf] | PDF 文档加载 | 可选 |
| pdfplumber | 精确 PDF 表格提取 | 可选 |
| fastapi + uvicorn | API 服务封装 | 可选 |

---

## 六、版本历史与升级路线

| 版本 | 日期 | 核心变化 |
|:----:|:----:|:--------:|
| 0.1.0 | 2026-06-06 | 初始版本：环境检测 / 模型下载 / 切分 / 知识库 / Prompt / Web UI / CLI |
| 0.1.1 | 2026-06-06 | R-12 数据目录合规、frontmatter 补充、版本号合规 |
| 0.2.0 | 2026-06-06 | 模型路径查找通用化、exception 加固、功能测试全量通过 |

**计划中**：
- 0.3.0：语法索引 / query 重写 / 混合检索（稠密+稀疏）
- 0.4.0：RAPTOR 摘要索引 / 多模态检索
- 0.5.0：评估集 / LLM-as-Judge 自动评测

---

> 本文档基于 local-rag-builder v0.2.0 的 SKILL.md + references/*.md + 核心脚本综合分析整理。
