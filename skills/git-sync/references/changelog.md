## [2.34.0] - 2026-07-31

### 修复
- **LLM 交互步骤被 QUIET_MODE 吞掉导致后台死锁** — `main()` 中的 `step_llm_file_filter`（文件筛除）和 `step_sensitive_scan`（敏感脱敏）在静默模式下 stdout 被重定向到 `/dev/null`，WorkBuddy 看不到输出也就无法写入决策文件，死循环挂起。修复：LLM 交互步骤临时恢复 `sys.stdout` 到 `sys.__stdout__`，确保 WorkBuddy 在前台能看到引导提示
- **`step_sensitive_scan` 假 LLM 决策** — 声称"自动生成 LLM 决策"但实际上是一组硬编码的 if/else 规则（`public_docs` × `public_labels` 匹配），既不调用模型也不按用户指引推理。修复：改为真正的 LLM 交互模式，打印发现详情 + 脱敏引导 → 等待 WorkBuddy 写决策文件 → 超时 120s 后全部脱敏保安全
- **`step_llm_file_filter` 无限等待** — 无超时回退，决策文件不来就永远挂起。修复：加 120s 超时 → 超时后全量保留所有文件

### 变更
- **SKILL.md 约束更新** — 明确标注"仅前台运行"，禁止在后台/Bash 任务中运行 git-sync，因为 LLM 交互步骤需要 WorkBuddy 在前台读取输出并写决策文件

## [2.33.0] - 2026-07-27

### 新增
- **路径统一管理**：所有临时文件迁移到 `_paths.py` 的 `TEMP_DIR`（`~/.workbuddy/skills/.standardization/git-sync/temp/`），`_paths.py` 新增 `temp_scan_path()` / `temp_filter_scan_path()` 等统一路径函数
- **Agent 类型自动检测**：不再硬编码 `rag_assistant/__init__.py`，改为 `rglob("__init__.py")` 扫描含 `__version__` 的文件，兼容 `structured_writer/__init__.py` 等任意命名
- **文件筛除决策助手脚本**：`step_llm_file_filter` 生成 `write_filter_decision_{name}.py` 脚本，LLM 通过 Bash 执行写入决策文件，不再依赖 Write tool
- **`WORK_REPO` 路径归一化**：`git-sync.sh` 使用 `.as_posix()` 统一为正斜杠，避免反斜杠在 Python 字符串中被转义

### 变更
- **`manifest.json` 路径同步 `_paths.py`**：`repos.workbuddy-skills.path` 改为 `.workbuddy/workbuddy-skills`，`manifest.py` `get_repo_path()` 回退到 `from _paths import WORK_REPO`
- **`git-sync.py` 版本对比**：agent 仓库版本来用 `rglob` 而非硬编码路径
- **参考文档修正**：`reference.md` 路径描述同步为 `.workbuddy`，移除错误的 `WorkBuddy` 引用

### 修复
- agent 版本号读取失败（硬编码 `rag_assistant/__init__.py`） → 改为 `rglob` 查找
- `git-sync.sh` 版本号读取中反斜杠导致 Python 字符串转义错误
- `clean_zip_source.py` / `sync_with_exclude.py` 未排除 `.standardization/git-sync/temp/` 目录

## [2.32.0] - 2026-07-21

### 变更
- **文件筛除管道封闭**：`step_llm_file_filter` 无 decision 文件时不再 `return None`，改为 **poll 等待** LLM 写入 decision 文件后自动继续，不需重跑 git-sync。门禁封闭，不允许任何方式 bypass

### 修复
- **`--skip-push` 不存在导致报错**：移除了代码中残留的 `--skip-push` 引用

## [2.31.0] - 2026-07-21

