# -*- coding: utf-8 -*-
# 文件名: src/scraper.py
# B站知识区数据爬虫模块
# 功能：调用B站公开API采集知识区热门视频数据，保存为CSV

import os
import time
import random
import requests
import pandas as pd

# ── 工具函数：默认日志打印到终端 ─────────────────────────
_LOG = print


def _set_logger(func):
    """全局替换日志函数（供 GUI 注入回调）"""
    global _LOG
    _LOG = func


# ── 浏览器伪装 ──────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
]

# ── 知识分区TID映射 ─────────────────────────────────────────
KNOWLEDGE_TIDS = {
    36: "知识", 201: "科学科普", 124: "社科人文", 228: "财经",
    207: "校园学习", 208: "职业职场", 209: "设计创意", 229: "野生技能协会",
}

# ── 全局 Session（复用连接 + 持有 cookies） ─────────────────
_SESSION = requests.Session()


def _init_session():
    """先访问B站首页获取 cookies，提高后续API请求的成功率"""
    try:
        resp = _SESSION.get(
            "https://www.bilibili.com/",
            headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            timeout=10,
        )
        resp.encoding = "utf-8"
    except requests.RequestException:
        pass


# ── 工具函数 ────────────────────────────────────────────────


def _random_headers():
    """生成完整的随机请求头"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }


def _fetch_json(url, timeout=15):
    """发送GET请求并解析JSON响应，失败返回None"""
    try:
        resp = _SESSION.get(url, headers=_random_headers(), timeout=timeout)
        if resp.status_code != 200:
            _LOG(f"[WARN] HTTP {resp.status_code} <- {url}")
            return None
        data = resp.json()
        if data.get("code") != 0:
            _LOG(f"[WARN] API code={data.get('code')}, msg={data.get('message', '')} <- {url}")
            return None
        return data
    except requests.RequestException as e:
        _LOG(f"[ERROR] 请求失败 {url} -> {e}")
        return None


def _extract_video(item):
    """从API返回的单条视频条目中提取目标字段"""
    stat = item.get("stat", {})
    owner = item.get("owner", {})
    return {
        "title": item.get("title", "").strip(),
        "owner_name": owner.get("name", ""),
        "pubdate": item.get("pubdate", 0),
        "duration": item.get("duration", 0),
        "view": stat.get("view", 0),
        "danmaku": stat.get("danmaku", 0),
        "reply": stat.get("reply", 0),
        "favorite": stat.get("favorite", 0),
        "coin": stat.get("coin", 0),
        "share": stat.get("share", 0),
        "like": stat.get("like", 0),
        "tid": item.get("tid", 0),
        "tname": item.get("tname", ""),
        "videos": item.get("videos", 1),
    }


# ── 数据源采集函数 ──────────────────────────────────────────


def fetch_popular_list(pages=3):
    """热门推荐接口：/x/web-interface/popular"""
    all_videos = []
    base_url = "https://api.bilibili.com/x/web-interface/popular"

    for pn in range(1, pages + 1):
        url = f"{base_url}?pn={pn}&ps=50"
        _LOG(f"[爬虫] 正在采集 热门推荐 第{pn}页 ...")
        data = _fetch_json(url)
        if data is None:
            _LOG(f"[爬虫] 热门推荐 第{pn}页 采集失败，跳过")
            continue

        video_list = data.get("data", {}).get("list", [])
        for item in video_list:
            all_videos.append(_extract_video(item))

        _LOG(f"[爬虫] 热门推荐 第{pn}页 获取 {len(video_list)} 条，"
             f"累计 {len(all_videos)} 条")

        time.sleep(random.uniform(0.5, 1.5))

    return all_videos


def fetch_knowledge_zone(pages=3):
    """知识区分区动态接口：/x/web-interface/dynamic/region?rid=36"""
    all_videos = []
    base_url = "https://api.bilibili.com/x/web-interface/dynamic/region"

    for pn in range(1, pages + 1):
        url = f"{base_url}?rid=36&ps=50&pn={pn}"
        _LOG(f"[爬虫] 正在采集 知识区动态 第{pn}页 ...")
        data = _fetch_json(url)
        if data is None:
            _LOG(f"[爬虫] 知识区动态 第{pn}页 采集失败，跳过")
            continue

        video_list = data.get("data", {}).get("archives", [])
        for item in video_list:
            all_videos.append(_extract_video(item))

        _LOG(f"[爬虫] 知识区动态 第{pn}页 获取 {len(video_list)} 条，"
             f"累计 {len(all_videos)} 条")

        time.sleep(random.uniform(0.5, 1.5))

    return all_videos


# ── 主入口 ──────────────────────────────────────────────────


def fetch_and_save(filename="data/raw_data.csv", pages=5, append=False):
    """
    综合采集B站知识区热门视频数据并保存为CSV。

    参数
    ----------
    filename : str
        输出CSV文件路径。
    pages : int
        每个主源采集的页数（每页约 40~50 条）。
    append : bool
        True=追加合并旧数据；False=直接覆盖。

    返回 pandas.DataFrame
    """
    _LOG("=" * 50)
    _LOG("B站知识区数据爬虫 启动")
    _LOG("=" * 50)

    _init_session()
    _LOG("[爬虫] Session 初始化完成")

    # 1. 热门推荐
    popular_data = fetch_popular_list(pages=pages)
    _LOG(f"[爬虫] 热门推荐采集完毕，共 {len(popular_data)} 条")

    # 2. 知识区动态
    knowledge_data = fetch_knowledge_zone(pages=pages)
    _LOG(f"[爬虫] 知识区动态采集完毕，共 {len(knowledge_data)} 条")

    # 3. 合并去重
    all_videos = popular_data + knowledge_data
    seen = set()
    unique_videos = []
    for v in all_videos:
        key = (v["title"], v["owner_name"])
        if key not in seen:
            seen.add(key)
            unique_videos.append(v)

    df_new = pd.DataFrame(unique_videos)
    _LOG(f"[爬虫] 新采集去重后共 {len(df_new)} 条")

    # 4. 追加/覆盖
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

    if append and os.path.exists(filename):
        try:
            df_old = pd.read_csv(filename, encoding="utf-8-sig")
            _LOG(f"[爬虫] 读取已有数据 {len(df_old)} 条，准备合并")
            df_all = pd.concat([df_old, df_new], ignore_index=True)
            df_all = df_all.drop_duplicates(subset=["title", "owner_name"],
                                            keep="last")
            _LOG(f"[爬虫] 合并去重后共 {len(df_all)} 条")
        except Exception:
            _LOG(f"[爬虫] 读取旧文件失败，直接使用新数据")
            df_all = df_new
    else:
        df_all = df_new
        _LOG(f"[爬虫] 覆盖模式：直接写入")

    # 5. 筛选知识区
    knowledge_tids = set(KNOWLEDGE_TIDS.keys())
    before = len(df_all)
    df_in = df_all[df_all["tid"].isin(knowledge_tids)]
    _LOG(f"[爬虫] 知识区筛选: {before} -> {len(df_in)} 条")

    if len(df_in) >= 10:
        df_final = df_in.reset_index(drop=True)
    else:
        _LOG(f"[爬虫] 知识区视频不足10条，保留全部数据")
        df_final = df_all.reset_index(drop=True)

    # 6. 保存
    df_final.to_csv(filename, index=False, encoding="utf-8-sig")
    _LOG(f"[爬虫] 数据已保存 -> {os.path.abspath(filename)} ({len(df_final)} 条)")
    _LOG("=" * 50)

    return df_final


# ── 独立运行入口 ────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    fetch_and_save("data/raw_data.csv", pages=5, append=False)
