# git-sync 完整使用指南

> 本文档是 SKILL.md 的渐进式补充，包含完整的执行流程、步骤详解和配置说明。

---

## 完整执行流程（步骤 0 → 6）

### 步骤 0：安全校验（v1.4 新增）

| 校验项 | 规则 |
|--------|------|
| 路径穿越防护 | 拒绝 `../`、`..\\`、`/` 开头、`C:` 开头 |
| 目标路径范围 | `realpath` 必须在 `WORK_REPO/skills/` 内 |
| 同步工具选择 | 优先 `rsync --delete`，不可用则 `rm -rf` + `cp -r` |

### 步骤 0.5：维护清单检查（v1.3 新增）

同步前自动检查 `manifest.json`，决定行为：

| 检查结果 | 行为 |
|---------|------|
| `FOUND:uploaded` | ✅ 继续执行 |
| `FOUND:not-uploaded` | ⏳ 继续执行，完成后标记 uploaded=true |
| `NOT_FOUND` | ❓ 询问：加入清单 / 仅本次同步 / 中止 |

### 步骤 0.7：版本号三方对比（v1.6 新增）

| 对比结果 | 行为 |
|---------|------|
| 清单无此条目 | ✅ 正常执行，完后写入 version 到清单 |
| 清单 version = 待更新 version | ❓ 询问是否跳过（默认跳过） |
| 清单 version < 待更新 version | ✅ 正常升级，更新清单 |
| 清单 version > 待更新 version | ❌ 版本异常，询问策略（覆盖/拉取/合并/中止） |

> 注：以 manifest.json 记录的 version 为准，仓库 _meta.json 仅作参考。

### 步骤 1：_meta.json 标准化校验

确保符合标准 5 字段结构：

| 标准字段 | 缺失时处理 |
|---------|-----------|
| `name` | 使用目录名 |
| `version` | 使用传入的 version 参数 |
| `description` | 从 SKILL.md 提取 |
| `author` | 从 config.json 读取（缺省为 `your-name-here`） |
| `tags` | 设为空数组 `[]` |

**自动删除非标准字段**：`slug`、`ownerId`、`publishedAt`、`display_name`、`platforms`

### 步骤 1.5：SKILL.md 规范化审查（v1.8 新增）

- **工具**：`skill_audit.py`（独立 Python CLI，零依赖）
- **规则集**：R-01 ~ R-10（4 ERROR + 6 WARN）
- **模式**：纯警告不阻断（始终 exit(0)）
- **输出**：人类可读终端报告 + 支持 `--json` 模式
- **特性**：同义词关键词匹配容忍章节命名不一致

### 步骤 2：同步文件到工作仓库

将技能从 `SKILLS_DIR/<skill-name>/` 同步到 `WORK_REPO/skills/<skill-name>/`。

### 步骤 3：全量重新生成 README.md

> **关键原则**：README.md = 仓库实际内容，不手动维护。

从仓库 `skills/` 目录实际扫描，全量替换 README.md 中的技能列表表格和目录结构。

### 步骤 3.5：SKILL.md 审查输出

审查结果以人类可读格式打印到终端：

```
==================================================
📋 Skill 更新检查报告: <skill-name>
==================================================

✅ 通过项:
   ✅ _meta.json 结构正常
   ...

⚠️  警告/建议:
   💡 具体警告信息...

结论: ERROR=0 WARN=1 PASS=5
```

### 步骤 4：提交并推送到双平台

```bash
git add → git commit → git pull --rebase → git push
```

推送结果分别记录：
- 码云成功 → 更新 `gitee_version` + 标记 `gitee_ok=true`
- GitHub 成功 → 更新 `github_version` + 标记 `github_ok=true`
- `uploaded` = `gitee_ok AND github_ok`

### 步骤 5：生成 ZIP 安装包

```
输出: SKILLS_DIR/.dist/<skill-name>-v<x.x.x>.zip
排除: *.zip, __pycache__/, .DS_Store, .git, *.html, *.log, ...
```

打包在临时副本中进行，不影响源文件。敏感信息过滤（如果启用）作用于副本。

### 步骤 6：统一输出 + HTML 索引

1. 复制 ZIP 到统一目录 `~/.workbuddy/skills/.dist/`
2. 自动生成/刷新 `index.html` 索引页（含 file:// 链接 + 文件大小 + 时间）
3. 自动打开 dist/ 目录（Windows explorer / macOS open / Linux xdg-open）

> **每次执行完毕后 AI 必须主动调用 `preview_url` 打开 index.html。**

---

## config.json 完整配置模板

```json
{
  "author": "你的作者名",
  "gitee": {
    "user": "你的码云用户名",
    "repo": "workbuddy-skills",
    "branch": "main",
    "remote_name": "gitee"
  },
  "github": {
    "user": "你的 GitHub 用户名",
    "repo": "workbuddy-skills",
    "branch": "main",
    "remote_name": "origin"
  }
}
```

**关键字段说明**：

| 字段 | 影响范围 |
|------|---------|
| `author` | `_meta.json` 默认作者名；敏感扫描中的用户名检测基准 |
| `gitee.user` / `github.user` | 生成的查看链接和 README 安装命令中的用户名占位符 |
| `gitee.repo` / `github.repo` | 工作仓库名称（通常两个平台相同） |
| `branch` | 推送目标分支（通常为 main） |
