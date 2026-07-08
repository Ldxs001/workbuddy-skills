"""
skill_scanner.py — 扫描技能目录，解析 SKILL.md frontmatter
零外部依赖，纯字符串解析 YAML frontmatter
"""

import os, re, sys

_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from chain_model import SkillInfo

SKILLS_BASE = os.path.expanduser("~/.workbuddy/skills")


def _parse_frontmatter(text: str) -> dict:
    """从 SKILL.md 文本中提取 YAML frontmatter（--- 块）"""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    end = 1
    while end < len(lines) and lines[end].strip() != "---":
        end += 1
    meta = {}
    for line in lines[1:end]:
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # 列表 [a, b, c]
        if value.startswith("[") and value.endswith("]"):
            items = value[1:-1].split(",")
            value = [i.strip().strip("'\"").strip("'") for i in items if i.strip()]
        # 布尔
        elif value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        # 字符串
        else:
            value = value.strip("'\"")

        # 处理一个 key 对应多个 trigger 当它是字符串/分隔时
        if key in ("trigger", "trigger_negative") and isinstance(value, str):
            value = re.split(r"[/,，、]", value)
            value = [v.strip() for v in value if v.strip()]

        meta[key] = value
    return meta


def scan_skills(*base_dirs: str) -> list[SkillInfo]:
    """扫描一个或多个技能目录，返回所有技能的 SkillInfo 列表
    不传参数时默认扫描 ~/.workbuddy/skills/
    """
    dirs = list(base_dirs) if base_dirs else [SKILLS_BASE]
    all_skills = []
    seen_names: set[str] = set()

    for base in dirs:
        if not os.path.isdir(base):
            continue

        for entry in sorted(os.listdir(base)):
            skill_dir = os.path.join(base, entry)
            skill_md = os.path.join(skill_dir, "SKILL.md")
            if not os.path.isdir(skill_dir) or not os.path.isfile(skill_md):
                continue

            try:
                with open(skill_md, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                all_skills.append(SkillInfo(name=entry, error=str(e)))
                continue

            meta = _parse_frontmatter(content)
            name = meta.get("name", entry)
            if name in seen_names:
                name = f"{name} ({entry})"
            seen_names.add(name)

            tags = meta.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]

            triggers = meta.get("trigger", [])
            if isinstance(triggers, str):
                triggers = [triggers]

            info = SkillInfo(
                name=name,
                display_name=meta.get("displayName", meta.get("name", "")),
                description=meta.get("description", ""),
                version=str(meta.get("version", "")),
                author=meta.get("author", ""),
                tags=tags,
                triggers=triggers,
                path=skill_dir,
                permission_weight=str(meta.get("permission_weight", "")),
                sensitive_access=bool(meta.get("sensitive_access", False)),
                critical_write=bool(meta.get("critical_write", False)),
            )
            all_skills.append(info)

    return all_skills


def search_skills(skills: list[SkillInfo], query: str) -> list[SkillInfo]:
    """按名称/描述/标签搜索技能"""
    q = query.lower().strip()
    if not q:
        return skills
    result = []
    for s in skills:
        if (q in s.name.lower() or
            q in s.display_name.lower() or
            q in s.description.lower() or
            any(q in t.lower() for t in s.tags)):
            result.append(s)
    return result
