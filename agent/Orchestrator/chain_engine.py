"""
chain_engine.py — 流水线执行引擎
遍历 Pipeline 节点，顺序/并行/循环执行，LLM 粘合输出到下一个技能输入。
"""

import os, subprocess, sys, threading, json, time, re
from datetime import datetime
from typing import Optional

# 支持直接/模块两种运行方式
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from chain_model import Pipeline, PipelineNode, flatten_nodes
from llm_client import LLMClient, LLMConnectionError
from skill_scanner import scan_skills, SKILLS_BASE

OUTPUT_DIR = os.path.join(_DIR, "output")
_DEBUG_LOG_PATH = os.path.join(_DIR, "llm_debug.log")


def _debug_log(text: str, max_len: int = 200):
    """将 LLM 原始输出写入调试日志"""
    try:
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now().isoformat()} ---\n")
            f.write(text[:max_len])
            f.write(f"\n... (length={len(text)})\n")
    except Exception:
        pass


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── 输出文件解析 ──────────────────────────────────────

_FILE_RE = re.compile(
    r'\[FILE:\s*([^\]]+?)\]\s*(.*?)\s*\[/FILE\]',
    re.DOTALL | re.IGNORECASE
)


def _save_outputs(text: str) -> tuple[str, list[str]]:
    """
    从 LLM 输出中提取 [FILE:filename]...[/FILE] 块，保存到 output/，
    返回 (清理后的文本, 已保存文件路径列表)
    """
    _ensure_output_dir()
    saved = []
    cleaned = text

    for match in _FILE_RE.finditer(text):
        filename = match.group(1).strip()
        content = match.group(2).strip()
        if not filename or not content:
            continue

        # 安全化文件名
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', filename)
        fpath = os.path.join(OUTPUT_DIR, safe_name)

        try:
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            saved.append(fpath)
        except Exception:
            continue

        # 从结果中移除 marker，替换为文件名提示
        cleaned = cleaned.replace(match.group(0), f"\n[文件已保存: {fpath}]\n")

    return cleaned, saved


# ── LLM 调用 ──────────────────────────────────────────

def _llm_call(llm: LLMClient, prompt: str, progress_callback=None,
              system: str = "") -> str:
    """调用 LLM，捕获连接异常并给出可读错误"""
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        raw = llm.chat(messages)
        # 调试：保存原始 LLM 输出到日志
        _debug_log(raw)

        if not raw or not raw.strip():
            if progress_callback:
                progress_callback("[LLM 返回空内容] 模型未生成输出")
            return "[LLM 返回空内容] 模型可能未正确加载，或 prompt 超出上下文窗口。检查 LM Studio 的模型状态。"
        cleaned, saved = _save_outputs(raw)
        if saved and progress_callback:
            for fp in saved:
                progress_callback(f"  ⬇ 已保存: {fp}")
        return cleaned
    except LLMConnectionError as e:
        if progress_callback:
            progress_callback(f"[LLM 连接失败] {e}")
        return f"[LLM 连接失败] {e}\n请检查 LM Studio / Ollama 是否在 {llm.base_url} 运行。"
    except TimeoutError as e:
        msg = f"模型推理超过 {llm.timeout} 秒。可在设置中调大 LLM 超时。"
        if progress_callback:
            progress_callback(f"[LLM 超时] {msg}")
        return f"[LLM 超时] {msg}"
    except Exception as e:
        if progress_callback:
            progress_callback(f"[LLM 错误] {e}")
        return f"[LLM 错误] {e}"


# ── 技能目录/脚本 ─────────────────────────────────────

def _find_skill_dir(skill_name: str) -> Optional[str]:
    skills = scan_skills()
    for s in skills:
        if s.name == skill_name:
            return s.path
    candidate = os.path.join(SKILLS_BASE, skill_name)
    if os.path.isdir(candidate):
        return candidate
    return None


