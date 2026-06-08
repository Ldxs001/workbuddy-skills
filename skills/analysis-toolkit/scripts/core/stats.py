"""
基础统计方法模块
"""
import numpy as np


def calc_precision_stats(values):
    """
    精密度统计：SD, RSD, 平均值, 中位数。
    
    Parameters
    ----------
    values : array-like
    
    Returns
    -------
    dict
        {"mean", "median", "sd", "rsd", "count", "min", "max"}
    """
    arr = np.array(values, dtype=float)
    mean = np.mean(arr)
    sd = np.std(arr, ddof=1)
    
    return {
        "mean": mean,
        "median": np.median(arr),
        "sd": sd,
        "rsd": sd / mean * 100 if mean != 0 else 0,
        "count": len(arr),
        "min": np.min(arr),
        "max": np.max(arr),
    }


def calc_synthetic_std(groups, method="standard"):
    """
    合成标准差。
    
    适用场景：多个组（不同水平/批次）的精密度合并。
    
    Parameters
    ----------
    groups : list of array-like
        每个组的数值列表
    method : str
        "standard" — 正规算法（加权合并）
        "simple" — 简单算法（SQRT((SD1²+SD2²+...+SDk²)/k)）
    
    Returns
    -------
    dict
        {"synthetic_std", "synthetic_rsd", "overall_mean", "group_stats"}
    """
    group_stats = []
    total_n = 0
    total_ss = 0
    weighted_sum = 0
    sd_squares = 0
    k = len(groups)
    
    for g in groups:
        arr = np.array(g, dtype=float)
        n = len(arr)
        mean = np.mean(arr)
        sd = np.std(arr, ddof=1)
        ss = (n - 1) * sd ** 2
        
        group_stats.append({
            "n": n, "mean": mean, "sd": sd, "ss": ss
        })
        total_n += n
        total_ss += ss
        weighted_sum += mean * n
        sd_squares += sd ** 2
    
    if method == "simple":
        # 简单算法：SQRT(ΣSD² / k)
        synthetic_std = np.sqrt(sd_squares / k) if k > 0 else 0
    else:
        # 正规算法（加权合并）：SQRT(Σ(n-1)SD² / (Σn - k))
        synthetic_std = np.sqrt(total_ss / (total_n - k)) if total_n > k else 0
    
    overall_mean = weighted_sum / total_n if total_n > 0 else 0
    
    return {
        "synthetic_std": synthetic_std,
        "synthetic_rsd": synthetic_std / overall_mean * 100 if overall_mean != 0 else 0,
        "overall_mean": overall_mean,
        "group_count": k,
        "total_n": total_n,
        "method": method,
        "group_stats": group_stats,
    }


def calc_precision(values):
    """
    calc_precision_stats 的简写别名。
    """
    return calc_precision_stats(values)
