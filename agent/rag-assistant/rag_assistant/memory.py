"""
记忆系统：短期原文 + 压缩摘要 + 知识缺口 + 用户习惯画像
"""
import os
import json
import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class Memory:
    """统一记忆管理"""

    # 短期超过此行数触发压缩
    # 每轮对话=2行(user+assistant)，100行=最近50轮
    COMPRESS_THRESHOLD = 100
    # 压缩时移除的最旧行数，保留最近行数=THRESHOLD - COMPRESS_REMOVE
    COMPRESS_REMOVE = 40

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.memory_dir = os.path.join(data_dir, "memory")
        self.sessions_dir = os.path.join(data_dir, "sessions")
        os.makedirs(self.memory_dir, exist_ok=True)
        os.makedirs(self.sessions_dir, exist_ok=True)

    # ═══════════════ 短期记忆 ═══════════════

    def get_short_term(self, session_id: str = "default") -> str:
        """读取当前 session 的短期记忆"""
        path = os.path.join(self.sessions_dir, f"{session_id}.txt")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except OSError as e:
                logger.error(f"读取短期记忆失败: {e}")
        return ""

    def append_short_term(self, session_id: str, role: str, content: str):
        """追加一条对话到短期记忆"""
        path = os.path.join(self.sessions_dir, f"{session_id}.txt")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 截断超长内容防止文件膨胀
        if len(content) > 2000:
            content = content[:2000] + "..."
        entry = f"[{timestamp}] {role}: {content}\n"
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(entry)
        except OSError as e:
            logger.error(f"写入短期记忆失败: {e}")

    def clear_short_term(self, session_id: str = "default"):
        """清空短期记忆"""
        path = os.path.join(self.sessions_dir, f"{session_id}.txt")
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as e:
            logger.error(f"清空短期记忆失败: {e}")

    def short_term_line_count(self, session_id: str = "default") -> int:
        """返回短期记忆行数（用于判断是否需要压缩）"""
        content = self.get_short_term(session_id)
        return len([l for l in content.split("\n") if l.strip()])

    def pop_oldest_lines(self, session_id: str, n: int = None) -> str:
        """取最旧 n 行做压缩，保留剩余。n 默认 COMPRESS_REMOVE"""
        if n is None:
            n = self.COMPRESS_REMOVE
        """
        从短期记忆中取出最旧的 N 行，返回取出的文本
        剩余部分写回文件
        """
        content = self.get_short_term(session_id)
        lines = content.split("\n")
        kept = lines[n:]
        removed = "\n".join(lines[:n])

        path = os.path.join(self.sessions_dir, f"{session_id}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(kept))
        except OSError as e:
            logger.error(f"截断短期记忆失败: {e}")
            return ""
        return removed

    # ═══════════════ 压缩记忆 ═══════════════

    def needs_compression(self, session_id: str = "default") -> bool:
        """短期记忆是否需要压缩"""
        return self.short_term_line_count(session_id) > self.COMPRESS_THRESHOLD

    def store_compressed(self, session_id: str, summary: str):
        """追加一条压缩摘要"""
        path = os.path.join(self.memory_dir, f"compressed_{session_id}.txt")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}]\n{summary}\n---\n"
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(entry)
        except OSError as e:
            logger.error(f"写入压缩记忆失败: {e}")

    def get_compressed(self, session_id: str = "default", limit: int = 3) -> str:
        """读取最近的压缩摘要"""
        path = os.path.join(self.memory_dir, f"compressed_{session_id}.txt")
        if not os.path.exists(path):
            return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                sections = f.read().strip().split("\n---\n")
            recent = [s.strip() for s in sections if s.strip()][-limit:]
            return "\n\n".join(recent)
        except OSError as e:
            logger.error(f"读取压缩记忆失败: {e}")
            return ""

    # ═══════════════ 知识缺口 ═══════════════

    def record_gap(self, query: str, kb: str = ""):
        """记录一次检索无结果"""
        path = os.path.join(self.memory_dir, "kb_gaps.json")
        try:
            gaps = []
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    gaps = json.load(f)

            # 去重：相同 query 计数 +1
            for g in gaps:
                if g["query"] == query:
                    g["count"] = g.get("count", 0) + 1
                    g["last_seen"] = datetime.now().isoformat()
                    break
            else:
                gaps.append({
                    "query": query,
                    "kb": kb,
                    "count": 1,
                    "first_seen": datetime.now().isoformat(),
                    "last_seen": datetime.now().isoformat(),
                })

            # 只保留最近 200 条
            gaps = gaps[-200:]

            with open(path, "w", encoding="utf-8") as f:
                json.dump(gaps, f, ensure_ascii=False, indent=2)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"记录知识缺口失败: {e}")

    def get_gaps(self, min_count: int = 2) -> list:
        """返回高频知识缺口（用于提示管理员补充资料）"""
        path = os.path.join(self.memory_dir, "kb_gaps.json")
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                gaps = json.load(f)
            return [g for g in gaps if g.get("count", 0) >= min_count]
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"读取知识缺口失败: {e}")
            return []

    # ═══════════════ 用户习惯与性格画像 ═══════════════

    # 人格衰减基数：每次更新时旧值 * DECAY_BASE，新样本加权
    PERSONALITY_DECAY = 0.98

    @staticmethod
    def _classify_sentence(msg: str) -> dict:
        """规则级语言分析：句式 + 语气 + 深度"""
        if not msg:
            return {"sentence_type": "statement", "tone": "neutral", "depth": "shallow"}

        # 句式分类
        sentence_type = "statement"
        has_question_mark = bool(re.search(r'[?？]', msg))
        has_rhetorical = bool(re.search(r'难道|岂|何尝|不是吗|不觉得|不就', msg))
        has_imperative_start = bool(re.match(r'^[请给帮列做写](.{0,20})', msg))
        has_exclamation = bool(re.search(r'[!！]', msg))

        if has_rhetorical or (has_question_mark and re.search(r'吗|呢|难道|岂', msg)):
            sentence_type = "rhetorical"
        elif has_question_mark or re.search(r'什么|怎么|为什么|如何|是否|有没有|多少|哪', msg):
            sentence_type = "question"
        elif has_exclamation or has_imperative_start:
            sentence_type = "imperative"

        # 语气分类
        tone = "neutral"
        if re.search(r'具体|详细|数据|来源|参数|标准|依据|不是|不对|根本|明明|到底|究竟', msg):
            tone = "critical"
        elif re.search(r'好奇|有趣|有意思|原理|机制|本质|本质上是', msg):
            tone = "curious"
        elif re.search(r'呵呵|哈[哈哈]|哦[哦]|就这|就这点|所以呢|然后呢', msg):
            tone = "sarcastic"
        elif len(msg.strip()) <= 8:
            tone = "terse"
        elif re.search(r'非常|太[棒好]|绝对|完全|终于|太好了|太棒了|厉害', msg):
            tone = "enthusiastic"

        # 深度估计
        n = len(msg.strip())
        if n < 10:
            depth = "shallow"
        elif n < 50:
            depth = "medium"
        else:
            depth = "deep"

        return {"sentence_type": sentence_type, "tone": tone, "depth": depth}

    @staticmethod
    def _ocean_delta(msg: str, is_rag: bool, is_chat: bool, is_import: bool,
                     analysis: dict) -> dict:
        """根据单次交互计算 OCEAN 各维度增量（每个维度 -1~+1）"""
        tone = analysis.get("tone", "neutral")
        stype = analysis.get("sentence_type", "statement")
        depth = analysis.get("depth", "shallow")

        d = {"openness": 0.0, "conscientiousness": 0.0,
             "extraversion": 0.0, "agreeableness": 0.0, "neuroticism": 0.0}

        # 从操作类型推断
        if is_rag:
            d["openness"] += 0.3       # 检索行为 = 探索新信息
            d["conscientiousness"] += 0.1
        if is_import:
            d["conscientiousness"] += 0.4   # 导入 = 有条理
        if is_chat:
            d["extraversion"] += 0.2   # 聊天 = 社交意愿

        # 从语气推断
        if tone == "critical":
            d["conscientiousness"] += 0.25  # 追求精确
            d["agreeableness"] -= 0.2       # 对抗性
            d["neuroticism"] += 0.15        # 不满情绪
        elif tone == "curious":
            d["openness"] += 0.3
            d["agreeableness"] += 0.15
        elif tone == "sarcastic":
            d["agreeableness"] -= 0.3
            d["neuroticism"] += 0.2
            d["extraversion"] -= 0.1
        elif tone == "terse":
            d["extraversion"] -= 0.15
            d["conscientiousness"] += 0.1   # 直奔主题
        elif tone == "enthusiastic":
            d["extraversion"] += 0.25
            d["agreeableness"] += 0.15

        # 从句式推断
        if stype == "rhetorical":
            d["neuroticism"] += 0.15
            d["agreeableness"] -= 0.1
        elif stype == "imperative":
            d["conscientiousness"] += 0.1
            d["agreeableness"] -= 0.1

        # 深度
        if depth == "deep":
            d["openness"] += 0.15
            d["conscientiousness"] += 0.2
        elif depth == "shallow":
            d["neuroticism"] += 0.05

        return d

    def record_habit(self, msg: str, is_rag: bool, is_chat: bool, is_import: bool, kb: str = ""):
        """记录用户使用习惯与性格画像"""
        path = os.path.join(self.memory_dir, "user_habits.json")
        try:
            # 默认初始化
            habits = {
                "rag_queries": 0, "chat_messages": 0, "imports": 0,
                "kbs_used": {}, "total": 0,
                "linguistic": {"sentence_type": {}, "tone": {}, "depth": {}, "total_analyzed": 0},
                "personality": {"openness": 0.5, "conscientiousness": 0.5,
                                "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
                "decay_base": self.PERSONALITY_DECAY,
            }
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                # 兼容旧数据：无画像字段时保留旧结构
                for k in habits:
                    if k not in existing:
                        existing[k] = habits[k]
                habits = existing

            # ── 统计计数（原逻辑）──
            habits["total"] = habits.get("total", 0) + 1
            if is_rag:
                habits["rag_queries"] = habits.get("rag_queries", 0) + 1
            if is_chat:
                habits["chat_messages"] = habits.get("chat_messages", 0) + 1
            if is_import:
                habits["imports"] = habits.get("imports", 0) + 1
            if kb:
                kbs = habits.setdefault("kbs_used", {})
                kbs[kb] = kbs.get(kb, 0) + 1

            # 记录最近 5 条提问方式方便分析模式
            recent = habits.setdefault("recent_queries", [])
            if is_rag:
                recent.append(msg[:80])
                habits["recent_queries"] = recent[-5:]

            # ── 语言风格分析（规则级）──
            analysis = self._classify_sentence(msg)
            ling = habits.setdefault("linguistic", {})
            for cat, val in analysis.items():
                bucket = ling.setdefault(cat, {})
                bucket[val] = bucket.get(val, 0) + 1
            ling["total_analyzed"] = ling.get("total_analyzed", 0) + 1

            # ── OCEAN 人格更新（衰减 + 增量）──
            decay = habits.get("decay_base", self.PERSONALITY_DECAY)
            delta = self._ocean_delta(msg, is_rag, is_chat, is_import, analysis)
            personality = habits.setdefault("personality", {})
            for dim in ("openness", "conscientiousness", "extraversion",
                        "agreeableness", "neuroticism"):
                old = personality.get(dim, 0.5)
                # 衰减 + 新样本加权
                new_val = old * decay + delta.get(dim, 0.0) * (1 - decay)
                personality[dim] = max(0.0, min(1.0, new_val))  # 钳制 0-1

            habits["last_active"] = datetime.now().isoformat()

            with open(path, "w", encoding="utf-8") as f:
                json.dump(habits, f, ensure_ascii=False, indent=2)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"记录用户习惯失败: {e}")

    def get_habits(self) -> dict:
        """获取用户习惯摘要"""
        path = os.path.join(self.memory_dir, "user_habits.json")
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"读取用户习惯失败: {e}")
            return {}

    def get_persona(self) -> dict:
        """合成用户画像：语言风格 + 人格 + 使用偏好"""
        habits = self.get_habits()
        if not habits:
            return {}

        ling = habits.get("linguistic", {})
        personality = habits.get("personality", {})
        total_analyzed = ling.get("total_analyzed", 0) or 1  # 防除零

        # 语言风格占比
        def _top_pct(bucket):
            if not bucket:
                return "", 0.0
            top_k = max(bucket, key=bucket.get)
            return top_k, bucket[top_k] / total_analyzed

        top_type, type_pct = _top_pct(ling.get("sentence_type", {}))
        top_tone, tone_pct = _top_pct(ling.get("tone", {}))
        top_depth, depth_pct = _top_pct(ling.get("depth", {}))

        # 人格标签映射
        def _dim_label(dim, val):
            labels = {
                "openness": ("守成型", "探索型")[val > 0.55],
                "conscientiousness": ("随性型", "严谨型")[val > 0.55],
                "extraversion": ("内敛型", "外放型")[val > 0.55],
                "agreeableness": ("对抗型", "亲和型")[val > 0.55],
                "neuroticism": ("稳定型", "敏感型")[val < 0.45],
            }
            return labels.get(dim, "")

        return {
            "linguistic_summary": {
                "dominant_type": top_type,
                "type_ratio": round(type_pct, 2),
                "dominant_tone": top_tone,
                "tone_ratio": round(tone_pct, 2),
                "dominant_depth": top_depth,
                "depth_ratio": round(depth_pct, 2),
            },
            "personality": {dim: round(val, 2) for dim, val in personality.items()},
            "personality_labels": {dim: _dim_label(dim, personality.get(dim, 0.5))
                                   for dim in personality},
            "behavior": {
                "rag_pct": round(habits.get("rag_queries", 0) / max(habits.get("total", 1), 1), 2),
                "chat_pct": round(habits.get("chat_messages", 0) / max(habits.get("total", 1), 1), 2),
                "import_pct": round(habits.get("imports", 0) / max(habits.get("total", 1), 1), 2),
            },
            "total_interactions": habits.get("total", 0),
        }

    def build_persona_context(self) -> str:
        """生成用户画像提示文本（用于拼入 LLM prompt）"""
        persona = self.get_persona()
        if not persona or persona.get("total_interactions", 0) < 3:
            return ""

        ling = persona.get("linguistic_summary", {})
        pl = persona.get("personality_labels", {})
        pv = persona.get("personality", {})
        bhv = persona.get("behavior", {})

        parts = ["【用户习惯画像】"]

        # 语言风格
        stype = ling.get("dominant_type", "")
        tone = ling.get("dominant_tone", "")
        depth = ling.get("dominant_depth", "")
        if stype:
            parts.append(f"语言风格：以{stype}句为主（{ling.get('type_ratio', 0):.0%}），"
                         f"语气偏{tone}（{ling.get('tone_ratio', 0):.0%}），"
                         f"深度以{depth}为主（{ling.get('depth_ratio', 0):.0%}）")

        # 人格
        labels = [v for k, v in pl.items() if v]
        if labels:
            parts.append(f"人格倾向：{'、'.join(labels)}")
        # 人格数值（仅当有明显倾向时）
        notable = []
        for dim, val in pv.items():
            if val > 0.65:
                notable.append(f"{dim}(偏高{val:.2f})")
            elif val < 0.35:
                notable.append(f"{dim}(偏低{val:.2f})")
        if notable:
            parts.append(f"人格细节：{'；'.join(notable)}")

        # 行为偏好
        if bhv.get("rag_pct", 0) > 0.5:
            parts.append("行为偏好：高频使用知识库检索")
        if bhv.get("import_pct", 0) > 0.2:
            parts.append("行为偏好：常导入文档到知识库")

        return "\n".join(parts)

    # ═══════════════ 构建上下文 ═══════════════

    def build_context(self, session_id: str = "default") -> str:
        """构建记忆上下文，拼入 Agent Prompt"""
        parts = []

        # 1. 压缩摘要（历史脉络）
        compressed = self.get_compressed(session_id)
        if compressed:
            parts.append("[历史对话摘要]\n" + compressed)

        # 2. 短期记忆（最近对话）
        short = self.get_short_term(session_id)
        if short.strip():
            parts.append("[当前对话]\n" + short)

        return "\n\n".join(parts)
