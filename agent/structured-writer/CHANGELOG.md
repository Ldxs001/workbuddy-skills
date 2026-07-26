# Structured Writer 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本号遵循语义版本控制（`app/__init__.py` 唯一源）。

---

## [0.2.5b4] - 2026-07-26
### 修复
- PyPI long_description 缺失更新日志（CHANGELOG.md 未同步到构建目录）

## [0.2.5b3] - 2026-07-26
### 新增
- **PyPI 发布准备**：`app/` → `structured_writer/` 目录改名；新增 `LICENSE`（Apache 2.0）、`README.md`、`blueprint.json`
- **GitHub Actions 检测支持**：`publish-pypi.yml` 新增 `structured_writer/__init__.py` 路径匹配

### 变更
- `app/` 目录重命名为 `structured_writer/`（PyPI 包名兼容）
- 删除 `data/` 目录中输出文件和会话记录

## [0.2.5b2] - 2026-07-26
### 新增
- **两级 RAG 查询**：节级别查一次（背景资料）+ 每个子结构再查一次（针对性资料），prompt 分【背景资料】和【针对性资料】两段注入
- **实时状态显示**：进度轮询带 `status_text`，显示每步操作（"RAG查询: 白酒 → 技术演进背景" / "写作中: 自注意力机制"）
- **子结构写作要点显示**：大纲子结构下方灰色小字显示 `summary`
- **`state_manager.set_status_text()`**：写作过程中每步写入状态文本，自动持久化

### 修复
- RAG 错误不再塞进写作 prompt（超时/失败只写 status_text，不污染 LLM 输入）
- `rag_stats` 字段缺失导致 `get_progress` 报错

## [0.2.5b1] - 2026-07-26
### 新增
- **RAG 知识库对接**：新建 `app/rag_client.py`，支持通过 HTTP 调 rag-assistant 8767 外部 API 查询知识库
- **外部 API `/api/kb/query`**：rag-assistant 新增端点，接收 `query`/`kb`/`top_k`，调 `agent.rag.query()` 完整检索管线，不消耗 LLM token
- **RAG 状态探测 + 冷启动**：配置 Tab 自动检测 8767 在线状态（🟢/🔴），支持填路径后冷启动 rag-assistant 子进程（`--no-web --api-port 8767` → 修正为 `--port 18765 --api-port 8767`）
- **RAG 指示灯 + KB 下拉联动**：大纲卡片中勾选 RAG 后，显示可用知识库下拉列表（数据来自 `:8767/api/kb/list`），默认"自动KB"走路由
- **提示词模板系统**：预置 5 套模板（通用公文/新闻报道/论文综述/技术报告/自定义），配置 Tab 下拉切换 + 编辑器实时修改
- **子结构系统**：大纲每节含 2-4 个子结构，写作时逐子结构串行调用 LLM，`###` 标题分隔；planner 自动补全子结构缺失字段
- **大纲勾选/取消**：每节和每个子结构左侧加 checkbox，取消节=取消其下所有子结构，生成时自动过滤未勾选项
- **双级排序**：节排序用阿拉伯数字（1-N），子结构排序用罗马数字（i-iv）
- **续写机制**：检测 `finish_reason == "length"` 自动续写，最多 5 轮，保证长文不被截断；空内容（推理吃光 token）跳过续写
- **LLM 客户端增强**：`chat_detailed()` 返回 `{content, finish_reason}`；`max_tokens` 从 config 传入并存储，writer 不再自行覆盖

### 变更
- **端口改为 8770**：避开 rag-assistant 的 8765/8766/8767
- **LLMClient 存储 max_tokens**：config 中设置的上下文窗口真正生效，writer 不再自行计算导致 content 为空
- **配置 Tab 增加 Token 提示**：推理模型建议不低于 4096，长文建议 8192 以上

### 修复
- 跳过空子结构（推理模型 token 耗尽导致 content="" 时不输出空节标题）
- `ragKbs.map is not a function` — `Array.isArray()` 守卫
- KB 下拉为空 — 后端将 `/api/kb/list` 返回的字典转数组
- 会话切换不清消息区 — 先 `innerHTML = ''` 再加载
- `subprocess.PIPE` 缓冲区满卡死子进程 — 改为 `tempfile.NamedTemporaryFile`
- RAG 冷启动阻塞 HTTP 服务器 — 改为后台线程异步轮询
- Python GBK 编码崩溃 — `PYTHONIOENCODING=utf-8`

## [0.1.0] - 2026-07-26
### 新增
- 项目骨架：`main.py` + HTTP 服务器 + 配置/对话双 Tab
- LLM 统一客户端（LM Studio / Ollama）
- 会话状态管理 + MD5 指纹保护
- 大纲规划器（LLM 生成结构化 JSON 大纲）
- 串行写作器（逐节 context_loader + LLM 写作 + .md 输出）
- 异步后台生成 + 进度轮询
- 会话恢复（断线重连）
- setup.bat 一键启动
