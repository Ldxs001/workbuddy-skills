"""
rag-assistant 入口
独立智能体，自包含 local-rag-builder 完整技能
"""
import os
import sys
import json
import shutil
import time
import logging
import argparse

# 禁用 pyc 缓存（防止旧缓存导致加载旧代码）
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# 自身 engine/ 目录（自包含技能引擎）
ENGINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_assistant", "engine")
if ENGINE_PATH not in sys.path:
    sys.path.insert(0, ENGINE_PATH)

from rag_assistant import __version__ as rag_version
from rag_assistant.agent import Agent
from rag_assistant.web_ui import start_web_ui

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rag-assistant")


def load_config() -> dict:
    """从引擎的正确位置加载配置"""
    try:
        from config import load_config as engine_load
        return engine_load()
    except ImportError:
        pass
    # fallback: 顶层 config.json（兼容旧版）
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


def _execute_structured(agent, query_obj: dict) -> dict:
    """执行一次结构化查询，返回协议标准输出"""
    q = query_obj.get("query", "")
    if not q:
        return {"status": "error", "answer": "", "error": "query 为空"}
    
    kb = query_obj.get("kb")
    mode = query_obj.get("mode", "auto")
    top_k = query_obj.get("top_k", 5)
    score_threshold = query_obj.get("score_threshold", 0.0)
    return_sources = query_obj.get("return_sources", False)
    session_id = query_obj.get("session_id", "batch")

    t0 = time.time()

    # 根据 mode 决定走 RAG 还是搜索
    if mode == "search_only":
        context = agent.search.search(q, max_results=top_k)
        snippets = "\n".join(
            f"{r.get('title','')}: {r.get('snippet','')}" for r in context.get("results", [])[:top_k]
        )
        answer = agent.llm.chat([
            {"role": "system", "content": "基于以下搜索结果回答用户问题。" if snippets else "搜索无结果，礼貌告知用户。"},
            {"role": "user", "content": q},
        ])
        latency = int((time.time() - t0) * 1000)
        return {
            "status": "success", "answer": answer.get("text", ""),
            "has_context": bool(snippets), "search_used": True,
            "latency_ms": latency,
        }

    # RAG 查询
    result = agent.rag.query(q, kb_name=kb, k=top_k, score_threshold=score_threshold)
    has_context = result.get("has_context", False)
    actual_kb = result.get("kb", kb or "")

    # 无上下文且允许搜索 → 联网搜索回退
    search_used = False
    if not has_context and mode != "rag_only" and hasattr(agent, 'search') and agent.search.enabled:
        ctx = agent.search.search(q, max_results=top_k)
        snippets = "\n".join(
            f"{r.get('title','')}: {r.get('snippet','')}" for r in ctx.get("results", [])[:top_k]
        )
        if snippets:
            context_text = snippets
            search_used = True
        else:
            context_text = result.get("context", "")
    else:
        context_text = result.get("context", "")

    # LLM 生成回答
    if context_text:
        sys_msg = f"基于以下资料回答用户问题。\n资料（来自 {actual_kb}）：\n{context_text}"
    else:
        sys_msg = f"知识库（{actual_kb}）中没有找到相关信息。请礼貌告知用户。"
    answer = agent.llm.chat([
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": q},
    ])

    latency = int((time.time() - t0) * 1000)
    resp = {
        "status": "success",
        "answer": answer.get("text", ""),
        "kb": actual_kb,
        "route_method": "direct",
        "has_context": has_context,
        "search_used": search_used,
        "latency_ms": latency,
        "error": "",
    }
    if return_sources and result.get("docs"):
        resp["sources"] = [
            {
                "kb": d.get("_kb", actual_kb) if isinstance(d, dict) else getattr(d, "metadata", {}).get("_kb", actual_kb),
                "document": d.get("metadata", {}).get("source", "") if isinstance(d, dict) else getattr(d, "metadata", {}).get("source", ""),
                "relevance": d.get("metadata", {}).get("score", 0.0) if isinstance(d, dict) else getattr(d, "metadata", {}).get("score", 0.0),
                "chunk": d.get("content", "")[:200] if isinstance(d, dict) else (getattr(d, "page_content", "")[:200]),
            }
            for d in (result.get("docs", []) or [])
        ][:top_k]
    return resp


def cmd_batch(args, agent):
    """批量处理模式：读 JSON，出 JSON"""
    import json
    input_path = args.input or (sys.stdin.read() if not sys.stdin.isatty() else None)
    if not input_path:
        print('{"status":"error","error":"需要 --input 或管道输入"}')
        sys.exit(2)

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            query_obj = json.load(f)
    else:
        query_obj = json.loads(input_path)

    result = _execute_structured(agent, query_obj)
    output = args.output
    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    else:
        print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["status"] == "success" else 1)


def cmd_jsonl(args, agent):
    """管道 JSONL 模式：逐行读入，逐行输出"""
    import json
    exit_code = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            query_obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "error", "error": f"JSON 解析失败: {e}"}, ensure_ascii=False))
            exit_code = 1
            continue
        result = _execute_structured(agent, query_obj)
        print(json.dumps(result, ensure_ascii=False))
        if result["status"] != "success":
            exit_code = 1
    sys.exit(exit_code)


