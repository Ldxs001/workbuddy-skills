# 更新日志 — local-rag-builder

## 1.0.0 (2026-06-07)

### 重大重构
- `text_splitter.py` 全面重写为三层流水线：守卫栈(多选) → 主策略(单选) → 后处理(单选/不选)
- 新增插件注册架构 `StrategyPlugin`/`GuardPlugin`，每个策略声明 `config_schema`
- 5 内置策略 + 5 内置守卫全部注册到插件系统，Web UI 根据 schema 动态渲染表单
- `split_by_sentence` 支持 `language` 参数（中文/English/自定义）及自定义分隔符
- metadata 白名单继承：headers/semantic 子切继承 h1/h2/h3/source

### 新增功能
- 输入源配置：PDF/OCR/HTML→MD 开关
- GuardStack 守卫栈：mermaid/code/math/table/html 可链式保护与还原
- Web UI 大改：守卫栈卡片、5 策略动态配置表单、后处理配置、极客模式 JSON 编辑器
- 配置模板系统：保存/加载/删除复用模板
- 知识库自动分类规则编辑器（关键词 + 扩展名匹配），Web UI 可视化管理（添加/编辑/删除/重置）
- 新 API：`/api/override`, `/api/input-source`, `/api/config/raw`, `/api/template/*`, `/api/rules/*`
- 所有配置/规则可一键恢复默认

### 修复
- `rag_core.py` 缺失 `strategy_overrides` 传递，导致策略级 chunk_size 覆盖入库时不生效
- Guard 链式占位符冲突（改为唯一前缀 `__GUARD_NAME_X__`）
- HTML 编码错误（surrogate pair）
- 多处文档与代码不同步

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
- SKILL.md 及全文件移除 WorkBuddy 特化引用，改为 `xxxx` 代指任意智能体
- 所有 docstring 和注释统一通用化描述

## 0.4.0 (2026-06-06)

### 修复
- **【关键】`rag_env_setup.py` pip 锁死导致 auto-install 报 OK 但啥也没装的 BUG**
  - 根因：`install_packages()` 内 `except Exception: pass` 吞掉 pip 升级超时异常，返回空 `{}`，调用方误判为安装成功
  - 修复：移除裸 `except: pass`，所有异常明确 catch 并报告
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
- `rag_core.py` 移除所有 LLM 依赖，改为纯核心层。新增 `format_skill_output()` 返回结构化 JSON（含已填充 prompt）
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
