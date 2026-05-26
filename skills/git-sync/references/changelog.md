# git-sync 版本更新日志

---
---

## v2.6.22（2026-05-26）

> 发布日期：2026-05-26

**改写类型：Patch — 修复 push 前提前 pull 导致本地修改被覆盖的根因 bug**

### 修复

- **修复 push 前提前 pull 导致本地修改被覆盖（核心根因）**
  - 删除 `scripts/git-sync.py` push 前的 `_pull_with_cred_url()` 调用
  - 改为 push 失败时再执行 `pull --rebase` 后重试
  - 根因：`git-sync.py` 第 477/491 行 push 前先 pull → 远程旧版本（5-6 字段 frontmatter）覆盖本地新版本（11 字段）
- **修复 SKILL.md frontmatter 字段缺失**
  - 补全 11 字段（`artifact_paths`、`writing_standards`）
  - 删除非标准字段 `tags`

### 影响文件

- `scripts/git-sync.py` — `_push_with_cred_url()` 逻辑修复
- `SKILL.md` — frontmatter 11 字段完整化

---

## v2.6.21（2026-05-26）

