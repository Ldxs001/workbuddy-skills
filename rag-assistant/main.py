"""
rag-assistant 入口
独立智能体，自包含 local-rag-builder 完整技能
"""
import os
import sys
import json
import shutil
import logging
import argparse

# 禁用 pyc 缓存（防止旧缓存导致加载旧代码）
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# 自身 scripts/ 目录（自包含技能副本）
SCRIPTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
if SCRIPTS_PATH not in sys.path:
    sys.path.insert(0, SCRIPTS_PATH)

from rag_assistant.agent import Agent
from rag_assistant.web_ui import start_web_ui

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rag-assistant")


def load_config() -> dict:
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def cmd_migrate(args):
    """从 local-rag-builder 技能迁移现有数据到本智能体"""
    skill_data = os.path.expanduser("~/.workbuddy/skills/.standardization/local-rag-builder/data")
    target = os.path.join(os.path.dirname(__file__), "data")

    if not os.path.exists(skill_data):
        print(f"❌ 源数据目录不存在: {skill_data}")
        return

    print("=" * 50)
    print("  迁移现有数据到 rag-assistant")
    print("=" * 50)
    print(f"  源: {skill_data}")
    print(f"  目标: {target}")

    # 知识库（复制目录内容，目标已存在时合并）
    src_kb = os.path.join(skill_data, "kb")
    dst_kb = os.path.join(target, "kb")
    if os.path.exists(src_kb):
        kb_items = [n for n in os.listdir(src_kb) if n != '__pycache__']
        print(f"\n📁 知识库 ({len(kb_items)} 项)")
        for item in kb_items:
            src_item = os.path.join(src_kb, item)
            dst_item = os.path.join(dst_kb, item)
            if os.path.exists(dst_item):
                print(f"  ⏭️  {item} (已存在)")
            else:
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item)
                else:
                    shutil.copy2(src_item, dst_item)
                print(f"  ✅ {item}")

    # 模型（含索引文件）
    src_models = os.path.join(skill_data, "models")
    dst_models = os.path.join(target, "models")
    if os.path.exists(src_models):
        model_items = [n for n in os.listdir(src_models) if n != '__pycache__']
        print(f"\n📁 模型 ({len(model_items)} 项)")
        for item in model_items:
            src_item = os.path.join(src_models, item)
            dst_item = os.path.join(dst_models, item)
            if os.path.exists(dst_item):
                print(f"  ⏭️  {item} (已存在)")
            else:
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item)
                else:
                    shutil.copy2(src_item, dst_item)
                print(f"  ✅ {item}")

    # 配置（合并到目标）
    for fname in ["config.json", "kb_signatures.json", "kb_index.json"]:
        src = os.path.join(skill_data, fname)
        dst = os.path.join(target, fname)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"  ✅ {fname}")
        elif os.path.exists(src):
            print(f"  ⏭️  {fname} (已存在)")

    # Prompt
    src_prompts = os.path.join(skill_data, "prompts")
    dst_prompts = os.path.join(target, "prompts")
    if os.path.exists(src_prompts) and not os.path.exists(dst_prompts):
        shutil.copytree(src_prompts, dst_prompts)
        print(f"  ✅ prompts/")

    print(f"\n迁移完成。数据在: {target}")


def main():
    parser = argparse.ArgumentParser(description="RAG 智能助手")
    parser.add_argument("--port", type=int, default=8765, help="Web 界面端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")
    parser.add_argument("--data-dir", type=str, default=None, help="数据目录")
    parser.add_argument("--config", type=str, default=None, help="配置文件路径")
    parser.add_argument("--no-web", action="store_true", help="不启动 Web 界面")

    subparsers = parser.add_subparsers(dest="command")
    migrate_parser = subparsers.add_parser("migrate", help="从 local-rag-builder 迁移现有数据")

    args = parser.parse_args()

    if args.command == "migrate":
        cmd_migrate(args)
        return

    config = load_config()
    if args.data_dir:
        config["data_dir"] = args.data_dir
    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            config.update(json.load(f))

    data_dir = config.get("data_dir", os.path.join(os.path.dirname(__file__), "data"))
    config["data_dir"] = data_dir
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "memory"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "sessions"), exist_ok=True)

    # 初始化智能体
    logger.info("正在初始化 RAG 智能体...")
    agent = Agent(config)

    if not agent.rag.ready:
        logger.warning("RAG 模块未就绪 - 请确保 data/ 目录下有知识库和模型")
        logger.info("运行 python main.py migrate 可迁移现有数据")

    model_name = agent.llm.model or config.get("llm_model", "")
    if model_name:
        llm_ok = agent.llm.check_health()
        if llm_ok:
            logger.info(f"LLM 后端 [{agent.llm.backend}] 连接正常，模型: {model_name}")
        else:
            logger.warning(f"LLM 后端 [{agent.llm.backend}] 未响应，可通过 Web 配置后测试")
    else:
        logger.info("LLM 模型未配置，可通过 Web 配置后再测试连接")

    print()
    print("=" * 50)
    print("  RAG 智能助手 v0.1.0")
    print("=" * 50)
    print(f"  RAG 模块: {'✅ 就绪' if agent.rag.ready else '❌ 未加载'}")
    print(f"  LLM 后端: {agent.llm.backend}")
    print(f"  LLM 模型: {agent.llm.model or '默认'}")
    print(f"  数据目录: {data_dir}")
    print()

    if not args.no_web:
        start_web_ui(agent, port=args.port, host=args.host)
    else:
        # CLI 模式
        print("CLI 模式（输入 exit 退出）")
        while True:
            try:
                msg = input("\n>>> ").strip()
                if not msg:
                    continue
                if msg.lower() in ("exit", "quit", "q"):
                    break
                if msg == "/reset":
                    agent.reset_session()
                    print("[记忆已重置]")
                    continue
                if msg == "/archive":
                    agent.archive_memory()
                    print("[记忆已归档]")
                    continue

                result = agent.chat(msg)
                print()
                print(result.get("text", ""))
                if result.get("search_used"):
                    print("\n[注: 使用了联网搜索补充]")
            except KeyboardInterrupt:
                break
            except EOFError:
                break

        print("\n再见！")


if __name__ == "__main__":
    main()
