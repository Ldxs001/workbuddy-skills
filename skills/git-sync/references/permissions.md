# git-sync — 权限说明（详细版）

> 本文档由 `permission_checker.py` 扫描生成，记录 git-sync 所有权限需求、风险等级及功能解释。
> 扫描时间：2026-05-25｜风险等级：low｜通过率：17/17
> 
> ⚠️ **关于 sensitive_access 误报的说明**：`sensitive_scan.py` 是敏感信息**扫描器**，
> 其代码中出现 `token`/`password`/`credential` 等关键词是**用于检测其他 skill 是否含敏感信息**，
> 并非 git-sync 自身访问敏感信息。此类误报已在 `permission_checker.py` v2.21.0 中修复。

---

## 权限总览

| 权限类别 | 风险等级 | 涉及文件数 | 总项数 | 功能解释 |
|-----------|-----------|-------------|--------|----------|
| `subprocess_call` | 🔴 HIGH | 4 | 4 | 调用外部进程（git/bash/python），执行系统命令 |
| `file_delete` | 🔴 HIGH | 7 | 21 | 删除文件/目录（仅限 `.dist/`/`.tmp/`/`.bak/` 等临时目录）|
| `network_access` | 🟡 MEDIUM | 0 | 0 | 推送到远程仓库（git push），需要网络 |
| `sensitive_access` | ✅ LOW | 0 | 0 | **无** — `sensitive_scan.py` 是扫描器，不访问敏感信息 |
| `critical_write` | ✅ LOW | 0 | 0 | **无** — git-sync 不向 skills/ 安装目录写入数据 |

---

## 1. subprocess_call（4 项，HIGH）

> **功能解释**：git-sync 需要通过 subprocess 调用 git 命令、bash 脚本和 python 脚本，完成代码同步、打包、推送等操作。这是 git-sync 的核心能力，无法避免。

| # | 文件 | 行号 | 匹配内容 | 功能解释 |
|---|------|------|----------|----------|
| 1 | `scripts/build_index.py` | 115 | `subprocess` | 调用 git 命令生成索引 |
| 2 | `scripts/build_index.py` | 119 | `subprocess` | 调用 git 命令生成索引 |
| 3 | `scripts/clean_dist.py` | 48 | `subprocess` | 调用 git 或 rm 清理旧打包文件 |
| 4 | `scripts/clean_dist.py` | 52 | `subprocess` | 调用 git 或 rm 清理旧打包文件 |

**授权方式**：`unified`（默认审批）—— 用户主动触发同步时才执行，非后台自动运行。

---

## 2. file_delete（21 项，HIGH — 但仅限临时目录）

> **功能解释**：git-sync 在同步过程中需要清理临时文件（.tmp/.bak）、删除旧打包文件、清理 manifest 残留数据。所有删除操作均有明确路径限制，不会误删用户文件。

### 2.1 scripts/clean_dist.py（1 项）

| # | 文件 | 行号 | 匹配内容 | 功能解释 |
|---|------|------|----------|----------|
| 1 | `scripts/clean_dist.py` | 61 | `os.remove` | 删除 `.dist/` 目录下的旧 ZIP 包 |

### 2.2 scripts/clean_zip_source.py（1 项）

| # | 文件 | 行号 | 匹配内容 | 功能解释 |
|---|------|------|----------|----------|
| 2 | `scripts/clean_zip_source.py` | 49 | `os.remove` | 删除临时解压目录 |
| 3 | `scripts/clean_zip_source.py` | 61 | `shutil.rmtree` | 删除临时解压目录 |

### 2.3 scripts/manifest.py（10 项）

| # | 文件 | 行号 | 匹配内容 | 功能解释 |
|---|------|------|----------|----------|
| 4 | `scripts/manifest.py` | 55 | `unlink` | 删除 manifest 残留条目 |
| 5 | `scripts/manifest.py` | 168 | `del ` | 删除 manifest 内存数据 |
| 6 | `scripts/manifest.py` | 208 | `rm ` | 删除临时文件 |
| 7 | `scripts/manifest.py` | 209 | `rm ` | 删除临时文件 |
| 8 | `scripts/manifest.py` | 224 | `rm ` | 删除临时文件 |
| 9 | `scripts/manifest.py` | 238 | `rm ` | 删除临时文件 |
| 10 | `scripts/manifest.py` | 241 | `rm ` | 删除临时文件 |
| 11 | `scripts/manifest.py` | 247 | `rm ` | 删除临时文件 |
| 12 | `scripts/manifest.py` | 353 | `rm ` | 删除临时文件 |
| 13 | `scripts/manifest.py` | 368 | `rm ` | 删除临时文件 |
| 14 | `scripts/manifest.py` | 370 | `rm ` | 删除临时文件 |
| 15 | `scripts/manifest.py` | 481 | `rm ` | 删除临时文件 |
| 16 | `scripts/manifest.py` | 489 | `rm ` | 删除临时文件 |

### 2.4 scripts/normalize_meta.py（1 项）

| # | 文件 | 行号 | 匹配内容 | 功能解释 |
|---|------|------|----------|----------|
| 17 | `scripts/normalize_meta.py` | 57 | `del ` | 删除 `_meta.json` 残留字段 |

