"""
direct_llm_client.py — 直接 Python 加载本地模型（GPU/CPU 分摊）

通过 llama-cpp-python 直接加载 GGUF 模型，无需 LM Studio / Ollama。

核心特性:
  - GPU/CPU 分层卸载: n_gpu_layers 自动适配 8GB 显存
  - MoE 模型优化: 针对 qwen3.6-35b-a3b 等 MoE 架构特化
  - OOM 保护: 自动降级 n_gpu_layers
  - 接口兼容: 继承 LLMClient，Agent 无需改动

依赖安装:
  pip install llama-cpp-python
  # 如需 CUDA 加速（推荐）:
  # CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python
  # 或预编译 wheel:
  # pip install llama-cpp-python --prefer-binary --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124
"""

import json
import os
import subprocess
import sys
from typing import Optional

from .agent_config import AgentConfig
from .llm_client import LLMClient, LLMError, LLMConnectionError


# ======================================================================
# GGUF 模型自动发现
# ======================================================================

GGUF_SEARCH_PATHS = [
    os.path.expanduser("~/.lmstudio/models/**/*.gguf"),     # LM Studio 缓存
    os.path.expanduser("~/models/**/*.gguf"),               # ~/models/
    os.path.expanduser("~/*.gguf"),                         # ~/ 根目录
]

# 已知你的模型路径（加速查找）:
# ~/.lmstudio/models/lmstudio-community/Qwen3.6-35B-A3B-GGUF/Qwen3.6-35B-A3B-Q4_K_M.gguf

# 推荐模型: qwen3.6-35b-a3b GGUF Q4_K_M
RECOMMENDED_MODEL = {
    "name": "qwen3.6-35b-a3b-Q4_K_M",
    "hf_repo": "Qwen/Qwen3-35B-A3B-GGUF",
    "hf_file": "qwen3-35b-a3b-q4_k_m.gguf",
    "size_gb": 20,
    "description": "Qwen3.6 MoE 35B (3B activated) Q4_K_M 量化",
    "vram_gb": 8,  # 推荐 GPU 显存
}


def find_gguf_files() -> list[str]:
    """搜索系统上已有的 GGUF 文件（递归）"""
    import glob
    found = []
    for pattern in GGUF_SEARCH_PATHS:
        found.extend(glob.glob(pattern, recursive=True))
    # 也搜一下当前目录
    cwd_gguf = glob.glob("**/*.gguf", recursive=True)
    found.extend(cwd_gguf)
    # 去重
    return list(dict.fromkeys(found))


