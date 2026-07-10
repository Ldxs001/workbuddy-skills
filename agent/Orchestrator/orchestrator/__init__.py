"""
Orchestrator v2 — 链驱动智能体系统

核心工作方式：链为主体，对话为附属。
1. 编排 Pipeline（技能链，含 seq/par/loop 多步骤）
2. 对话选择链 + 下达任务
3. 链驱动执行（skill-sub 优化 / 直接执行）
4. 逐步执行直到输出

LLM 后端可选:
  - LLMClient: 通过 LM Studio / Ollama API 调用（零依赖）
  - DirectLLMClient: 直接 Python 加载 GGUF（需 llama-cpp-python）

统一模型管理:
  - ModelManager: 跨技能发现 / 加载 / 卸载 / GPU 仲裁
"""

from .agent_config import AgentConfig
from .agent_loop import Agent, ToolRegistry
from .llm_client import LLMClient
from .memory import ConversationMemory, WorkingMemory
from .tool_base import BaseTool, ToolResult
from .tools import LoadSkillTool, ReadFileTool, WriteFileTool, ListDirTool
from .tools import WebFetchTool, WebSearchTool, PythonExecuteTool

try:
    from .direct_llm_client import DirectLLMClient
except ImportError:
    DirectLLMClient = None

from .model_manager import ModelManager, ModelInfo, ModelType, get_model_manager

# === Skill Pipeline Orchestrator ===
from .chain_model import SkillInfo, Pipeline, PipelineNode
from .skill_scanner import scan_skills, search_skills
from .chain_engine import execute_pipeline, execute_node

__version__ = "2.0.0"
__all__ = [
    "AgentConfig", "Agent", "ToolRegistry",
    "LLMClient", "DirectLLMClient",
    "ConversationMemory", "WorkingMemory",
    "BaseTool", "ToolResult",
    "ModelManager", "ModelInfo", "ModelType", "get_model_manager",
    "LoadSkillTool", "ReadFileTool", "WriteFileTool", "ListDirTool",
    "WebFetchTool", "WebSearchTool", "PythonExecuteTool",
    # Pipeline Orchestrator
    "SkillInfo", "Pipeline", "PipelineNode",
    "scan_skills", "search_skills",
    "execute_pipeline", "execute_node",
]
