"""
main.py — CLI 入口

功能:
  1. 多后端切换: LM Studio / Ollama / 自定义 API / 直接加载 GGUF
  2. 模型罗列: --list-models 显示所有可用模型
  3. 智能体: RAG + 文件 + 网络 + Python 执行，多工具协作

用法:
  python main.py                                       # 默认 (LM Studio)
  python main.py --list-models                         # 罗列所有模型
  python main.py --backend ollama                      # Ollama 后端
  python main.py --backend lm-studio                   # LM Studio 后端
  python main.py --backend custom --base-url http://x:8000/v1 --model xxx
  python main.py --direct                              # 直接加载 GGUF
  python main.py --direct --model 2                    # 选择列表中的第2个模型
  python main.py --query "你的问题"                     # 单次问答
  python main.py --no-rag                              # 不带 RAG 工具
"""

import os

# ======================================================================
# 【配置区】改这里，别的地方不用动
# ======================================================================
# 后端: "lm-studio" / "ollama" / "custom" / "direct" / "list-models"
CFG_BACKEND = "lm-studio"

# direct 模式：模型名称或序号，留空则运行时可选
CFG_MODEL = ""

# custom 模式
CFG_BASE_URL = ""
CFG_API_KEY = "not-needed"
CFG_CUSTOM_MODEL = ""

# 单次问答：留空则进入交互模式
CFG_QUERY = ""

# 开关
CFG_VERBOSE = False
CFG_GPU_LAYERS = -1          # direct模式: -1=自动, 0=纯CPU
CFG_AUTO_INSTALL_GPU = True  # 自动装 GPU 版

# 技能路径（自包含，只扫这里）
# 把你想要智能体用的技能复制到这个目录下
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_SCRIPT_DIR)
CFG_SKILL_DIRS = [
    os.path.join(_PARENT_DIR, "skills"),
]
# ======================================================================

import argparse
import json
import sys

if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from orchestrator.agent_config import AgentConfig
from orchestrator.agent_loop import Agent
from orchestrator.llm_client import LLMClient
from orchestrator.tools.file_tool import ReadFileTool, WriteFileTool, ListDirTool
from orchestrator.tools.web_tool import WebFetchTool, WebSearchTool, PythonExecuteTool
from orchestrator.tools.skill_loader import LoadSkillTool

CAPABILITY_TEXT = """
  链驱动智能体 — 核心工作方式：执行技能链（Pipeline）。

  可用工具:
    load_skill       → 加载任意技能（读 SKILL.md，自动理解用法）
    read_file        → 读取本地文件
    write_file       → 写入本地文件
    list_directory   → 列出目录内容
    web_fetch        → 获取网页内容
    web_search       → 搜索网络
    python_execute   → 执行 Python 代码

  技能在配置的路径下，用 SKILL.md 描述能力。
  链编排：在 Web UI 的 Pipeline Tab 中拖拽组合技能。
"""