def detect_vram_gb() -> float:
    """检测可用 GPU 显存（GB）"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if lines and lines[0].strip().isdigit():
                free_mb = int(lines[0].strip())
                return free_mb / 1024
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    # 回退: Python 尝试 pynvml (如有)
    try:
        from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetMemoryInfo
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(0)
        info = nvmlDeviceGetMemoryInfo(handle)
        return info.free / (1024 ** 3)
    except ImportError:
        pass
    return 0  # 未知


def estimate_gpu_layers(vram_gb: float, model_size_gb: float, layers_total: int) -> int:
    """
    根据可用显存估算可卸载的 GPU 层数。

    Parameters
    ----------
    vram_gb : float
        可用显存 (GB)
    model_size_gb : float
        模型文件大小 (GB)
    layers_total : int
        模型总层数

    Returns
    -------
    int : 建议的 n_gpu_layers 值
    """
    if vram_gb <= 0 or model_size_gb <= 0:
        return 0

    # 每层约占总大小的比例
    # MoE 模型: 每层占比 ≈ 1/layers_total
    # 留 1GB 余量给 KV cache 和其他开销
    usable = max(0, vram_gb - 1.5)
    fraction = usable / model_size_gb
    estimated = int(layers_total * fraction)

    # 边界保护
    estimated = max(0, min(estimated, layers_total))
    return estimated


# ======================================================================
# DirectLLMClient
# ======================================================================

class DirectLLMClient(LLMClient):
    """
    直接加载本地 GGUF 模型的 LLM 客户端。

    GPU/CPU 分摊策略:
      - 自动搜索已有 GGUF 文件
      - 自动检测可用显存
      - 自动计算最优 n_gpu_layers
      - OOM 时自动降级重试

    配置新增字段 (agent_config.json):
      "direct_llm": {
          "model_path": "auto",        # GGUF 路径 / "auto" 自动搜索
          "n_gpu_layers": -1,          # -1=自动, 0=CPU only, N=前N层卸载GPU
          "n_ctx": 8192,               # 上下文窗口
          "n_threads": 0,              # CPU 线程数 (0=auto)
          "offload_kqv": true,         # K/Q/V 也卸载到 GPU
          "flash_attn": true,          # Flash Attention (需支持)
          "verbose": false,
          "model_search_paths": []     # 额外搜索路径
      }
    """

    def __init__(self, config: AgentConfig):
        # 不调 super().__init__，因为不走 HTTP
        self.config = config
        self.base_url = "direct://local"  # 标记为直接加载模式
        self.api_key = ""
        self.model = config.llm_model
        self.temperature = config.llm_temperature
        self.max_tokens = config.llm_max_tokens
        self.top_p = config.llm_top_p

        # direct_llm 专属配置
        dl = config.data.get("direct_llm", {})
        self.model_path = dl.get("model_path", "auto")
        self._requested_gpu_layers = dl.get("n_gpu_layers", -1)
        self.n_ctx = dl.get("n_ctx", 8192)
        self.n_threads = dl.get("n_threads", 0)
        self.offload_kqv = dl.get("offload_kqv", True)
        self.flash_attn = dl.get("flash_attn", True)
        self.verbose = dl.get("verbose", False)
        self.extra_paths = dl.get("model_search_paths", [])

        # 内部状态
        self._llama = None
        self._actual_gpu_layers = 0

    # ------------------------------------------------------------------
    # 模型加载
    # ------------------------------------------------------------------
    def _resolve_model_path(self) -> str:
        """定位 GGUF 模型文件路径"""
        if self.model_path and self.model_path != "auto":
            if os.path.exists(self.model_path):
                return self.model_path
            raise FileNotFoundError(f"指定的模型路径不存在: {self.model_path}")

        # 自动搜索
        candidates = find_gguf_files()
        if self.extra_paths:
            import glob
            for p in self.extra_paths:
                candidates.extend(glob.glob(p))
        candidates = list(dict.fromkeys(candidates))

        if not candidates:
            raise FileNotFoundError(
                f"未找到 GGUF 模型文件。\n"
                f"请从 HuggingFace 下载 {RECOMMENDED_MODEL['name']}:\n"
                f"  huggingface-cli download {RECOMMENDED_MODEL['hf_repo']} {RECOMMENDED_MODEL['hf_file']} --local-dir ./models\n\n"
                f"或将 GGUF 文件放在以下路径之一:\n"
                f"  {chr(10).join('  - ' + p for p in GGUF_SEARCH_PATHS)}"
            )

        # 优先选最大的（最有可能是目标模型）
        candidates.sort(key=lambda p: os.path.getsize(p) if os.path.isfile(p) else 0, reverse=True)
        chosen = candidates[0]
        size_gb = os.path.getsize(chosen) / (1024**3) if os.path.isfile(chosen) else 0
        print(f"  自动选择模型: {chosen} ({size_gb:.1f} GB)")
        return chosen

    def _calc_gpu_layers(self, model_path: str) -> tuple[int, str]:
        """
        计算 GPU 层数。返回 (n_gpu_layers, reason)

        策略:
          - 用户显式指定 >0 → 直接用
          - 用户指定 -1 → 自动计算
          - 用户指定 0 → CPU only
        """
        if self._requested_gpu_layers > 0:
            return self._requested_gpu_layers, "用户指定"

        if self._requested_gpu_layers == 0:
            return 0, "用户指定 CPU only"

        # -1: 自动计算
        vram_free = detect_vram_gb()
        model_size = os.path.getsize(model_path) / (1024**3) if os.path.isfile(model_path) else 20

        # MoE 模型典型层数: qwen3 MoE ~48 层
        # 不同模型层数不同，这里用保守估计
        # 实际上 llama.cpp 会自行处理，这里只是估算启动值
        estimated_layers_total = 48

        if vram_free <= 0:
            # 无法检测显存，保守给 0
            return 0, "无法检测显存，回退 CPU only"

        # 可用显存 ≈ LM Studio 退出后释放的空间
        # 当前 LM Studio 占 ~7GB，退出后可释放
        # 但用户可能不想退出 LM Studio，用剩余 ~1GB
        available = min(vram_free, model_size * 0.3)  # 保守: 最多放 30% 到 GPU

        if available < 1:
            reason = f"显存不足 ({vram_free:.1f}GB free)，回退 CPU only"
            return 0, reason

        layers = estimate_gpu_layers(available, model_size, estimated_layers_total)
        layers = max(0, layers)
        reason = f"自动: {available:.1f}GB 显存 / {model_size:.1f}GB 模型 ≈ {layers}/{estimated_layers_total} 层"

        # 如果 LM Studio 在跑，提示用户退出以释放显存
        if vram_free < 3:
            reason += "（提示: 关闭 LM Studio 可释放 ~7GB 显存）"

        return layers, reason

    def _ensure_loaded(self):
        """确保模型已加载"""
        if self._llama is not None:
            return

        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "需要安装 llama-cpp-python:\n"
                "  # 基础安装 (CPU):\n"
                "  pip install llama-cpp-python\n\n"
                "  # CUDA 加速 (推荐 RTX 4060):\n"
                "  CMAKE_ARGS=\"-DGGML_CUDA=on\" pip install llama-cpp-python\n"
                "  # 或预编译 wheel:\n"
                "  pip install llama-cpp-python --prefer-binary "
                "--extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124"
            )

        # 定位模型
        model_path = self._resolve_model_path()
        model_size = os.path.getsize(model_path) / (1024**3)

        # 计算 GPU 层数
        n_gpu_layers, reason = self._calc_gpu_layers(model_path)
        self._actual_gpu_layers = n_gpu_layers

        if n_gpu_layers > 0:
            print(f"  🎯 GPU 卸载: {n_gpu_layers} 层 ({reason})")
        else:
            print(f"  💻 CPU only: {reason}")

        # 计算 CPU 线程数
        if self.n_threads <= 0:
            try:
                self.n_threads = os.cpu_count() or 4
            except:
                self.n_threads = 4

        print(f"  加载模型: {model_path} ({model_size:.1f} GB)")
        print(f"  上下文: {self.n_ctx} tokens | 线程: {self.n_threads}")

        try:
            self._llama = Llama(
                model_path=model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=n_gpu_layers,
                offload_kqv=self.offload_kqv,
                flash_attn=self.flash_attn,
                verbose=self.verbose,
                # MoE 优化
                no_mmap=False,  # 允许 pagefile 交换
                # 内存控制
                tensor_split=None,
            )
            print(f"  ✅ 模型加载成功")
        except RuntimeError as e:
            err_str = str(e).lower()
            if "cuda" in err_str or "memory" in err_str or "cublas" in err_str:
                # OOM: 降级重试
                if n_gpu_layers > 0:
                    fallback = max(0, n_gpu_layers // 2)
                    print(f"  ⚠️ GPU OOM，降级到 {fallback} 层重试...")
                    try:
                        self._llama = Llama(
                            model_path=model_path,
                            n_ctx=min(self.n_ctx, 4096),  # 缩小上下文
                            n_threads=self.n_threads,
                            n_gpu_layers=fallback,
                            offload_kqv=False,
                            flash_attn=self.flash_attn,
                            verbose=self.verbose,
                        )
                        self._actual_gpu_layers = fallback
                        print(f"  ✅ 降级后加载成功 ({fallback} GPU 层)")
                        return
                    except Exception as e2:
                        # 终极降级: CPU only
                        print(f"  ⚠️ 降级仍失败，回退 CPU only...")
                        self._llama = Llama(
                            model_path=model_path,
                            n_ctx=self.n_ctx,
                            n_threads=self.n_threads,
                            n_gpu_layers=0,
                            verbose=self.verbose,
                        )
                        self._actual_gpu_layers = 0
                        print(f"  ✅ CPU only 加载成功")
                        return
            raise RuntimeError(f"模型加载失败: {e}")

    # ------------------------------------------------------------------
    # LLMClient 接口
    # ------------------------------------------------------------------
    def check_connection(self) -> tuple[bool, str]:
        """检测模型是否可加载"""
        try:
            self._ensure_loaded()
            return True, f"模型已加载 (GPU: {self._actual_gpu_layers} 层, 上下文: {self.n_ctx})"
        except (ImportError, FileNotFoundError, RuntimeError) as e:
            return False, str(e)

    def chat(self, messages: list[dict], **kwargs) -> str:
        """调用本地模型推理"""
        self._ensure_loaded()

        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        try:
            response = self._llama.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=kwargs.get("top_p", self.top_p),
                stop=kwargs.get("stop", None),
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            raise LLMError(f"本地模型推理失败: {e}")

    def chat_stream(self, messages: list[dict], **kwargs):
        """流式推理"""
        self._ensure_loaded()

        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        try:
            stream = self._llama.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=kwargs.get("top_p", self.top_p),
                stream=True,
            )
            for chunk in stream:
                delta = chunk["choices"][0]["delta"]
                if "content" in delta:
                    yield delta["content"]
        except Exception as e:
            raise LLMError(f"本地模型流式推理失败: {e}")

    def ask(self, system: str, user: str, **kwargs) -> str:
        return self.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], **kwargs)

    @property
    def gpu_info(self) -> str:
        """返回 GPU 使用情况描述"""
        if self._actual_gpu_layers > 0:
            return f"GPU {self._actual_gpu_layers} 层 / CPU {self.n_threads} 线程"
        return f"CPU only ({self.n_threads} 线程)"


# ======================================================================
# 快捷入口
# ======================================================================
def download_model(quant: str = "Q4_K_M"):
    """
    下载推荐的 qwen 模型。

    Usage:
        python -c "from direct_llm_client import download_model; download_model()"
    """
    repo = RECOMMENDED_MODEL["hf_repo"]
    file = RECOMMENDED_MODEL["hf_file"]
    print(f"下载 {repo}/{file} ...")
    print(f"  量化: {quant}")
    print(f"  大小: ~{RECOMMENDED_MODEL['size_gb']} GB")
    print()
    print("方式1: huggingface-cli")
    print(f"  huggingface-cli download {repo} {file} --local-dir ./models")
    print()
    print("方式2: 直接下载")
    print(f"  https://huggingface.co/{repo}/resolve/main/{file}")
    print()
    print("下载后放在 ./models/ 或 ~/models/ 下，智能体会自动识别")


# ======================================================================
# GPU 自动检测 + 安装
# ======================================================================
def check_gpu_llama() -> tuple[bool, str]:
    """
    检测 llama-cpp-python 是否已安装并支持 GPU。

    Returns
    -------
    (ok, msg)
        (True, "CUDA 版本")  → 直接用
        (False, "原因")       → 需要安装
    """
    try:
        import llama_cpp.llama_cpp as lcpp
        if hasattr(lcpp, "ggml_backend_cuda_init"):
            return True, f"llama-cpp-python {llama_cpp.__version__} (CUDA)"
        else:
            return False, "llama-cpp-python 已安装但为 CPU only 版本"
    except ImportError:
        return False, "llama-cpp-python 未安装"
    except Exception as e:
        return False, f"检测异常: {e}"


def install_gpu_llama(python_path: str = "") -> bool:
    """
    自动安装 CUDA 版 llama-cpp-python（国内优化）。

    实测 GitHub Pages (abetlen.github.io) 直连可达，50MB wheel 约 1-2 分钟。
    策略:
      1. 直连下载 wheel（超时 300s）
      2. 主索引用阿里云镜像拉依赖
      3. 先试 cu124 → cu121 → cu118

    Parameters
    ----------
    python_path : str
        指定 Python 路径，留空自动找

    Returns
    -------
    bool : 是否安装成功
    """
    import subprocess
    import sys
    import urllib.request
    import tempfile

    # 找 Python 路径
    if not python_path:
        candidates = [
            r"C:\Users\sm001\AppData\Local\Programs\Python\Python311\python.exe",
            sys.executable,
        ]
        for p in candidates:
            if os.path.exists(p):
                python_path = p
                break
        if not python_path:
            print("❌ 找不到 Python")
            return False

    # 检测 Python 版本标签
    py_ver = subprocess.run(
        [python_path, "-c", "import sys; print(f'cp{sys.version_info.major}{sys.version_info.minor}')"],
        capture_output=True, text=True, timeout=5,
    ).stdout.strip()
    print(f"  使用 Python: {python_path} ({py_ver})")

    # 阿里云镜像（pip 安装依赖时用）
    aliyun_mirror = "https://mirrors.aliyun.com/pypi/simple/"

    # CUDA wheel 版本 + URL
    cuda_versions = [
        ("cu124", "https://abetlen.github.io/llama-cpp-python/whl/cu124/llama_cpp_python-0.3.30-{py_ver}-{py_ver}-win_amd64.whl"),
        ("cu121", "https://abetlen.github.io/llama-cpp-python/whl/cu121/llama_cpp_python-0.3.30-{py_ver}-{py_ver}-win_amd64.whl"),
        ("cu118", "https://abetlen.github.io/llama-cpp-python/whl/cu118/llama_cpp_python-0.3.30-{py_ver}-{py_ver}-win_amd64.whl"),
    ]

    temp_dir = tempfile.gettempdir()

    for cuda_ver, url_tpl in cuda_versions:
        wheel_url = url_tpl.format(py_ver=py_ver)
        wheel_file = os.path.join(temp_dir, f"llama_cpp_python-0.3.30-{py_ver}-{py_ver}-win_amd64.whl")

        print(f"  ⏳ [{cuda_ver}] 下载 wheel (50MB, 约1-2分钟)...")
        try:
            req = urllib.request.Request(
                wheel_url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                with open(wheel_file, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)

            file_size = os.path.getsize(wheel_file) / (1024**2)
            print(f"    下载完成 ({file_size:.0f}MB)")

            # pip install（用阿里云拉依赖）
            cmd = [
                python_path, "-m", "pip", "install",
                wheel_file,
                "--force-reinstall",
                "-i", aliyun_mirror,
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            try: os.remove(wheel_file)
            except: pass

            if r.returncode == 0:
                # 验证 GPU
                verify = subprocess.run(
                    [python_path, "-c",
                     "import llama_cpp.llama_cpp as l; print('ok:', hasattr(l, 'ggml_backend_cuda_init'))"],
                    capture_output=True, text=True, timeout=10,
                )
                if "ok: True" in verify.stdout:
                    print(f"  ✅ GPU 加速已启用!")
                    return True
                else:
                    print(f"  ⚠️ 安装成功但 GPU 未启用, 回退 CPU 模式")
                    return False
            else:
                print(f"  ❌ pip 安装失败: {r.stderr[-200:]}")
        except urllib.error.URLError as e:
            print(f"    下载失败: {e.reason}")
        except subprocess.TimeoutExpired:
            print(f"    超时")
        except Exception as e:
            print(f"    失败: {str(e)[:80]}")

    print()
    print("=" * 56)
    print("  自动安装失败。手动操作:")
    print(f"  1. 浏览器打开上面那个 URL，下载 wheel")
    print(f"  2. pip install 下载的文件 -i https://mirrors.aliyun.com/pypi/simple/")
    print("=" * 56)
    return False


def ensure_gpu_llama(python_path: str = "") -> bool:
    """
    一键确保 GPU 版 llama-cpp-python 可用。

    检测 → 已有 GPU → 返回 True
    检测 → CPU only 或无 → 自动安装 → 返回结果

    Usage:
        from direct_llm_client import ensure_gpu_llama
        ensure_gpu_llama()
    """
    ok, msg = check_gpu_llama()
    if ok:
        print(f"  ✅ {msg}")
        return True

    print(f"  ⚠️ {msg}")
    print("  📦 正在自动安装 CUDA 版...")
    return install_gpu_llama(python_path)
