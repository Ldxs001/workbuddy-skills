"""
knowledge_schema — 知识库标准化接口

标准化格式说明：
- 知识条目采用 **YAML frontmatter + Markdown** 格式
  （与 Obsidian / Hugo / Jekyll / Notion 导出同款，用户基础极大）
- 项目数据采用 **JSON** 自描述格式
- 内置转换器：外部数据库 → 标准格式 → 知识库

标准格式（LLM 可直接生成）：
────────────────────────────────────────
  知识条目（YAML+Markdown）:
  ---
  title: 文档标题
  type: note          # note / article / benchmark / industry
  tags: [AI, Agent]
  domain: ai-enterprise
  source: Gartner 2026
  created: 2026-06-03
  ---
  Markdown content here...

  项目数据（JSON）:
  {
    "format": "wbs-v1",
    "project": { "name": "...", "domain": "..." },
    "work_packages": [...],
    "dependencies": [...]
  }
────────────────────────────────────────
"""
import json
import os
import re
import sqlite3
from datetime import datetime
from typing import Optional

# ═══════════════════════════════════════════════════════
# 标准字段定义
# ═══════════════════════════════════════════════════════

ENTRY_FIELDS = {
    "title":      "标题（必填）",
    "type":       "类型: note(笔记) / article(文章) / benchmark(基准) / industry(行业) / project_ref(项目参考)",
    "tags":       "标签列表，如 [AI, Agent] 或 'AI,Agent'",
    "domain":     "领域: ai-enterprise / construction / software / manufacturing / event / research / general",
    "source":     "来源（URL/书名/报告名）",
    "ref_link":   "引用链接",
    "created":    "创建日期 YYYY-MM-DD",
    "content":    "内容（Markdown 格式）",
}

PROJECT_FIELDS = {
    "project.name":        "项目名称",
    "project.description": "项目描述",
    "project.domain":      "项目领域",
    "project.scale":       "规模: small / medium / large",
    "work_packages[].id":  "任务ID（1-based，必填）",
    "work_packages[].name": "任务名称（如 1.1 痛点调研）",
    "work_packages[].phase": "所属阶段编号（如 1）",
    "work_packages[].o":   "乐观估算（天）",
    "work_packages[].m":   "最可能估算（天）",
    "work_packages[].p":   "悲观估算（天）",
    "work_packages[].deliverable": "交付物",
    "dependencies[].task":     "任务ID",
    "dependencies[].depends_on": "前置任务ID",
    "dependencies[].type":     "依赖类型: FS / SS / FF / SF",
}


# ═══════════════════════════════════════════════════════
# 格式转换器
# ═══════════════════════════════════════════════════════

def entry_to_markdown(entry: dict) -> str:
    """
    将知识条目转为标准 YAML frontmatter + Markdown 格式。
    输出的文件可被 Obsidian / Hugo / Jekyll 直接读取。
    """
    title = entry.get("title", "未命名")
    content = entry.get("content", "")
    
    # 构建 frontmatter
    front = ["---"]
    front.append(f'title: "{title}"')
    front.append(f'type: {entry.get("type", "note")}')
    
    tags = entry.get("tags", "")
    if isinstance(tags, str) and tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        front.append(f"tags: [{', '.join(tag_list)}]")
    elif isinstance(tags, list) and tags:
        front.append(f"tags: [{', '.join(tags)}]")
    
    if entry.get("domain"):
        front.append(f"domain: {entry['domain']}")
    if entry.get("source"):
        front.append(f'source: "{entry["source"]}"')
    if entry.get("ref_link"):
        front.append(f'ref_link: "{entry["ref_link"]}"')
    front.append(f'created: {datetime.now().strftime("%Y-%m-%d")}')
    front.append("---")
    front.append("")
    
    return "\n".join(front) + content


def parse_markdown_entry(text: str) -> dict:
    """
    将 YAML frontmatter + Markdown 解析为知识条目字典。
    支持 Obsidian / Hugo / Jekyll 风格的 frontmatter。
    """
    entry = {"title": "", "content": "", "type": "note", "tags": "", "domain": "", "source": "", "ref_link": ""}
    
    # 解析 frontmatter
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', text, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        entry["content"] = fm_match.group(2).strip()
        
        for line in fm_text.strip().split("\n"):
            line = line.strip()
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip().strip('"').strip("'")
            
            if key == "title":
                entry["title"] = value
            elif key == "type":
                entry["type"] = value
            elif key == "tags":
                # 支持 [tag1, tag2] 和 "tag1,tag2" 和 tag1,tag2
                value = value.strip("[]").strip("()")
                entry["tags"] = ",".join(t.strip().strip('"').strip("'") for t in value.split(",") if t.strip())
            elif key == "domain":
                entry["domain"] = value
            elif key == "source":
                entry["source"] = value
            elif key == "ref_link":
                entry["ref_link"] = value
    else:
        # 无 frontmatter，整段当内容
        entry["content"] = text.strip()
        # 尝试从内容第一行提取标题
        first_line = text.strip().split("\n")[0]
        if first_line.startswith("#"):
            entry["title"] = first_line.lstrip("#").strip()
        else:
            entry["title"] = first_line[:50] if len(first_line) < 50 else first_line[:47] + "..."
    
    return entry


