# CHANGELOG

## 0.2.1 (2026-06-04)

### 修复
- **R-10**: _meta.json name 与 SKILL.md frontmatter 不一致，统一为 skill-function-test
- **R-11**: 清理根目录残留的 .scenario-test_*、.function-test_* 临时文件
- **R-11**: scenario_engine.py 正则路径触发产出物检测，改用编译变量
- **R-12**: backup.py _DATA_DIR 路径声明不符合 R-12 规范，按标准模式重写
- **R-12**: _meta.json data_dir 对齐 DEFAULT_DATA_DIR_RAW（统一为 with /data/ 后缀）
- **R-06**: SKILL.md H1 对齐目录名 skill-function-test
- **R-18**: 创建 references/antipatterns.md（4 条反模式）
- **R-19**: 创建 references/faq.md（5 个 Q&A，### 子标题格式）

---

## 0.2.0 (2026-06-04)

### 新增
- **场景测试**：S1 场景链路完整性、S2 场景输入产出匹配、S3 场景数据流正确性
- **功能测试**：D1-D6 六个维度（语法解析、流程断点、数据污染、噪音、计算正确性、边界鲁棒性）
- **8 阶段流程**：备份 → 蓝皮书 → 询问 → 测试 → 修复 → 回归循环 → 回归确认 → 报告
- **阶段 7.5 LLM 后处理**：每条问题附带源代码上下文，辅助 LLM 判断误报
- **阶段 9 清理**：自动删除测试残留文件，管理备份目录
- **多语言修复器**：Python/Shell/JavaScript/PowerShell 通用修复工具
- `runner.py` 全流程编排器，代码硬编码 10 阶段不可跳过
