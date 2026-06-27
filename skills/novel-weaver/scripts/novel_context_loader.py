#!/usr/bin/env python3
"""
Context Loader — 上下文加载器
验证子结构是否已注册，加载写作上下文
"""
import json, sys
from pathlib import Path

# ── 情绪强度映射表 ──
INTENSITY_LABELS = [
    (0.0, 0.2, "微弱"),
    (0.2, 0.4, "轻度"),
    (0.4, 0.6, "中等"),
    (0.6, 0.8, "强烈"),
    (0.8, 1.0, "极致"),
]

def _intensity_label(val: float) -> str:
    """数值 → 标签"""
    for lo, hi, label in INTENSITY_LABELS:
        if lo <= val < hi:
            return label
    return "极致" if val >= 0.8 else "微弱"


# ── 情绪混合解读映射 ──
EMOTION_MIX_MAP = [
    # (primary, secondary, description)
    ({"愤怒", "恐惧"}, "色厉内荏：愤怒主导，恐惧底色"),
    ({"悲伤", "释然"}, "含泪释怀：悲伤中透出解脱"),
    ({"喜悦", "不安"}, "隐忧之喜：表面快乐，心底不安"),
    ({"恐惧", "好奇"}, "战栗探索：在恐惧中前行"),
    ({"爱", "悲伤"}, "悲伤爱意：深爱伴随失去的痛"),
    ({"平静", "期待"}, "静待之姿：宁静中暗涌期待"),
    ({"愤怒", "悲伤"}, "悲愤交加：愤怒源于深层悲伤"),
    ({"恐惧", "坚定"}, "凛然：恐惧但不退缩"),
    ({"喜悦", "释然"}, "释然喜悦：解脱后的轻松"),
]

def _emotion_mix_description(emotions: list) -> str:
    """分析情绪混合，返回人类可读描述"""
    if not emotions or len(emotions) < 2:
        return ""
    types = {e.get("type", "") for e in emotions}
    for ps, desc in EMOTION_MIX_MAP:
        if ps == types:
            return desc
    # 默认根据主次比描述
    primary = max(emotions, key=lambda e: e.get("intensity", 0))
    secondary = max([e for e in emotions if e != primary], key=lambda e: e.get("intensity", 0)) if len(emotions) > 1 else None
    if secondary and secondary.get("intensity", 0) > 0.3:
        return f"混合情绪：{primary.get('type','')}主导，{secondary.get('type','')}底色"
    return f"单一主导：{primary.get('type','')}"


def _format_emotions(sub: dict) -> str:
    """格式化情绪输出：愤怒 强烈[0.8/1] + 恐惧 轻度[0.3/1]"""
    emos = sub.get("emotions", [])
    if not emos:
        tone = sub.get("tone", "")
        if tone:
            return f"[情绪基调] {tone}"
        return ""
    # 兼容两种格式：遗留的字符串数组 ["疑惑","不安"] 和新格式 [{"type":"疑惑","intensity":0.5}]
    parts = []
    for e in emos:
        if isinstance(e, str):
            parts.append(f"{e}")
        else:
            t = e.get("type", "")
            v = e.get("intensity", 0)
            label = _intensity_label(v)
            parts.append(f"{t} {label}[{v:.1f}/1]")
    line = " + ".join(parts)
    if all(isinstance(e, str) for e in emos):
        return f"[情绪提示] {line}"
    mix = _emotion_mix_description(emos)
    if mix:
        line += f"\n           → {mix}"
    return line


def _find_characters_in_chapter(data: dict, chapter_id: str, sub_key: str) -> list:
    """扫描本章涉及的角色（基于子结构概述匹配角色名）"""
    chars = data.get("characters", [])
    if not chars:
        return []
    ch_info = None
    for ch in data.get("chapters", []):
        if ch["id"] == chapter_id:
            ch_info = ch
            break
    if not ch_info:
        return []
    subs = ch_info.get("sub_structures", {})
    involved = []
    # 从本章所有子结构概述中匹配角色名
    combined = ch_info.get("overview", "")
    for sk, sv in subs.items():
        combined += " " + sv.get("summary", "")
    for c in chars:
        if c.get("name") in combined:
            involved.append(c)
    return involved


