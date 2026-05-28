import sys, os, json

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ref_path = os.path.join(SKILL_DIR, "references", "reference.md")

with open(ref_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix run_audit CLI docs - replace wrong section with correct one
old_section = '''### run_audit — 全量审计入口\n\n**功能：** 对指定技能目录执行全部 24 条规则（R-01~R-24）的审计，支持三种模式。\n\n```bash\n# 创建模式审计（新技能）\npython scripts/run_audit.py <skill_dir> --mode create\n\n# 更新模式审计（已有技能）\npython scripts/run_audit.py <skill_dir> --mode update\n\n# 重构模式审计\npython scripts/run_audit.py <skill_dir> --mode refactor\n\n# 指定输出格式 + 自动修复\npython scripts/run_audit.py <skill_dir> --mode update --output html --fix\n\n# 输出 JSON 报告\npython scripts/run_audit.py <skill_dir> --mode update --output json\n```\n\n**参数说明：**\n| 参数 | 类型 | 必需 | 默认值 | 说明 |\n|------|------|------|--------|------|\n| `skill_dir` | str(位置) | 是 | — | 技能根目录路径 |\n| `--mode` | str | 是 | — | 模式：`create` / `update` / `refactor` |\n| `--output` | str | 否 | text | 输出格式：`json` / `html` / `text` |\n| `--fix` | flag | 否 | False | 审计后自动调用 `apply_fix` 修复 |'''

new_section = '''### run_audit.py — 全量审计入口\n\n**功能：** 对指定技能目录执行全部 24 条规则（R-01~R-24）的审计，支持 audit/check/fix 三种子命令。\n\n```bash\n# 全量审计（默认输出文本格式）\npython scripts/run_audit.py audit <skill_dir> [--output text|json|html]\n\n# 快速检查（仅核心规则）\npython scripts/run_audit.py check <skill_dir>\n\n# 审计后自动修复\npython scripts/run_audit.py audit <skill_dir> --fix\n\n# JSON 格式输出\npython scripts/run_audit.py audit <skill_dir> --output json\n```\n\n**子命令说明：**\n| 子命令 | 说明 | 参数 |\n|--------|------|------|\n| `audit <dir>` | 全量审计（R-01~R-24） | `[--output text|json|html]` `[--fix]` |\n| `check <dir>` | 快速检查（仅核心规则） | 无 |\n| `fix <dir>` | 审计后自动修复 | 无 |\n\n**参数说明：**\n| 参数 | 类型 | 必需 | 默认值 | 说明 |\n|------|------|------|--------|------|\n| `skill_dir` | str(位置) | 是 | — | 技能根目录路径 |\n| `--output` | str | 否 | text | 输出格式：`json` / `html` / `text` |\n| `--fix` | flag | 否 | False | 审计后自动调用 `apply_fix` 修复 |'''

if old_section in content:
    new_content = content.replace(old_section, new_section)
    print("✅ 找到并替换了 run_audit 章节")
else:
    # Try to find the actual content and fix it
    if '### run_audit — 全量审计入口' in content:
        print("⚠️ 找到标题但未匹配完整章节，尝试手动修复")
        # Find the section and replace it manually
        import re
        pattern = r'### run_audit [^\n]*\n\n\*\*功能：[^\n]*\n\n```bash\n.*?```\n\n\*\*参数说明：[^\n]*\n\| 参数 \|[^\n]*\n\|[^\n]*\n\|[^\n]*\n\|[^\n]*\n\|[^\n]*\n'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            new_content = content[:match.start()] + new_section + '\n\n---\n\n' + content[match.end():]
            print("✅ 正则匹配并替换成功")
        else:
            print("❌ 无法匹配章节内容")
            sys.exit(1)
    else:
        print("❌ 未找到 run_audit 章节")
        sys.exit(1)

# Write back with backup
sys.path.insert(0, os.path.join(SKILL_DIR, 'scripts'))
from safe_io import safe_write
result = safe_write(ref_path, new_content, backup=True)
print(json.dumps(result, ensure_ascii=False, indent=2))
