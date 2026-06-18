## [2.93.0] - 2026-06-18

### 修复
- 修复 _run_audit_loop 细碎循环分离策略（规则ID→fix-key粒度）、新增停滞检测（_fixes_applied+_prev_sig）、修复 _struct_dir 路径硬编码、统一文档描述

---

## [2.92.0] - 2026-06-18

### 修复
- v2.91.0 最终改造：文档更新+架构修复+创建骨架升级

---

## [2.91.0] - 2026-06-18

### 修复
- v2.90.0: 前置LLM二次筛阻断点钩子

---

## [2.90.0] - 2026-06-18

### 新增
- `_run_audit_loop()` 新增**前置 LLM 二次筛除阻断点**：
  - 流程: ①审计 → ②报告展示 → **③★LLM二次筛** → ④_filter_false_positives → ⑤细碎循环
  - 首次进入时检查 `--classify` 文件，无数据则阻断，输出 3 步操作指引
  - `--continue` 标志跳过阻断点，支持 LLM 标记误报后重新进入修复循环
  - 阻断点保存 `.remaining_llm.json`，`--continue` 时恢复

### 修复
- skill-standardization 自身标准化改造：模式-命令映射锁代码级强制 + SyntaxError 修复

---

## [2.88.2] - 2026-06-18

### 修复
- 修复 `structure_checker.py:254` f-string 内嵌 ASCII 双引号导致 SyntaxError

### 改进
- `_semantic_precheck()` 新增 `llm_mode` 参数，代码级校验语义自检闸门输出模式与当前子命令是否一致（模式-命令映射锁）
- 4 个子命令（audit/refactor/create/update）新增 `--mode` CLI 参数
- SKILL.md 新增「★ 模式-命令映射锁（代码级强制）」铁律，快速开始命令补上 `--mode` 参数

---

## [2.88.1] - 2026-06-18

### 修复
- R-07: 触发条件正/否定区域分离，仅计正向区域的 bullet，修正否定条件 bullet 被充作正向触发计数的缺陷
- R-07: 新增正向触发词内容质量检测，识别模板式/泛化话术
- C-13b/C-15: 扩展正则支持 Markdown 链接格式引用检测 + 残缺引用检测
- 规则 check 描述: 移除"必须修复""建议修复"等程度判断语，仅保留客观检查描述
- R-20 输出格式: 移除"🔴 必须修/🟡 需修/⚪ 可选择修"程度标签
- `_llm_only_rules`: 删除静态白名单，改为 fix key 自声明 auto-fix 能力
- references/faq.md: 审计报告分类表移除程度判断，改由 LLM 二次筛归类的客观描述

---

## [2.88.0] - 2026-06-17

### 修复
- refactor: skill-standardization

---


## [2.87.4] - 2026-06-17

### 修复
- 展示报告强制: 审计/改造完成后LLM必须用present_files打开报告给用户查看。

---
