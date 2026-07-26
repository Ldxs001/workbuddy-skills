"""
插件管理器 — 负责插件的发现、注册、生命周期、安全管控
"""
import asyncio
import importlib
import importlib.util
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

from .base import PluginBase

logger = logging.getLogger(__name__)

# ── 6 字段池（智能体→插件的全部可给信息） ──
FIELD_POOL = {"question", "answer_draft", "thinking", "rag_context", "session_id", "plugin_dir"}

# ── 内置插件目录 ──
BUILTIN_DIR = Path(__file__).parent / "builtin"


class PluginManager:
    """插件管理器"""

    def __init__(self, data_dir: str, plugin_config_path: str = None):
        self.data_dir = Path(data_dir)
        self.plugins_dir = self.data_dir / "plugins"          # 用户安装插件
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        # 配置路径
        self.config_path = Path(plugin_config_path or self.data_dir / "config" / "plugin_config.json")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 运行时状态
        self._plugins: dict[str, PluginBase] = {}       # name → instance
        self._metadata: dict[str, dict] = {}            # name → raw metadata
        self._enabled: set = set()                      # 已启用的插件名
        self._failure_count: dict[str, int] = {}        # 连续失败计数

        # SM3 函数引用（延迟加载）
        self._sm3 = None

    # ═══════════════ 初始化与发现 ═══════════════

    def discover_and_register(self):
        """扫描所有插件目录并注册"""
        # 1. 扫描内置插件
        if BUILTIN_DIR.exists():
            self._scan_directory(BUILTIN_DIR, builtin=True)

        # 2. 扫描用户安装插件
        if self.plugins_dir.exists():
            self._scan_directory(self.plugins_dir, builtin=False)

        # 3. 加载启用状态
        self._load_config()

        logger.info(f"插件系统初始化完成：共 {len(self._plugins)} 个插件，"
                     f"已启用 {len(self._enabled)} 个")

    def _scan_directory(self, directory: Path, builtin: bool):
        """扫描单个目录下的所有插件子目录"""
        for entry in sorted(directory.iterdir()):
            if not entry.is_dir():
                continue
            plugin_json = entry / "plugin.json"
            if not plugin_json.exists():
                continue
            try:
                self._register_plugin(entry, plugin_json, builtin)
            except Exception as e:
                logger.error(f"插件注册失败 [{entry.name}]: {e}")

    def _register_plugin(self, plugin_dir: Path, plugin_json: Path, builtin: bool):
        """注册单个插件"""
        # 1. 读取元数据
        with open(plugin_json, "r", encoding="utf-8") as f:
            meta = json.load(f)

        name = meta.get("name", "")
        if not name:
            raise ValueError(f"插件缺少 name 字段: {plugin_json}")

        # 2. 验证必填字段
        self._validate_metadata(meta)

        # 3. 签名校验（非强制，sm3_hash 为空则跳过）
        if meta.get("sm3_hash"):
            self._verify_signature(plugin_dir, meta)

        # 4. 动态加载插件类（确保项目根在 sys.path 中）
        # 向上查找：从插件目录回溯，找到 rag_assistant/ 的父目录作为项目根
        _project_root = plugin_dir
        while _project_root.parent != _project_root:
            if (_project_root / "rag_assistant").is_dir():
                _project_root = _project_root
                break
            _project_root = _project_root.parent
        if str(_project_root) not in sys.path:
            sys.path.insert(0, str(_project_root))

        plugin_module_name = meta.get("module", f"plugin_{name}")
        plugin_class_name = meta.get("class", "Plugin")

        # 尝试导入
        spec = importlib.util.spec_from_file_location(
            plugin_module_name,
            plugin_dir / f"{plugin_module_name}.py"
        )
        if not spec or not spec.loader:
            # 回退：尝试 plugin.py
            spec = importlib.util.spec_from_file_location(
                plugin_module_name,
                plugin_dir / "plugin.py"
            )
        if not spec or not spec.loader:
            raise ImportError(f"无法找到插件主文件: {plugin_dir}")

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        plugin_class = getattr(mod, plugin_class_name, None)
        if not plugin_class or not issubclass(plugin_class, PluginBase):
            raise TypeError(f"插件 {name} 未定义继承 PluginBase 的 {plugin_class_name} 类")

        # 5. 实例化并注入
        instance = plugin_class()
        instance.name = name
        instance.display_name = meta.get("display_name", name)
        instance.data_dir = self.data_dir / "plugins" / name
        instance.metadata = meta

        # 如果是内置插件，创建数据目录
        instance.data_dir.mkdir(parents=True, exist_ok=True)

        # 6. 注册
        self._plugins[name] = instance
        self._metadata[name] = meta
        logger.info(f"插件已注册: {name} v{meta.get('version', '?')} "
                     f"{'(内置)' if builtin else '(用户安装)'}")

    def _validate_metadata(self, meta: dict):
        """校验插件元数据必填字段"""
        required = ["name", "display_name", "version", "type", "mandatory", "input_fields"]
        for field in required:
            if field not in meta:
                raise ValueError(f"插件元数据缺少必填字段: {field}")

        if meta["type"] not in ("input_return", "input_output"):
            raise ValueError(f"插件 type 必须为 input_return 或 input_output: {meta['type']}")

        # 校验 input_fields 是否在字段池内
        for f in meta["input_fields"]:
            if f not in FIELD_POOL:
                raise ValueError(f"插件声明了非法字段 '{f}'，可用字段: {sorted(FIELD_POOL)}")

    def _verify_signature(self, plugin_dir: Path, meta: dict):
        """SM3 签名验证"""
        self._ensure_sm3()
        expected = meta["sm3_hash"]
        actual = self._compute_hash(plugin_dir)
        if actual != expected:
            logger.warning(f"插件签名不匹配 [{meta['name']}]，"
                           f"期望 {expected[:16]}... 实际 {actual[:16]}...")

    def _ensure_sm3(self):
        """延迟加载 SM3 函数"""
        if self._sm3 is not None:
            return
        try:
            # 尝试从项目导入（运行时的完整路径）
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from engine.knowledge_base_manager import sm3 as _sm3_func
            self._sm3 = _sm3_func
        except ImportError:
            # 回退：直接用 hashlib
            import hashlib
            self._sm3 = lambda data: hashlib.new('sm3', data).hexdigest()

    @staticmethod
    def _compute_hash(plugin_dir: Path) -> str:
        """计算插件目录所有代码文件的 SM3 哈希

        注意：计算 plugin.json 时会先去掉 sm3_hash 字段，
        与 tools/sign_plugin.py 的计算方式保持一致。
        """
        import hashlib
        import json

        files = sorted(
            p for p in plugin_dir.rglob("*")
            if p.suffix == ".py" or p.name == "plugin.json"
        )
        # 排除 data/、__pycache__、.git、*.pyc
        files = [
            p for p in files
            if not any(part.startswith((".", "__")) for part in p.relative_to(plugin_dir).parts)
            and p.suffix != ".pyc"
        ]
        hasher = hashlib.new('sm3')
        for f in files:
            if f.name == "plugin.json":
                # 去掉 sm3_hash 再参与哈希计算
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    data.pop("sm3_hash", None)
                    cleaned = json.dumps(data, ensure_ascii=False, sort_keys=True)
                    hasher.update(cleaned.encode("utf-8"))
                except Exception:
                    hasher.update(f.read_bytes())
            else:
                hasher.update(f.read_bytes())
        return hasher.hexdigest()

    # ═══════════════ 配置持久化 ═══════════════

    def _load_config(self):
        """从配置文件加载启用状态"""
        if not self.config_path.exists():
            # 初次使用，不启用任何插件
            self._save_config()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            enabled = cfg.get("enabled_plugins", [])
            # 只保留已注册的插件
            self._enabled = {name for name in enabled if name in self._plugins}
        except Exception as e:
            logger.error(f"加载插件配置失败: {e}")
            self._enabled = set()

    def _save_config(self):
        """持久化插件配置"""
        cfg = {
            "enabled_plugins": sorted(self._enabled),
            "plugin_settings": {},
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    # ═══════════════ 公共 API ═══════════════

    def list_plugins(self) -> list[dict]:
        """返回所有插件的基本信息（给 Web UI）"""
        result = []
        for name, meta in self._metadata.items():
            result.append({
                "name": name,
                "display_name": meta.get("display_name", name),
                "version": meta.get("version", ""),
                "type": meta.get("type", ""),
                "mandatory": meta.get("mandatory", False),
                "description": meta.get("description", ""),
                "has_config_ui": meta.get("has_config_ui", False),
                "author": meta.get("author", ""),
                "enabled": name in self._enabled,
                "builtin": meta.get("builtin", False),
            })
        return result

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """按名称获取插件实例"""
        return self._plugins.get(name)

    def enable_plugin(self, name: str) -> bool:
        """启用插件（下一轮对话生效）"""
        if name not in self._plugins:
            return False
        self._enabled.add(name)
        self._save_config()
        logger.info(f"插件已启用: {name}")
        return True

    def disable_plugin(self, name: str) -> bool:
        """禁用插件（下一轮对话生效）"""
        self._enabled.discard(name)
        self._save_config()
        logger.info(f"插件已禁用: {name}")
        return True

    def is_enabled(self, name: str) -> bool:
        """检查插件是否已启用"""
        return name in self._enabled

    # ═══════════════ 钩子执行 ═══════════════

    def run_before_response(self, inputs: dict) -> str:
        """
        before_response 阶段：调用所有已启用的 input_return 插件。
        返回注入的额外上下文（多个插件结果按 priority 合并）。
        """
        injected_parts = []

        for name in sorted(self._enabled):
            plugin = self._plugins.get(name)
            if not plugin or plugin.type != "input_return":
                continue

            # 字段裁剪
            plugin_inputs = {k: v for k, v in inputs.items() if k in plugin.input_fields}

            result = self._safe_execute(plugin, plugin_inputs)
            if result is None:
                continue  # 失败已记录

            # 校验输出格式
            out_type = result.get("type", "plain_text")
            content = result.get("content", "")

            if out_type not in ("markdown", "json", "csv", "plain_text"):
                logger.warning(f"插件 {name} 返回了非法 type '{out_type}'，已丢弃")
                continue

            priority = result.get("priority", 0)

            # 格式化片段（带来源标签）
            snippet = content.strip()
            if snippet:
                tag = plugin.display_name or name
                snippet = f"【{tag}】\n{snippet}"
                injected_parts.append((priority, snippet))

        if not injected_parts:
            return ""

        # 按 priority 降序排列
        injected_parts.sort(key=lambda x: -x[0])
        combined = "\n\n---\n\n".join(part for _, part in injected_parts)
        return combined

    def run_after_response(self, inputs: dict):
        """
        after_response 阶段：调用所有已启用的 input_output 插件。
        不阻塞主流程，失败仅记录日志。
        """
        for name in sorted(self._enabled):
            plugin = self._plugins.get(name)
            if not plugin or plugin.type != "input_output":
                continue

            plugin_inputs = {k: v for k, v in inputs.items() if k in plugin.input_fields}
            result = self._safe_execute(plugin, plugin_inputs)

            if result is None:
                error_msg = f"{plugin.display_name}调用失败"
            elif result.get("execution_error"):
                error_msg = f"{plugin.display_name}调用失败：{result['execution_error']}"
            else:
                error_msg = ""

            if error_msg:
                logger.warning(error_msg)

    def _safe_execute(self, plugin: PluginBase, inputs: dict) -> Optional[dict]:
        """安全执行插件调用：超时 + 异常捕获 + 熔断"""
        name = plugin.name
        timeout = plugin.timeout

        # 熔断检查
        if self._failure_count.get(name, 0) >= 3:
            logger.warning(f"插件 {name} 连续失败 3 次，自动禁用")
            self.disable_plugin(name)
            return None

        try:
            start = time.time()
            # 异步执行带超时
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                coro = plugin.execute(inputs)
                result = loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
            except asyncio.TimeoutError:
                raise TimeoutError(f"执行超时 ({timeout}s)")
            finally:
                loop.close()

            elapsed = time.time() - start
            logger.info(f"插件 {name} 执行完成 ({elapsed:.2f}s)")

            # 成功 → 重置失败计数
            self._failure_count[name] = 0
            result["execution_time_ms"] = int(elapsed * 1000)
            return result

        except Exception as e:
            elapsed = time.time() - start if 'start' in locals() else 0
            logger.error(f"插件 {name} 执行失败 ({elapsed:.2f}s): {e}")

            # 累加失败计数
            self._failure_count[name] = self._failure_count.get(name, 0) + 1

            return {
                "type": "plain_text",
                "content": "",
                "priority": 0,
                "execution_time_ms": int(elapsed * 1000),
                "execution_error": str(e),
            }