# ======================================================================
# CLI 参数
# ======================================================================
def build_parser():
    p = argparse.ArgumentParser(
        description="Orchestrator - 动态技能加载智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 运行模式
    p.add_argument("--query", "-q", default="", help="单次问答（不进入交互模式）")
    p.add_argument("--check", action="store_true", help="仅检测后端连接，不进入对话")
    p.add_argument("--list-models", action="store_true", help="罗列所有可用模型")
    p.add_argument("--verbose", default="", choices=["True", "False", ""],
                   help="是否打印思考过程")
    p.add_argument("--web", action="store_true", help="启动 Web UI")
    p.add_argument("--port", type=str, default="8765", help="Web UI 端口（默认 8765，设为 auto 自动分配空闲端口）")
    p.add_argument("--pidfile", default="", help="PID 文件路径（setup.bat 用）")
    # 批处理 / 管道模式
    p.add_argument("--batch", nargs=2, metavar=("INPUT", "OUTPUT"), default=None,
                   help="批处理模式: --batch input.json output.json")
    p.add_argument("--jsonl", action="store_true",
                   help="JSONL 管道模式: stdin 逐行读，stdout 逐行输出")

    # 后端选择
    backend = p.add_argument_group("后端选择（四选一，默认 lm-studio）")
    backend.add_argument("--backend", default="lm-studio",
                         choices=["lm-studio", "ollama", "custom", "direct"],
                         help="LLM 后端")
    backend.add_argument("--direct", action="store_true",
                         help="等同 --backend direct")

    # API 后端参数
    api = p.add_argument_group("API 后端参数 (lm-studio / ollama / custom)")
    api.add_argument("--base-url", default="",
                     help="自定义 API 地址 (custom 模式下必填)")
    api.add_argument("--api-key", default="", help="API Key")

    # 直接加载参数
    direct = p.add_argument_group("直接加载参数 (direct)")
    direct.add_argument("--model", "-m", default="",
                        help="模型名称或列表中序号 (如 '2' 或 'qwen3.6-35b-a3b-Q4_K_M')")
    direct.add_argument("--gpu-layers", type=int, default=-1,
                        help="GPU 卸载层数 (-1=自动, 0=CPU)")

    # 其他
    p.add_argument("--config", "-c", default="", help="配置文件路径")
    p.add_argument("--no-rag", action="store_true", help="不加载 RAG 工具")
    p.add_argument("--no-web", action="store_true", help="不加载网络工具")

    return p


# ======================================================================
# 模型罗列
# ======================================================================
def list_models():
    """扫描并打印所有可用模型"""
    from orchestrator.model_manager import get_model_manager

    mgr = get_model_manager()
    mgr.discover(force_rescan=True)
    all_models = mgr.list()

    if not all_models:
        print("未发现任何本地模型。")
        print("  GGUF 模型请放在: ~/.lmstudio/models/ 或 ~/models/")
        print("  HF 模型会自动从 ~/.cache/huggingface/hub/ 识别")
        return

    print(f"\n发现 {len(all_models)} 个模型:")
    print()

    # 按类型分组
    from orchestrator.model_manager import ModelType
    for mtype in [ModelType.GGUF, ModelType.SENTENCE_TRANSFORMER,
                  ModelType.CAUSAL_LM, ModelType.RERANKER]:
        models = [m for m in all_models if m.model_type == mtype]
        if not models:
            continue
        print(f"  [{mtype.value}]")
        for i, m in enumerate(models, 1):
            loaded = " [已加载]" if mgr.is_loaded(m.name) else ""
            gpu_tag = f" ~~> {m.vram_estimate_gb:.0f}GB VRAM" if m.vram_estimate_gb > 0 else ""
            print(f"    {i}. {m.name}  ({m.size_gb:.1f}GB, {m.source}){loaded}{gpu_tag}")
            print(f"       路径: {m.path}")
        print()

    print("用法示例:")
    print("  python main.py --direct --model 1")
    print("  python main.py --direct --model qwen3.6-35b-a3b-Q4_K_M")
    print()


# ======================================================================
# LLM 工厂
# ======================================================================
def make_llm(config, args):
    """根据参数创建 LLM 客户端"""

    # === 1. direct: 直接加载 GGUF ===
    if args.backend == "direct" or args.direct:
        return _make_direct_llm(config, args)

    # === 2. API 后端 ===
    base_url = args.base_url
    model_name = args.model

    if args.backend == "lm-studio":
        base_url = base_url or "http://localhost:1234/v1"
        model_name = model_name or "qwen/qwen3.6-35b-a3b"
    elif args.backend == "ollama":
        base_url = base_url or "http://localhost:11434/v1"
        model_name = model_name or ""
    elif args.backend == "custom":
        if not base_url:
            print("❌ custom 模式需要 --base-url")
            print("   例: --backend custom --base-url http://localhost:8000/v1 --model xxx")
            sys.exit(1)
        if not model_name:
            print("⚠️  custom 模式建议指定 --model")
    else:
        print(f"❌ 未知后端: {args.backend}")
        sys.exit(1)

    # 写入配置
    config.data["llm"]["base_url"] = base_url
    config.data["llm"]["api_key"] = args.api_key or "not-needed"
    if model_name:
        config.data["llm"]["model_name"] = model_name

    llm = LLMClient(config)
    ok, msg = llm.check_connection()
    if not ok:
        print(f"❌ [{args.backend}] 连接失败: {msg}")
        print(f"   地址: {base_url}")
        print(f"   模型: {model_name}")
        if args.backend == "lm-studio":
            print(f"   请启动 LM Studio 并加载模型")
        elif args.backend == "ollama":
            print(f"   请运行: ollama serve")
        sys.exit(1)
    print(f"  ✅ [{args.backend}] {msg}")
    return llm


def _make_direct_llm(config, args):
    """通过 ModelManager 直接加载 GGUF"""

    # 自动检测+安装 GPU 版 llama-cpp-python
    if CFG_AUTO_INSTALL_GPU:
        from orchestrator.direct_llm_client import ensure_gpu_llama
        ensure_gpu_llama()

    from orchestrator.model_manager import get_model_manager

    mgr = get_model_manager()
    mgr.discover()
    gguf_models = mgr.list(type_filter="gguf", llm_only=True)

    if not gguf_models:
        print("❌ 未找到 GGUF 模型文件")
        print("   请先下载 GGUF 模型放在 ~/.lmstudio/models/ 或 ~/models/")
        print("   或使用 --backend lm-studio 走 LM Studio API")
        sys.exit(1)

    # 选择模型
    model_name = args.model
    if not model_name:
        # 没指定 → 显示列表让用户选
        print("\n可用的 GGUF 模型:")
        for i, m in enumerate(gguf_models, 1):
            print(f"  {i}. {m.name}  ({m.size_gb:.1f}GB)")
        print()
        try:
            choice = input("选择模型 (1-{}): ".format(len(gguf_models))).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            sys.exit(1)

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(gguf_models):
                model_name = gguf_models[idx].name
            else:
                print(f"❌ 序号超出范围 (1-{len(gguf_models)})")
                sys.exit(1)
        elif choice:
            model_name = choice  # 直接输入名称
        else:
            model_name = gguf_models[0].name

    # 检查名称是否存在，不存在则尝试序号匹配
    matched = mgr.get(model_name)
    if matched is None:
        # 尝试序号
        if model_name.isdigit():
            idx = int(model_name) - 1
            if 0 <= idx < len(gguf_models):
                matched = gguf_models[idx]
                model_name = matched.name

    if matched is None:
        print(f"❌ 未找到模型: {model_name}")
        print(f"   可用: {', '.join(m.name for m in gguf_models)}")
        sys.exit(1)

    print(f"  📦 加载: {model_name} ({matched.size_gb:.1f}GB)")

    # 通过 ModelManager 加载
    device = "gpu" if args.gpu_layers != 0 else "cpu"
    n_gpu_layers = args.gpu_layers if args.gpu_layers >= 0 else -1

    try:
        instance = mgr.load(
            model_name,
            device=device,
            n_gpu_layers=n_gpu_layers,
        )
    except ImportError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        sys.exit(1)

    device_info = mgr._device_map.get(model_name, "?")
    print(f"  ✅ [direct] 加载成功 (设备: {device_info})")

    # 包装为 LLMClient 兼容接口
    class _DirectWrapper(LLMClient):
        def __init__(self, inst, name, gpu_info):
            self._model = inst
            self._model_name = name
            self._gpu_info = gpu_info
            self.base_url = "direct://local"
            self.model = name

        def check_connection(self):
            return True, f"GGUF: {self._model_name} ({self._gpu_info})"

        def chat(self, messages, **kwargs):
            return self._model.create_chat_completion(
                messages=messages,
                temperature=kwargs.get("temperature", 0.3),
                max_tokens=kwargs.get("max_tokens", 4096),
            )["choices"][0]["message"]["content"]

    return _DirectWrapper(instance, model_name, device_info)


# ======================================================================
# 创建 Agent
# ======================================================================
def create_agent(config, llm):
    """创建智能体"""
    agent = Agent(config)
    agent.llm = llm

    tools = [
        LoadSkillTool(extra_dirs=CFG_SKILL_DIRS),
        ReadFileTool(), WriteFileTool(), ListDirTool(),
        WebFetchTool(), WebSearchTool(), PythonExecuteTool(),
    ]

    agent.register_tools(tools)
    return agent


# ======================================================================
# 交互模式
# ======================================================================
def interactive(agent, config, backend_name):
    print()
    print("=" * 56)
    print("  Local Agent — 多工具智能体")
    print(f"  后端: {backend_name}")
    print(f"  工具: {len(agent.tools.list())} 个")
    print(f"  命令: /exit  /reset  /tools  /help")
    print("=" * 56)

    while True:
        try:
            text = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见")
            break
        if not text:
            continue

        cmd = text.lower()
        if cmd in ("/exit", "/quit", "exit", "quit"):
            break
        if cmd == "/reset":
            agent.reset()
            print("已重置")
            continue
        if cmd == "/tools":
            for t in agent.tools.list():
                print(f"  - {t.name}: {t.description}")
            continue
        if cmd == "/help":
            print("/exit 退出  /reset 重置")
            print("/tools 查看工具  /help 帮助")
            continue

        try:
            answer = agent.run(text)
            print(f"AI: {answer}")
        except Exception as e:
            print(f"错误: {e}")


# ======================================================================
# Pipeline 扁平化与执行（批处理/管道模式用）
# ======================================================================
def _flatten_pipeline(nodes, depth=0):
    """递归展开 Pipeline 树为扁平步骤列表"""
    result = []
    for i, node in enumerate(nodes):
        mode = node.get("mode", "seq")
        name = node.get("name", "")
        display = node.get("display", name or "(unnamed)")
        children = node.get("children", [])
        if mode == "par":
            names = [c.get("display", c.get("name","(unnamed)")) for c in children]
            result.append({"mode":"par","display":display,"children_names":names})
            for child in children:
                child_name = child.get("name","")
                if child_name:
                    result.append({"mode":"seq","display":child.get("display",child_name),"name":child_name})
        elif mode == "loop":
            times = node.get("loop_times", 3) or node.get("times", 3)
            result.append({"mode":"loop","display":display,"times":times})
            for t in range(times):
                sub = _flatten_pipeline(children, depth+1)
                for s in sub:
                    s["_loop"] = t + 1
                result.extend(sub)
        else:
            result.append({"mode":"seq","display":display,"name":name})
    return result

def _execute_pipeline_batch(nodes, agent=None):
    """执行 Pipeline 并返回结果文本（批处理/管道模式）"""
    flat = _flatten_pipeline(nodes)
    if not flat:
        return "（空 Pipeline）"
    lines = []
    for i, step in enumerate(flat):
        mode = step.get("mode","seq")
        display = step.get("display","")
        loop_info = f" [第{step['_loop']}轮]" if step.get("_loop") else ""
        if mode == "par":
            names = step.get("children_names",[])
            lines.append(f"  [{i+1}] ⬡ 并行组: {' | '.join(names)}")
        elif mode == "loop":
            lines.append(f"  [{i+1}] ↻ 循环组: {display} ({step['times']}次)")
        else:
            name = step.get("name","")
            lines.append(f"  [{i+1}] → {display}{loop_info}")
            if agent and name:
                try:
                    result = agent.run(f"执行技能: {name}")
                    lines.append(f"      结果: {result[:200]}")
                except Exception as e:
                    lines.append(f"      错误: {e}")
    return "\n".join(lines)


def run_batch(input_path, output_path, agent=None):
    """JSON 批处理模式"""
    import time
    start = time.time()
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        _write_json_output({"success": False, "error": f"读取失败: {e}"}, output_path)
        return
    nodes = data
    if isinstance(data, dict):
        nodes = data.get("nodes", data.get("tree", []))
    if not nodes or not isinstance(nodes, list):
        nodes = data if isinstance(data, list) else []
    try:
        output = _execute_pipeline_batch(nodes, agent)
        elapsed = int((time.time() - start) * 1000)
        result = {"success": True, "output": output, "steps": len(_flatten_pipeline(nodes)), "latency_ms": elapsed}
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        result = {"success": False, "error": str(e), "latency_ms": elapsed}
    _write_json_output(result, output_path)


def _write_json_output(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [batch] 结果已写入: {path}")


def run_jsonl(agent=None):
    """JSONL 管道模式"""
    import sys, time
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        start = time.time()
        try:
            data = json.loads(line)
            query = data.get("query", data.get("message", ""))
            nodes = data.get("nodes", data.get("tree", []))
            if nodes:
                output = _execute_pipeline_batch(nodes, agent)
            elif query:
                output = agent.run(query) if agent else f"[jsonl] {query[:100]}"
            else:
                output = "（空输入）"
            elapsed = int((time.time() - start) * 1000)
            sys.stdout.write(json.dumps({"success": True, "output": output, "latency_ms": elapsed}, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            sys.stdout.write(json.dumps({"success": False, "error": str(e), "latency_ms": elapsed}, ensure_ascii=False) + "\n")
            sys.stdout.flush()


# ======================================================================
# 入口
# ======================================================================
def main():
    args = build_parser().parse_args()

    # 【配置区】优先使用代码里的配置
    if CFG_BACKEND == "list-models":
        list_models()
        return

    # 用代码配置覆盖命令行参数
    if args.backend == "lm-studio" and CFG_BACKEND != "lm-studio":
        args.backend = CFG_BACKEND
    if CFG_MODEL:
        args.model = CFG_MODEL
    if CFG_BASE_URL:
        args.base_url = CFG_BASE_URL
    if CFG_API_KEY:
        args.api_key = CFG_API_KEY
    if CFG_CUSTOM_MODEL and not args.model:
        args.model = CFG_CUSTOM_MODEL
    if CFG_QUERY:
        args.query = CFG_QUERY
    if CFG_VERBOSE:
        args.verbose = "True"
    if CFG_GPU_LAYERS != -1:
        args.gpu_layers = CFG_GPU_LAYERS

    if args.direct:
        args.backend = "direct"

    # 加载配置
    if args.config:
        cfg_path = args.config
    else:
        cwd_cfg = os.path.join(os.getcwd(), "agent_config.json")
        script_cfg = os.path.join(_SCRIPT_DIR, "agent_config.json")
        cfg_path = cwd_cfg if os.path.exists(cwd_cfg) else script_cfg

    config = AgentConfig.load(cfg_path)

    if args.verbose == "True":
        config.data["agent"]["verbose"] = True
    elif args.verbose == "False":
        config.data["agent"]["verbose"] = False

    # 批处理模式 (无需 LLM)
    if args.batch:
        input_path, output_path = args.batch
        run_batch(input_path, output_path, agent=None)
        return

    # JSONL 管道模式 (无需 LLM)
    if args.jsonl:
        run_jsonl(agent=None)
        return

    # 创建 LLM
    llm = make_llm(config, args)
    if args.check:
        return

    # 显示工具列表
    print(CAPABILITY_TEXT)

    # 创建智能体
    from orchestrator.tools.skill_loader import LoadSkillTool
    agent = create_agent(config, llm)

    # Web UI 模式
    if args.web:
        import socket
        port = args.port
        if port == "auto":
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", 0))
            port = s.getsockname()[1]
            s.close()
        else:
            port = int(port)
        if args.pidfile:
            with open(args.pidfile, "w") as f:
                f.write(f"{os.getpid()}\n{port}")
                portfile = args.pidfile.replace(".pid", ".port")
                with open(portfile, "w") as pf:
                    pf.write(str(port))
        from orchestrator.web_ui import start_web_ui
        start_web_ui(agent=agent, config=config, port=port)
        return

    if args.query:
        print(f"Q: {args.query}")
        try:
            print(f"A: {agent.run(args.query)}")
        except Exception as e:
            print(f"错误: {e}")
    else:
        interactive(agent, config, args.backend)


if __name__ == "__main__":
    main()
