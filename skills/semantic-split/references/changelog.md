# semantic-split 版本更新日志

---

## v2.2.0（2026-05-23）

**改写类型：skill-standardization 标准化改造（R-11 产出物迁移 + 结构补全）**

### 变更内容

#### R-11 产出物路径修正（铁律4）
- `data/capabilities/make_product_ppt_v1.json` 从技能目录迁移至 `~/.workbuddy/semantic-split/data/capabilities/`
- `scripts/json_manager.py` DATA_DIR 路径常量更新：`SKILL_DIR / "data"` → `Path.home() / ".workbuddy" / "semantic-split" / "data"`
- 旧 `data/` 目录已删除

#### 交叉引用修复（9处）
- `references/automation_tasks.md`：4 处 `data/` 路径 + 目录树更新
- `references/loading_decision_tree.md`：2 处路径引用更新
- `references/json_schema.md`：3 处 CLI 示例路径 + 目录树更新

#### 结构补全
- 新增「快速开始」章节（含 scan/categorize/create/generalize 四个核心命令示例）
- 知识库路径说明：`~/.workbuddy/semantic-split/data/`

#### 版本号同步
- SKILL.md `version:` `2.1.0` → `2.2.0`
- `_meta.json` `"version"` `2.1.0` → `2.2.0`

### 标准化审查结果
- ERROR=0, WARN=1, PASS=5（预修复：1E → 0E）

---

## v2.1.0（2026-05-22）

**改写类型：初始标准化**

- 初始版本，由 skill-standardization 引擎创建
