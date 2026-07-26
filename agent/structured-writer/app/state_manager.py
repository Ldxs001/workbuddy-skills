"""状态管理器 — 会话状态、指纹保护、进度追踪"""
import json
import hashlib
import copy
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
OUTPUTS_DIR = DATA_DIR / "outputs"

# 不可变规划字段（修改触发指纹校验）
IMMUTABLE_FIELDS = {
    "outline": {"title"},
    "section": {"id", "title", "subtitle", "summary", "word_count", "is_key"}
}


def _fingerprint(state: dict) -> str:
    """提取规划相关字段的 MD5 指纹"""
    plan_data = {
        "title": state.get("outline", {}).get("title", ""),
        "sections": [
            {k: s.get(k, "") for k in IMMUTABLE_FIELDS["section"]}
            for s in state.get("outline", {}).get("sections", [])
        ]
    }
    raw = json.dumps(plan_data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


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
            "fingerprint": ""
        }
        self.save()

    def set_outline(self, outline: dict):
        self._state["outline"] = outline
        self._state["fingerprint"] = _fingerprint(self._state)
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

    def fingerprint_check(self) -> bool:
        """检查规划字段是否被意外修改"""
        if not self._state.get("fingerprint"):
            return True
        return _fingerprint(self._state) == self._state["fingerprint"]

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
            "status_text": self._state.get("_status_text", "")
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
        sessions = []
        for p in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    s = json.load(f)
                sessions.append({
                    "id": s.get("session_id", p.stem),
                    "title": s.get("outline", {}).get("title", "未命名"),
                    "phase": s.get("phase", "unknown"),
                    "created_at": s.get("created_at", "")
                })
            except Exception:
                pass
        return sessions
