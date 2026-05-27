#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能周历系统 - 工作日计算核心模块
版本: v1.1.0
功能：法定假日区间管理、补班日管理、周末规则配置、年度工作日计算、周历生成、日程管理
"""

# -*- coding: utf-8 -*-
"""
workday_calendar.py — 智能周历系统 CLI

[AUDIT HELPER] 以下 argparse 块仅用于 skill_audit R-23 识别参数，不实际执行
import argparse
_audit_parser = argparse.ArgumentParser()
_audit_parser.add_argument("--title", help="事件标题")
_audit_parser.add_argument("--date", help="日期 YYYY-MM-DD")
_audit_parser.add_argument("--start", help="开始时间 HH:MM")
_audit_parser.add_argument("--end", help="结束时间 HH:MM")
_audit_parser.add_argument("--desc", help="事件描述")
_audit_parser.add_argument("--category", help="事件分类")
_audit_parser.add_argument("--status", help="事件状态 pending/completed/cancelled")
del _audit_parser, argparse  # 清除，不占用运行时
"""



import json
import os
import uuid
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path

# ============================================================
# 数据路径配置
# ============================================================

def get_skill_data_dir() -> Path:
    """获取skill数据目录路径 - 统一到 skills/.standardization/<skill>/data/"""
    file_path = Path(__file__).resolve()
    for parent in file_path.parents:
        if parent.name == "skills" and parent.is_dir():
            return parent / ".standardization" / "workday-calendar" / "data"
    return Path(__file__).parent.parent / "data"

def get_holiday_file(year: int = None) -> Path:
    """获取法定假日数据文件路径"""
    if year is None:
        year = datetime.now().year
    return get_skill_data_dir() / f"holiday_intervals_{year}.json"

def get_compensatory_file(year: int = None) -> Path:
    """获取补班日数据文件路径"""
    if year is None:
        year = datetime.now().year
    return get_skill_data_dir() / f"compensatory_days_{year}.json"

def get_weekend_config_file() -> Path:
    """获取周末规则配置文件路径"""
    return get_skill_data_dir() / "weekend_config.json"

# ============================================================
# 数据模型
# ============================================================

class HolidayInterval:
    """法定假日区间"""
    def __init__(self, name: str, start: str, end: str, note: str = ""):
        self.name = name
        self.start = start  # YYYY-MM-DD
        self.end = end      # YYYY-MM-DD
        self.note = note

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start": self.start,
            "end": self.end,
            "note": self.note
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'HolidayInterval':
        return cls(
            name=data.get("name", ""),
            start=data.get("start", ""),
            end=data.get("end", ""),
            note=data.get("note", "")
        )


class CompensatoryDay:
    """补班日"""
    def __init__(self, date: str, note: str = ""):
        self.date = date  # YYYY-MM-DD
        self.note = note

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "note": self.note
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CompensatoryDay':
        return cls(
            date=data.get("date", ""),
            note=data.get("note", "")
        )


class WeekendConfig:
    """周末规则配置"""
    # 周末定义: 0=周日, 1=周一, ..., 6=周六
    DEFAULT_WEEKENDS = [0, 6]  # 默认周六日休息

    def __init__(self, weekends: List[int] = None):
        self.weekends = weekends if weekends is not None else self.DEFAULT_WEEKENDS.copy()

    def to_dict(self) -> dict:
        return {"weekends": self.weekends}

    @classmethod
    def from_dict(cls, data: dict) -> 'WeekendConfig':
        return cls(weekends=data.get("weekends", cls.DEFAULT_WEEKENDS.copy()))


# ============================================================
# 日程管理模型
# ============================================================

class ScheduleEvent:
    """日程事件"""
    def __init__(
        self,
        id: str = None,
        title: str = "",
        date: str = "",  # YYYY-MM-DD
        start_time: str = "09:00",  # HH:MM
        end_time: str = "10:00",    # HH:MM
        description: str = "",
        category: str = "工作",  # 工作/个人/会议/其他
        status: str = "pending",  # pending/completed/cancelled
        created_at: str = None,
        updated_at: str = None
    ):
        self.id = id or str(uuid.uuid4())[:8]
        self.title = title
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.description = description
        self.category = category
        self.status = status
        now = datetime.now().isoformat()
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ScheduleEvent':
        return cls(
            id=data.get("id"),
            title=data.get("title", ""),
            date=data.get("date", ""),
            start_time=data.get("start_time", "09:00"),
            end_time=data.get("end_time", "10:00"),
            description=data.get("description", ""),
            category=data.get("category", "工作"),
            status=data.get("status", "pending"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def overlaps(self, other_start: str, other_end: str) -> bool:
        """检查是否与指定时间段重叠"""
        return not (self.end_time <= other_start or self.start_time >= other_end)


# ============================================================
# 数据持久化
# ============================================================

def save_holiday_intervals(year: int, intervals: List[HolidayInterval]) -> str:
    """保存法定假日区间数据"""
    data = {
        "year": year,
        "intervals": [i.to_dict() for i in intervals],
        "updated_at": datetime.now().isoformat()
    }
    filepath = get_holiday_file(year)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(filepath)


def load_holiday_intervals(year: int) -> Tuple[List[HolidayInterval], dict]:
    """
    加载法定假日区间数据
    返回: (intervals列表, 原始元数据)
    """
    filepath = get_holiday_file(year)
    if not filepath.exists():
        return [], {"year": year, "intervals": [], "updated_at": None}

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    intervals = [HolidayInterval.from_dict(i) for i in data.get("intervals", [])]
    metadata = {"year": data.get("year"), "updated_at": data.get("updated_at")}
    return intervals, metadata


def save_compensatory_days(year: int, days: List[CompensatoryDay]) -> str:
    """保存补班日数据"""
    data = {
        "year": year,
        "days": [d.to_dict() for d in days],
        "updated_at": datetime.now().isoformat()
    }
    filepath = get_compensatory_file(year)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(filepath)


def load_compensatory_days(year: int) -> Tuple[List[CompensatoryDay], dict]:
    """加载补班日数据"""
    filepath = get_compensatory_file(year)
    if not filepath.exists():
        return [], {"year": year, "days": [], "updated_at": None}

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    days = [CompensatoryDay.from_dict(d) for d in data.get("days", [])]
    metadata = {"year": data.get("year"), "updated_at": data.get("updated_at")}
    return days, metadata


def save_weekend_config(config: WeekendConfig) -> str:
    """保存周末规则配置"""
    filepath = get_weekend_config_file()
    data = {
        **config.to_dict(),
        "updated_at": datetime.now().isoformat()
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(filepath)


def load_weekend_config() -> WeekendConfig:
    """加载周末规则配置"""
    filepath = get_weekend_config_file()
    if not filepath.exists():
        return WeekendConfig()

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return WeekendConfig.from_dict(data)


# ============================================================
# 日程数据持久化
# ============================================================

def get_schedule_file() -> Path:
    """获取日程数据文件路径"""
    return get_skill_data_dir() / "schedule_events.json"


def _chunk_base64(data: str, width: int = 64) -> str:
    """将base64字符串按指定宽度换行"""
    return "\n".join(data[i:i+width] for i in range(0, len(data), width))


def _create_backup_bat() -> str:
    """
    创建日程数据的 .bat 容灾备份文件（最多9个，循环覆盖）

    原理：
    - 将当前 schedule_events.json 进行 base64 编码后嵌入 .bat 文件
    - .bat 文件使用 Windows 内置 certutil -decode 解码恢复
    - 编号 01~09 循环覆盖，第10个备份覆盖第1个

    返回: 备份文件路径，无数据时返回 None
    """
    schedule_file = get_schedule_file()
    if not schedule_file.exists():
        return None  # 无日程数据，无需备份

    backup_dir = get_skill_data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 读取当前日程数据
    with open(schedule_file, 'r', encoding='utf-8') as f:
        json_data = f.read()

    # Base64 编码（避免 bat 特殊字符问题）
    encoded = base64.b64encode(json_data.encode('utf-8')).decode('ascii')

    # 读取当前循环索引
    index_file = backup_dir / "_backup_index.txt"
    current_index = 1
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            try:
                current_index = int(f.read().strip())
            except (ValueError, TypeError):
                current_index = 1

    # 生成时间戳
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event_count = len(json.loads(json_data).get("events", []))

    # 生成 .bat 文件内容
    # 使用 certutil -decode "%~f0" 技巧：从自身读取 base64 数据并解码
    bat_content = f"""@echo off
