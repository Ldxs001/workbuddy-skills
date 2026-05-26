# git-sync 版本更新日志

---
---

## v2.6.23（2026-05-26）

> 发布日期：2026-05-26

**改写类型：Patch — 修复 ZIP 打包混入垃圾文件**

### 修复

- **`pack_zip.py`：排除规则支持 fnmatch 通配符**
  - `exclude_files`（精确匹配）→ `exclude_file_patterns`（fnmatch 通配符）
  - 新增模式：`*.bak*`、`fix_*.py`、`force_*.py`、`patch_*.py`、`insert_*.py`、`*_fixed.py`
  - 新增 UTF-8 输出配置（Windows 终端兼容）
- **`clean_zip_source.py`：改为安全模式**
  - 原实现会直接删除源目录文件，改为仅日志输出、不执行删除
  - 仅 `TEMP_DIR` 内的临时文件可安全清理

### 影响文件

- `scripts/pack_zip.py`
- `scripts/clean_zip_source.py`

---



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

