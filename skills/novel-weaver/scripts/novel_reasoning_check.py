#!/usr/bin/env python3
"""
Reasoning Check — 推理审核引擎（v1.0）
基于 Qwythos-9B-Claude-Mythos-5-1M GGUF Q4_K_M 实现推理级别内容审核。

定位：finalize-chapter 第6步（BERT 语义之后，需 GPU）
有模型 → 执行5项推理审核
无模型 → 自动跳过，不影响现有流程

推理审核项目：
  1. 因果合理性 [HARD]    — 事件是否有前文铺垫，转折是否牵强
  2. 人物行为一致性 [HARD] — 行为是否符合人格设定
  3. 情绪弧自然度 [SOFT]   — 情绪转变是否有递进，是否突兀
  4. 对话匹配度 [SOFT]     — 对话是否符合角色身份/性格/处境
  5. 论证可靠性 [SOFT]     — 角色的推理/判断是否有逻辑漏洞

依赖：
  - llama-cpp-python（pip install，Windows 需先装 g++ 编译器 + cmake）
  - Qwythos-9B GGUF Q4_K_M（首次 `from_pretrained` 自动下载 ~5.5GB）

Windows 编译器安装：
  # 1. 检查 g++
  g++ --version
  #    无输出 → 下载 winlibs 压缩包:
  #    下载: https://github.com/brechtsanders/winlibs_mingw/releases/download/
  #          16.1.0posix-14.0.0-ucrt-r3/
  #          winlibs-x86_64-posix-seh-gcc-16.1.0-mingw-w64ucrt-14.0.0-r3.zip
  #    镜像: https://sourceforge.net/projects/winlibs-mingw/
  #    解压到: ~/.workbuddy/skills/.standardization/novel-weaver/models/winlibs/
  #    将 mingw64/bin 加入 PATH
  
  # 2. 检查 cmake
  cmake --version
  #    无输出 → pip install cmake
  
  # 3. 安装 llama-cpp-python
  pip install llama-cpp-python -i https://mirrors.aliyun.com/pypi/simple/
    HF_ENDPOINT=https://hf-mirror.com python -c "
from llama_cpp import Llama
Llama.from_pretrained(repo_id='empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF', filename='Qwythos-9B-Claude-Mythos-5-1M-Q4_K_M.gguf')
"
  ModelScope 镜像:
    pip install modelscope -i https://mirrors.aliyun.com/pypi/simple/
    python -c "from modelscope import snapshot_download; snapshot_download('Qwythos-9B-Claude-Mythos-5-1M-GGUF')"
  hf-transfer 加速:
    pip install hf-transfer -i https://mirrors.aliyun.com/pypi/simple/
"""
import json, sys, re, os
from pathlib import Path

_LLM = None

# ── GGUF 配置 ──
GGUF_REPO = "empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF"
GGUF_FILE = "Qwythos-9B-Claude-Mythos-5-1M-Q4_K_M.gguf"
GGUF_CACHE = str(Path.home() / ".cache" / "huggingface" / "hub")

# ── 5项审核的维度定义 ──
DIMENSIONS = [
    {"key": "causality", "name": "因果合理性", "hard": True,
     "desc": "事件是否有前文铺垫？转折是否牵强？"},
    {"key": "character_consistency", "name": "人物行为一致性", "hard": True,
     "desc": "角色行为是否符合其人格设定？"},
    {"key": "emotion_arc", "name": "情绪弧自然度", "hard": False,
     "desc": "情绪转变是否有递进？是否突兀？"},
    {"key": "dialogue", "name": "对话匹配度", "hard": False,
     "desc": "对话是否符合角色身份/性格/处境？"},
    {"key": "reasoning", "name": "论证可靠性", "hard": False,
     "desc": "角色的推理/判断是否有逻辑漏洞？"},
]


