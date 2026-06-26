# -*- coding: utf-8 -*-
# 文件名: src/visualizer.py
# B站知识区视频特征分析 - Matplotlib 可视化模块
# 生成包含 3 个子图的综合统计图表

import os
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # 非交互式后端，避免 GUI 线程冲突
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")


def generate_plots(data_path="data/processed_data.csv",
                   output_path="data/visualization.png"):
    """
    生成包含3个子图的综合统计画布并保存为PNG。

    子图布局：
        (0,0) 相关性热力图
        (0,1) 目标变量（最后一列）分布直方图 + KDE
        (1,0) 播放量 vs 互动率 散点图

    参数
    ----------
    data_path : str
        预处理后的数据CSV路径。
    output_path : str
        输出图片路径 (.png)。

    返回
    -------
    str  实际保存的图片路径。
    """
    print("[可视化] 读取数据 ...")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"未找到输入文件: {data_path}")

    df = pd.read_csv(data_path, encoding="utf-8-sig")
    print(f"[可视化] 数据 {len(df)} 行, {len(df.columns)} 列")

    # ── 1. 筛选数值列 ──────────────────────────────────────
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] < 2:
        raise ValueError(f"数值列不足（当前 {numeric_df.shape[1]} 列）无法绘图")

    print(f"[可视化] 数值列: {numeric_df.columns.tolist()}")

    target_col = numeric_df.columns[-1]   # 最后一列为 y
    print(f"[可视化] 目标变量: {target_col}")

    # ── 2. 创建画布 ────────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("B站知识区视频特征分析", fontsize=16, fontweight="bold", y=0.98)

    # ── 子图 1: 相关性热力图 (左上) ─────────────────────────
    ax1 = axes[0, 0]
    corr = numeric_df.corr()
    n_feats = corr.shape[0]

    im = ax1.imshow(corr.values, cmap="RdYlBu_r", vmin=-1, vmax=1,
                    aspect="auto", interpolation="nearest")

    # 显示数值标签
    for i in range(n_feats):
        for j in range(n_feats):
            val = corr.values[i, j]
            color = "white" if abs(val) > 0.5 else "black"
            ax1.text(j, i, f"{val:.2f}", ha="center", va="center",
                     fontsize=7, color=color, fontweight="bold")

    ax1.set_xticks(range(n_feats))
    ax1.set_yticks(range(n_feats))
    ax1.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax1.set_yticklabels(corr.columns, fontsize=8)
    ax1.set_title("特征相关性热力图", fontsize=12)

    # Colorbar
    cbar = fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
    cbar.set_label("Pearson r", fontsize=9)

    # ── 子图 2: 目标变量分布直方图 + KDE (右上) ────────────
    ax2 = axes[0, 1]
    data_vals = numeric_df[target_col].dropna().values

    # 如果数值过大（播放量级），取对数以便观察
    use_log = data_vals.max() > 1e6
    if use_log:
        plot_vals = np.log10(data_vals.clip(1))   # clip(1) 避免 log(0)
        xlabel = f"log10({target_col})"
        title_suffix = "(对数尺度)"
    else:
        plot_vals = data_vals
        xlabel = target_col
        title_suffix = ""

    ax2.hist(plot_vals, bins=min(50, max(10, len(np.unique(plot_vals)) // 5)),
             density=True, alpha=0.6, color="steelblue", edgecolor="white",
             label="直方图")

    # KDE
    try:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(plot_vals)
        x_grid = np.linspace(plot_vals.min(), plot_vals.max(), 200)
        ax2.plot(x_grid, kde(x_grid), color="crimson", linewidth=2,
                 label="KDE 曲线")
    except ImportError:
        ax2.plot([], [], label="KDE (需 scipy)")

    ax2.set_xlabel(xlabel, fontsize=10)
    ax2.set_ylabel("密度", fontsize=10)
    ax2.set_title(f"{target_col} 分布 {title_suffix}".strip(), fontsize=12)
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", alpha=0.3)

    # ── 子图 3: 播放量 vs 互动率 散点图 (左下) ─────────────
    ax3 = axes[1, 0]

    # 尝试找 interaction_rate, 否则用 coin
    x_plot_col = None
    for candidate in ["interaction_rate", "coin", "favorite", "like"]:
        if candidate in numeric_df.columns:
            x_plot_col = candidate
            break

    if x_plot_col is None:
        # 随便选第一个不是 target 的数值列
        x_plot_col = [c for c in numeric_df.columns if c != target_col][0]

    plot_df = numeric_df[[x_plot_col, target_col]].dropna()

    if len(plot_df) > 0:
        x_vals = plot_df[x_plot_col].values
        y_vals = plot_df[target_col].values

        # 用播放量着色（若与目标列不同）
        scatter = ax3.scatter(x_vals, y_vals, c=y_vals, cmap="viridis",
                              alpha=0.6, s=30, edgecolors="none")

        cbar3 = fig.colorbar(scatter, ax=ax3, fraction=0.046, pad=0.04)
        cbar3.set_label(target_col, fontsize=9)

        # 拟合趋势线
        try:
            mask = np.isfinite(x_vals) & np.isfinite(y_vals)
            if mask.sum() > 2:
                coeffs = np.polyfit(x_vals[mask], y_vals[mask], deg=1)
                trend = np.poly1d(coeffs)
                x_sorted = np.sort(x_vals[mask])
                ax3.plot(x_sorted, trend(x_sorted), "r--", linewidth=1.5,
                         alpha=0.8, label=f"趋势线 (y={coeffs[0]:.2e}x+{coeffs[1]:.2e})")
                ax3.legend(fontsize=8)
        except Exception:
            pass
    else:
        ax3.text(0.5, 0.5, "数据不足以绘制散点图",
                 ha="center", va="center", transform=ax3.transAxes)

    ax3.set_xlabel(x_plot_col, fontsize=10)
    ax3.set_ylabel(target_col, fontsize=10)
    ax3.set_title(f"{target_col} vs {x_plot_col}", fontsize=12)
    ax3.grid(alpha=0.3)

    # ── 子图 4 (右下) 留空，放文本总结 ─────────────────────
    ax4 = axes[1, 1]
    ax4.axis("off")

    summary_lines = [
        "📊 数据摘要",
        f"总样本量: {len(df)}",
        f"特征数: {numeric_df.shape[1]}",
        f"目标变量: {target_col}",
        "",
        f"📈 目标统计",
        f"最小值: {data_vals.min():,.0f}",
        f"最大值: {data_vals.max():,.0f}",
        f"平均值: {data_vals.mean():,.0f}",
        f"中位数: {np.median(data_vals):,.0f}",
        f"标准差: {data_vals.std():,.0f}",
        "",
        f"📌  Top-5 相关特征",
    ]

    if target_col in corr.columns:
        target_corr = corr[target_col].drop(target_col).abs().sort_values(
            ascending=False).head(5)
        for feat, val in target_corr.items():
            summary_lines.append(f"  {feat}: {val:.3f}")

    ax4.text(0.1, 0.95, "\n".join(summary_lines),
             transform=ax4.transAxes, fontsize=10,
             verticalalignment="top", fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow",
                       edgecolor="gray", alpha=0.8))

    # ── 保存 ────────────────────────────────────────────────
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    print(f"[可视化] 图表已保存 -> {os.path.abspath(output_path)}")

    return os.path.abspath(output_path)


# ── 独立运行入口 ────────────────────────────────────────────

if __name__ == "__main__":
    if os.path.exists("data/processed_data.csv"):
        generate_plots("data/processed_data.csv", "data/visualization.png")
    else:
        print("请先运行 analyzer.py 进行数据预处理")
