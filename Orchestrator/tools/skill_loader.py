"""
tools/skill_loader.py — 动态技能加载器

通过读取 SKILL.md 让智能体理解任意技能的能力，无需写 adapter。
工作方式和你（WorkBuddy）读文档→执行脚本完全一致。
"""

import glob
import os
import re
from pathlib import Path
from typing import Optional

from ..tool_base import BaseTool, ToolResult


# 默认技能搜索路径（空，只扫配置传入的路径）
DEFAULT_SKILLS_DIRS: list[str] = []


def _find_skill_dir(name: str, extra_dirs: list[str] = None) -> Optional[str]:
    """在已知路径中查找技能目录"""
    search_dirs = list(DEFAULT_SKILLS_DIRS)
    if extra_dirs:
        search_dirs = extra_dirs + search_dirs

    for base in search_dirs:
        # 直接匹配 ~/.workbuddy/skills/{name}/
        target = os.path.join(base, name)
        if os.path.isdir(target) and os.path.isfile(os.path.join(target, "SKILL.md")):
            return target
        # 匹配 ~/.workbuddy/skills/{name}/SKILL.md
        if os.path.isfile(os.path.join(base, name)):
            return base

    return None


def _list_skills(extra_dirs: list[str] = None) -> list[dict]:
    """列出所有可用技能"""
    search_dirs = list(DEFAULT_SKILLS_DIRS)
    if extra_dirs:
        search_dirs = extra_dirs + search_dirs

    found = []
    seen = set()

    for base in search_dirs:
        if not os.path.isdir(base):
            continue
        for entry in sorted(os.listdir(base)):
            skill_dir = os.path.join(base, entry)
            skill_md = os.path.join(skill_dir, "SKILL.md")
            if os.path.isfile(skill_md) and entry not in seen:
                seen.add(entry)
                # 提取展示名称
                display = entry
                try:
                    with open(skill_md, encoding="utf-8") as f:
                        content = f.read(2000)
                    m = re.search(r'displayName\s*:\s*"([^"]+)"', content)
                    if m:
                        display = m.group(1)
                    # 找 "核心能力" 标题后的第一句话
                    cap_m = re.search(r'核心能力.*?\n(.+?)(?:\n|$)', content)
                    brief = cap_m.group(1).strip()[:80] if cap_m else ""
                except:
                    brief = ""
                found.append({"name": entry, "display": display, "brief": brief})

    return found


def _read_skill_summary(skill_dir: str) -> str:
    """读取 SKILL.md 并提取关键信息"""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return ""

    with open(skill_md, encoding="utf-8") as f:
        content = f.read()

    summary_parts = []

    # 1. 提取 displayName + description
    m = re.search(r'displayName\s*:\s*"([^"]+)"', content)
    name = m.group(1) if m else os.path.basename(skill_dir)
    m = re.search(r'description\s*:\s*"([^"]+)"', content)
    desc = m.group(1) if m else ""
    summary_parts.append(f"技能: {name}")
    if desc:
        summary_parts.append(f"描述: {desc}")

    # 2. 提取触发条件（知道什么时候该用）
    trigger_section = re.search(
        r'## 触发条件\s*(.*?)(?:\n##\s|\Z)', content, re.DOTALL
    )
    if trigger_section:
        triggers = trigger_section.group(1).strip()[:300]
        summary_parts.append(f"\n触发条件:\n{triggers}")

    # 3. 提取核心能力
    cap_section = re.search(
        r'## 核心能力\s*(.*?)(?:\n##\s|\Z)', content, re.DOTALL
    )
    if cap_section:
        caps = cap_section.group(1).strip()[:500]
        summary_parts.append(f"\n核心能力:\n{caps}")

    # 4. 提取工作流程 / 快速开始中的命令
    for section_keyword in ["快速开始", "工作流程", "Commands", "Usage"]:
        cmd_section = re.search(
            rf'##\s*{section_keyword}\s*(.*?)(?:\n##\s|\Z)', content, re.DOTALL
        )
        if cmd_section:
            cmds = cmd_section.group(1).strip()[:600]
            summary_parts.append(f"\n使用方法:\n{cmds}")
            break

    # 5. 提取 scripts/ 目录中的脚本清单
    scripts_dir = os.path.join(skill_dir, "scripts")
    if os.path.isdir(scripts_dir):
        scripts = [f for f in os.listdir(scripts_dir) if f.endswith(".py")]
        if scripts:
            summary_parts.append(f"\n可用脚本 ({len(scripts)} 个):")
            for s in sorted(scripts):
                spath = os.path.join(scripts_dir, s)
                ssize = os.path.getsize(spath)
                # 读脚本第一段 docstring
                try:
                    with open(spath, encoding="utf-8") as sf:
                        first_line = sf.readline().strip()
                    doc = first_line.lstrip('"""').strip()[:60] if '"""' in first_line else ""
                except:
                    doc = ""
                summary_parts.append(f"  python scripts/{s}  ({ssize/1024:.0f}KB){' - ' + doc if doc else ''}")

    # 6. 数据目录
    data_dir = os.path.join(skill_dir, "data")
    if os.path.isdir(data_dir):
        summary_parts.append(f"\n数据目录: {data_dir}")

    return "\n".join(summary_parts)


