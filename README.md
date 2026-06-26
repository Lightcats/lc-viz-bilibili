# B站知识区爆款视频特征分析

> 桌面端全流程数据分析工具 — 从数据采集、预处理、可视化、建模到 Streamlit 交互看板启动的完整闭环。

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动主程序（GUI）

```bash
python main_gui.py
```

### 3. 或直接启动 Streamlit 看板

```bash
# 先生成 app.py
python -c "from assets.app_template import APP_TEMPLATE; open('app.py','w',encoding='utf-8').write(APP_TEMPLATE)"
# 再启动看板
streamlit run app.py
```

---

## 功能模块

### GUI 界面流程（5步闭环）

| 步骤 | 功能 | 说明 |
|------|------|------|
| **① 数据采集** | 爬虫采集 **或** 导入本地文件 | 点击后弹窗二选一；爬虫支持覆盖/追加模式 |
| **② 数据预处理** | 自动清洗 + 特征工程 | 时间戳提取、计算互动率、去空去重 |
| **③ 多维度可视化** | 生成 4 子图统计画布（全英文标签） | 相关性热力图、分布直方图+KDE、散点图+趋势线 |
| **④ 数据建模** | LinearRegression 训练 | 自动 R² 评估，模型持久化 |
| **⑤ Streamlit 看板** | 启动完整交互看板 | 4标签页：采集→处理→可视化→预测 |

### Streamlit 看板功能（4 标签页）

| 标签页 | 功能 |
|--------|------|
| **数据采集** | 爬虫采集（可调页数）+ 上传 CSV/XLSX + 管道状态指示 |
| **数据处理** | 一键预处理 + 清洗前后对比 + 衍生列说明 |
| **可视化图表** | 展示统计大图 + 相关性分析 + 特征分布 + 数据预览 |
| **播放量预测** | 模型性能说明 + 特征重要性 + 侧边栏调参 + 预测结果解读（百分位/热度评级/贡献分解） |

### 数据采集两种方式详解

点击 **「1. 数据采集」** 按钮后弹出选择窗口：

| 方式 | 操作 | 适用场景 |
|------|------|----------|
| **爬虫采集** | 自动调用B站 API → 采集知识区视频 → 保存到 `data/` | 联网环境，无现成数据 |
| **导入本地文件** | 选择 `.csv` 或 `.xlsx` → 复制/转换到 `data/` | 已有数据文件 |

爬虫采集支持：
- **覆盖模式**（默认）：每次爬取完全替换旧数据
- **追加模式**：保留旧数据 + 新数据合并去重

### 辅助工具

各模块也可独立运行：

```bash
# 爬虫独立采集
python src/scraper.py                                    # 默认 3 页 → data/raw_data.csv
python -c "from src.scraper import fetch_and_save; fetch_and_save('data/raw_data.csv', pages=5, append=True)"

# 预处理 + 建模流水线（需先有 data/raw_data.csv）
python src/analyzer.py

# 可视化（需先有 data/processed_data.csv）
python src/visualizer.py

# 独立启动 Streamlit 看板
python -c "from assets.app_template import APP_TEMPLATE; open('app.py','w',encoding='utf-8').write(APP_TEMPLATE)"
streamlit run app.py
```

---

## 项目结构

```
lc-viz-bilibili/
├── main_gui.py                 # ★ 主程序入口（Tkinter GUI）
├── requirements.txt            # 依赖清单
├── README.md                   # 本文件
│
├── src/
│   ├── scraper.py              # B站知识区数据爬虫（支持日志回调注入）
│   ├── analyzer.py             # 数据预处理 + 线性回归建模
│   └── visualizer.py           # Matplotlib 可视化图表生成（英文标签）
│
├── assets/
│   └── app_template.py         # Streamlit 看板模板（4标签页完整流程，中文UI）
│
├── data/                       # [运行时生成] 所有数据文件
│   ├── raw_data.csv            #   原始数据
│   ├── processed_data.csv      #   预处理后数据
│   ├── model.pkl               #   训练好的模型（含特征名）
│   └── visualization.png       #   统计图表
│
└── app.py                      # [运行时生成] Streamlit 看板脚本
```

---

## 数据字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | str | 视频标题 |
| `owner_name` | str | UP主名称 |
| `pubdate` | int/datetime | 发布时间戳 → 预处理后转为 datetime 并提取 hour/weekday |
| `duration` | int | 视频时长（秒） |
| `view` | int | 播放量（模型预测目标） |
| `danmaku` / `reply` | int | 弹幕数 / 评论数 |
| `favorite` / `coin` / `share` | int | 收藏 / 投币 / 分享 |
| `like` | int | 点赞数 |
| `tid` / `tname` | int/str | 分区ID / 分区名称 |
| `videos` | int | 分P数 |
| `title_len` | int | *(衍生)* 标题字数 |
| `interaction_rate` | float | *(衍生)* (点赞+收藏+投币)/播放量 |

---

## 技术栈

- **GUI 框架**：Tkinter（Python 内置）
- **数据分析**：pandas, numpy
- **可视化**：matplotlib（imshow / 直方图 / KDE / 散点图）
- **机器学习**：scikit-learn（LinearRegression）
- **交互看板**：Streamlit
- **数据采集**：requests + B站公开 API（popular / region）
- **数据持久化**：CSV / pickle / PNG

---

## 注意事项

1. **B站 API 限制**：爬虫依赖 B站公开接口（`/x/web-interface/popular` 和 `/x/web-interface/dynamic/region`），如遇请求失败请稍后重试
2. **Streamlit 启动**：首次使用会动态生成 `app.py`，如未安装 streamlit 会在日志中提示
3. **重置流程**：仅恢复按钮状态和清空日志，不会删除 `data/` 目录下的文件
4. **数据要求**：建议准备至少 50 条以上的记录以获得有意义的建模结果
5. **日志实时显示**：爬虫运行时所有输出会实时显示在 GUI 日志框中（通过日志回调注入实现）
