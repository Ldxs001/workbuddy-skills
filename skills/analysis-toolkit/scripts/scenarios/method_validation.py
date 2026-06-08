"""
方法验证（Method Validation）

场景：标准曲线拟合、检出限/定量限计算、回收率、曲线引入不确定度。

核心流程：
1. 标准曲线拟合（线性/多项式，支持强制过零点）
2. 计算方法检出限（LOD）和定量限（LOQ）
3. 加标回收率计算
4. 标准曲线引入的不确定度分量计算
"""
import numpy as np
import matplotlib.pyplot as plt

from ..analysis.regression import linear_regression, polynomial_regression
from ..output import publish


def calibration_curve(x, y, force_zero=False, degree=1):
    """
    标准曲线拟合。

    Parameters
    ----------
    x : array-like — 浓度
    y : array-like — 响应值（峰面积等）
    force_zero : bool — 是否强制过零点
    degree : int — 多项式阶数（1=线性，>1=多项式）

    Returns
    -------
    dict
    """
    if degree == 1:
        result = linear_regression(x, y, force_zero=force_zero)
    else:
        result = polynomial_regression(x, y, degree=degree)

    result["force_zero"] = force_zero
    result["degree"] = degree
    result["x"] = np.array(x).tolist()
    result["y"] = np.array(y).tolist()
    publish(result, title="标准曲线拟合")
    return result


def calc_lod_loq(sigma=None, slope=1, standard="gbt27417", sigma_source="curve",
                 calibration_data=None):
    """
    计算检出限（LOD）和定量限（LOQ）。

    支持两种标准、四种 sigma 来源。

    ── 标准依据 ──

    standard="gbt27417"（GB/T 27417-2017 合格评定 化学分析方法确认和验证指南）:
        LOD = 3 × σ / b
        LOQ = 3 × LOD = 9 × σ / b
        这是你SOP里写的，出自该标准 5.4.2.2 c）校准方程法。

    standard="ich"（ICH Q2(R1) / 中国药典 2020版）:
        LOD = 3.3 × σ / b
        LOQ = 10 × σ / b

    ── sigma 来源（sigma_source）──

    "curve"（校准方程法）:
        σ = Sy/x（标准曲线回归的剩余标准偏差）
        b = 曲线斜率
        直接用曲线数据计算，不需要额外试验。
        对应你问的"通过标准曲线直接反推"。

    "instrument"（仪器精密度法）:
        σ = 仪器精密度试验的标准偏差（你SOP的做法）
        b = 曲线斜率
        需要单独做仪器精密度测试。

    "blank"（空白标准偏差法）:
        σ = 空白测定的标准偏差（n≥10）
        b = 曲线斜率（如果空白在响应单位，需除b换算到浓度）

    "noise"（信噪比法）:
        σ = 基线噪声的标准偏差
        slope=1 时 LOD/LOQ 直接以信号单位输出
        适用于光谱类仪器

    Parameters
    ----------
    sigma : float, optional
        标准偏差值。若不提供，从 calibration_data 自动获取 Sy/x。
    slope : float
        斜率/灵敏度（默认1）。
    standard : str
        "gbt27417"（默认）或 "ich"
    sigma_source : str
        "curve", "instrument", "blank", "noise"
    calibration_data : dict, optional
        calibration_curve 的返回结果。当 sigma 未提供时，从中提取 Sy/x 和斜率。

    Returns
    -------
    dict
    """
    # 如果提供了 calibration_data，自动提取
    if calibration_data is not None:
        if sigma is None:
            sigma = calibration_data.get("syx", calibration_data.get("residual_std", 0))
        if slope == 1:
            slope = calibration_data.get("slope", calibration_data.get("b", 1))

    if slope == 0:
        raise ValueError("斜率为0，无法计算检出限")
    if sigma is None or sigma <= 0:
        raise ValueError("标准偏差必须提供且大于0")

    # 按标准选公式
    if standard == "gbt27417":
        lod = 3 * sigma / slope
        loq = 3 * lod  # = 9 × σ / b
        formula_str = "LOD=3σ/b, LOQ=3×LOD (GB/T 27417-2017)"
    elif standard == "ich":
        lod = 3.3 * sigma / slope
        loq = 10 * sigma / slope
        formula_str = "LOD=3.3σ/b, LOQ=10σ/b (ICH Q2(R1))"
    else:
        raise ValueError(f"不支持的标准: {standard}")

    result = {
        "lod": lod,
        "loq": loq,
        "sigma": sigma,
        "sigma_source": sigma_source,
        "slope": slope,
        "standard": standard,
        "formula": formula_str,
    }
    publish(result, title="检出限/定量限计算")
    return result


