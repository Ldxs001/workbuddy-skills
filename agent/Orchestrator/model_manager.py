"""
model_manager.py — 统一模型管理器

跨技能统一管理所有 AI 模型的生命周期：
  - 发现: 自动扫描 LM Studio / novel-weaver / local-rag-builder / HF cache
  - 加载: 根据模型类型自动选择加载器
  - 设备: GPU/CPU 仲裁，避免显存冲突
  - 生命周期: 懒加载 + 卸载 + 优先级调度

支持的模型类型:
  - gguf:              llama-cpp-python Llama (GGUF 格式大语言模型)
  - sentence_transformer:  sentence-transformers (嵌入/语义模型)
  - causal_lm:         transformers AutoModelForCausalLM (文本生成)
  - reranker:          transformers AutoModelForSequenceClassification (重排序)
"""

import glob
import json
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# ======================================================================
# 模型类型枚举
# ======================================================================
class ModelType(Enum):
    GGUF = "gguf"
    SENTENCE_TRANSFORMER = "sentence_transformer"
    CAUSAL_LM = "causal_lm"
    RERANKER = "reranker"
    UNKNOWN = "unknown"

    @classmethod
    def from_path(cls, path: str) -> "ModelType":
        p = path.lower()
        if p.endswith(".gguf"):
            return cls.GGUF
        # safetensors index 文件
        if os.path.basename(p) == "model.safetensors.index.json":
            return cls.CAUSAL_LM
        # config.json + 无 .gguf → 可能是 HF 格式
        bn = os.path.basename(p)
        if bn == "config.json":
            return cls.UNKNOWN  # 需要进一步判断
        return cls.UNKNOWN


