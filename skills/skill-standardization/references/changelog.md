## [2.95.5] - 2026-06-24

### 修复
- `--json` 输出污染：`_semantic_precheck()` 检测到 `--json` 参数时将门禁文字写入 stderr 而非 stdout，确保 JSON 流可解析

### 更新
- `.standardization/skill-standardization/` 数据目录文档修正为 per-skill 子目录结构，移除不存在的 `logs/ops.log`，backup 格式修正为 `.bak`
- `audit-all` 能力边界描述修正：从"仅支持一级子目录"改为"遍历所有子目录，不自动排除"

## [2.95.4] - 2026-06-24

### 修复
- fix 循环无限循环根因：`fixes_applied == 0` 时 fix key 不清除（原逻辑 `fix_key in fix_details` 因 fix_details 为空永远不成立），改为无条件 `del res["fix"]`
- fix 循环 R-25 fix key 反复注入：加 `loop_count == 1` 条件，仅首轮注入，避免 auto-fix 死循环
- `_run_audit_loop()` 修复指引：`apply_fix()` → "手动编辑 SKILL.md 或 references/"
- 移除循环内所有 `--classify` 出口文案（误判标记仅在前置 LLM 二次筛查阶段进行）

### 更新
- `.standardization/skill-standardization/` 数据目录结构说明：调整为 per-skill 子目录结构，移除不存在的 `logs/ops.log`，backup 格式修正为 `.bak`（原文档写 `.zip`）
- `audit-all` 能力边界描述：从"仅支持一级子目录"改为"遍历所有子目录，不自���排除"
- 修复 `--json` 模式输出污染：`_semantic_precheck()` 在 `--json` 请求时将门禁文字输出到 stderr 而非 stdout，确保 JSON 流纯净
- R-17 修复指引：从"添加「→ 详见 references/xxx.md」散落引用"改为"优先使用渐进式文件索引表，禁止正文散落引用"，解决与 C-13 的矛盾
- C-12 约束上限：从 5 条改为 9 条（适应多钩子技能的需求）
- `.fix_loop_check.json` 循环检测改用动态技能名路径（原硬编码为 novel-weaver）

## [2.95.3] - 2026-06-22

### 修复
- `_run_audit_loop()` 锁函数名 typo：`_create_refactor_lock()` → `_lock_refactor()`
  - 之前 NameError 导致 `.refactor_locked.lock` 从未被创建，`sys.exit(2)` 也跑不到
  - 剩余 LLM 修复项时 exit code=1（崩溃）而非 2（强制锁定），LLM 可绕过循环
- `_semantic_precheck()` 模式锁：refactor 模式下允许 `audit --classify` 通过（二次筛除是 refactor 流程的内置步骤）

### 新增
- `--classify --category engine_cant_judge` 的 `--reason` 改为**必填**，且必须包含文件路径/行号证据
- 纯嘴说"引擎无法理解"不再被接受，须提供如 `permissions.md:91 YYYY 是年份通配符` 的具体定位

## [2.95.2] - 2026-06-21

### 修复
- SKILL.md 能力与限制表：`--audit-all` 参数形式修正为 `audit-all` 子命令
- references/guide.md：`audit --verify` 示例补齐缺失的 `--confirmed` 参数；`update --continue` 改为 `refactor --continue`（update 实际不支持 --continue）
- references/reference.md：从"部分内容已过时"模糊状态改为明确的已废弃声明，指向 guide.md 和 rules.md
- references/faq.md：删除无关的 `_skillhub_meta.json` 历史遗留 QA
- SKILL.md + _meta.json：description 精简，去除旧 changelog 残留文字

---

## [2.95.1] - 2026-06-21

### 修复
- C-12 触发条件格式检查：`"**正向触发**" in sec_body` 字符串精确匹配不支持冒号变体，改为 `r'\*\*正向触发(：)?\*\*'` 正则，兼容 `**正向触发**` / `**正向触发：**` / `**正向触发**：` 三种写法
- 一致性审查 missing_doc_ref 死循环：auto-fix 不可修复时循环 20 轮才终止，改为首次发现即保存 `.remaining_llm.json` 后 `sys.exit(0)` 清爽退出，由 LLM `--classify` 处理误报后 `--continue`

---

## [2.95.0] - 2026-06-20

### 修复
- 文档同步更新: --classify 改为必须带 --category; --mode 改为必传; _llm_only_fix_keys 新增 section_names; guide.md 命令示例全部加 --category

---

## [2.94.0] - 2026-06-20

### 修复
- --category 误判类别强制 + --mode 必传 + 修复循环 exit(2) 阻断 + body.json 合法化 + C-11 三层 instruction + 一致性审查嵌套目录修复 + OMP 硬编码泛化

---

## [2.93.2] - 2026-06-20

### 修复
- 修复: _run_audit_loop 前置LLM二次筛阻断点被 refactor --continue 绕过（skip_llm_prefilter=True）。移除该跳参，改为无条件检查 --classify 数据是否存在

---

## [2.93.1] - 2026-06-19

### 修复
- 修复: 重构锁机制(_lock/_unlock/_is_locked) + classify自动验证 + R-XX误判ID支持 + step5误报过滤 + 报告生成锁阻断

---

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
