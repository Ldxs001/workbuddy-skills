# git-sync 完整参考手册

> CLI 命令速查、路径变量、排除列表、文件结构规范。

---

## manifest.py 子命令速查

`manifest.py` 是独立 CLI，管理维护清单（manifest.json），不污染 git-sync 主流程。

### 清单条目结构（v1.7 更新）

```json
{
  "repos": {
    "workbuddy-skills": {
      "items": {
        "git-sync": {
          "type": "skill",
          "added_at": "2026-05-22",
          "uploaded": true,
          "gitee_ok": true,
          "github_ok": true,
          "version": "1.8.0",
          "gitee_version": "1.8.0",
          "github_version": "1.8.0",
          "note": ""
        }
      }
    }
  }
}
```

### 命令参考

```bash
# ── 查询类 ──
python manifest.py list                              # 列出所有条目
python manifest.py list workbuddy-skills             # 按仓库过滤
python manifest.py check workbuddy-skills my-skill    # 是否在清单内（退出码: 0=双 ok, 1=部分, 2=未找到）
python manifest.py version workbuddy-skills my-skill  # 查询版本号

# ── 更新类 ──
python manifest.py add workbuddy-skills my-skill --type skill              # 加入（默认 uploaded=false）
python manifest.py add workbuddy-skills my-skill --type skill --uploaded   # 加入并标记已上传
python manifest.py remove workbuddy-skills my-skill                       # 从清单删除
python manifest.py version workbuddy-skills my-skill 1.9.0                # 更新版本号（双平台）
python manifest.py version workbuddy-skills my-skill 1.9.0 --platform gitee  # 仅更新码云
python manifest.py set-uploaded workbuddy-skills my-skill --platform gitee   # 标记平台已上传
python manifest.py set-uploaded workbuddy-skills my-skill --platform both    # 标记双平台已上传

# ── 同步类 ──
python manifest.py diff workbuddy-skills            # 对比清单(uploaded=true) vs 仓库实际文件
python manifest.py sync-readme workbuddy-skills      # 根据仓库实际文件全量重新生成 README.md
```

### 三单一致模型

```
维护清单 (manifest.json)
    └─ 可含"只登记、未上传"条目 (uploaded:false)

执行端（仓库实际文件 skills/<name>/）
    └─ 清单中 uploaded=true 的子集

README.md（技能列表 + 目录树）
    └─ 由 sync-readme 全量生成，永远 = 仓库实际内容
```

> **不会出现 README 有但仓库没有的情况。**

---

## 路径变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SKILLS_DIR` | `~/.workbuddy/skills` | 技能源目录（本地 skill 所在位置） |
| `WORK_REPO` | `~/.workbuddy/workbuddy-skills` | Git 工作仓库（推送目标） |
| `MANIFEST_FILE` | `scripts/manifest.json` | 维护清单文件路径 |
| `DIST_DIR` | `SKILLS_DIR/.dist/` | ZIP 统一输出目录（v1.5 新增） |

## ZIP 打包排除列表

以下文件/目录**不会**被包含在生成的 ZIP 包中：

| 类别 | 排除项 |
|------|--------|
| 缓存 | `__pycache__/`, `*.pyc`, `.DS_Store`, `Thumbs.db` |
| 版本控制 | `.git/` |
| 打包产物 | `*.zip` |
| 本地预览 | `*.html` |
| 日志 | `*.log` |
| 脚本自身 | `git-sync.sh`, `update_manifest_version.py`, `preview_server.py`, `build_index_now.py` |
| 运行时数据 | `.decisions.json`, `.sensitive_scan_*.json` |
| 杂项 | `._*`, `ZIP_OUT`, `*.gitignore` |

## Skill 标准目录结构

```
<skill-name>/
├── SKILL.md                  # [必填] 技能主文件
├── _meta.json                # [必填] 元数据（5字段）
├── references/                     # [可选] 渐进式 MD 辅助文档
│   ├── guide.md
│   ├── examples.md
│   ├── reference.md
│   └── ...
├── scripts/                  # [可选] Python/Shell 脚本
│   ├── *.py
│   ├── *.sh
│   └── spec/
├── assets/                   # [可选] 静态资源
└── tests/                    # [可选] 测试文件
```

**根目录仅允许 SKILL.md 和 _meta.json。**

---

## 敏感信息过滤详细规则

### 检测规则完整表

| 类型 | 正则模式示例 | 严重度 | 说明 |
|------|-------------|--------|------|
| 邮箱地址 | `\w+@\w+\.\w+` | 🔴 critical | 任何 email 格式 |
| Token / API Key | `token=`, `api_key=`, `secret=` | 🔴 critical | 键值对形式的密钥 |
| 私钥内容 | `-----BEGIN .* PRIVATE KEY-----` | 🔴 critical | PEM 格式私钥 |
| 内网 IP | `10\.\d+`, `172\.(1[6-9]|2\d|3[01])\.`, `192\.168\.` | 🟡 medium | RFC1918 私有地址 |
| 本地绝对路径 | `[A-Z]:\\Users\\`, `/home/`, `/Users/` | 🟡 medium | 用户主目录路径 |
| 配置用户名 | config.json 中 author/gitee.user/github.user 的值 | 🟢 low | 来自配置的用户名 |

> **注意**：`_meta.json` 的 `author` 字段是署名，默认不脱敏。

### 三种运行模式

通过环境变量 `GIT_SYNC_SENSITIVE_MODE` 或 `--skip-scan` 参数控制：

| 模式 | 配置方式 | 行为 |
|------|---------|------|
| **交互提示**（默认） | 不配置或 `prompt` | 扫描后按文件粒度交互确认 |
| **总是脱敏** | `GIT_SYNC_SENSITIVE_MODE=always-sanitize` | 自动全部脱敏（非交互） |
| **保持不变** | `GIT_SYNC_SENSITIVE_MODE=keep-as-is` 或 `--skip-scan` | 跳过扫描，源文件不动 |

### 交互式确认选项

扫描完成后用户可选：

1. **全部脱敏** — 公开上架场景推荐
2. **全部保留** — 私有仓库场景
3. **逐个文件选择** — 对每个文件单独决定
4. **逐项细选** — 对单文件的每个敏感条目逐一确认
5. **中止同步/打包**

### 打包时行为

```
源文件（~/.workbuddy/skills/my-skill/）  ← 不变
     ↓ 复制到临时副本
临时副本（/tmp/xxx/）                     ← 执行脱敏操作
     ↓ 打包
输出 ZIP → .dist/my-skill-v1.0.0.zip
     ↓ 清理
临时副本删除
```

同步到仓库时，脱敏作用于工作仓库副本（WORK_REPO/skills/<name>/），源文件同样不变。
