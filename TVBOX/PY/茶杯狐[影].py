# -*- coding: utf-8 -*-
import sys
import re
import requests
from urllib.parse import quote
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://citapa.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Mobile Safari/537.36",
            "Referer": self.host + "/",
            "Origin": self.host
        }

    def getName(self):
        return "茶杯狐"

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|avi|mkv|mov|ts)(\?|$)', url or "", re.I))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {
            "class": [
                {"type_id": "1", "type_name": "电影"},
                {"type_id": "2", "type_name": "电视剧"},
                {"type_id": "3", "type_name": "综艺"},
                {"type_id": "4", "type_name": "动漫"}
            ]
        }

    def homeVideoContent(self):
        return {"list": self.parseList(self.get(self.host + "/"))}

    def categoryContent(self, tid, pg, filter, extend):
        html = self.get(self.host + "/search.php?searchtype=5&tid=" + str(tid) + "&page=" + str(pg))
        return {
            "page": int(pg),
            "pagecount": 999,
            "limit": 24,
            "total": 999999,
            "list": self.parseList(html)
        }

    def detailContent(self, ids):
        vid = ids[0]
        html = self.get(self.host + "/movie/index" + vid + ".html")
        name = self.clean(self.match(html, r'<h1[^>]*>(.*?)</h1>') or self.match(html, r'<meta property="og:title" content="(.*?)"'))
        pic = self.fix(self.match(html, r'<meta property="og:image" content="(.*?)"') or self.match(html, r'<img[^>]+(?:data-src|data-original|src)=["\']([^"\']+)'))
        desc = self.clean(self.match(html, r'<meta property="og:description" content="(.*?)"') or self.match(html, r'剧情：([\s\S]*?)在线观看'))
        tabs = re.findall(r'data-dropdown-value=["\']([^"\']+)["\']', html)
        panels = re.findall(r'<div class="module-list module-player-list[\s\S]*?</div>\s*</div>\s*</div>', html)
        play_from = []
        play_url = []
        for i, p in enumerate(panels):
            eps = []
            for m in re.finditer(r'<a[^>]+title=["\']([^"\']+)["\'][^>]+href=["\']([^"\']*?/play/[^"\']+)["\']', p):
                t = self.clean(m.group(1))
                u = self.fix(m.group(2))
                if t and u:
                    eps.append(t + "$" + u)
            if not eps:
                for m in re.finditer(r'<a[^>]+href=["\']([^"\']*?/play/[^"\']+)["\'][^>]*>(.*?)</a>', p):
                    t = self.clean(m.group(2))
                    u = self.fix(m.group(1))
                    if t and u:
                        eps.append(t + "$" + u)
            if eps:
                key = tabs[i] if i < len(tabs) else "线路" + str(i + 1)
                if key not in play_from:
                    play_from.append(key)
                    play_url.append("#".join(eps))
        if not play_url:
            eps = []
            for m in re.finditer(r'<a[^>]+href=["\']([^"\']*?/play/' + vid + r'-[^"\']+)["\'][^>]*>(.*?)</a>', html):
                t = self.clean(m.group(2)) or "播放"
                u = self.fix(m.group(1))
                if t and u:
                    eps.append(t + "$" + u)
            if eps:
                play_from.append("默认")
                play_url.append("#".join(eps))
        return {
            "list": [{
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_content": desc,
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "$$$".join(play_url)
            }]
        }

    def searchContent(self, key, quick, pg="1"):
        html = ""
        try:
            html = requests.post(self.host + "/search.php", headers=self.headers, data={"searchword": key}, timeout=15).text
        except Exception:
            html = ""
        if not html or "module-item" not in html:
            html = self.get(self.host + "/search.php?searchword=" + quote(key) + "&page=" + str(pg))
        return {"list": self.parseList(html), "page": int(pg)}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 1, "url": id, "header": self.headers}

    def localProxy(self, param):
        return [404, "text/plain", "", ""]

    def destroy(self):
        return "正在Destroy"

    def get(self, url):
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception:
            return ""

    def match(self, text, rule):
        m = re.search(rule, text or "", re.S)
        return m.group(1) if m else ""

    def clean(self, text):
        return re.sub(r"\s+", " ", re.sub(r"<.*?>", "", text or "")).strip()

    def fix(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return url

    def parseList(self, html):
        res = []
        seen = set()
        for m in re.finditer(r'<div class="module-item">([\s\S]*?)</div>\s*</div>', html or "", re.S):
            item = m.group(1)
            href = self.match(item, r'href=["\']/movie/index(\d+)\.html["\']')
            if not href or href in seen:
                continue
            seen.add(href)
            name = self.clean(self.match(item, r'alt=["\']([^"\']+)') or self.match(item, r'title=["\']([^"\']+)') or self.match(item, r'class="module-item-title"[^>]*>(.*?)</a>'))
            pic = self.fix(self.match(item, r'(?:data-src|data-original|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif)[^"\']*)'))
            remarks = self.clean(self.match(item, r'class="module-item-text"[^>]*>(.*?)</div>'))
            if name:
                res.append({
                    "vod_id": href,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
        if not res:
            for m in re.finditer(r'<a[^>]+href=["\']/movie/index(\d+)\.html["\'][^>]*title=["\']([^"\']+)["\'][\s\S]*?<img[^>]+(?:data-src|data-original|src)=["\']([^"\']+)["\'][\s\S]*?(?:class="module-item-text"[^>]*>(.*?)</div>)?', html or "", re.S):
                vid = m.group(1)
                if vid in seen:
                    continue
                seen.add(vid)
                res.append({
                    "vod_id": vid,
                    "vod_name": self.clean(m.group(2)),
                    "vod_pic": self.fix(m.group(3)),
                    "vod_remarks": self.clean(m.group(4))
                })
        return res