"""
local_agent — 基于本地 LLM 的 Python 智能体系统 / Skill Pipeline Orchestrator

LLM 后端可选:
  - LLMClient: 通过 LM Studio / Ollama API 调用（零依赖）
  - DirectLLMClient: 直接 Python 加载 GGUF（需 llama-cpp-python）

统一模型管理:
  - ModelManager: 跨技能发现 / 加载 / 卸载 / GPU 仲裁

Skill Pipeline Orchestrator:
  - Pipeline / PipelineNode: 流水线数据模型
  - SkillInfo: 技能元数据
  - scan_skills: 扫描技能目录
  - execute_pipeline: 执行流水线
  - Orchestrator: tkinter 编排 GUI
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

__version__ = "1.1.0"
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
