"""
agent_loop.py — ReAct 智能体核心循环

Think → Act → Observe 三步骤循环：
  1. LLM 输出 JSON 格式的动作（工具调用或最终回答）
  2. 执行工具
  3. 观察结果并反馈给 LLM

完全无外部框架依赖，纯 Python + urllib。
"""

import json
import re
import traceback
from typing import Optional

from .agent_config import AgentConfig
from .llm_client import LLMClient, LLMError
from .memory import ConversationMemory, WorkingMemory
from .tool_base import BaseTool, ToolResult


# ---------------------------------------------------------------------------
# ReAct Prompt 模板
# ---------------------------------------------------------------------------
REACT_SYSTEM_PROMPT = """你是一个拥有工具使用能力的 AI 智能体。你的核心任务是：**通过思考 + 调用工具** 来解决用户的问题。

## 行为准则

1. **思考再行动**：每次回复必须先思考，再决定下一步做什么。
2. **工具优先**：需要信息时优先调用工具（RAG搜索、文件读取、网络搜索等），不要猜测。
3. **高效**：一次调用能解决的问题不要分多次。可以从工具结果的上下文中推理出答案。
4. **诚实**：工具没有找到相关信息时，如实告知用户，不要编造。
5. **简洁**：工具调用结果已经显示的内容不要在最终回答中重复。

## 可用工具

{tool_descriptions}

## 输出格式

你必须用 **严格的 JSON 格式** 输出，格式如下：

### 1. 调用工具
```json
{{
  "thought": "我当前的思考...",
  "action": "工具名称",
  "action_input": {{
    "参数名": "参数值"
  }}
}}
```

### 2. 最终回答
```json
{{
  "thought": "我已经有了足够的信息来回答用户的问题。",
  "action": "final_answer",
  "action_input": {{
    "answer": "你的完整回答..."
  }}
}}
```

### 3. 任务完成但需要更多信息
```json
{{
  "thought": "我无法完全回答这个问题，需要用户补充信息。",
  "action": "ask_user",
  "action_input": {{
    "question": "你想问用户的问题..."
  }}
}}
```

## 重要规则

- 一次只输出一个 JSON 块
- JSON 必须合法、完整
- "thought" 字段用中文思考
- 工具名称必须是可用工具列表中的精确名称
- 参数名必须与工具 Schema 中定义的一致
- 不要输出除了 JSON 之外的任何内容（除非是在最终回答中）
- 如果工具返回空结果，尝试换一个工具或换一种搜索方式"""


# ---------------------------------------------------------------------------
# JSON 提取器
# ---------------------------------------------------------------------------
_JSON_PATTERN = re.compile(
    r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL
)
_FALLBACK_PATTERN = re.compile(
    r'\{\s*"thought"\s*:\s*".*?"\s*,\s*"action"\s*:\s*".*?"\s*,\s*"action_input"\s*:\s*\{.*?\}\s*\}', re.DOTALL
)


def _extract_json(text: str) -> Optional[dict]:
    """从 LLM 回复中提取第一个 JSON 对象"""
    # 优先匹配 ```json ... ``` 代码块
    for match in _JSON_PATTERN.finditer(text):
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

    # 回退：裸 JSON 格式
    for match in _FALLBACK_PATTERN.finditer(text):
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            continue

    # 最后尝试：最宽松的 JSON 对象提取
    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict) and "action" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    return None


# ---------------------------------------------------------------------------
# 工具注册表
# ---------------------------------------------------------------------------
class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def register_many(self, tools: list[BaseTool]):
        for t in tools:
            self.register(t)

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_descriptions(self) -> str:
        """返回 ReAct prompt 中的工具描述文本"""
        lines = []
        for tool in self._tools.values():
            lines.append(tool.get_react_description())
        return "\n".join(lines)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# ---------------------------------------------------------------------------
