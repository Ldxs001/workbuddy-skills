# skill-sub 变更日志
## v1.19.2 (2026-05-26)

### 修复
- `calc_intent_similarity()` 分词 bug：`chain_words` 未做 `re.findall` 分词导致永远匹配不上；加入 `user_intent` 字段参与相似度计算
- `cmd_error_stats()` 日志目录路径错误：`log_dir` 手工拼路径改为使用 `LOGS_DIR`；文件读取改 `with open()` 上下文管理器

---
## v1.16.2 (2026-05-26)

### 修复（R-07/R-15/R-18/R-20 合规改造）
- 修复 `SKILL.md` frontmatter `name: .` → `name: skill-sub`
- 清理 frontmatter 中泄漏的审计控制字段（`antipattern_count` / `writing_standards` 等）
- `## 反模式` 独立章节删除，改为行内引用 `references/antipatterns.md`
- `## 注意事项` 改名为 `## 重要说明`，删除与 AP-01 重复的第1条
- `references/antipatterns.md` 标记格式修复（`**：` → `：**`）
- 版本号统一：`SKILL.md` 标题 / 正文 / frontmatter 全部为 `1.16.2`

### 新增
- `references/antipatterns.md` 已含 AP-01~AP-05 五条反模式（含 `**错误做法：**` / `**正确做法：**` / `**深层原因：**` 标记）

---

## v1.16.1 (历史版本)

- 早期版本变更记录...