def _read_skill_md(skill_dir: str) -> str:
    mdf = os.path.join(skill_dir, "SKILL.md")
    if os.path.isfile(mdf):
        with open(mdf, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _get_skill_scripts(skill_dir: str) -> list[str]:
    scripts_dir = os.path.join(skill_dir, "scripts")
    if os.path.isdir(scripts_dir):
        return sorted([
            os.path.join(scripts_dir, f)
            for f in os.listdir(scripts_dir)
            if f.endswith(".py") or f.endswith(".sh") or f.endswith(".bat")
        ])
    return []


def _get_main_script(skill_name: str, scripts: list[str]) -> Optional[str]:
    if not scripts:
        return None
    scripts_dir = os.path.dirname(scripts[0])
    for ext in (".py", ".sh", ".bat"):
        candidate = os.path.join(scripts_dir, skill_name + ext)
        if candidate in scripts:
            return candidate
    for name in ("main.py", "run.py", "index.py"):
        candidate = os.path.join(scripts_dir, name)
        if candidate in scripts:
            return candidate
    return None


def _run_script(script: str, timeout: int = 1800, progress_callback=None) -> str:
    if script.endswith(".py"):
        runner = [sys.executable, script]
    elif script.endswith(".bat"):
        runner = [script]
    else:
            runner = ["bash", script]
    try:
        r = subprocess.run(
            runner, capture_output=True, timeout=timeout,
            cwd=os.path.dirname(os.path.dirname(script)),
            text=True, encoding='utf-8', errors='replace',
        )
        return (r.stdout or r.stderr or "(无输出)").strip()
    except subprocess.TimeoutExpired:
        return f"[超时] {script}（超过{timeout}秒）"
    except Exception as e:
        return f"[错误] {e}"


# ── LLM 粘合 / 优化 ──────────────────────────────────

def _llm_glue(llm: LLMClient, prev_skill_md: str, next_skill_md: str,
              prev_output: str, prev_skill_name: str, next_skill_name: str,
              user_intent: str, progress_callback=None) -> str:
    """严格按技能接口转换：读上一个的输出格式 + 下一个的输入格式 → 精确转换"""
    system = "你是技能编排粘合器。你的任务：读下一个技能的说明，理解它需要什么输入格式和触发条件，然后把上一个输出精确转换过去。"
    prompt = f"""用户完整需求：{user_intent}

=== 上一个技能「{prev_skill_name}」的说明（它的输出格式） ===
{prev_skill_md[:1500]}

=== 上一个技能的实际输出内容 ===
{prev_output[:2000]}

=== 下一个技能「{next_skill_name}」的说明（读这个来理解它要什么输入） ===
{next_skill_md[:3000]}

---
任务：把上一个技能的输出内容，转换成下一个技能「{next_skill_name}」所需要的输入格式。
- 读下一个技能的说明，判断它期望什么形式的输入（文字描述？结构化 JSON？文件名？参数？）。
- 读上一个技能的说明，判断它的输出是什么格式。
- 按下一个技能的要求精确转换。
- 只输出转换后的内容。"""
    return _llm_call(llm, prompt, progress_callback, system=system)


def _optimize_pipeline(pipeline: Pipeline, progress_callback=None) -> bool:
    """
    硬编码的流水线优化器，不依赖外部技能或 LLM。
    固化 skill-sub 的优化逻辑到智能体内部。

    优化策略：
    1. 连续重复步骤 → 包裹为循环
    2. 连续不同且无依赖的步骤 → 包裹为并行
    3. 冗余检测 → 删除完全相同的连续重复
    4. 排序优化 → 拓扑序重排
    """
    if progress_callback:
        progress_callback("正在优化流水线...")

    nodes = pipeline.nodes
    if len(nodes) < 2:
        return False

    changed = False
    new_nodes = []
    i = 0

    while i < len(nodes):
        n = nodes[i]

        # ── Phase 1: 连续重复检测 → 循环 ──
        repeat_count = 1
        while i + repeat_count < len(nodes):
            nxt = nodes[i + repeat_count]
            if nxt.skill_name == n.skill_name and nxt.mode == n.mode:
                repeat_count += 1
            else:
                break

        if repeat_count >= 2 and n.mode == "seq":
            # 连续重复 2+ 次 → 包裹为 loop
            loop_node = PipelineNode(
                skill_name=n.skill_name,
                display_name=f"循环 {n.display_name or n.skill_name} ({repeat_count}次)",
                mode="loop",
                loop_times=repeat_count,
                loop_start=1,
                loop_end=repeat_count,
                children=[PipelineNode(
                    skill_name=n.skill_name,
                    display_name=n.display_name,
                    mode="seq",
                )],
            )
            new_nodes.append(loop_node)
            i += repeat_count
            changed = True
            if progress_callback:
                progress_callback(f"  ↻ {n.display_name or n.skill_name} ×{repeat_count} → 循环")
            continue

        # ── Phase 2: 无依赖步骤检测 → 并行 ──
        # 相邻的不同 seq 步骤且各自不依赖对方 → 可并行
        distinct_count = 1
        while i + distinct_count < len(nodes):
            nxt = nodes[i + distinct_count]
            if nxt.skill_name != n.skill_name and n.mode == "seq" and nxt.mode == "seq":
                # 简单启发式：不同技能的连续 seq 步骤可并行
                distinct_count += 1
            else:
                break

        if distinct_count >= 3:
            # 3+ 个连续不同步骤 → 并行
            par_children = []
            for j in range(distinct_count):
                orig = nodes[i + j]
                par_children.append(PipelineNode(
                    skill_name=orig.skill_name,
                    display_name=orig.display_name,
                    mode="seq",
                ))
            par_node = PipelineNode(
                display_name=f"并行 {len(par_children)}个步骤",
                mode="par",
                children=par_children,
            )
            new_nodes.append(par_node)
            i += distinct_count
            changed = True
            if progress_callback:
                progress_callback(f"  ∥ {distinct_count}个步骤 → 并行")
            continue

        # ── Phase 3: 精确重复删除 ──
        if len(new_nodes) > 0:
            last = new_nodes[-1]
            if (last.skill_name == n.skill_name and last.mode == n.mode
                    and last.mode == "seq"):
                # 完全相同的 seq 步骤在优化后相邻 → 去重
                if progress_callback:
                    progress_callback(f"  ✕ 去重: {n.display_name or n.skill_name}")
                i += 1
                changed = True
                continue

        # ── Phase 4: 原样保留 ──
        new_nodes.append(n)
        i += 1

    if changed:
        pipeline.nodes = new_nodes
        if progress_callback:
            progress_callback(f"优化完成 — {len(new_nodes)} 个步骤")
    else:
        if progress_callback:
            progress_callback("无需优化")

    return changed


# ── 内置通用工具（color-toolkit-turn / universal-file-ops 固化） ──

def _file_op(action: str, path: str, content: str = "") -> str:
    """原子化文件操作，固化 universal-file-ops 的 CRUD 核心"""
    try:
        if action == "read":
            if not os.path.isfile(path):
                return f"[错误] 文件不存在: {path}"
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        elif action == "write":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, path)
            return f"[已写入] {path} ({len(content)} 字符)"
        elif action == "append":
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
            return f"[已追加] {path}"
        elif action == "delete":
            if os.path.isfile(path):
                os.remove(path)
                return f"[已删除] {path}"
            return f"[错误] 文件不存在: {path}"
        else:
            return f"[错误] 未知操作: {action}"
    except Exception as e:
        return f"[错误] {e}"


