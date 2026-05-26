#!/usr/bin/env python3
"""P2 扩展点补丁：参数提取 + 兼容性检查 + 资源分析 + Plan B 生成"""
from pathlib import Path
import json
import re

SKILL_DIR = Path(r"C:\Users\sm001\.workbuddy\skills\skill-sub")


def patch_parameter_extraction():
    """参数提取：增强 skill_extractor.py，提取技能的命令行参数 schema"""
    p = SKILL_DIR / "scripts" / "skill_extractor.py"
    if not p.exists():
        print("  ❌ skill_extractor.py 不存在")
        return False

    content = p.read_text(encoding="utf-8")

    # 检查是否已存在
    if "def extract_parameters(" in content:
        print("  ⚠️  extract_parameters 已存在")
        return True

    # 在文件末尾添加新函数
    new_func = '''
def extract_parameters(skill_name):
    """提取技能的命令行参数 schema"""
    skill_path = find_skill_path(skill_name)
    if not skill_path:
        return None, f"技能 {skill_name} 未找到"

    skill_dir = skill_path.parent
    schema = {
        "skill_name": skill_name,
        "parameters": {},
        "examples": []
    }

    # 1. 从 SKILL.md 中提取参数信息
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        md_content = skill_md.read_text(encoding="utf-8")
        # 查找参数部分
        param_section = re.search(
            r"## .*参数.*\n(.*?)(?=\n## |\Z)",
            md_content, re.DOTALL | re.IGNORECASE
        )
        if param_section:
            schema["parameters"]["from_skill_md"] = param_section.group(1)[:500]

    # 2. 从 Python 脚本中提取 argparse 参数
    for py_file in skill_dir.glob("scripts/*.py"):
        try:
            py_content = py_file.read_text(encoding="utf-8")
            # 查找 add_argument 调用
            args_found = re.findall(
                r"add_argument\(\s*[\"\\']([^\"\\']+)[\"\\']"
                r"(?:.*?description=[\"\\']([^\"\\']*?)[\"\\'])?",
                py_content, re.DOTALL
            )
            for arg_name, arg_desc in args_found:
                schema["parameters"][arg_name] = {
                    "description": arg_desc or "",
                    "from_script": py_file.name
                }
        except Exception:
            pass

    # 3. 从 references/ 中提取参数信息
    ref_dir = skill_dir / "references"
    if ref_dir.exists():
        for ref_file in ref_dir.glob("*.md"):
            try:
                ref_content = ref_file.read_text(encoding="utf-8")
                # 查找参数示例
                examples = re.findall(
                    r"--\w+.*?(?=\n|$)",
                    ref_content, re.MULTILINE
                )
                schema["examples"].extend(examples[:5])
            except Exception:
                pass

    return schema, None


def cmd_extract_params(args):
    """命令行接口：提取技能参数"""
    schema, err = extract_parameters(args.skill)
    if err:
        print(f"❌ {err}")
        return 1

    print(f"📋 参数提取: {args.skill}")
    print(f"{'='*70}")
    print(json.dumps(schema, ensure_ascii=False, indent=2))

    # 保存到缓存
    cache_dir = SKILL_DIR / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"params_{args.skill}.json"
    cache_file.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n✅ 已保存到 {cache_file}")

    return 0
'''

    # 插入到文件末尾
    content = content.rstrip() + new_func
    p.write_text(content, encoding="utf-8")
    print("  ✅ 参数提取功能已添加")
    return True


