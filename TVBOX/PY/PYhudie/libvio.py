#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clun-test —— LIBVIO (www.libhd.com) 影视站数据抓取与连通性测试工具

站点结构（STUI/MacCMS 模板，资源 API 已关闭，仅能从 HTML 页抓取）：
    首页    https://www.libhd.com/
    分类    https://www.libhd.com/type/{tid}.html     (1=电影 2=剧集 4=番剧)
    搜索    https://www.libhd.com/search/-------------.html?wd=关键词
    详情    https://www.libhd.com/detail/{vod_id}.html
    播放    https://www.libhd.com/w/{vod_id}-{src}-{ep}.html

用法示例：
    python libvio.py ping                     # 站点连通性/健康检查
    python libvio.py hot                      # 抓取首页热播榜（按分区）
    python libvio.py type 2 -p 1 -n 5         # 抓取剧集分类前 5 页
    python libvio.py search 死神              # 搜索关键词
    python libvio.py detail 714893571         # 抓取详情页（含播放源/网盘链接）
    python libvio.py detail 714893571 -json   # 详情输出 JSON
    python libvio.py crawl 2 -p 1 -n 10 -o out.json   # 分类批量抓取并落盘

输出格式：默认表格文本，-json 输出 JSON，-csv 输出 CSV。

内置 TVBox 适配（英文名 LIBVIO）：
    类  spider.Spider —— 实现 homeContent/homeVideoContent/categoryContent/
    detailContent/searchContent/playerContent，可直接作为 TVBox 源使用；
    自测  python3 libvio_test.py
    无 curl_cffi 环境自动退化为 requests。
