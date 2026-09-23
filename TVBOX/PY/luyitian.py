# coding=utf-8
import sys
import json
import re
import requests
import base64
from bs4 import BeautifulSoup
from urllib.parse import unquote, urljoin

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider():
        def fetch(self, url, headers=None, timeout=10):
            try:
                res = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                res.encoding = 'utf-8'
                return res
            except Exception as e:
                print(f"fetch error: {e}")
                return None

class Spider(BaseSpider):
    def getName(self):
        return "撸一天"

    def init(self, extend=""):
        self.host = "https://luyitian.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        })

    def homeVideoContent(self):
        return {"list": []}

    def localProxy(self, params):
        return [200, "video/MP2T", ""]

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def fetch(self, url, headers=None, timeout=5):
        try:
            req_headers = headers or self.session.headers
            res = self.session.get(url, headers=req_headers, timeout=timeout, allow_redirects=True)
            res.encoding = 'utf-8'
            return res
        except Exception as e:
            print(f"fetch error: {e}")
            return None

    def homeContent(self, filter):
        # ---------- 修复分类：使用完整 34 个分类（与 luyitian.py 一致） ----------
        classes = [
            {"type_name": "国产精品", "type_id": "26"}, {"type_name": "中文字幕", "type_id": "28"},
            {"type_name": "日本有码", "type_id": "11"}, {"type_name": "日本无码", "type_id": "12"},
            {"type_name": "国产剧情", "type_id": "27"}, {"type_name": "国产自拍", "type_id": "29"},
            {"type_name": "欧美精品", "type_id": "31"}, {"type_name": "动漫视频", "type_id": "4"},
            {"type_name": "三级伦理", "type_id": "10"}, {"type_name": "网友自拍", "type_id": "2"},
            {"type_name": "成人动漫", "type_id": "24"}, {"type_name": "丝袜足交", "type_id": "23"},
            {"type_name": "乱伦熟女", "type_id": "21"}, {"type_name": "制服诱惑", "type_id": "22"},
            {"type_name": "强奸乱伦", "type_id": "25"}, {"type_name": "日本中字", "type_id": "51"},
            {"type_name": "欧美中字", "type_id": "52"}, {"type_name": "网红明星", "type_id": "91"},
            {"type_name": "麻豆传媒", "type_id": "92"}, {"type_name": "天美传媒", "type_id": "93"},
            {"type_name": "果冻传媒", "type_id": "94"}, {"type_name": "星空无限", "type_id": "95"},
            {"type_name": "精东影业", "type_id": "96"}, {"type_name": "蜜桃影像", "type_id": "97"},
            {"type_name": "九一视频", "type_id": "98"}, {"type_name": "糖心视频", "type_id": "99"},
            {"type_name": "皇家华人", "type_id": "100"}, {"type_name": "传媒汇总", "type_id": "101"},
            {"type_name": "偷拍自拍", "type_id": "102"}, {"type_name": "推特网红", "type_id": "103"},
            {"type_name": "经典老片", "type_id": "81"}, {"type_name": "国模私拍", "type_id": "85"},
            {"type_name": "国产主播", "type_id": "35"}, {"type_name": "国产SM", "type_id": "105"}
        ]

        # ---------- 修正 filters：去除已废弃的子分类，保留有效的映射 ----------
        filters = {
            # 中文字幕 (28) 下可能有子分类，但原filter中的“日本中字”其实对应51，此处保留
            "28": [{"key": "tid", "name": "子分类", "value": [{"n": "全部", "v": "28"}, {"n": "日本中字", "v": "51"}]}],
            # 国产精品 (26) 下没有子分类，但为了兼容过滤，我们可以留空
            "26": [{"key": "tid", "name": "子分类", "value": [{"n": "全部", "v": "26"}]}],
            # 其他分类按需添加，这里只保留有效的
            "20": [{"key": "tid", "name": "子分类", "value": [{"n": "全部", "v": "20"}, {"n": "国产精品", "v": "26"}, {"n": "国产剧情", "v": "27"}, {"n": "国产自拍", "v": "29"}, {"n": "国产主播", "v": "35"}, {"n": "国模私拍", "v": "85"}, {"n": "网红明星", "v": "91"}, {"n": "国产SM", "v": "105"}]}],
            "21": [{"key": "tid", "name": "子分类", "value": [{"n": "全部", "v": "21"}, {"n": "人妻", "v": "31"}, {"n": "素人", "v": "44"}, {"n": "口爆颜射", "v": "46"}, {"n": "萝莉少女", "v": "47"}, {"n": "美乳巨乳", "v": "48"}, {"n": "制服诱惑", "v": "52"}, {"n": "调教", "v": "57"}, {"n": "出轨", "v": "58"}, {"n": "有码精品", "v": "101"}]}],
            "22": [{"key": "tid", "name": "子分类", "value": [{"n": "全部", "v": "22"}, {"n": "无码精品", "v": "102"}]}],
            "23": [{"key": "tid", "name": "子分类", "value": [{"n": "全部", "v": "23"}, {"n": "欧美精品", "v": "104"}]}],
            "24": [{"key": "tid", "name": "子分类", "value": [{"n": "全部", "v": "24"}, {"n": "动漫精品", "v": "103"}]}],
            "25": [{"key": "tid", "name": "子分类", "value": [{"n": "全部", "v": "25"}, {"n": "综合三级", "v": "39"}]}],
            "36": [{"key": "tid", "name": "子分类", "value": [{"n": "全部", "v": "36"}, {"n": "韩国主播", "v": "37"}]}],
            "41": [{"key": "tid", "name": "子分类", "value": [{"n": "全部", "v": "41"}, {"n": "Cosplay", "v": "106"}]}]
        }

        return {'class': classes, 'filters': filters}

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 999, "limit": 20, "total": 9999}
        
        real_tid = extend.get('tid', tid)
        # ---------- 尝试多种 URL 格式，解决国产精品无数据问题 ----------
        urls_to_try = [
            f"{self.host}/vodtype/{real_tid}-{pg}/",
            f"{self.host}/vodtype/{real_tid}-{pg}.html",
            f"{self.host}/vodtype/{real_tid}/",
            f"{self.host}/vodtype/{real_tid}.html"
        ]
        res = None
        for url in urls_to_try:
            print(f"Trying URL: {url}")  # 调试输出，可注释
            res = self.fetch(url, headers={'Referer': self.host})
            if res and res.status_code == 200:
                # 简单检查页面是否包含视频列表元素
                if 'video' in res.text or 'vod' in res.text or 'item' in res.text:
                    break
            res = None
        if not res:
            return result

        soup = BeautifulSoup(res.text, 'html.parser')
        vod_list = []
        
        # 合并多个选择器，优先使用更通用的
        items = (soup.select('.video-film-list .video-item') or
                 soup.select('div#mdym > div') or
                 soup.select('.stui-vodlist__item') or
                 soup.select('.myui-vodlist__box') or
                 soup.select('.video-item') or
                 soup.select('.item') or
                 soup.select('.vodlist_item') or
                 soup.select('.video-img-box'))

        for item in items:
            a = item.select_one('a') or item.find('a')
            if not a:
                continue

            href = a.get('href', '')
            # 尝试多种 ID 提取方式
            vid_match = re.search(r'/vodplay/(\d+)', href)
            if not vid_match:
                vid_match = re.search(r'/voddetail/(\d+)', href)
            vid = vid_match.group(1) if vid_match else href

            name = ""
            img = item.select_one('img')
            if img and img.get('alt'):
                name = img['alt']
            if not name and a.get('title'):
                name = a['title']
            if not name:
                title_elem = item.select_one('.title') or item.select_one('.name') or item.select_one('.text') or item.select_one('.video-title')
                if title_elem:
                    name = title_elem.get_text(strip=True)
            if not name:
                name = a.get_text(strip=True)
            if not name:
                name = "未知标题"

            pic = ""
            if img:
                pic = img.get('data-src') or img.get('src', '')
                if pic and not pic.startswith('http'):
                    pic = urljoin(self.host, pic)

            remark = ""
            remark_elem = item.select_one('.remarks') or item.select_one('.note') or item.select_one('.tag') or item.select_one('.sub-title') or item.select_one('.video-remarks')
            if remark_elem:
                remark = remark_elem.get_text(strip=True)
            elif item.text.strip():
                lines = [l.strip() for l in item.text.split('\n') if l.strip()]
                if lines:
                    remark = lines[-1][:20]

            vod_list.append({
                "vod_id": vid,
                "vod_name": name.strip(),
                "vod_pic": pic,
                "vod_remarks": remark
            })

        result['list'] = vod_list
        # 分页信息提取
        page_elem = soup.select_one('.page .page-link, .pagination a, .page a')
        if page_elem:
            try:
                last_page = int(re.search(r'(\d+)', page_elem.get('href', '')).group(1)) if 'href' in page_elem.attrs else 1
                result['pagecount'] = max(last_page, 1)
            except:
                pass
        return result

    def detailContent(self, ids):
        vid = ids[0]
        url = f"{self.host}/vodplay/{vid}-1-1/"
        res = self.fetch(url, headers={'Referer': self.host})
        if not res:
            return {"list": []}

        soup = BeautifulSoup(res.text, 'html.parser')
        raw_title = soup.title.text.split('|')[0].replace('在线播放在线观看','').replace('《','').replace('》','').strip()

        vod = {
            "vod_id": vid,
            "vod_name": raw_title,
            "vod_type": "视频",
            "vod_content": "资源来自于网络",
            "vod_play_from": "Luyitian",
            "vod_play_url": f"播放${vid}-1-1"
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg=1):
        url = f"{self.host}/vodsearch/{key}----------{pg}---/"
        res = self.fetch(url, headers={'Referer': self.host})
        if not res:
            return {"list": []}

        soup = BeautifulSoup(res.text, 'html.parser')
        vod_list = []
        items = (soup.select('.video-film-list .video-item') or
                 soup.select('div#mdym > div') or
                 soup.select('.stui-vodlist__item') or
                 soup.select('.myui-vodlist__box') or
                 soup.select('.video-item') or
                 soup.select('.video-img-box'))

        for item in items:
            a = item.select_one('a') or item.find('a')
            if not a:
                continue

            href = a.get('href', '')
            vid_match = re.search(r'/vodplay/(\d+)', href)
            vid = vid_match.group(1) if vid_match else href

            name = ""
            img = item.select_one('img')
            if img and img.get('alt'):
                name = img['alt']
            if not name and a.get('title'):
                name = a['title']
            if not name:
                title_elem = item.select_one('.title') or item.select_one('.name') or item.select_one('.video-title')
                if title_elem:
                    name = title_elem.get_text(strip=True)
            if not name:
                name = a.get_text(strip=True)
            if not name:
                name = "搜索结果"

            pic = ""
            if img:
                pic = img.get('data-src') or img.get('src', '')

            vod_list.append({
                "vod_id": vid,
                "vod_name": name.strip(),
                "vod_pic": pic,
                "vod_remarks": ""
            })
        return {"list": vod_list}

    def _js_decode(self, js_str):
        b64_match = re.search(r'atob\s*\(\s*["\']([^"\']+)["\']\s*\)', js_str)
        if b64_match:
            try:
                decoded = base64.b64decode(b64_match.group(1)).decode('utf-8')
                return decoded
            except:
                pass
        unescape_match = re.search(r'unescape\s*\(\s*["\']([^"\']+)["\']\s*\)', js_str)
        if unescape_match:
            try:
                decoded = unquote(unescape_match.group(1))
                return decoded
            except:
                pass
        url_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', js_str, re.I)
        if url_match:
            return url_match.group(1)
        return None

    def _sniff_xhr(self, html, page_url):
        patterns = [
            r'fetch\s*\(\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'XMLHttpRequest.*?\.open\s*\(\s*["\']GET["\']\s*,\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'\.get\s*\(\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'url\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'src\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]
        for pat in patterns:
            match = re.search(pat, html, re.I)
            if match:
                url = match.group(1)
                if not url.startswith('http'):
                    url = urljoin(page_url, url)
                return url
                
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.I | re.S)
        for script_content in scripts:
            if script_content.strip():
                found = self._js_decode(script_content)
                if found and '.m3u8' in found:
                    return found
        return None

    def playerContent(self, flag, id, vipFlags=None):
        play_url = f"{self.host}/vodplay/{id}/"
        res = self.fetch(play_url, headers={'Referer': self.host}, timeout=5)
        if not res:
            return {"parse": 1, "url": play_url}

        html = res.text
        m3u8_url = None

        match = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\});', html, re.DOTALL)
        if match:
            try:
                json_str = match.group(1).strip()
                if json_str.endswith(','):
                    json_str = json_str[:-1]
                config = json.loads(json_str)
                m3u8_url = config.get('url', '')
            except:
                pass

        if not m3u8_url:
            m3u8_url = self._js_decode(html)

        if not m3u8_url:
            m3u8_url = self._sniff_xhr(html, play_url)

        if not m3u8_url:
            return {"parse": 1, "url": play_url}

        m3u8_url = unquote(m3u8_url)
        if m3u8_url.startswith('//'):
            m3u8_url = 'https:' + m3u8_url
        elif not m3u8_url.startswith('http'):
            m3u8_url = urljoin(self.host, m3u8_url)

        return {
            "parse": 0,
            "playUrl": "",
            "url": m3u8_url,
            "header": {
                "User-Agent": self.session.headers['User-Agent'],
                "Referer": play_url,
                "Origin": self.host
            }
        }