# 智能体循环
# ---------------------------------------------------------------------------
class Agent:
    """
    ReAct 智能体主循环。

    用法:
        agent = Agent(config)
        agent.register_tools([...])
        answer = agent.run("用户的问题")
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm = LLMClient(config)
        self.memory = ConversationMemory(config)
        self.working_memory = WorkingMemory(config)
        self.tools = ToolRegistry()
        self.verbose = config.agent_verbose

    def register_tools(self, tools: list[BaseTool]):
        """注册可用工具"""
        self.tools.register_many(tools)

    def register(self, tool: BaseTool):
        """注册单个工具"""
        self.tools.register(tool)

    # ------------------------------------------------------------------
    # 内部：构建 System Prompt
    # ------------------------------------------------------------------
    def _build_system_prompt(self) -> str:
        tool_desc = self.tools.get_descriptions()
        working_mem = self.working_memory.to_text()

        prompt = REACT_SYSTEM_PROMPT.format(tool_descriptions=tool_desc)

        if working_mem.strip():
            prompt += f"\n\n## 工作记忆\n{working_mem}"

        return prompt

    # ------------------------------------------------------------------
    # 内部：格式化对话历史
    # ------------------------------------------------------------------
    def _build_messages(self, user_input: str) -> list[dict]:
        system_prompt = self._build_system_prompt()

        messages = [{"role": "system", "content": system_prompt}]

        # 添加上下文
        ctx = self.working_memory.data.get("facts", [])
        if ctx:
            messages.append({
                "role": "system",
                "content": f"记住以下关键事实:\n" + "\n".join(f"• {f}" for f in ctx[-5:]),
            })

        # 添加对话历史（最后 N 轮）
        for msg in self.memory.get_recent(10):
            messages.append(msg)

        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

    # ------------------------------------------------------------------
    # 内部：执行工具调用
    # ------------------------------------------------------------------
    def _execute_action(self, action: str, action_input: dict) -> ToolResult:
        tool = self.tools.get(action)
        if tool is None:
            return ToolResult(False, error=f"未知工具: {action}。可用工具: {', '.join(t.name for t in self.tools.list())}")

        if self.verbose:
            print(f"  🛠️ 调用工具: {action}({json.dumps(action_input, ensure_ascii=False)})")

        try:
            result = tool.execute(**action_input)
        except TypeError as e:
            # 参数不匹配，尝试给个友好的错误
            return ToolResult(False, error=f"工具「{action}」参数错误: {e}。正确的参数: {json.dumps(tool.get_schema(), ensure_ascii=False)}")
        except Exception as e:
            return ToolResult(False, error=f"工具「{action}」执行异常: {e}\n{traceback.format_exc()}")

        if self.verbose:
            status = "✅ 成功" if result.success else f"❌ 失败: {result.error[:100]}"
            print(f"  {status}")
            if result.success and result.output:
                preview = result.output[:200].replace("\n", " ")[:200]
                print(f"  输出预览: {preview}...")

        return result

    # ------------------------------------------------------------------
    # 内部：单步推理
    # ------------------------------------------------------------------
    def _step(self, messages: list[dict], step_num: int) -> tuple[Optional[dict], str]:
        """执行一步 ReAct 循环：LLM 输出 → 解析 JSON"""
        if self.verbose:
            print(f"\n  🧠 思考步骤 #{step_num}...")

        try:
            response = self.llm.chat(
                messages,
                temperature=0.1,  # 工具调用用低温度提高稳定性
                max_tokens=2048,
            )
        except LLMError as e:
            return None, f"LLM 调用失败: {e}"

        if self.verbose:
            # 只打印 thought
            parsed = _extract_json(response)
            if parsed and "thought" in parsed:
                print(f"  💭 {parsed['thought']}")

        parsed = _extract_json(response)
        if parsed is None:
            # 解析失败，给 LLM 反馈并让重试
            feedback = (
                f"你的回复无法被解析为有效的 JSON 格式。请严格按照以下格式输出：\n\n"
                f"```json\n{{\n  \"thought\": \"你的思考\",\n  \"action\": \"工具名或 final_answer\",\n  \"action_input\": {{...}}\n}}\n```\n\n"
                f"你刚才的输出为:\n{response[:500]}"
            )
            return None, feedback

        return parsed, response

    # ------------------------------------------------------------------
    # 运行智能体（一次对话）
    # ------------------------------------------------------------------
    def run(
        self,
        user_input: str,
        max_steps: Optional[int] = None,
    ) -> str:
        """
        运行智能体，返回最终回答。

        Parameters
        ----------
        user_input : str
            用户输入
        max_steps : int, optional
            覆盖最大步数

        Returns
        -------
        str : 最终回答
        """
        max_steps = max_steps or self.config.agent_max_steps
        max_retries = self.config.agent_max_retries
        stop_on_error = self.config.agent_stop_on_tool_error

        # 构建初始消息
        messages = self._build_messages(user_input)
        self.memory.add_user(user_input)

        # 日志记录
        trajectory = []

        for step in range(1, max_steps + 1):
            # ---------- Think ----------
            action_data, raw_response = self._step(messages, step)

            if action_data is None:
                # JSON 解析失败，加入反馈消息让 LLM 重试
                messages.append({"role": "assistant", "content": raw_response or ""})
                messages.append({"role": "user", "content": raw_response})
                continue

            action = action_data.get("action", "")
            action_input = action_data.get("action_input", {})
            thought = action_data.get("thought", "")

            # 保存思考轨迹
            trajectory.append({"step": step, "thought": thought, "action": action})

            # ---------- 最终回答 ----------
            if action == "final_answer":
                answer = action_input.get("answer", "") if isinstance(action_input, dict) else str(action_input)
                self.memory.add_assistant(answer)

                # 提取关键事实存到工作记忆
                self.working_memory.add_fact(f"Q: {user_input[:100]}... A: {answer[:100]}...")

                if self.verbose:
                    print(f"\n  ✅ 最终回答 ({step} 步)")

                return answer

            # ---------- 询问用户 ----------
            if action == "ask_user":
                question = action_input.get("question", "需要你补充一些信息") if isinstance(action_input, dict) else str(action_input)
                answer = f"[需要用户补充] {question}"
                self.memory.add_assistant(answer)
                return answer

            # ---------- 调用工具 ----------
            result = self._execute_action(action, action_input)

            # 工具执行失败的决策
            if not result.success:
                if stop_on_error:
                    error_msg = f"工具「{action}」执行失败（stop_on_error=True）: {result.error}"
                    self.memory.add_assistant(error_msg)
                    return error_msg

                # 把错误信息加入对话，让 LLM 决定是重试还是换方式
                observation = result.to_observation()
                messages.append({
                    "role": "assistant",
                    "content": json.dumps(action_data, ensure_ascii=False),
                })
                messages.append({
                    "role": "user",
                    "content": f"工具执行结果:\n{observation}\n\n请根据这个结果决定下一步。如果是参数错误，修正后重试；如果是工具不可用，尝试换一个工具或告知用户。",
                })
                continue

            # ---------- Observe ----------
            observation = result.to_observation()
            messages.append({
                "role": "assistant",
                "content": json.dumps(action_data, ensure_ascii=False),
            })
            messages.append({
                "role": "user",
                "content": f"工具执行结果:\n{observation}",
            })

        # ---------- 超步数 ----------
        fallback = f"已达到最大推理步数 ({max_steps})，无法完成。最后轨迹: {json.dumps(trajectory[-3:], ensure_ascii=False)}"
        self.memory.add_assistant(fallback)
        return fallback

    # ------------------------------------------------------------------
    # 重置会话
    # ------------------------------------------------------------------
    def reset(self):
        """重置会话记忆，保留工作记忆"""
        self.memory.clear()

    def reset_all(self):
        """完全重置（含工作记忆）"""
        self.memory.clear()
        self.working_memory = WorkingMemory(self.config)