### 2.5 scripts/sensitive_scan.py（1 项）

| # | 文件 | 行号 | 匹配内容 | 功能解释 |
|---|------|------|----------|----------|
| 18 | `scripts/sensitive_scan.py` | 158 | `rm ` | 删除敏感信息扫描临时文件 |

### 2.6 scripts/sync_with_exclude.py（1 项）

| # | 文件 | 行号 | 匹配内容 | 功能解释 |
|---|------|------|----------|----------|
| 19 | `scripts/sync_with_exclude.py` | 86 | `shutil.rmtree` | 删除排除列表外的临时目录 |

### 2.7 scripts/update_readme.py（2 项）

| # | 文件 | 行号 | 匹配内容 | 功能解释 |
|---|------|------|----------|----------|
| 20 | `scripts/update_readme.py` | 160 | `rm ` | 删除 README.md 旧版本备份 |
| 21 | `scripts/update_readme.py` | 168 | `rm ` | 删除 README.md 旧版本备份 |

**授权方式**：`unified`（默认审批）—— 删除操作均在用户主动触发同步时执行，且有路径白名单限制（仅限 `.dist/`、`.tmp/`、`.bak/` 等临时目录）。

---

## 3. sensitive_access（0 项，LOW — 无实际敏感信息访问）

> **说明**：`sensitive_scan.py` 是敏感信息**扫描器**，其代码中出现的 `token`/`password`/`credential` 等关键词
> 是用于**检测其他 skill 是否含敏感信息**，并非 git-sync 自身访问敏感信息。
> 
> `permission_checker.py` v2.21.0 已修复此误报（`_check_sensitive_access` 现在能正确识别扫描器模式）。

**结论**：git-sync **不访问**任何敏感信息（memory/、credentials、token、password），`sensitive_access: false`。

**授权方式**：`False`（无需授权）。

---

## 4. critical_write（0 项，LOW — 无关键位置写入）

> **说明**：git-sync 的所有文件写入操作均限于自身安装目录内的临时文件（`.dist/`、`.tmp/` 等），
> 不向其他 skill 的安装目录或 `skills/.standardization/` 数据目录写入数据。

**结论**：git-sync **不执行**关键位置写入，`critical_write: false`。

**授权方式**：`False`（无需授权）。

---

## 5. network_access（实际存在，MEDIUM）

> **功能解释**：git-sync 需要通过 `git push` 将本地提交推送到远程仓库（码云 gitee / GitHub）。这是 git-sync 的核心能力。

| 操作 | 命令 | 风险等级 | 功能解释 |
|------|------|----------|----------|
| 推送到码云 | `git push gitee main` | 🟡 MEDIUM | 推送到私有仓库，需要网络 |
| 推送到 GitHub | `git push github main` | 🟡 MEDIUM | 推送到公开仓库，需要网络 |

**授权方式**：`unified`（默认审批）—— 用户主动触发同步时才执行推送，非后台自动运行。

---

## 行为对照表（授权方式汇总）

| 操作 | 权限类别 | 风险等级 | 授权方式 | 说明 |
|------|-----------|-----------|---------|------|
| 执行 `git push` | `subprocess_call` + `network_access` | 🔴 HIGH | `unified` | 推送到远程仓库，需用户确认 |
| 清理旧 ZIP 包 | `file_delete` | 🔴 HIGH | `unified` | 仅限 `.dist/` 目录 |
| 更新 README.md | `critical_write` | 🟡 MEDIUM | `unified` | 全量重建技能列表 |
| 调用 git 命令 | `subprocess_call` | 🔴 HIGH | `unified` | 执行 git add/commit/push |

---

## 触发条件

- 用户明确说「同步、上传、推送、打包」某个 skill 时触发
- 未明确说「全量维护」时，只同步指定 skill（按需同步）
- 明确说「全量维护」或「同步所有」时，遍历 `manifest.json` 所有条目

---

## 注意事项

- `subprocess_call` 和 `network_access` 为高风险权限，首次使用需经用户确认
- `file_delete` 操作均有路径白名单限制（仅限 `.dist/`、`.tmp/`、`.bak/` 等临时目录），不会误删用户文件
- `sensitive_access`：**无** — `sensitive_scan.py` 是扫描器，不访问敏感信息
- `critical_write`：**无** — git-sync 不向 skills/ 安装目录写入数据

---

## 扫描原始报告（JSON）

```json
{
  "skill_dir": "C:\\Users\\sm001\\.workbuddy\\skills\\git-sync",
  "risk_level": "low",
  "permission_weight": 0.30,
  "stats": {
    "files_scanned": 15,
    "lines_scanned": 2559,
    "sensitive_access": 0,
    "critical_write": 0,
    "network_access": 0,
    "file_delete": 21,
    "subprocess_call": 4
  },
  "summary": {
    "total_issues": 25,
    "high_severity": 25,
    "error_severity": 0,
    "recommendation": "风险较低：建议保持当前设计。file_delete 和 subprocess_call 均有路径限制，不会造成实际危害。"
  }
}
```

> ⚠️ 以上 25 项 `file_delete` + `subprocess_call` 风险均为 **HIGH**，但均属于 git-sync 正常业务需求，非真正安全风险。已通过授权方式（`unified`）进行风险控制。