def patch_compatibility_check():
    """兼容性检查：添加 check_compatibility 函数"""
    p = SKILL_DIR / "scripts" / "chain_manager.py"
    if not p.exists():
        print("  ❌ chain_manager.py 不存在")
        return False

    content = p.read_text(encoding="utf-8")

    if "def check_compatibility(" in content:
        print("  ⚠️  check_compatibility 已存在")
        return True

    # 在文件末尾添加
    new_func = '''
def check_compatibility(chain_name):
    """检查调用链中技能的版本兼容性"""
    chain = load_chain(chain_name)
    if not chain:
        return None, f"调用链 {chain_name} 不存在"

    steps = chain.get("steps", [])
    issues = []

    for step in steps:
        skill_name = step.get("skill_name", "")
        if not skill_name or skill_name in ("(内置)", "(内置打包)"):
            continue

        # 检查技能是否存在
        skill_path = find_skill_path(skill_name)
        if not skill_path:
            issues.append({
                "step": step.get("step_name", "?"),
                "skill": skill_name,
                "issue": "技能未安装",
                "severity": "error"
            })
            continue

        # 检查技能版本（如果有 version 文件）
        version_file = skill_path.parent / "version.txt"
        if version_file.exists():
            version = version_file.read_text(encoding="utf-8").strip()
            # 简单检查：如果版本号包含 "v1." 但当前是 "v2."，可能有兼容性问题
            if version.startswith("v1.") and "v2." in version:
                issues.append({
                    "step": step.get("step_name", "?"),
                    "skill": skill_name,
                    "issue": f"版本可能不兼容: {version}",
                    "severity": "warning"
                })

    return issues, None


def cmd_check_compat(args):
    """命令行接口：检查兼容性"""
    issues, err = check_compatibility(args.name)
    if err:
        print(f"❌ {err}")
        return 1

    if not issues:
        print(f"✅ {args.name} 没有兼容性问题")
        return 0

    print(f"🔍 兼容性检查: {args.name}")
    print(f"{'='*70}")
    for issue in issues:
        icon = "❌" if issue["severity"] == "error" else "⚠️"
        print(f"  {icon} {issue['step']} ({issue['skill']}): {issue['issue']}")

    return 0
'''

    content = content.rstrip() + new_func
    p.write_text(content, encoding="utf-8")
    print("  ✅ 兼容性检查功能已添加")
    return True


def patch_resource_analysis():
    """资源分析：添加 analyze_resources 函数"""
    p = SKILL_DIR / "scripts" / "chain_executor.py"
    if not p.exists():
        print("  ❌ chain_executor.py 不存在")
        return False

    content = p.read_text(encoding="utf-8")

    if "def analyze_resources(" in content:
        print("  ⚠️  analyze_resources 已存在")
        return True

    new_func = '''
def analyze_resources(chain):
    """分析调用链的资源需求"""
    steps = chain.get("steps", [])
    analysis = {
        "total_steps": len(steps),
        "skills_needed": set(),
        "network_required": False,
        "file_access": False,
        "external_tools": set(),
        "estimated_time": "未知"
    }

    for step in steps:
        skill_name = step.get("skill_name", "")
        if skill_name and skill_name not in ("(内置)", "(内置打包)"):
            analysis["skills_needed"].add(skill_name)

        # 检查是否需要网络
        action = step.get("action", "").lower()
        if any(kw in action for kw in ["fetch", "download", "api", "http", "网络", "搜索"]):
            analysis["network_required"] = True

        # 检查是否需要文件访问
        if any(kw in action for kw in ["文件", "读取", "写入", "file", "read", "write"]):
            analysis["file_access"] = True

        # 检查是否需要外部工具
        if "browser" in action or "浏览器" in action:
            analysis["external_tools"].add("browser")
        if "git" in action or "同步" in action:
            analysis["external_tools"].add("git")

    # 估算时间（简单规则）
    time_per_step = 30  # 秒
    if analysis["network_required"]:
        time_per_step += 20
    total_time = len(steps) * time_per_step
    analysis["estimated_time"] = f"{total_time}秒 ({total_time//60}分{total_time%60}秒)"

    analysis["skills_needed"] = list(analysis["skills_needed"])
    analysis["external_tools"] = list(analysis["external_tools"])

    return analysis


def cmd_analyze(args):
    """命令行接口：资源分析"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    analysis = analyze_resources(chain)

    print(f"📊 资源分析: {args.name}")
    print(f"{'='*70}")
    print(f"  总步骤数: {analysis['total_steps']}")
    print(f"  所需技能: {', '.join(analysis['skills_needed']) or '无'}")
    print(f"  需要网络: {'是' if analysis['network_required'] else '否'}")
    print(f"  需要文件访问: {'是' if analysis['file_access'] else '否'}")
    print(f"  需要外部工具: {', '.join(analysis['external_tools']) or '无'}")
    print(f"  预估执行时间: {analysis['estimated_time']}")

    return 0
'''

    content = content.rstrip() + new_func
    p.write_text(content, encoding="utf-8")
    print("  ✅ 资源分析功能已添加")
    return True


