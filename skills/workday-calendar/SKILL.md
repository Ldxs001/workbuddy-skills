---
name: workday-calendar
version: 1.2.0
description: 智能周历系统 - 国家法定假日区间管理、年度工作日计算、周历生成、日程管理。支持数据本地JSON存储，AI友好调用接口。
trigger: 法定假日|周历|工作日|调休|补班|节假日|假日区间|年度工日|日程|安排|空闲时间
---管理、年度工作日计算、周历生成、日程管理。支持数据本地JSON存储，AI友好调用接口。
trigger: 法定假日|周历|工作日|调休|补班|节假日|假日区间|年度工日|日程|安排|空闲时间
---
## 触发条件

当用户出现以下意图时，加载本技能：

- 查询或管理**法定假日**、**补班日**、**调休**安排
- 计算**年度工作日**、**工作日统计**
- 生成**周历**、**日程安排**
- 查询某天的**空闲时间**、**日程安排**
- 添加、修改、删除**日程事件**
- 说出关键词："周历"、"工作日"、"假日区间"、"日程"、"安排"

---

# 智能周历系统 (Workday Calendar)

管理国家法定假日、补班日、自定义周末规则，计算年度工作日，生成周历，并支持个人日程管理。

## 核心能力

### 📅 工作日计算
- **法定假日区间管理** - 以区间形式存储节假日，支持AI批量导入
- **补班日管理** - 单独记录调休上班日期
- **周末规则可配置** - 支持单休、双休、大小周等各类工时制度
- **工作日计算** - 自动计算年度总工日，优先级：补班 > 节假日 > 周末

### 📊 日程管理
- **添加日程** - 指定日期、起止时间、标题、分类
- **删除/修改日程** - 支持CRUD完整操作
- **查询空闲时间** - 自动查找某日空闲时段
- **日程列表生成** - 自动生成未来N天日程文本

## 工作流程

### 首次使用 / 新年份
```
1. 初始化年度数据 → 2. 导入法定假日 → 3. 导入补班日 → 4. 核对规则确认表 → 5. 计算工作日
```
⚠️ **第4步必须执行**：使用 `rules` 命令查看规则确认表，核对节假日和补班日是否正确

### 日程管理
```
添加日程 → 查询/修改 → 查找空闲时间 → 生成日程列表
```

---

## 使用指南

### 1. 工作日计算

#### 计算年度总工日
```python
summary = calculate_total_workdays(2026)
# 返回:
# {
#   "year": 2026,
#   "total_workdays": 247,
#   "total_holidays": 118,
#   "holiday_count": 28,
#   "compensatory_count": 5
# }
```

#### 生成周历
```python
calendar = generate_weekly_calendar(2026)
for week in calendar:
    print(f"第{week['week_number']}周")
    for day in week['days']:
        if day['date']:
            print(f"  {day['date']}: {day['day_type']}")
```

#### 同步数据到新年份
```python
result = sync_year(2026, 2025)
# 返回: {"holidays_synced": 7, "compensatory_synced": 4}
```

### 2. 日程管理

#### 添加日程
```python
event, msg = add_schedule_event(
    title="团队会议",
    date="2026-05-20",
    start_time="14:00",
    end_time="15:00",
    description="项目进度讨论",
    category="会议"
)
# 返回: (事件对象, "日程已添加: 团队会议 (2026-05-20 14:00-15:00)")
```

#### 🛡️ 容灾备份（自动）

每次添加新日程前，系统自动创建 `.bat` 备份文件，确保意外情况下可一键回退。

```python
# 每次 add_schedule_event() 调用时自动执行，无需手动干预
# 备份文件存储在: data/backups/schedule_backup_01.bat ~ schedule_backup_09.bat
# 最多保留 9 个备份，超过后循环覆盖（最新覆盖最旧）
```

**恢复方式**：
```bash
# Windows: 双击 .bat 文件即可恢复
# 或命令行执行
cmd /c data/backups/schedule_backup_03.bat
```

**备份机制**：
- 每次 `add_schedule_event()` 保存前，自动将当前 `schedule_events.json` 备份
- .bat 文件使用 `certutil -decode` 自解码技术，无需依赖外部文件
- 编号 01~09 循环覆盖，第10个备份覆盖第1个

#### 列出指定日期日程
```python
events = get_schedule_by_date("2026-05-20")
for e in events:
    print(f"{e.start_time}-{e.end_time} {e.title}")
```

#### 查询空闲时间
```python
slots = find_free_slots(
    date="2026-05-20",
    start_search="09:00",
    end_search="18:00",
    min_duration=30  # 最小空闲30分钟
)
# 返回:
# [
#   {"start": "10:00", "end": "14:00", "duration": 240},
#   {"start": "15:30", "end": "18:00", "duration": 150}
# ]
```