def _color_validate(hex_color: str) -> Optional[str]:
    """检查颜色格式是否正确，返回规范化后的颜色或 None"""
    m = re.match(r'^#?([0-9a-fA-F]{6})$', hex_color.strip())
    if m:
        return "#" + m.group(1).upper()
    m = re.match(r'^#?([0-9a-fA-F]{3})$', hex_color.strip())
    if m:
        c = m.group(1)
        return "#" + "".join(c[i]*2 for i in range(3)).upper()
    return None


def _calc_contrast(fg: str, bg: str) -> float:
    """计算两颜色的对比度比（WCAG 标准）"""
    def rel_lum(hex_s):
        hex_s = hex_s.lstrip("#")
        r, g, b = int(hex_s[0:2], 16) / 255, int(hex_s[2:4], 16) / 255, int(hex_s[4:6], 16) / 255
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    l1, l2 = rel_lum(fg), rel_lum(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _color_check(text: str) -> list[str]:
    """扫描文本中出现的颜色，检测对比度问题"""
    issues = []
    colors = re.findall(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}', text)
    # 检查常见前景/背景色对
    pairs = [("#FFFFFF", "#000000"), ("#000000", "#FFFFFF")]
    for c in set(colors):
        valid = _color_validate(c)
        if not valid:
            issues.append(f"颜色格式错误: {c}")
    for i, c1 in enumerate(colors):
        for j, c2 in enumerate(colors):
            if i < j:
                c1v, c2v = _color_validate(c1), _color_validate(c2)
                if c1v and c2v:
                    ratio = _calc_contrast(c1v, c2v)
                    if ratio < 3.0:
                        issues.append(f"对比度过低: {c1v}/{c2v} = {ratio:.1f}:1 (建议 ≥ 3:1)")
    return issues


def _validate_html(html: str) -> list[str]:
    """基本 HTML 结构校验"""
    issues = []
    if not html.strip():
        issues.append("HTML 内容为空")
        return issues
    # 检查基本标签完整性
    tags = {"<html": "</html>", "<head": "</head>", "<body": "</body>",
            "<div": "</div>", "<table": "</table>"}
    for open_tag, close_tag in tags.items():
        opens = html.lower().count(open_tag)
        closes = html.lower().count(close_tag)
        if opens > 0 and opens != closes:
            issues.append(f"标签不匹配: {open_tag} ({opens}个) vs {close_tag} ({closes}个)")
    # 检查 emoji
    emoji_pattern = re.compile(r'[\U0001F300-\U0001FAFF]')
    emojis = emoji_pattern.findall(html)
    if emojis:
        issues.append(f"含 {len(emojis)} 个 emoji（通常影响排版）")
    # 检查内联样式是否完整
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL | re.IGNORECASE)
    for sb in style_blocks:
        if "@import" in sb.lower() and "url(" in sb.lower():
            issues.append("style 含外部 CDN import，建议内联")
    return issues


