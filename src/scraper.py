# -*- coding: utf-8 -*-
# 文件名: src/scraper.py
# B站知识区数据爬虫模块
# 功能：调用B站公开API采集知识区热门视频数据，保存为CSV

import os
import time
import random
import requests
import pandas as pd

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
        # 提取任何 Set-Cookie
        if resp.cookies:
            pass  # Session 自动保存
    except requests.RequestException:
        pass  # 首页请求失败不影响后续，只是少了 cookies


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
            print(f"[WARN] HTTP {resp.status_code} <- {url}")
            return None
        data = resp.json()
        if data.get("code") != 0:
            print(f"[WARN] API code={data.get('code')}, msg={data.get('message', '')} <- {url}")
            return None
        return data
    except requests.RequestException as e:
        print(f"[ERROR] 请求失败 {url} -> {e}")
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
    """
    从「热门推荐」接口采集数据。
    接口：/x/web-interface/popular
    每次返回约 40 条热门视频，通过 pn 参数分页。

    这是B站最稳定的公开API之一，无需特殊权限。
    """
    all_videos = []
    base_url = "https://api.bilibili.com/x/web-interface/popular"

    for pn in range(1, pages + 1):
        url = f"{base_url}?pn={pn}&ps=50"
        print(f"[爬虫] 正在采集 热门推荐 第{pn}页 ...")
        data = _fetch_json(url)
        if data is None:
            print(f"[爬虫] 热门推荐 第{pn}页 采集失败，跳过")
            continue

        video_list = data.get("data", {}).get("list", [])
        for item in video_list:
            all_videos.append(_extract_video(item))

        print(f"[爬虫] 热门推荐 第{pn}页 获取 {len(video_list)} 条，"
              f"累计 {len(all_videos)} 条")

        time.sleep(random.uniform(0.5, 1.5))

    return all_videos


def fetch_knowledge_zone(pages=3):
    """
    从「分区动态」接口采集知识区视频。
    接口：/x/web-interface/dynamic/region?rid=36&ps=50&pn={n}
    rid=36 为知识区，每次约 50 条，多页翻采。
    这个接口返回的是知识区最新热门内容，非常适合本项目的需求。
    """
    all_videos = []
    base_url = "https://api.bilibili.com/x/web-interface/dynamic/region"

    for pn in range(1, pages + 1):
        url = f"{base_url}?rid=36&ps=50&pn={pn}"
        print(f"[爬虫] 正在采集 知识区动态 第{pn}页 ...")
        data = _fetch_json(url)
        if data is None:
            print(f"[爬虫] 知识区动态 第{pn}页 采集失败，跳过")
            continue

        video_list = data.get("data", {}).get("archives", [])
        for item in video_list:
            all_videos.append(_extract_video(item))

        print(f"[爬虫] 知识区动态 第{pn}页 获取 {len(video_list)} 条，"
              f"累计 {len(all_videos)} 条")

        time.sleep(random.uniform(0.5, 1.5))

    return all_videos


def fetch_popular_series():
    """
    从「热门系列」接口一次性获取数据（作为补充）。
    接口：/x/web-interface/popular/series/one?number={n}
    注意：此接口有时限流，仅作为补充源。
    """
    all_videos = []
    base_url = "https://api.bilibili.com/x/web-interface/popular/series/one"

    for n in range(1, 6):
        url = f"{base_url}?number={n}"
        print(f"[爬虫] 尝试 热门系列 #{n} ...")
        data = _fetch_json(url)
        if data is None:
            continue

        video_list = data.get("data", {}).get("list", [])
        for item in video_list:
            all_videos.append(_extract_video(item))

        print(f"[爬虫] 热门系列 #{n} 获取 {len(video_list)} 条")
        time.sleep(random.uniform(1.0, 2.0))

    print(f"[爬虫] 热门系列共获取 {len(all_videos)} 条")
    return all_videos


# ── 主入口 ──────────────────────────────────────────────────


def fetch_and_save(filename="data/raw_data.csv", pages=5):
    """
    综合采集B站知识区热门视频数据并保存为CSV。
    使用多源策略保证数据量：

        1. 热门推荐（主源）：每页约 40 条，pages 页
        2. 知识区动态（主源）：每页约 50 条，pages 页
        3. 热门系列（补充源）：作为额外补充

    参数
    ----------
    filename : str
        输出CSV文件路径（相对路径）。
    pages : int
        每个主源采集的页数（每页约 40~50 条）。

    返回
    -------
    pandas.DataFrame
        采集到的视频数据。
    """
    print("=" * 50)
    print("B站知识区数据爬虫 启动")
    print("=" * 50)

    # 预热：访问首页获取 cookies
    _init_session()
    print("[爬虫] Session 初始化完成")

    # 1. 热门推荐（主源）
    popular_data = fetch_popular_list(pages=pages)
    print(f"[爬虫] 热门推荐采集完毕，共 {len(popular_data)} 条")

    # 2. 知识区动态（主源）
    knowledge_data = fetch_knowledge_zone(pages=pages)
    print(f"[爬虫] 知识区动态采集完毕，共 {len(knowledge_data)} 条")

    # 3. 合并去重（热门系列接口已失效，忽略）
    all_videos = popular_data + knowledge_data
    seen = set()
    unique_videos = []
    for v in all_videos:
        key = (v["title"], v["owner_name"])
        if key not in seen:
            seen.add(key)
            unique_videos.append(v)

    df = pd.DataFrame(unique_videos)
    print(f"[爬虫] 合并去重后共 {len(df)} 条视频")

    # 5. 筛选知识区（tid 在知识区范围内）
    knowledge_tids = set(KNOWLEDGE_TIDS.keys())
    before = len(df)
    df_in_knowledge = df[df["tid"].isin(knowledge_tids)]
    print(f"[爬虫] 知识区筛选: {before} -> {len(df_in_knowledge)} 条")

    # 如果有足够的知识区数据就用筛选后的，否则全部保留
    if len(df_in_knowledge) >= 10:
        df = df_in_knowledge.reset_index(drop=True)
    else:
        print(f"[爬虫] 知识区视频不足10条，保留全部数据")
        df = df.reset_index(drop=True)

    # 6. 保存 CSV
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"[爬虫] 数据已保存 -> {os.path.abspath(filename)} ({len(df)} 条)")
    print("=" * 50)

    return df


# ── 独立运行入口 ────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    fetch_and_save("data/raw_data.csv", pages=5)
