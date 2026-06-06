"""
local-rag-builder 交互式 CLI 界面
v0.1.0
支持自定义 Prompt、知识库切换、参数调整
"""

import os
import sys
import re
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_core import get_embeddings, get_llm, answer_question, verify_llm_connection, import_documents_to_kb
from config import load_config, save_config, reset_config
from prompt_manager import load_template, save_template, reset_template, get_default_template
from knowledge_base_manager import list_knowledge_bases, create_knowledge_base, delete_knowledge_base, auto_classify, set_classify_rule
from embedding_model_manager import list_downloaded_models, download_model


HELP_TEXT = """
可用命令:
  /help             显示此帮助
  /prompt show      显示当前 Prompt 模板
  /prompt set       设置 Prompt 模板（输入 END 结束）
  /prompt reset     重置为默认模板
  /kb list          列出所有知识库
  /kb create <name> 创建新知识库
  /kb use <name>    切换到指定知识库
  /kb delete <name> 删除知识库
  /kb classify <关键词>  设置自动分类规则
  /model list       列出已下载的嵌入模型
  /model use <id>   切换嵌入模型
  /config show      显示当前配置
  /config set <key> <value>  修改配置
  /reset            重置所有配置
  /import <file>    导入文件到当前知识库
  /verify-llm       验证 LLM 连接
  /exit             退出
"""


