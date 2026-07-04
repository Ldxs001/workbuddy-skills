# Skills Repository

> **用户技能仓库** — 由 git-sync 自动同步维护。
> 最后更新：2026-07-04

本仓库托管 wUwproject 技能合集，码云（Gitee）和 GitHub 双平台同步。

---

## 技能列表

以下为仓库中实际存在的技能（由 `git-sync` 全量生成，请勿手动修改此表格）：

| 技能名 | 描述 |
|--------|------|
| `activity-duration-estimation` | 活动历时估算 + WBS工作分解 + 项目文档生成 + 经济效益分析 + 挣值管理（Activity Duration Estimation & WBS & Project Docs & Economic Analysis & EVM）—— 支持三点估算/蒙特卡洛四种方法 + WBS项目规划与分解 + 项目文档双模式生成（手动空模版/逐节自动）+ ROI/NPV/IRR/BCR 经济效益分析 + PV/EV/AC/SPI/CPI 挣值管理。三库隔离架构：shared.db + economic.db + evm.db。输出自包含HTML评估报告、经济效益分析报告和挣值分析报告。 |
| `analysis-toolkit` | 检验检测行业质量控制和数据分析工具箱。覆盖室内质控、室间比对、批次间比对、方法验证、趋势监控五大场景。方法通用，跨领域适用。 |
| `color-toolkit` | 专业颜色工具集，支持颜色编码转换、对比度计算、智能颜色推荐、HTML预览生成。适用于UI设计、无障碍开发、配色方案生成等场景。 |
| `drawiodo` | draw.io 自动做图 Skill。当用户要求画图、生成图表、做架构图、流程图、UML、ER 图、时序图、思维导图等时触发。生成 .drawio 文件并用 draw.io 打开。支持思考-确认-迭代-版本回溯的完整工作流，8 个 Hook Point 安全校验。 |
| `everything-search-breadmemory` | 基于Everything/es.exe的本地文件搜索引擎 + 面包屑知识管理系统 + 艾宾浩斯复习引擎 + 拓扑甜甜圈知识关联 + 容灾备份。Agent通用，CLI驱动。 |
| `git-sync` | 将 skill 代码规范化推送到码云、GitHub，并生成 ZIP 安装包。修复_push_with_cred_url/pull_with_cred_url 未检查 URL 内嵌 token 的缺陷（remote URL 已含 token 时不需查 git-credentials）。 |
| `hug-html` | 8种原子组件自由组合 + 3级约束, cell merging, two-level module system (base + composite), 7+ built-in templates, grid-aware visual editor, style presets, post-generation audit, user template save-as, Chinese error handling |
| `latex-modular` | LaTeX 模块化组合技能。提取 LaTeX 文档头/组件（表格、图片、列表、章节样式）作为可组合模块，通过 Python 脚本稳定组合生成不报错的 lualatex 文档，支持从原始 LaTeX 代码重构进模块化体系。 |
| `local-rag-builder` | 本地 RAG 系统搭建技能，支持环境检测修复、嵌入模型多源下载、5种切分策略 + GuardStack + 后处理 + 插件注册、多知识库管理 + 自动分类规则、可调 Prompt、Web 可视化配置 + 极客模式 + 模板管理 |
| `memory-pet` | 宠物记忆压缩技能 - 通过文本块宠物交互触发记忆保存。纯ASCII文字图，Python全量管理，亲密度衰减与逃跑机制，跨平台智能体记忆系统。 |
| `novel-weaver` | 结构化小说写作辅助技能。场景配置→大纲生成→因果链双重验证→pipeline 流程门禁→子结构先行规划→情绪混合系统→文风约束→人格驱动→分段写作→连通性补充→风格校验+逻辑检查(含实体状态+关系链)+大纲忠实度+结尾收束验证+实体关系追踪+角色别名识别+跨章行为摘要。全流程硬约束+门禁跟踪。 |
| `round-robin-allocator` | 均匀轮转分配工具 — 将 N 个对象在 T 个轮次中按比例分配 K 种选项，最大化覆盖多样性，支持四种后处理模式调整重复分布。 |
| `semantic-split` | 语义拆分与智能规划。将自然语言拆分为结构化需求块，三管线协同调度（正则结构分析→bge 语义匹配→bge-reranker 重排序），5W2H提取与约束标注增强语义理解，双视角推理整合为单一执行步骤，自增强闭环自动沉淀能力级 JSON 模板，10门禁钩子系统管控流程。 |
| `simulated-peak-plot` | 生成模拟峰图（高斯峰），用于色谱、光谱或任何信号可视化。支持簇峰(N子峰各独立标注)/融峰(合成单标注)/单峰、负峰(倒峰)、标注控制(annotate)、扫描速率(scan_rate)、碰撞避让标注、自定义坐标轴/单位、CSV导出及CSV导入，**负峰（倒峰）**。 |
| `skill-function-test` | 技能场景测试套件 —— 备份 → 蓝皮书 → 配置确认 → S1-S3场景测试 → D1-D6功能测试 → S4执行忠实度 → 修复 → bump → 双格式报告 → 结论写入test-report.md。配置驱动流程，钩子强制阻断。 |
| `skill-standardization` | Skill 标准化规范引擎。支持 R-01~R-26 规范审查（audit / create / update / refactor / bump / readonly 六模式），含权限扫描、数据目录合规检查、渐进式加载、LLM 二次筛分类。 |
| `skill-sub` | 调用链编排技能 — 既是调用链编辑器，也是粗粒度规划器。理解用户意图 → 规划 Skill 参与顺序 → 更新/保存/推荐调用链 → 拼接为调用链（支持循环/分支编排、子步骤拓扑排序、准确步骤计数）。 |
| `svg-composer` | SVG 拼接工具，支持内置 FontAwesome 字符集（0-9, A-Z）和四种拼接模式 |
| `triphasic-execution` | Execute→Review→Advance 三步循环执行框架。增强步骤规划能力、增强语义理解；明确空转/重试/换思路/求助完整流转规则；最多重试3次、最多空转3次强制约束。 |
| `universal-file-ops` | 为普通大模型/智能体用户提供一站式文件操作与 Python 代码质量保障能力。支持文件 CRUD、Python 代码质量流水线、沙箱测试、流程钩子系统。 |
| `workday-calendar` | 智能周历系统。支持法定假日、补班日、轮休系统（跳过/不跳过法定假双模式）、特殊休息（公休/临修）、个人日程管理。 |

---

## 目录结构

```
workbuddy-skills/
├── Cogito_Scribit/
├── LICENSE
├── README.md
├── architecture/
└── skills/
```

---

## 如何使用

### 方式一：从码云（Gitee）安装
```bash
cd ~/.workbuddy/skills
git clone https://gitee.com/wUwproject/workbuddy-skills.git temp-skills
cp -r temp-skills/skills/* .
rm -rf temp-skills
```

### 方式二：从 GitHub 安装
```bash
cd ~/.workbuddy/skills/
git clone https://github.com/Ldxs001/workbuddy-skills.git temp-skills
cp -r temp-skills/skills/* .
rm -rf temp-skills
```

### 方式三：ZIP 包安装
从 Releases 下载对应技能的 ZIP 包，解压到 `~/.workbuddy/skills/` 目录。

---

## 维护说明

- 本仓库由 **git-sync** 技能自动维护
- README.md 由 `update_readme.py` **从仓库实际文件全量生成**，不手动编辑
- 维护清单：`skills/.standardization/git-sync/data/manifest.json`（记录计划管理的技能全集）
- 三单一致原则：**清单 ⊇ 仓库 = README.md**

---

## 许可证

MIT License