class LoadSkillTool(BaseTool):
    """
    加载任意 WorkBuddy 技能。

    读取技能的 SKILL.md，让智能体理解其能力和用法。
    之后可以调用 python_execute 来执行技能的脚本。

    等价于 WorkBuddy 自己加载技能的方式——读文档，然后执行。
    """

    def __init__(self, extra_dirs: list[str] = None):
        super().__init__(
            name="load_skill",
            description="加载一个 WorkBuddy 技能，读取其 SKILL.md 并理解它的能力和用法。之后你可以通过 python_execute 调用它的脚本。",
        )
        self.extra_dirs = extra_dirs or []

    def execute(
        self,
        skill_name: str = "",
        list_all: bool = False,
        max_chars: int = 3000,
    ) -> ToolResult:
        """
        Parameters
        ----------
        skill_name : str
            技能名称（目录名），如 "novel-weaver", "local-rag-builder"
        list_all : bool
            列出所有可用技能
        max_chars : int
            返回内容最大字符数
        """
        if list_all:
            skills = _list_skills(self.extra_dirs)
            if not skills:
                return ToolResult(
                    False,
                    error="未找到任何技能。技能应放在 ~/.workbuddy/skills/ 下",
                )
            lines = [f"找到 {len(skills)} 个技能:\n"]
            for s in skills:
                brief = f" - {s['brief']}" if s.get("brief") else ""
                lines.append(f"  {s['name']}{brief}")
            lines.append(
                '\n用法: load_skill(skill_name="xxx") 加载某个技能'
            )
            return ToolResult(True, output="\n".join(lines))

        if not skill_name:
            return ToolResult(False, error="请指定技能名称，或设置 list_all=True 列出所有技能")

        skill_dir = _find_skill_dir(skill_name, self.extra_dirs)
        if not skill_dir:
            return ToolResult(
                False,
                error=f"技能 '{skill_name}' 未找到。\n"
                      f"搜索路径: {', '.join(DEFAULT_SKILLS_DIRS + (self.extra_dirs or []))}\n"
                      f"用 load_skill(list_all=True) 查看所有可用技能",
            )

        summary = _read_skill_summary(skill_dir)
        if not summary:
            return ToolResult(False, error=f"技能 '{skill_name}' 的 SKILL.md 为空或无法读取")

        if len(summary) > max_chars:
            summary = summary[:max_chars] + "\n\n...(内容已截断)"

        return ToolResult(
            True,
            output=f"技能 [{skill_name}] 已加载:\n\n{summary}",
            data={"skill_name": skill_name, "skill_dir": skill_dir, "summary": summary},
        )

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "技能目录名称，如 novel-weaver, local-rag-builder, workday-calendar 等",
                    },
                    "list_all": {
                        "type": "boolean",
                        "description": "设为 true 则列出所有可用技能，不需要 skill_name",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "返回内容最大字符数（可选，默认 3000）",
                    },
                },
            },
        }