def _auto_heal_run(script: str, timeout: int = 300, progress_callback=None) -> str:
    """运行 Python 脚本，ImportError 自动 pip install 后重试"""
    if not script.endswith(".py"):
        return _run_script(script, timeout, progress_callback)

    for attempt in range(3):
        try:
            r = subprocess.run(
                [sys.executable, script],
                capture_output=True, timeout=timeout,
                cwd=os.path.dirname(os.path.dirname(script)),
                text=True, encoding='utf-8', errors='replace',
            )
        except subprocess.TimeoutExpired:
            return f"[超时] {script}（超过{timeout}秒）"
        except Exception as e:
            return f"[错误] {e}"

        stderr_lower = r.stderr.lower() if r.stderr else ""
        # 检测 ImportError / ModuleNotFoundError
        import_errors = re.findall(r'(?:importerror|modulenotfounderror|no module named)\s*[\'"]?([a-zA-Z0-9_]+)', stderr_lower)
        if not import_errors:
            return (r.stdout or r.stderr or "(无输出)").strip()

        for pkg in import_errors[:3]:
            if progress_callback:
                progress_callback(f"  pip install {pkg}...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                capture_output=True, timeout=120,
                text=True, encoding='utf-8', errors='replace',
            )

    return (r.stdout or r.stderr or "(无输出)").strip()


# ── semantic-split 固化（可勾选功能） ──

_5W2H_RE = re.compile(
    r'(?:什么|what|做什么|内容|主题)[：:\s]*(.+?)(?=[。；;]|$)|'
    r'(?:为什么|why|原因|目的)[：:\s]*(.+?)(?=[。；;]|$)|'
    r'(?:谁|who|负责人|执行人)[：:\s]*(.+?)(?=[。；;]|$)|'
    r'(?:哪里|where|地点|位置|平台)[：:\s]*(.+?)(?=[。；;]|$)|'
    r'(?:什么时候|when|时间|截止)[：:\s]*(.+?)(?=[。；;]|$)|'
    r'(?:怎么做|how|方式|方法|步骤|流程)[：:\s]*(.+?)(?=[。；;]|$)|'
    r'(?:多少|how\s*much|数量|预算|大小)[：:\s]*(.+?)(?=[。；;]|$)',
    re.IGNORECASE
)


