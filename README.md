# WorkBuddy Skills Repository

> **用户技能仓库** — 由 git-sync 自动同步维护。
> 最后更新：2026-05-27

本仓库存放 WorkBuddy 用户技能，支持码云（Gitee）和 GitHub 双平台同步。

---

## 技能列表

以下为仓库中实际存在的技能（由 `git-sync` 全量生成，请勿手动修改此表格）：

| 技能名 | 描述 |
|--------|------|
| `.dist` | 技能描述 |
| `.standardization` | 技能描述 |
| `color-toolkit` | 专业颜色工具集 - HEX/RGB/HSL/HSV/CMYK转换、四种对比度算法、智能配色推荐 |
| `drawiodo` | draw.io 自动做图 Skill。当用户要求画图、生成图表、做架构图、流程图、UML、ER图、时序图、思维导图等时触发。生成 .drawio 文件并用 draw.io 打开。支持思考-确认-迭代-版本回溯的完整工作流。 |
| `everything-search-breadmemory` | 基于Everything/es.exe的本地文件搜索引擎 + 面包屑知识管理系统 + 艾宾浩斯复习引擎 + 拓扑甜甜圈知识关联 + 容灾备份。Agent通用，CLI驱动。 |
| `git-sync` | 将skill代码规范化推送到码云、GitHub，并生成ZIP安装包。v2.6.23：ZIP打包排除通配符支持（*.bak*等）；clean_zip_source改为安全模式 |
| `round-robin-allocator` | 将 N 个对象在 T 个轮次中按比例分配 K 种选项，贪心算法确保每个对象尽量每轮获得不同选项。支持自然语言输入、一行统计数据解析、Markdown/CSV/HTML 三种输出。 |
| `semantic-split` | 语义拆分与智能规划技能。将自然语言拆分为结构化需求块，基于5W2H维度提取与约束标注增强语义理解，双视角推理整合为单一执行步骤，支持自增强json沉淀机制。 |
| `simulated-peak-plot` | 生成模拟峰图（高斯峰），用于色谱、光谱或任何信号可视化。支持自定义峰参数、噪声水平、基线设置、复合峰（N个子峰组合）、自定义坐标轴标题/单位、CSV完整数据导出、可点击的file:///路径输出、以及从设备导出数据导入CSV。 |
| `skill-standardization` | Skill 标准化规范引擎 v2.38.4。structure_checker.py 用 ast.parse() 替换 compile() 修复 SyntaxWarning；SKILL.md 新增排错止损规则；antipatterns.md 新增 AP-12/AP-13。 |
| `skill-sub` | skill-sub 调用链编辑器与粗粒度规划器 |
| `skills` | 技能描述 |
| `svg-composer` | SVG 拼接工具，支持内置 FontAwesome 字符集（0-9, A-Z）和四种拼接模式 |
| `triphasic-execution` | Execute→Review→Advance 三步循环执行框架 v5.15.0。修复渐进式加载说明、触发条件否定条件、术语不一致（设置→配置）、中英文混排、拼写错误（tAsk_progress.py → task_progress.py）。 |
| `universal-file-ops` | 为普通大模型/智能体用户提供一站式文件操作与 Python 代码质量保障能力。 v1.1.0：重建 python_env.py，修复 _log() 输出到 stderr，修复 utils.py VENV_DIR 定义顺序，18/18 功能测试通过。 支持：文件 CRUD、Python 环境管理、代码规范化/审查/OO 化/测试生成、沙箱验证。 |
| `workbuddy-fs-manager` | WorkBuddy 文件系统管理器技能。 |
| `workday-calendar` | 智能周历系统 v1.5.0 - 新增2026年排班表生成（export_excel/generate_schedule）、Excel导出、HTML/Markdown/Excel格式排班输出 |

---

## 目录结构

```
workbuddy-skills/
├── README.md
├── LICENSE
└── skills/
├── .dist/
├── .standardization/
├── color-toolkit/
├── drawiodo/
├── everything-search-breadmemory/
├── git-sync/
├── round-robin-allocator/
├── semantic-split/
├── simulated-peak-plot/
├── skill-standardization/
├── skill-sub/
├── skills/
├── svg-composer/
├── triphasic-execution/
├── universal-file-ops/
├── workbuddy-fs-manager/
└── workday-calendar/
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
