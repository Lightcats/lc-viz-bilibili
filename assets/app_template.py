# -*- coding: utf-8 -*-
# 文件名: assets/app_template.py
# Streamlit 交互看板模板
# 提供4标签页完整流程：数据采集 → 数据处理 → 可视化 → 预测
# 由 main_gui.py 动态写入 app.py

APP_TEMPLATE = r'''# -*- coding: utf-8 -*-
"""
B站知识区爆款视频特征分析 - 交互看板
完整工作流：采集 → 处理 → 可视化 → 预测
"""

import os
import sys
import io
import contextlib
import pickle
import warnings
import pandas as pd
import numpy as np
import streamlit as st

warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from src.scraper import fetch_and_save
from src.analyzer import preprocess_data, train_model
from src.visualizer import generate_plots

# ================================================================
#  页面配置
# ================================================================
st.set_page_config(
    page_title="B站知识区视频分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 B站知识区爆款视频特征分析")
st.markdown("完整工作流：采集 → 预处理 → 可视化 → 预测")

# ================================================================
#  会话状态初始化
# ================================================================
for key, path in [
    ("raw_exists", "data/raw_data.csv"),
    ("processed_exists", "data/processed_data.csv"),
    ("model_exists", "data/model.pkl"),
    ("viz_exists", "data/visualization.png"),
]:
    if key not in st.session_state:
        st.session_state[key] = os.path.exists(path)

# ================================================================
#  标签页
# ================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🕷️ 数据采集",
    "⚙️ 数据处理",
    "📈 可视化图表",
    "🎯 播放量预测",
])

# ---------------------------------------------------------------
#  标签页 1：数据采集
# ---------------------------------------------------------------
with tab1:
    st.header("数据采集")
    st.markdown("通过爬虫或本地文件导入B站知识区视频数据。")

    col_a, col_b = st.columns(2)

    # --- 方式 A：爬虫采集 ---
    with col_a:
        st.subheader("🕷️ 爬虫采集")
        st.markdown("调用B站API采集知识区热门视频。")

        pages = st.number_input("每源采集页数", min_value=1, max_value=20,
                                value=3, step=1,
                                help="每页约40~50条，两源合计约 pages×100 条")

        if st.button("🚀 开始爬取", width='stretch'):
            progress_placeholder = st.empty()
            output_placeholder = st.empty()

            log_capture = io.StringIO()
            with contextlib.redirect_stdout(log_capture):
                with st.spinner("正在调用B站API采集数据 ..."):
                    try:
                        df = fetch_and_save(filename="data/raw_data.csv",
                                            pages=pages)
                        st.session_state.raw_exists = True
                        progress_placeholder.success(
                            f"✅ 采集完成！共 {len(df)} 条视频")
                    except Exception as e:
                        progress_placeholder.error(f"❌ 采集失败: {e}")

            with output_placeholder.expander("查看采集日志"):
                st.code(log_capture.getvalue())

        if st.session_state.raw_exists:
            st.info("📁 数据文件: `data/raw_data.csv`")
            if st.checkbox("预览原始数据", key="preview_raw"):
                try:
                    df_raw = pd.read_csv("data/raw_data.csv", encoding="utf-8-sig")
                    st.dataframe(df_raw.head(10), width='stretch')
                    st.caption(f"{len(df_raw)} 行 x {len(df_raw.columns)} 列")
                except Exception:
                    st.warning("无法读取数据文件")

    # --- 方式 B：上传文件 ---
    with col_b:
        st.subheader("📂 上传文件")
        st.markdown("从本机选择 CSV 或 Excel 文件导入。")

        uploaded_file = st.file_uploader(
            "选择 CSV 或 Excel 文件",
            type=["csv", "xlsx"],
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            os.makedirs("data", exist_ok=True)
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_up = pd.read_csv(uploaded_file, encoding="utf-8-sig")
                    df_up.to_csv("data/raw_data.csv", index=False,
                                 encoding="utf-8-sig")
                else:
                    df_up = pd.read_excel(uploaded_file, engine="openpyxl")
                    df_up.to_csv("data/raw_data.csv", index=False,
                                 encoding="utf-8-sig")

                st.session_state.raw_exists = True
                st.success(f"✅ 已上传 {uploaded_file.name} ({len(df_up)} 行)")
                st.dataframe(df_up.head(10), width='stretch')
            except Exception as e:
                st.error(f"文件读取失败: {e}")

    # --- 管道状态指示器 ---
    st.divider()
    st.caption("**流程状态：**")
    status_cols = st.columns(4)
    status_cols[0].metric("原始数据",
                          "✅ 就绪" if st.session_state.raw_exists else "⏳ 等待")
    status_cols[1].metric("处理后数据",
                          "✅ 就绪" if st.session_state.processed_exists else "⏳ 等待")
    status_cols[2].metric("模型",
                          "✅ 就绪" if st.session_state.model_exists else "⏳ 等待")
    status_cols[3].metric("可视化",
                          "✅ 就绪" if st.session_state.viz_exists else "⏳ 等待")

# ---------------------------------------------------------------
#  标签页 2：数据处理
# ---------------------------------------------------------------
with tab2:
    st.header("数据处理")
    st.markdown("对原始数据进行预处理：特征提取、清洗、保存。")

    if not st.session_state.raw_exists:
        st.warning("⚠️ 尚未采集数据，请先在「数据采集」标签页中收集数据。")
    else:
        st.info("📁 原始数据: `data/raw_data.csv`")

        if st.button("⚙️ 执行预处理", type="primary",
                     width='stretch'):
            with st.spinner("正在预处理数据 ..."):
                try:
                    before, after = preprocess_data(
                        input_path="data/raw_data.csv",
                        output_path="data/processed_data.csv",
                    )
                    st.session_state.processed_exists = True
                    st.success("✅ 预处理完成！")
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("清洗前", f"{before} 行")
                    col_m2.metric("清洗后", f"{after} 行")
                    col_m3.metric("删除", f"{before - after} 行",
                                  delta_color="inverse")
                except Exception as e:
                    st.error(f"预处理失败: {e}")

        if st.session_state.processed_exists:
            st.divider()
            st.subheader("预处理数据预览")
            try:
                df_proc = pd.read_csv("data/processed_data.csv",
                                      encoding="utf-8-sig")
                st.dataframe(df_proc.head(10), width='stretch')
                st.caption(f"{len(df_proc)} 行 x {len(df_proc.columns)} 列")

                derived = [c for c in df_proc.columns
                           if c not in pd.read_csv("data/raw_data.csv",
                                                   encoding="utf-8-sig").columns]
                if derived:
                    st.info(f"**新增衍生列:** {', '.join(derived)}")
            except Exception as e:
                st.warning(f"无法预览: {e}")

# ---------------------------------------------------------------
#  标签页 3：可视化图表
# ---------------------------------------------------------------
with tab3:
    st.header("📈 可视化图表与数据分析")
    st.markdown("基于处理后数据生成的统计图表与深度分析。")

    if not st.session_state.processed_exists:
        st.warning("⚠️ 尚未处理数据，请先在「数据处理」标签页中执行预处理。")
    else:
        # 加载数据
        try:
            df_viz = pd.read_csv("data/processed_data.csv", encoding="utf-8-sig")
            num_cols = df_viz.select_dtypes(include=[np.number]).columns.tolist()
            target = num_cols[-1] if num_cols else None
        except Exception:
            df_viz = None
            num_cols = []
            target = None

        # ── 顶部：数据概览卡片 ──
        if df_viz is not None:
            st.subheader("📊 数据概览")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("总样本量", f"{len(df_viz)}")
            c2.metric("特征总数", f"{len(df_viz.columns)}")
            c3.metric("数值特征", f"{len(num_cols)}")
            c4.metric("缺失值", f"{df_viz.isnull().sum().sum()}")
            c5.metric("目标变量", target)

        # ── 主内容区：图表 + 侧边分析 ──
        col_v1, col_v2 = st.columns([3, 1])

        with col_v2:
            st.caption("图表操作")
            if st.button("🔄 重新生成图表", width='stretch'):
                with st.spinner("正在生成图表 ..."):
                    try:
                        generate_plots(
                            data_path="data/processed_data.csv",
                            output_path="data/visualization.png",
                        )
                        st.session_state.viz_exists = True
                        st.success("✅ 图表已重新生成！")
                    except Exception as e:
                        st.error(f"图表生成失败: {e}")

            # 快速统计
            if df_viz is not None and target:
                st.divider()
                st.caption("目标变量统计")
                try:
                    vals = df_viz[target].dropna()
                    st.metric("最小值", f"{vals.min():,.0f}")
                    st.metric("最大值", f"{vals.max():,.0f}")
                    st.metric("平均值", f"{vals.mean():,.0f}")
                    st.metric("中位数", f"{np.median(vals):,.0f}")
                    st.metric("标准差", f"{vals.std():,.0f}")
                except Exception:
                    pass

        with col_v1:
            if st.session_state.viz_exists and os.path.exists("data/visualization.png"):
                st.image("data/visualization.png", width='stretch')
            else:
                st.info("尚未生成图表，点击右侧「重新生成图表」按钮。")

        # ── 特征相关性分析 ──
        if df_viz is not None and target and len(num_cols) > 1:
            st.divider()
            st.subheader("🔗 特征与目标变量相关性分析")
            st.markdown("下图展示各数值特征与播放量的相关系数（正值 = 正相关，负值 = 负相关）。")

            try:
                corr = df_viz[num_cols].corr()[target].drop(target).sort_values()
                corr_df = corr.reset_index()
                corr_df.columns = ["特征", "相关系数"]

                col_c1, col_c2 = st.columns([2, 1])
                with col_c1:
                    st.bar_chart(corr_df.set_index("特征"), height=350)

                with col_c2:
                    st.markdown("**Top 正向相关**")
                    top_pos = corr_df.sort_values("相关系数", ascending=False).head(3)
                    for _, r in top_pos.iterrows():
                        st.success(f"**{r['特征']}**: {r['相关系数']:+.3f}")

                    st.markdown("**Top 负向相关**")
                    top_neg = corr_df.sort_values("相关系数").head(3)
                    for _, r in top_neg.iterrows():
                        st.error(f"**{r['特征']}**: {r['相关系数']:+.3f}")
            except Exception:
                st.warning("相关性分析失败")

        # ── 关键特征分布 ──
        if df_viz is not None and target and len(num_cols) > 1:
            st.divider()
            st.subheader("📋 关键特征分布速览")
            st.markdown("选择特征查看其分布情况。")

            # 选择与目标相关度最高的几个特征展示
            try:
                corr_abs = df_viz[num_cols].corr()[target].drop(target).abs()
                top_feats = corr_abs.sort_values(ascending=False).head(6).index.tolist()
            except Exception:
                top_feats = [c for c in num_cols if c != target][:6]

            selected_feat = st.selectbox("选择特征查看分布", top_feats)

            if selected_feat:
                col_d1, col_d2 = st.columns(2)

                with col_d1:
                    st.caption("直方图")
                    feat_vals = df_viz[selected_feat].dropna()
                    vc = feat_vals.value_counts().sort_index().head(30).reset_index()
                    vc.columns = [selected_feat, "频次"]
                    st.bar_chart(vc.set_index(selected_feat), height=250)

                with col_d2:
                    st.caption("描述统计")
                    s = df_viz[selected_feat].describe()
                    s_df = pd.DataFrame({
                        "统计量": ["计数", "均值", "标准差", "最小值", "25%", "50%", "75%", "最大值"],
                        "值": [f"{s['count']:.0f}", f"{s['mean']:.2f}", f"{s['std']:.2f}",
                               f"{s['min']:.2f}", f"{s['25%']:.2f}", f"{s['50%']:.2f}",
                               f"{s['75%']:.2f}", f"{s['max']:.2f}"],
                    })
                    st.dataframe(s_df, hide_index=True, width='stretch')

        # ── 数据样本预览 ──
        if df_viz is not None:
            st.divider()
            st.subheader("👁️ 数据样本预览")
            with st.expander("展开查看前 10 条数据"):
                st.dataframe(df_viz.head(10), width='stretch')
                st.caption(f"{len(df_viz)} 行 x {len(df_viz.columns)} 列")

# ---------------------------------------------------------------
#  标签页 4：播放量预测
# ---------------------------------------------------------------
with tab4:
    st.header("🎯 播放量预测")
    st.markdown("""
    基于 **线性回归模型**，根据视频的关键特征（时长、弹幕、点赞、收藏等）预测其播放量。
    左侧边栏可调节各特征值，点击「预测播放量」查看结果与解读。
    """)

    if not st.session_state.processed_exists:
        st.warning("⚠️ 尚未处理数据，请先在「数据处理」标签页中执行预处理。")
    else:
        # ── 自动训练 ──
        if not st.session_state.model_exists:
            if st.button("🏋️ 立即训练模型", type="primary",
                         width='stretch'):
                with st.spinner("正在训练线性回归模型 ..."):
                    try:
                        r2, feats = train_model(
                            input_path="data/processed_data.csv",
                            model_path="data/model.pkl",
                        )
                        st.session_state.model_exists = True
                        st.success(f"✅ 模型训练完成！R² = {r2:.4f}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"训练失败: {e}")

        if st.session_state.model_exists:
            try:
                with open("data/model.pkl", "rb") as f:
                    model_data = pickle.load(f)

                model = model_data["model"]
                features = model_data["features"]
                r2 = model_data.get("r2", None)

                df_pred = pd.read_csv("data/processed_data.csv",
                                      encoding="utf-8-sig")

                # ════════════════════════════════════════════════
                #  模型性能展示区
                # ════════════════════════════════════════════════
                with st.expander("📊 模型性能说明", expanded=False):
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("决定系数 R²", f"{r2:.4f}" if r2 else "N/A",
                                  help="R² 越接近 1 说明模型拟合越好。0.5 以上表示模型能解释一半以上的播放量变化。")
                    col_m2.metric("特征数量", f"{len(features)}",
                                  help="模型使用了多少个特征进行预测。")
                    col_m3.metric("训练样本", f"{len(df_pred)}",
                                  help="用于训练的数据条数。")

                    st.markdown("""
                    **R² 解读：**
                    - **R² > 0.7**：模型拟合良好，预测较可靠
                    - **0.4 < R² < 0.7**：模型有一定解释力，可做趋势参考
                    - **R² < 0.4**：模型解释力有限，结果仅供参考

                    影响播放量的因素复杂（算法推荐、标题吸引力、封面、时效性等），
                    线性模型难以完全捕捉所有非线性关系，因此 R² 在 0.4~0.7 属于正常范围。
                    """)

                # ════════════════════════════════════════════════
                #  特征重要性（回归系数）
                # ════════════════════════════════════════════════
                with st.expander("📌 各特征对播放量的影响（回归系数）", expanded=False):
                    st.markdown("""
                    回归系数表示该特征每增加 1 个单位，播放量预计变化的值。
                    **正值** = 该特征越高，播放量越高；**负值** = 该特征越高，播放量越低。
                    """)

                    coef_df = pd.DataFrame({
                        "特征": features,
                        "回归系数": model.coef_,
                    }).sort_values("回归系数", ascending=False)

                    col_b1, col_b2 = st.columns([2, 1])
                    with col_b1:
                        st.bar_chart(coef_df.set_index("特征"), height=300)
                    with col_b2:
                        st.markdown("**📈 正向促进（最高）**")
                        for _, r in coef_df.head(3).iterrows():
                            st.success(f"**{r['特征']}**: +{r['回归系数']:.2e}")

                        st.markdown("**📉 负向抑制（最低）**")
                        for _, r in coef_df.tail(3).iterrows():
                            st.error(f"**{r['特征']}**: {r['回归系数']:.2e}")

                # ════════════════════════════════════════════════
                #  侧边栏：特征调节
                # ════════════════════════════════════════════════
                st.sidebar.header("🎛️ 特征调节面板")
                if r2:
                    st.sidebar.success(f"模型 R² = {r2:.4f}")
                st.sidebar.markdown("---")
                st.sidebar.caption("拖动滑块调整各特征值，点击「预测播放量」查看结果")

                user_input = {}
                for feat in features:
                    if feat in df_pred.columns:
                        col_vals = df_pred[feat].dropna()
                        if len(col_vals) == 0:
                            min_v, max_v, default_v = 0.0, 1.0, 0.5
                        else:
                            min_v = float(col_vals.min())
                            max_v = float(col_vals.max())
                            default_v = float(col_vals.median())

                        span = max_v - min_v
                        step_val = 1.0 if span > 100 else (
                            0.1 if span > 1 else 0.01)

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
                            value=0.0, step=0.1,
                        )

                # ════════════════════════════════════════════════
                #  预测主区域
                # ════════════════════════════════════════════════
                col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
                with col_p2:
                    predict_clicked = st.button(
                        "🚀 预测播放量",
                        type="primary",
                        width='stretch',
                    )

                    if predict_clicked:
                        try:
                            input_df = pd.DataFrame([user_input])
                            input_df = input_df[features]

                            prediction = model.predict(input_df)[0]
                            pred_int = int(round(prediction))

                            st.balloons()
                            st.markdown("### ✅ 预测结果")
                            st.divider()

                            # ── 核心预测值 ──
                            st.metric(
                                label="📺 预测播放量",
                                value=f"{pred_int:,}",
                                delta=("🔥 爆款潜力"
                                       if pred_int > 100000
                                       else "📈 普通热度"),
                            )

                            # ── 百分位解读 ──
                            actual_views = df_pred["view"].dropna()
                            percentile = (actual_views < pred_int).mean() * 100

                            st.markdown("#### 📊 结果解读")
                            st.markdown(
                                f"该视频 **预测获得 {pred_int:,} 次播放**，"
                                f"**超过数据集中 {percentile:.1f}%** 的视频。"
                            )

                            # 进度条（相对数据最高值）
                            max_possible = max(actual_views.max(), pred_int)
                            pct = (min(pred_int / max_possible * 100, 100)
                                   if max_possible > 0 else 0)
                            st.progress(pct / 100)
                            st.caption(f"已达数据集中最高播放量的 {pct:.1f}%")

                            # ── 热度评级 ──
                            st.markdown("#### 🏆 热度评级")
                            q25, q50, q75 = (
                                actual_views.quantile(0.25),
                                actual_views.quantile(0.50),
                                actual_views.quantile(0.75),
                            )
                            if pred_int > q75:
                                st.success("🔥 **爆款潜力** — 预测播放量超过数据集中 75% 的视频")
                            elif pred_int > q50:
                                st.info("📈 **中等偏上** — 预测播放量超过数据集中 50% 的视频")
                            elif pred_int > q25:
                                st.warning("📊 **中等水平** — 预测播放量处于数据集中下游")
                            else:
                                st.error("📉 **偏低** — 预测播放量低于数据集中 75% 的视频")

                            st.divider()

                            # ── 特征贡献分解 ──
                            st.markdown("#### 🔍 特征贡献分解")
                            st.markdown("各特征对预测结果的贡献（= 回归系数 × 该特征值），"
                                        "绿色=正向推动播放量，红色=拉低播放量。")

                            base_pred = model.intercept_
                            contributions = model.coef_ * input_df.values[0]
                            contrib_df = pd.DataFrame({
                                "特征": features,
                                "贡献值": contributions,
                            }).sort_values("贡献值", ascending=False)

                            col_c1, col_c2 = st.columns([2, 1])
                            with col_c1:
                                st.bar_chart(contrib_df.set_index("特征"), height=250)
                            with col_c2:
                                st.metric("基线 (截距)", f"{base_pred:+,.0f}",
                                          help="当所有特征为0时的基准播放量")
                                top_feat = contrib_df.iloc[0]
                                st.success(f"**最大正向推动**\n{top_feat['特征']}: "
                                           f"+{top_feat['贡献值']:+,.0f}")
                                bottom_feat = contrib_df.iloc[-1]
                                st.error(f"**最大负向拉动**\n{bottom_feat['特征']}: "
                                         f"{bottom_feat['贡献值']:+,.0f}")

                            # ── 输入数据 vs 数据集均值 ──
                            st.divider()
                            st.markdown("#### ⚖️ 输入值与数据集对比")
                            st.markdown("你的输入值与训练数据平均值的对比，"
                                        "了解哪些特征设得比平均水平高/低。")

                            compare_data = []
                            for feat in features:
                                if feat in df_pred.columns:
                                    input_val = user_input[feat]
                                    mean_val = float(df_pred[feat].mean())
                                    delta = input_val - mean_val
                                    direction = "⬆ 高于均值" if delta > 0 else (
                                        "⬇ 低于均值" if delta < 0 else "➡ 等于均值")
                                    compare_data.append({
                                        "特征": feat,
                                        "输入值": f"{input_val:.2f}",
                                        "数据均值": f"{mean_val:.2f}",
                                        "差异": direction,
                                    })

                            st.dataframe(
                                pd.DataFrame(compare_data),
                                hide_index=True,
                                width='stretch',
                            )

                            # ── 输入特征原始值 ──
                            with st.expander("📝 查看输入特征原始值"):
                                st.json(user_input)

                        except Exception as e:
                            st.error(f"预测失败: {e}")
                            st.info("请检查特征列是否与训练数据一致。")

            except Exception as e:
                st.error(f"模型加载失败: {e}")

# ---------------------------------------------------------------
#  页脚
# ---------------------------------------------------------------
st.divider()
st.caption("B站知识区爆款视频特征分析 | "
           "数据来源: Bilibili 公开 API | "
           f"数据目录: {os.path.abspath('data')}")
'''

if __name__ == "__main__":
    print(f"模板长度: {len(APP_TEMPLATE)} 字符")
    print("使用 main_gui.py 第5步写入 app.py")
