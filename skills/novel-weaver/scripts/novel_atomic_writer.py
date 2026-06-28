#!/usr/bin/env python3
"""
Atomic Writer — 原子写入器（v3，格式硬约束+别名钩子版）

格式规范（钩子强制执行，阻断式）：
  第1行: L## · S##《标题》
  第2..N-2行: 正文（纯叙事，不得含子结构标记行，不得含【别名】标记行）
  第N-1行: 【别名】声明（由本钩子拦截，不写进正文）
  末行: L##S##（由本脚本自动追加）

流程门禁：
  1. title_line 正则校验（阻断）
  2. body 标记行检测（阻断）
  3. 正文非空检测（阻断）
  4. 标点缺失校验（软性，不阻断）
  5. 别名声明拦截（阻断：缺失则阻断，存在则剥离并注册）
  6. 元注释污染检测（阻断）
  7. 署名/代名检测（阻断）
  8. 原子写入 → fsync → 追加编号标记 → 再次 fsync
"""
import sys, os, re, subprocess
from pathlib import Path

TITLE_PATTERN = re.compile(r'^L\d+ · S\d+《.+》$')
MARKER_PATTERN = re.compile(r'^L\d+S\d+$')
ALIAS_PATTERN = re.compile(r'^【别名】\s*(.+?)\s*=\s*(.+)$')
ALIAS_NONE_PATTERN = re.compile(r'^【别名】\s*无\s*$')
SCRIPTS_DIR = Path(__file__).parent

# 署名/代名检测模式（禁止 LLM 擅自添加）
SIGNATURE_PATTERNS = [
    r'由\s*\w*\s*(撰写|创作|生成|编写|完成)',
    r'本文\s*(由|为)\s*\w*\s*(撰写|创作|生成|编写)',
    r'WorkBuddy\s*(创作|生成|编写|撰写)',
    r'(撰写|创作|生成)于\s*\w*\s*(助手|AI|WorkBuddy)',
    r'在\s*\w*\s*(指导|帮助|协助)下\s*(撰写|创作|生成)',
    r'本文由\s*\w+\s*创作',
]