def main():
    parser = argparse.ArgumentParser(description="RAG 智能助手")
    parser.add_argument("--port", type=int, default=8765, help="Web 界面端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")
    parser.add_argument("--data-dir", type=str, default=None, help="数据目录")
    parser.add_argument("--config", type=str, default=None, help="配置文件路径")
    parser.add_argument("--no-web", action="store_true", help="不启动 Web 界面")
    parser.add_argument("--pidfile", type=str, default=None, help="PID 文件路径")
    parser.add_argument("--api-port", type=int, default=None, help="外部 API 端口（默认不启动，指定端口即启动，如 8767）")

    # 批量/管道模式
    parser.add_argument("--batch", action="store_true", help="批量处理模式（需配合 --input/--query）")
    parser.add_argument("--input", type=str, default=None, help="JSON 输入文件路径")
    parser.add_argument("--output", type=str, default=None, help="JSON 输出文件路径")
    parser.add_argument("--jsonl", action="store_true", help="管道 JSONL 模式（从 stdin 逐行读）")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("migrate", help="从 local-rag-builder 迁移现有数据")

    args = parser.parse_args()

    # 写 PID 文件（供 bat 杀旧进程用）
    if args.pidfile:
        with open(args.pidfile, "w") as f:
            f.write(str(os.getpid()))

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

    # 探测所有 KB 索引完整性（阻塞，跑完才启动服务器）
    print("  检查知识库索引...")
    kb_ok = kb_bad = 0
    try:
        from rag_core import get_embeddings, retrieve_documents
        from knowledge_base_manager import _load_index, _save_index
        emb = get_embeddings()
        kb_dir = os.path.join(data_dir, "kb")
        kb_index = _load_index()
        # 对齐索引：删除目录已不存在的条目
        stale = [name for name, info in kb_index.items()
                 if not os.path.isdir(info.get("path", ""))]
        for name in stale:
            del kb_index[name]
        if stale:
            _save_index(kb_index)
            print(f"  清理索引: 移除 {len(stale)} 个已删除的 KB 条目")
        if os.path.isdir(kb_dir):
            for entry in sorted(os.listdir(kb_dir)):
                kp = os.path.join(kb_dir, entry)
                if not os.path.isdir(kp) or entry.startswith(".") or entry.startswith("_"):
                    continue
                if not os.path.isfile(os.path.join(kp, "chroma.sqlite3")):
                    continue
                # 跳过空 KB（如 default 兜底库），不报 HNSW 损坏噪点
                entry_info = kb_index.get(entry, {})
                if entry_info.get("doc_count", 0) == 0:
                    kb_ok += 1
                    continue
                try:
                    # 只验证 KB 可访问，不触发懒重建（启动扫描不做全量 embedding）
                    from chroma_adapter import Chroma
                    vs = Chroma(persist_directory=kp, embedding_function=emb)
                    _cnt = vs._hnsw.count()
                    kb_ok += 1
                except Exception:
                    logger.warning(f"  知识库 [{entry}] 不可访问")
                    kb_bad += 1
    except Exception:
        pass
    if kb_ok + kb_bad > 0:
        detail = f"  ✅ {kb_ok} 正常" if kb_ok else ""
        if kb_bad:
            detail += f"  ❌ {kb_bad} 损坏(已修复)"
        print(f"  知识库: {kb_ok + kb_bad} 个 ({kb_ok} 正常{' / ' + str(kb_bad) + ' 已修复' if kb_bad else ''})")
    else:
        print("  知识库: 无")

    if not agent.rag.ready:
        logger.warning("RAG 模块未就绪 - 请确保 data/ 目录下有知识库和模型")
    if args.command != "migrate":
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

    # ── 批量模式：--batch --input query.json --output result.json ──
    if args.batch:
        cmd_batch(args, agent)
        return

    # ── 管道 JSONL 模式 ──
    if args.jsonl:
        cmd_jsonl(args, agent)
        return

    # ── 普通模式 ──
    print()
    print("=" * 50)
    print(f"  RAG 智能助手 v{rag_version}")
    print("=" * 50)
    print(f"  RAG 模块: {'✅ 就绪' if agent.rag.ready else '❌ 未加载'}")
    print(f"  LLM 后端: {agent.llm.backend}")
    print(f"  LLM 模型: {agent.llm.model or '默认'}")
    print(f"  数据目录: {data_dir}")
    print()

    if not args.no_web:
        # 外部 API（可选）
        if args.api_port:
            from rag_assistant.external_api import start_external_api
            import threading
            api_thread = threading.Thread(
                target=start_external_api,
                args=(agent, args.api_port),
                daemon=True,
            )
            api_thread.start()
            logger.info(f"外部 API 服务已启动 (port {args.api_port})")

        start_web_ui(agent, port=args.port, host=args.host)
    else:
        # CLI 交互模式
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
