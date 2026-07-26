# Structured Writer · 结构化写作智能体 — 设计方案

> 创建日期：2026-07-26
> 状态：实施中

## 一、项目定位

一个带交互式规划界面的结构化写作助手。用户提供主题/提示词 → LLM 生成大纲 → 用户交互调整（排序、标记 RAG、设定字数）→ 逐节串行写作 → 输出 `.md` 文件。

- 通过 HTTP 调用 rag-assistant:8767 可选地获取 RAG 资料
- 不依赖 RAG 亦可独立运行

## 二、文件结构

```
structured-writer/
├── main.py                          # 入口：启动 Web 服务器
├── setup.bat                        # Windows 一键启动（双击）
├── config.json                      # 默认配置
├── requirements.txt                 # 依赖
├── README.md                        # 说明文档
├── SCHEMA.md                        # ⬅ 本文件，持久化方案
│
├── app/
│   ├── __init__.py
│   ├── web_ui.py                    # HTTP 服务器 + 内联 HTML/CSS/JS 界面
│   ├── config_manager.py            # 配置读写管理
│   ├── planner.py                   # 大纲规划器
│   ├── writer.py                    # 串行写作器
│   ├── rag_client.py                # RAG 客户端
│   ├── state_manager.py             # 状态管理
│   └── llm_client.py                # LLM 统一客户端
│
└── data/
    ├── sessions/                    # 会话状态 JSON
    └── outputs/                     # 最终 .md 文件
```

## 三、核心数据流

```
用户输入主题
    ↓
planner.plan_outline() → LLM 生成大纲 JSON
    ↓
Web UI 渲染交互式大纲（排序下拉框 + RAG 复选框 + 字数编辑）
    ↓
用户确认 → 发送写作指令 JSON
    ↓
writer.generate_article() → 按用户排序逐节串行写作
    ├─ 每节前：context_loader（前文 + 可选 RAG 资料）
    ├─ LLM 写正文
    └─ state_manager 更新进度
    ↓
合并全文 → 输出 .md → 显示下载链接
```

## 四、子结构定义

每个子结构 = 小标题下的多段落节（非单段）：

```json
{
  "id": "s1",
  "title": "技术路线对比",
  "subtitle": "ASIC vs GPU vs FPGA",
  "summary": "对比三种主流AI芯片架构的优劣",
  "word_count": 1200,
  "is_key": true
}
```

- `is_key: true` → 重点节，字数可上浮 50%
- 用户可修改字数、排序、RAG 开关和知识库选择

## 五、交互式大纲 UI

每个子结构显示为卡片：
- 排序下拉框：空/1/2/3/4...（空=按大纲原始顺序）
- RAG 复选框 + 知识库下拉列表
- 字数编辑输入框
- ⭐ 重点标记

## 六、写作管线

串行逐节，每节流程：
1. context_loader 加载上下文 → 主题 + 前文 + RAG + 字数约束
2. LLM 写正文
3. state 更新 + 追加到全文缓冲区
4. 下一节...

前文截断长度：800 字（最新内容）
RAG 可选：不查 RAG 也能写作

## 七、实施路线（3 Phase）

### Phase 1 — 基础可运行 ✅（已完成）
| # | 任务 | 文件 | 状态 |
|---|------|------|------|
| 1 | 搭骨架：main.py + web_ui.py 基本 HTTP | main.py, web_ui.py | ✅ |
| 2 | 配置 Tab + config_manager | web_ui.py, config_manager.py | ✅ |
| 3 | 对话 Tab 基础版 | web_ui.py | ✅ |
| 4 | LLM 客户端 | llm_client.py | ✅ |
| 5 | 状态管理器 | state_manager.py | ✅ |
| 6 | 大纲规划器 | planner.py | ✅ |
| 7 | 串行写作器基础版 | writer.py | ✅ |
| 8 | main.py 整合 + setup.bat | main.py, setup.bat | ✅ |
| 9 | 联调测试 | - | ✅ |
| 10 | 端口改为 8770 | 全项目 | ✅ |
| 11 | 异步生成 + 进度轮询 | web_ui.py | ✅ |
| 12 | 会话恢复（断线重连） | web_ui.py | ✅ |
| 7 | 串行写作器基础版 | writer.py | ⬜ |
| 8 | main.py 整合 | main.py | ⬜ |
| 9 | 联调测试 | - | ⬜ |

### Phase 2 — 交互式大纲 + RAG
| # | 任务 | 状态 |
|---|------|------|
| 1 | 前端渲染交互式大纲 HTML | ⬜ |
| 2 | JS 收集用户操作并提交 | ⬜ |
| 3 | 后端接收指令 + 重排序 + RAG 注入 | ⬜ |
| 4 | rag-assistant 外部 API 加 query 端点 | ⬜ |
| 5 | rag_client.py RAG 客户端 | ⬜ |

### Phase 3 — 打磨
| # | 任务 | 状态 |
|---|------|------|
| 1 | 写作进度实时显示 | ⬜ |
| 2 | .md 下载 | ⬜ |
| 3 | Session 恢复 | ⬜ |
| 4 | 错误处理/重试 | ⬜ |
| 5 | UI 细节打磨 | ⬜ |

## 八、关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Web 框架 | Python http.server | 无依赖，与 rag-assistant 一致 |
| 前端 | 内联 HTML/CSS/JS | 无框架，单文件部署 |
| 排序 | 下拉框 1/2/3/4 | 用户指定 |
| RAG 依赖 | 可选 | 用户指定 |
| RAG 接口 | HTTP → rag-assistant:8767 | 松耦合 |
| 字数控制 | 基础字数 + 重点上浮 50% | 灵活 |
| 前文传递 | 截断最新 800 字 | 防止超上下文 |
| 状态保护 | MD5 指纹 | 继承 novel-weaver |
