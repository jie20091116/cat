#!/usr/bin/python
# -*- coding: utf-8 -*-
import re, json, requests
from urllib.parse import quote, urlencode
try:
    from lxml import etree
except Exception:
    etree = None
from base.spider import Spider


class Spider(Spider):
    def getName(self): return "PTT视频"

    def init(self, extend=""):
        self.host = "https://ptt.red"
        try: ext = json.loads(extend) if str(extend).strip().startswith("{") else {}
        except Exception: ext = {}
        self.lang = ext.get("lang", "")
        self.relay = ext.get("relay", "").rstrip("/")
        self.searchPath = ""
        self.headers = {"User-Agent": ext.get("ua", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"), "Referer": self.host + "/", "Accept-Language": "zh-TW,zh;q=0.9"}
        if ext.get("cookie"): self.headers["Cookie"] = ext["cookie"]
        self.categories = [{"type_id": "3", "type_name": "电视剧"}, {"type_id": "1", "type_name": "电影"}, {"type_id": "4", "type_name": "动漫"}, {"type_id": "2", "type_name": "综艺"}, {"type_id": "66", "type_name": "短剧"}, {"type_id": "53", "type_name": "体育"}]
        self.areas = [["全部", ""], ["大陆", "19"], ["香港", "20"], ["台湾", "81"], ["日本", "83"], ["韩国", "82"], ["欧美", "22"], ["泰国", "92"], ["其他", "23"]]
        self.years = ["2026", "2025", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017", "2016"]

    def _fix(self, u):
        if not u: return ""
        if u.startswith("//"): return "https:" + u
        if u.startswith("/"): return self.host + u
        return u

    def _blocked(self, t): return not t or "Just a moment" in t or "cf-chl" in t or "Enable JavaScript and cookies" in t or "__cdnlah_pow_config" in t or "_chg_waf_pow" in t

    def _get(self, path):
        url = path if path.startswith("http") else self.host + self.lang + path
        txt = None
        try:
            r = requests.get(url, headers=self.headers, timeout=15); r.encoding = "utf-8"; txt = r.text
            if self._blocked(txt): print("[WARN] 被网关拦截 status=%s len=%s url=%s" % (r.status_code, len(txt), url))
        except requests.exceptions.Timeout: print("[ERROR] 请求超时: %s" % url)
        except requests.exceptions.ConnectionError: print("[ERROR] 连接错误: %s" % url)
        except Exception as e: print("[ERROR] 请求失败: %s, %s" % (url, str(e)))
        if self._blocked(txt) and self.relay:
            try:
                r = requests.get(self.relay + "/?url=" + quote(url, safe=""), headers={"User-Agent": self.headers["User-Agent"]}, timeout=45); r.encoding = "utf-8"; txt = r.text
            except Exception as e: print("[ERROR] relay失败: %s" % str(e))
        return None if self._blocked(txt) else txt

    def _pic(self, vid):
        try: return "%s/images/node/%d/%s.avif" % (self.host, int(vid) // 10000, vid)
        except Exception: return ""

    def _parse_list(self, html):
        if not html: return []
        if etree is None:
            print("[WARN] lxml 不可用，降级为正则解析")
            return [{"vod_id": v, "vod_name": n, "vod_pic": self._fix(p)} for v, p, n in dict((m[0], m) for m in re.findall(r'href="/(\d+)"><img[^>]*?src="([^"]+)"[^>]*?alt="([^"]*)"', html)).values()]
        tree = etree.HTML(html); results, seen = [], set()
        items = tree.xpath('//div[@id="videos"]//div[contains(@class,"item")]') or tree.xpath('//div[contains(@class,"card")][.//img[@alt]]') or tree.xpath('//a[.//img[@alt]]')
        for it in items:
            try:
                href = "".join(it.xpath('.//a/@href')[:1]) or it.get("href", "")
                vid = href.strip("/").split("/")[-1]
                if not vid.isdigit() or vid in seen: continue
                name = "".join(it.xpath('.//img/@alt')[:1]).strip() or "".join(it.xpath('.//div[contains(@class,"lines")]//a//text()')).strip()
                if not name: continue
                seen.add(vid)
                pic = "".join(it.xpath('.//img/@data-original | .//img/@data-src | .//img/@src')[:1])
                note = "".join(it.xpath('.//div[contains(@class,"imagelabel-bottom-right")]//text()')).strip()
                year = "".join(it.xpath('.//div[contains(@class,"imagelabel-bottom-left")]//text()')).strip()
                results.append({"vod_id": vid, "vod_name": name, "vod_pic": self._fix(pic) or self._pic(vid), "vod_year": year.replace("年", ""), "vod_remarks": note})
            except Exception: continue
        return results

    def _get_pagination(self, html, pg):
        if not html: return int(pg)
        tree = etree.HTML(html)
        nums = [int(x) for x in tree.xpath('//ul[contains(@class,"pagination")]//a[@data-page]/text()') if x.strip().isdigit()]
        nxt = tree.xpath('//li[contains(@class,"page-item") and contains(@class,"next")]/@class')
        return max(nums + [int(pg)]) + (1 if nxt and "disabled" not in nxt[0] else 0)

    def _extract_m3u8(self, html):
        if not html: return None
        for p in [r'var\s+now\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']', r'var\s+player_data\s*=\s*(\{.*?\})', r'player_\w+\s*=\s*(\{.*?\})\s*[;<]', r'url:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', r'var\s+playurl\s*=\s*["\']([^"\']+)["\']', r'(https?://[^\s"\'\\]+\.(?:m3u8|mp4)[^\s"\'\\]*)']:
            m = re.search(p, html.replace("\\/", "/"), re.S)
            if not m: continue
            val = m.group(1)
            if val.startswith("{"):
                try: val = json.loads(val).get("url", "")
                except Exception:
                    m2 = re.search(r'"(https?://[^"]+\.(?:m3u8|mp4)[^"]*)"', val); val = m2.group(1) if m2 else ""
            if val: return self._fix(val)
        return None

    def homeContent(self, filter):
        fl = {c["type_id"]: [{"key": "category_id", "name": "地区", "value": [{"n": a[0], "v": a[1]} for a in self.areas]}, {"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}] + [{"n": y, "v": y} for y in self.years]}] for c in self.categories}
        return {"class": self.categories, "list": self._parse_list(self._get("/")), "filters": fl}

    def homeVideoContent(self): return {"list": self._parse_list(self._get("/"))}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        qs = {"page": pg}
        for k in ("category_id", "year"):
            if (extend or {}).get(k): qs[k] = extend[k]
        html = self._get("/p/%s?%s" % (tid, urlencode(qs)))
        lst = self._parse_list(html)
        return {"page": int(pg), "pagecount": self._get_pagination(html, pg) if lst else int(pg), "limit": 48, "total": 999999, "list": lst}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        for p in ([self.searchPath] if self.searchPath else ["/node/search?q={k}&page={p}", "/node/search?keyword={k}&page={p}", "/node/search?title={k}&page={p}", "/s/{k}?page={p}"]):
            lst = self._parse_list(self._get(p.format(k=quote(key), p=pg)))
            if lst:
                self.searchPath = p
                return {"list": lst, "page": int(pg)}
        return {"list": [], "page": int(pg)}

    def detailContent(self, ids):
        vid = str(ids[0]).strip("/").split("/")[-1]
        html = self._get("/" + vid)
        if not html: return {"list": []}
        tree = etree.HTML(html)
        title = ("".join(tree.xpath('//h1//text()')).strip() or "".join(tree.xpath('//title/text()')).split(" - ")[0].strip())
        eps, seen = [], set()
        for a in tree.xpath('//a[@href]'):
            lk = a.get("href", "")
            if lk in seen or not re.match(r'^/%s[/\-_]|^/play/|^/v/%s' % (vid, vid), lk): continue
            nm = ("".join(a.xpath('.//text()')).strip() or a.get("title", "")).strip()
            if not nm: continue
            seen.add(lk)
            eps.append(nm.replace("$", "").replace("#", "") + "$" + self._fix(lk))
        return {"list": [{"vod_id": vid, "vod_name": title, "vod_pic": self._pic(vid), "vod_content": "".join(tree.xpath('//div[contains(@class,"content-wrapper")]//p[1]//text()')).strip(), "vod_play_from": "PTT", "vod_play_url": "#".join(eps or ["正片$" + self.host + "/" + vid])}]}

    def playerContent(self, flag, id, vipFlags):
        pid = id if id.startswith("http") else self.host + "/" + id.strip("/")
        url = self._extract_m3u8(self._get(pid))
        if not url: return {"parse": 1, "url": pid, "header": self.headers}
        return {"parse": 0, "url": url, "header": {"User-Agent": self.headers["User-Agent"], "Referer": self.host + "/"}}