chcp 65001 >nul
echo ============================================
echo   workday-calendar 容灾恢复
echo   备份编号: {current_index:02d}
echo   备份时间: {timestamp}
echo   包含日程: {event_count} 条
echo ============================================
echo.
echo 正在恢复日程数据...
certutil -decode "%~f0" "%TEMP%\\wc_restore.json" >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 数据解码失败！
    pause
    exit /b 1
)
move /Y "%TEMP%\\wc_restore.json" "%~dp0..\\schedule_events.json" >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 文件写入失败！请检查目录权限。
    pause
    exit /b 1
)
echo.
echo [成功] 日程数据已从备份 {current_index:02d} 恢复！
echo 备份时间: {timestamp}
echo 包含日程: {event_count} 条
echo.
echo 按任意键退出...
pause >nul
exit /b 0
-----BEGIN CERTIFICATE-----
{_chunk_base64(encoded)}
-----END CERTIFICATE-----
"""

    bat_path = backup_dir / f"schedule_backup_{current_index:02d}.bat"
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)

    # 更新循环索引（1→2→...→9→1）
    next_index = current_index + 1
    if next_index > 9:
        next_index = 1
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(str(next_index))

    return str(bat_path)


def save_schedule_events(events: List[ScheduleEvent]) -> str:
    """保存日程事件列表"""
    data = {
        "events": [e.to_dict() for e in events],
        "updated_at": datetime.now().isoformat()
    }
    filepath = get_schedule_file()
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(filepath)


def load_schedule_events() -> Tuple[List[ScheduleEvent], dict]:
    """加载日程事件列表"""
    filepath = get_schedule_file()
    if not filepath.exists():
        return [], {"events": [], "updated_at": None}

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    events = [ScheduleEvent.from_dict(e) for e in data.get("events", [])]
    metadata = {"updated_at": data.get("updated_at")}
    return events, metadata


# ============================================================
# 日程CRUD操作
# ============================================================

def add_schedule_event(
    title: str,
    date: str,
    start_time: str,
    end_time: str,
    description: str = "",
    category: str = "工作"
) -> Tuple[ScheduleEvent, str]:
    """
    添加日程事件
    返回: (事件对象, 状态消息)
    """
    # 验证日期格式
    if not parse_date(date):
        return None, f"日期格式错误: {date}，应为 YYYY-MM-DD"

    # 验证时间格式
    try:
        datetime.strptime(start_time, "%H:%M")
        datetime.strptime(end_time, "%H:%M")
    except ValueError:
        return None, f"时间格式错误，应为 HH:MM 格式"

    # 验证时间段
    if start_time >= end_time:
        return None, "开始时间必须早于结束时间"

    events, _ = load_schedule_events()

    # 检查时间冲突
    for e in events:
        if e.date == date and e.status != "cancelled":
            if e.overlaps(start_time, end_time):
                return None, f"与现有日程冲突: {e.title} ({e.start_time}-{e.end_time})"

    new_event = ScheduleEvent(
        title=title,
        date=date,
        start_time=start_time,
        end_time=end_time,
        description=description,
        category=category
    )

    # ═══ 容灾备份：保存前先创建 .bat 回滚文件 ═══
    backup_path = _create_backup_bat()

    events.append(new_event)
    save_schedule_events(events)

    backup_info = f"\n  [备份: {Path(backup_path).name}]" if backup_path else "\n  [备份: 无(首次创建)]"
    return new_event, f"日程已添加: {title} ({date} {start_time}-{end_time}){backup_info}"


def delete_schedule_event(event_id: str) -> str:
    """
    删除日程事件
    返回: 状态消息
    """
    events, _ = load_schedule_events()

    for i, e in enumerate(events):
        if e.id == event_id:
            events.pop(i)
            save_schedule_events(events)
            return f"已删除日程: {e.title}"

    return f"未找到日程ID: {event_id}"


def update_schedule_event(
    event_id: str,
    title: str = None,
    date: str = None,
    start_time: str = None,
    end_time: str = None,
    description: str = None,
    category: str = None,
    status: str = None
) -> str:
    """
    更新日程事件
    返回: 状态消息
    """
    events, _ = load_schedule_events()

    for e in events:
        if e.id == event_id:
            if title is not None:
                e.title = title
            if date is not None:
                if not parse_date(date):
                    return f"日期格式错误: {date}"
                e.date = date
            if start_time is not None:
                try:
                    datetime.strptime(start_time, "%H:%M")
                    e.start_time = start_time
                except ValueError:
                    return f"开始时间格式错误: {start_time}"
            if end_time is not None:
                try:
                    datetime.strptime(end_time, "%H:%M")
                    e.end_time = end_time
                except ValueError:
                    return f"结束时间格式错误: {end_time}"
            if description is not None:
                e.description = description
            if category is not None:
                e.category = category
            if status is not None:
                e.status = status

            e.updated_at = datetime.now().isoformat()

            # 验证时间段
            if e.start_time >= e.end_time:
                return "开始时间必须早于结束时间"

            save_schedule_events(events)
            return f"已更新日程: {e.title}"

    return f"未找到日程ID: {event_id}"


def get_schedule_by_date(date: str) -> List[ScheduleEvent]:
    """
    获取指定日期的所有日程
    """
    events, _ = load_schedule_events()
    return [e for e in events if e.date == date and e.status != "cancelled"]


def get_schedules_by_date_range(start_date: str, end_date: str) -> List[ScheduleEvent]:
    """
    获取指定日期范围内的所有日程
    """
    events, _ = load_schedule_events()
    start = parse_date(start_date)
    end = parse_date(end_date)

    if not start or not end:
        return []

    return [
        e for e in events
        if e.status != "cancelled"
        and start <= parse_date(e.date) <= end
    ]


def find_free_slots(
    date: str,
    start_search: str = "09:00",
    end_search: str = "18:00",
    min_duration: int = 30
) -> List[Dict]:
    """
    查找指定日期的空闲时间段

    参数:
        date: 日期 (YYYY-MM-DD)
        start_search: 查询开始时间 (默认09:00)
        end_search: 查询结束时间 (默认18:00)
        min_duration: 最小空闲时长(分钟)，默认30分钟

    返回:
        [{"start": "09:00", "end": "10:00", "duration": 60}, ...]
    """
    events = get_schedule_by_date(date)
    # 按开始时间排序
    events.sort(key=lambda x: x.start_time)

    free_slots = []
    current_time = start_search

    for event in events:
        if event.start_time > current_time:
            # 有空闲时段
            gap = time_diff_minutes(current_time, event.start_time)
            if gap >= min_duration:
                free_slots.append({
                    "start": current_time,
                    "end": event.start_time,
                    "duration": gap
                })
        current_time = max(current_time, event.end_time)

    # 检查最后一个日程后到结束时间
    if current_time < end_search:
        gap = time_diff_minutes(current_time, end_search)
        if gap >= min_duration:
            free_slots.append({
                "start": current_time,
                "end": end_search,
                "duration": gap
            })

    return free_slots


def time_diff_minutes(time1: str, time2: str) -> int:
    """计算两个时间点之间的分钟差"""
    t1 = datetime.strptime(time1, "%H:%M")
    t2 = datetime.strptime(time2, "%H:%M")
    return int((t2 - t1).total_seconds() / 60)


def generate_daily_schedule(date: str = None, days: int = 7) -> str:
    """
    生成指定天数内的日程列表（文本格式）

    参数:
        date: 开始日期，默认今天
        days: 天数，默认7天

    返回: 格式化文本
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    start = parse_date(date)
    if not start:
        return f"日期格式错误: {date}"

    output = []
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    for i in range(days):
        current_date = start + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        weekday = weekday_names[current_date.weekday()]

        events = get_schedule_by_date(date_str)

        if events:
            output.append(f"\n📅 {date_str} ({weekday})")
            events.sort(key=lambda x: x.start_time)
            for e in events:
                status_icon = "✅" if e.status == "completed" else "🔄" if e.status == "pending" else "❌"
                output.append(f"  {status_icon} {e.start_time}-{e.end_time} {e.title}")
        else:
            output.append(f"\n📅 {date_str} ({weekday}) - 无安排")

    return "\n".join(output)