#### 查询日期范围日程
```python
events = get_schedules_by_date_range("2026-05-20", "2026-05-25")
```

#### 删除日程
```python
msg = delete_schedule_event(event_id)
# 返回: "已删除日程: 团队会议"
```

#### 更新日程
```python
msg = update_schedule_event(
    event_id,
    title="新标题",
    start_time="15:00",
    end_time="16:00",
    status="completed"
)
```

#### 生成日程列表
```python
# 今天及后续7天
schedule_text = generate_today_schedule()

# 指定日期及天数
schedule_text = generate_daily_schedule("2026-05-20", 14)
```

---

## CLI 命令

```bash
# 规则确认（重要！初始化后必须执行，核对配置是否正确）
python workday_calendar.py rules 2026           # 导出规则确认表

# 工作日计算
python workday_calendar.py calculate 2026       # 计算年度工日
python workday_calendar.py calendar 2026        # 生成周历JSON
python workday_calendar.py sync 2026 2025       # 同步数据
python workday_calendar.py init 2026            # 初始化年度数据

# 日程管理
python workday_calendar.py add 2026-05-20 09:00 10:00 "晨会" "团队同步" 工作
python workday_calendar.py list 2026-05-20
python workday_calendar.py free 2026-05-20 09:00 18:00
python workday_calendar.py delete <event_id>
python workday_calendar.py update <event_id> --title="新标题" --status=completed
python workday_calendar.py schedule 7            # 生成7天日程列表
python workday_calendar.py today                 # 今天+7天日程
```

### ⚠️ 重要：规则确认表

初始化年度数据后，**强烈建议**执行 `rules` 命令查看规则确认表：

```
python workday_calendar.py rules 2026
```

该表会显示：
- 🔧 周末规则配置（双休/单休/大小周）
- 🎉 法定节假日列表及日期范围
- 💼 补班日列表
- ⚠️ 配置冲突警告
- 📊 年度统计摘要

请核对配置是否与官方发布的节假日安排一致。

---

## 数据存储位置

```
~/.workbuddy/skills/workday-calendar/data/
├── holiday_intervals_2026.json    # 2026年法定假日
├── compensatory_days_2026.json     # 2026年补班日
├── weekend_config.json             # 周末规则（全局）
├── schedule_events.json            # 日程事件（全局）
└── backups/                        # 容灾备份（自动）
    ├── schedule_backup_01.bat      # .bat 回滚脚本，最多9个循环覆盖
    ├── schedule_backup_02.bat
    ├── ...
    └── _backup_index.txt           # 循环索引（记录下一个写入编号）
```

---

## 优先级规则

### 日期类型优先级
| 优先级 | 类型 | 规则 |
|--------|------|------|
| 1 | **补班日** | 强制计为工作日 |
| 2 | **法定假日** | 强制计为休息日 |
| 3 | **周末** | 按配置的周末规则 |
| 4 | **工作日** | 其他日期 |

### 日程冲突检测
添加日程时会自动检测与现有日程的时间冲突。

---

## 典型场景

### 场景1：查工作日
```
用户：2026年有多少个工作日？
AI：调用 calculate_total_workdays(2026)
```

### 场景2：安排会议找空闲时间
```
用户：5月20日下午有什么空闲时间？
AI：调用 find_free_slots("2026-05-20", "09:00", "18:00")
返回：[{"start": "15:30", "end": "18:00", "duration": 150}]
```

### 场景3：添加新日程
```
用户：明天下午2点到3点我要开会
AI：调用 add_schedule_event("开会", tomorrow, "14:00", "15:00")
```

### 场景4：查看今天和未来几天的安排
```
用户：帮我看看这周有什么安排
AI：调用 generate_today_schedule()
```

### 场景5：删除或修改日程
```
用户：取消明天的会议
AI：先 list 找到ID，然后 delete <id>

用户：把下午的会议改到3点
AI：update <id> --start=15:00 --end=16:00
```

### 场景6：每天定时生成日程列表
用户可以设置自动化任务：
```
命令：python workday_calendar.py today
时间：每天早上 08:00
```

---

## 日程数据格式

```json
{
  "events": [
    {
      "id": "d008b885",
      "title": "团队会议",
      "date": "2026-05-20",
      "start_time": "14:00",
      "end_time": "15:00",
      "description": "项目进度讨论",
      "category": "会议",
      "status": "pending",
      "created_at": "2026-05-19T22:00:00",
      "updated_at": "2026-05-19T22:00:00"
    }
  ],
  "updated_at": "2026-05-19T22:00:00"
}
```

### 分类选项
- 工作
- 个人
- 会议
- 其他

### 状态选项
- pending（待完成）
- completed（已完成）
- cancelled（已取消）

---

## 相关文件

- `scripts/workday_calendar.py` - 核心计算逻辑
- `references/data_format.md` - 数据格式详细说明
- `data/` - JSON数据存储目录
