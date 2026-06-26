# -*- coding: utf-8 -*-
# 文件名: src/analyzer.py
# B站知识区视频特征分析 - 数据处理与建模核心逻辑
# 供 main_gui.py 调用

import os
import sys
import pickle
import warnings
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

warnings.filterwarnings("ignore", category=UserWarning)


def preprocess_data(input_path="data/raw_data.csv",
                    output_path="data/processed_data.csv"):
    """
    数据预处理流水线。

    步骤：
        1. 读取 CSV
        2. pubdate 时间戳 → datetime → 提取 hour / weekday
        3. 计算衍生指标：title_len, interaction_rate
        4. 清洗：删除全空列 → 删除含缺失值行 → 删除重复行
        5. 输出清洗后的 CSV，并确保 'view' 为最后一列
        6. 返回 (清洗前行数, 清洗后行数)

    参数
    ----------
    input_path : str
        原始数据CSV路径。
    output_path : str
        处理后数据CSV路径。

    返回
    -------
    tuple (before_clean, after_clean)
    """
    print("[预处理] 读取数据 ...")
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"未找到输入文件: {input_path}")

    df = pd.read_csv(input_path, encoding="utf-8-sig")
    before_clean = len(df)
    print(f"[预处理] 原始数据 {before_clean} 行, {len(df.columns)} 列")

    # ── 1. 时间戳处理 ──────────────────────────────────────
    if "pubdate" in df.columns:
        df["pubdate"] = pd.to_datetime(df["pubdate"], unit="s", errors="coerce")
        df["hour"] = df["pubdate"].dt.hour.astype("Int64")
        df["weekday"] = df["pubdate"].dt.weekday.astype("Int64")
        print("[预处理] 已提取 hour / weekday")
    else:
        print("[预处理] 警告: 未找到 pubdate 列")

    # ── 2. 衍生指标 ────────────────────────────────────────
    if "title" in df.columns:
        df["title_len"] = df["title"].astype(str).str.len()
        print("[预处理] 已计算 title_len")
    else:
        df["title_len"] = 0

    like_col = "like" if "like" in df.columns else None
    favorite_col = "favorite" if "favorite" in df.columns else None
    coin_col = "coin" if "coin" in df.columns else None
    view_col = "view" if "view" in df.columns else None

    if all(col is not None for col in [like_col, favorite_col, coin_col, view_col]):
        # 防止除以零
        df["interaction_rate"] = (
            (df[like_col] + df[favorite_col] + df[coin_col])
            / df[view_col].replace(0, np.nan)
        )
        print("[预处理] 已计算 interaction_rate")
    else:
        df["interaction_rate"] = 0.0
        print("[预处理] 警告: 缺少计算 interaction_rate 所需的列")

    # ── 3. 数据清洗 ────────────────────────────────────────
    # 3a. 删除全空列
    before_cols = len(df.columns)
    df = df.dropna(axis=1, how="all")
    dropped_cols = before_cols - len(df.columns)
    if dropped_cols > 0:
        print(f"[预处理] 删除了 {dropped_cols} 个全空列")

    # 3b. 删除含缺失值的行
    before_rows = len(df)
    df = df.dropna()
    dropped_rows = before_rows - len(df)
    if dropped_rows > 0:
        print(f"[预处理] 删除了 {dropped_rows} 个含缺失值的行")

    # 3c. 删除重复行
    before_rows = len(df)
    df = df.drop_duplicates()
    dup_rows = before_rows - len(df)
    if dup_rows > 0:
        print(f"[预处理] 删除了 {dup_rows} 个重复行")

    # ── 4. 重新排列列: 保证 view 在最后一列 ────────────────
    cols = df.columns.tolist()
    if "view" in cols:
        cols.remove("view")
        cols.append("view")
        df = df[cols]
        print("[预处理] 已将 view 列移至末尾")

    after_clean = len(df)
    print(f"[预处理] 完成！清洗前 {before_clean} 行 -> 清洗后 {after_clean} 行")

    # 保存
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[预处理] 已保存 -> {os.path.abspath(output_path)}")

    return before_clean, after_clean


def train_model(input_path="data/processed_data.csv", model_path="data/model.pkl"):
    """
    基于线性回归训练播放量预测模型。

    步骤：
        1. 读取预处理后的 CSV
        2. 自动识别所有数值列，最后一列作为 y（目标 = view）
        3. 其余数值列作为 X（特征）
        4. 训练 LinearRegression
        5. 计算 R^2
        6. 序列化模型及特征名到 .pkl
        7. 返回 (r2_score, feature_names)

    参数
    ----------
    input_path : str
        预处理后的数据CSV路径。
    model_path : str
        模型输出路径 (.pkl)。

    返回
    -------
    tuple (r2, feature_names)
        r2 : float  决定系数
        feature_names : list  使用的特征列名
    """
    print("[建模] 读取预处理数据 ...")
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"未找到输入文件: {input_path}")

    df = pd.read_csv(input_path, encoding="utf-8-sig")
    print(f"[建模] 数据 {len(df)} 行, {len(df.columns)} 列")

    # ── 1. 筛选数值列 ──────────────────────────────────────
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    print(f"[建模] 数值列: {numeric_cols}")

    if len(numeric_cols) < 2:
        raise ValueError(
            f"数值列不足（当前 {len(numeric_cols)} 列），至少需要 1 个特征 + 1 个目标"
        )

    # 最后一列数值作为 y
    y_col = numeric_cols[-1]
    x_cols = numeric_cols[:-1]

    print(f"[建模] 目标变量 (y): {y_col}")
    print(f"[建模] 特征变量 (X): {x_cols}")

    X = df[x_cols].values
    y = df[y_col].values

    # ── 2. 训练 ────────────────────────────────────────────
    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    r2 = r2_score(y, y_pred)

    print(f"[建模] 训练完成！R^2 = {r2:.4f}")
    print(f"[建模] 特征数 = {len(x_cols)}")

    # ── 3. 保存模型（含特征名） ────────────────────────────
    model_data = {
        "model": model,
        "features": x_cols,
        "r2": r2,
    }
    with open(model_path, "wb") as f:
        pickle.dump(model_data, f)
    print(f"[建模] 模型已保存 -> {os.path.abspath(model_path)}")

    return r2, x_cols


# ── 独立运行入口 ────────────────────────────────────────────

if __name__ == "__main__":
    # 独立测试流程
    os.makedirs("data", exist_ok=True)
    if os.path.exists("data/raw_data.csv"):
        before, after = preprocess_data("data/raw_data.csv", "data/processed_data.csv")
        print(f"\n预处理结果: {before} -> {after} 行")
        if os.path.exists("data/processed_data.csv"):
            r2, feats = train_model("data/processed_data.csv", "data/model.pkl")
            print(f"建模结果: R^2={r2:.4f}, 特征={feats}")
    else:
        print("请先使用 src/scraper.py 采集数据，或准备 data/raw_data.csv")
