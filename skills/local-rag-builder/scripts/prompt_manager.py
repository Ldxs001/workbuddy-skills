"""
local-rag-builder Prompt 管理模块
v0.2.0
系统层（固化）+ 用户层（可配置）分离设计
"""

import os
import sys
from utils import PROMPTS_DIR

# ==================== 系统层（固化，用户不可见） ====================
# 包含：A 系统指令 + B 资料占位 + C 问题占位 + E 回答前缀
SYSTEM_PROMPT_PREFIX = "基于以下资料回答问题。如果资料中没有相关信息，请说\"不知道\"。\n\n资料：\n{context}\n\n问题：\n{question}\n\n回答："

# ==================== 用户层（可配置，默认值） ====================
# 只包含 D 输出格式指令，暴露给用户编辑
DEFAULT_USER_TEMPLATE = "请用 Markdown 格式输出，并在末尾附上引用片段编号。"

TEMPLATE_FILE = os.path.join(PROMPTS_DIR, "custom_prompt_template.txt")


def get_template_path():
    return TEMPLATE_FILE


def load_template():
    """加载用户层 Prompt 模板，不存在则返回默认用户模板"""
    try:
        if os.path.exists(TEMPLATE_FILE):
            with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    # 向后兼容：旧模板包含完整 SYSTEM_PREFIX → 剥离并迁移
                    # 检测标志：末尾含 "回答："
                    if "回答：" in content and ("资料：" in content or "问题：" in content):
                        suffix = content[content.rfind("回答：") + 4:].strip()
                        if suffix:
                            save_template(suffix)
                            return suffix
                        return DEFAULT_USER_TEMPLATE
                    # 用户模板中不应有 {context}/{question}（系统层已有）
                    if "{context}" in content or "{question}" in content:
                        return content
                    return content
    except (OSError, IOError):
        pass
    return DEFAULT_USER_TEMPLATE


def save_template(content):
    """保存用户层 Prompt 模板"""
    try:
        tmp = TEMPLATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content.strip())
        os.replace(tmp, TEMPLATE_FILE)
        return True
    except (OSError, IOError) as e:
        return False


def reset_template():
    """重置用户层为默认"""
    save_template(DEFAULT_USER_TEMPLATE)
    return DEFAULT_USER_TEMPLATE


def get_default_template():
    """获取完整 Prompt（系统+用户默认，供显示）"""
    return SYSTEM_PROMPT_PREFIX + DEFAULT_USER_TEMPLATE


def get_full_prompt(user_template=None):
    """获取完整 Prompt（系统+用户，供构建）"""
    user = user_template or load_template()
    return SYSTEM_PROMPT_PREFIX + user


def build_prompt(context, question, template=None):
    """构建最终 Prompt：系统层 + 用户层，填充占位符"""
    full = get_full_prompt(template)
    return full.format(context=context, question=question)


def list_saved_templates():
    """列出所有已保存的模板"""
    templates = []
    prompts_dir = PROMPTS_DIR
    if not os.path.exists(prompts_dir):
        return templates
    for f in os.listdir(prompts_dir):
        if f.endswith(".txt"):
            templates.append(f)
    return templates


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prompt 管理工具")
    parser.add_argument("--show", action="store_true", help="显示当前用户层模板")
    parser.add_argument("--show-full", action="store_true", help="显示完整 Prompt（系统+用户）")
    parser.add_argument("--set", type=str, help="设置用户层模板内容（多行用 \\n 分隔）")
    parser.add_argument("--set-file", type=str, help="从文件读取并设置用户层模板")
    parser.add_argument("--reset", action="store_true", help="重置用户层为默认")
    parser.add_argument("--list", action="store_true", help="列出所有已保存模板")

    args = parser.parse_args()

    if args.show:
        print(load_template())
    elif args.show_full:
        print(get_full_prompt())
    elif args.set:
        content = args.set.replace("\\n", "\n")
        save_template(content)
        print(f"[OK] 用户层模板已保存 ({len(content)} 字符)")
    elif args.set_file:
        try:
            with open(args.set_file, "r", encoding="utf-8") as f:
                save_template(f.read())
            print(f"[OK] 已从 {args.set_file} 加载用户层模板")
        except (OSError, IOError) as e:
            print(f"[!] 读取文件失败: {e}")
            sys.exit(1)
    elif args.reset:
        save_template(DEFAULT_USER_TEMPLATE)
        print("[OK] 已重置用户层为默认")
    elif args.list:
        templates = list_saved_templates()
        for t in templates:
            print(t)
    else:
        parser.print_help()