def validate_and_write(content, filepath, chapter, sub_key, signature=None, state_path=None):
    """
    原子写入 + 多钩子校验。
    signature: {"enabled": bool, "text": str} 或 None（跳过检测）
    """
    fp = Path(filepath)
    fp.parent.mkdir(parents=True, exist_ok=True)

    sub_marker = f"{chapter}{sub_key}"
    lines = content.split("\n")

    # ── 钩子1: 第1行标题格式校验（阻断） ──
    first_line = lines[0].strip() if lines else ""
    if not TITLE_PATTERN.match(first_line):
        print(f"[HOOK-BLOCK] 第1行不是合法标题格式")
        print(f"  期望: L{chapter} · {sub_key}《标题》")
        print(f"  实际: {first_line}")
        return False

    # ── 钩子5: 别名声明拦截（阻断：缺失则阻断，存在则剥离+注册）──
    alias_line = None
    alias_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if ALIAS_PATTERN.match(stripped):
            alias_line = stripped
            alias_idx = i
            break
        if ALIAS_NONE_PATTERN.match(stripped):
            alias_line = stripped
            alias_idx = i
            break

    if alias_line is None:
        # 第一子结构可豁免（尚无角色可产生别名）
        if sub_key != "S01":
            print(f"[HOOK-BLOCK] 缺少【别名】声明")
            print(f"  若无别名请输出: 【别名】无")
            print(f"  若有别名请输出: 【别名】老陈 = 陈叔")
            return False
    elif alias_line.startswith("【别名】无"):
        # 声明无别名，剥离即可
        lines.pop(alias_idx)
        print(f"  [别名] 声明: 无别名")
    else:
        # 解析别名声明并注册
        m = ALIAS_PATTERN.match(alias_line)
        if m:
            char_name = m.group(1).strip()
            alias = m.group(2).strip()
            lines.pop(alias_idx)  # 从正文剥离
            print(f"  [别名] 声明: {char_name} ← 「{alias}」")
            if state_path:
                sm_path = SCRIPTS_DIR / "novel_state_manager.py"
                r = subprocess.run(
                    [sys.executable, str(sm_path), "register-alias", state_path, char_name, alias],
                    capture_output=True, text=True, encoding="utf-8"
                )
                if r.returncode == 0:
                    for out_line in r.stdout.strip().split("\n"):
                        if out_line.strip():
                            print(f"    {out_line.strip()}")
                else:
                    print(f"    [WARN] 别名注册失败: {r.stderr.strip()}")

    # ── 钩子6: 正文非空检测（阻断）──
    # 重新构建 body（别名行已被剥离）
    body_lines = lines[1:]
    body_text = "\n".join(body_lines).strip()
    if not body_text:
        print(f"[HOOK-BLOCK] 正文为空，拒绝写入")
        return False

    # ── 钩子7: 正文标记行检测（阻断）──
    for i, line in enumerate(body_lines, 2):
        stripped = line.strip()
        if MARKER_PATTERN.match(stripped):
            print(f"[HOOK-BLOCK] 正文第{i}行含非法子结构标记: {line.strip()}")
            return False

    # ── 钩子8: 标点缺失校验（软性，不阻断）──
    PUNCTUATION = set("，。；：？！、,.;:?!")
    MAX_SEGMENT = 80
    for i, line in enumerate(body_lines, 2):
        stripped = line.strip()
        if not stripped:
            continue
        # 按标点分割后检查最长片段
        segments = []
        current = ""
        for ch in stripped:
            if ch in PUNCTUATION:
                if current.strip():
                    segments.append(current.strip())
                current = ""
            else:
                current += ch
        if current.strip():
            segments.append(current.strip())
        longest = max((len(s) for s in segments), default=0)
        if longest > MAX_SEGMENT:
            print(f"  [PUNCT] 正文第{i}行含超长无标点片段（{longest}字），建议补充断句标点")

    # ── 写入前确认: 最终内容不含元注释污染 ──
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if re.match(r'^\*\*(S\d+|L\d+)\s*(完成|全章完成)', stripped):
            print(f"[HOOK-BLOCK] 正文第{i}行含元注释污染: {line.strip()}")
            print(f"  禁止将助手工作记录写入作品文件")
            return False

    # ── 钩子4: 署名/代名检测（代码级硬阻断） ──
    if signature is None:
        # 未传入配置，跳过检测
        pass
    elif not signature.get("enabled", False):
        # 签名关闭：禁止任何署名/代名
        for i, line in enumerate(lines, 1):
            for pat in SIGNATURE_PATTERNS:
                if re.search(pat, line):
                    print(f"[HOOK-BLOCK] 正文第{i}行含禁止的署名/代名: {line.strip()}")
                    print(f"  匹配模式: {pat}")
                    print(f"  当前设置: signature.enabled=false")
                    print(f"  如需添加署名，请执行: python novel_state_manager.py set-signature <state_path> true \"署名文本\"")
                    return False
    else:
        # 签名开启：只允许指定的署名文本，禁止自行编造
        sig_text = signature.get("text", "")
        for i, line in enumerate(lines, 1):
            for pat in SIGNATURE_PATTERNS:
                m = re.search(pat, line)
                if m:
                    if not sig_text:
                        # 开启了签名但未指定文本 → 不允许任何署名
                        print(f"[HOOK-BLOCK] 正文第{i}行含署名内容，但 signature.text 为空: {line.strip()}")
                        print(f"  请先设置签名文本: python novel_state_manager.py set-signature <state_path> true \"署名文本\"")
                        return False
                    if sig_text not in line:
                        # 署名文本与配置值不匹配
                        print(f"[HOOK-BLOCK] 正文第{i}行署名与配置值不匹配: {line.strip()}")
                        print(f"  当前设置: signature.text=\"{sig_text}\"")
                        print(f"  如需修改署名: python novel_state_manager.py set-signature <state_path> true \"新署名\"")
                        return False

    # ── 原子写入 ──
    # 写入正文（不含末行标记）
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())

    # 追加子结构编号标记
    with open(fp, "a", encoding="utf-8") as f:
        f.write(f"\n{sub_marker}\n")
        f.flush()
        os.fsync(f.fileno())

    print(f"[WRITE-OK] {filepath}")
    print(f"  标题: {first_line}")
    print(f"  正文: {len(body_lines)} 行")
    print(f"  标记: {sub_marker}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("用法: python novel_atomic_writer.py <content_file|-> <filepath> <chapter> <sub_key>")
        print("  - 表示从 stdin 读取内容")
        print("  示例: echo '内容' | python novel_atomic_writer.py - /path/to/L01/S01.txt L01 S01")
        sys.exit(1)

    content_src = sys.argv[1]
    filepath = sys.argv[2]
    chapter = sys.argv[3]
    sub_key = sys.argv[4]

    if content_src == "-":
        content = sys.stdin.read()
    else:
        content = Path(content_src).read_text(encoding="utf-8-sig")

    success = validate_and_write(content, filepath, chapter, sub_key)
    if not success:
        sys.exit(1)