def run_interactive():
    """运行交互式 RAG 对话"""
    cfg = load_config()
    active_kb = cfg.get("kb", {}).get("active_kb", "default")

    # 初始化
    print("=" * 50)
    print("  本地 RAG 交互系统")
    print("=" * 50)

    # 验证 LLM 连接
    llm_ok, llm_msg = verify_llm_connection()
    print(f"  [{chr(10003) if llm_ok else '!'}] {llm_msg}")

    # 检查嵌入模型
    try:
        embeddings = get_embeddings()
        print(f"  [{chr(10003)}] 嵌入模型就绪")
    except ValueError as e:
        print(f"  [!] {e}")
        print("  请先运行: python scripts/embedding_model_manager.py --interactive")
        embeddings = None

    print(f"  当前知识库: {active_kb}")
    print(f"  输入 /help 查看命令，直接输入问题开始问答")
    print("=" * 50)

    llm = get_llm()

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出。")
            break

        if not user_input:
            continue

        # 命令处理
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=2)
            cmd = parts[0].lower()

            if cmd == "/exit":
                print("退出。")
                break

            elif cmd == "/help":
                print(HELP_TEXT)

            elif cmd == "/prompt":
                sub = parts[1].lower() if len(parts) > 1 else ""
                if sub == "show":
                    print(f"\n当前 Prompt 模板:\n{'-' * 40}\n{load_template()}\n{'-' * 40}")
                elif sub == "set":
                    print("请输入新模板（输入 END 单独一行结束）：")
                    lines = []
                    while True:
                        try:
                            line = input()
                            if line.strip() == "END":
                                break
                            lines.append(line)
                        except EOFError:
                            break
                    content = "\n".join(lines)
                    if content.strip():
                        save_template(content)
                        print(f"[OK] 模板已保存 ({len(content)} 字符)")
                    else:
                        print("[!] 模板为空，未保存")
                elif sub == "reset":
                    reset_template()
                    print("[OK] 已重置为默认模板")
                else:
                    print("用法: /prompt show|set|reset")

            elif cmd == "/kb":
                sub = parts[1].lower() if len(parts) > 1 else ""
                if sub == "list":
                    kbs = list_knowledge_bases()
                    for name, info in kbs.items():
                        print(f"  {name}: {info.get('description', '')} [{info.get('doc_count', 0)} 文档]")
                elif sub == "create" and len(parts) > 2:
                    ok, msg = create_knowledge_base(parts[2])
                    print(f"[{'OK' if ok else '!'}] {msg}")
                elif sub == "use" and len(parts) > 2:
                    cfg = load_config()
                    if "kb" not in cfg:
                        cfg["kb"] = {}
                    cfg["kb"]["active_kb"] = parts[2]
                    save_config(cfg)
                    print(f"[OK] 已切换到知识库 '{parts[2]}'")
                elif sub == "delete" and len(parts) > 2:
                    ok, msg = delete_knowledge_base(parts[2])
                    print(f"[{'OK' if ok else '!'}] {msg}")
                else:
                    print("用法: /kb list|create <name>|use <name>|delete <name>")

            elif cmd == "/model":
                sub = parts[1].lower() if len(parts) > 1 else ""
                if sub == "list":
                    models = list_downloaded_models()
                    if not models:
                        print("未下载任何嵌入模型")
                    else:
                        print(f"已下载模型 ({len(models)}):")
                        for m in models:
                            print(f"  {m['model_id']}: {m['path']}")
                elif sub == "use" and len(parts) > 2:
                    cfg = load_config()
                    cfg["embedding"]["model_path"] = parts[2]
                    save_config(cfg)
                    print(f"[OK] 已切换到模型: {parts[2]}")
                else:
                    print("用法: /model list|use <model_id>")

            elif cmd == "/config":
                sub = parts[1].lower() if len(parts) > 1 else ""
                if sub == "show":
                    cfg = load_config()
                    print(json.dumps(cfg, ensure_ascii=False, indent=2))
                elif sub == "set" and len(parts) > 3:
                    try:
                        # 支持点号路径: retrieval.k=5
                        key_path = parts[2].split(".")
                        value = parts[3]
                        # 尝试转换类型
                        try:
                            value = int(value)
                        except ValueError:
                            try:
                                value = float(value)
                            except ValueError:
                                if value.lower() in ("true", "false"):
                                    value = value.lower() == "true"
                        cfg = load_config()
                        target = cfg
                        for k in key_path[:-1]:
                            if k not in target:
                                target[k] = {}
                            target = target[k]
                        target[key_path[-1]] = value
                        save_config(cfg)
                        print(f"[OK] 已设置 {parts[2]} = {value}")
                    except Exception as e:
                        print(f"[!] 设置失败: {e}")
                else:
                    print("用法: /config show|set <key> <value>")

            elif cmd == "/reset":
                reset_config()
                reset_template()
                print("[OK] 所有配置已重置为默认值")

            elif cmd == "/import" and len(parts) > 1:
                filepath = parts[1]
                if not os.path.exists(filepath):
                    print(f"[!] 文件不存在: {filepath}")
                    continue
                print(f"导入 {filepath} 到知识库 '{active_kb}'...")
                try:
                    if embeddings is None:
                        embeddings = get_embeddings()
                    result = import_documents_to_kb(filepath, active_kb, embeddings)
                    print(f"[{'OK' if result['success'] else '!'}] {result['message']}")
                    print(f"  切分块数: {result['chunks_count']}")
                except Exception as e:
                    print(f"[!] 导入失败: {e}")

            elif cmd == "/verify-llm":
                ok, msg = verify_llm_connection()
                print(f"[{'OK' if ok else '!'}] {msg}")

            else:
                print(f"未知命令: {cmd}。输入 /help 查看可用命令")
        else:
            # 问答模式
            if embeddings is None:
                print("[!] 嵌入模型未加载，请先通过 /model 配置")
                continue

            try:
                print("  思考中...")
                result = answer_question(user_input, kb_name=active_kb,
                                         embeddings=embeddings, llm_instance=llm)
                print(f"\n{result['answer']}")
                if result["source_docs"]:
                    print(f"\n--- 引用片段 ({len(result['source_docs'])} 个) ---")
                    for i, doc in enumerate(result["source_docs"]):
                        content = doc.page_content[:120] if hasattr(doc, "page_content") else str(doc)[:120]
                        print(f"  [{i + 1}] {content}...")
            except Exception as e:
                print(f"[!] 错误: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG 交互式 CLI")
    parser.add_argument("--kb", type=str, help="初始知识库")
    parser.add_argument("--model", type=str, help="初始嵌入模型路径/ID")
    parser.add_argument("--non-interactive", type=str, help="非交互模式：直接回答问题")
    parser.add_argument("--json", action="store_true", help="非交互模式输出 JSON")

    args = parser.parse_args()

    if args.kb:
        cfg = load_config()
        cfg["kb"]["active_kb"] = args.kb
        save_config(cfg)

    if args.model:
        cfg = load_config()
        cfg["embedding"]["model_path"] = args.model
        save_config(cfg)

    if args.non_interactive:
        # 非交互模式：单次问答，供智能体调用
        try:
            embeddings = get_embeddings()
            llm = get_llm()
            result = answer_question(args.non_interactive, embeddings=embeddings, llm_instance=llm)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
            else:
                print(result["answer"])
        except Exception as e:
            if args.json:
                print(json.dumps({"error": str(e)}, ensure_ascii=False))
            else:
                print(f"[!] 错误: {e}")
        sys.exit(0)

    run_interactive()