def patch_plan_b_generation():
    """Plan B 生成：添加 generate_plan_b 函数"""
    p = SKILL_DIR / "scripts" / "chain_executor.py"
    if not p.exists():
        print("  ❌ chain_executor.py 不存在")
        return False

    content = p.read_text(encoding="utf-8")

    if "def generate_plan_b(" in content:
        print("  ⚠️  generate_plan_b 已存在")
        return True

    new_func = '''
def generate_plan_b(chain, step_index):
    """为指定步骤生成 Plan B（备选方案）"""
    steps = chain.get("steps", [])
    if step_index < 0 or step_index >= len(steps):
        return None, "步骤索引超出范围"

    step = steps[step_index]
    skill_name = step.get("skill_name", "")
    action = step.get("action", "")

    plan_b = {
        "original_step": step.get("step_name", ""),
        "alternatives": []
    }

    # 规则1：如果技能是通用的，提供替代技能
    generic_skills = {
        "git-sync": ["git-sync", "skill-sub"],
        "skill-sub": ["skill-sub", "git-sync"],
        "drawiodo": ["drawiodo", "web-search-exa"],
    }

    if skill_name in generic_skills:
        for alt in generic_skills[skill_name]:
            if alt != skill_name:
                plan_b["alternatives"].append({
                    "type": "skill_replacement",
                    "skill": alt,
                    "reason": f"用 {alt} 替代 {skill_name}"
                })

    # 规则2：如果 action 包含特定关键词，提供方法替代
    if "生成" in action or "create" in action:
        plan_b["alternatives"].append({
            "type": "method_change",
            "method": "manual",
            "reason": "如果自动生成失败，可以手动创建"
        })

    if "上传" in action or "upload" in action:
        plan_b["alternatives"].append({
            "type": "method_change",
            "method": "local_save",
            "reason": "如果上传失败，可以先保存到本地"
        })

    # 规则3：添加通用 fallback
    plan_b["alternatives"].append({
        "type": "skip",
        "reason": "如果所有方案都失败，可以跳过此步骤（如果业务允许）"
    })

    return plan_b, None


def cmd_generate_plan_b(args):
    """命令行接口：生成 Plan B"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    plan_b, err = generate_plan_b(chain, args.step - 1)  # 用户看到的 step 是 1-based
    if err:
        print(f"❌ {err}")
        return 1

    print(f"🔄 Plan B 生成: 步骤 {args.step}")
    print(f"{'='*70}")
    print(f"  原步骤: {plan_b['original_step']}")
    print(f"\n  备选方案:")
    for i, alt in enumerate(plan_b["alternatives"], 1):
        print(f"    {i}. [{alt['type']}] {alt['reason']}")

    return 0
'''

    content = content.rstrip() + new_func
    p.write_text(content, encoding="utf-8")
    print("  ✅ Plan B 生成功能已添加")
    return True


if __name__ == "__main__":
    print("=== 开始 P2 扩展点补丁 ===")

    print("[1/4] 参数提取...")
    r1 = patch_parameter_extraction()

    print("[2/4] 兼容性检查...")
    r2 = patch_compatibility_check()

    print("[3/4] 资源分析...")
    r3 = patch_resource_analysis()

    print("[4/4] Plan B 生成...")
    r4 = patch_plan_b_generation()

    if all([r1, r2, r3, r4]):
        print("\n✅ 所有 P2 扩展点补丁成功！")
    else:
        print("\n⚠️ 部分补丁失败，请检查上述输出")
