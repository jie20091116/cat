import re
import json
import urllib.parse
from base.spider import Spider
from bs4 import BeautifulSoup


class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.host = "https://www.wancaifang.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host
        }
        self._timeout = 15

    def init(self, extend=""):
        pass

    def getName(self):
        return "万彩坊"

    def getDependence(self):
        return []

    def destroy(self):
        pass

    def _fix(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return url

    def _parse_list(self, html):
        videos = []
        seen = set()
        for m in re.finditer(
            r'<a[^>]*class="[^"]*stui-vodlist__thumb[^"]*"[^>]+href="(https?://[^"]+/detail/(\d+)\.html)"[^>]+title="([^"]*)"[^>]+data-original="([^"]*)"',
            html):
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            videos.append({
                "vod_id": vid,
                "vod_name": m.group(3),
                "vod_pic": self._fix(m.group(4)),
                "vod_remarks": ""
            })
        return videos

    def homeContent(self, filter):
        classes = [
            {"type_id": "9322", "type_name": "电影"},
            {"type_id": "9323", "type_name": "剧集"},
            {"type_id": "9324", "type_name": "综艺"},
            {"type_id": "9325", "type_name": "动漫"},
            {"type_id": "9326", "type_name": "短剧"},
        ]
        sort_filter = {"key": "sort", "name": "排序", "value": [
            {"n": "最新上映", "v": ""}, {"n": "最新更新", "v": "time"},
            {"n": "点击榜", "v": "visit"}, {"n": "推荐榜", "v": "vote"},
        ]}
        filters = {}
        for tid in ["9322", "9323", "9324", "9325", "9326"]:
            filters[tid] = [
                {"key": "type", "name": "类型", "value": [
                    {"n": "全部", "v": tid},
                ]},
                sort_filter,
            ]
        filters["9322"][0]["value"] += [
            {"n": "喜剧片", "v": "9332"}, {"n": "爱情片", "v": "9333"},
            {"n": "动作片", "v": "9334"}, {"n": "科幻片", "v": "9335"}, {"n": "恐怖片", "v": "9336"},
            {"n": "战争片", "v": "9337"}, {"n": "剧情片", "v": "9338"}, {"n": "动画片", "v": "9339"},
            {"n": "记录片", "v": "9340"},
        ]
        filters["9323"][0]["value"] += [
            {"n": "国产剧", "v": "9342"}, {"n": "港台剧", "v": "9343"},
            {"n": "韩国剧", "v": "9344"}, {"n": "日本剧", "v": "9345"}, {"n": "欧美剧", "v": "9346"},
            {"n": "泰国剧", "v": "9347"}, {"n": "海外剧", "v": "9348"},
        ]
        filters["9324"][0]["value"] += [
            {"n": "大陆综艺", "v": "9352"}, {"n": "港台综艺", "v": "9353"},
            {"n": "日韩综艺", "v": "9354"}, {"n": "欧美综艺", "v": "9355"},
        ]
        filters["9325"][0]["value"] += [
            {"n": "国产动漫", "v": "9362"}, {"n": "港台动漫", "v": "9363"},
            {"n": "日韩动漫", "v": "9364"}, {"n": "欧美动漫", "v": "9365"},
        ]
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        rsp = self.fetch(self.host, headers=self.headers, timeout=self._timeout)
        return {"list": self._parse_list(rsp.text)[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        t = extend.get('type', tid)
        sort = extend.get('sort', '')
        if sort:
            url = f"{self.host}/sortlist/{t}/{sort}-{pg}.html"
        elif pg == "1":
            url = f"{self.host}/sortlist/{t}.html"
        else:
            url = f"{self.host}/sortlist/{t}/last-{pg}.html"
        rsp = self.fetch(url, headers=self.headers, timeout=self._timeout)
        return {"list": self._parse_list(rsp.text), "pagecount": 9999}

    def detailContent(self, ids):
        vid = ids[0]
        rsp = self.fetch(f"{self.host}/detail/{vid}.html", headers=self.headers, timeout=self._timeout)
        html = rsp.text
        soup = BeautifulSoup(html, 'html.parser')

        vod = {"vod_id": vid}

        jsonld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        if jsonld:
            try:
                data = json.loads(jsonld.group(1))
                for item in data.get("@graph", []):
                    if item.get("@type") == "VideoObject":
                        vod["vod_name"] = item.get("name", "")
                        vod["vod_content"] = item.get("description", "")
                        thumbs = item.get("thumbnailUrl", [""])
                        vod["vod_pic"] = self._fix(thumbs[0] if isinstance(thumbs, list) else thumbs)
                        break
            except:
                pass

        og_img = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if og_img and "vod_pic" not in vod:
            vod["vod_pic"] = self._fix(og_img.group(1))
        og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if og_title and "vod_name" not in vod:
            vod["vod_name"] = og_title.group(1)
        if "vod_name" not in vod:
            m = re.search(r'<title>([^<]+)</title>', html)
            if m:
                name = m.group(1)
                name = re.sub(r'高清完整版在线观看.*', '', name)
                name = re.sub(r'[-–—].*', '', name)
                vod["vod_name"] = name.strip()

        desc = re.search(r'<meta name="description" content="([^"]+)"', html)
        if desc and "vod_content" not in vod:
            vod["vod_content"] = desc.group(1)

        label_map = {"类型": "type_name", "地区": "vod_area", "年份": "vod_year", "语言": "vod_lang"}
        for p in soup.find_all('p', class_=lambda c: c and 'data' in c):
            all_spans = p.find_all('span', class_=lambda c: c and 'text-muted' in c)
            if not all_spans:
                continue
            first_label = all_spans[0].get_text(strip=True).rstrip('：:')
            if first_label in ("导演", "主演"):
                full_text = p.get_text(strip=True).replace(all_spans[0].get_text(strip=True), '').strip()
                if first_label == "导演":
                    vod["vod_director"] = full_text
                else:
                    vod["vod_actor"] = full_text
            else:
                full_raw = p.get_text(strip=True)
                label_positions = []
                for span in all_spans:
                    span_clean = ''.join(span.find_all(string=True, recursive=False)).strip()
                    if not span_clean:
                        span_clean = span.get_text(strip=True)
                    label = span_clean.rstrip('：:')
                    if label in label_map:
                        idx = full_raw.find(span_clean)
                        if idx >= 0:
                            label_positions.append((label, idx, len(span_clean)))
                label_positions.sort(key=lambda x: x[1])
                for i, (label, idx, span_len) in enumerate(label_positions):
                    key = label_map[label]
                    start = idx + span_len
                    if i + 1 < len(label_positions):
                        end = label_positions[i + 1][1]
                    else:
                        end = len(full_raw)
                    value = full_raw[start:end].strip().rstrip('：:')
                    if label == "年份":
                        m = re.search(r'\d{4}', value)
                        if m:
                            value = m.group()
                    if value:
                        vod[key] = value

        episodes = []
        for a in soup.select('[class*="stui-content__playlist"] a[href*="/movie/"]'):
            href = a.get('href', '')
            title = a.get('title', '') or a.text.strip()
            if href and title:
                episodes.append(f"{title}${self._fix(href)}")

        if episodes:
            vod["vod_play_from"] = "默认线路"
            vod["vod_play_url"] = "#".join(episodes)
        else:
            vod["vod_play_from"] = "默认线路"
            vod["vod_play_url"] = f"播放${self._fix(f'/detail/{vid}.html')}"

        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/index.php/vod/search.html?wd={urllib.parse.quote(key)}"
        rsp = self.fetch(url, headers=self.headers, timeout=self._timeout)
        return {"list": self._parse_list(rsp.text), "pagecount": 1}

    def playerContent(self, flag, id, vipFlags):
        play_url = self._fix(id)
        rsp = self.fetch(play_url, headers=self.headers, timeout=self._timeout)
        m = re.search(r'thisUrl\s*=\s*"([^"]+)"', rsp.text)
        if m:
            video_url = m.group(1).replace('\\', '')
            if video_url:
                return {"parse": 0, "url": video_url, "header": self.headers}
        return {"parse": 1, "url": play_url, "header": self.headers}

    def isVideoFormat(self, url):
        if not url:
            return False
        return any(ext in url for ext in ['.mp4', '.m3u8', '.flv', '.avi', '.mkv', '.ts'])

    def manualVideoCheck(self):
        return False