### 安全修复（重大）
- **【安全】移除 `--skip-scan` 参数**：`--skip-scan` 允许跳过敏感信息脱敏流程，导致邮箱/Token/本地路径等敏感信息可能被推送到公开仓库。已彻底移除该参数和所有相关逻辑（git-sync.py / git-sync.sh）
- **【安全】移除 `GIT_SYNC_SENSITIVE_MODE=keep-as-is`**：该环境变量模式允许保留敏感信息不做脱敏。已彻底移除，同 `--skip-scan`
- **【安全】敏感信息脱敏改为强制流程**：代码同步前和工作仓库同步后两处脱敏均为强制执行，无任何跳过选项
- **【安全】审计报告标记修正**：之前跳过脱敏后审计报告显示"✅ 脱敏状态：未扫描"，现改为"❌ 脱敏状态：未扫描（脱敏是强制安全门禁，不允许跳过）"
- **文档清理**：SKILL.md、reference.md、faq.md、guide.md 移除所有 `--skip-scan` 和 `keep-as-is` 相关引用

## [2.30.0] - 2026-07-21

### 变更
- **LLM 文件筛除不再卡死**：`step_llm_file_filter()` 不再只写扫描文件后空等，改为全量打印文件列表 + 规则到 stdout，要求 WorkBuddy 在回复中输出决策 JSON。不再静默挂起
- **路径映射从 manifest 统一管理**：manifest 条目新增 `source_path` / `repo_path` 字段，`manifest.py add` 自动按 type 填充默认路径。`git-sync.py` 优先读 manifest，无则回退硬编码。skill 和 agent 统一走同一套逻辑
- **README 更新同时覆盖 skills + agents**：移除 `is_skill` 限制，agent 同步后也会触发 README 重新生成（`update_readme.py` 本身已支持扫描 agent/ 目录）
- **Release 简化**：只打 tag + 建 Release 页面，不传 ZIP。源码包由 GitHub/Gitee 自动从 tag 生成
- **仓库名从 config.json 读取**：`release_creator.py` 和 `step_release_create()` 不再硬编码，改为读 `config.json` 的 `gitee.user/repo` + `github.user/repo`
- **版本号全局归一化 PEP 440**：新增 `_normalize_version()` 函数，入口统一转换版本格式（`1.7.0-beta` → `1.7.0b1`），所有外部输出用归一化版本，源文件不改
- **dev_status 自动判别**：PEP 440 预发布后缀（`.bN`/`.rcN`/`.aN`/`.devN`）→ `4 - Beta`，纯 `x.y.z` → `5 - Production/Stable`
- **PyPI trigger tag 通用化**：格式统一为 `pypi/{type}/{name}/{version}`，manifest 驱动，所有项目通用
- **新增 GitHub Actions 模板**：`references/pypi-github-actions.yml`，监听 `pypi/*/*/*`，Trusted Publisher 配置指南

## [2.28.2] - 2026-07-16

### 修复
- **PyPI 发布 long_description 缺少更新说明**：`pypi_publish.py` 的 setup.py 模板在构建时自动读取 CHANGELOG.md，提取当前版本对应的 changelog 区块追加到 long_description。PyPI 项目页现在会同时显示 README 和更新说明
- **PEP 440 版本命名合规化**：`rag-assistant` 版本号 `1.3.0-beta` → `1.3.0b1`（PEP 440 要求 pre-release 标识符不带 `-`）

## [2.28.1] - 2026-07-16

### 新增
- **update_readme.py 支持 CC BY-SA 4.0**：许可证章节新增 CC BY-SA 4.0 行；目录树自动添加许可证标注（Cogito_Scribit/ 和 architecture/ → CC BY-SA 4.0，skills/ → MIT，agent/ → Apache 2.0 等）

## [2.28.0] - 2026-07-15

### 新增
- **Gitee 发行版创建**：`release_creator.py` 在创建 GitHub Release 后自动调用 Gitee API 创建发行版，token 从 `config.json` 的 `gitee_token` 字段读取
- **GITEE_TOKEN 环境变量支持**：`_get_gitee_token()` 优先读取环境变量，其次读 config.json

### 修复
- **step_llm_file_filter 秒删扫描文件**：写入 `.file_filter_{name}.json` 后立即 `unlink()` 删除，LLM 来不及审查。改为保留扫描文件、输出审查指令（路径+格式），等 LLM 写入决策文件后下次运行继续
- **release_creator.py 只发 GitHub 不发 Gitee**：全程只调用 GitHub API，Gitee 推送 tag 但不创建发行版。新增第 5 步：Gitee API 创建发行版

## [2.27.2] - 2026-07-13

