"""
分析质控工具包 — 标准注册表

## 数据模型

### Standard（标准定义）

| 字段 | 类型 | 必需 | 说明 |
|------|------|:----:|------|
| `standard_id` | str | ✅ | 唯一标识符，如 `gbt27417`、`ich` |
| `name` | str | ✅ | 标准简称，如 `GB/T 27417-2017` |
| `full_name` | str | ✅ | 标准全称，如 `合格评定 化学分析方法确认和验证指南` |
| `industry` | list[str] | ✅ | 适用行业列表，如 `["化学分析", "食品检测"]` |
| `applicable_functions` | list[str] | ✅ | 适用的计算函数，如 `["calc_lod_loq"]` |
| `parameters` | dict | ✅ | 公式参数键值对 |
| `formulas` | dict | ✅ | 人可读的公式描述 |
| `notes` | str | | 补充说明，如出自标准第几节 |
| `sigma_sources_supported` | list[str] | | 支持的 sigma 来源 |
| `output_fields` | list[str] | | 输出结果中应包含哪些字段 |

### 字段提取指南（供 LLM/智能体注册新标准时参考）

要从一份标准文档中提取信息注册为新标准，需定位以下内容：

1. **standard_id**: 取标准号小写去符号，如 `GB/T 27417-2017` → `gbt27417`
2. **name**: 标准号原样，如 `GB/T 27417-2017`
3. **full_name**: 标准封面标题，如 `合格评定 化学分析方法确认和验证指南`
4. **industry**: 从标准适用范围章节提取
5. **applicable_functions**: 根据公式类型判断归属哪个计算函数
6. **parameters**: 公式中的系数/因子，如 LOD=3σ/b 中的 3
7. **formulas**: 标准原文中的公式
8. **sigma_sources_supported**: 标准中规定 sigma 的测定方法

### 注册示例（LLM 输出格式）

```python
{
    "standard_id": "gbt5009_295",
    "name": "GB 5009.295-2023",
    "full_name": "食品安全国家标准 化学分析方法验证通则",
    "industry": ["食品检测", "理化检验"],
    "applicable_functions": ["calc_lod_loq", "calc_recovery"],
    "parameters": {
        "lod_factor": 3,
        "loq_factor": 10,
        "recovery_accept_min": 90,
        "recovery_accept_max": 108,
    },
    "formulas": {
        "lod": "LOD = 3 × σ / b",
        "loq": "LOQ = 10 × σ / b",
    },
    "sigma_sources_supported": ["curve", "instrument", "blank"],
    "notes": "替代 GB/T 27417-2017 在食品检测领域的引用",
}
```
"""
import os
import json
from typing import Optional

# ═══════════════════════════════════════════════════════
# 数据目录（R-12 合规）
# ═══════════════════════════════════════════════════════
SKILL_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".."
))
_standards_dir = os.path.normpath(os.path.join(
    SKILL_DIR, "..", ".standardization", "analysis-toolkit", "data", "standards"
))
STANDARDS_FILE = os.path.join(_standards_dir, "standards.json")
TEMPLATES_FILE = os.path.join(_standards_dir, "templates.json")


# ═══════════════════════════════════════════════════════
# 内部数据模型
# ═══════════════════════════════════════════════════════

class Standard:
    """标准定义"""
    REQUIRED_FIELDS = {"standard_id", "name", "full_name", "industry",
                       "applicable_functions", "parameters", "formulas"}

    def __init__(self, data: dict):
        missing = self.REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ValueError(f"标准定义缺少必需字段: {missing}")
        self.data = data

    @property
    def standard_id(self) -> str:
        return self.data["standard_id"]

    def get(self, key, default=None):
        return self.data.get(key, default)

    def to_dict(self) -> dict:
        return dict(self.data)

    def applies_to(self, func_name: str) -> bool:
        """判断此标准是否适用于指定函数"""
        return func_name in self.data.get("applicable_functions", [])


# ═══════════════════════════════════════════════════════
# 标准注册表
# ═══════════════════════════════════════════════════════