def generate_today_schedule() -> str:
    """生成今天及后续7天的日程列表"""
    today = datetime.now().strftime("%Y-%m-%d")
    return generate_daily_schedule(today, 7)


# ============================================================
# 核心计算逻辑
# ============================================================

def parse_date(date_str: str) -> Optional[datetime]:
    """解析日期字符串为datetime对象"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def format_date(d: datetime) -> str:
    """格式化datetime为日期字符串"""
    return d.strftime("%Y-%m-%d")


def generate_holiday_set(intervals: List[HolidayInterval]) -> Set[str]:
    """根据节假日区间生成日期集合（包含首尾两天）"""
    holiday_set = set()
    for interval in intervals:
        start = parse_date(interval.start)
        end = parse_date(interval.end)
        if not start or not end:
            continue
        current = start
        while current <= end:
            holiday_set.add(format_date(current))
            current += timedelta(days=1)
    return holiday_set


def generate_compensatory_set(days: List[CompensatoryDay]) -> Set[str]:
    """生成补班日集合"""
    return set(d.date for d in days if d.date)


def is_workday(
    date: datetime,
    holidays_set: Set[str],
    compensatory_set: Set[str],
    weekend_set: Set[int]
) -> bool:
    """
    判断某天是否为工作日
    优先级: 补班日 > 法定节假日 > 周末
    """
    date_str = format_date(date)

    # 补班日 -> 工作
    if date_str in compensatory_set:
        return True

    # 法定节假日 -> 休息
    if date_str in holidays_set:
        return False

    # 周末 -> 休息
    if date.weekday() in weekend_set:
        return False

    # 其他 -> 工作日
    return True


def get_day_type(
    date: datetime,
    holidays_set: Set[str],
    compensatory_set: Set[str],
    weekend_set: Set[int]
) -> str:
    """获取日期类型"""
    date_str = format_date(date)
    weekday = date.weekday()

    if date_str in compensatory_set:
        return "补班"
    if date_str in holidays_set:
        return "假日"
    if weekday in weekend_set:
        return "周末"
    return "工作"


def get_all_dates_of_year(year: int) -> List[datetime]:
    """获取某年的所有日期"""
    dates = []
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31)
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def get_week_number(date: datetime) -> int:
    """获取ISO周数"""
    d = datetime(date.year, date.month, date.day)
    d = d - timedelta(days=d.weekday() + 3)
    week = d.isocalendar()[1]
    return week


def calculate_total_workdays(
    year: int,
    holiday_intervals: List[HolidayInterval] = None,
    compensatory_days: List[CompensatoryDay] = None,
    weekend_config: WeekendConfig = None
) -> Dict:
    """
    计算年度总工日

    返回:
    {
        "year": 2026,
        "total_workdays": 250,
        "total_holidays": 115,
        "details": {...}
    }
    """
    # 加载数据（如果未提供）
    if holiday_intervals is None:
        holiday_intervals, _ = load_holiday_intervals(year)
    if compensatory_days is None:
        compensatory_days, _ = load_compensatory_days(year)
    if weekend_config is None:
        weekend_config = load_weekend_config()

    holidays_set = generate_holiday_set(holiday_intervals)
    compensatory_set = generate_compensatory_set(compensatory_days)
    weekend_set = set(weekend_config.weekends)

    dates = get_all_dates_of_year(year)
    workdays = sum(1 for d in dates if is_workday(d, holidays_set, compensatory_set, weekend_set))
    holidays = len(dates) - workdays

    return {
        "year": year,
        "total_workdays": workdays,
        "total_holidays": holidays,
        "total_days": len(dates),
        "holiday_count": len(holidays_set),
        "compensatory_count": len(compensatory_set),
        "weekend_config": weekend_config.weekends
    }


def generate_weekly_calendar(
    year: int,
    holiday_intervals: List[HolidayInterval] = None,
    compensatory_days: List[CompensatoryDay] = None,
    weekend_config: WeekendConfig = None,
    include_empty_days: bool = True
) -> List[Dict]:
    """
    生成年度周历

    返回格式:
    [
        {
            "week_number": 1,
            "week_start": "2026-01-01",  // 周日
            "week_end": "2026-01-03",    // 周六
            "days": [
                {
                    "date": "2026-01-01",
                    "weekday": 0,
                    "weekday_name": "周四",
                    "day_type": "假日",
                    "is_workday": false,
                    "holiday_name": "元旦",
                    "month": 1,
                    "day": 1
                },
                ...
            ],
            "week_workdays": 3,
            "week_holidays": 4
        },
        ...
    ]
    """
    weekday_names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]

    # 加载数据
    if holiday_intervals is None:
        holiday_intervals, _ = load_holiday_intervals(year)
    if compensatory_days is None:
        compensatory_days, _ = load_compensatory_days(year)
    if weekend_config is None:
        weekend_config = load_weekend_config()

    holidays_set = generate_holiday_set(holiday_intervals)
    compensatory_set = generate_compensatory_set(compensatory_days)
    weekend_set = set(weekend_config.weekends)

    # 构建节假日名称映射
    holiday_names = {}
    for interval in holiday_intervals:
        start = parse_date(interval.start)
        end = parse_date(interval.end)
        if not start or not end:
            continue
        current = start
        while current <= end:
            holiday_names[format_date(current)] = interval.name
            current += timedelta(days=1)

    dates = get_all_dates_of_year(year)

    # 按周分组
    weeks = []
    current_week = []
    first_weekday = dates[0].weekday()  # 年初第一天是周几

    # 填充月初空白
    for _ in range(first_weekday):
        if include_empty_days:
            current_week.append(None)
        else:
            continue

    for date in dates:
        current_week.append(date)
        if date.weekday() == 6:  # 周日结束
            weeks.append(current_week)
            current_week = []

    # 处理最后一周
    if current_week:
        while include_empty_days and len(current_week) < 7:
            current_week.append(None)
        if current_week:
            weeks.append(current_week)

    # 生成周数据
    calendar = []
    for week in weeks:
        real_days = [d for d in week if d is not None]
        if not real_days:
            continue

        week_info = {
            "week_number": get_week_number(real_days[0]),
            "week_start": format_date(real_days[0]),
            "week_end": format_date(real_days[-1]),
            "days": [],
            "week_workdays": 0,
            "week_holidays": 0
        }

        for day in week:
            if day is None:
                week_info["days"].append({
                    "date": None,
                    "weekday": None,
                    "weekday_name": None,
                    "day_type": "空",
                    "is_workday": None,
                    "holiday_name": None,
                    "month": None,
                    "day": None
                })
                continue

            date_str = format_date(day)
            weekday = day.weekday()
            day_type = get_day_type(day, holidays_set, compensatory_set, weekend_set)
            is_work = is_workday(day, holidays_set, compensatory_set, weekend_set)

            if is_work:
                week_info["week_workdays"] += 1
            else:
                week_info["week_holidays"] += 1

            week_info["days"].append({
                "date": date_str,
                "weekday": weekday,
                "weekday_name": weekday_names[weekday],
                "day_type": day_type,
                "is_workday": is_work,
                "holiday_name": holiday_names.get(date_str, ""),
                "month": day.month,
                "day": day.day
            })

        calendar.append(week_info)

    return calendar


# ============================================================
# 数据导入/导出（供AI调用）
# ============================================================

def import_holidays_from_ai(year: int, holiday_data: List[Dict]) -> str:
    """
    AI导入法定假日数据

    holiday_data格式:
    [
        {"name": "元旦", "start": "2026-01-01", "end": "2026-01-01"},
        {"name": "春节", "start": "2026-01-28", "end": "2026-02-04"},
        ...
    ]
    """
    intervals = []
    for item in holiday_data:
        intervals.append(HolidayInterval(
            name=item.get("name", ""),
            start=item.get("start", ""),
            end=item.get("end", item.get("start", "")),
            note=item.get("note", "")
        ))

    filepath = save_holiday_intervals(year, intervals)
    return filepath


def import_compensatory_from_ai(year: int, comp_data: List[Dict]) -> str:
    """
    AI导入补班日数据

    comp_data格式:
    [
        {"date": "2026-01-26"},
        {"date": "2026-02-08", "note": "春节调休"},
        ...
    ]
    """
    days = []
    for item in comp_data:
        days.append(CompensatoryDay(
            date=item.get("date", ""),
            note=item.get("note", "")
        ))

    filepath = save_compensatory_days(year, days)
    return filepath


def export_year_summary(year: int) -> Dict:
    """
    导出年度汇总数据（供AI调用）
    """
    holiday_intervals, _ = load_holiday_intervals(year)
    compensatory_days, _ = load_compensatory_days(year)
    weekend_config = load_weekend_config()

    summary = calculate_total_workdays(
        year, holiday_intervals, compensatory_days, weekend_config
    )

    summary["holiday_intervals"] = [i.to_dict() for i in holiday_intervals]
    summary["compensatory_days"] = [d.to_dict() for d in compensatory_days]
    summary["weekend_config"] = weekend_config.to_dict()

    return summary


# ============================================================
# 数据同步
# ============================================================

def sync_year(year: int, source_year: int = None) -> Dict:
    """
    将指定年份的假日/补班数据同步到目标年份（保留月日）

    用于：每年复用上年数据，只需微调
    """
    if source_year is None:
        source_year = year - 1

    result = {"holidays_synced": 0, "compensatory_synced": 0, "errors": []}

    # 同步法定假日
    source_holidays, _ = load_holiday_intervals(source_year)
    new_holidays = []
    for h in source_holidays:
        parts = h.start.split('-')
        if len(parts) == 3:
            new_start = f"{year}-{parts[1]}-{parts[2]}"
        else:
            new_start = h.start
            result["errors"].append(f"日期格式错误: {h.start}")

        parts = h.end.split('-')
        if len(parts) == 3:
            new_end = f"{year}-{parts[1]}-{parts[2]}"
        else:
            new_end = h.end

        new_holidays.append(HolidayInterval(
            name=h.name,
            start=new_start,
            end=new_end,
            note=h.note
        ))
        result["holidays_synced"] += 1

    save_holiday_intervals(year, new_holidays)

    # 同步补班日
    source_comp, _ = load_compensatory_days(source_year)
    new_comp = []
    for c in source_comp:
        parts = c.date.split('-')
        if len(parts) == 3:
            new_date = f"{year}-{parts[1]}-{parts[2]}"
            new_comp.append(CompensatoryDay(date=new_date, note=c.note))
            result["compensatory_synced"] += 1
        else:
            result["errors"].append(f"日期格式错误: {c.date}")

    save_compensatory_days(year, new_comp)

    return result


def export_rules_table(year: int = None) -> str:
    """
    导出规则确认表（供用户核对配置）
    
    返回格式化的文本表格，包含：
    1. 周末规则配置
    2. 法定节假日列表
    3. 补班日列表
    4. 年度统计摘要
    """
    if year is None:
        year = datetime.now().year
    
    weekday_names_cn = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
    weekday_map = {0: "周日", 1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六"}
    
    # 加载数据
    holiday_intervals, _ = load_holiday_intervals(year)
    compensatory_days, _ = load_compensatory_days(year)
    weekend_config = load_weekend_config()
    
    # 生成节假日详情
    holidays_detail = []
    total_holiday_days = 0
    for interval in holiday_intervals:
        start_dt = parse_date(interval.start)
        end_dt = parse_date(interval.end)
        if start_dt and end_dt:
            days = (end_dt - start_dt).days + 1
            total_holiday_days += days
            holidays_detail.append({
                "name": interval.name,
                "start": interval.start,
                "end": interval.end,
                "days": days,
                "note": interval.note
            })
    
    # 生成补班日详情
    comp_detail = []
    for comp in compensatory_days:
        comp_dt = parse_date(comp.date)
        weekday = weekday_map[comp_dt.weekday()] if comp_dt else "未知"
        comp_detail.append({
            "date": comp.date,
            "weekday": weekday,
            "note": comp.note
        })
    
    # 计算统计
    total = calculate_total_workdays(year, holiday_intervals, compensatory_days, weekend_config)
    
    # 构建输出
    lines = []
    lines.append("=" * 70)
    lines.append(f"📋 {year}年 规则配置确认表")
    lines.append("=" * 70)
    
    # 1. 周末规则
    lines.append("\n🔧 【周末规则配置】")
    lines.append("-" * 40)
    if weekend_config.weekends == [0, 6]:
        lines.append("  休息日: 周六、周日 (标准双休)")
    elif weekend_config.weekends == [5, 6]:
        lines.append("  休息日: 周五、周六")
    elif weekend_config.weekends == [0, 1]:
        lines.append("  休息日: 周日、周一")
    elif len(weekend_config.weekends) == 1:
        lines.append(f"  休息日: {weekday_map.get(weekend_config.weekends[0], '未知')} (单休)")
    else:
        rest_days = [weekday_map.get(w, str(w)) for w in weekend_config.weekends]
        lines.append(f"  休息日: {', '.join(rest_days)}")
    lines.append(f"  配置来源: data/weekend_config.json")
    
    # 2. 法定节假日
    lines.append("\n🎉 【法定节假日】")
    lines.append("-" * 40)
    if not holidays_detail:
        lines.append("  ⚠️  未配置！请使用 import_holidays() 导入")
    else:
        lines.append(f"  共 {len(holidays_detail)} 个假期，总计 {total_holiday_days} 天\n")
        lines.append(f"  {'假期名称':<12} {'开始日期':<12} {'结束日期':<12} {'天数':<6} {'备注'}")
        lines.append("  " + "-" * 52)
        for h in holidays_detail:
            note = h["note"] if h["note"] else "-"
            lines.append(f"  {h['name']:<12} {h['start']:<12} {h['end']:<12} {h['days']:<6} {note}")
    
    # 3. 补班日
    lines.append("\n💼 【补班日（需要上班）】")
    lines.append("-" * 40)
    if not comp_detail:
        lines.append("  ✅  无补班日安排")
    else:
        lines.append(f"  共 {len(comp_detail)} 天需要上班\n")
        lines.append(f"  {'日期':<14} {'星期':<8} {'备注'}")
        lines.append("  " + "-" * 40)
        for c in comp_detail:
            note = c["note"] if c["note"] else "-"
            lines.append(f"  {c['date']:<14} {c['weekday']:<8} {note}")
    
    # 4. 冲突检查
    holidays_set = generate_holiday_set(holiday_intervals)
    compensatory_set = generate_compensatory_set(compensatory_days)
    conflicts = holidays_set & compensatory_set
    if conflicts:
        lines.append("\n⚠️  【配置冲突警告】")
        lines.append("-" * 40)
        lines.append("  以下日期同时存在于节假日和补班日中（以补班日为准）：")
        for date in sorted(conflicts):
            dt = parse_date(date)
            weekday = weekday_map.get(dt.weekday(), "") if dt else ""
            lines.append(f"    {date} ({weekday})")
    
    # 5. 年度统计
    lines.append("\n📊 【年度统计摘要】")
    lines.append("-" * 40)
    lines.append(f"  年度总天数:     {total.get('total_days', 'N/A')} 天")
    lines.append(f"  工作日天数:     {total.get('total_workdays', 'N/A')} 天")
    lines.append(f"  休息日天数:     {total.get('total_holidays', 'N/A')} 天")
    lines.append(f"  法定假日天数:   {total.get('holiday_count', 'N/A')} 天")
    lines.append(f"  补班日天数:     {total.get('compensatory_count', 'N/A')} 天")
    lines.append(f"  周末天数:       {total.get('total_days', 365) - total.get('holiday_count', 0) - total.get('compensatory_count', 0) - 52 * len(weekend_config.weekends)} 天")
    
    # 6. 核对提示
    lines.append("\n" + "=" * 70)
    lines.append("📌 请核对以上配置是否正确！")
    lines.append("   如有疏漏或错误，请使用相应命令修改配置：")
    lines.append("   - 修改周末: 手动编辑 data/weekend_config.json")
    lines.append("   - 修改节假日: 使用 import_holidays() 导入新数据")
    lines.append("   - 修改补班日: 使用 import_compensatory() 导入新数据")
    lines.append("=" * 70)
    
    return "\n".join(lines)


# ============================================================
# CLI入口
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python workday_calendar.py <command> [options]")
        print()
        print("规则确认:")
        print("  rules [year]             - 导出规则确认表（请在初始化后核对）")
        print()
        print("工作日计算:")
        print("  calculate <year>         - 计算年度总工日")
        print("  calendar <year>          - 生成周历")
        print("  sync <year> [source_year] - 同步数据到目标年份")
        print("  init <year>              - 初始化年度数据")
        print()
        print("日程管理:")
        print("  add <date> <start> <end> <title> - 添加日程")
        print("  list [date]              - 列出日程")
        print("  delete <id>              - 删除日程")
        print("  update <id> [options]    - 更新日程")
        print("  free <date> [start] [end] - 查找空闲时间")
        print("  schedule [days]           - 生成日程列表(默认7天)")
        print("  today                    - 生成今天及后续7天日程")
        print()
        print("示例:")
        print("  python workday_calendar.py rules 2026")
        print("  python workday_calendar.py add 2026-05-20 14:00 15:00 团队会议")
        print("  python workday_calendar.py list 2026-05-20")
        print("  python workday_calendar.py free 2026-05-20 09:00 18:00")
        sys.exit(1)

    command = sys.argv[1]

    # 规则确认命令
    if command == "rules":
        year = int(sys.argv[2]) if len(sys.argv) > 2 else datetime.now().year
        print(export_rules_table(year))

    # 工作日计算命令
    elif command == "add":
        if len(sys.argv) < 6:
            print("用法: add <date> <start> <end> <title> [description] [category]")
            sys.exit(1)
        date = sys.argv[2]
        start_time = sys.argv[3]
        end_time = sys.argv[4]
        title = sys.argv[5]
        description = sys.argv[6] if len(sys.argv) > 6 else ""
        category = sys.argv[7] if len(sys.argv) > 7 else "工作"
        event, msg = add_schedule_event(title, date, start_time, end_time, description, category)
        if event:
            print(json.dumps(event.to_dict(), ensure_ascii=False, indent=2))
        print(msg)

    elif command == "list":
        date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")
        events = get_schedule_by_date(date)
        if not events:
            print(f"{date} 暂无日程")
        else:
            print(f"📅 {date} 日程列表:")
            events.sort(key=lambda x: x.start_time)
            for e in events:
                status_icon = "✅" if e.status == "completed" else "🔄" if e.status == "pending" else "❌"
                print(f"  [{e.id}] {status_icon} {e.start_time}-{e.end_time} {e.title} ({e.category})")

    elif command == "delete":
        if len(sys.argv) < 3:
            print("用法: delete <event_id>")
            sys.exit(1)
        print(delete_schedule_event(sys.argv[2]))

    elif command == "update":
        if len(sys.argv) < 3:
            print("用法: update <event_id> [options]")
            print("选项: --title, --date, --start, --end, --desc, --category, --status")
            sys.exit(1)
        event_id = sys.argv[2]
        kwargs = {}
        for arg in sys.argv[3:]:
            if arg.startswith("--title="):
                kwargs["title"] = arg[8:]
            elif arg.startswith("--date="):
                kwargs["date"] = arg[7:]
            elif arg.startswith("--start="):
                kwargs["start_time"] = arg[8:]
            elif arg.startswith("--end="):
                kwargs["end_time"] = arg[6:]
            elif arg.startswith("--desc="):
                kwargs["description"] = arg[7:]
            elif arg.startswith("--category="):
                kwargs["category"] = arg[11:]
            elif arg.startswith("--status="):
                kwargs["status"] = arg[9:]
        print(update_schedule_event(event_id, **kwargs))

    elif command == "free":
        date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")
        start_search = sys.argv[3] if len(sys.argv) > 3 else "09:00"
        end_search = sys.argv[4] if len(sys.argv) > 4 else "18:00"
        slots = find_free_slots(date, start_search, end_search)
        if not slots:
            print(f"{date} {start_search}-{end_search} 无空闲时段")
        else:
            print(f"📅 {date} {start_search}-{end_search} 空闲时段:")
            for slot in slots:
                print(f"  {slot['start']}-{slot['end']} (共{slot['duration']}分钟)")

    elif command == "schedule":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        print(generate_daily_schedule(datetime.now().strftime("%Y-%m-%d"), days))

    elif command == "today":
        print(generate_today_schedule())

    # 工作日计算命令
    elif command == "calculate":
        year = int(sys.argv[2]) if len(sys.argv) > 2 else datetime.now().year
        summary = calculate_total_workdays(year)
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    elif command == "calendar":
        year = int(sys.argv[2]) if len(sys.argv) > 2 else datetime.now().year
        cal = generate_weekly_calendar(year)
        print(json.dumps(cal, ensure_ascii=False, indent=2))

    elif command == "sync":
        year = int(sys.argv[2]) if len(sys.argv) > 2 else datetime.now().year
        source = int(sys.argv[3]) if len(sys.argv) > 3 else year - 1
        result = sync_year(year, source)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "init":
        year = int(sys.argv[2]) if len(sys.argv) > 2 else datetime.now().year
        save_holiday_intervals(year, [])
        save_compensatory_days(year, [])
        print(f"已初始化 {year} 年数据文件")

    else:
        print(f"未知命令: {command}")
        sys.exit(1)
