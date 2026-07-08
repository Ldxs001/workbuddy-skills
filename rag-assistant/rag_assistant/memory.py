"""
记忆系统：短期原文 + 压缩摘要 + 知识缺口
"""
import os
import json
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

    # ═══════════════ 用户习惯 ═══════════════

    def record_habit(self, msg: str, is_rag: bool, is_chat: bool, is_import: bool, kb: str = ""):
        """记录用户使用习惯"""
        path = os.path.join(self.memory_dir, "user_habits.json")
        try:
            habits = {"rag_queries": 0, "chat_messages": 0, "imports": 0,
                      "kbs_used": {}, "total": 0}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    habits = json.load(f)

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
