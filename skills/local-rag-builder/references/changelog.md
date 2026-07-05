## [1.3.1] - 2026-07-05

### 改进
- **扫描 PDF 自动 OCR**：`import_documents_to_kb()` 自动检测扫描版 PDF，无文本时回退 EasyOCR（不再需要手动写 OCR 脚本）
- **KB 签名自动更新**：`add_documents_to_kb()` 入库时自动调用 `update_kb_signature()`，签名不再滞后
- **签名质量提升**：过滤纯数字 token、中文词加权 3x、取中后段代表性片段（跳过封面/目录）
- **文档一致性修复**：SKILL.md / guide.md / setup-spec.md / faq.md 中 Python 版本从"3.8-3.11"更新为"3.11+"，补充 OCR 回退和签名功能说明

---

## [1.3.0] - 2026-07-05

### 新增
- **路由层关键词语义分类**：路由开启后，入库和出库共享同一套 reranker 语义匹配逻辑
  - 入库：`auto_classify()` 新增 `use_semantic` 参数，路由开时用 reranker 对 `rule.keywords × doc_content` 打分，而非硬匹配
  - 出库：`route_query()` 新增 `① 关键词语义路由` 步骤，先于硬编码和签名回退执行
  - 扩展名匹配始终精确，不受路由开关影响
  - CLI：`rag_skill.py --import-file --auto-classify` 自动分类入库
  - Web UI：路由层新增「语义分类阈值」配置项

---

## [1.2.18] - 2026-07-05

### 修复
- **Web UI 启动报错 UnboundLocalError**：`generate_html()` 中 `RECOMMENDED_RERANK_MODELS` 在第 119 行使用但在第 128 行才 import，导致 Python 将其视为未绑定的局部变量
  - 根因：过滤器代码插入位置在 import 语句之前
  - 修复：将过滤逻辑移到 `from embedding_model_manager import ...` 之后

---

## [1.2.17] - 2026-07-05

### 重构
- **知识库列表移除嵌入模型下拉框**：图1（KB 列表）的逐 KB 模型选择器与图2（规则编辑器）完全重叠，移除后只显示 KB 名 + 文档数。KB 嵌入模型选择统一在「自动分类规则」编辑弹窗中操作。

---

## [1.2.16] - 2026-07-05

### 修复
- **知识库嵌入模型选择器存的是文件路径而非模型 ID**：下拉菜单的 `value` 用了 `m.get("path")`，导致 `set_kb_model()` 将完整文件路径写入 KB 配置
  - 根因：`rag_web_ui.py` 规则编辑器 `<option value="{path}">` 存的是文件路径
  - 修复：改为 `value="{model_id}"`，保存标准模型 ID
- **`get_embeddings()` 无法解析 model_id 到文件路径**：KB 配置存的是 model_id（如 `maidalun1020/bce-embedding-base_v1`），但 `get_embeddings()` 直接调 `os.path.exists()` 找不到，fallback 到字母序第一个模型（通常是 reranker）
  - 修复：新增 `model_index.json` 查找逻辑，将 model_id 转为真实文件路径

---

## [1.2.15] - 2026-07-05

### 修复
- **Web UI 知识库嵌入模型选择器混入重排序模型**：`list_downloaded_models()` 返回所有已下载模型（嵌入+重排序），知识库规则编辑器的模型下拉列表未做过滤，导致用户可能误选 mxbai-rerank 等重排序模型作为知识库的嵌入模型
  - 根因：`generate_html()` 和 `/api/kb-models` 接口直接将 `list_downloaded_models()` 结果用于 KB 模型选择器
  - 修复：SSR 和 API 两端均过滤掉 `RECOMMENDED_RERANK_MODELS` 中的模型

### 改进
- **模型列表增加标签**：嵌入模型、重排序模型、路由模型的列表项前面分别标注 `[嵌入]`、`[重排序]`、`[路由]` 标签，防止混淆

---

## [1.2.14] - 2026-07-05

### 修复
- **LICENSE.md 署名**：版权持有者从 `[username-redacted]`（git-sync 脱敏残留）恢复为 `wUwproject`

---

## [1.2.13] - 2026-07-05

### 文档
- **LICENSE.md**：新增第三方模型许可声明表，列出 BGE/all-MiniLM/e5 等可下载模型的许可协议

---

## [1.2.12] - 2026-07-05