def calc_recovery(measured, spiked, blank=0):
    """
    加标回收率计算。

    Parameters
    ----------
    measured : array-like — 加标样品测量值列表
    spiked : float or array-like — 加标浓度
    blank : float — 空白值

    Returns
    -------
    dict
    """
    measured = np.array(measured)
    if isinstance(spiked, (int, float)):
        spiked = np.full_like(measured, spiked)

    recoveries = [(m - blank) / s * 100 for m, s in zip(measured, spiked)]

    result = {
        "recoveries": recoveries,
        "mean_recovery": np.mean(recoveries),
        "std_recovery": np.std(recoveries, ddof=1),
    }
    publish(result, title="加标回收率计算")
    return result


def curve_uncertainty(calibration_data, sample_responses,
                      n_cal_points=None, n_sample_replicates=None):
    """
    标准曲线拟合引入的相对标准不确定度 u_rel(curve)。

    这是测量不确定度的**一个分量**（通常为主要分量），
    而非总不确定度——总不确定度还需合成标准溶液配制、样品前处理等其他分量。

    公式（EURACHEM/CITAC Guide, CNAS-GL006）：

        u_rel = (Sy/x) / (b · x_sample) ×
                √{ 1/p + 1/n + (x_sample - x̄)² / Σ(xi - x̄)² }

    对应你Excel里的公式：
        =(S12/S11)*(SQRT(1/U3+1/U5+((T3-AVERAGE(R3:R9))^2)/SUM((R3:R9-AVERAGE(R3:R9))^2)))/T3

    Parameters
    ----------
    calibration_data : dict — calibration_curve的返回值
    sample_responses : array-like — 样品的多次测量响应值
    n_cal_points : int, optional — 校准点数
    n_sample_replicates : int, optional — 样品重复测量次数

    Returns
    -------
    dict
    """
    syx = calibration_data.get("syx", calibration_data.get("residual_std", 0))
    slope = calibration_data.get("slope", calibration_data.get("b", 0))
    intercept = calibration_data.get("intercept", calibration_data.get("a", 0))
    x_vals = np.array(calibration_data.get("x", []))

    n = n_cal_points if n_cal_points else len(x_vals)
    p = n_sample_replicates if n_sample_replicates else len(sample_responses)

    if n < 2 or p < 1 or slope == 0:
        raise ValueError("数据不足，无法计算不确定度")

    y_sample_mean = np.mean(sample_responses)
    x_sample = (y_sample_mean - intercept) / slope
    x_mean = np.mean(x_vals)
    ss_xx = np.sum((x_vals - x_mean) ** 2)

    if ss_xx <= 0:
        raise ValueError("校准点浓度方差为0，无法计算")

    u_rel = (syx / slope / x_sample) * np.sqrt(1/p + 1/n + (x_sample - x_mean)**2 / ss_xx)

    result = {
        "relative_uncertainty": u_rel,
        "standard_uncertainty": u_rel * x_sample,
        "x_sample": x_sample,
        "syx": syx,
        "slope": slope,
    }
    publish(result, title="曲线引入不确定度")
    return result


def calibration_plot(x, y, result, title="标准曲线"):
    """
    标准曲线拟合图。

    Parameters
    ----------
    x : array-like
    y : array-like
    result : dict — calibration_curve的返回值
    title : str

    Returns
    -------
    matplotlib.figure.Figure
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.scatter(x, y, c='#2ecc71', s=60, edgecolors='#27ae60', linewidth=0.5,
               label="实测点", zorder=5)

    # 拟合线
    x_fit = np.linspace(min(x), max(x), 100)
    if result.get("degree", 1) == 1:
        y_fit = result["slope"] * x_fit + (0 if result.get("force_zero") else result["intercept"])
    else:
        coeffs = result.get("coefficients", [])
        y_fit = np.polyval(coeffs, x_fit)

    ax.plot(x_fit, y_fit, 'r-', linewidth=2, label="拟合曲线")
    ax.set_xlabel("浓度")
    ax.set_ylabel("响应值")
    ax.set_title(title)

    # 标注回归方程
    if result.get("degree", 1) == 1:
        eq_text = f"y = {result['slope']:.4e}x"
        if not result.get("force_zero"):
            eq_text += f" + {result['intercept']:.4e}"
        eq_text += f"\nr = {result.get('r', 0):.4f}"
        eq_text += f"\nr² = {result.get('r2', 0):.4f}"
    else:
        eq_text = "多项式拟合"
    ax.text(0.05, 0.95, eq_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    publish({}, title="标准曲线图", figure=fig, html_filename="calibration_curve.html")
    return fig