def load_context(state_path, chapter, sub_key):
    """加载写作上下文：上一子结构的末3行+当前子结构规划+人格/情绪/文风约束"""
    sp = Path(state_path)
    if not sp.exists():
        print(f"[错误] state 文件不存在: {state_path}")
        sys.exit(1)

    data = json.loads(sp.read_text(encoding="utf-8-sig"))

    # 查找当前章节
    ch_info = None
    for ch in data.get("chapters", []):
        if ch["id"] == chapter:
            ch_info = ch
            break

    if not ch_info:
        print(f"[错误] 章节 {chapter} 未找到")
        sys.exit(1)

    # 验证子结构已注册
    subs = ch_info.get("sub_structures", {})
    if sub_key not in subs:
        print(f"[阻断] {chapter}{sub_key} 未注册，拒绝加载上下文")
        print(f"[提示] 先运行 plan-chapter 注册子结构")
        sys.exit(1)

    # ── 串行阻断：上一子结构未标记完成时强制走 write-sub ──
    sub_keys = sorted(subs.keys())
    current_idx = sub_keys.index(sub_key) if sub_key in sub_keys else -1
    if current_idx > 0:
        prev_key = sub_keys[current_idx - 1]
        prev_status = subs[prev_key].get("status", "pending")
        if prev_status != "completed":
            prev_title = subs[prev_key].get("title", prev_key)
            print(f"[HOOK-BLOCK] 上一子结构 {chapter}{prev_key}《{prev_title}》未标记完成（status={prev_status}）")
            print(f"[要求] 子结构写作必须串行，请先完成上一子结构的 state 标记：")
            print(f"  cat chapters/{chapter}/{prev_key}.txt | python novel_workflow_engine.py write-sub \\")
            print(f"    \"{state_path}\" {chapter} {prev_key}")
            print(f"[完成后] 重新运行 context_loader 即可继续")
            sys.exit(1)

    # 查找上一个已完成的子结构（取末3行作为上文）
    prev_lines = []
    if current_idx > 0:
        prev_key = sub_keys[current_idx - 1]
        prev_file = Path(sp.parent) / "chapters" / chapter / f"{prev_key}.txt"
        if prev_file.exists():
            lines = prev_file.read_text(encoding="utf-8-sig").strip().split("\n")
            prev_text = [l for l in lines if not l.strip().startswith(f"{chapter}")]
            prev_lines = prev_text[-3:] if len(prev_text) >= 3 else prev_text

    # ── [硬性] 字数约束（从子结构 word_count_target 读取，无需硬编码）──
    LENGTH_LABELS = {"short": "短篇", "medium": "中篇", "long": "长篇"}
    length = data.get("meta", {}).get("length", "")
    length_label = LENGTH_LABELS.get(length, length)
    sub_target = subs[sub_key].get("word_count_target", {})
    word_count_note = ""
    if sub_target and sub_target.get("min") and sub_target.get("max"):
        lo, hi, check_hi = sub_target["min"], sub_target["max"], sub_target.get("check_max", int(sub_target["max"] * 1.15))
        word_count_note = f"  篇幅: {length_label}\n  每子结构字数范围: {lo}-{hi}（校验上浮至 {check_hi}）"
    else:
        word_count_note = f"  篇幅: {length_label}（未设定字数目标，请运行 plan-chapter 更新）"

    # ── 输出标准上下文 ──
    print(f"{'='*50}")
    print(f"[上下文] {chapter}{sub_key}")
    print(f"[章节概述] {ch_info.get('overview', '')}")
    print(f"[子结构规划] title={subs[sub_key].get('title','')}")
    print(f"[子结构概述] {subs[sub_key].get('summary','')}")
    print(f"{_format_emotions(subs[sub_key])}")
    if prev_lines:
        print(f"[上一子结构末3行]:")
        for l in prev_lines:
            print(f"  | {l}")
    print(f"{'='*50}")
    # 字数约束单独分段输出，确保 LLM 看到
    print(f"\n{'='*50}")
    print(f"[硬性] 字数约束")
    print(f"{'='*50}")
    print(word_count_note)
    print(f"  提示: 以叙事单位自然结束为准，不强行撑到目标")
    print(f"{'='*50}\n")

    # ── [硬性] 已出场关键人物（登场即累加，不按章节过滤）──
    char_entries = []
    for c in data.get("characters", []):
        fa = c.get("first_appearance", "")
        if not fa:
            continue
        role = c.get("role", "")
        func = c.get("function", "")
        label = f"{c['name']}({role})" if role else c['name']
        if func:
            char_entries.append(f"  {label}: {func}")
        else:
            char_entries.append(f"  {label}: [提示] 未填写 function")
    if char_entries:
        print(f"{'='*50}")
        print(f"[硬性] 已出场关键人物")
        print(f"{'='*50}")
        for line in char_entries:
            print(line)
        print(f"{'='*50}\n")

    # ── [参考] 情绪写作参考（tone 场景词，引导而非判定） ──
    tone = subs[sub_key].get("tone", "")
    if tone:
        tone_kw_map = {
            "紧张": ["脚步声", "围堵", "攥紧", "屏息", "逼近", "昏暗", "颤抖", "冷汗", "心跳", "身后", "不敢动", "停步", "围上来", "三个人", "黑暗", "夜路", "短句", "压迫"],
            "悲伤": ["沉默", "怀念", "叹息", "沉重", "别离", "往事", "难过", "哽咽", "遗物", "远方", "说不出口", "一个人"],
            "愤怒": ["握拳", "砸桌", "低吼", "瞪", "质问", "凭什么", "混蛋", "找死", "忍不住"],
            "温馨": ["微笑", "轻声", "牵", "晚饭", "灯光", "肩膀", "晚安", "相依", "家"],
            "悬疑": ["为什么", "怎么回事", "痕迹", "不对劲", "暗自", "暗中", "视线", "余光"],
            "平静": ["躺着", "闭眼", "呼吸", "均匀", "微风", "寂静", "枕头", "梦"],
            "恐惧": ["后退", "尖叫", "跑", "逃", "拼命", "僵硬", "屏住", "冷汗"],
            "欢乐": ["笑出声", "哈哈", "得意", "轻松", "嬉笑", "嘴", "乐"],
            "疑惑探索": ["好奇", "翻", "查看", "研究", "琢磨", "试验", "对比", "验证", "想不通", "定睛", "端详"],
            "专注": ["专注", "凝视", "目不转睛", "仔细", "认真", "盯着", "埋头", "研读", "一字不漏"],
            "启发": ["原来如此", "明白了", "懂了", "灵感", "窍", "悟", "发现", "意识到", "突然明白"],
            "顿悟": ["豁然", "一下子", "灵光", "开窍", "通透", "醍醐", "秒懂"],
            "沉思": ["沉思", "琢磨", "反复", "深入", "反省", "扪心", "自问", "陷入"],
            "闲适略带好奇": ["闲", "逛", "溜达", "看看", "瞧瞧", "不急", "晃", "好奇", "打量"],
            "理性分析": ["分析", "计算", "判断", "推理", "逻辑", "数据", "参数", "概率", "规律"],
            "希望与使命感": ["希望", "使命", "意义", "值得", "担当", "信念", "信仰", "愿意"],
        }
        tone_words = tone_kw_map.get(tone, [])
        if tone_words:
            print(f"\n{'='*50}")
            print(f"[参考] 情绪写作参考（数据仅供参考）")
            print(f"{'='*50}")
            print(f"  规划情绪: {tone}")
            print(f"  可参考的场景词: {'、'.join(tone_words[:8])}")
            print(f"  提示: 情绪通过场景/动作/对话传达，不依赖直接使用上述词汇")
            print(f"{'='*50}\n")

    # ── [参考] 钩子位建议（is_hook_possible=true 时输出，不阻断） ──
    if subs[sub_key].get("is_hook_possible"):
        # 找下一章标题
        chapters_list = data.get("chapters", [])
        next_ch_title = ""
        for ci, ch in enumerate(chapters_list):
            if ch["id"] == chapter and ci + 1 < len(chapters_list):
                next_ch = chapters_list[ci + 1]
                next_ch_title = f"{next_ch.get('id', '')}: {next_ch.get('title', '')}"
                break
        print(f"\n{'='*50}")
        print(f"[参考] 钩子位建议（不强制）")
        print(f"{'='*50}")
        print(f"  本子结构是本章末子结构，可考虑设为伏笔/悬念/承诺")
        if next_ch_title:
            print(f"  下章: {next_ch_title}")
        print(f"  可选类型:")
        print(f"    - 悬念：留下一个未解答的问题")
        print(f"    - 伏笔：埋设一个日后才揭示的线索")
        print(f"    - 承诺：暗示下一章将有重要发展")
        print(f"  如不设伏笔，请确保本子结构自然收束（非悬停式结尾）")
        print(f"{'='*50}\n")

    # ── [硬性] 人格约束（硬性） ──
    involved = _find_characters_in_chapter(data, chapter, sub_key)
    if involved:
        has_personality = any(c.get("mbti") or c.get("archetype") for c in involved)
        if has_personality:
            print(f"\n{'='*50}")
            print(f"[硬性] 人格约束（硬性）")
            print(f"{'='*50}")
            for c in involved:
                mbti = c.get("mbti", "")
                archetype = c.get("archetype", "")
                if mbti or archetype:
                    parts = []
                    if mbti: parts.append(f"MBTI={mbti}")
                    if archetype: parts.append(f"原型={archetype}")
                    print(f"  {c['name']}: {', '.join(parts)}")
            print(f"  提示: 角色言行必须符合其人格设定")
            print(f"{'='*50}\n")

    # ── [硬性] 文风约束（硬性） ──
    ws = data.get("writing_style", {})
    if ws:
        print(f"\n{'='*50}")
        print(f"[硬性] 文风约束（硬性）")
        print(f"{'='*50}")
        for key, label in [("narrative_voice", "叙事视角"),
                           ("tense", "时态"),
                           ("sentence_preference", "句式偏好"),
                           ("vocabulary_register", "词汇"),
                           ("description_depth", "描写深度"),
                           ("custom_rules", "自定义规则")]:
            val = ws.get(key, "")
            if val:
                print(f"  {label}: {val}")
        print(f"  提示: 全文文风一致，不可偏离")
        print(f"{'='*50}\n")

    # ── [硬性] 署名约束（代码级硬阻断） ──
    sig = data.get("signature", {"enabled": False, "text": ""})
    sig_enabled = sig.get("enabled", False)
    sig_text = sig.get("text", "")
    print(f"\n{'='*50}")
    if sig_enabled:
        print(f"[硬性] 署名约束（硬性）")
        print(f"{'='*50}")
        print(f"  状态: 已开启")
        if sig_text:
            print(f"  署名: {sig_text}")
        print(f"  允许在作品末尾添加署名")
        print(f"  禁止使用自行编造的署名文本（必须 = 配置值）")
    else:
        print(f"[硬性] 署名约束（代码级硬阻断）")
        print(f"{'='*50}")
        print(f"  状态: 已关闭")
        print(f"  禁止在正文中出现任何署名/代名内容")
        print(f"  atomic_writer 代码级阻断，写入即报错")
    print(f"{'='*50}\n")

    # ── [硬性] 收尾命题框（is_ending=true 时追加） ──
    if subs[sub_key].get("is_ending"):
        ending_type = subs[sub_key].get("ending_type", "未指定")
        project = data.get("project", "未知项目")
        core_conflict = data.get("core_conflict", "未知冲突")
        protagonist = data.get("protagonist", "未知主角")
        theme = data.get("theme", "未知主题")

        print(f"\n{'='*50}")
        print(f"[硬性] 收尾约束（硬性）")
        print(f"{'='*50}")
        print(f"  收尾类型: {ending_type}")
        print(f"  {'─'*40}")
        if ending_type == "封闭式":
            print(f"  □ 核心冲突必须落地（起始于: {core_conflict}）")
            print(f"  □ 主角弧必须闭合（起始于: {protagonist}）")
            print(f"  □ 主题必须回扣（{theme}）")
            print(f"  □ 末句用动作收束（推门。/关灯。/转身。）")
        elif ending_type == "开放式":
            print(f"  □ 核心冲突必须有明确结果（起始于: {core_conflict}）")
            print(f"  □ 留白必须服务于主题（{theme}）")
            print(f"  □ 情绪基调必须收敛")
            print(f"  □ 禁止: 未完待续/预知后事如何/一切才刚刚开始")
        elif ending_type == "悬停式":
            print(f"  □ 留下一个具体悬念（必须可命名）")
            print(f"  □ 悬停点必须是节奏最高处")
            print(f"  □ 主角必须有阶段性成长（起始于: {protagonist}）")
            print(f"  □ 情绪必须有明确指向（焦虑/希望/恐惧/期待）")
            print(f"  □ 禁止: 未完待续/一切才刚刚开始")
        else:
            print(f"  ⚠️ 末子结构概述缺少【收尾类型】标签（应为封闭式/开放式/悬停式）")
            print(f"  □ 请修正概述后重新 plan-chapter")
        print(f"  {'─'*40}")
        print(f"  提示: 以上为命题约束，不可偏离")
        print(f"{'='*50}\n")

    # ── [下一步] 下一步命令提示 ──
    print(f"\n{'='*50}")
    print(f"[下一步] 下一步 - 写入命令")
    print(f"{'='*50}")
    print(f"  # 将以下内容通过 stdin 管道写入:")
    print(f"  cat <<'EOF' | python novel_workflow_engine.py write-sub \\")
    print(f"    \"{state_path}\" {chapter} {sub_key}")
    print(f"  L{chapter[1:]} · S{sub_key[1:]}\u300a{subs[sub_key].get('title','')}\u300b")
    print(f"  ...正文内容...")
    print(f"  EOF")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python novel_context_loader.py <state_path> <chapter> <sub_key>")
        sys.exit(1)
    load_context(sys.argv[1], sys.argv[2], sys.argv[3])