def _semantic_split(user_intent: str, progress_callback=None) -> list[dict]:
    """
    固化 semantic-split 的核心：5W2H 提取 + 结构拆分。
    返回 [{step, desc, depends_on}] 列表。
    """
    if not user_intent:
        return []

    # 5W2H 提取
    dims = {"what": "", "why": "", "who": "", "where": "",
            "when": "", "how": "", "how_much": ""}
    dim_keys = list(dims.keys())
    for m in _5W2H_RE.finditer(user_intent):
        for i, g in enumerate(m.groups()):
            if g and i < len(dim_keys):
                if not dims[dim_keys[i]]:
                    dims[dim_keys[i]] = g.strip()

    # 自然语言拆分：按 "，然后" "先" "再" "接着" 等切分
    steps = []
    markers = [r'先(.+?)(?:再|然后|接着)', r'(.+?)(?:然后|接着|之后)(.+)',
               r'第一步[：:\s]*(.+?)(?=第二步|$)', r'第二步[：:\s]*(.+)']

    found_steps = []
    for marker in markers:
        m = re.search(marker, user_intent)
        if m:
            for g in m.groups():
                if g and g.strip() and len(g.strip()) > 2:
                    found_steps.append(g.strip())
            if found_steps:
                break

    if not found_steps:
        # 没有显式步骤标记 → 用 5W2H 生成单步
        found_steps = [user_intent[:100]]

    result = []
    for i, step_text in enumerate(found_steps):
        step = {
            "step": i + 1,
            "desc": step_text,
            "depends_on": list(range(1, i)) if i > 0 else [],
        }
        # 如果 5W2H 有内容，附加到描述
        dim_info = "; ".join(f"{k}={v}" for k, v in dims.items() if v)
        if dim_info:
            step["5w2h"] = dim_info
        result.append(step)

    if progress_callback:
        progress_callback(f"语义拆分: {len(result)} 个子步骤")

    return result


# ── 自审/自循环（triphasic 固化） ──

def _self_review_output(output: str, step_name: str, llm: LLMClient,
                         progress_callback=None) -> tuple[bool, str]:
    """
    自审输出质量。检查常见问题：
    - HTML 结构错误
    - 颜色冲突
    - 代码语法问题
    - 排版拥挤
    - 思路偏离
    返回 (通过, 审查意见)
    """
    issues = []

    # 1. HTML 校验（如果有 HTML）
    if "[FILE:" in output.lower() or "<html" in output.lower() or "<!DOCTYPE" in output:
        html_blocks = re.findall(r'\[FILE:\s*([^\]]+\.html)\]\s*(.*?)\s*\[/FILE\]', output, re.DOTALL | re.IGNORECASE)
        for fname, content in html_blocks:
            issues.extend(_validate_html(content))

    # 2. 颜色检查
    color_issues = _color_check(output)
    issues.extend(color_issues)

    # 3. LLM 深度审查（复杂步骤）
    if llm and llm.check_connection()[0]:
        system = "你是质量审查员。审查以下输出，只输出问题列表，每行一个。如果没问题输出「OK」。"
        prompt = f"""步骤名称: {step_name}
输出内容:
{output[:1500]}

检查以下问题（只输出问题，不要解释）：
- 产出物是否为空或残缺？
- 排版是否拥挤或错乱？
- 代码是否有明显错误（不完整标签、语法错误）？
- 是否存在偏离原始需求的输出？"""
        review = llm.ask(system, prompt)
        review = review.strip()
        if review and review != "OK" and "OK" not in review[:10]:
            issues.append(f"LLM 审查: {review[:200]}")

    if issues:
        report = "\n".join(f"  ⚠ {i}" for i in issues[:5])
        return False, report

    return True, "OK"


def _triphasic_execute_step(node: PipelineNode, llm: LLMClient,
                             prev_output: str, user_intent: str,
                             prev_name: str, next_name: str,
                             script_timeout: int = 1800,
                             progress_callback=None) -> str:
    """
    三步执行：Execute → Review → Advance（最多 3 次重试）。
    """
    step_name = node.display_name or node.skill_name
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        # Execute
        if progress_callback:
            progress_callback(f"[{step_name}] 执行 (第{attempt}次)...")
        output = execute_node(node, llm, prev_output, user_intent,
                               prev_name, next_name,
                               script_timeout=script_timeout,
                               triphasic=False,
                               progress_callback=progress_callback)

        if not output or output.startswith("[错误]") or output.startswith("[LLM"):
            if progress_callback:
                progress_callback(f"[{step_name}] ❌ 执行失败（第{attempt}次）")
            if attempt < max_retries:
                continue
            return f"[{step_name}] 重试{max_retries}次后仍失败:\n{output}"

        # Review
        if progress_callback:
            progress_callback(f"[{step_name}] 审查...")
        passed, review = _self_review_output(output, step_name, llm, progress_callback)

        # Advance
        if passed:
            if progress_callback:
                progress_callback(f"[{step_name}] ✅ 通过审查")
            return output
        else:
            if progress_callback:
                progress_callback(f"[{step_name}] ⚠ 审查发现问题:\n{review}")
            if attempt < max_retries:
                if progress_callback:
                    progress_callback(f"[{step_name}] 第{attempt}次不通过，重试...")
                # 将审查意见作为额外上下文传给下次执行
                prev_output = f"{prev_output}\n\n[审查反馈（需修正）]\n{review}"
            else:
                return f"[{step_name}] 重试{max_retries}次后审查仍不通过:\n{output}\n\n审查意见:\n{review}"

    return output