### 新增
- **EasyOCR 回退机制**：OCR 输入源检测增加 EasyOCR 作为 PaddleOCR 的回退选项。
  当 PaddleOCR 不可用时（如 PaddlePaddle 兼容性问题），自动切换到 EasyOCR。
  `_check_dep("enable_ocr")` 现在返回 `ready` 如果 paddleocr 或 easyocr 任一可用。
  自动安装时先尝试 paddleocr，失败后尝试 easyocr。

### 文档修正
- **Web UI OCR 描述**：`rag_web_ui.py` 和 `rag_settings.html` 的 OCR 提示文本从 `paddleocr` 改为 `paddleocr (CPU: paddleocr / GPU: paddleocr-gpu) / easyocr`
- **SKILL.md 限制**：文件类型支持描述从"不支持 PDF、图片OCR"改为"可选扩展支持 PDF/OCR/HTML→MD（输入源开关）"

---

## [1.2.11] - 2026-07-05

### 修复

- **检索 k 值 UI 联动**：开启 Rerank 时 `retrieval.k` 自动设为 20，关闭时恢复 3。
  之前只在 `retrieve_context()` 层做运行时缩放，但 UI 上 k 值不联动，用户看到的始终是 3。
  根因：`/api/reranker/toggle` 只改了 `reranker.enabled`，没有同步改 `retrieval.k`。
- **输入源状态指示器初始状态**：修复页面刚打开时三个状态点显示黑色（无色）的问题。
  根因：SSR 生成的 `<span class="src-dot">` 缺少初始 CSS 类（ready/missing/off），`refreshSrcStatus()` 异步调用前点显示为默认黑色。
  修复：`generate_html()` 中根据 toggle 状态和 `_check_dep()` 结果直接 SSR 正确的 CSS 类。
- **清理冗余代码**：移除 `refreshSrcStatus()` 中的死代码 `var on=document.querySelector(...)`。

---

## [1.2.10] - 2026-07-05

### 新增
- **检索 k 自动扩容**：rerank 开启时 `retrieve_context()` 自动将 `retrieval.k` 从 3 扩容到 `max(k, reranker.top_k × 4)`（默认 20），保证精排有足够候选池
  - 根因：rerank 关闭时 k=3 是合理的最终输出数；rerank 开启后 k=3 只能召回 3 个候选，精排无筛选空间
  - 修复：检索前检测 rerank 开关状态，开启时 `effective_k = max(default_k, reranker_top_k * 4)`

### 文档对齐
- **architecture.md**：新增 Router/Reranker 模块依赖和查询流程图；添加 k 与 reranker.top_k 参数耦合说明
- **setup-spec.md**：strategy #7 标注 semantic 使用全局嵌入模型；retrieval.k #14 和 reranker.top_k #29 添加耦合约束说明
- **SKILL.md**：核心能力表新增路由层（#4）和 Rerank 层（#5），Web 面板描述补充 Router/Rerank 控件
- **guide.md**：Web 面板功能列表补充 Rerank 层和路由层配置项

---

## [1.2.9] - 2026-07-05

### 修复
- **语义切分硬编码嵌入模型**：`split_semantic` 和 `split_semantic` 后处理子切均硬编码 `BAAI/bge-small-zh-v1.5`，不随用户配置的嵌入模型变化
  - 根因：`split_pipeline` 没有 `embeddings` 参数，`_run_secondary` 也没有，`rag_core.import_documents_to_kb` 手里有 `embeddings` 却从未传递
  - 修复：`split_pipeline` 新增 `embeddings=None` 参数，语义主策略时注入 `strategy_kwargs`；`_run_secondary` 新增 `embeddings=None` 参数，语义子切使用传入模型；`rag_core.import_documents_to_kb` 将 `embeddings` 传入 `split_pipeline`
  - 向后兼容：不传 `embeddings` 时仍 fallback 到 `bge-small-zh-v1.5`
- **sentence 切分 fallback delimiter 乱附着**：NLTK 不可用时 regex fallback 吃掉真实标点后硬粘 `delimiters[0]`（"。"），导致 `"你吃饭了吗？"` → `"你吃饭了吗。"`
  - 根因：`re.split` 非捕获组模式会丢弃 delimiter，后续用 `delimiters[0]` 硬补
  - 修复：改用捕获组 `(…)` 保留 delimiter，按 i,i+1 配对取出内容+真实标点，空 content 跳过，末尾无标点不追加

