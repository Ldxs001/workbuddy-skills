"""
插件基类 — 所有插件必须继承 PluginBase
"""
import abc
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PluginBase(abc.ABC):
    """所有插件的抽象基类"""

    # 由 PluginManager 在注册时自动注入
    name: str = ""
    display_name: str = ""
    data_dir: Path = Path()       # data/plugins/<name>/
    metadata: dict = {}           # plugin.json 完整内容

    # ── 元数据快捷访问 ──

    @property
    def type(self) -> str:
        """input_return | input_output"""
        return self.metadata.get("type", "input_return")

    @property
    def mandatory(self) -> bool:
        return self.metadata.get("mandatory", False)

    @property
    def input_fields(self) -> list:
        return self.metadata.get("input_fields", [])

    @property
    def has_config_ui(self) -> bool:
        return self.metadata.get("has_config_ui", False)

    @property
    def timeout(self) -> int:
        return self.metadata.get("timeout", 15)

    # ── 抽象方法 ──

    @abc.abstractmethod
    async def execute(self, inputs: dict) -> dict:
        """
        插件的唯一执行入口。

        Args:
            inputs: 智能体裁剪后的输入字段
                    （从 6 字段池中按 self.input_fields 选取）

        Returns:
            标准返回格式:
            {
                "type": str,          # markdown / json / csv / plain_text
                "content": str,       # 实际内容
                "priority": int,      # 合并顺序，越大越优先
                "execution_error": str | None  # 失败时填原因，成功为 None
            }
        """
        ...

    def open_config_ui(self):
        """
        可选。has_config_ui=True 时实现。
        插件自行弹出配置界面，可用 HTML/tkinter/Qt/cmd 任何方式。
        """
        pass
