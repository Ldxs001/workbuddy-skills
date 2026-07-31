"""状态管理器 — 会话状态、进度追踪"""
import json
import copy
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
ARCHIVES_DIR = DATA_DIR / "archives" / "sessions"
OUTPUTS_DIR = DATA_DIR / "outputs"


class StateManager:
    def __init__(self, session_id=None):
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

        if session_id:
            self.session_id = session_id
        else:
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.path = SESSIONS_DIR / f"{self.session_id}.json"
        self._state = None

    def init_session(self, config: dict = None):
        self._state = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "config": config or {},
            "outline": {
                "title": "",
                "sections": []
            },
            "user_orders": {},
            "output_file": "",
            "phase": "config",    # config → planning → reviewing → writing → done
        }
        self.save()

    def set_outline(self, outline: dict):
        self._state["outline"] = outline
        self._state["phase"] = "reviewing"
        self.save()

    def set_user_orders(self, orders: dict):
        self._state["user_orders"] = orders
        self.save()

    def set_phase(self, phase: str):
        self._state["phase"] = phase
        self.save()

    def set_output_file(self, path: str):
        self._state["output_file"] = path
        self.save()

    def update_section(self, section_id: str, updates: dict):
        """更新某个 section 或 sub_section 的状态"""
        for s in self._state["outline"].get("sections", []):
            if s["id"] == section_id:
                s.update(updates)
                self.save()
                return
            # 搜子结构
            for ss in s.get("sub_sections", []):
                if ss["id"] == section_id:
                    ss.update(updates)
                    self.save()
                    return
        self.save()

    def get_progress(self) -> dict:
        sections = self._state["outline"].get("sections", [])
        total_sections = len(sections)
        done_sections = sum(1 for s in sections if s.get("status") == "done")

        # 统计子结构粒度
        total_subs = 0
        done_subs = 0
        for s in sections:
            subs = s.get("sub_sections", [])
            if subs:
                total_subs += len(subs)
                done_subs += sum(1 for ss in subs if ss.get("status") == "done")
            else:
                total_subs += 1
                done_subs += 1 if s.get("status") == "done" else 0

        total_words = sum(s.get("actual_word_count", 0) for s in sections)
        return {
            "total": total_subs,
            "done": done_subs,
            "total_sections": total_sections,
            "done_sections": done_sections,
            "total_words": total_words,
            "phase": self._state.get("phase"),
            "title": self._state.get("outline", {}).get("title", ""),
            "status_text": self._state.get("_status_text", "") if self._state.get("phase") in ("writing",) else ""
        }

    def set_status_text(self, text: str):
        """设置当前状态文本（显示在进度条下方）"""
        self._state["_status_text"] = text
        self.save()

    def get_state(self):
        return copy.deepcopy(self._state)

    def load(self, session_id: str = None):
        sid = session_id or self.session_id
        p = SESSIONS_DIR / f"{sid}.json"
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                self._state = json.load(f)
            self.session_id = sid
            self.path = p
        else:
            raise FileNotFoundError(f"Session {sid} 不存在")

    def save(self):
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)
        tmp.replace(self.path)

    def list_sessions(self) -> list[dict]:
        """列出所有活跃和已归档会话"""
        sessions = []
        for is_archived, base_dir in [(False, SESSIONS_DIR), (True, ARCHIVES_DIR)]:
            if not base_dir.is_dir():
                continue
            for p in sorted(base_dir.glob("*.json"), reverse=True):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        s = json.load(f)
                    sessions.append({
                        "id": s.get("session_id", p.stem),
                        "title": s.get("outline", {}).get("title", "未命名"),
                        "phase": s.get("phase", "unknown"),
                        "created_at": s.get("created_at", ""),
                        "active": not is_archived
                    })
                except Exception:
                    pass
        # 按活跃优先、再按时间倒序
        sessions.sort(key=lambda x: (not x["active"], x.get("created_at", "")), reverse=True)
        return sessions

    def archive_session(self, session_id: str) -> bool:
        """归档指定会话：移入 archives/sessions/"""
        try:
            ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
            src = SESSIONS_DIR / f"{session_id}.json"
            if src.exists():
                dst = ARCHIVES_DIR / f"{session_id}.json"
                src.replace(dst)
            return True
        except Exception:
            return False

    def restore_session(self, session_id: str) -> bool:
        """恢复归档会话：移回 sessions/"""
        try:
            SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
            src = ARCHIVES_DIR / f"{session_id}.json"
            if src.exists():
                dst = SESSIONS_DIR / f"{session_id}.json"
                src.replace(dst)
            return True
        except Exception:
            return False

    def delete_session(self, session_id: str) -> bool:
        """永久删除会话（从两种目录中都删除）"""
        try:
            for base_dir in [SESSIONS_DIR, ARCHIVES_DIR]:
                p = base_dir / f"{session_id}.json"
                if p.exists():
                    p.unlink()
            return True
        except Exception:
            return False

    @classmethod
    def check_session_limit(cls, max_sessions: int = 20):
        """检查活跃会话数，超过则归档最旧的非当前会话"""
        sm = cls()
        sessions = sm.list_sessions()
        active = [s for s in sessions if s.get("active")]
        if len(active) > max_sessions:
            # 最旧的（排序已按时间倒序，最后一个最旧）
            oldest = active[-1]
            sm.archive_session(oldest["id"])
