#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026年排班表生成脚本
根据workday-calendar生成完整排班安排
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加workday_calendar模块路径
sys.path.insert(0, str(Path(__file__).parent))

from workday_calendar import (
    load_holiday_intervals,
    load_compensatory_days,
    load_weekend_config,
    get_skill_data_dir
)

def is_workday(date: str, year: int = 2026) -> bool:
    """判断某天是否为工作日"""
    from workday_calendar import WeekendConfig
    
    # 加载配置
    holiday_intervals, _ = load_holiday_intervals(year)
    compensatory_days, _ = load_compensatory_days(year)
    weekend_config = load_weekend_config()
    
    # 补班日优先
    for comp_day in compensatory_days:
        if comp_day.date == date:
            return True
    
    # 法定假日
    from datetime import date as date_type
    check_date = date_type.fromisoformat(date)
    for interval in holiday_intervals:
        start = date_type.fromisoformat(interval.start)
        end = date_type.fromisoformat(interval.end)
        if start <= check_date <= end:
            return False
    
    # 周末
    weekday = check_date.weekday()  # 0=周一, 6=周日
    # 转换为配置格式 (0=周日, 6=周六)
    weekday_config = (weekday + 1) % 7
    if weekday_config in weekend_config.weekends:
        return False
    
    return True

def generate_schedule(year: int = 2026):
    """生成全年排班表"""
    
    # 排班人员配置
    day_shift_staff = ["冯瑶瑶", "刘文珠"]  # 白班固定两人
    evening_shift_staff = ["吴王思淼"]  # 晚班固定一人
    sample_staff = [
        "范轶欧", "张文强", "张丽莹", "王淑龙",
        "李蔚", "辛成龙", "付颖", "迟英欣", "赵红兵"
    ]  # 接样人员9人轮班
    
    # 生成全年日期
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    
    schedule = []
    sample_index = 0
    
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        weekday_name = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][current.weekday()]
        
        if is_workday(date_str, year):
            # 工作日
            sample_person = sample_staff[sample_index % len(sample_staff)]
            sample_index += 1
            
            schedule.append({
                "date": date_str,
                "weekday": weekday_name,
                "day_shift": f"8:30-17:00 ({day_shift_staff[0]}、{day_shift_staff[1]})",
                "evening_shift": f"17:00-21:00 ({evening_shift_staff[0]})",
                "sample_staff": f"8:30-17:00 ({sample_person})",
                "note": ""
            })
        else:
            # 休息日
            schedule.append({
                "date": date_str,
                "weekday": weekday_name,
                "day_shift": "休息",
                "evening_shift": "休息",
                "sample_staff": "休息",
                "note": "周末/假日"
            })
        
        current += timedelta(days=1)
    
    return schedule

def export_to_markdown(schedule, output_file: str):
    """导出为Markdown表格"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# 2026年排班表\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 排班规则\n\n")
        f.write("- **白班**: 8:30-17:00，固定人员：冯瑶瑶、刘文珠\n")
        f.write("- **晚班**: 17:00-21:00，固定人员：吴王思\n")
        f.write("- **接样人员**: 8:30-17:00，9人轮班：范轶欧、张文强、张丽莹、王淑龙、李蔚、辛成龙、付颖、迟英欣、赵红兵\n")
        f.write("- **休息日**: 周六、周日及法定假日\n\n")
        f.write("---\n\n")
        
        f.write("## 排班明细\n\n")
        f.write("| 日期 | 星期 | 白班 (8:30-17:00) | 晚班 (17:00-21:00) | 接样人员 (8:30-17:00) | 备注 |\n")
        f.write("|------|------|---------------------|---------------------|---------------------------|------|\n")
        
        for entry in schedule:
            f.write(f"| {entry['date']} | {entry['weekday']} | {entry['day_shift']} | {entry['evening_shift']} | {entry['sample_staff']} | {entry['note']} |\n")
    
    print(f"Markdown排班表已导出: {output_file}")

def export_to_html(schedule, output_file: str):
    """导出为自包含HTML（粉紫→蓝绿渐变）"""
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2026年排班表</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .rules {{
            padding: 20px 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }}
        .rules h2 {{
            font-size: 18px;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .rules ul {{
            list-style: none;
            padding-left: 0;
        }}
        .rules li {{
            padding: 5px 0;
            color: #495057;
        }}
        .table-container {{
            padding: 20px;
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        thead {{
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            white-space: nowrap;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e9ecef;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .workday {{
            color: #212529;
        }}
        .holiday {{
            background: #fff3cd;
            color: #856404;
        }}
        .weekend {{
            background: #f8d7da;
            color: #721c24;
        }}
        .note {{
            font-size: 12px;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗓️ 2026年排班表</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="rules">
            <h2>📋 排班规则</h2>
            <ul>
                <li><strong>白班</strong>: 8:30-17:00，固定人员：冯瑶瑶、刘文珠</li>
                <li><strong>晚班</strong>: 17:00-21:00，固定人员：吴王思</li>
                <li><strong>接样人员</strong>: 8:30-17:00，9人轮班：范轶欧、张文强、张丽莹、王淑龙、李蔚、辛成龙、付颖、迟英欣、赵红兵</li>
                <li><strong>休息日</strong>: 周六、周日及法定假日（共33天）</li>
            </ul>
        </div>
        
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>星期</th>
                        <th>白班 (8:30-17:00)</th>
                        <th>晚班 (17:00-21:00)</th>
                        <th>接样人员 (8:30-17:00)</th>
                        <th>备注</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for entry in schedule:
        date_obj = datetime.strptime(entry['date'], '%Y-%m-%d')
        is_weekend = date_obj.weekday() >= 5
        is_holiday = entry['note'] != ""
        
        row_class = 'workday'
        if is_holiday:
            row_class = 'holiday'
        elif is_weekend:
            row_class = 'weekend'
        
        html_content += f"""
                    <tr class="{row_class}">
                        <td>{entry['date']}</td>
                        <td>{entry['weekday']}</td>
                        <td>{entry['day_shift']}</td>
                        <td>{entry['evening_shift']}</td>
                        <td>{entry['sample_staff']}</td>
                        <td class="note">{entry['note']}</td>
                    </tr>
"""
    
    html_content += """                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML排班表已导出: {output_file}")

if __name__ == "__main__":
    year = 2026
    schedule = generate_schedule(year)
    
    # 导出Markdown
    md_file = Path(__file__).parent / f"schedule_{year}.md"
    export_to_markdown(schedule, str(md_file))
    
    # 导出HTML
    html_file = Path(__file__).parent / f"schedule_{year}.html"
    export_to_html(schedule, str(html_file))
    
    print(f"\n[OK] 排班表生成完成！")
    print(f"  - Markdown: {md_file}")
    print(f"  - HTML: {html_file}")