### 新增
- **Web UI Rerank 输出数量控件**：Rerank 层卡片新增 `top_k` 数字输入框，范围 1-50
- **SKILL.md frontmatter**：新增 `slug` 和 `displayName` 字段，满足 SkillHub 发布要求

---

## [1.2.8] - 2026-07-05

### 新增
- **输入源状态指示灯**：每个输入源开关旁显示 ⬤ 色点
  - 🟡 黄 = 开关未开启 / 检测中
  - 🟢 绿 = 依赖已安装可用
  - 🔴 红 = 依赖缺失
  - 页面加载时自动检测依赖状态，开关点击后实时更新
- 新增 `/api/dep-check` 端点返回所有输入源依赖状态

---

## [1.2.7] - 2026-07-05

### 修复
- **路由层回退模型选择每次重启后重置**：
  - 根因：保存时写入 `router.fallback.model_path`，但 HTML 生成时读取 `router.model_path_fallback`，路径不一致导致始终读不到已保存的值，回退到列表第一个模型
  - 修复：`_mlist("fb")` 的 `current_path` 改为 `fb_cfg.get("model_path", "")`

---

## [1.2.6] - 2026-07-05

### 新增
- **输入源开关自动安装依赖**：打开 PDF/OCR/HTML→MD 开关时自动检测并 `pip install` 所需包
  - `enable_pdf` → 依次检测 `pypdf` / `pdfplumber`，都无则装 `pypdf`
  - `enable_ocr` → 检测 `paddleocr`，无则安装
  - `enable_html2md` → 检测 `html2text`，无则安装
  - 安装失败时开关保持关闭，返回错误提示

---

## [1.2.5] - 2026-07-05

### 修复
- **所有 toggle 开关需要多次点击才能生效**：
  - 根因：`<label>` 包裹 `<input type="checkbox">` 时，点击 label 同时触发两件事：(1) label 的 `onclick` 调用 API toggle，(2) 浏览器原生将 checkbox 的 `click` 事件冒泡回 label，导致 `onclick` **二次触发**，API 被调两次（刚开又关）
  - 修复：所有 6 个 toggle 的 `<input>` 添加 `onclick="event.stopPropagation()"`，阻止 checkbox 原生 click 冒泡到 label
  - 影响范围：Rerank 开关 / 路由开关 / 多知识库路由开关 / PDF 解析开关 / OCR 开关 / HTML→MD 开关

---

## [1.2.4] - 2026-07-05

