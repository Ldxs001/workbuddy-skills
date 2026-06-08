"""
Pipeline 引擎 — 定义和执行分析流水线。

一个 Pipeline 是一系列有序步骤（Step），
每个步骤指向一个函数及其参数，
上一步的结果可传递给下一步。

示例：

    pipe = Pipeline("我的分析", steps=[
        Step("加载", "core.loader.load_data", {"path": "data.xlsx"}),
        Step("精密度", "scenarios.internal_qc.internal_precision_analysis",
             {"data": "%加载%", "level_col": "水平", "value_col": "结果"}),
        Step("质控图", "scenarios.internal_qc.control_chart",
             {"data": "%加载%", "value_col": "结果"}),
    ])
    result = pipe.run()
"""
import importlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable


@dataclass
class Step:
    """流水线的一个步骤"""
    name: str                              # 步骤名称（用于引用输出）
    target: str                            # "module.func_name"，如 "scenarios.internal_qc.control_chart"
    params: Dict[str, Any] = field(default_factory=dict)  # 参数
    description: str = ""                  # 可选说明

    def resolve(self, context: Dict[str, Any]) -> Callable:
        """将 target 字符串解析为实际函数"""
        mod_path, func_name = self.target.rsplit(".", 1)
        mod = importlib.import_module(f"scripts.{mod_path}")
        return getattr(mod, func_name)

    def resolve_params(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """将参数中的引用替换为上下文中的实际值。

        引用语法：
            %input%     — 整个原始输入数据
            %step_name% — 上一步的完整返回值 dict
            %step_name.key% — 上一步返回值中的某个字段
        """
        resolved = {}
        for k, v in self.params.items():
            if isinstance(v, str) and v.startswith("%") and v.endswith("%"):
                ref = v[1:-1]
                if ref == "input":
                    resolved[k] = context.get("__input__")
                elif "." in ref:
                    step, key = ref.split(".", 1)
                    step_result = context.get(step, {})
                    resolved[k] = step_result.get(key) if isinstance(step_result, dict) else step_result
                else:
                    resolved[k] = context.get(ref)
            else:
                resolved[k] = v
        return resolved


@dataclass
class Pipeline:
    """分析流水线"""
    name: str
    steps: List[Step]
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def run(self, input_data=None, verbose=True) -> Dict[str, Any]:
        """
        依次执行所有步骤。

        Parameters
        ----------
        input_data : any, optional
            传递给使用 %input% 引用的步骤
        verbose : bool
            是否打印步骤进度

        Returns
        -------
        dict
            {step_name: step_return_value, ...}
        """
        context = {"__input__": input_data}
        results = {}

        if verbose:
            print(f"▶ 运行流水线: {self.name}")
            print(f"  共 {len(self.steps)} 步")
            print()

        for i, step in enumerate(self.steps):
            if verbose:
                print(f"  [{i+1}/{len(self.steps)}] {step.name} ... ", end="", flush=True)

            try:
                func = step.resolve(context)
                params = step.resolve_params(context)

                # 检查函数参数签名，如果第一个参数名为 self 则传 context
                import inspect
                sig = inspect.signature(func)
                filtered_params = {}
                for pname in sig.parameters:
                    if pname in params:
                        filtered_params[pname] = params[pname]

                result = func(**filtered_params)
                context[step.name] = result
                results[step.name] = result

                if verbose:
                    rtype = type(result).__name__
                    print(f"✓ ({rtype})")

            except Exception as e:
                if verbose:
                    print(f"✗ 失败: {e}")
                results[step.name] = {"error": str(e)}
                # 不中断，继续执行后续步骤

        if verbose:
            print(f"  ✅ 完成: {sum(1 for v in results.values() if not isinstance(v, dict) or 'error' not in v)}/{len(self.steps)} 步成功")

        # ── 自动验证：所有计算步骤结束后，用不同算法复测 ──
        try:
            from .verify import verify_all, verify_summary
            self._validation = verify_all(results, context)
            results["__verify__"] = {
                "results": self._validation,
                "summary": verify_summary(self._validation),
                "passed": all(v.get("pass") for v in self._validation if v.get("pass") is not None),
            }
            if verbose:
                print(f"\n{results['__verify__']['summary']}")
        except Exception as e:
            if verbose:
                print(f"\n  ⚠ 验证未执行: {e}")

        return results

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "steps": [{"name": s.name, "target": s.target, "params": s.params, "description": s.description}
                      for s in self.steps],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Pipeline":
        steps = [Step(**s) for s in d["steps"]]
        return cls(name=d["name"], steps=steps,
                   description=d.get("description", ""),
                   tags=d.get("tags", []))


def pipeline(*steps, name="未命名流水线", description="", tags=None):
    """快速创建 Pipeline 的便捷函数。

    Example:
        from scripts.pipeline import pipeline, step

        p = pipeline(
            step("加载", "core.loader.load_data", {"path": "data.xlsx"}),
            step("分析", "scenarios.internal_qc.internal_precision_analysis",
                 {"data": "%input%", "level_col": "水平", "value_col": "结果"}),
            name="我的分析",
            description="从Excel加载数据 → 精密度分析",
        )
        r = p.run(input_data)
    """
    return Pipeline(
        name=name,
        steps=list(steps),
        description=description,
        tags=tags or [],
    )


def step(name, target, **params):
    """创建单个步骤的便捷函数。"""
    return Step(name=name, target=target, params=params)