_SKILL_EXEC_SYSTEM = """\
你是技能「{skill_name}」，处于流水线中的一环。
前一个技能：「{prev_name}」  后一个技能：「{next_name}」

⛔ 禁止行为（违反=执行失败）：
- 禁止输出解释、计划、描述
- 禁止输出"我建议"、"我将"、"首先"等引导语
- 禁止不输出实质性内容
- 禁止把技能说明抄一遍当作输出

✅ 输出契约：
- 如果技能说明说"生成 HTML"、"自包含 HTML"、"输出 HTML"，你必须直接输出 [FILE: 文件名.html] 包裹的完整 HTML 代码
- 如果技能说明说"生成 JSON"、"结构化数据"，输出 [FILE: 文件名.json] 包裹的 JSON
- 其他文件类型同理：文件名.扩展名
- 文本类输出直接写文字，不用 FILE 标记

⌛ 记住：你的工作结果会被传给下一个技能。只输出内容本身，让下一个技能可以正确接收。
"""


def _build_skill_prompt(skill_md: str, user_intent: str, prev_output: str) -> str:
    """执行 prompt：把 SKILL.md + 上下文 + 任务传给 LLM，让 LLM 按技能说明执行"""
    return f"""## 技能说明（你的功能、输入格式、输出格式都在这里，按此执行）
{skill_md[:3000]}

## 任务
{user_intent}

## 上下文（上一个步骤的输出）
{prev_output[:2000]}

---
严格按技能说明执行。直接输出。"""


def execute_node(node: PipelineNode, llm: LLMClient,
                 prev_output: str, user_intent: str,
                 prev_skill_name: str = "",
                 next_skill_name: str = "",
                 script_timeout: int = 1800,
                 triphasic: bool = False,
                 progress_callback=None) -> str:
    """执行单个节点，返回输出文本。triphasic=True 启用自审查循环。"""
    # 如果启用 triphasic 且不是 par/loop 容器（容器内部递归处理）
    if triphasic and node.mode == "seq" and node.skill_name:
        return _triphasic_execute_step(node, llm, prev_output, user_intent,
                                        prev_skill_name, next_skill_name,
                                        script_timeout, progress_callback)

    prefix = f"[{node.display_name or node.skill_name}]"

    if progress_callback:
        progress_callback(f"{prefix} 开始执行...")

    if node.mode == "par":
        outputs = [None] * len(node.children)
        threads = []
        def run_child(i, child):
            outputs[i] = execute_node(child, llm, prev_output, user_intent,
                                       prev_skill_name, next_skill_name,
                                       script_timeout, triphasic, progress_callback)
        for i, child in enumerate(node.children):
            t = threading.Thread(target=run_child, args=(i, child), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=1800)
        result = "\n--- 并行结果 ---\n" + "\n".join(
            f"[子步骤 {i+1}] {o}" for i, o in enumerate(outputs) if o
        )
        return result

    if node.mode == "loop":
        times = node.loop_times or 1
        if node.loop_start is not None and node.loop_end is not None:
            times = node.loop_end - node.loop_start + 1
        outputs = []
        current_input = prev_output
        for i in range(times):
            if progress_callback:
                progress_callback(f"{prefix} 第 {i+1}/{times} 轮")
            for child in node.children:
                current_input = execute_node(child, llm, current_input, user_intent,
                                              prev_skill_name, next_skill_name,
                                              script_timeout, triphasic, progress_callback)
                outputs.append(current_input)
        return "\n".join(f"[循环第 {i+1} 次] {o}" for i, o in enumerate(outputs))

    # seq: 执行单个技能
    sdir = _find_skill_dir(node.skill_name)
    if not sdir:
        return f"[错误] 找不到技能目录: {node.skill_name}"

    skill_md = _read_skill_md(sdir)
    scripts = _get_skill_scripts(sdir)
    main_script = _get_main_script(node.skill_name, scripts)

    if main_script:
        if progress_callback:
            progress_callback(f"{prefix} 运行脚本 {os.path.basename(main_script)}...")
        return _run_script(main_script, script_timeout, progress_callback)

    # LLM 执行 — 用 system 指令压制 LLM 的"解释倾向"
    if progress_callback:
        progress_callback(f"{prefix} LLM 执行...")

    system = _SKILL_EXEC_SYSTEM.format(
        skill_name=node.display_name or node.skill_name,
        prev_name=prev_skill_name or "(首个步骤)",
        next_name=next_skill_name or "(末个步骤)",
    )
    prompt = _build_skill_prompt(skill_md, user_intent, prev_output)
    return _llm_call(llm, prompt, progress_callback, system=system)


