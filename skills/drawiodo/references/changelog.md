## 2.2.2 (2026-06-04)

### 修复
- audit --fix 自动修正: frontmatter_fields, h1, version, external_data_dir
- 修复 H1 不含技能名（# drawiodo: draw.io 自动做图 Skill）
- 补充 frontmatter trigger 字段（4 条触发规则）
- 修复 _meta.json description 与 SKILL.md 不一致
- 修复 SKILL.md data_dir 路径与 _meta.json 统一
- 修复 changelog.md 旧版本 v 前缀（v2.2.1 → 2.2.1）
- 移除 drawio.py 硬编码 LIB_DIR 路径，改用脚本所在目录
- 修复 drawio_templates.py import math 在文件末尾问题

---

## 2.2.1 (2026-05-30)

### 修复
- audit --fix 自动修正
