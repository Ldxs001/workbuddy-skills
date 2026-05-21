"""
round-robin-allocator  |  核心分配算法
========================================
通用均匀轮转分配：将 N 个"对象"在 T 个"轮次"中，
按比例分配 K 种"选项"，并尽量让每个对象每轮获得不同选项。

术语映射（可自定义，下面仅为示例）：
  对象  ← 项目 / 学生 / 用户 / 商品 ...
  轮次  ← 周期 / 周 / 月 / 阶段 ...
  选项  ← 方案 / 策略 / 组 / 颜色 ...

Public API
----------
allocate(N, T, K, ratios) -> list[dict]
    返回 N 个对象的分配结果。

每个结果 dict 结构：
  {
    "id":       int,          # 对象编号（1-based）
    "slots":    list[int],    # 每轮分到的选项编号（1-based），长度 T
    "used":     set[int],     # 已覆盖的选项集合
    "coverage": float,        # 覆盖率 = len(used) / K
  }
"""

from __future__ import annotations
from collections import defaultdict
from typing import Sequence


# ─────────────────────────────────────────────
# 公开接口
# ─────────────────────────────────────────────

def allocate(
    N: int,
    T: int,
    K: int,
    ratios: Sequence[float],
) -> list[dict]:
    """
    均匀轮转分配。

    Parameters
    ----------
    N : 对象数量（>0）
    T : 轮次数量（>0）
    K : 选项数量（>0，len(ratios) 必须 == K）
    ratios : 各选项的分配比例（可以是百分比或任意正数）

    Returns
    -------
    list of dict，每项包含 id / slots / used / coverage
    """
    if len(ratios) != K:
        raise ValueError(f"ratios 长度 {len(ratios)} 与 K={K} 不一致")
    if any(r < 0 for r in ratios):
        raise ValueError("比例不能为负数")
    total_ratio = sum(ratios)
    if total_ratio <= 0:
        raise ValueError("比例之和必须大于 0")

    norm = [r / total_ratio for r in ratios]

    objects = [{"id": i + 1, "slots": [], "used": set()} for i in range(N)]

    # ── 阶段1：为每轮生成选项池（确定性，按 Hamilton 大余数法） ──
    period_pools: list[list[int]] = []
    for _ in range(T):
        quotas = _hamilton_quota(N, norm, K)
        pool: list[int] = []
        for option_idx, count in enumerate(quotas):
            pool.extend([option_idx + 1] * count)
        period_pools.append(pool)

    # ── 阶段2：贪心分配（优先填补覆盖空白） ──
    for t in range(T):
        remaining: dict[int, int] = defaultdict(int)
        for opt in period_pools[t]:
            remaining[opt] += 1

        # 覆盖率低的对象优先处理
        order = sorted(range(N), key=lambda i: (len(objects[i]["used"]), i))

        for i in order:
            obj = objects[i]
            # 优先选"尚未覆盖"且剩余最多的选项
            novel = [(opt, cnt) for opt, cnt in remaining.items()
                     if cnt > 0 and opt not in obj["used"]]
            if novel:
                selected = max(novel, key=lambda x: (x[1], -x[0]))[0]
            else:
                # 退而求其次：选剩余最多的（重复也无妨）
                fallback = [(opt, cnt) for opt, cnt in remaining.items() if cnt > 0]
                if not fallback:
                    raise RuntimeError(f"轮次 {t+1} 选项池耗尽，请检查参数")
                selected = max(fallback, key=lambda x: (x[1], -x[0]))[0]

            obj["slots"].append(selected)
            obj["used"].add(selected)
            remaining[selected] -= 1

    # ── 阶段3：优化（尝试消除同轮次重复，提升覆盖率） ──
    _optimize(objects, period_pools, T, K)

    # ── 计算最终覆盖率 ──
    for obj in objects:
        obj["used"] = set(obj["slots"])          # 重新同步（优化后可能变化）
        obj["coverage"] = len(obj["used"]) / K

    return objects


# ─────────────────────────────────────────────
# 内部工具
# ─────────────────────────────────────────────

def _hamilton_quota(N: int, norm_ratios: list[float], K: int) -> list[int]:
    """Hamilton（最大余数）配额法：确保配额之和 == N。"""
    raw = [N * r for r in norm_ratios]
    quotas = [int(x) for x in raw]
    fractions = [(raw[i] - quotas[i], i) for i in range(K)]
    deficit = N - sum(quotas)
    # 按余数降序补齐
    for _, idx in sorted(fractions, reverse=True)[:deficit]:
        quotas[idx] += 1
    return quotas


def _optimize(objects: list[dict], pools: list[list[int]], T: int, K: int) -> None:
    """
    迭代优化：将重复使用次数最多的选项替换为未覆盖选项，
    前提是目标轮次的配额还有空余。
    """
    improved = True
    while improved:
        improved = False
        for obj in objects:
            slots = obj["slots"]
            freq: dict[int, int] = defaultdict(int)
            for s in slots:
                freq[s] += 1

            # 找重复最多的选项
            dup_options = [opt for opt, cnt in freq.items() if cnt > 1]
            if not dup_options:
                continue
            worst = max(dup_options, key=lambda x: freq[x])

            for t in range(T):
                if slots[t] != worst:
                    continue

                # 计算该轮各选项使用量
                used_in_t: dict[int, int] = defaultdict(int)
                for o in objects:
                    if t < len(o["slots"]):
                        used_in_t[o["slots"][t]] += 1
                pool_count: dict[int, int] = defaultdict(int)
                for opt in pools[t]:
                    pool_count[opt] += 1

                best = None
                best_gain = 0
                for cand in range(1, K + 1):
                    if cand == worst:
                        continue
                    if used_in_t.get(cand, 0) >= pool_count.get(cand, 0):
                        continue  # 该选项在此轮已无剩余配额
                    gain = 0 if cand in obj["used"] else 1
                    if gain > best_gain or (gain == best_gain and best and cand < best):
                        best = cand
                        best_gain = gain

                if best and best_gain > 0:
                    slots[t] = best
                    obj["used"] = set(slots)
                    improved = True
                    break


# ─────────────────────────────────────────────
# 统计辅助
# ─────────────────────────────────────────────

def compute_stats(results: list[dict], T: int, K: int) -> dict:
    """
    计算全局统计信息。

    Returns dict with keys:
      period_dist  : {t: {option: count}}
      avg_coverage : float
      full_coverage: int  (覆盖率==1 的对象数)
    """
    period_dist: dict[int, dict[int, int]] = {
        t: defaultdict(int) for t in range(T)
    }
    for obj in results:
        for t, opt in enumerate(obj["slots"]):
            period_dist[t][opt] += 1

    coverages = [obj["coverage"] for obj in results]
    return {
        "period_dist": period_dist,
        "avg_coverage": sum(coverages) / len(coverages) if coverages else 0.0,
        "full_coverage": sum(1 for c in coverages if c >= 1.0),
    }
