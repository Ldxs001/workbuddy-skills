#!/usr/bin/env python3
"""
skill_extractor.py - Skill Step Extractor v1.1.0
从 SKILL.md 中自动提取关键执行步骤，供调用链编排使用。

v1.1.0 新增：提取指令名称填入 skill_instruction 字段。

零外部依赖，仅使用 Python 标准库。
跨平台支持 Windows/Linux/macOS。
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ============================================================
# 路径配置
# ============================================================

def get_skills_dir():
    """获取已安装技能目录"""
    env_dir = os.environ.get("WORKBUDDY_SKILLS_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".workbuddy" / "skills"


SKILLS_DIR = get_skills_dir()


# ============================================================
# SKILL.md 解析
# ============================================================

def find_skill_dir(skill_name):
    """根据技能名称查找技能目录"""
    if not SKILLS_DIR.exists():
        return None

    # 精确匹配
    for entry in SKILLS_DIR.iterdir():
        if entry.is_dir() and entry.name.lower() == skill_name.lower():
            return entry

    # 模糊匹配（名称包含）
    for entry in SKILLS_DIR.iterdir():
        if entry.is_dir():
            slug = entry.name.lower().replace(" ", "-")
            if skill_name.lower() in slug or slug in skill_name.lower():
                return entry

    return None


def read_skill_md(skill_path):
    """读取 SKILL.md 文件内容"""
    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        return None
    with open(skill_file, "r", encoding="utf-8") as f:
        return f.read()


def extract_frontmatter(content):
    """提取 YAML frontmatter"""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    fm_text = content[3:end].strip()
    result = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            result[key] = val
    return result


def extract_description(content):
    """提取技能描述（从第一段非空非标题文本中获取）"""
    lines = content.split("\n")
    desc_lines = []
    in_frontmatter = content.startswith("---")
    fm_end = 0
    if in_frontmatter:
        fm_end = content.find("---", 3)
        if fm_end == -1:
            fm_end = 0
        else:
            fm_end += 3

    for line in lines:
        # 跳过 frontmatter
        if content.index(line) < fm_end:
            continue
        stripped = line.strip()
        if not stripped:
            if desc_lines:
                break
            continue
        if stripped.startswith("#"):
            continue
        # 取第一段作为描述
        desc_lines.append(stripped)
        if len(" ".join(desc_lines)) > 200:
            break

    return " ".join(desc_lines).strip()


def extract_trigger_keywords(content):
    """提取触发关键词"""
    triggers = []
    # 匹配常见触发模式
    patterns = [
        r'(?:触发|trigger|when)[：:]\s*(.+?)(?:\n|$)',
        r'(?:触发条件|触发场景)[：:]\s*(.+?)(?:\n|$)',
        r'(?:使用场景|场景)[：:]\s*(.+?)(?:\n|$)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        triggers.extend(matches)

    # 从表格中提取触发场景
    table_pattern = r'\|\s*[^|]*?触发[^|]*?\|\s*([^|]+?)\s*\|'
    table_matches = re.findall(table_pattern, content, re.IGNORECASE)
    triggers.extend(table_matches)

    return list(set(t.strip() for t in triggers if t.strip()))


def extract_core_commands(content):
    """提取核心指令/命令（含指令名称供 skill_instruction 使用）"""
    commands = []

    # 匹配 ### 标题（通常是子命令/指令名称）
    heading_pattern = r'###\s+(?:\d+\.\s*)?(\S.+?)(?:\s*`([^`]+)`)?\s*$'
    for match in re.finditer(heading_pattern, content, re.MULTILINE):
        title = match.group(1).strip()
        cmd = match.group(2)
        if cmd:
            commands.append({"name": title, "command": cmd})
        elif title and not any(skip in title.lower() for skip in
                                ["示例", "注意", "核心概念", "数据结构", "触发", "存储",
                                 "安装", "配置", "脚本", "cli", "使用示例", "禁止行为",
                                 "循环规则", "完整示例", "说明", "对比", "模式", "版本"]):
            commands.append({"name": title, "command": title})

    return commands


def extract_skill_instructions(content):
    """提取可用于调用链的 skill_instruction 候选列表。

    返回指令名称列表，每个名称是 SKILL.md 中识别到的可执行指令，
    用于在创建调用链时填入 step 的 skill_instruction 字段。
    """
    instructions = []

    # 从 ### 标题提取（与 extract_core_commands 同源，但格式更精炼）
    heading_pattern = r'###\s+(?:\d+\.\s*)?`?(\w[\w\s-]+?)`?\s*(?:\(([^)]+)\))?\s*$'
    skip_words = [
        "示例", "注意", "核心概念", "数据结构", "触发", "存储",
        "安装", "配置", "脚本", "cli", "使用示例", "禁止行为",
        "循环规则", "完整示例", "说明", "对比", "模式", "版本",
        "agent", "ai", "必读", "注意事", "快速", "速查"
    ]
    for match in re.finditer(heading_pattern, content, re.MULTILINE):
        name = match.group(1).strip()
        cmd = match.group(2)
        # 确定指令名称
        if cmd:
            instruction = cmd.strip()
        else:
            instruction = name
        # 过滤掉非指令标题
        if any(skip in instruction.lower() for skip in skip_words):
            continue
        if len(instruction) > 30:
            instruction = instruction[:30]
        if instruction and instruction not in instructions:
            instructions.append(instruction)

    return instructions


def extract_key_steps(content):
    """提取关键执行步骤（从代码块、列表、流程描述中）"""
    steps = []

    # 从编号列表中提取步骤
    numbered_pattern = r'(?:步骤|Step)\s*(\d+)\s*[：:]\s*(.+?)(?:\n|$)'
    for match in re.finditer(numbered_pattern, content, re.IGNORECASE):
        step_num = int(match.group(1))
        step_desc = match.group(2).strip()
        steps.append({"index": step_num, "description": step_desc})

    # 从字母编号步骤提取
    alpha_pattern = r'([A-Z])\.\s*(.+?)(?:\n|$)'
    for match in re.finditer(alpha_pattern, content):
        letter = match.group(1)
        desc = match.group(2).strip()
        if len(desc) > 5:  # 过滤太短的行
            steps.append({
                "index": ord(letter) - ord('A') + 1,
                "description": desc
            })

    # 去重并排序
    seen = set()
    unique_steps = []
    for s in sorted(steps, key=lambda x: x["index"]):
        key = s["description"][:50]
        if key not in seen:
            seen.add(key)
            unique_steps.append(s)

    return unique_steps


def extract_cli_usage(content):
    """提取 CLI 使用方式"""
    cli_info = []

    # 匹配代码块中的命令
    code_blocks = re.findall(r'```(?:bash|shell)?\n(.*?)```', content, re.DOTALL)
    for block in code_blocks:
        for line in block.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("//"):
                cli_info.append(line)

    return cli_info[:20]  # 限制数量


def extract_all(skill_name, skill_path=None):
    """提取技能的所有关键信息"""
    if skill_path is None:
        skill_dir = find_skill_dir(skill_name)
        if not skill_dir:
            return {"error": f"技能 '{skill_name}' 未找到", "skill_name": skill_name}
    else:
        skill_dir = Path(skill_path)

    content = read_skill_md(skill_dir)
    if content is None:
        return {"error": f"SKILL.md 不存在于 {skill_dir}", "skill_name": skill_name}

    frontmatter = extract_frontmatter(content)
    description = extract_description(content)
    triggers = extract_trigger_keywords(content)
    commands = extract_core_commands(content)
    skill_instructions = extract_skill_instructions(content)
    key_steps = extract_key_steps(content)
    cli_usage = extract_cli_usage(content)

    # 读取 _meta.json
    meta = {}
    meta_file = skill_dir / "_meta.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

    return {
        "skill_name": skill_name,
        "dir_name": skill_dir.name,
        "slug": frontmatter.get("slug", meta.get("slug", "")),
        "version": frontmatter.get("version", meta.get("version", "")),
        "agent_created": frontmatter.get("agent_created", False),
        "description": description[:500],
        "trigger_keywords": triggers[:10],
        "core_commands": commands[:10],
        "skill_instructions": skill_instructions[:20],
        "key_steps": key_steps[:10],
        "cli_examples": cli_usage[:10],
        "has_scripts": (skill_dir / "scripts").is_dir(),
        "script_files": [f.name for f in (skill_dir / "scripts").glob("*.py")] if (skill_dir / "scripts").is_dir() else []
    }


# ============================================================
# 命令实现
# ============================================================

def cmd_extract(args):
    """提取单个技能的关键信息"""
    result = extract_all(args.skill, args.path)
    if "error" in result:
        print(f"❌ {result['error']}")
        return 1

    print(f"📌 技能: {result['skill_name']}")
    print(f"{'='*60}")
    print(f"  目录: {result['dir_name']}")
    if result.get("slug"):
        print(f"  Slug: {result['slug']}")
    if result.get("version"):
        print(f"  版本: {result['version']}")
    print(f"  描述: {result['description'][:200]}")

    if result.get("trigger_keywords"):
        print(f"\n  🔑 触发关键词:")
        for t in result["trigger_keywords"]:
            print(f"     - {t}")

    if result.get("core_commands"):
        print(f"\n  📋 核心指令:")
        for c in result["core_commands"]:
            cmd_str = f" ({c['command']})" if c.get("command") and c["command"] != c["name"] else ""
            print(f"     - {c['name']}{cmd_str}")

    # v1.1.0: 显示可用的 skill_instruction 候选
    if result.get("skill_instructions"):
        print(f"\n  🏷️ 可用指令（skill_instruction 候选）:")
        for si in result["skill_instructions"]:
            print(f"     - {si}")

    if result.get("key_steps"):
        print(f"\n  🔧 关键步骤:")
        for s in result["key_steps"]:
            print(f"     {s['index']}. {s['description']}")

    if result.get("has_scripts"):
        print(f"\n  📁 脚本文件:")
        for sf in result["script_files"]:
            print(f"     - {sf}")

    # JSON 输出（可选）
    if args.json:
        print(f"\n{'─'*60}")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


def cmd_scan(args):
    """扫描所有已安装技能"""
    if not SKILLS_DIR.exists():
        print(f"❌ 技能目录不存在: {SKILLS_DIR}")
        return 1

    skills = []
    for entry in sorted(SKILLS_DIR.iterdir()):
        if entry.is_dir() and not entry.name.startswith("."):
            skill_md = entry / "SKILL.md"
            if skill_md.exists():
                skills.append(entry)

    if not skills:
        print("📋 未找到任何已安装技能")
        return 0

    print(f"📋 扫描已安装技能（共 {len(skills)} 个）")
    print(f"{'='*60}")

    results = []
    for skill_dir in skills:
        result = extract_all(skill_dir.name, skill_dir)
        if "error" not in result:
            # 标签过滤
            if args.tag:
                desc_lower = result.get("description", "").lower()
                triggers_str = " ".join(result.get("trigger_keywords", [])).lower()
                tags_str = desc_lower + " " + triggers_str
                if args.tag.lower() not in tags_str:
                    continue
            results.append(result)

    if not results:
        print(f"  未找到匹配 '{args.tag}' 的技能" if args.tag else "  无结果")
        return 0

    for r in results:
        print(f"\n  📌 {r['dir_name']}")
        print(f"     描述: {r['description'][:100]}")
        if r.get("trigger_keywords"):
            print(f"     触发: {'; '.join(r['trigger_keywords'][:3])}")
        if r.get("core_commands"):
            cmd_names = [c["name"] for c in r["core_commands"][:5]]
            print(f"     指令: {', '.join(cmd_names)}")
        if r.get("skill_instructions"):
            si_names = r["skill_instructions"][:5]
            print(f"     可用指令: {', '.join(si_names)}")
        scripts = r.get("script_files", [])
        if scripts:
            print(f"     脚本: {', '.join(scripts)}")

    # JSON 输出（可选）
    if args.json:
        print(f"\n{'─'*60}")
        print(json.dumps(results, ensure_ascii=False, indent=2))

    return 0


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Skill Extractor v1.1.0 - 技能关键步骤提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python skill_extractor.py extract --skill "triphasic-execution"
  python skill_extractor.py extract --skill "git-sync" --json
  python skill_extractor.py scan
  python skill_extractor.py scan --tag "搜索"
  python skill_extractor.py scan --json
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # extract
    p_extract = subparsers.add_parser("extract", help="提取单个技能的关键信息")
    p_extract.add_argument("--skill", required=True, help="技能名称")
    p_extract.add_argument("--path", default=None, help="技能目录路径（可选）")
    p_extract.add_argument("--json", action="store_true", help="JSON 格式输出")

    # scan
    p_scan = subparsers.add_parser("scan", help="扫描所有已安装技能")
    p_scan.add_argument("--tag", default=None, help="按关键词过滤")
    p_scan.add_argument("--json", action="store_true", help="JSON 格式输出")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "extract": cmd_extract,
        "scan": cmd_scan,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
