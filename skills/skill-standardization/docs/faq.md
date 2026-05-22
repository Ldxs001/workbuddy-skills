# 常见问题（FAQ）

> 本文件收集 skill-standardization v2 使用过程中的常见疑问和解答。
> 按「使用场景 → 技术细节 → 最佳实践」组织。

---

## 目录

1. [基础概念](#基础概念)
2. [create 模式](#create-模式)
3. [update 模式](#update-模式)
4. [refactor 模式](#refactor-模式)
5. [审查与规范](#审查与规范)
6. [渐进式 MD 体系](#渐进式-md-体系)
7. [版本管理](#版本管理)
8. [集成与扩展](#集成与扩展)

---

## 基础概念

### Q1: 什么是 SKILL.md 标准化规范草案 v0.1？

**A:** 这是 skill-standardization 的核心依据——一份定义了标准 Skill 文件应如何编写的规范文档。主要包含：

- **Frontmatter 规范**：3 个必须字段（name/version/description）+ 7 个可选字段
- **正文结构规范**：5 个必须章节 + 4 个推荐章节 + N 个可选章节
- **审查规则**：R-01~R-10 共 10 条自动检查规则

该草案存储在 `spec/frontmatter.json`、`spec/body.json` 和 `spec/rules.json` 中，可通过 `json_loader.py load` 查看。

### Q2: skill-standardization 和 git-sync 是什么关系？

**A:** 它们是协作关系：

```
git-sync（同步流程）
  └─ 步骤 3.5: 调用 skill_audit.py audit
       └─ skill-standardization（提供审查能力）
            ├─ R-01~R-10 规则检查
            └─ 输出报告（纯警告，不阻断同步）
```

git-sync 负责将 skill 推送到远程仓库，在推送前调用 skill-standardization 进行规范性检查。

### Q3: 「三级复杂度」是什么意思？

**A:** 标准 Skill 目录结构支持三种复杂度级别：

| 级别 | 内容 | 适用场景 |
|------|------|---------|
| **minimal** | 仅 `SKILL.md` + `_meta.json` | 纯提示型 skill（如 color-toolkit） |
| **standard** | + `scripts/` + `docs/` | 有脚本或辅助文档的 skill |
| **full** | + `assets/` + `tests/` | 复杂工具型 skill |

大多数 skill 属于 standard 级别。

---

## create 模式

### Q4: 创建后的 SKILL.md 有很多 TODO，我需要全部填完吗？

**A:** 不需要全部立即填完，但建议至少完成以下必填项：

**必须填写的 TODO：**
1. `description` — frontmatter 中的描述（create 时通过 --desc 可预设）
2. `触发场景` 章节 — 明确何时触发此 skill
3. `核心能力` 表格 — 列出至少 1 个核心功能
4. `快速开始` — 提供最简使用示例

**可以后续补充的：**
- 详细教程 → 拆分到 `docs/guide.md`
- 示例集合 → 拆分到 `docs/examples.md`
- FAQ → 拆分到 `docs/faq.md`

### Q5: create 生成的版本号为什么是 0.1.0？

**A:** 这是有意设计。按照 SemVer 规范：

- `0.x.y` 表示初始开发阶段，API 可能不稳定
- 首次正式发布时应升级到 `1.0.0`
- create 模板的 `0.1.0` 是起点，后续由开发者根据实际变更升级

### Q6: 可以自定义 create 模板吗？

**A:** 当前版本的模板硬编码在 `skill_builder.py` 的 `SKILL_TEMPLATE` 和 `META_TEMPLATE` 变量中。要修改模板：

1. 编辑 `scripts/skill_builder.py`
2. 找到第 ~34 行的 `SKILL_TEMPLATE` 字符串
3. 修改占位符或新增字段
4. 保存后下次 create 即生效

> 未来版本可能支持外部模板文件。

---

## update 模式

### Q7: update 和 refactor 怎么选？

**A:** 简单判断：

| 场景 | 选择 |
|------|------|
| 已基本标准，想检查是否有遗漏 | `update` |
| 结构混乱、根目录散落文件多 | `refactor` |
| 不确定 | 先 `update` 看报告，再决定 |

update 是**轻量检查**（只读+可选修复），refactor 是**重量改造**（移动文件+重组目录）。

### Q8: update --fix 会修改哪些内容？

**A:** 当前 --fix 仅自动修复以下项目：

| 修复项 | 动作 |
|--------|------|
| `_meta.json` 缺失 | 创建新的 _meta.json（含默认值） |
| `_meta.json` 缺少字段 | 补充空值（tags 为空数组） |

**不会自动修改的：**
- SKILL.md frontmatter（需手动添加）
- 缺失的正文章节（仅提示）
- 根目录散落文件（仅建议）

### Q9: update 报告中的 ERROR/WARN/PASS 是什么意思？

**A:**

| 类型 | 含义 | 处理建议 |
|------|------|---------|
| **PASS** (✅) | 该项检查完全通过 | 无需操作 |
| **WARN** (⚠️) | 存在不规范但非致命的问题 | 建议修复 |
| **ERROR** (❌) | 存在严重不规范 | 应尽快修复 |
| **💡** | 改进建议（非规则） | 可选优化 |

> 注意：这些分类是 skill-builder 自身的报告格式，与 R-01~R-10 审查规则的分类体系不同。R-01~R-04 为 ERROR 级，R-05~R-10 为 WARN 级。

---

## refactor 模式

### Q10: refactor 会删除我的文件吗？

**A:** 不会！refactor 的核心设计原则是**信息零遗漏**：

- ✅ 仅执行 `move`（移动）操作
- ❌ 绝不执行 `delete`（删除）操作
- ✅ 执行前强制备份（除非显式 `--no-backup`）
- ✅ 移动后验证总字节一致性（允许 1% 容差）

如果验证发现文件总大小差异超过 1%，会输出警告提示可能丢失。

### Q11: 什么时候应该用 --dry-run？

**A:** **几乎每次 refactor 都应先用 --dry-run！**

dry-run 会输出完整的迁移计划但不执行任何实际操作，让你确认：
- 哪些文件会被移动到哪里
- 哪些文件会保留在原位及原因
- 是否有意外情况

确认计划无误后再去掉 `--dry-run` 正式执行。

### Q12: refactor 后如何回滚？

**A:** refactor 默认会创建时间戳命名的备份目录：

```bash
# 备份位置示例：
./my-skill_bak_refactor_20260522_190000/

# 回滚方法（用备份覆盖当前目录）：
mv ./my-skill_bak_refactor_20260522_190000 ./my-skill
```

> 如果用了 `--no-backup`，则无法自动回滚！

### Q13: 我的旧版 `_skillhub_meta.json` 会被怎么处理？

**A:** 保留在原位，不参与迁移。refactor 检测到此文件时会在报告中标注为 "legacy meta (keep)"。

你可以：
- 手动将其内容迁移到新版 `_meta.json` 后删除
- 或者继续保留（不影响正常使用）

---

## 审查与规范

### Q14: R-01~R-04 是 ERROR 级，会阻止 git-sync 吗？

**A:** 不会！自 v2.0 起，所有审查结果均为**纯警告模式**：

- 即使有 ERROR 级问题，`skill_audit.py` 也始终返回退出码 `0`
- git-sync 收到退出码 0 后会继续后续同步步骤
- 审查报告会明确标注每个问题的严重程度供参考

这个设计的目的是**不阻断工作流**，让用户自行决定何时修复。

### Q15: 如何理解「同义词匹配」？

**A:** 审查规则中的章节检查使用模糊匹配。例如「触发场景」章节的匹配关键词包括：

`触发条件`, `触发场景`, `适用场景`, `触发`

只要 H2 标题包含其中任一关键词即视为通过。这允许一定的命名灵活性，同时保持语义一致性。

完整同义词表见 SKILL.md 中「审查规则」章节的同义关键词表格。

### Q16: 审查规则可以自定义吗？

**A:** 当前版本规则定义在 `spec/rules.json` 中，是静态 JSON 配置。要自定义规则：

1. 编辑 `spec/rules.json`
2. 添加/修改规则条目
3. 对应更新 `spec/_index.json` 的模块注册

> 未来版本可能支持外部规则文件加载。

---

## 渐进式 MD 体系

### Q17: docs/ 下的文件是必需的吗？

**A:** 不是。渐进式 MD 文件的设计原则是：

> **SKILL.md 必须可独立理解核心功能和使用方法。docs/ 下的文件是按需加载的补充材料，缺失不影响基本使用。**

对于 minimal 级别的 skill，可以完全不创建 docs/ 目录。
对于 standard/full 级别，建议至少有 `guide.md`。

### Q18: SKILL.md 超过 200 行怎么办？

**A:** update 检查时会提示超过 200 行的建议拆分。拆分策略：

1. 识别可独立成文档的大段落（如详细教程、大量示例）
2. 在 SKILL.md 中保留摘要 + 引用语法指向 docs/
3. 将详细内容移入对应 .md 文件

引用语法示例：
```markdown
→ 详见 `docs/guide.md` 完整教程
→ `docs/examples.md` 包含更多使用示例
```

### Q19: 渐进式文件的命名有规定吗？

**A:** 推荐使用以下标准命名（也是 progressive_md.json 中注册的标准文件）：

| 文件名 | 用途 |
|--------|------|
| `guide.md` | 详细教程 / 使用指南 |
| `examples.md` | 示例集合 / 用例库 |
| `reference.md` | API 参考 / 命令手册 |
| `faq.md` | 常见问题 / 疑难解答 |
| `changelog.md` | 版本更新日志 |
| `architecture.md` | 架构设计 / 模块说明 |

也可以根据 skill 特点增减文件，但建议保持命名一致性以便 AI 加载识别。

---

## 版本管理

### Q20: 版本号出现在哪些地方？需要全部保持一致吗？

**A:** 是的，以下是完整的版本号位置清单：

| # | 位置 | 说明 | 格式 |
|---|------|------|------|
| 1 | `SKILL.md` frontmatter `version:` | 主版本号 | SemVer（如 `2.0.0`） |
| 2 | `_meta.json` `"version"` | 元数据版本 | 与 SKILL.md 一致 |
| 3 | `manifest.json` `"version"`（如有） | 仓库注册版本 | 与上述一致 |
| 4 | 各 `spec/*.json` 的 `"_version"` | 规范文件自身的版本 | 通常跟随主版本 |
| 5 | `json_loader.py` 自述字符串 | 工具自身版本标识 | `vX.Y.Z` |
| 6 | `skill_builder.py` 自述字符串 | 工具自身版本标识 | `vX.Y.Z` |
| 7 | `skill_audit.py` 自述字符串 | 工具自身版本标识 | `vX.Y.Z` |

**位置 1-3 必须严格一致**（三方一致原则）。位置 4-7 跟随主版本号更新即可。

### Q21: 如何正确升级版本号？

**A:** 按照 SemVer 规范：

| 变更类型 | 示例 | 说明 |
|---------|------|------|
| Patch（补丁） | `2.0.0` → `2.0.1` | Bug 修复，无功能变化 |
| Minor（次版） | `2.0.0` → `2.1.0` | 新增向后兼容的功能 |
| Major（主版） | `2.0.0` → `3.0.0` | 不兼容的重大变更 |

升级步骤：
1. 修改 `SKILL.md` frontmatter 中的 version
2. 同步修改 `_meta.json` 中的 version
3. 如有 manifest.json，同步修改
4. 更新 spec/*.json 的 `_version`（如规范本身有变化）
5. 更新各脚本的自述字符串
6. 在 changelog.md 中记录变更内容

---

## 集成与扩展

### Q22: 可以在其他 Python 项目中导入这些脚本吗？

**A:** 可以，但需注意：

- 脚本设计为 CLI 工具（通过 `if __name__ == "__main__"` 入口）
- 函数级别的导入是安全的（如 `load_spec()`、`cmd_update()` 等）
- 所有依赖都是 Python 标准库，无第三方包

导入示例：
```python
import sys
sys.path.append("path/to/skill-standardization/scripts")
from json_loader import load_spec
from skill_builder import cmd_create, cmd_update, cmd_refactor
```

### Q23: 如何为新 skill 编写 spec JSON？

**A:** 如果要扩展规范体系（例如新增一种检查维度），需要：

1. 在 `scripts/spec/` 下新建 `.json` 文件
2. 在 `spec/_index.json` 的 `modules` 数组中注册
3. 在 `json_loader.py` 中确保能被 load 命令发现

JSON 文件的推荐结构：
```json
{
  "_version": "1.0.0",
  "_description": "简要描述",
  "_depends_on": ["frontmatter"], // 可选的依赖声明
  // ... 具体规范内容
}
```

### Q24: Windows 上路径斜杠有问题吗？

**A:** 脚本内部统一使用 `pathlib.Path` 处理路径，自动适配操作系统：

- Windows: `C:\Users\...` → 内部转为 Path 对象
- Linux/Mac: `/home/...` → 同上
- 输出路径显示时使用正斜杠 `/` 保持跨平台一致

CLI 参数传入的路径（反斜杠）会被 pathlib 自动规范化。
