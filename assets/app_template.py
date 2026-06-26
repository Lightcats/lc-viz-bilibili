# -*- coding: utf-8 -*-
# 文件名: assets/app_template.py
# Streamlit 交互看板模板
# 本文件定义 APP_TEMPLATE 字符串，由 main_gui.py 动态写入 app.py

APP_TEMPLATE = r'''# -*- coding: utf-8 -*-
"""
B站知识区爆款视频特征分析 - Streamlit 交互看板
自动生成自 main_gui.py
"""

import pickle
import warnings
import pandas as pd
import numpy as np
import streamlit as st

warnings.filterwarnings("ignore")

# ── 页面配置 ────────────────────────────────────────────────
st.set_page_config(
    page_title="B站知识区视频分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 B站知识区爆款视频特征分析")
st.markdown("基于 LinearRegression 的播放量预测看板")

# ── 加载数据 ────────────────────────────────────────────────

@st.cache_data
def load_data(path="data/processed_data.csv"):
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
        return df
    except FileNotFoundError:
        st.error(f"数据文件未找到: {path}")
        return None


@st.cache_resource
def load_model(path="data/model.pkl"):
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        st.error(f"模型文件未找到: {path}")
        return None


df = load_data()
model_data = load_model()

# ── 主区域：数据预览 ────────────────────────────────────────
st.header("📋 原始数据预览")

if df is not None:
    st.dataframe(df.head(10), use_container_width=True)
    st.caption(f"数据集共 {len(df)} 行, {len(df.columns)} 列")
else:
    st.stop()

# ── 侧边栏：特征输入 ────────────────────────────────────────
st.sidebar.header("🎛️ 特征调节面板")

if model_data is None:
    st.sidebar.warning("模型未加载，请先训练模型")
    st.stop()

model = model_data["model"]
features = model_data["features"]
r2 = model_data.get("r2", None)

st.sidebar.success(f"模型 R² = {r2:.4f}" if r2 else "模型已加载")
st.sidebar.markdown("---")
st.sidebar.markdown("**调整以下特征值进行预测**")

# 为每个特征创建滑块输入
user_input = {}
for feat in features:
    if df is not None and feat in df.columns:
        col_vals = df[feat].dropna()
        if len(col_vals) == 0:
            min_v, max_v, default_v = 0.0, 1.0, 0.5
        else:
            min_v = float(col_vals.min())
            max_v = float(col_vals.max())
            default_v = float(col_vals.median())

        # 根据数值范围决定步长
        span = max_v - min_v
        step_val = 1.0 if span > 100 else (0.1 if span > 1 else 0.01)

        user_input[feat] = st.sidebar.slider(
            label=f"{feat}",
            min_value=min_v,
            max_value=max_v,
            value=default_v,
            step=step_val,
            format="%.2f" if step_val < 1 else "%.0f",
        )
    else:
        user_input[feat] = st.sidebar.number_input(
            label=f"{feat} (手动输入)",
            value=0.0,
            step=0.1,
        )

# ── 预测区域 ────────────────────────────────────────────────
st.header("🎯 播放量预测")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    predict_clicked = st.button("🚀 开始预测", type="primary", use_container_width=True)

    if predict_clicked:
        try:
            # 构造输入 DataFrame
            input_df = pd.DataFrame([user_input])
            # 确保列顺序与训练时一致
            input_df = input_df[features]

            prediction = model.predict(input_df)[0]
            pred_int = int(round(prediction))

            st.balloons()
            st.markdown("### ✅ 预测结果")

            # 用 metric 组件展示
            st.metric(
                label="预测播放量",
                value=f"{pred_int:,}",
                delta=f"{'🔥 爆款潜力' if pred_int > 100000 else '📈 普通热度'}",
            )

            # 进度条可视化
            max_possible = max(df["view"].max(), pred_int) if df is not None else pred_int
            pct = min(pred_int / max_possible * 100, 100) if max_possible > 0 else 0
            st.progress(pct / 100)
            st.caption(f"相对当前数据最高播放量的 {pct:.1f}%")

            # 显示输入特征
            with st.expander("📝 查看输入特征值"):
                st.json(user_input)

        except Exception as e:
            st.error(f"预测失败: {e}")
            st.info("提示: 请检查特征列是否与模型训练时一致")

# ── 页脚 ────────────────────────────────────────────────────
st.markdown("---")
st.caption("B站知识区爆款视频特征分析工具 | 数据来源: Bilibili API")
'''

if __name__ == "__main__":
    # 直接运行此文件仅打印模板（供调试用）
    print(APP_TEMPLATE[:200] + "...")
    print(f"\n模板长度: {len(APP_TEMPLATE)} 字符")