### 修复
- **LLM 决策缺失不阻断**：`step_llm_file_filter` 在决策文件不存在时 `return set()` 而非 `sys.exit(1)`，导致 0 文件同步后自动提交推送空目录。改为硬阻断，杜绝误删

## [2.27.1] - 2026-07-11

### 修复
- **WORK_REPO 路径不统一**：`git-sync.sh` 使用 `$HOME/.workbuddy/workbuddy-skills`，`_paths.py` 使用 `Path.home() / "WorkBuddy" / "workbuddy-skills"`，导致文件同步到错误目录。统一为 `$HOME/WorkBuddy/workbuddy-skills`

## [2.27.0] - 2026-07-10

### 修复
- **pypi_publish.py SSH remote 崩溃**：`remote_url.split("//")[1]` 在 SSH remote 格式（`git@host:path`）下数组越界。添加 `"//" in remote_url` 前置检查
- **pypi_publish.py 默认构建 sdist**：`python -m build` 同时打 sdist 和 wheel，sdist 在部分环境下报 license 错误。改为 `--wheel` 仅构建 wheel
- **git-sync.py LLM 决策缺失时默认全部保留**：无决策文件时 `return {f["path"] for f in tree}` 放行所有文件，安全风险。改为 `return set()` 阻断（fail closed）

## [2.26.6] - 2026-07-09

### 修复
- **displayName 不一致**：ClawHub/SkillHub 发布的显示名统一为 kebab-case（`git-sync`），废除驼峰格式 `Git Sync`

## [2.26.5] - 2026-07-09

### 修复
- **报告推送状态被"跳过"覆盖**：`skipped_sync` 为 True 时强制所有平台显示"⏭️ 跳过"，掩盖了实际推送成功的结果。改为仅当 skipped 且推送失败时显示跳过
- **日志重复输出**：`LOG_BUFFER` 在同一作用域中被 `print` 了两次，导致所有日志都出现双份

## [2.26.4] - 2026-07-09

### 文档
- **SKILL.md 全面更新**：移除过时的"三端同步"描述，替换为"全平台发布工具"；删除"不支持批量"的矛盾声明；能力表更新为全平台 + 支持 `all` 模式
- **reference.md 修复**：MANIFEST_FILE 路径（`scripts/manifest.json` → 正确绝对路径）、WORK_REPO 跨平台说明、敏感扫描更新为 LLM 自动决策模式、ZIP 排除更新为 LLM 动态过滤（v2.26+）
- **guide.md 修复**：skill_audit 独立 CLI → 内联审计；config.json 模板增加 `email` 字段
- **faq.md 修复**：Q11 更新为 LLM 自动决策；Q14 更新为内联审计说明（删除已失效的 CLI 命令）
- **update_readme.py 更新**：新增 agent/ 目录扫描 + 智能体列表表格；许可部分增加 Apache 2.0；config.json readme.description 恢复用户自定义文案（"合集与智能体项目"）

## [2.26.3] - 2026-07-09