def project_to_json(state) -> str:
    """
    将 PipelineState 转为标准 JSON 格式。
    输出可被其他工具直接解析。
    """
    wp_list = []
    if hasattr(state, 'phases') and state.phases:
        for i, p in enumerate(state.phases, 1):
            is_cp = False
            if hasattr(state, 'cpm_result') and state.cpm_result and state.cpm_result.critical_ids:
                is_cp = i in state.cpm_result.critical_ids
            wp_list.append({
                "id": i,
                "name": p.get("name", ""),
                "phase": re.match(r'^(\d+)\.', p.get("name", "").strip()).group(1) if re.match(r'^(\d+)\.', p.get("name", "").strip()) else "",
                "o": p.get("o", 0), "m": p.get("m", 0), "p": p.get("p", 0),
                "deliverable": p.get("deliverable", ""),
                "is_critical": is_cp,
            })

    dep_list = []
    if hasattr(state, 'dependencies') and state.dependencies:
        for tid, deps in state.dependencies.items():
            for dep in (deps if isinstance(deps, list) else [deps]):
                pd = dep[0] if isinstance(dep, (list, tuple)) else dep
                dt = dep[1] if isinstance(dep, (list, tuple)) and len(dep) >= 2 else "FS"
                dep_list.append({"task": tid, "depends_on": pd, "type": dt})

    data = {
        "format": "wbs-v1",
        "schema": "https://workbuddy-skills.github.io/schemas/wbs-v1.json",
        "project": {
            "name": getattr(state, 'project_name', ""),
            "description": getattr(state, 'description', ""),
            "domain": "",
            "total_duration": getattr(state, 'cpm_result', None).project_duration if hasattr(state, 'cpm_result') and state.cpm_result else 0,
        },
        "work_packages": wp_list,
        "dependencies": dep_list,
    }

    return json.dumps(data, ensure_ascii=False, indent=2)


def parse_project_json(json_str: str) -> tuple[list[dict], dict]:
    """
    将标准 JSON 项目数据解析为 (phases, dependencies) 元组。
    可直接用于 PipelineState。
    """
    data = json.loads(json_str)
    if data.get("format") != "wbs-v1":
        raise ValueError(f"不支持的格式: {data.get('format')}。仅支持 wbs-v1")

    phases = []
    for wp in data.get("work_packages", []):
        phases.append({
            "name": wp.get("name", ""),
            "o": wp.get("o", 0), "m": wp.get("m", 0), "p": wp.get("p", 0),
            "deliverable": wp.get("deliverable", ""),
        })

    deps = {}
    for dep in data.get("dependencies", []):
        tid = dep.get("task", 0)
        pred = dep.get("depends_on", 0)
        dtype = dep.get("type", "FS")
        if tid and pred:
            deps.setdefault(tid, []).append((pred, dtype))

    return phases, deps


# ═══════════════════════════════════════════════════════
# 外部数据库标准化对接
# ═══════════════════════════════════════════════════════

TABLE_MAPPINGS = {
    "default": {
        "title": "title",
        "content": "content",
        "type": "type",
        "tags": "tags",
        "domain": "domain",
        "source": "source",
    },
    "obsidian": {
        "description": "Obsidian vault 中的 Markdown 文件",
        "title": "filename",     # 文件名作为标题
        "content": "body",       # 文件内容
        "tags": "frontmatter.tags",  # frontmatter 中的 tags
        "domain": "frontmatter.domain",
        "type": "frontmatter.type",
    },
    "notion_export": {
        "description": "Notion 导出的 Markdown/CSV",
        "title": "Name",
        "content": "Content",
        "tags": "Tags",
        "domain": "Domain",
    },
    "hugo": {
        "description": "Hugo 静态站点的 content/ 目录",
        "title": "frontmatter.title",
        "content": "body",
        "tags": "frontmatter.tags",
        "domain": "frontmatter.domain",
    },
    "jira_export": {
        "description": "Jira 导出的项目数据（CSV）",
        "title": "Summary",
        "content": "Description",
        "type": "Issue Type",
        "tags": "Labels",
    },
}


