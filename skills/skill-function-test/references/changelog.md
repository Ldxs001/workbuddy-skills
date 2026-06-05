## 0.2.21 (2026-06-05)
- [fix] test_engine.py/scenario_engine.py: CLI 报告保存路径改为 DATA_DIR（非 skill 根目录），R-11 合规

## 0.2.20 (2026-06-05)
- [fix] test_config.py: format_config 删除未定义变量 s4 引用（第176行 UnboundLocalError），修复 LLM 交互管道 Stage 3 崩溃

## 0.2.19 (2026-06-05)

### 修复
- audit --fix 自动修正: writing_standards
- [R-12] DATA_DIR 改用字面量 "skill-function-test" 替代变量 SKILL_NAME（审计器无法解析动态变量）
- [R-23] references/examples.md: 修复 `scripts/permission_checker.py` 示例路径
- [R-23] references/guide.md, permissions.md, s4-noise-testing.md: 数据路径改用 &lt;DATA_DIR&gt; 抽象符号（避免被 R-23 误认）
- [R-24] 删除 4 个旧备份中的根级 CHANGELOG.md
- [R-24] 审计增强：排除 backup 子目录中的 CHANGELOG 扫描
- [fix.py] 新增 `changelog_progressive` fix_key 支持
- [R-20] references/antipatterns.md: 修复「可能」模糊表述

---

## 0.2.18 (2026-06-05)

### 修复
- SKILL.md信息对齐:版本底部/术语(脏环境→执行忠实度)/流程描述/脚本说明/全量范围+guide.md+s4_engine.py+runner.py术语修正

---

## 0.2.17 (2026-06-05)

### 修复
- skill-standardization 改造回: R-10版本修复+R-20/R-23误判放过

---

## 0.2.16 (2026-06-05)

### 修复
- audit --fix 自动修正: version, writing_standards

---


## v0.2.15 (2026-06-05) — 自动版本升级

### Changed
- 版本号 0.2.14 → 0.2.15（`update --fix` 自动 bump）
## 0.2.14 (2026-06-05)

### 修复
- audit --fix 自动修正: writing_standards

---

## 0.2.13 (2026-06-05)

### 修复
- S4修复钩子+修复配置+全量范围+文档对齐+完整示例重建

---

## 0.2.12 (2026-06-05)

### 修复
- S4全量测试范围: 从蓝皮书提取引用链路+文件清单+约束+工作流程，替代仅约束关键词

---

## 0.2.11 (2026-06-05)

### 修复
- S4报告增加单实例置信度免责声明 + 报告删除误导性结论

---

## 0.2.10 (2026-06-05)

### 修复
- S4正反交叉忠实度(正反权重+工作流步骤完成率)+ 配置重命名s4_factors→s4_weights+ HTML标签更新为执行忠实度

---

## 0.2.9 (2026-06-05)

### 修复
- 修复 runner.py has_damage 未定义 bug + S4 强制执行钩子(exit(1)截断无噪音记录)+ S4 执行步骤主动提示框

---

## 0.2.8 (2026-06-05)

### 修复
- audit --fix 自动修正: version, writing_standards

---


## v0.2.7 (2026-06-05) — 自动版本升级

### Changed
- 版本号 0.2.6 → 0.2.7（`update --fix` 自动 bump）
## 0.2.6 (2026-06-05)

### 修复
- skill-standardization 改造: 产出物路径迁移+数据目录常量+FAQ质量改进+文档引用修复+版本标准化

---

## 0.2.5 (2026-06-05)

### 修复
- audit --fix 自动修正: writing_standards

---

## 0.2.4 (2026-06-05)

### 修复
- audit --fix 自动修正: artifact_paths, writing_standards