# ── 流水线执行 ──────────────────────────────────────

def execute_pipeline(pipeline: Pipeline, llm: LLMClient,
                     user_intent: str = "",
                     script_timeout: int = 1800,
                     progress_callback=None) -> str:
    """执行完整流水线"""
    _ensure_output_dir()

    if progress_callback:
        progress_callback(f"开始执行流水线: {pipeline.name}")

    # 0. 连接预检
    ok, reason = llm.check_connection()
    if not ok:
        return (f"[LLM 连接失败] {reason}\n"
                f"请确认 LLM 后端已在 {llm.base_url} 运行。\n"
                f"如使用 LM Studio，请启动并加载模型；如使用 Ollama，请运行 ollama serve。")

    intent = user_intent or pipeline.name

    # 0.5 语义拆分（如果启用）
    if pipeline.semantic_split and intent:
        split_steps = _semantic_split(intent, progress_callback)
        if len(split_steps) > 1:
            if progress_callback:
                progress_callback(f"语义拆分出 {len(split_steps)} 个子步骤")

    # 1. 优化（固化算法）
    if pipeline.optimize:
        _optimize_pipeline(pipeline, progress_callback)

    # 2. 执行
    output = intent
    flat = flatten_nodes(pipeline.nodes)
    for i, node in enumerate(flat):
        if progress_callback:
            progress_callback(f"步骤 {i+1}/{len(flat)} — {node.display_name or node.skill_name}")

        prev_name = flat[i - 1].display_name or flat[i - 1].skill_name if i > 0 else ""
        next_name = flat[i + 1].display_name or flat[i + 1].skill_name if i < len(flat) - 1 else ""

        sdir = _find_skill_dir(node.skill_name)

        # LLM 粘合
        if sdir and not _get_main_script(node.skill_name, _get_skill_scripts(sdir)) and i > 0:
            prev_sdir = _find_skill_dir(flat[i - 1].skill_name)
            prev_skill_md = _read_skill_md(prev_sdir) if prev_sdir else ""
            next_skill_md = _read_skill_md(sdir)

            output = _llm_glue(llm, prev_skill_md, next_skill_md,
                               output,
                               prev_name, node.display_name or node.skill_name,
                               intent,
                               progress_callback)

        output = execute_node(node, llm, output, intent,
                              prev_name, next_name,
                              script_timeout=script_timeout,
                              triphasic=pipeline.triphasic,
                              progress_callback=progress_callback)

    # 3. 最终保存（如果结果包含 FILE marker 但没被 parse 到，兜底保存）
    final_text = output or "(流水线执行完毕，无输出)"

    # 汇总已保存文件
    saved_files = [os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR)
                   if os.path.isfile(os.path.join(OUTPUT_DIR, f))]
    saved_files = sorted(saved_files, key=os.path.getmtime, reverse=True)

    # 如果有保存的文件，在结果顶部添加提示
    if saved_files:
        file_list = "\n".join(f"  📄 {f}" for f in saved_files[:5])
        final_text = f"--- 已保存 {len(saved_files)} 个文件 ---\n{file_list}\n\n{final_text}"

    return final_text