class StandardRegistry:
    """标准注册表 — 管理所有已注册的标准"""

    def __init__(self, filepath: str = STANDARDS_FILE):
        self._filepath = filepath
        self._standards: dict[str, Standard] = {}
        self._load()

    def _load(self):
        """从 JSON 文件加载标准"""
        if not os.path.exists(self._filepath):
            self._standards = {}
            return
        try:
            with open(self._filepath, "r", encoding="utf-8") as f:
                raw_list = json.load(f)
            self._standards = {}
            for item in raw_list:
                try:
                    std = Standard(item)
                    self._standards[std.standard_id] = std
                except ValueError as e:
                    import warnings
                    warnings.warn(f"跳过无效标准定义: {e}")
        except (json.JSONDecodeError, IOError) as e:
            import warnings
            warnings.warn(f"标准文件读取失败: {e}")
            self._standards = {}

    def _save(self):
        """持久化到 JSON 文件"""
        os.makedirs(os.path.dirname(self._filepath), exist_ok=True)
        raw_list = [s.to_dict() for s in self._standards.values()]
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump(raw_list, f, ensure_ascii=False, indent=2)

    # ── 查询接口 ──

    def get(self, standard_id: str) -> Optional[Standard]:
        """按 ID 查询标准"""
        return self._standards.get(standard_id)

    def list_all(self) -> list[dict]:
        """列出所有标准（摘要信息）"""
        return [
            {"standard_id": s.standard_id, "name": s.get("name"),
             "industry": s.get("industry", []),
             "applicable_functions": s.get("applicable_functions", [])}
            for s in self._standards.values()
        ]

    def list_by_industry(self, industry: str) -> list[dict]:
        """按行业筛选标准"""
        return [
            {"standard_id": s.standard_id, "name": s.get("name"),
             "formulas": s.get("formulas")}
            for s in self._standards.values()
            if industry.lower() in [ind.lower() for ind in s.get("industry", [])]
        ]

    def list_by_function(self, func_name: str) -> list[dict]:
        """按适用函数筛选标准"""
        return [
            {"standard_id": s.standard_id, "name": s.get("name"),
             "parameters": s.get("parameters")}
            for s in self._standards.values()
            if s.applies_to(func_name)
        ]

    def get_parameter(self, standard_id: str, key: str, default=None):
        """获取指定标准的参数值"""
        std = self.get(standard_id)
        if not std:
            return default
        return std.get("parameters", {}).get(key, default)

    # ── 注册/注销接口（供 LLM/智能体调用） ──

    def register(self, data: dict) -> dict:
        """
        注册新标准。

        LLM 调用示例：
        ```python
        from scripts.standards.registry import StandardRegistry
        reg = StandardRegistry()
        result = reg.register({
            "standard_id": "gbt5009_295",
            "name": "GB 5009.295-2023",
            "full_name": "食品安全国家标准 化学分析方法验证通则",
            "industry": ["食品检测"],
            "applicable_functions": ["calc_lod_loq"],
            "parameters": {"lod_factor": 3, "loq_factor": 10},
            "formulas": {"lod": "LOD = 3σ/b", "loq": "LOQ = 10σ/b"},
        })
        ```

        Returns
        -------
        dict — {"status": "ok"|"warning"|"error", "message": str, "standard_id": str}
        """
        try:
            std = Standard(data)
        except ValueError as e:
            return {"status": "error", "message": str(e), "standard_id": None}

        existing = self._standards.get(std.standard_id)
        if existing:
            self._standards[std.standard_id] = std
            self._save()
            return {
                "status": "warning",
                "message": f"标准 '{std.standard_id}' 已存在，已覆盖更新",
                "standard_id": std.standard_id,
            }
        else:
            self._standards[std.standard_id] = std
            self._save()
            return {
                "status": "ok",
                "message": f"标准 '{std.standard_id}' 注册成功",
                "standard_id": std.standard_id,
            }

    def unregister(self, standard_id: str) -> dict:
        """删除标准"""
        if standard_id not in self._standards:
            return {"status": "error", "message": f"标准 '{standard_id}' 不存在"}
        del self._standards[standard_id]
        self._save()
        return {"status": "ok", "message": f"标准 '{standard_id}' 已删除"}

    def get_lod_loq_params(self, standard: str) -> dict:
        """
        获取 LOD/LOQ 计算参数。

        Parameters
        ----------
        standard : str — 标准 ID

        Returns
        -------
        dict — {"lod_factor": float, "loq_factor": float, "standard_info": str} 或 None
        """
        std = self.get(standard)
        if not std:
            return None
        params = std.get("parameters", {})
        lod_factor = params.get("lod_factor")
        loq_factor = params.get("loq_factor")
        if lod_factor is None or loq_factor is None:
            return None
        return {
            "lod_factor": lod_factor,
            "loq_factor": loq_factor,
            "standard_info": f"{std.get('name')} ({std.get('full_name', '')})",
            "standard_id": standard,
        }


# ═══════════════════════════════════════════════════════
# 单例
# ═══════════════════════════════════════════════════════

_default_registry = None


def get_registry() -> StandardRegistry:
    """获取默认注册表实例"""
    global _default_registry
    if _default_registry is None:
        _default_registry = StandardRegistry()
    return _default_registry


def reset_registry():
    """重置注册表（用于单元测试）"""
    global _default_registry
    _default_registry = None


# ═══════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════

def main():
    """命令行入口"""
    import sys
    reg = get_registry()
    if len(sys.argv) < 2:
        print("用法: python -m scripts.standards.registry <命令> [参数]")
        print("命令: list, get <id>, list-by-industry <行业>, list-by-function <函数名>")
        print("       register <json文件路径>, unregister <id>")
        return

    cmd = sys.argv[1]
    if cmd == "list":
        items = reg.list_all()
        print(f"已注册标准 ({len(items)} 个):")
        for item in items:
            print(f"  {item['standard_id']}: {item['name']} [{', '.join(item['industry'])}]")
    elif cmd == "get" and len(sys.argv) > 2:
        std = reg.get(sys.argv[2])
        if std:
            import json as _j
            print(_j.dumps(std.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"标准 '{sys.argv[2]}' 不存在")
    elif cmd == "list-by-industry" and len(sys.argv) > 2:
        items = reg.list_by_industry(sys.argv[2])
        print(f"行业 '{sys.argv[2]}' 相关标准 ({len(items)} 个):")
        for item in items:
            print(f"  {item['standard_id']}: {item['name']}")
    elif cmd == "list-by-function" and len(sys.argv) > 2:
        items = reg.list_by_function(sys.argv[2])
        print(f"函数 '{sys.argv[2]}' 可用标准 ({len(items)} 个):")
        for item in items:
            print(f"  {item['standard_id']}: {item['name']}")
    elif cmd == "register" and len(sys.argv) > 2:
        with open(sys.argv[2], "r", encoding="utf-8") as f:
            data = json.load(f)
        result = reg.register(data)
        print(f"[{result['status']}] {result['message']}")
    elif cmd == "unregister" and len(sys.argv) > 2:
        result = reg.unregister(sys.argv[2])
        print(f"[{result['status']}] {result['message']}")
    else:
        print("未知命令或参数不足")


if __name__ == "__main__":
    main()