# ======================================================================
# 模型元数据
# ======================================================================
@dataclass
class ModelInfo:
    """单个模型元数据"""
    name: str               # 显示名称 (e.g., "qwen3.6-35b-a3b-Q4_K_M")
    path: str               # 文件/目录绝对路径
    model_type: ModelType   # 类型
    size_gb: float = 0      # 文件大小(GB)
    source: str = ""        # 来源 (lm-studio / novel-weaver / rag / hf-cache / user)
    vram_estimate_gb: float = 0  # 加载后显存估算
    loader: str = ""        # 使用的加载器
    is_llm: bool = True     # 是否是独立大语言模型（过滤 mmproj 等辅助文件）
    priority: int = 1       # GPU 优先级: 10=大LLM, 5=中型, 1=小嵌入

    def __post_init__(self):
        # 过滤非 LLM 辅助文件
        bn = os.path.basename(self.path).lower() if os.path.isfile(self.path) else self.name.lower()
        if self.model_type == ModelType.GGUF and (
            bn.startswith("mmproj") or "mmproj" in bn
        ):
            self.is_llm = False

        # 【必须先算大小，再设优先级】
        if self.size_gb <= 0 and os.path.exists(self.path):
            try:
                if os.path.isfile(self.path):
                    self.size_gb = os.path.getsize(self.path) / (1024**3)
                elif os.path.isdir(self.path):
                    total = 0
                    for dirpath, _, filenames in os.walk(self.path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            try:
                                total += os.path.getsize(fp)
                            except OSError:
                                pass
                    self.size_gb = total / (1024**3)
            except OSError:
                pass

        # 估算 VRAM
        if self.model_type == ModelType.GGUF:
            # GGUF: VRAM ≈ n_gpu_layers/total_layers * size
            # 保守估 30%
            self.vram_estimate_gb = self.size_gb * 0.3
        elif self.model_type == ModelType.CAUSAL_LM:
            # transformers: 4bit ≈ size/4, fp16 ≈ size/2
            self.vram_estimate_gb = self.size_gb * 0.5
        elif self.model_type == ModelType.SENTENCE_TRANSFORMER:
            self.vram_estimate_gb = min(self.size_gb * 1.5, 1.0)  # 小模型
        elif self.model_type == ModelType.RERANKER:
            self.vram_estimate_gb = min(self.size_gb * 1.5, 2.0)

        # 加载器
        if self.model_type == ModelType.GGUF:
            self.loader = "llama_cpp.Llama"
        elif self.model_type == ModelType.SENTENCE_TRANSFORMER:
            self.loader = "sentence_transformers.SentenceTransformer"
        elif self.model_type == ModelType.CAUSAL_LM:
            self.loader = "transformers.AutoModelForCausalLM"
        elif self.model_type == ModelType.RERANKER:
            self.loader = "transformers.AutoModelForSequenceClassification"

        # 自动设定优先级（必须放在 size_gb/vram 计算之后）
        if self.model_type == ModelType.GGUF and self.size_gb > 5:
            self.priority = 10       # 大 LLM → 独占 GPU
        elif self.model_type == ModelType.RERANKER:
            self.priority = 5        # 重排序 → 次优先
        elif self.model_type == ModelType.CAUSAL_LM and self.size_gb < 5:
            self.priority = 3        # 小因果模型 → 低优先
        elif self.model_type == ModelType.SENTENCE_TRANSFORMER:
            self.priority = 1        # 嵌入模型 → CPU 优先


# ======================================================================
# 系统级 GPU 信息
# ======================================================================
def _detect_vram() -> dict:
    """检测 GPU 显存信息"""
    result = {"total_gb": 0, "free_gb": 0, "used_gb": 0, "available": False}
    try:
        import subprocess
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.free,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            parts = r.stdout.strip().split(", ")
            if len(parts) == 3 and all(p.strip().isdigit() for p in parts):
                total, free, used = [int(p.strip()) / 1024 for p in parts]
                result.update({"total_gb": total, "free_gb": free,
                               "used_gb": used, "available": True})
    except Exception:
        pass
    return result


# ======================================================================
# 已知模型扫描路径
# ======================================================================
KNOWN_SEARCH_PATHS = {
    "lm-studio": os.path.expanduser("~/.lmstudio/models/**/*.gguf"),
    "novel-weaver": os.path.join(
        os.path.expanduser("~/.workbuddy/skills/.standardization/novel-weaver/models/"),
        "**/*"),
    "rag-embeddings": os.path.join(
        os.path.expanduser("~/.workbuddy/skills/local-rag-builder/data/models/"),
        "**/*"),
    "hf-cache": os.path.join(
        os.path.expanduser("~/.cache/huggingface/hub/"),
        "**/*"),
}

# ---------------------------------------------------------------
# 已知模型的快速索引（避免全盘扫描）
# ---------------------------------------------------------------
KNOWN_MODELS = [
    # === local_agent / qwen ===
    ModelInfo(
        name="qwen3.6-35b-a3b-Q4_K_M",
        path=os.path.expanduser(
            "~/.lmstudio/models/lmstudio-community/"
            "Qwen3.6-35B-A3B-GGUF/Qwen3.6-35B-A3B-Q4_K_M.gguf"
        ),
        model_type=ModelType.GGUF,
        source="lm-studio",
    ),
    # === novel-weaver ===
    ModelInfo(
        name="bge-small-zh-v1.5",
        path=os.path.join(
            os.path.expanduser("~/.workbuddy/skills/.standardization/novel-weaver/models/"),
            "bge-small-zh"
        ),
        model_type=ModelType.SENTENCE_TRANSFORMER,
        source="novel-weaver",
    ),
    ModelInfo(
        name="DeepSeek-R1-Distill-Qwen-1.5B",
        path=os.path.join(
            os.path.expanduser("~/.workbuddy/skills/.standardization/novel-weaver/models/"),
            "ds-r1-distill-qwen-1.5b"
        ),
        model_type=ModelType.CAUSAL_LM,
        source="novel-weaver",
    ),
]


# ======================================================================
# ModelManager 核心
# ======================================================================
class ModelManager:
    """
    统一模型管理器。

    用法:
        mgr = ModelManager()

        # 发现所有模型
        mgr.discover()

        # 按类型筛选
        gguf_models = mgr.list(type_filter="gguf")

        # 加载模型
        llm = mgr.load("qwen3.6-35b-a3b-Q4_K_M", device="gpu")

        # 使用
        response = llm.create_chat_completion(messages=[...])

        # 卸载（释放显存）
        mgr.unload("qwen3.6-35b-a3b-Q4_K_M")
        mgr.unload_all()
    """

    def __init__(self):
        self._registry: dict[str, ModelInfo] = {}     # name → ModelInfo
        self._loaded: dict[str, Any] = {}             # name → loaded instance
        self._device_map: dict[str, str] = {}         # name → "gpu" | "cpu"
        self._vram = _detect_vram()
        self._vram_reserved = 0.0                     # 已分配显存追踪

    # ------------------------------------------------------------------
    # 模型发现
    # ------------------------------------------------------------------
    def discover(self, force_rescan: bool = False) -> list[ModelInfo]:
        """
        扫描所有已知路径，注册发现的模型。
        返回新发现的模型列表。
        """
        found = []

        # 1. 先注册已知模型 (快速路径)
        for info in KNOWN_MODELS:
            if info.name not in self._registry and os.path.exists(info.path):
                self._registry[info.name] = info
                found.append(info)

        # 2. 扫描文件系统
        if force_rescan:
            for source, pattern in KNOWN_SEARCH_PATHS.items():
                for filepath in glob.glob(pattern, recursive=True):
                    if not os.path.isfile(filepath):
                        continue
                    info = self._classify(filepath, source)
                    if info and info.name not in self._registry:
                        self._registry[info.name] = info
                        found.append(info)

        return found

    def _classify(self, path: str, source: str) -> Optional[ModelInfo]:
        """根据文件路径分类模型"""
        p = path.lower()

        # GGUF
        if p.endswith(".gguf"):
            name = os.path.splitext(os.path.basename(path))[0]
            return ModelInfo(name=name, path=path, model_type=ModelType.GGUF, source=source)

        # 目录级别的 HF 模型
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "config.json")):
            name = os.path.basename(path)
            # 尝试判断类型
            config_path = os.path.join(path, "config.json")
            try:
                with open(config_path) as f:
                    cfg = json.load(f)
                arch = cfg.get("architectures", [""])[0] if cfg.get("architectures") else ""
                if "ForCausalLM" in arch:
                    mtype = ModelType.CAUSAL_LM
                elif "ForSequenceClassification" in arch:
                    mtype = ModelType.RERANKER
                else:
                    mtype = ModelType.SENTENCE_TRANSFORMER
            except Exception:
                mtype = ModelType.UNKNOWN

            return ModelInfo(name=name, path=path, model_type=mtype, source=source)

        return None

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def get(self, name: str) -> Optional[ModelInfo]:
        return self._registry.get(name)

    def list(self, type_filter: Optional[str] = None,
             source_filter: Optional[str] = None,
             loaded_only: bool = False,
             llm_only: bool = True) -> list[ModelInfo]:
        """列出模型，支持筛选"""
        results = []
        for info in self._registry.values():
            if type_filter and info.model_type.value != type_filter:
                continue
            if source_filter and info.source != source_filter:
                continue
            if loaded_only and info.name not in self._loaded:
                continue
            if llm_only and not info.is_llm:
                continue
            results.append(info)
        return sorted(results, key=lambda x: -x.size_gb)

    def summary(self) -> str:
        """打印模型概览"""
        lines = ["模型管理器概览:"]
        # 按类型分组
        by_type: dict[str, list[ModelInfo]] = {}
        for info in self._registry.values():
            by_type.setdefault(info.model_type.value, []).append(info)

        for mtype, infos in sorted(by_type.items()):
            lines.append(f"\n  [{mtype}]")
            for info in infos:
                loaded = "✅" if info.name in self._loaded else "  "
                lines.append(f"  {loaded} {info.name}  ({info.size_gb:.1f}GB, {info.source})")

        lines.append(f"\n  总计: {len(self._registry)} 个模型")
        lines.append(f"  已加载: {len(self._loaded)} 个")
        if self._vram["available"]:
            lines.append(f"  显存: {self._vram['used_gb']:.1f}/{self._vram['total_gb']:.0f}GB 已用, "
                         f"{self._vram['free_gb']:.1f}GB 空闲")
        return "\n".join(lines)

    def model_stats(self) -> dict:
        """返回结构化统计"""
        return {
            "total": len(self._registry),
            "loaded": len(self._loaded),
            "by_type": {t: len([m for m in self._registry.values()
                                if m.model_type.value == t])
                        for t in set(m.model_type.value for m in self._registry.values())},
            "vram": self._vram,
        }

    # ------------------------------------------------------------------
    # 设备仲裁
    # ------------------------------------------------------------------
    def _pick_device(self, info: ModelInfo, preferred: str = "auto") -> tuple[str, str]:
        """
        决定模型加载到哪个设备。

        优先级调度策略:
          - 大 LLM (priority 10) → 优先 GPU
          - 小模型 (priority < 10) → 如果大 LLM 已占 GPU，自动 CPU
          - 用户强制指定则覆盖

        Parameters
        ----------
        info : ModelInfo
        preferred : str
            "auto" | "gpu" | "cpu"

        Returns
        -------
        (device, reason) : (str, str)
        """
        VRAM_MARGIN = 1.5  # GB 余量

        if preferred == "cpu":
            return "cpu", "用户指定 CPU"

        if not self._vram["available"] or self._vram["total_gb"] == 0:
            return "cpu", "未检测到 GPU"

        # 检查是否有更高优先级的模型已占 GPU
        higher_priority_loaded = any(
            self._registry.get(n) and self._registry[n].priority > info.priority
            and self._device_map.get(n) == "gpu"
            for n in self._loaded
        )

        if higher_priority_loaded:
            return "cpu", f"GPU 已被更高优先级模型占用，回退 CPU"

        # 如果已有一个同优先级模型在 GPU 上，检查 VRAM 剩余
        same_priority_on_gpu = [
            n for n in self._loaded
            if self._registry.get(n)
            and self._registry[n].priority == info.priority
            and self._device_map.get(n) == "gpu"
        ]

        if same_priority_on_gpu:
            # 已有一个同优先级模型在用 GPU，算剩余
            used = sum(
                self._registry[n].vram_estimate_gb for n in same_priority_on_gpu
            )
            free = self._vram["free_gb"] - used
            needed = info.vram_estimate_gb + VRAM_MARGIN
            if free >= needed:
                return "gpu", f"同优先级模型共存，剩余 {free:.1f}GB >= {needed:.1f}GB"
            else:
                return "cpu", f"显存不足共存 ({free:.1f}GB < {needed:.1f}GB)"

        # auto: 空闲显存判断
        needed = info.vram_estimate_gb + VRAM_MARGIN
        if self._vram["free_gb"] >= needed:
            return "gpu", f"显存充足 ({self._vram['free_gb']:.1f}GB >= {needed:.1f}GB)"
        else:
            return "cpu", (f"显存不足 ({self._vram['free_gb']:.1f}GB < {needed:.1f}GB), "
                           f"回退 CPU")

    # ------------------------------------------------------------------
    # 加载 & 卸载
    # ------------------------------------------------------------------
    def load(self, name: str, device: str = "auto",
             **kwargs) -> Any:
        """
        加载模型。

        Parameters
        ----------
        name : str
            模型名称
        device : str
            "auto" | "gpu" | "cpu"
        **kwargs
            传递给加载器的额外参数

        Returns
        -------
        model_instance : 模型实例
        """
        if name in self._loaded:
            return self._loaded[name]

        info = self._registry.get(name)
        if info is None:
            # 尝试先扫描
            self.discover()
            info = self._registry.get(name)
        if info is None:
            raise KeyError(f"未知模型: {name}。可用: {', '.join(self._registry.keys())}")

        actual_device, reason = self._pick_device(info, preferred=device)
        self._device_map[name] = actual_device

        if info.loader.startswith("llama_cpp"):
            instance = self._load_gguf(info, actual_device, **kwargs)
        elif info.loader.startswith("sentence_transformers"):
            instance = self._load_sentence_transformer(info, actual_device, **kwargs)
        elif info.loader.startswith("transformers.AutoModelForCausalLM"):
            instance = self._load_causal_lm(info, actual_device, **kwargs)
        elif info.loader.startswith("transformers.AutoModelForSequenceClassification"):
            instance = self._load_reranker(info, actual_device, **kwargs)
        else:
            raise ValueError(f"不支持的加载器: {info.loader}")

        self._loaded[name] = instance
        if actual_device == "gpu":
            self._vram_reserved += info.vram_estimate_gb

        return instance

    def _load_gguf(self, info: ModelInfo, device: str, **kwargs) -> Any:
        """加载 GGUF 模型"""
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError("需要安装 llama-cpp-python: pip install llama-cpp-python")

        n_gpu_layers = -1 if device == "gpu" else 0
        # GPU 时根据剩余显存计算可卸载层数
        if device == "gpu" and self._vram["available"]:
            free_gb = self._vram["free_gb"]
            usable = max(0, free_gb - 1.0)
            fraction = usable / info.size_gb
            estimated_layers = max(1, int(48 * fraction))  # 典型 48 层
            n_gpu_layers = min(estimated_layers, 48)

        return Llama(
            model_path=info.path,
            n_ctx=kwargs.get("n_ctx", 8192),
            n_threads=kwargs.get("n_threads", os.cpu_count() or 4),
            n_gpu_layers=n_gpu_layers,
            offload_kqv=kwargs.get("offload_kqv", True) if device == "gpu" else False,
            flash_attn=kwargs.get("flash_attn", True),
            verbose=kwargs.get("verbose", False),
        )

    def _load_sentence_transformer(self, info: ModelInfo, device: str, **kwargs) -> Any:
        """加载 sentence-transformers 模型"""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("需要安装 sentence-transformers")

        # sentence-transformers 内部自己管理设备
        return SentenceTransformer(
            info.path,
            trust_remote_code=True,
        )

    def _load_causal_lm(self, info: ModelInfo, device: str, **kwargs) -> Any:
        """加载 transformers 因果语言模型"""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError:
            raise ImportError("需要安装 transformers + torch")

        device_map = "cuda" if device == "gpu" else "cpu"
        torch_dtype = kwargs.get("torch_dtype", "auto")

        tokenizer = AutoTokenizer.from_pretrained(info.path, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            info.path,
            trust_remote_code=True,
            torch_dtype=torch_dtype,
            device_map=device_map,
            low_cpu_mem_usage=True,
        )
        return {"model": model, "tokenizer": tokenizer}

    def _load_reranker(self, info: ModelInfo, device: str, **kwargs) -> Any:
        """加载 reranker 模型"""
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError:
            raise ImportError("需要安装 transformers + torch")

        device_map = "cuda" if device == "gpu" else "cpu"
        tokenizer = AutoTokenizer.from_pretrained(info.path, trust_remote_code=True)
        model = AutoModelForSequenceClassification.from_pretrained(
            info.path,
            trust_remote_code=True,
            device_map=device_map,
        )
        return {"model": model, "tokenizer": tokenizer}

    def unload(self, name: str):
        """卸载指定模型，释放内存"""
        if name not in self._loaded:
            return
        instance = self._loaded.pop(name)
        info = self._registry.get(name)
        if info and self._device_map.get(name) == "gpu":
            self._vram_reserved -= info.vram_estimate_gb
        self._device_map.pop(name, None)
        # 显式删除引用 + 垃圾回收提示
        del instance
        import gc; gc.collect()
        if self._vram["available"]:
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

    def unload_all(self):
        """卸载所有已加载模型"""
        for name in list(self._loaded.keys()):
            self.unload(name)

    def is_loaded(self, name: str) -> bool:
        return name in self._loaded

    # ------------------------------------------------------------------
    # 上下文管理器（临时加载-使用-卸载）
    # ------------------------------------------------------------------
    def using(self, name: str, device: str = "auto", **kwargs):
        """
        上下文管理器: with mgr.using('model') as m: ...

        进入时加载，退出时自动卸载。
        """
        return _ModelContext(self, name, device, **kwargs)


class _ModelContext:
    """ModelManager 的上下文管理器"""

    def __init__(self, mgr: ModelManager, name: str, device: str = "auto", **kwargs):
        self.mgr = mgr
        self.name = name
        self.device = device
        self.kwargs = kwargs
        self.instance = None

    def __enter__(self):
        self.instance = self.mgr.load(self.name, device=self.device, **self.kwargs)
        return self.instance

    def __exit__(self, *args):
        self.mgr.unload(self.name)
        self.instance = None


# ======================================================================
# 单例
# ======================================================================
_manager_instance: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """获取全局 ModelManager 单例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ModelManager()
        _manager_instance.discover()
    return _manager_instance