### 修复
- **自动分类规则编辑后蓝色三角箭头仍显示"默认模型"**：
  - 根因1：`saveRule()` 调用 `/api/kb-model` 设置 KB 模型，但目标 KB（规则名）不存在于 `kb_index.json`，`set_kb_model` 返回失败
  - 修复：`/api/kb-model` 处理时若 KB 不存在则自动创建
  - 根因2：`refreshRules` 显示用 `split('/')` 提取模型名，Windows 路径用 `\` 无法正确拆分
  - 修复：自动检测路径分隔符（`\` 或 `/`），提取末段目录名，将 `_` 转为 `/` 显示

---

## [1.2.3] - 2026-07-05

### 修复
- **`list_downloaded_models` 返回无权重文件的空目录模型**：
  - 根因：只从 `model_index.json` 读取，不验证文件是否实际存在。目录被删除/损坏后仍显示"已下载"并可被选中
  - 修复：遍历索引时调用 `_check_integrity()` 过滤，仅返回权重文件完整的模型

---

## [1.2.2] - 2026-07-05

### 修复
- **Web UI 下载进度监控不兼容 ModelScope 缓存目录结构**：
  - 根因：ModelScope 的 `snapshot_download(cache_dir=xx)` 将文件写入 `BAAI/bge-m3` 格式（`org/name`），但 Web UI 进度扫描硬编码为 HuggingFace 的 `models--BAAI--bge-m3` 格式
  - 修复：进度监控同时扫描 HF（`models--`）和 ModelScope（`org/name`）两种缓存路径前缀
- **`_download_with_modelscope` 未安装时跳过而非自动安装**：
  - 根因：函数入口只 `import` 检测，未安装就直接返回失败
  - 修复：`modelscope` 未安装 → 自动 `pip install` → 成功则继续下载，失败才跳下一源
- **HF ↔ ModelScope 模型 ID 映射**：部分模型在两平台 org/name 不一致导致下载挂起
  - 新增 `_MS_MODEL_ID_MAP` 映射表，当前覆盖：
    - `maidalun1020/bce-embedding-base_v1` → `maidalun/bce-embedding-base_v1`
    - `Alibaba-NLP/gte-Qwen2-7B-instruct` → `iic/gte-Qwen2-7B-instruct`
  - `_download_with_modelscope` 入口自动查表映射
- timeout 从 600s 提升至 1800s（BGE-M3 约 2.2GB 需要）

---

## [1.2.0] - 2026-07-05

### 新增
- **嵌入推荐模型大扩充**：从 6 个增至 14 个，补齐常用多语言系列
  - `BAAI/bge-m3`：BGE 多语言旗舰，支持 100+ 语言，Dense+Sparse+MultiVec 三种检索方式
  - `intfloat/multilingual-e5-small/base/large-instruc`：E5 多语言系列（小/中/大），覆盖 100 语言
  - `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`：多语言 paraphrase，50+ 语言
  - `BAAI/bge-large-en-v1.5`：英文高精度嵌入
  - `Alibaba-NLP/gte-Qwen2-7B-instruct`：阿里 GTE 大模型嵌入
  - `sentence-transformers/all-mpnet-base-v2`：英文高精度嵌入
- 模型列表重新分组：BGE 系列 / 多语言系列 / 中文双语系列 / 英文系列

---

## [1.1.3] - 2026-06-21

### 修复
- changelog: 补充 1.1.0 遗漏的 rerank 开发记录（路由层三层架构、rerank 三种模式、排序规则、模型下载三源轮换等）

---

## [1.1.2] - 2026-06-21

### 修复
- SKILL.md 文档描述与实际代码对齐：
  - 移除不存在的 `--retrieve-only` / `--mode integrated` 参数引用
  - 下载源描述"LLM 找源"改为"直连（hf_direct）"
  - 支持文件类型从"md / txt / pdf / URL"修正为"txt / md / py / json / yaml"
  - `chunk_size` 范围 50–2000 → 50–5000，`chunk_overlap` 范围 0–500 → 0–1000
- references/commands.md 补充缺失的 CLI 参数（`--no-router`, `--no-reranker`, `--show-routing`, `--import-file`, `--kb-list`, `--k`, `--threshold` 等）
- references/architecture.md 索引表描述修复（skill-standardization → local-rag-builder）

---

## [1.1.1] - 2026-06-21

### 修复
- refactor: 标准化改造（sensitive_access / permission_weight 自动修正、LICENSE 声明、渐进式索引表、非标章节拆分至 references/、工作流输入/输出标注、限制章节）

---

## [1.1.0] - 2026-06-21

### 新增
- **多知识库路由层（Router）**：三层路由架构
  - HardcodedRouter：基于 KB 规则的硬编码路由（知识库签名自动归纳 + 关键词匹配）
  - FallbackRouter：BGE-Reranker-v2-M3 语义回退路由，用户查询自动路由到最相关知识库
  - Broadcast：全量广播模式（查询同时发送到所有知识库）
- **Rerank 层（Reranker）**：检索后重排序
  - ModelReranker：transformer 模型重排序（默认 BAAI/bge-reranker-v2-m3）
  - RuleReranker：排序规则引擎（score_weight / recency / source_weight / boost_keywords 四种规则类型）
  - HybridReranker：模型 + 规则混合重排，支持权重叠加
- **路由/Rerank 共享模型体系**：`RECOMMENDED_RERANK_MODELS` 专用列表（BGE-Reranker-v2-M3 / bge-reranker-base / bge-reranker-large 等），与嵌入模型独立
- **排序规则编辑器**：Web UI 覆盖层弹窗（与知识库规则编辑器一致），支持新增/编辑/删除排序规则
- **模型下载系统三源轮换**：
  - ModelScope / hf-mirror.com / hf-direct（直连）三源自动切换
  - 断点续传：`.incomplete` 标记文件 + blobs 缓存检测
  - 后台下载线程：旋转动画 + 实时下载速度显示 + 30 分钟硬超时
  - 0KB 持续 3 分钟自动切换下载源 + 每个源 3 次重试
  - 下载前自动清理残留 `.incomplete` 文件

### 修复
- 下载源 key 不匹配（`hf_mirror` vs `huggingface_mirror`）：统一命名
- tqdm `\r` 阻塞 readline：设置 `HF_HUB_DISABLE_PROGRESS_BARS=1`
- 监控目录不区分 modelscope/HF 缓存结构：统一扫描 `model_downloads/` 下匹配模型名的所有文件
- hf_direct 默认走 hf-mirror.com 而非 huggingface.co（国内网络友好）
- Web UI API handler 缺少 return：空 mid 时正确返回不再继续执行
- 排序规则弹窗点击无响应：改为覆盖层弹窗模式（与 KB 规则编辑器一致）
- 嵌入模型默认选中：无默认值时自动选中推荐模型列表第一个
- 极客模式/模板管理功能恢复：`--gen-html` 模式下可编辑所有 32+ 参数

### 重构
- Web UI 设置面板卡片重新排序：输入源 → Prompt → 嵌入 → 守卫 → 切片 → 检索 → LLM → 知识库 → 路由 → Rerank → 极客
- 路由/Rerank 配置从键盘输入改为下拉选择（与嵌入模型一致，横向撑满布局）

---

## 1.0.5 (2026-06-13)

### 修复
- refactor: 标准化改造（渐进式索引表格式修复、权限文档补充）

## 1.0.4 (2026-06-13)

### 新增
- KB 专属嵌入模型：每个知识库可独立选择嵌入模型，未指定时回退全局默认
- Web UI KB 管理新增模型下拉选择器
- `/api/kb-model`、`/api/kb-models` API 端点

### 修复
- `knowledge_base_manager.py` `create_knowledge_base()` 新增 `model_id` 参数
- `rag_core.py` `get_embeddings()` 新增 `kb_name` 参数，自动查 KB 专属模型

## 1.0.3 (2026-06-13)

### 修复
- 标准化改造：SKILL.md frontmatter 修复、权限文档补充、产出物路径合规
- 三端版本同步至 1.0.3

## 1.0.2 (2026-06-13)

### 修复
- 删除根目录 `.venv_rag` 遗留虚拟环境
- 同步三端版本号至 1.0.2

## 1.0.1 (2026-06-13)

### 修复
- `rag_core.py` 配置路径失效时无法回退到 `find_model_dirs()`（`if not model_path` 改为 `if not model_path or not os.path.exists(model_path)`）
- `rag_core.py` `HuggingFaceEmbeddings` 未限制本地加载（添加 `local_files_only=True` 避免加载失败时摸 Hub）
- `embedding_model_manager.py` `_check_integrity()` 将仅有 `config.json` 的目录误判为完整（改为要求至少有权重文件）
- 删除根目录残留的空 `data/` 目录

## 1.0.0 (2026-06-07)

## 0.5.0 (2026-06-06)

### 新增
- **运行模式切换**：新增 `mode` 配置（`integrated` / `standalone`）
  - Web UI LLM 卡片改为模式选择器，集成模式下隐藏 LLM 参数
  - 新增 `/api/mode` 端点：POST 切换模式
- **pip 锁自动清理**：`--cleanup-locks` 参数、`cleanup_pip_locks()` 函数、安装前自动清理 stale 锁
- **`--no-deps` 反锁死策略**：chromadb 自动分步安装（先 22 个 core deps 再本体）
- **`--mirror` 镜像选择**：支持 `aliyun / tencent / tsinghua / ustc` 国内镜像源
- **`--dry-run` 试运行模式**：只检测不安装，报告将要安装的包列表
- **流式输出**：`_pip_run()`、`run_command()` 改为 `Popen` 逐行流式输出，用户和 Bash 工具实时看到进度
- pip 安装日志自动写入 `data/logs/pip_install_*.log`

### 修复
- **`except Exception: pass` 吞异常**：install_packages 返回空 {} 却报"安装完成"，改为明确 catch + 报告
- **安装后验证**：`pip list` + `check_missing()` 双重确认才报 OK，不再虚假通过
- **包名标准化**：`list_installed()` 统一 `_`→`-`，修复 `huggingface_hub` vs `huggingface-hub` 不匹配
- **NameError**：`--auto-install` 失败提示中的 `{python}` 未定义
- **config.py `load_config()`**：`mode` 字段非 dict 导致 `.update()` 崩溃，兼容非 dict 顶层字段

### 重构
- SKILL.md 及全文件删除 WorkBuddy 特化引用，改为 `xxxx` 代指任意智能体
- 所有 docstring 和注释统一通用化描述

## 0.4.0 (2026-06-06)

### 修复
- **【关键】`rag_env_setup.py` pip 锁死导致 auto-install 报 OK 但啥也没装的 BUG**
  - 根因：`install_packages()` 内 `except Exception: pass` 吞掉 pip 升级超时异常，返回空 `{}`，调用方误判为安装成功
  - 修复：删除裸 `except: pass`，所有异常明确 catch 并报告
  - 修复：安装后通过 `pip list` + `check_missing()` 双重验证才报 OK
  - 修复：安装前自动检测并清理 stale pip 锁文件（Windows `%LOCALAPPDATA%/pip/ephem/`）
- **新增 pip 锁自动清理** — `--cleanup-locks` 参数、`cleanup_pip_locks()` 函数、安装前自动清理
- **新增 `--no-deps` 反锁死策略** — chromadb 自动分步安装（先 core deps 再本体），耗时过长的依赖图不会一次性解析
- **新增 `--mirror` 镜像选择** — 支持 `aliyun / tencent / tsinghua / ustc` 四个国内镜像源
- **新增 `--dry-run` 试运行模式** — 只检测不安装，报告将要安装的包列表
- **SKILL.md**：更新命令速查表，补充 `--cleanup-locks` 和 `--mirror`
- **`_pip_run()` 改为流式输出而非 `capture_output`**：修复 Bash 工具因长时间无字符输出而超时杀进程的问题
- **`list_installed()` 包名标准化**：修复 pip 输出 `huggingface_hub`（下划线）但 requirements 列表写 `huggingface-hub`（连字符）导致的验证误报
- **修复 NameError**：`--auto-install` 失败提示中的 `{python}` 未定义

## 0.3.0 (2026-06-06)

### 重构
- **双模式架构**：拆分为 `rag_skill.py`（技能模式，纯检索无 LLM）和 `rag_standalone.py`（独立模式，检索+LLM 全链路）
- `rag_core.py` 删除所有 LLM 依赖，改为纯核心层。新增 `format_skill_output()` 返回结构化 JSON（含已填充 prompt）
- `embedding_model_manager.py`：路径查找改为通用内容感知方案（`_normalize` + `_name_similarity` + `_is_model_dir`），不再依赖任何特定变形模式

### 新增
- `rag_skill.py`：零 LLM 依赖的技能接口，仅返回结构化 JSON，供任何智能体使用
- `rag_standalone.py`：独立系统，含交互式 CLI + `/llm-help` 命令 + 内置三个 LLM 方案接入指南
- `references/llm-setup.md`：结构化 LLM 接入文档（LM Studio / Ollama / vLLM 三方案含配置方式）

### 修复
- `rag_web_ui.py`：修复 `verify_llm_connection` 导入路径（已迁移到 rag_standalone）
- `config.py`/`prompt_manager.py`/`rag_env_setup.py`：exception 覆盖加固
- R-10/R-11/R-23 合规修复（产出物路径迁移、文档引用更新）
- 文档引用 `rag_interface.py` 全部更新为 `rag_skill.py`/`rag_standalone.py`

## 0.2.0 (2026-06-06)

- 重构: 嵌入模型路径查找改为通用内容感知方案（`_normalize` + `_name_similarity` + `_is_model_dir`），不再依赖特定变形模式
- 重构: `verify_model` 改用 `_is_model_dir` 通用检测
- 重构: `get_model_path` 改用相似度评分匹配
- 修复: exception 覆盖率加固（config.py/prompt_manager.py/rag_env_setup.py）
- 测试: 功能测试通过（D1-D6: 0 BLOCK, 57 WARN）

## 0.1.1 (2026-06-06)

- 修复: 数据目录路径合规（R-12）
- 修复: frontmatter 补充 trigger/trigger_negative/license 字段
- 修复: 版本号格式合规

## 0.1.0 (2026-06-06)

- 初始版本
- 环境自动检测与修复（Python 版本、缺失包）
- 嵌入模型多源下载（ModelScope/HuggingFace/LLM 搜索）
- 完整性校验与路径修正
- 6 种文本切分策略 + 组合切分
- 多知识库管理与自动分类
- Prompt 模板持久化
- Web 可视化配置界面
- 结构化 JSON 接口（智能体调用）
- 交互式 CLI 界面
