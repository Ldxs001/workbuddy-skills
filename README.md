# WorkBuddy Skills

wUwproject 原创技能合集，统一管理与发布。

## 技能列表

| 技能 | 说明 |
|------|------|
| `drawio-diagram` | draw.io 自动作图，支持流程图、架构图、UML、ER图、时序图、思维导图等 |
| `simulated-peak-plot` | 高斯峰模拟与可视化，支持多峰叠加、CSV 导入导出、网格线自定义 |
| `triphasic-execution` | Execute→Review→Advance 三步循环执行框架，防止无限死循环或单步骤卡住 |
| `everything-search-breadmemory` | 基于 Everything/es.exe 的本地文件搜索引擎 + 面包屑知识管理系统 + 艾宾浩斯复习引擎 |
| `git-sync` | 将 skill 代码规范化推送到码云、GitHub 并生成 ZIP 包，自动更新 README.md 技能列表 |
| `round-robin-allocator` | 均匀轮转分配，将 N 个对象在 T 个轮次中按比例分配 K 种选项，贪心算法尽量确保每轮不同 |
| `skill-sub` | 调用链编排技能，步骤级串联，三层回退执行，分级重试 |
| `svg-composer` | SVG 拼接工具，支持内置 FontAwesome 字符集和四种拼接模式 |
| `temp_svg-composer` | SVG 拼接工具（轻量版），支持内置字符集（0-9, A-Z, a-z）和外部 SVG 文件拼接 |
| `workday-calendar` | 智能周历系统，法定假日/补班日管理，工作日计算，日程管理 |
| `color-toolkit` | 专业颜色工具集，支持颜色编码转换、对比度计算、智能配色推荐、HTML 预览生成 |

## 目录结构

```
workbuddy-skills/
├── skills/
│   ├── drawio-diagram/
│   ├── simulated-peak-plot/
│   ├── triphasic-execution/
│   ├── everything-search-breadmemory/
│   ├── git-sync/
│   ├── round-robin-allocator/
│   ├── skill-sub/
│   ├── svg-composer/
│   ├── temp_svg-composer/
│   ├── workday-calendar/
│   ├── color-toolkit/
├── LICENSE
└── README.md
```

## 新增技能

1. 将技能文件夹放入 `skills/` 目录
2. `git add .` → `git commit -m "Add xxx skill"`
3. `git push gitee main` → `git push origin main`

## 远程仓库

- **Gitee**: https://gitee.com/wUwproject/workbuddy-skills
- **GitHub**: https://github.com/Ldxs001/workbuddy-skills
