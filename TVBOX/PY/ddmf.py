#!/usr/bin/python
# -*- coding: utf-8 -*-
import re, json, requests
from urllib.parse import quote
try:
    from lxml import etree
except Exception:
    etree = None
from base.spider import Spider

PAGEFMT = ["%s?page=%s", "%s/page/%s"]


class Spider(Spider):
    def getName(self): return "蛋蛋魔法影视"

    def init(self, extend=""):
        self.host = "https://www.ddmf.net"
        try: ext = json.loads(extend) if str(extend).strip().startswith("{") else {}
        except Exception: ext = {}
        if ext.get("host"): self.host = ext["host"].rstrip("/")
        self.pageFmt = ext.get("pageFmt", "")
        ua = ext.get("ua", "Mozilla/5.0 (Linux; Android 13; V2219A) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36")
        self.headers = {
            "User-Agent": ua,
            "Referer": self.host + "/",
            "Origin": self.host,
            "X-Turbo-Charged-By": "LiteSpeed",
        }
        if ext.get("cookie"): self.headers["Cookie"] = ext["cookie"]
        self.relay = ext.get("relay", "").rstrip("/")
        self.categories = [{"type_id": "1", "type_name": "电影"}, {"type_id": "2", "type_name": "电视剧"}, {"type_id": "3", "type_name": "综艺"}, {"type_id": "4", "type_name": "动漫"}]

    def _fix(self, u):
        if not u: return ""
        if u.startswith("//"): return "https:" + u
        if u.startswith("/"): return self.host + u
        return u

    def _gated(self, html):
        marks = ("Just a moment", "cf-chl", "__cf_chl", "Enable JavaScript and cookies", "cf_clearance", "Checking your browser")
        return bool(html) and any(m in html for m in marks)

    def _garbled(self, html):
        if not html: return False
        sample = html[:200]
        bad = sum(1 for c in sample if ord(c) < 32 and c not in "\t\n\r" or ord(c) > 0xfffd or (0xd800 <= ord(c) <= 0xdfff))
        return len(sample) > 0 and bad / len(sample) > 0.15

    def _direct(self, url):
        try:
            r = requests.get(url, headers=self.headers, timeout=15); r.encoding = "utf-8"
            return r.status_code, (r.text or "")
        except requests.exceptions.Timeout: print("[ERROR] 请求超时: %s" % url); return None, ""
        except requests.exceptions.ConnectionError: print("[ERROR] 连接错误: %s" % url); return None, ""
        except Exception as e: print("[ERROR] 请求失败: %s, %s" % (url, str(e))); return None, ""

    def _via_relay(self, url):
        if not self.relay: return None
        try:
            r = requests.get(self.relay + "/?url=" + quote(url, safe=""), headers={"User-Agent": self.headers["User-Agent"]}, timeout=45)
            r.encoding = "utf-8"
            return r.text or ""
        except Exception as e:
            print("[ERROR] relay失败: %s" % str(e)); return None

    def _get(self, path):
        url = path if path.startswith("http") else self.host + path
        status, body = self._direct(url)
        garbled = self._garbled(body)
        blocked = status is None or status >= 400 or self._gated(body) or garbled
        if blocked:
            if garbled:
                reason = "响应体疑似未正确解压(乱码，非拦截页文字)"
            elif self._gated(body):
                reason = "疑似JS挑战/机器人识别页"
            else:
                reason = "状态码%s" % status
            print("[WARN] 直连异常(%s) url=%s len=%d 片段=%r" % (reason, url, len(body), body[:200]))
            if garbled:
                print("[WARN] 响应体是压缩后未解压的二进制，不是拦截页内容，无法据此判断是否被拦截，请检查Accept-Encoding与本环境的解压库支持")
                return None
            if self.relay:
                print("[INFO] 尝试通过relay取页: %s" % url)
                relayed = self._via_relay(url)
                if relayed and not self._gated(relayed) and not self._garbled(relayed):
                    return relayed
                print("[WARN] relay取页仍失败或仍被拦截")
            else:
                print("[WARN] 浏览器可正常访问但脚本被拦，可能是请求头/TLS指纹识别，也可能是其他原因，需拿到真实响应体内容才能判断。"
                      "建议：1) 确认上面的浏览器级请求头是否已生效；2) 配置 ext.relay 走真实浏览器内核中转")
            return None
        return body

    def _tree(self, html, tag="页面"):
        if not html: return None
        if etree is None: print("[WARN] lxml 不可用"); return None
        tree = etree.HTML(html)
        if tree is None: print("[WARN] %s etree解析为空，长度=%d 片段=%r" % (tag, len(html), html[:80]))
        return tree

    _NOTE_RE = re.compile(r'^(更新HD|HD|第?\d+(?:\.\d+)?集?|全\d+集|正片|完结|全集|国语|中字|播放|立即播放|详情)$')

    def _name_of(self, a):
        name = (a.get("title") or "").strip()
        if name:
            return name if not self._NOTE_RE.match(name) else ""
        strong = "".join(a.xpath('.//strong//text()')).strip()
        if strong:
            return strong
        txt = "".join(a.xpath('.//text()')).strip()
        if not txt or self._NOTE_RE.match(txt):
            return ""
        return txt

    def _regex_list(self, html):
        out, seen = [], set()
        for m in re.finditer(r'href="[^"]*?/voddetail/(\d+)\.html"[^>]*?title="([^"]*)"|href="[^"]*?/voddetail/(\d+)\.html"[^>]*?<strong>([^<]*)</strong>', html):
            vid = m.group(1) or m.group(3)
            name = (m.group(2) or m.group(4) or "").strip()
            if not vid or vid in seen or not name: continue
            seen.add(vid); out.append({"vod_id": vid, "vod_name": name, "vod_pic": ""})
        return out

    def _cls(self, name):
        return 'contains(concat(" ", normalize-space(@class), " "), " %s ")' % name

    def _parse_list(self, html):
        if not html: return []
        tree = self._tree(html, "列表") if etree else None
        if tree is None: return self._regex_list(html)
        results, seen = [], set()
        cards = tree.xpath('//*[%s or %s]' % (self._cls("module-card-item"), self._cls("module-poster-item")))
        for card in cards:
            if card.xpath('.//div[contains(@class,"module-card-item-class")][contains(text(),"福利")]'):
                continue
            m = None
            for a in [card] + card.xpath('.//a[contains(@href,"/voddetail/")]'):
                mm = re.search(r'/voddetail/(\d+)\.html', a.get("href", ""))
                if mm and (a.get("title") or a.xpath('.//strong//text()')):
                    m = mm; break
            if m is None:
                for a in [card] + card.xpath('.//a[contains(@href,"/voddetail/")]'):
                    mm = re.search(r'/voddetail/(\d+)\.html', a.get("href", ""))
                    if mm: m = mm; break
            if not m or m.group(1) in seen: continue
            links = card.xpath('.//a[contains(@href,"/voddetail/")][@title]') or card.xpath('.//a[contains(@href,"/voddetail/")][.//strong]') or card.xpath('.//a[contains(@href,"/voddetail/")]')
            target = links[0] if links else card
            name = self._name_of(target)
            if not name: continue
            seen.add(m.group(1))
            pic = ""
            for at in ("data-original", "data-src", "src"):
                v = card.xpath('.//img/@%s' % at)
                if v and "load.gif" not in v[0]: pic = v[0]; break
            note = "".join(card.xpath('.//div[contains(@class,"module-item-note")]//text()')).strip()
            results.append({"vod_id": m.group(1), "vod_name": name, "vod_pic": self._fix(pic), "vod_remarks": note})
        return results

    def _first(self, lst): return lst[0]["vod_id"] if lst else ""

    def _paged(self, base, pg):
        if pg == "1": return self._get(base)
        if self.pageFmt: return self._get(self.pageFmt % (base, pg))
        first = self._first(self._parse_list(self._get(base)))
        for f in PAGEFMT:
            html = self._get(f % (base, pg))
            got = self._parse_list(html)
            if got and self._first(got) != first:
                self.pageFmt = f
                print("[INFO] 分页格式确定: %s" % (f % ("{base}", "{pg}")))
                return html
        print("[WARN] 未能确定分页格式(vodshow页码位置未验证)，仅返回首屏")
        return self._get(base)

    def _safe_home_list(self):
        # 首页 / 混杂了福利视频分区条目，不作为列表源；改为仅拼接白名单分类(电影/电视剧/综艺/动漫)的
        # vodtype 落地页，从源头避免福利视频内容混入
        out, seen = [], set()
        for c in self.categories:
            for v in self._parse_list(self._get("/vodtype/%s.html" % c["type_id"])):
                if v["vod_id"] in seen: continue
                seen.add(v["vod_id"]); out.append(v)
                if len(out) >= 60: return out
        return out

    def homeContent(self, filter):
        fl = {c["type_id"]: [{"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(2026, 2014, -1)]}] for c in self.categories}
        return {"class": self.categories, "list": self._safe_home_list(), "filters": fl}

    def homeVideoContent(self): return {"list": self._safe_home_list()}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or "1")
        year = (extend or {}).get("year", "")
        base = "/vodshow/%s-----------%s.html" % (tid, year) if year else "/vodshow/%s-----------.html" % tid
        lst = self._parse_list(self._paged(base, pg))
        return {"page": int(pg), "pagecount": int(pg) + 1 if lst else int(pg), "limit": 32, "total": 999999, "list": lst}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or "1")
        lst = self._parse_list(self._get("/vodsearch/%s-------------.html" % quote(key)))
        return {"list": lst, "page": int(pg)}

    def _field(self, text, key):
        m = re.search(r'%s\s*[:：]\s*([^\n]{1,200})' % key, text)
        return m.group(1).strip(" \u3000|/") if m else ""

    def detailContent(self, ids):
        vid = re.sub(r'\D', '', str(ids[0]))
        html = self._get("/voddetail/%s.html" % vid)
        tree = self._tree(html, "详情页")
        if tree is None: return {"list": []}
        text = "\n".join(x.strip() for x in tree.xpath('//text()') if x.strip())
        pic = ""
        for v in tree.xpath('//img/@data-original | //img/@src'):
            if v and "load.gif" not in v and "logo" not in v and "touxiang" not in v and "dsm.jpg" not in v:
                pic = v; break
        intro = "".join(tree.xpath('//div[contains(@class,"module-info-introduction-content")]//p//text() | //div[contains(@class,"module-info-introduction-content")]//text()')).strip()
        intro = re.sub(r'(?:艾旦影视|海外影院|海外影视|海外华人|海外福利影院|蛋蛋电影网|haiwaiyingyuan)[^<]*$', '', intro)
        remarks = self._field(text, "备注") or self._field(text, "更新") or self._field(text, "连载")
        if re.search(r'\d{4}-\d{2}-\d{2}', remarks or ""): remarks = ""
        vod = {"vod_id": vid,
               "vod_name": "".join(tree.xpath('//h1//text()')).strip(),
               "vod_pic": self._fix(pic),
               "vod_year": self._field(text, "年份") or "".join(tree.xpath('//a[contains(@href,"/vodshow/")]/text()')[:1]).strip(),
               "vod_area": "".join(tree.xpath('//a[contains(@href,"/vodshow/")]/text()')[1:2]).strip(),
               "type_name": "".join(tree.xpath('//a[contains(@href,"/vodshow/")]/text()')[2:3]).strip(),
               "vod_director": self._field(text, "导演"), "vod_actor": self._field(text, "主演"),
               "vod_remarks": remarks,
               "vod_content": intro or self._field(text, "剧情") or self._field(text, "简介")}
        groups, best = {}, {}
        tabs = tree.xpath('//*[contains(@class,"module-tab-item")]/@data-dropdown-value')
        src_order = []
        for panel in tree.xpath('//*[contains(@class,"module-list")][@id]'):
            for a in panel.xpath('.//a[contains(@href,"/vodplay/")]'):
                mm = re.search(r'/vodplay/%s-(\d+)-' % vid, a.get("href", ""))
                if mm and mm.group(1) not in src_order:
                    src_order.append(mm.group(1))
        tab_of = {}
        for i, tab in enumerate(tabs):
            if i < len(src_order): tab_of[src_order[i]] = tab
        for a in tree.xpath('//a[contains(@href,"/vodplay/")]'):
            lk = a.get("href", "")
            m = re.search(r'/vodplay/%s-(\d+)-(\d+)\.html' % vid, lk)
            if not m: continue
            src, ep = m.group(1), int(m.group(2))
            span = "".join(a.xpath('.//span//text()')).strip()
            cand = (span, lk, a)
            prev = best.get((src, ep))
            if prev is None or (span and not prev[0]):
                best[(src, ep)] = cand
        for (src, ep), (span, lk, a) in sorted(best.items()):
            nm = span or (a.get("title") or "").strip()
            nm = re.sub(r'^播放.{0,40}第|^播放.{0,40}(?:全集|正片)?$|^立即?播放|^立刻播放', '', nm) or ("第%d集" % ep)
            groups.setdefault(src, []).append((ep, nm, lk))
        froms, urls = [], []
        for src in sorted(groups, key=lambda s: (len(s), s)):
            eps = sorted(groups[src], key=lambda x: x[0])
            froms.append(tab_of.get(src) or "线路%s" % src)
            urls.append("#".join(nm.replace("$", "").replace("#", "") + "$" + self._fix(lk) for _, nm, lk in eps))
        vod["vod_play_from"] = "$$$".join(froms) if froms else "蛋蛋魔法影视"
        vod["vod_play_url"] = "$$$".join(urls) if urls else ("正片$%s/voddetail/%s.html" % (self.host, vid))
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        pid = id if id.startswith("http") else self._fix(id)
        html = self._get(pid) or ""
        url = ""
        for p in [r'var\s+player_\w*\s*=\s*(\{.*?\})\s*[<;]', r'"url"\s*:\s*"([^"]+)"', r'var\s+now\s*=\s*["\']([^"\']+)["\']', r'url:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', r'(https?://[^\s"\'\\<>]+\.(?:m3u8|mp4)[^\s"\'\\<>]*)']:
            m = re.search(p, html.replace("\\/", "/"), re.S)
            if not m: continue
            val = m.group(1)
            if val.startswith("{"):
                try: val = json.loads(val).get("url", "")
                except Exception:
                    m2 = re.search(r'"url"\s*:\s*"([^"]+)"', val); val = m2.group(1).replace("\\/", "/") if m2 else ""
            if val: url = self._fix(val); break
        if not url: return {"parse": 1, "url": pid, "header": {**self.headers, "Referer": pid}}
        m = re.match(r'https?://[^/]+', url)
        ref = m.group(0) if m else self.host
        return {"parse": 0, "url": url, "header": {"User-Agent": self.headers["User-Agent"], "Referer": ref}}