### 修复
- **Git Bash 格式本地路径漏脱敏**：sensitive_scan.py 的本地路径正则只匹配 `C:\Users\` 反斜杠格式，未匹配 `/c/Users/` Git Bash 格式。导致 git-sync.sh 中的硬编码路径 `[LOCAL_PATH]/...` 未被扫描发现
- **LLM 决策逻辑修复**：`"路径"` 之前被纳入 public_labels 允许列表，导致公开文档中的真实路径被 keep。改为仅当没有 "本地绝对路径" / "家目录路径" 标签时才 keep

### 变更
- sensitive_scan.py 本地路径正则增强：同时匹配 Windows 反斜杠和 Git Bash 正斜杠格式

## [2.26.2] - 2026-07-09

### 修复
- **ClawHub 发布在 Windows 上崩溃**：subprocess 调用 npx 需要 shell=True，否则找不到可执行文件
- **SkillHub 发布版本错误**：必须显式传 `--version` 参数，不可依赖 SKILL.md frontmatter（平台上已有旧版本时 frontmatter 读取不可靠）
- **Market-only/正常模式输出被吞**：market 步骤改用 print() 直接输出，不走 LOG_BUFFER

### 文档
- 全面更新 SKILL.md 描述、约束、触发条件、核心能力和平台发布差异表
- 更新 references/guide.md 完整执行流程（步骤 0→9）和新版调用方式

## [2.26.1] - 2026-07-09

### 变更
- **LLM 文件过滤器改用 Python 扫描**：Python glob 自动查找规则文件（blueprint*, *rules*, blueprints/），读取内容后与文件树一并传给 LLM。LLM 只做决策判断，不扫描目录，大幅节省 token
- **引导优化**：明确要求保留所有 .py 代码文件、文档、许可证等核心文件

### 修复
- 移除对 `references/blueprint_rules.md` 的硬编码路径引用，改为 Python 动态扫描

## [2.26.0] - 2026-07-09
### 变更
- **移除硬编码黑名单**：不再使用 EXCLUDE_PATTERNS（__pycache__/, *.bak, node_modules/ 等）排除文件
- **LLM 文件过滤器**：新增 step_llm_file_filter，在同步前引导 LLM 审核源文件列表，决定哪些文件可以进入仓库。模型权重、私库数据、缓存文件等由 LLM 判断后排除，不再依赖穷举黑名单
- **同步前置过滤**：LLM 返回允许列表后，sync_files 只复制允许的文件，仓库中只进干净数据

## [2.25.0] - 2026-07-09
### 新增
- **类型自动检测**：自动识别 skill（_meta.json）和 agent（__init__.py），skill 走原流程，agent 同步到 agent/ 目录
- **all 模式**：git-sync all 遍历全部 skills + agents
- **ClawHub 自动发布**：推送到 git 后自动执行 clawhub publish（skill）
- **SkillHub 自动发布**：推送到 git 后自动执行 skillhub publish（skill）
- **PyPI 发布**：--pypi 标志，隔离构建 + twine 上传
- **Release 创建**：--release 标志，git tag + GitHub API Release

### 变更
- 参数解析新增 --skip-market / --market-only / --pypi / --release
- step_commit_and_push / step_version_compare 支持动态子目录路径

## [2.24.2] - 2026-07-06

### 修复
- **`step_sensitive_scan` HOOK-BLOCK 阻塞 pipeline**：敏感扫描发现疑似信息后 `sys.exit(1)` 卡死等待人工决策文件。改为自动生成 LLM 风格决策：公开文档（LICENSE/README/changelog/SKILL.md 等）中的用户名/署名 → keep，邮箱/token/IP → sanitize。无需 `--skip-scan`，无需人工介入

## [2.24.1] - 2026-07-02

### 修复
- **_paths.py WORK_REPO 路径错误** — `Path.home() / ".workbuddy" / "workbuddy-skills"` 指向不存在目录，导致 git-sync 静默退出。修正为 `Path.home() / "WorkBuddy" / "workbuddy-skills"` 指向实际仓库。同时修复 git-sync.py QUIET_MODE 调试后还原

## [2.24.0] - 2026-06-29

### 变更
- **脱敏流程改为 LLM 决策** — `make_all_sanitize.py` 自动全量脱敏回退移除，改为 findings 输出后 HOOK-BLOCK，等待 LLM 审阅并创建 decisions 文件后继续，不再替 LLM 做判断

### 修复
- **sensitive_scan.py 裸扫全部** — `author` 是公开笔名不应自动排除，改为全部扫描暴露给 LLM 判断

## [2.23.2] - 2026-06-27

### 修复
- git-sync.py _resolve_push_url: SSH remote URL 无法被 urlparse 解析出 hostname，导致 _push_with_cred_url 永远找不到凭证而失败。SSH 用 key 认证无需 credential，直接返回 raw_url 让 SSH key 处理

---

## [2.23.1] - 2026-06-27

### 修复
- SKILL.md: fix duplicate `## 触发条件` 标题（auto-fix 遗留）
- SKILL.md: 约束措辞微调以通过 C-18 `参数约束`/`格式要求` 关键词检查

---

## [2.23.0] - 2026-06-27