"""

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional

try:
    from curl_cffi import requests as creq
    IS_CURL_CFFI = True
except ImportError:  # TVBox 运行时可能未安装 curl_cffi，退化为标准 requests
    import requests as creq
    IS_CURL_CFFI = False
from bs4 import BeautifulSoup
from urllib.parse import quote, urlencode

BASE = "https://www.libhd.com"
SITE_NAME = "LIBVIO"  # 站点英文名
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": BASE + "/",
    "Accept": "*/*",
}
TIMEOUT = 15
SLEEP = 0.6  # 请求间隔，避免触发风控
# 说明：该站 CDN 对“过于拟真的浏览器指纹”(impersonate) 会下发 js-pow
# 工作量证明挑战；使用 curl_cffi 的原生 TLS 指纹 + 精简头即可正常访问。
USE_IMPERSONATE = False

TIDS = {1: "电影", 2: "剧集", 4: "番剧"}
TIDS_REV = {v: k for k, v in TIDS.items()}


# ---------------------------------------------------------------- 数据模型
@dataclass
class VideoItem:
    """列表页中的一部影视条目。"""
    title: str = ""
    detail_url: str = ""
    vod_id: str = ""
    cover: str = ""
    status: str = ""       # 更新状态，如 第11集/周六日更 / 已完结
    score: str = ""        # 评分，可能为空
    type_name: str = ""    # 所属分类


@dataclass
class VideoDetail(VideoItem):
    """详情页完整信息。"""
    category: str = ""          # 剧情,喜剧
    area: str = ""              # 地区
    year: str = ""              # 年份
    release: str = ""           # 上映时间
    episode_total: str = ""     # 共多少集
    update_date: str = ""       # 更新时间
    actors: List[str] = field(default_factory=list)
    director: List[str] = field(default_factory=list)
    intro: str = ""             # 简介
    douban_url: str = ""        # 豆瓣链接
    play_groups: dict = field(default_factory=dict)  # {源名: {集名: 播放url}}
    netdisks: List[dict] = field(default_factory=list)  # 网盘链接
    related: List[VideoItem] = field(default_factory=list)  # 猜你喜欢


# ---------------------------------------------------------------- 网络层
def _solve_pow(body: str) -> Optional[str]:
    """当 CDN 下发 js-pow 挑战时，从页面提取参数并求解叠加前缀，返回放行 cookie 值。

    挑战逻辑（从页面脚本还原）：
      cookie = {POW}={TS}_{MODE}_{nonce}_{SIG}
      其中 nonce 需满足 sha256(SIG + str(i)).hexdigest().startswith(DIFF)
    """
    m = re.search(r'var TS\s*=\s*"(\d+)"', body)
    m2 = re.search(r'var SIG\s*=\s*"([0-9a-f]+)"', body)
    m3 = re.search(r'var DIFF\s*=\s*"([0-9a-f]+)"', body)
    m4 = re.search(r'var POW\s*=\s*"([^"]+)"', body)
    m5 = re.search(r'var MODE\s*=\s*"([^"]+)"', body)
    if not (m and m2 and m3 and m4):
        return None
    ts, sig, diff, powname = m.group(1), m2.group(1), m3.group(1), m4.group(1)
    mode = m5.group(1) if m5 else "auto"
    difflen = len(diff)
    if difflen < 2 or difflen > 6:
        return None
    i = 0
    while i < 4_000_000:  # 4 hex ≈ 16 次方期望尝试
        if hashlib.sha256((sig + str(i)).encode()).hexdigest().startswith(diff):
            return f"{ts}_{mode}_{i}_{sig}"
        i += 1
    return None


class LibhdClient:
    def __init__(self, base: str = BASE, timeout: int = TIMEOUT, sleep: float = SLEEP):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.sleep = sleep
        self.session = creq.Session()
        self.session.headers.update(HEADERS)

    def _request(self, url: str, **kw) -> creq.Response:
        kw.setdefault("timeout", self.timeout)
        if USE_IMPERSONATE and IS_CURL_CFFI:
            kw["impersonate"] = "chrome"
            kw.setdefault("http_version", 2)
        resp = self.session.get(url, **kw)
        # 命中 js-pow 挑战：自动求解并重试一次
        if resp.status_code == 403 and "x-cdn-challenge" in resp.headers:
            val = _solve_pow(resp.text)
            if val:
                self.session.cookies.update({re.search(
                    r'var POW\s*=\s*"([^"]+)"', resp.text).group(1): val})
                resp = self.session.get(url, **kw)
        return resp

    def get(self, path: str, params: Optional[dict] = None) -> str:
        url = path if path.startswith("http") else self.base + path
        try:
            resp = self._request(url, params=params)
            resp.raise_for_status()
            resp.encoding = resp.encoding or "utf-8"
        except Exception as exc:
            raise ConnectionError(f"请求失败: {url} -> {exc}") from exc
        time.sleep(self.sleep)
        body = resp.text
        # 首页/详情页偶尔返回风控占位"closed"
        if body.strip().lower() == "closed":
            raise PermissionError(f"站点返回风控占位(closed): {url}")
        return body

    def api(self, ac: str = "list", **params) -> dict:
        """尝试访问标准资源 API。该站已关闭(closed)，多数会失败，保留能力。"""
        params = {"ac": ac, **params}
        url = self.base + "/api.php/provide/vod/"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        text = resp.text.strip()
        if text.lower() == "closed":
            raise PermissionError("该站点的资源 API 已关闭(closed)，仅支持 HTML 页面抓取")
        return resp.json()


# ---------------------------------------------------------------- 解析层
def parse_vod_id(detail_url: str) -> str:
    m = re.search(r"/detail/(\d+)\.html", detail_url or "")
    return m.group(1) if m else ""


def parse_list_page(html: str, type_name: str = "") -> List[VideoItem]:
    """解析首页/分类/搜索列表页的 stui-vodlist__box 条目。"""
    soup = BeautifulSoup(html, "html.parser")
    items: List[VideoItem] = []
    for box in soup.select("div.stui-vodlist__box"):
        a = box.select_one("a.stui-vodlist__thumb")
        if not a:
            continue
        detail_url = a.get("href") or ""
        cover = a.get("data-original") or a.get("src") or ""
        status = ""
        score = ""
        if st := box.select_one("span.pic-text"):
            status = st.get_text(strip=True)
        if st := box.select_one("span.pic-tag-top"):
            score = st.get_text(strip=True)
        title = (a.get("title") or "").strip()
        if not title and (t := box.select_one(".stui-vodlist__detail .title a")):
            title = t.get_text(strip=True)
        items.append(
            VideoItem(
                title=title,
                detail_url=self_abs(detail_url),
                vod_id=parse_vod_id(detail_url),
                cover=cover,
                status=status,
                score=score,
                type_name=type_name,
            )
        )
    return items


def self_abs(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    return BASE.rstrip("/") + href


def parse_detail_page(html: str, vod_id: str = "") -> VideoDetail:
    """解析详情页：基本信息、播放源、网盘链接、猜你喜欢。"""
    soup = BeautifulSoup(html, "html.parser")
    d = VideoDetail(vod_id=vod_id)

    # 标题
    h1 = soup.select_one("h1.title")
    if h1:
        d.title = h1.get_text(strip=True)
    if not d.title:
        if t := soup.select_one("title"):
            d.title = re.sub(r"\s*[-–—]\s*" + SITE_NAME + r".*$", "", t.get_text(strip=True))

    # 信息块：.vod-meta 下的 span.meta-item，按模板顺序
    # （依次为 类型 / 地区 / 年份 / 上映xx / 共xx集 / 更新xx / 主演 / 导演）
    for span in soup.select(".vod-meta .meta-item, span.meta-item"):
        txt = span.get_text(" ", strip=True)
        if not txt:
            continue
        if txt.startswith("主演："):
            d.actors = [x.strip() for x in txt[3:].split(",") if x.strip()]
        elif txt.startswith("导演："):
            d.director = [x.strip() for x in txt[3:].split(",") if x.strip()]
        elif txt.startswith("上映"):
            d.release = txt[2:].strip()
        elif txt.startswith("共") and "集" in txt:
            d.episode_total = txt
        elif txt.startswith("更新"):
            d.update_date = txt[2:].strip()
        elif txt.startswith("类型"):
            d.category = txt[2:].strip()
        elif re.fullmatch(r"\d{4}", txt):
            d.year = txt
        elif txt:
            # 无前缀且非年份，可能是类型或地区；用关键词区分
            if not d.category and any(k in txt for k in ("剧情", "喜剧", "动作", "爱情", "科幻", "悬疑", "惊悚", "恐怖", "犯罪", "动画", "冒险", "奇幻", "纪录", "真人", "音乐", "家庭", "历史", "战争", "西部", "运动")):
                d.category = txt
            elif not d.area:
                d.area = txt

    # 简介（展开前详情 + 展开后内容统一切断）
    if sk := soup.select_one("span.detail-sketch"):
        d.intro = sk.get_text(strip=True)
    if not d.intro:
        if dc := soup.select_one("span.detail-content"):
            d.intro = dc.get_text(strip=True)

    # 评分 + 豆瓣
    if rt := soup.select_one("a.vod-rating .score, .vod-rating .score"):
        d.score = rt.get_text(strip=True).replace("分", "")
    for a in soup.select("a[href*='douban.com']"):
        d.douban_url = a.get("href", "")

    # 播放源分组（每个 .playlist-panel 的 panel-head h3 + ul）
    for panel in soup.select("div.playlist-panel"):
        ul = panel.select_one("ul.stui-content__playlist")
        if not ul:
            continue
        head = panel.select_one(".panel-head h3")
        src_name = head.get_text(strip=True) if head else f"源{len(d.play_groups) + 1}"
        groups = d.play_groups.setdefault(src_name, {})
        for a in ul.select("a[href*='/w/']"):
            ep = a.get_text(strip=True) or "?"
            groups[ep] = self_abs(a.get("href") or "")

    # 网盘链接（.netdisk-panel 内的 netdisk-item）
    for a in soup.select("div.netdisk-panel a.netdisk-item, a.netdisk-item"):
        href = a.get("href") or ""
        if "pan." in href:
            # 优先取 .netdisk-name；否则去掉行尾 ↙/↗ 箭头后再截取
            name = (a.select_one(".netdisk-name").get_text(strip=True)
                    if a.select_one(".netdisk-name") else "")
            if not name:
                name = re.sub(r"[↗↘↙↖↑↓→←↔\s]+$", "",
                              a.get_text(" ", strip=True)).strip() or "网盘"
            d.netdisks.append({"name": name, "url": href})

    # 猜你喜欢（剔除当前视频自身，站点会把“猜你喜欢”当前条也渲染出来）
    d.related = [it for it in parse_list_page(html) if it.vod_id != vod_id]

    # 详情页自身链接与封面
    if vod_id:
        d.detail_url = self_abs(f"/detail/{vod_id}.html")
    if img := soup.select_one(".vod-poster__wrap img.lazyload, .vod-poster__wrap img"):
        d.cover = img.get("data-original") or img.get("data-src") or img.get("src") or ""
    if not d.cover:
        if img := soup.select_one(".stui-content__thumb img, a.stui-vodlist__thumb img"):
            d.cover = img.get("data-original") or img.get("src") or ""
    return d


# ---------------------------------------------------------------- 业务命令
def cmd_ping(client: LibhdClient) -> dict:
    """连通性/健康检查：探测首页、各分类、搜索、详情、播放、API 的状态。"""
    probes = {
        "首页": "/",
        "分类-电影": "/type/1.html",
        "分类-剧集": "/type/2.html",
        "分类-番剧": "/type/4.html",
        "搜索页": "/search/-------------.html?wd=测试",
    }
    results = {}
    for name, path in probes.items():
        t0 = time.time()
        try:
            body = client.get(path)
            code, ms = 200, int((time.time() - t0) * 1000)
            title = re.search(r"<title>(.*?)</title>", body, re.S)
            results[name] = {
                "status": "OK", "http": code, "ms": ms,
                "page_title": title.group(1).strip() if title else "",
                "size": len(body),
            }
        except Exception as exc:
            results[name] = {
                "status": "FAIL", "http": None, "ms": int((time.time() - t0) * 1000),
                "error": str(exc),
            }
    # 详情/播放页用首页出现的真实 id 探测（避免硬编码失效）
    try:
        home = client.get("/")
        items = parse_list_page(home)
        if items:
            vid = items[0].vod_id
            path = f"/detail/{vid}.html"
            t0 = time.time()
            body = client.get(path)
            results["详情页"] = {
                "status": "OK", "http": 200,
                "ms": int((time.time() - t0) * 1000),
                "page_title": re.search(r"<title>(.*?)</title>", body, re.S).group(1)
                if re.search(r"<title>(.*?)</title>", body, re.S) else "",
                "size": len(body),
            }
    except Exception as exc:
        results["详情页"] = {"status": "FAIL", "http": None, "ms": 0, "error": str(exc)}
    # 标准资源 API
    try:
        client.api("list", pg=1)
        results["资源API"] = {"status": "OK", "http": 200, "ms": 0, "note": "可用"}
    except PermissionError:
        results["资源API"] = {"status": "CLOSED", "http": None, "ms": 0, "note": "站点已关闭该接口"}
    except Exception as exc:
        results["资源API"] = {"status": "FAIL", "http": None, "ms": 0, "error": str(exc)}
    return results


def cmd_hot(client: LibhdClient, limit: Optional[int] = None) -> List[VideoItem]:
    """抓取首页各分区热播内容（今日更新/电影/剧集/番剧/综艺，按分区标注所属分类）。"""
    html = client.get("/")
    soup = BeautifulSoup(html, "html.parser")
    items: List[VideoItem] = []
    current_name = "今日更新"
    for el in soup.select(".stui-pannel__bd > *"):
        if el.name == "div" and el.get("class") and "stui-vodlist__head" in el.get("class"):
            # STUI 模板中分区标题(h3)位于其列表<ul>之前，标记后续列表归属
            name = el.select_one("h3 a") or el.select_one("h3")
            current_name = name.get_text(strip=True) if name else "今日更新"
        elif el.name == "ul" and "stui-vodlist" in (el.get("class") or []):
            items.extend(parse_list_page(str(el), type_name=current_name))
    return items[:limit] if limit else items


def cmd_type(client: LibhdClient, tid: int, page: int = 1, pages: int = 1,
             limit: Optional[int] = None) -> List[VideoItem]:
    """抓取分类列表，支持多页。"""
    out: List[VideoItem] = []
    name = TIDS.get(tid, f"分类{tid}")
    for pg in range(page, page + pages):
        body = client.get(f"/type/{tid}.html", params={"page": pg} if pg > 1 else None)
        items = parse_list_page(body, type_name=name)
        if not items:
            break
        out.extend(items)
        if limit and len(out) >= limit:
            break
    return out[:limit] if limit else out


def cmd_search(client: LibhdClient, keyword: str, limit: Optional[int] = None) -> List[VideoItem]:
    """搜索关键词。"""
    body = client.get("/search/-------------.html", params={"wd": keyword})
    items = parse_list_page(body, type_name="搜索")
    return items[:limit] if limit else items


def cmd_detail(client: LibhdClient, vod_id: str) -> VideoDetail:
    """抓取详情页。"""
    body = client.get(f"/detail/{vod_id}.html")
    return parse_detail_page(body, vod_id=vod_id)


def cmd_crawl(client: LibhdClient, tid: int, pages: int, out_json: Optional[str] = None,
              out_csv: Optional[str] = None) -> List[VideoItem]:
    """分类批量抓取并可落盘。"""
    items = cmd_type(client, tid, page=1, pages=pages)
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump([asdict(i) for i in items], f, ensure_ascii=False, indent=2)
        print(f"[已保存] {out_json} ({len(items)} 条)")
    if out_csv:
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(asdict(items[0]).keys()) if items else [])
            if items:
                w.writeheader()
                w.writerows(asdict(i) for i in items)
        print(f"[已保存] {out_csv} ({len(items)} 条)")
    return items


# ---------------------------------------------------------------- 输出层
def print_items(items: List[VideoItem], title: str = "") -> None:
    if title:
        print(f"\n== {title} ==")
    if not items:
        print("（无结果）")
        return
    width = max(len(i.title) for i in items)
    for i in items:
        tags = " ".join(x for x in [i.type_name, i.score, i.status] if x)
        print(f"  {i.title:<{width}}  {tags}  {i.detail_url}")


def print_detail(d: VideoDetail) -> None:
    print(f"\n== {d.title} ==")
    meta = " / ".join(
        x for x in [
            d.category, d.area, d.year, d.release,
            d.episode_total,
            f"更新 {d.update_date}" if d.update_date else "",
        ] if x
    )
    if meta:
        print(f"  信息: {meta}")
    if d.actors:
        print(f"  主演: {', '.join(d.actors)}")
    if d.director:
        print(f"  导演: {', '.join(d.director)}")
    if d.score:
        print(f"  评分: {d.score}")
    if d.intro:
        print(f"  简介: {d.intro[:120]}{'…' if len(d.intro) > 120 else ''}")
    if d.douban_url:
        print(f"  豆瓣: {d.douban_url}")
    if d.play_groups:
        print("  播放源:")
        for src, eps in d.play_groups.items():
            print(f"    [{src}] 共 {len(eps)} 集，示意: {list(eps.items())[:3]}")
    if d.netdisks:
        print("  网盘:")
        for nd in d.netdisks:
            print(f"    {nd['name']}: {nd['url']}")
    if d.related:
        print_items(d.related[:6], "猜你喜欢")


def print_ping(results: dict) -> None:
    print(f"\n== {SITE_NAME} 站点健康检查 ==")
    for name, r in results.items():
        status = r.get("status", "?")
        ms = r.get("ms", 0)
        note = r.get("page_title") or r.get("note") or r.get("error") or ""
        flag = {"OK": "✔", "CLOSED": "⊘", "FAIL": "✘"}.get(status, "?")
        print(f"  {flag} {name:<12} {status:<7} {ms:>5}ms  {note}")


# ---------------------------------------------------------------- TVBox 适配（LIBVIO）
try:
    from base.spider import Spider as BaseSpider  # Pyramid/TVBox 运行时
except ImportError:  # 独立 CLI 环境下仍可导入本模块
    class BaseSpider:
        def init(self, extend=""): pass
        def getName(self): return SITE_NAME
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False
        def destroy(self): pass
        def localProxy(self, param): return None
        def homeContent(self, filter):
            return {"class": [], "list": [], "filters": {}}
        def homeVideoContent(self):
            return {"list": []}
        def categoryContent(self, tid, pg, filter, extend):
            return {"list": [], "page": int(pg or 1), "pagecount": 1, "limit": 0, "total": 0}
        def detailContent(self, ids):
            return {"list": []}
        def searchContent(self, key, quick, pg="1"):
            return {"list": [], "page": int(pg or 1)}
        def playerContent(self, flag, id, vipFlags):
            return {"parse": 0, "url": id or "", "header": {}}


# 站点分类（首页导航实测）与筛选
_SITE_CLASSES = [
    {"type_id": "1", "type_name": "电影"},
    {"type_id": "2", "type_name": "剧集"},
    {"type_id": "3", "type_name": "综艺"},
    {"type_id": "4", "type_name": "番剧"},
    {"type_id": "6", "type_name": "动作片"},
    {"type_id": "7", "type_name": "喜剧片"},
    {"type_id": "8", "type_name": "爱情片"},
    {"type_id": "9", "type_name": "科幻片"},
    {"type_id": "10", "type_name": "恐怖片"},
    {"type_id": "11", "type_name": "剧情片"},
    {"type_id": "12", "type_name": "战争片"},
    {"type_id": "23", "type_name": "动画片"},
    {"type_id": "13", "type_name": "国剧"},
    {"type_id": "14", "type_name": "港台剧"},
    {"type_id": "15", "type_name": "日韩剧"},
    {"type_id": "16", "type_name": "欧美剧"},
    {"type_id": "21", "type_name": "纪录片"},
    {"type_id": "24", "type_name": "泰国剧"},
]
_SITE_AREA = ["中国大陆", "中国香港", "中国台湾", "韩国", "日本", "美国", "泰国", "英国", "新加坡", "其他"]


def _site_filters(tid: str) -> list:
    """STUI /show/ 筛选配置（area/by/year 为 URL 中间段）。"""
    return [
        {"key": "area", "name": "地区",
         "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in _SITE_AREA]},
        {"key": "year", "name": "年份",
         "value": [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(2026, 2018, -1)]},
        {"key": "by", "name": "排序",
         "value": [{"n": "时间", "v": "time"}, {"n": "人气", "v": "hits"}, {"n": "评分", "v": "score"}]},
    ]


def _show_url(tid: str, page: int = 0, area: str = "", by: str = "", year: str = "") -> str:
    """构造 STUI 分类页 URL：/show/{tid}-{area}-{by}-----{page}--{year}.html"""
    segs = [tid, area or "", by or "", "", "", "", "", "",
            str(page) if page else "", "", "", year or ""]
    return f"{BASE}/show/{'-'.join(segs)}.html"


def _to_vod(item: VideoItem) -> dict:
    """VideoItem -> TVBox 列表项。"""
    remarks = item.status or ""
    if item.score and item.score not in ("0.0", "0"):
        remarks = (item.status + "/" + item.score) if item.status else item.score
    return {
        "vod_id": item.vod_id,
        "vod_name": item.title,
        "vod_pic": item.cover,
        "vod_remarks": remarks,
    }


class Spider(BaseSpider):
    """LIBVIO (www.libhd.com) —— TVBox 适配源。"""

    def getName(self):
        return SITE_NAME

    def init(self, extend=""):
        self.host = BASE
        self.client = LibhdClient(base=self.host, sleep=0)  # 复用 js-pow 处理层

    def isVideoFormat(self, url):
        return any(x in (url or "") for x in [".m3u8", ".mp4", ".flv", ".ts"])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def localProxy(self, param):
        return None

    def _get(self, url: str) -> str:
        if not url:
            return ""
        try:
            return self.client.get(url)
        except Exception:
            return ""

    # ---- 首页 ----
    def homeContent(self, filter):
        try:
            html = self._get(self.host + "/")
            items = [_to_vod(i) for i in parse_list_page(html)][:20]
        except Exception:
            items = []
        return {
            "class": [dict(c) for c in _SITE_CLASSES],
            "list": items,
            "filters": {c["type_id"]: _site_filters(c["type_id"]) for c in _SITE_CLASSES},
        }

    def homeVideoContent(self):
        try:
            html = self._get(self.host + "/")
            items = [_to_vod(i) for i in parse_list_page(html)]
        except Exception:
            items = []
        return {"list": items[:30]}

    # ---- 分类 ----
    def categoryContent(self, tid, pg, filter, extend):
        try:
            ext = extend or {}
            url = _show_url(str(tid), page=int(pg or 1),
                            area=ext.get("area", ""), by=ext.get("by", ""),
                            year=ext.get("year", ""))
            html = self._get(url)
            if not html:
                raise ValueError("no html")
            items = [_to_vod(i) for i in parse_list_page(html)]
            pc = 1
            m = re.search(r'class="active num"[^>]*>[^<]*<a[^>]*>\s*\d+/(\d+)', html)
            if not m:
                m = re.search(r'(\d+)---\.html"[^>]*>\s*尾页', html)
            if m:
                pc = int(m.group(1))
            return {"list": items, "page": int(pg or 1), "pagecount": pc,
                    "limit": len(items), "total": pc * len(items) if items else 0}
        except Exception:
            return {"list": [], "page": int(pg or 1), "pagecount": 1,
                    "limit": 0, "total": 0}

    # ---- 详情 ----
    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, (list, tuple)) else ids
            html = self._get(f"{self.host}/detail/{str(vid)}.html")
            if not html:
                return {"list": []}
            d = parse_detail_page(html, vod_id=str(vid))
            vod = {
                "vod_id": str(vid),
                "vod_name": d.title or str(vid),
                "vod_pic": d.cover,
                "vod_year": d.year,
                "vod_area": d.area,
                "vod_director": " ".join(d.director),
                "vod_actor": " ".join(d.actors),
                "vod_remarks": d.status or d.episode_total or d.update_date,
                "vod_content": d.intro,
                "type_name": d.category,
            }
            play_from, play_url = [], []
            for src, eps in d.play_groups.items():
                if eps:
                    play_from.append(src)
                    play_url.append("#".join(f"{ep}${u}" for ep, u in eps.items()))
            if d.netdisks:
                play_from.append("网盘下载")
                play_url.append("#".join(f"{n['name']}${n['url']}" for n in d.netdisks))
            vod["vod_play_from"] = "$$$".join(play_from)
            vod["vod_play_url"] = "$$$".join(play_url)
            return {"list": [vod]}
        except Exception:
            return {"list": []}

    # ---- 搜索 ----
    def searchContent(self, key, quick, pg="1"):
        try:
            url = f"{self.host}/search/{quote(key)}----------{pg}---.html"
            html = self._get(url)
            items = [_to_vod(i) for i in parse_list_page(html)] if html else []
            return {"list": items, "page": int(pg or 1)}
        except Exception:
            return {"list": [], "page": int(pg or 1)}

    # ---- 播放 ----
    def _player_ref(self, url: str) -> str:
        """播放器原始 host（播放页/站点 origin）：媒体 CDN 只放行该 Referer。"""
        if url:
            m = re.match(r'https?://[^/]+', url)
            if m:
                return m.group(0)
        return self.host

    def _resolve_encrypted(self, data: dict) -> str:
        """把 player_aaaa 中 encrypt=3 的加密 url 经站点 /vid/ 播放器解析为直链。

        站点播放器把直链藏在一闪即逝的 /vid/{player}.php 页里（页内含一次性 token）：
          - from=yd189  -> /vid/yd.php    内嵌 fetch('/vid/parse_yd.php?...') 直取 JSON
          - from=ty_new1 -> /vid/ty4.php  内嵌 LIBVIO_CFG.parseUrl，POST rawUrl 换直链
        """
        enc = (data.get("url") or "").strip()
        if not enc:
            return ""
        vid = data.get("id") or ""
        sid = data.get("sid") or ""
        nid = data.get("nid") or ""
        link_next = data.get("link_next") or ""
        fromv = data.get("from") or ""
        # 已知播放器的 /vid 解析端点；未知 from 从 player js 提取 iframe 路径兜底
        mapping = {"yd189": "/vid/yd.php", "ty_new1": "/vid/ty4.php"}
        ep = mapping.get(fromv)
        if not ep:
            js = self._get(f"{self.host}/static/player/{fromv}.js?v=3.9") if fromv else ""
            m = re.search(r'/vid/[A-Za-z0-9_./-]*\.php', js or "")
            ep = m.group(0) if m else ""
        if not ep:
            return ""
        params = {
            "url": enc,
            "next": link_next or f"/w/{vid}-{sid}-{nid}.html",
            "id": vid,
            "nid": nid,
        }
        try:
            body = self._get(f"{self.host}{ep}?{urlencode(params)}")
        except Exception:
            body = ""
        if not body:
            return ""
        # ty4 风格：LIBVIO_CFG.parseUrl + POST rawUrl
        m = re.search(r'window\.LIBVIO_CFG\s*=\s*(\{.*?\});', body, re.S)
        if m:
            try:
                cfg = json.loads(m.group(1))
                pu = (cfg.get("parseUrl") or "").replace("\\u0026", "&")
                raw = cfg.get("rawUrl") or enc
                if pu:
                    r = self.client.session.post(
                        self.host + pu,
                        data=json.dumps({"url": raw}),
                        headers={"Content-Type": "application/json",
                                 **dict(HEADERS)},
                        timeout=TIMEOUT,
                    )
                    j = json.loads(r.text)
                    if j.get("url"):
                        return j["url"]
            except Exception:
                pass
        # yd 风格：页面内首次加载 fetch('/vid/parse_yd.php?...') 直取 JSON
        m = re.search(r"fetch\(\s*['\"]([^'\"]*parse_yd\.php[^'\"]*)['\"]", body)
        if m:
            try:
                j = json.loads(self._get(self.host + m.group(1)))
                if j.get("url"):
                    return j["url"]
            except Exception:
                pass
        # vr2 风格：window.__PP = {urls:"..."}（DPlayer 直链）
        m = re.search(r'window\.__PP\s*=\s*(\{.*?\});', body, re.S)
        if m:
            try:
                pp = json.loads(m.group(1))
                u = pp.get("urls") or pp.get("url") or ""
                if u.startswith("http"):
                    return u
            except Exception:
                pass
        return ""

    def playerContent(self, flag, id, vipFlags):
        id = (id or "").strip()
        if not id:
            return {"parse": 0, "url": "", "header": {}}
        if id.startswith("//"):
            id = "https:" + id
        # 网盘/磁力等非播放页直链，交给播放器/WebView
        if any(x in id for x in ("pan.", "magnet:", "thunder:", "ed2k:")):
            return {"parse": 1, "url": id, "header": dict(HEADERS)}
        try:
            if id.startswith("http") and f"/w/" in id:
                html = self._get(id)
                m = re.search(r'var player_aaaa=(\{.*?\})\s*</script>', html, re.S)
                if m:
                    data = json.loads(m.group(1))
                    url = (data.get("url") or "").strip()
                    # Referer 用播放器原始 host（播放页/站点 origin），
                    # 媒体 CDN(v3.vbing.me 等) 只放行该 Referer，否则 403
                    headers = {"User-Agent": HEADERS["User-Agent"],
                               "Referer": self._player_ref(id)}
                    if url.startswith("http"):
                        return {"parse": 0, "url": url, "header": headers}
                    if url:
                        # encrypt=3 加密地址：经站点 /vid/ 播放器解析为直链（多线路）
                        real = self._resolve_encrypted(data)
                        if real:
                            return {"parse": 0, "url": real, "header": headers}
                    # 直链为空/解析失败：交给播放器 WebView 按页面兜底
                    return {"parse": 1, "url": id,
                            "header": {"User-Agent": HEADERS["User-Agent"], "Referer": id}}
                # /w/ 页面未解析出 player_aaaa，交给播放器 WebView 兜底
                return {"parse": 1, "url": id,
                        "header": {"User-Agent": HEADERS["User-Agent"], "Referer": id}}
            return {"parse": 0, "url": id, "header": dict(HEADERS)}
        except Exception:
            return {"parse": 1, "url": id,
                    "header": {"User-Agent": HEADERS["User-Agent"], "Referer": id}}


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=f"clun-test: {SITE_NAME} (libhd.com) 影视站数据抓取与测试工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ping", help="站点连通性/健康检查")
    p = sub.add_parser("hot", help="抓取首页热播")
    p.add_argument("-n", "--limit", type=int, default=None, help="最多条数")

    p = sub.add_parser("type", help="抓取分类列表")
    p.add_argument("tid", type=int, help="分类 id: 1电影 2剧集 4番剧")
    p.add_argument("-p", "--page", type=int, default=1, help="起始页")
    p.add_argument("-P", "--pages", type=int, default=1, help="抓取页数")
    p.add_argument("-n", "--limit", type=int, default=None, help="最多条数")

    p = sub.add_parser("search", help="搜索")
    p.add_argument("keyword", help="关键词")
    p.add_argument("-n", "--limit", type=int, default=None, help="最多条数")

    p = sub.add_parser("detail", help="抓取详情页")
    p.add_argument("vod_id", help="视频 id，如 714893571")
    p.add_argument("-json", action="store_true", help="输出 JSON")

    p = sub.add_parser("crawl", help="分类批量抓取并落盘")
    p.add_argument("tid", type=int, help="分类 id")
    p.add_argument("-P", "--pages", type=int, default=3, help="抓取页数")
    p.add_argument("-o", "--out-json", help="输出 JSON 文件路径")
    p.add_argument("-c", "--out-csv", help="输出 CSV 文件路径")

    p = sub.add_parser("api", help="尝试访问标准资源 API（站点已关闭则报错）")
    p.add_argument("-pg", type=int, default=1, help="页码")

    args = ap.parse_args()
    client = LibhdClient()

    try:
        if args.cmd == "ping":
            print_ping(cmd_ping(client))
        elif args.cmd == "hot":
            items = cmd_hot(client, args.limit)
            print_items(items, f"首页热播（{len(items)} 条）")
        elif args.cmd == "type":
            items = cmd_type(client, args.tid, args.page, args.pages, args.limit)
            print_items(items, f"{TIDS.get(args.tid, args.tid)}分类（{len(items)} 条）")
        elif args.cmd == "search":
            items = cmd_search(client, args.keyword, args.limit)
            print_items(items, f'搜索「{args.keyword}」（{len(items)} 条）')
        elif args.cmd == "detail":
            d = cmd_detail(client, args.vod_id)
            if args.json:
                print(json.dumps(asdict(d), ensure_ascii=False, indent=2))
            else:
                print_detail(d)
        elif args.cmd == "crawl":
            items = cmd_crawl(client, args.tid, args.pages, args.out_json, args.out_csv)
            print_items(items, f"{TIDS.get(args.tid, args.tid)}分类批量（{len(items)} 条）")
        elif args.cmd == "api":
            data = client.api("list", pg=args.pg)
            print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
    except PermissionError as exc:
        print(f"[风控/限制] {exc}", file=sys.stderr)
        return 2
    except ConnectionError as exc:
        print(f"[网络错误] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())