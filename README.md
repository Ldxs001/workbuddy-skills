# WorkBuddy Skills

Ldxs 原创技能合集，统一管理与发布。

## 技能列表

| 技能 | 说明 |
|------|------|
| `drawio-diagram` | draw.io 自动作图，支持流程图、架构图、UML、ER图、时序图、思维导图等 |
| `triphasic-execution` | Execute→Review→Advance 三步循环执行框架，双模式设计，跨平台通用 |
| `workspace-cleanup` | 工作区归档 + JSONL 幽灵任务清理，综合维护工具 |
| `workbuddy-fs-manager` | 跨平台文件系统管理，归档工作区、同步数据库、清理任务记录 |
| `simulated-peak-plot` | 高斯峰模拟与可视化，支持多峰叠加、CSV 导入导出、网格线自定义 |
| `workday-calendar` | 智能周历系统，法定假日/补班日/周末规则计算，日程管理，跨平台纯Python无依赖 |
| `svg-composer` | SVG符号横向/纵向拼接，支持预览HTML生成，四种拼接模式 |
| `color-toolkit` | 专业颜色工具集，支持颜色编码转换、对比度计算、智能配色推荐、HTML预览生成。适用于UI设计、无障碍开发、配色方案生成等场景。 |
| `git-sync` | 将skill代码规范化推送到码云、GitHub并生成ZIP包，自动更新README.md技能列表 |
| `round-robin-allocator` | 均匀轮转分配，将N个对象在T个轮次中按比例分配K种选项，贪心算法尽量确保每轮不同 |
| `everything-search` | 基于Everything/es.exe的本地文件搜索引擎 + 面包屑知识管理系统 + 艾宾浩斯复习引擎。Agent通用，CLI驱动。 |

## 目录结构

```
workbuddy-skills/
├── skills/
│   ├── drawio-diagram/
│   ├── triphasic-execution/
│   ├── workspace-cleanup/
│   ├── workbuddy-fs-manager/
│   ├── simulated-peak-plot/
│   ├── workday-calendar/
│   ├── svg-composer/
│   ├── color-toolkit/
│   ├── git-sync/
│   ├── round-robin-allocator/
│   └── everything-search/
├── LICENSE
└── README.md
```

## 新增技能

1. 将技能文件夹放入 skills/ 目录
2. git add . → git commit -m "Add xxx skill"
3. git push gitee main → git push origin main

## 远程仓库

- **Gitee**: https://gitee.com/wUwproject/workbuddy-skills
- **GitHub**: https://github.com/Ldxs001/workbuddy-skills
