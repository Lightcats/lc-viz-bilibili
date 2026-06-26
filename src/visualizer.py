# -*- coding: utf-8 -*-
# 文件名: src/visualizer.py
# Bilibili Knowledge Zone Video Feature Analysis - Matplotlib Visualization Module
# Generates a 3-panel statistical chart canvas

import os
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")


def generate_plots(data_path="data/processed_data.csv",
                   output_path="data/visualization.png"):
    """
    Generate a 3-panel statistical chart canvas and save as PNG.

    Layout:
        (0,0) Feature correlation heatmap
        (0,1) Target variable distribution (histogram + KDE)
        (1,0) Scatter plot: view count vs interaction rate

    Parameters
    ----------
    data_path : str
        Path to preprocessed CSV data.
    output_path : str
        Path to save output PNG.

    Returns
    -------
    str  Absolute path of saved image.
    """
    print("[Viz] Reading data ...")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Input file not found: {data_path}")

    df = pd.read_csv(data_path, encoding="utf-8-sig")
    print(f"[Viz] Data: {len(df)} rows, {len(df.columns)} columns")

    # ── 1. Select numeric columns ────────────────────────────
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] < 2:
        raise ValueError(f"Not enough numeric columns ({numeric_df.shape[1]}), "
                         f"need at least 2")

    print(f"[Viz] Numeric columns: {numeric_df.columns.tolist()}")

    target_col = numeric_df.columns[-1]   # last column = target (view)
    print(f"[Viz] Target variable: {target_col}")

    # ── 2. Create canvas ─────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Bilibili Knowledge Zone Video Feature Analysis",
                 fontsize=16, fontweight="bold", y=0.98)

    # ══════════════════════════════════════════════════════════
    # Subplot 1: Correlation heatmap (top-left)
    # ══════════════════════════════════════════════════════════
    ax1 = axes[0, 0]
    corr = numeric_df.corr()
    n_feats = corr.shape[0]

    im = ax1.imshow(corr.values, cmap="RdYlBu_r", vmin=-1, vmax=1,
                    aspect="auto", interpolation="nearest")

    # Display numeric labels
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
    ax1.set_title("Feature Correlation Heatmap", fontsize=12)

    cbar = fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
    cbar.set_label("Pearson r", fontsize=9)

    # ══════════════════════════════════════════════════════════
    # Subplot 2: Target distribution histogram + KDE (top-right)
    # ══════════════════════════════════════════════════════════
    ax2 = axes[0, 1]
    data_vals = numeric_df[target_col].dropna().values

    # Log-scale if values are huge (millions)
    use_log = data_vals.max() > 1e6
    if use_log:
        plot_vals = np.log10(data_vals.clip(1))
        xlabel = f"log10({target_col})"
        title_suffix = " (log scale)"
    else:
        plot_vals = data_vals
        xlabel = target_col
        title_suffix = ""

    ax2.hist(plot_vals, bins=min(50, max(10, len(np.unique(plot_vals)) // 5)),
             density=True, alpha=0.6, color="steelblue", edgecolor="white",
             label="Histogram")

    # KDE
    try:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(plot_vals)
        x_grid = np.linspace(plot_vals.min(), plot_vals.max(), 200)
        ax2.plot(x_grid, kde(x_grid), color="crimson", linewidth=2,
                 label="KDE Curve")
    except ImportError:
        ax2.plot([], [], label="KDE (requires scipy)")

    ax2.set_xlabel(xlabel, fontsize=10)
    ax2.set_ylabel("Density", fontsize=10)
    ax2.set_title(f"{target_col} Distribution{title_suffix}".strip(), fontsize=12)
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", alpha=0.3)

    # ══════════════════════════════════════════════════════════
    # Subplot 3: Scatter plot (bottom-left)
    # ══════════════════════════════════════════════════════════
    ax3 = axes[1, 0]

    # Find suitable x-axis column
    x_plot_col = None
    for candidate in ["interaction_rate", "coin", "favorite", "like"]:
        if candidate in numeric_df.columns:
            x_plot_col = candidate
            break

    if x_plot_col is None:
        x_plot_col = [c for c in numeric_df.columns if c != target_col][0]

    plot_df = numeric_df[[x_plot_col, target_col]].dropna()

    if len(plot_df) > 0:
        x_vals = plot_df[x_plot_col].values
        y_vals = plot_df[target_col].values

        scatter = ax3.scatter(x_vals, y_vals, c=y_vals, cmap="viridis",
                              alpha=0.6, s=30, edgecolors="none")

        cbar3 = fig.colorbar(scatter, ax=ax3, fraction=0.046, pad=0.04)
        cbar3.set_label(target_col, fontsize=9)

        # Trend line
        try:
            mask = np.isfinite(x_vals) & np.isfinite(y_vals)
            if mask.sum() > 2:
                coeffs = np.polyfit(x_vals[mask], y_vals[mask], deg=1)
                trend = np.poly1d(coeffs)
                x_sorted = np.sort(x_vals[mask])
                ax3.plot(x_sorted, trend(x_sorted), "r--", linewidth=1.5,
                         alpha=0.8,
                         label=f"Trend (y={coeffs[0]:.2e}x+{coeffs[1]:.2e})")
                ax3.legend(fontsize=8)
        except Exception:
            pass
    else:
        ax3.text(0.5, 0.5, "Insufficient data for scatter plot",
                 ha="center", va="center", transform=ax3.transAxes)

    ax3.set_xlabel(x_plot_col, fontsize=10)
    ax3.set_ylabel(target_col, fontsize=10)
    ax3.set_title(f"{target_col} vs {x_plot_col}", fontsize=12)
    ax3.grid(alpha=0.3)

    # ══════════════════════════════════════════════════════════
    # Subplot 4: Summary text panel (bottom-right)
    # ══════════════════════════════════════════════════════════
    ax4 = axes[1, 1]
    ax4.axis("off")

    summary_lines = [
        "DATA SUMMARY",
        f"Total samples: {len(df)}",
        f"Features: {numeric_df.shape[1]}",
        f"Target: {target_col}",
        "",
        "TARGET STATS",
        f"Min: {data_vals.min():,.0f}",
        f"Max: {data_vals.max():,.0f}",
        f"Mean: {data_vals.mean():,.0f}",
        f"Median: {np.median(data_vals):,.0f}",
        f"Std:  {data_vals.std():,.0f}",
        "",
        "TOP-5 CORRELATED FEATURES",
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

    # ── Save ─────────────────────────────────────────────────
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    print(f"[Viz] Chart saved -> {os.path.abspath(output_path)}")

    return os.path.abspath(output_path)


# ── Standalone entry ────────────────────────────────────────

if __name__ == "__main__":
    if os.path.exists("data/processed_data.csv"):
        generate_plots("data/processed_data.csv", "data/visualization.png")
    else:
        print("Run analyzer.py preprocessing first")