### 重构
- **[新增] scripts/_paths.py** — 路径集中管理模块，收归所有脚本中的路径常量
- **[git-sync.py]** 替换硬编码路径为 `from _paths import ...`
- **[manifest.py]** 替换硬编码路径为 `from _paths import ...`
- **[normalize_meta.py]** 替换硬编码路径为 `from _paths import ...`
- **[pack_zip.py]** 替换硬编码路径为 `from _paths import ...`
- **[permission_checker.py]** 替换硬编码路径为 `from _paths import ...`
- **[sensitive_scan.py]** 替换硬编码路径为 `from _paths import ...`
- **[sync_with_exclude.py]** 替换硬编码路径为 `from _paths import ...`
- **[update_readme.py]** 替换硬编码路径为 `from _paths import ...`
- **[clean_dist.py]** 替换硬编码路径为 `from _paths import ...`

---

## [2.22.0] - 2026-06-27

### 新增
- **[blueprint_scan.py] 蓝图扫描** — Python 扫描技能目录结构+内容采样，输出 blueprint.json，不做判断
- **[blueprint_rules.md] LLM 判断规则** — 筛除原则和脱敏原则，不写死任何具体路径/模式
- **[sync_with_exclude.py] 排除清单驱动** — 新增 `--exclude-list` 参数，读取 LLM 产出的排除清单，删除硬编码 EXCLUDE_DIRS
- **[sensitive_scan.py] 脱敏清单驱动** — 新增 `sanitize-list` 子命令，读取 LLM 产出的脱敏清单逐项替换
- **[git-sync.py] 蓝图钩子** — pipeline 新增 step_blueprint，排除/脱敏清单缺失时自动生成 blueprint.json 并阻断，等待 LLM 判断后继续

---

## [2.21.1] - 2026-06-16

### 修复
- 删除 version 参数，强制从 _meta.json 读取版本号

---

## [2.21.0] - 2026-06-16

### 修复
- refactor: git-sync

---

## [2.20.0] - 2026-06-16

### 修复
- refactor: git-sync

---

## [2.19.0] - 2026-06-16

### 修复
- refactor: git-sync

---

## [2.18.0] - 2026-06-16

### 修复
- refactor: git-sync

---

## [2.17.0] - 2026-06-16

### 修复
- refactor: git-sync

---

## [2.16.0] - 2026-06-16

### 修复
- refactor: git-sync

---

## [2.15.0] - 2026-06-16

### 修复
- refactor: git-sync

---

## [2.14.0] - 2026-06-16

### 修复
- refactor: git-sync

---

## [2.13.1] - 2026-06-16

### 修复
- references/permissions.md 重写：基于 PermissionChecker 扫描数据生成真实权限说明（CRITICAL 风险等级，15subprocess+19delete+9sensitive+2network）

---

## [2.13.0] - 2026-06-16

### 修复
- refactor 改造完成：C-10空行压缩、C-11章节指纹重排、C-12触发条件/约束格式化、C-14工作流结构化渲染、R-10版本同步、R-11 .bak 清理、R-23文档引用修复、R-26误判过滤

---

## [2.12.31] - 2026-06-16

### 改造
- skill-standardization 全流程改造完成（refactor）：C-10 空行压缩、C-11 章节名规范化、C-14 工作流章节由结构化数据渲染、C-17 示例结构化数据就绪、R-10 版本同步、R-11 .bak 文件清理

---

## [2.12.29] - 2026-06-16

### 修复
- **自动化修复**: audit --fix 自动修正

---

## [2.12.9] - 2026-06-16

### 修复
- **自动化修复**: audit --fix 自动修正

---

## [2.12.10] - 2026-06-16

### 修复
- **自动化修复**: audit --fix 自动修正

---

## [2.12.11] - 2026-06-16

### 修复
- **自动化修复**: audit --fix 自动修正

---

## [2.12.12] - 2026-06-16

### 修复
- **自动化修复**: audit --fix 自动修正

---

## [2.12.13] - 2026-06-16

### 修复
- **自动化修复**: audit --fix 自动修正

---

## [2.12.14] - 2026-06-16

### 修复
- **自动化修复**: audit --fix 自动修正

---

## [2.12.15] - 2026-06-16

### 修复
- **自动化修复**: audit --fix 自动修正

---

## [2.12.16] - 2026-06-16

