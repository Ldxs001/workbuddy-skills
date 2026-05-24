# 权限说明

> 由 `permission_checker.py` 扫描生成，基于脚本实际文件操作行为计算风险权重。

## 风险等级

`low`（权重 **0.00%**）

## 扫描摘要

| 项目 | 值 |
|------|-----|
| 扫描文件数 | 1 |
| 扫描行数 | 1348 |
| 风险等级 | low |
| 权重 | 0.00% |
| 高权限操作 | 无 |

## 权限操作清单

脚本 `scripts/workday_calendar.py` 文件操作均为**数据读写**（JSON 配置文件），无删除/网络/子进程操作：

| 操作 | 文件路径 | 权限 |
|------|----------|--------|
| 读假日配置 | `.standardization/workday-calendar/data/holiday_intervals_YYYY.json` | 📖 读 |
| 写假日配置 | `.standardization/workday-calendar/data/holiday_intervals_YYYY.json` | ✏️ 写 |
| 读补班配置 | `.standardization/workday-calendar/data/compensatory_days_YYYY.json` | 📖 读 |
| 写补班配置 | `.standardization/workday-calendar/data/compensatory_days_YYYY.json` | ✏️ 写 |
| 读周末配置 | `.standardization/workday-calendar/data/weekend_config.json` | 📖 读 |
| 写周末配置 | `.standardization/workday-calendar/data/weekend_config.json` | ✏️ 写 |
| 读日程数据 | `.standardization/workday-calendar/data/schedule_events.json` | 📖 读 |
| 写日程数据 | `.standardization/workday-calendar/data/schedule_events.json` | ✏️ 写 |

## 授权方式

**`silent`**（静默执行，无需用户授权）

理由：
- 权重 0.00%，无高权限操作
- 仅读写本地 JSON 数据文件  
- 无网络访问、无子进程调用、无文件删除操作  

## 权重说明

权重 = Σ(操作风险分值) / 100，上限 100%。

本技能仅做本地 JSON 数据读写，风险分值为 0，故权重 0.00%。
