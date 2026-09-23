#!/usr/bin/python
# -*- coding: utf-8 -*-
import re, json, base64, requests, urllib.parse
from lxml import etree
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "搜搜追剧"

    def init(self, extend=""):
        self.host = "https://sszzyy.com/"
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        self.headers = {"User-Agent": self.ua, "Referer": self.host}
        self.categories = [
            {"type_id": "20", "type_name": "电影"},
            {"type_id": "37", "type_name": "连续剧"},
            {"type_id": "38", "type_name": "综艺"},
            {"type_id": "39", "type_name": "动漫"},
            {"type_id": "40", "type_name": "短剧"},
        ]

    def _get(self, url):
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except:
            return None

    def _fix(self, u):
        if not u:
            return ""
        if u.startswith("//"):
            return "https:" + u
        return self.host + u.lstrip("/") if u.startswith("/") else u

    def _cls(self, name):
        return f'contains(concat(" ", normalize-space(@class), " "), " {name} ")'

    def _strip(self, s):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()

    def _parseList(self, html):
        if not html:
            return []
        tree = etree.HTML(html)
        items, seen = [], set()
        boxes = tree.xpath(f'//div[{self._cls("stui-vodlist__box")}]')
        if not boxes:
            boxes = tree.xpath('//div[contains(@class,"stui-vodlist__box")]')
        for box in boxes:
            a = box.xpath('.//a[contains(@href,"/vod/detail/id/")]')
            if not a:
                continue
            a = a[0]
            m = re.search(r"/detail/id/(\d+)", a.get("href", ""))
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            img = box.xpath('.//img/@data-original') or box.xpath('.//img/@src') or box.xpath('.//a/@data-original') or box.xpath('.//a/@src')
            title = self._strip(a.get("title", "")) or self._strip("".join(box.xpath('.//div[contains(@class,"detail")]//text()')))
            remark = self._strip("".join(box.xpath(f'.//span[{self._cls("pic-text")}][1]//text()')))
            items.append({"vod_id": m.group(1), "vod_name": title, "vod_pic": self._fix(img[0] if img else ""), "vod_remarks": remark})
        return items

    def homeContent(self, filter):
        return {"class": self.categories, "list": self._parseList(self._get(self.host)), "filters": {}}

    def homeVideoContent(self):
        return {"list": self._parseList(self._get(self.host))}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        url = f"{self.host}index.php/vod/show/id/{tid}/page/{pg}.html"
        html = self._get(url)
        vodList = self._parseList(html)
        pagecount = 1
        if html:
            tree = etree.HTML(html)
            nums = [int(x) for x in tree.xpath(f'//ul[{self._cls("stui-page__item")}]//a//text()') if str(x).isdigit()]
            if nums:
                pagecount = max(nums)
        return {"page": pg, "pagecount": pagecount, "limit": len(vodList) or 24, "total": 999, "list": vodList}

    def _lineNames(self, tree):
        names = []
        for a in tree.xpath('//ul[contains(@class,"nav-tabs")]/li/a[contains(@href,"#playlist")]'):
            names.append(self._strip("".join(a.xpath(".//text()"))))
        return names or [f"线路{i+1}" for i in range(len(tree.xpath('//ul[contains(@class,"stui-content__playlist")]')) or 1)]

    def detailContent(self, ids):
        vid = str(ids[0]).split("/")[-1].replace(".html", "")
        html = self._get(f"{self.host}index.php/vod/detail/id/{vid}.html")
        if not html:
            return {"list": []}
        tree = etree.HTML(html)
        name = self._strip("".join(tree.xpath("//h1//text()")))
        pic = ""
        m = re.search(r"vod_pic\s*=\s*'([^']+)'", html) or re.search(r"vod_pic\s*=\s*\"([^\"]+)\"", html)
        if m:
            pic = m.group(1)
        if not pic:
            pic = "".join(tree.xpath('//meta[@property="og:image"]/@content'))
        if not pic:
            pic = "".join(tree.xpath('//div[contains(@class,"stui-content__thumb")]//img/@data-original')) or "".join(tree.xpath('//div[contains(@class,"stui-content__thumb")]//img/@src'))
        desc = ""
        m = re.search(r"vod_content\s*=\s*'([^']+)'", html)
        if m:
            try:
                desc = base64.b64decode(m.group(1)).decode("utf-8", "ignore").strip()
            except:
                desc = ""
        year = self._strip("".join(tree.xpath('//p[contains(@class,"data")]//text()')))
        names = self._lineNames(tree)
        uls = tree.xpath('//ul[contains(@class,"stui-content__playlist")]')
        urls = []
        for ul in uls:
            eps = []
            for a in ul.xpath('.//a[contains(@href,"/vod/play/id/")]'):
                t = self._strip("".join(a.xpath(".//text()")))
                eps.append(f"{t}${self._fix(a.get('href', ''))}")
            urls.append("#".join(eps))
        froms = names
        if len(urls) != len(froms):
            froms = [froms[i] if i < len(froms) else f"线路{i+1}" for i in range(len(urls))]
        return {"list": [{
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": self._fix(pic),
            "vod_year": year,
            "vod_content": desc,
            "vod_play_from": "$$$".join(froms),
            "vod_play_url": "$$$".join(urls),
        }]}

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if str(pg).isdigit() else 1
        url = f"{self.host}index.php/vod/search.html?wd={urllib.parse.quote(key)}"
        return {"list": self._parseList(self._get(url)), "page": pg}

    def playerContent(self, flag, id, vipFlags):
        url = id if str(id).startswith("http") else self._fix(id)
        html = self._get(url) or ""
        playUrl, enc = "", "0"
        m = re.search(r"player_aaaa\s*=\s*(\{.*?\})\s*</script>", html, re.S) or re.search(r"player_aaaa\s*=\s*(\{.*\})", html)
        if m:
            try:
                cfg = json.loads(m.group(1))
                playUrl, enc = cfg.get("url", ""), str(cfg.get("encrypt", "0"))
            except:
                playUrl = ""
        if not playUrl:
            m2 = re.search(r'"url"\s*:\s*"(.*?)"', html)
            playUrl = m2.group(1).replace("\\/", "/") if m2 else url
        playUrl = playUrl.replace("\\/", "/")
        try:
            if enc == "1":
                playUrl = urllib.parse.unquote(playUrl)
            elif enc == "2":
                playUrl = urllib.parse.unquote(base64.b64decode(playUrl).decode("utf-8"))
        except:
            pass
        finalUrl = playUrl if re.search(r"\.(m3u8|mp4|flv|mkv|ts)(\?|$)", playUrl.split("#")[0], re.I) else (playUrl if str(playUrl).startswith("http") else url)
        header = dict(self.headers)
        try:
            p = urllib.parse.urlparse(finalUrl)
            if p.scheme and p.netloc:
                header["Referer"] = f"{p.scheme}://{p.netloc}/"
        except:
            pass
        if playUrl and re.search(r"\.(m3u8|mp4|flv|mkv|ts)(\?|$)", playUrl.split("#")[0], re.I):
            return {"parse": 0, "url": finalUrl, "header": header}
        return {"parse": 1, "url": finalUrl, "header": header}