def detect_table_mapping(external_db: str, table_name: str) -> dict | None:
    """
    自动检测外部表的字段映射。
    通过字段名匹配已知模式。
    """
    if not os.path.exists(external_db):
        return None
    
    conn = sqlite3.connect(external_db)
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1].lower() for row in cursor.fetchall()]
    conn.close()

    # 匹配已知映射
    for name, mapping in TABLE_MAPPINGS.items():
        if name == "default":
            continue
        # 检查关键字段是否存在
        key_fields = [v.split(".")[0] for v in mapping.values() if "." not in v]
        if "title" in mapping:
            key_fields.append(mapping["title"].split(".")[0])
        if all(f.lower() in columns for f in key_fields if f):
            return mapping
    
    # 回退：猜测映射
    guessed = {"title": "title", "content": "content"}
    for col in columns:
        if col in ("title", "name", "subject", "标题"):
            guessed["title"] = col
        elif col in ("content", "body", "text", "description", "内容"):
            guessed["content"] = col
        elif col in ("tags", "labels", "label", "tag", "标签"):
            guessed["tags"] = col
        elif col in ("domain", "category", "categories", "领域"):
            guessed["domain"] = col
        elif col in ("source", "url", "link", "来源", "链接"):
            guessed["source"] = col
        elif col in ("type", "kind", "entry_type", "类型"):
            guessed["type"] = col
    
    return guessed if len(guessed) > 1 else None


def generate_mapping_guide(external_columns: list[str]) -> str:
    """
    根据外部表的列名，生成字段映射指南（供 LLM 参考）。
    """
    guide = ["# 字段映射指南\n"]
    guide.append(f"外部表包含以下字段: {', '.join(external_columns)}\n")
    guide.append("建议映射到标准字段：\n")
    
    known = {
        "title": ["title", "name", "subject", "标题", "名称", "主题"],
        "content": ["content", "body", "text", "description", "内容", "正文", "描述"],
        "tags": ["tags", "labels", "label", "tag", "标签", "分类"],
        "domain": ["domain", "category", "categories", "领域", "类别"],
        "source": ["source", "url", "link", "来源", "来源链接"],
        "type": ["type", "kind", "entry_type", "类型"],
    }
    
    for standard, candidates in known.items():
        matches = [c for c in external_columns if c.lower() in candidates]
        if matches:
            guide.append(f"- {standard}: {matches[0]}")
        else:
            guide.append(f"- {standard}: (未找到匹配字段)")
    
    guide.append("\n映射示例：\n")
    guide.append('import_external_knowledge("old.db", "table", {')
    for standard, candidates in known.items():
        matches = [c for c in external_columns if c.lower() in candidates]
        guide.append(f'    "{standard}": "{matches[0] if matches else "?"}",')
    guide.append('})')
    
    return "\n".join(guide)


# ═══════════════════════════════════════════════════════
# 格式校验
# ═══════════════════════════════════════════════════════

def validate_entry(entry: dict) -> list[str]:
    """校验知识条目是否符合标准格式，返回错误列表"""
    errors = []
    if not entry.get("title"):
        errors.append("缺少必填字段: title")
    if entry.get("type") and entry["type"] not in ("note", "article", "benchmark", "industry", "project_ref", "imported"):
        errors.append(f"不支持的 type: {entry['type']}（应为 note/article/benchmark/industry/project_ref）")
    if entry.get("domain") and entry["domain"] not in ("ai-enterprise", "construction", "software", "manufacturing", "event", "research", "general"):
        errors.append(f"未知 domain: {entry['domain']}")
    return errors


def validate_project_json(json_str: str) -> list[str]:
    """校验项目 JSON 是否符合标准格式"""
    errors = []
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return [f"JSON 解析失败: {e}"]
    
    if data.get("format") != "wbs-v1":
        errors.append(f"format 应为 wbs-v1，收到: {data.get('format')}")
    if not data.get("project", {}).get("name"):
        errors.append("缺少 project.name")
    if not data.get("work_packages"):
        errors.append("缺少 work_packages")
    else:
        for wp in data["work_packages"]:
            if not wp.get("id"):
                errors.append("work_packages 中存在无 id 的条目")
            if not wp.get("name"):
                errors.append(f"work_packages 中存在无名条目 (id={wp.get('id')})")
    
    return errors