### 修复
- **自动化修复**: audit --fix 自动修正

---

## [2.12.6] - 2026-06-16

### 修复
- **改造修复**: 标准化改造过程中的多次版本号自动同步

---

## [2.12.5] - 2026-06-16

### 修复
- **改造修复**: SKILL.md 重构后的版本号同步

---

## [2.12.4] - 2026-06-16

### 修复
- **改造修复**: 修正 SKILL.md 章节格式（C-10/C-12/C-15）、新增限制章节、补充索引表 LICENSE 条目
- **文档更新**: 更新 skill_audit.py 引用为 -m scripts.skill_audit

---

## [2.12.3] - 2026-06-16

### 修复
- **改造修复**: 标准化改造过程中的 frontmatter 字段同步

---

## [2.12.2] - 2026-06-16

### 修复
- **自动修复**: 标准化改造过程中由 audit --fix 自动修正的 frontmatter 字段

---

## 2.12.0 (2026-06-15)

### 修复

- **修复 `_push_with_cred_url` / `_pull_with_cred_url` 未检查 URL 内嵌 token 的缺陷**：
  新增 `_resolve_push_url()` 函数，优先使用 remote URL 内嵌的凭证（如 `https://user:[email-redacted]/path`），
  其次从 `~/.git-credentials` 查找。之前只要 `~/.git-credentials` 中无条目就返回"找不到凭证"，
  即使 URL 已含 token 也无法推送。

## 2.11.0 (2026-06-15)

### 修复

- **修复 Windows nul 保留设备名导致 copytree 崩溃**：`sync_files()` 和 `step_pack_zip` 的临时目录复制改为逐个复制并跳过 `name.lower() == "nul"` 的条目，避免 Windows 内核将 `nul` 路径解析为 `\\.\nul` 设备

## 2.10.0 (2026-06-15)

### 重构

- **错误消息标准化**：新增 `_classify_push_error()` 函数，将 git push/pull 原始错误输出归类为中文描述（超时、DNS、认证、拒绝等），防止 LLM 误读 443 等原始错误码
- **`_pull_with_cred_url()` 增加错误处理**：pull 失败时也调用 `_classify_push_error()` 标准化错误消息
- **无更新时 `return True, True` → `return False, False`**：防止 manifest 版本号走在推送前面（无更新时不应更新 manifest）
- **reference.md 新增"错误码与错误消息说明"章节**：AI 必读，速查错误消息类别和应对原则

## 2.9.3 (2026-06-09)

### 修复
- **git commit author 从 config.json 读取**：改为使用 `author` + `email` 字段，不再硬编码 `WorkBuddy <workbuddy@local>`
- **config.json 新增 `email` 字段**：用于配置 git commit 提交者邮箱

---

## 2.9.2 (2026-06-09)

### 修复
- **README 文案从硬编码改为 config.json 驱动**：新增 `readme` 配置段（title/description/repo_name），update_readme.py 和 manifest.py 的 `_generate_readme()` 统一从 config.json 读取
- **GBK 终端编码崩溃**：manifest.py 和 git-sync.py 模块级替换 `print` 为 `_safe_print`，30+ 处 emoji 输出不再崩
- **git-sync.py 版本号与 _meta.json 不同步**：v2.6.22/2.6.23 → v2.9.2，对齐主版本

## 2.9.1 (2026-06-06)

### 修复
- `run_git()` 缺少 `timeout=120` 参数：GitHub 443 超时时 `subprocess.run` 永久挂死，脚本无法进入 retry 逻辑
  - 修复：添加 `timeout=120`，超时后抛出 `TimeoutExpired`，走 retry 流程并正常退出

## 2.9.0 (2026-06-03)

### 新增
- **静默模式**：步骤执行期间子进程输出被捕获，不泄漏到终端
- **日志缓冲**：log() 从直接打印改为缓冲，步骤结束统一输出

### 更新
- run_python() 在静默模式下自动 capture=True，阻止子进程 stdout 泄漏
- main() 所有步骤包裹在 redirect_stdout + QUIET_MODE 中
- 最终输出结构固定：统一步骤日志 + 固定格式报告

## 2.8.2 (2026-06-03)

