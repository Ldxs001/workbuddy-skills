"""
chain_model.py — Skill Pipeline 数据模型
"""

import json, uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class SkillInfo:
    """扫描到的技能元数据"""
    name: str                    # slug/目录名
    display_name: str = ""       # 用户可读名
    description: str = ""
    version: str = ""
    author: str = ""
    tags: list = field(default_factory=list)
    triggers: list = field(default_factory=list)
    path: str = ""               # 技能目录绝对路径
    permission_weight: str = ""
    sensitive_access: bool = False
    critical_write: bool = False
    error: str = ""              # 解析失败时记录错误

    @property
    def label(self) -> str:
        """左栏显示的文本"""
        dn = self.display_name or self.name
        ver = f"v{self.version}" if self.version else ""
        return f"{dn}  {ver}" if ver else dn

    @property
    def sublabel(self) -> str:
        """左栏次要文本"""
        return (self.description or "").strip()[:60]


@dataclass
class PipelineNode:
    """流水线中的一个节点"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    skill_name: str = ""          # 技能 slug
    display_name: str = ""        # 显示用的名字
    mode: str = "seq"             # seq | par | loop
    children: list = field(default_factory=list)  # PipelineNode 列表
    loop_start: Optional[int] = None
    loop_end: Optional[int] = None
    loop_times: Optional[int] = None
    input_text: str = ""          # 用户对该步骤的输入

    def to_dict(self) -> dict:
        d = {"id": self.id, "skill_name": self.skill_name,
             "display_name": self.display_name, "mode": self.mode,
             "input_text": self.input_text,
             "loop_start": self.loop_start, "loop_end": self.loop_end,
             "loop_times": self.loop_times}
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "PipelineNode":
        children = [cls.from_dict(c) for c in d.get("children", [])]
        return cls(
            id=d.get("id", uuid.uuid4().hex[:8]),
            skill_name=d.get("skill_name", ""),
            display_name=d.get("display_name", ""),
            mode=d.get("mode", "seq"),
            children=children,
            loop_start=d.get("loop_start"),
            loop_end=d.get("loop_end"),
            loop_times=d.get("loop_times"),
            input_text=d.get("input_text", ""),
        )


@dataclass
class Pipeline:
    """完整流水线"""
    name: str = "未命名"
    nodes: list = field(default_factory=list)  # PipelineNode 列表
    optimize: bool = False        # 是否启用 skill-sub 优化
    semantic_split: bool = False  # 是否启用语义拆分
    triphasic: bool = False       # 是否启用三步执行（自审+自循环）
    created: str = ""
    updated: str = ""

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().strftime("%Y-%m-%d %H:%M")
        if not self.updated:
            self.updated = self.created

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "optimize": self.optimize,
            "semantic_split": self.semantic_split,
            "triphasic": self.triphasic,
            "created": self.created,
            "updated": self.updated,
            "nodes": [n.to_dict() for n in self.nodes],
        }

    def to_json(self, indent=2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, d: dict) -> "Pipeline":
        nodes = [PipelineNode.from_dict(n) for n in d.get("nodes", [])]
        return cls(
            name=d.get("name", "未命名"),
            nodes=nodes,
            optimize=d.get("optimize", False),
            semantic_split=d.get("semantic_split", False),
            triphasic=d.get("triphasic", False),
            created=d.get("created", ""),
            updated=d.get("updated", ""),
        )

    @classmethod
    def from_json(cls, text: str) -> "Pipeline":
        return cls.from_dict(json.loads(text))


def flatten_nodes(nodes: list[PipelineNode]) -> list[PipelineNode]:
    """将嵌套的节点展平为执行顺序列表，并行/循环展开为标记"""
    result = []
    for n in nodes:
        if n.mode == "par":
            result.append(n)  # 并行容器本身作为标记
            result.extend(flatten_nodes(n.children))
        elif n.mode == "loop":
            result.append(n)
            result.extend(flatten_nodes(n.children))
        else:
            result.append(n)
    return result