def _load_model():
    """懒加载 GGUF Q4_K_M，失败则设为 None，缓存到 MODELS_DIR/qwythos-9b-q4"""
    global _LLM
    if _LLM is not None:
        return _LLM
    try:
        import os as _os
        # 从 _path_utils 读取 MODELS_DIR，失败则用默认
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from _path_utils import MODELS_DIR
            model_cache = str(MODELS_DIR / "qwythos-9b-q4")
        except Exception:
            model_cache = str(Path.home() / ".cache" / "huggingface" / "hub")
        _os.environ["HUGGINGFACE_HUB_CACHE"] = model_cache
        from llama_cpp import Llama
        print(f"[推理审核] 加载 GGUF: {GGUF_REPO}/{GGUF_FILE}")
        print(f"[推理审核] 缓存目录: {model_cache}")
        print(f"[推理审核] 首次加载需下载 ~5.5GB，请稍候...")
        _LLM = Llama.from_pretrained(
            repo_id=GGUF_REPO,
            filename=GGUF_FILE,
            n_ctx=8192,           # 8K 上下文（审核够用）
            n_threads=8,          # CPU 线程数
            n_gpu_layers=-1,      # -1 = 全部 GPU（有 GPU 时）
            verbose=False,        # 不输出 llama.cpp 日志
        )
        print(f"[推理审核] GGUF 加载完成")
    except ImportError:
        print("[推理审核] 模型不可用: 未安装 llama-cpp-python")
        print("[推理审核] 安装: pip install llama-cpp-python -i https://mirrors.aliyun.com/pypi/simple/")
        _LLM = None
    except Exception as e:
        print(f"[推理审核] 模型加载失败: {e}")
        print("[推理审核] 模型将自动跳过，不影响现有流程")
        _LLM = None
    return _LLM


def _strip_think(text: str) -> str:
    """剥离 <think>...</think> 推理块"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def _read_sub_file(chapter_dir, sub_key):
    """读取子结构文件正文（跳过标题行和末行标记）"""
    p = Path(chapter_dir) / f"{sub_key}.txt"
    if not p.exists():
        return ""
    lines = p.read_text(encoding="utf-8-sig").strip().split("\n")
    lines = [l for l in lines if not re.match(r'L\d+ · S\d+《', l.strip())]
    if lines and re.match(r'L\d+S\d+', lines[-1].strip()):
        lines = lines[:-1]
    return "\n".join(lines)


def _build_prompt(data, chapter, chapter_dir) -> str:
    """构建推理审核 prompt"""
    ch_info = None
    for ch in data.get("chapters", []):
        if ch["id"] == chapter:
            ch_info = ch
            break
    if not ch_info:
        return ""

    subs = ch_info.get("sub_structures", {})
    sorted_keys = sorted(subs.keys())

    # 角色设定摘要
    char_lines = []
    for c in data.get("characters", []):
        name = c.get("name", "")
        role = c.get("role", "")
        mbti = c.get("mbti", "")
        archetype = c.get("archetype", "")
        traits = c.get("traits", [])
        func = c.get("function", "")
        aliases = c.get("aliases", [])
        parts = [f"  {name}"]
        if role:
            parts[0] += f"（{role}）"
        if mbti or archetype:
            parts[0] += f" [{mbti or ''} {archetype or ''}]".strip()
        if func:
            parts.append(f"    功能: {func}")
        if traits:
            parts.append(f"    特质: {', '.join(traits[:4])}")
        if aliases:
            parts.append(f"    别名: {', '.join(aliases)}")
        char_lines.append("\n".join(parts))
    char_setting = "\n".join(char_lines) if char_lines else "（无角色设定）"

    # 子结构规划
    sub_lines = []
    for sk in sorted_keys:
        sv = subs[sk]
        tone = sv.get("tone", "")
        emotions = sv.get("emotions", [])
        emo_str = ""
        if emotions:
            emo_parts = []
            for e in emotions:
                if isinstance(e, dict):
                    emo_parts.append(f"{e.get('type','')}(强度{e.get('intensity',0):.1f})")
                else:
                    emo_parts.append(str(e))
            emo_str = " [" + ", ".join(emo_parts) + "]"
        sub_lines.append(f"  {sk}《{sv.get('title','')}》: {sv.get('summary','')} | tone={tone}{emo_str}")
    sub_plan = "\n".join(sub_lines) if sub_lines else "（无子结构规划）"

    # 正文内容（限制总长度——取前15行+后8行）
    content_parts = []
    for sk in sorted_keys:
        text = _read_sub_file(chapter_dir, sk)
        if not text.strip():
            continue
        lines = text.strip().split("\n")
        preview = "\n".join(lines[:15])
        if len(lines) > 23:
            preview += "\n    ...（中间省略）..."
            preview += "\n" + "\n".join(lines[-8:])
        content_parts.append(f"── {sk} ──\n{preview}")
    chapter_content = "\n\n".join(content_parts) if content_parts else "（无正文）"

    # 构建维度列表
    dim_lines = []
    for d in DIMENSIONS:
        level = "【硬性】" if d["hard"] else "【参考】"
        dim_lines.append(f"{level} {d['name']}: {d['desc']}")
    dims_str = "\n".join(dim_lines)

    prompt = f"""你是一个专业的小说审核编辑。请审核以下章节内容，严格按指定 JSON 格式输出审核结果。