### 修复
- SKILL.md「AI 执行后必须输出」指令缺失"如何输出"：仅声明"无需重新格式化"，
  未说明 AI 应将终端输出原文复制到回复中（终端输出在工具结果内，用户看不到）
  修复：明确要求"将终端输出的完整报告原文放入回复中，不重新格式化、不摘录、不加工"

---

## 2.8.1 (2026-06-03)

### 修复
- `step_skill_audit()` 在 manifest 更新前执行，导致最终报告显示过期 ERROR=1
  修复：审计移至 manifest 更新后执行，版本一致性检查使用最终数据

---

## 2.8.0 (2026-06-02)

### 新增

- **自动清理旧包**：每次生成 ZIP 后自动清理同一技能的旧包，保留最近 5 个版本

---

## 2.7.4 (2026-06-01)

### 修复
- C-13索引表补全

---

## 2.7.3 (2026-06-01)

### 修复
- R-10同步+渐进式索引表

---

## 2.7.2 (2026-06-01)

### 修复
- 恢复 v2.7.1后仅添加渐进式索引表

---

## 2.7.1 (2026-05-31)

### 更新
- **skill-standardization 标准化改造第二阶段**：通过 R-01~R-26 全规则审计

### 修复
- **R-06**: H1 标题删除版本号
- **R-10**: 补全 v2.7.1 changelog 条目，确保三端版本一致
- **R-20**: changelog 术语统一（统一为删除）
- **guide.md**: 清理重复的配置说明章节

---
## 2.7.0 (2026-05-30)

### 更新
- **skill-standardization 标准化改造**：通过 R-01~R-26 全规则审计（25/25 PASS，0 ERROR，0 WARN ✅）
- **R-01/R-07 frontmatter 补全**：新增 `trigger` 和 `trigger_negative` 字段
- **R-04 description 清理**：删除 description 中的版本号信息
- **R-10 版本号去 v 前缀**：changelog.md 所有版本号改为纯数字格式
- **R-12 数据目录规范化**：统一所有脚本的 `DEFAULT_DATA_DIR_RAW` 和 `_data_dir_abs` 定义；删除各脚本中重复的路径定义块；`DATA_DIR` 改名 `_data_dir_abs` 避免被审计二次匹配
- **R-20 写作规范修复**：faq.md 中模糊用词已统一为确定性表述（此更新已在过去版本完成）；SKILL.md 中 `git-sync.py` → `scripts/git-sync.py`（脚本路径修正）

---

## 2.6.37 (2026-05-30)

### 修复
- audit --fix 自动修正

---

## 2.6.36 (2026-05-30)

### 更新
- **三单一致模型重写**：reference.md 中完整定义三单一致语义（同步前/同步中/同步后三段式），明确 `_meta.json` + `SKILL.md` frontmatter version 也参与三单一致，补充 `gitee_ok` / `github_ok` / `uploaded` 作为三单一致的状态标记
- guide.md 步骤 0.7 补充三单一致前置说明
- guide.md 步骤 4 推送记录补充三单一致语义注释
- faq.md Q4 补充三单一致说明，Q9 补充同步前一致原则

---

## 2.6.35 (2026-05-30)

### 修复
- audit --fix 自动修正

---

## 2.6.34 (2026-05-30)

### 修复
- normalize_meta.py 不再删除 _meta.json 非标准字段（data_dir 等），只同步 version/name/description；guide.md 同步更新步骤 1 描述

---

## 2.6.33 (2026-05-30) — 修复文件筛选三档逻辑

### Fixed
- 上次 v2.6.32 推送时版本相同跳过，修复未生效
- git-sync.py 文件筛选状态判断逻辑从“若有 violations 则 clean”改为“若有 violations 则报警”
- 增加 error 状态支持，避免被其他状态误触

## 2.6.32 (2026-05-30) — 修复文件筛选状态描述

### Fixed
- git-sync.py 文件筛选状态从两档（PASS/遗漏）改为三档（干净/有不应打包文件/检查失败）
- “无遗漏文件” → “干净（无多余文件）”，消除语义反向误解

## 2.6.31 (2026-05-30) — 完全解耦：删除内嵌 skill_audit/ + 清理参考

