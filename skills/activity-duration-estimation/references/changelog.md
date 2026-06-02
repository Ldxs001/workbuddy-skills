## 1.0.3 (2026-06-02)

### 修复
- 标准化改造+修复反模式格式+扩展FAQ内容+修复术语混用

---

## 1.0.2 (2026-06-02)

### 修复
- audit --fix 自动修正: writing_standards

---

# 更新日志 (Changelog)

## 1.0.1 (2026-06-02)

- 标准化改造：templates/ 迁移至 .standardization/ 数据目录
- 创建 scripts/ 目录（含 __init__.py）
- SKILL.md 拆分至 ≤230 行，符合 R-17 渐进式加载规范
- 添加渐进式文件索引表
- 删除全部耦合性词汇（"借鉴"等）
- 修复前端描述字段与 _meta.json 同步
- _meta.json 精简为 7 标准字段
- 修复 H1 位置（紧跟在 frontmatter 后）
- 修复代码块语言标识
- 修复 FAQ 格式为 Q:/A: 标准格式
- 修复反模式格式：`**错误做法**：`→`**错误做法：**`（冒号归入加粗）
- 修复术语混用："版本更新历史"→"版本更新记录"
- 扩展FAQ内容（OMP来源Q=34字/A=187字，内容完整）
- 修复 skill-standardization 的 fix.py import error（parse_simple_yaml_frontmatter 缺失）
- 扩展 fix_writing_standards 支持 R-18 反模式格式自动修正
