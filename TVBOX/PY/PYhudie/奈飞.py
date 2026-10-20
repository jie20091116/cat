# -*- coding: utf-8 -*-
"""
奈飞影视 - naifei.im TVBox爬虫
修复：搜索分页、403跳转、图片兼容、播放解析容错、依赖延迟加载、缓存、反爬延迟
"""
import re
import json
import sys
import time
from urllib.parse import quote, urljoin
from base.spider import Spider

# 全局依赖预加载捕获
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"缺失依赖库: {e}, 请安装 requests beautifulsoup4")
    sys.exit(1)


class Spider(Spider):
    def __init__(self):
        super(Spider, self).__init__()
        self.host = "https://naifei.im"
        self.name = "奈飞影视"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': self.host
        }
        self.categories = {
            '1': '电影',
            '2': '剧集',
            '3': '综艺',
            '4': '动漫',
            '5': '短剧'
        }
        # 详情缓存：key=vid, value=(data, 时间戳) 10分钟过期
        self._detail_cache = {}
        self.cache_expire = 600

    def getName(self):
        return self.name

    def init(self, extend=""):
        pass

    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "5", "type_name": "短剧"},
        ]
        return {'class': classes, 'filters': {}, 'list': []}

    def homeVideoContent(self):
        try:
            videos = self._fetch_home()
            return {'list': videos}
        except Exception as e:
            print(f'[{self.name}] 首页爬取失败: {e}')
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg) if pg and str(pg).isdigit() else 1
            videos = self._fetch_category(tid, page)
            return {
                'page': page,
                'pagecount': 9999,
                'limit': 20,
                'total': 99999,
                'list': videos
            }
        except Exception as e:
            print(f'[{self.name}] 分类爬取失败: {e}')
            return {'page': int(pg), 'pagecount': 0, 'limit': 20, 'total': 0, 'list': []}

    def detailContent(self, ids):
        try:
            vod_id = ids[0] if isinstance(ids, list) else ids
            detail = self._fetch_detail(vod_id)
            if detail:
                return {'list': [detail]}
            return {'list': []}
        except Exception as e:
            print(f'[{self.name}] 详情爬取失败: {e}')
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        try:
            play_url = str(id).strip()
            # 分离标题和真实播放链接
            if '$' in play_url:
                _, play_url = play_url.split('$', 1)
            # 页面地址解析真实m3u8
            if play_url and self.host in play_url:
                real_url = self._parse_play_url(play_url)
                if real_url:
                    play_url = real_url
            return {
                'parse': 0,
                'playUrl': '',
                'url': play_url,
            }
        except Exception as e:
            print(f'[{self.name}] 播放解析失败: {e}')
            return {
                'parse': 1,
                'playUrl': '',
                'url': str(id),
            }

    def _parse_play_url(self, url):
        """解析播放页面获取真实m3u8，多重正则容错"""
        html = self._fetch_page(url)
        if not html:
            return None
        # 1. json url字段
        url_match = re.search(r'"url"\s*:\s*"(https?:[^"]+)"', html)
        if url_match:
            video_url = url_match.group(1).replace('\\/', '/')
            if video_url.startswith('http') and ('.m3u8' in video_url or '.mp4' in video_url):
                return video_url
        # 2. 全局匹配m3u8
        m3u8_reg = re.compile(r'https?://[^\'"\s]+?\.m3u8[^\'"\s]*')
        m3u8_list = m3u8_reg.findall(html)
        if m3u8_list:
            return m3u8_list[0].replace('\\/', '/')
        # 3. mp4兜底
        mp4_reg = re.compile(r'https?://[^\'"\s]+?\.mp4[^\'"\s]*')
        mp4_list = mp4_reg.findall(html)
        if mp4_list:
            return mp4_list[0].replace('\\/', '/')
        return None

    def searchContent(self, key, quick, pg="1"):
        """修复搜索分页，原联想接口仅返回20条，新增分页搜索页面"""
        try:
            page = int(pg) if pg and str(pg).isdigit() else 1
            videos = []
            # 第一页优先调用联想接口快速返回
            if page == 1:
                suggest_url = f"{self.host}/index.php/ajax/suggest?mid=1&limit=20&wd={quote(key)}"
                html = self._fetch_page(suggest_url)
                if html:
                    try:
                        data = json.loads(html)
                        if data.get('code') == 1 and data.get('list'):
                            for item in data['list']:
                                vod = self._parse_search_item(item)
                                if vod:
                                    videos.append(vod)
                    except:
                        pass
            # 所有页面通用搜索分页页面（解决多页搜索）
            search_url = f"{self.host}/vodsearch/{quote(key)}-{page}.html"
            html = self._fetch_page(search_url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                items = soup.find_all('a', class_='module-poster-item')
                for item in items:
                    vod = self._parse_video_item(item)
                    if vod and vod['vod_id'] not in [v['vod_id'] for v in videos]:
                        videos.append(vod)
            return {'list': videos}
        except Exception as e:
            print(f'[{self.name}] 搜索失败: {e}')
            return {'list': []}

    def _fetch_page(self, url, retries=2):
        """通用请求封装：反爬延迟、403跳转、编码、超时容错"""
        session = requests.Session()
        session.headers.update(self.headers)
        # 每次请求随机延迟防封禁
        time.sleep(0.3)
        for attempt in range(retries + 1):
            try:
                resp = session.get(url, timeout=15)
                # 403 页面跳转处理
                if resp.status_code == 403 or "window.location.href" in resp.text:
                    redirect_match = re.search(r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', resp.text)
                    if redirect_match:
                        redirect_path = redirect_match.group(1)
                        new_url = urljoin(self.host, redirect_path)
                        resp = session.get(new_url, timeout=15)
                    elif attempt < retries:
                        time.sleep(1.2)
                        # 访问首页刷新cookie
                        session.get(self.host, timeout=8)
                        continue
                resp.raise_for_status()
                # 自动识别编码
                resp.encoding = resp.apparent_encoding
                return resp.text
            except Exception as e:
                if attempt < retries:
                    time.sleep(1)
                    continue
                print(f'[{self.name}] 请求异常 url:{url} err:{str(e)}')
                return ''
        return ''

    def _fetch_home(self):
        """首页数据解析"""
        html = self._fetch_page(self.host)
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        videos = []
        items_containers = soup.find_all('div', class_='module-items')
        for container in items_containers:
            items = container.find_all('a', class_='module-poster-item')
            for item in items[:20]:
                vod = self._parse_video_item(item)
                if vod:
                    videos.append(vod)
        return videos[:50]

    def _fetch_category(self, tid, page=1):
        """分类列表"""
        if page <= 1:
            url = f"{self.host}/vodtype/{tid}.html"
        else:
            url = f"{self.host}/vodtype/{tid}-{page}.html"
        html = self._fetch_page(url)
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        videos = []
        items = soup.find_all('a', class_='module-poster-item')
        for item in items:
            vod = self._parse_video_item(item)
            if vod:
                videos.append(vod)
        return videos

    def _fetch_detail(self, vid):
        """详情页+缓存过期机制"""
        now = time.time()
        # 缓存过期清理
        if vid in self._detail_cache:
            cache_data, cache_time = self._detail_cache[vid]
            if now - cache_time < self.cache_expire:
                return cache_data
            else:
                del self._detail_cache[vid]

        url = f"{self.host}/voddetail/{vid}.html"
        html = self._fetch_page(url)
        if not html:
            return None
        soup = BeautifulSoup(html, 'html.parser')
        result = {"vod_id": vid, "vod_area": "", "vod_actor": "", "vod_director": "", "vod_year": "", "vod_remarks": ""}
        # 标题
        title_tag = soup.find('h1', class_='video-info-heading')
        result['vod_name'] = title_tag.text.strip() if title_tag else ''
        # 封面
        cover_img = soup.find('img', class_='lazy lazyload') or soup.find('img')
        if cover_img:
            pic = cover_img.get('data-original', cover_img.get('src', ''))
            if pic.startswith('//'):
                pic = 'https:' + pic
            result['vod_pic'] = pic
        else:
            result['vod_pic'] = ''
        # 详情信息
        info_items = soup.find_all('li', class_='list-item')
        area_list = []
        for item in info_items:
            text = item.text.strip()
            if '主演' in text and '：' in text:
                result['vod_actor'] = text.split('：')[-1]
            elif '导演' in text and '：' in text:
                result['vod_director'] = text.split('：')[-1]
            elif '地区' in text and '：' in text:
                area_list.append(text.split('：')[-1])
            elif '语言' in text and '：' in text:
                area_list.append(text.split('：')[-1])
            elif '年份' in text and '：' in text:
                result['vod_year'] = text.split('：')[-1]
            elif '更新' in text or '集数' in text:
                result['vod_remarks'] = text.split('：')[-1]
        # 地区语言合并
        result['vod_area'] = '/'.join(area_list)
        # 简介
        desc_tag = soup.find('div', class_='video-info-content')
        result['vod_content'] = desc_tag.text.strip() if desc_tag else '暂无简介'
        # 播放列表
        episodes = []
        play_box = soup.find('div', class_='module-play-list')
        if play_box:
            ep_links = play_box.find_all('a')
            for ep in ep_links:
                ep_name = ep.text.strip()
                ep_href = ep.get('href', '')
                if ep_name and ep_href:
                    full_ep_url = urljoin(self.host, ep_href)
                    episodes.append(f"{ep_name}${full_ep_url}")
        if episodes:
            result['vod_play_from'] = "奈飞线路"
            result['vod_play_url'] = '#'.join(episodes)
        else:
            result['vod_play_from'] = ''
            result['vod_play_url'] = ''
        # 写入缓存
        self._detail_cache[vid] = (result, now)
        return result

    def _parse_search_item(self, item):
        """解析ajax联想搜索结果"""
        try:
            vid = str(item.get('id', ''))
            name = item.get('name', '')
            if not vid or not name:
                return None
            pic = item.get('pic', '')
            if pic.startswith('//'):
                pic = 'https:' + pic
            return {
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': item.get('remarks', '')
            }
        except Exception:
            return None

    def _parse_video_item(self, item):
        """首页/分类页面卡片解析"""
        try:
            link = item.get('href', '')
            title = item.get('title', '未知影片')
            # 图片兼容
            img_tag = item.find('img')
            cover = ''
            if img_tag:
                cover = img_tag.get('data-original', img_tag.get('src', ''))
                if cover.startswith('//'):
                    cover = 'https:' + cover
            # 更新标签
            note_tag = item.find('div', class_='module-item-note')
            remark = note_tag.text.strip() if note_tag else ''
            # 提取vid
            vid_match = re.search(r'/voddetail/(\d+)\.html', link)
            if not vid_match:
                return None
            vid = vid_match.group(1)
            return {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': cover,
                'vod_remarks': remark
            }
        except Exception:
            return None