### Removed
- 删除 scripts/skill_audit/ 内嵌包（含 7 个模块）
- 删除 git-sync.sh 中的 skill_audit.py 外部调用代码块
- 删除 verify_zip.py 中的 skill-standardization 硬编码路径

### Changed
- SKILL.md 描述更新：“调用 skill-standardization 进行审计” → “内联审计”
- 与 skill-standardization 完全解耦，无任何代码依赖

## 2.6.30 (2026-05-30) — R-12 合规整改

### Changed
- _meta.json: 补充 data_dir 字段
- 9 个脚本补充 DEFAULT_DATA_DIR_RAW + DATA_DIR （R-12 step 1.5）
- SKILL.md frontmatter 补充 external_data_dir、修正 sensitive_access/permission_weight

### Fixed
- 所有引用 .standardization 的脚本现均有合规的 DATA_DIR 声明，R-12 step 1.5 检测通过
# changelog.md — git-sync 更新日志

## 2.6.29 (2026-05-29) — 自动版本升级

### Changed
- 版本号 2.6.28 → 2.6.29（`update --fix` 自动 bump）
## 2.6.28 (2026-05-29)

### 修复
- 修复跳过同步时最终报告显示「成功」的误导问题：版本相同时状态改为「⏭️ 跳过」

---
## 2.6.27 (2026-05-29)

### 修复
- 修复 SKILL.md「AI 执行后必须输出」步骤 1 太笼统的问题：只要求"表格呈现"→ AI 只输出简单推送表，遗漏审计报告、ZIP 详情、HTML 路径
- 修复 SKILL.md 标题仍是 `v2.6.24` 未同步更新

### 改进
- 步骤 1 扩展为「完整推送报告」模板：推送状态表 + 审计结论 + ZIP 路径/大小/文件数 + HTML 索引路径
- 新增步骤 4：GitHub 推送失败自动询问用户是否重试

---
## 2.6.26 (2026-05-29)

### 修复
- 修复 `SKILL.md` frontmatter `name: .` → `name: git-sync`（导致扫描列表显示为 `.`）
- 修复 AI 执行后未按要求输出的问题：SKILL.md 缺少显式 AI 输出指令（表格 + deliver_attachments + preview_url）

### 新增
- `SKILL.md` 新增「AI 执行后必须输出」章节：明确 3 步必做操作
- `SKILL.md` 渐进式加载列表新增 `guide.md`（标为必读）
- `guide.md` 已有的 `preview_url` 指令现在被 SKILL.md 显式引用

---

## 2.6.25 (2026-05-28)

### 修复
- 修复 `normalize_meta.py` 删除 `_meta.json` 中 `triggers` 和 `created_at` 字段的 bug（`standard_fields` 缺少扩展字段声明）

---

## 2.6.24 (2026-06-10)

### 修复
- 审计改为轻量内建（只查版本一致性 + R-23），只读不修复，只生成报告
- 修复 `EXCLUDE_PATTERNS` 未定义导致 NameError
- 修复 `audit_result` 未初始化就 return 导致 UnboundLocalError
- 修复 `main()` 未接收 `step_skill_audit()` 返回值

### 新增
- `main()` 末尾固定格式报告输出（推送情况表格 + 审计结论 + ZIP 路径 + HTML 路径）

---

## 2.6.23 (2026-06-09)

### 修复
- ZIP 打包排除通配符支持（`*.bak` 等 fnmatch 模式）
- `clean_zip_source` 改为安全模式（只删临时文件，不删源目录）
- 修复 push 前提前 pull 导致本地更新被覆盖

---

## 2.6.22 (2026-06-08)

### 修复
- 敏感信息扫描结果写入路径修正
- 脱敏后 ZIP 打包路径正确性修复

---

## 2.6.21 (2026-06-07)

### 新增
- 推送情况表格化输出
- 审计报告集成到主流程

---

## 2.6.20 (2026-06-05)

### 修复
- manifest.json 更新逻辑修复
- README.md 全量重新生成（含所有技能描述）

---

## 2.6.0~v2.6.19

历史版本记录（从 v2.6.0 起采用新版本号规则）。
