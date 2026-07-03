#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chain_cache.py - Chain Template Cache v1.0.0
自增强闭环模板缓存 — 参考 semantic-split 的自增强闭环设计。

每次链规划完成后保存为模板，下次相似意图直接复用。
匹配用 step_indexer 同源 n-gram 算法，零外部依赖。
"""

import json
import re
from datetime import datetime
from pathlib import Path

CACHE_DIR = (Path.home() / ".workbuddy" / "skills" / ".standardization"
             / "skill-sub" / "templates")

_TEMPLATE_VERSION = 1


def _ensure_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def save_template(intent, steps, milestones=None, adhesions=None):
    """将链规划结果保存为模板。"""
    _ensure_dir()
    intent_clean = re.sub(r'[\\/:*?"<>|]', '', intent)[:30]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{intent_clean}_{ts}.json"

    template = {
        "version": _TEMPLATE_VERSION,
        "intent": intent,
        "intent_keywords": _extract_keywords(intent),
        "steps": [
            {"step_id": s.get("step_id", s.get("skill_name", "")),
             "step_name": s.get("step_name", ""),
             "action": s.get("action", s.get("description", ""))[:100]}
            for s in steps
        ],
        "step_count": len(steps),
        "milestones": milestones or [],
        "adhesions": adhesions or [],
        "created_at": ts,
        "hit_count": 0,
    }

    path = CACHE_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    return path


def scan_templates(intent, min_score=0.3):
    """扫描模板库，返回匹配分数≥min_score 的模板列表。"""
    _ensure_dir()
    if not CACHE_DIR.exists():
        return []

    intent_keywords = _extract_keywords(intent)
    intent_chars = set("".join(intent_keywords))
    if not intent_chars:
        return []

    results = []
    for f in sorted(CACHE_DIR.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                tmpl = json.load(fh)
        except (json.JSONDecodeError, Exception):
            continue

        tmpl_keywords = tmpl.get("intent_keywords", [])
        tmpl_text = " ".join(tmpl_keywords)
        tmpl_chars = set(tmpl_text)

        # 词级别匹配
        word_matches = sum(1 for w in intent_keywords if w in tmpl_text)
        word_score = word_matches / max(len(intent_keywords), 1)

        # 字符级 n-gram
        char_overlap = len(intent_chars & tmpl_chars) / max(
            len(intent_chars | tmpl_chars), 1)

        # 取最高分
        score = max(word_score, char_overlap)

        if score >= min_score:
            tmpl["score"] = round(score, 2)
            results.append(tmpl)

    results.sort(key=lambda t: -t.get("score", 0))
    return results


def hit_template(intent, min_score=0.3):
    """尝试命中模板。命中返回 (template, score)，否则 (None, 0)。"""
    results = scan_templates(intent, min_score)
    if results:
        t = results[0]
        t["hit_count"] = t.get("hit_count", 0) + 1
        _update_hit_count(t)
        return t, t["score"]
    return None, 0


def _update_hit_count(template):
    """更新模板的命中计数。"""
    _ensure_dir()
    for f in CACHE_DIR.glob("*.json"):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            if (data.get("intent") == template.get("intent")
                    and data.get("created_at") == template.get("created_at")):
                data["hit_count"] = template.get("hit_count", 0)
                with open(f, "w", encoding="utf-8") as fw:
                    json.dump(data, fw, ensure_ascii=False, indent=2)
                return
        except Exception:
            continue


def _extract_keywords(text):
    """从意图文本提取关键词（词频+长度过滤）。"""
    if not text:
        return []
    # 中英文分词—简单按连续字符切
    words = re.findall(r'[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9]{2,}', text)
    return list(set(w.lower() for w in words if len(w) >= 2))


def list_templates():
    """列出所有已保存模板（含命中次数）。"""
    _ensure_dir()
    templates = []
    for f in sorted(CACHE_DIR.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                t = json.load(fh)
            templates.append({
                "filename": f.name,
                "intent": t.get("intent", "")[:40],
                "steps": t.get("step_count", 0),
                "milestones": t.get("milestones", []),
                "hit_count": t.get("hit_count", 0),
                "created_at": t.get("created_at", "?"),
            })
        except Exception:
            continue
    return templates


def clear_all():
    """清空所有模板缓存。"""
    _ensure_dir()
    count = 0
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
        count += 1
    print(f"✅ 已清除 {count} 个模板")
    return count


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for t in list_templates():
            print(f"  {t['filename'][:30]:30s} steps={t['steps']} "
                  f"hits={t['hit_count']} intent={t['intent']}")
    elif cmd == "clear":
        clear_all()
    elif cmd == "scan":
        intent = sys.argv[2] if len(sys.argv) > 2 else ""
        results = scan_templates(intent)
        print(f"搜索\"{intent}\": {len(results)} 个匹配")
        for r in results[:5]:
            print(f"  [{r['score']}] {r.get('intent','')[:40]} → {r['step_count']}步")
    else:
        print("用法: python chain_cache.py [list|clear|scan <intent>]")