【角色设定】
{char_setting}

【章节概述】
{ch_info.get('overview', '（无概述）')}

【子结构规划】
{sub_plan}

【正文预览】
{chapter_content}

【审核维度】
{dims_str}

【输出要求】
以 JSON 数组格式输出，每项格式：
{{"dimension": "维度名", "result": "PASS"|"HARD"|"SOFT", "detail": "具体说明（20-50字）"}}

必须包含全部 5 个维度，仅输出 JSON 数组，不要有其他文字。"""
    return prompt


def check_reasoning(state_path, chapter, chapter_dir):
    """
    推理审核主入口。
    返回 issues list，格式同 finalize-chapter 标准。
    """
    issues = []

    sp = Path(state_path)
    if not sp.exists():
        return issues
    data = json.loads(sp.read_text(encoding="utf-8-sig"))

    llm = _load_model()
    if llm is None:
        print("\n  [推理审核] 跳过（无 Qwythos-9B Q4_K_M 模型）")
        return issues

    print(f"\n{'='*50}")
    print(f"[推理审核] 开始推理审核...")
    print(f"{'='*50}")

    prompt = _build_prompt(data, chapter, chapter_dir)
    if not prompt:
        print("  [推理审核] 跳过：无法构建 prompt")
        return issues

    try:
        output = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.6,
            top_p=0.95,
            top_k=20,
            stop=None,
        )
        raw_output = output["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"\n  [推理审核] 推理异常: {e}")
        print(f"  → 跳过推理审核，不影响现有流程")
        return issues

    cleaned = _strip_think(raw_output)

    # 提取 JSON
    results = None
    json_match = re.search(r'\[.*?\]', cleaned, re.DOTALL)
    if json_match:
        try:
            results = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    if results is None:
        try:
            results = json.loads(cleaned)
        except json.JSONDecodeError:
            pass
    if not isinstance(results, list):
        results = [results] if results else []

    if not results:
        print(f"\n  [推理审核] 无法解析模型输出")
        print(f"  原始输出前300字: {cleaned[:300]}")
        print(f"  → 推理结果不可用，不作阻断")
        return issues

    print(f"\n  推理审核结果:")
    for r in results:
        dim = r.get("dimension", "?")
        result = r.get("result", "PASS")
        detail = r.get("detail", "")
        print(f"    [{result}] {dim}: {detail}")
        if result == "HARD":
            issues.append({
                "file": chapter,
                "problem": f"推理审核 - {dim}: {detail}",
                "position": f"{chapter} reasoning",
                "severity": "HARD",
                "suggestion": f"请检查{dim}问题，根据审核建议修改后重新 finalize-chapter"
            })
        elif result == "SOFT":
            issues.append({
                "file": chapter,
                "problem": f"推理审核 - {dim}: {detail}",
                "position": f"{chapter} reasoning",
                "severity": "SOFT",
                "suggestion": "参考审核建议，如需要可手动修改"
            })

    h_count = len([i for i in issues if i.get("severity") == "HARD"])
    s_count = len([i for i in issues if i.get("severity") == "SOFT"])
    print(f"\n{'─'*50}")
    print(f"[推理审核] 完成: {h_count} HARD + {s_count} SOFT")
    print(f"{'='*50}")

    return issues


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python novel_reasoning_check.py <state_path> <chapter> <chapter_dir>")
        print("  需安装: pip install llama-cpp-python")
        print("  镜像: pip install llama-cpp-python -i https://mirrors.aliyun.com/pypi/simple/")
        print("  模型: 首次运行自动下载 Qwythos-9B Q4_K_M GGUF (~5.5GB)")
        print("  下载镜像: HF_ENDPOINT=https://hf-mirror.com python ...")
        sys.exit(1)
    issues = check_reasoning(sys.argv[1], sys.argv[2], sys.argv[3])
    if issues:
        print(f"\n发现 {len(issues)} 个推理审核问题:")
        for i in issues:
            print(f"  [{i.get('severity','?')}] {i.get('problem','?')}")
    else:
        print("\n推理审核全部通过。")
