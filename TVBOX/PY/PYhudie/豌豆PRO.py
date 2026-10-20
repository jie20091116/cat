# coding: utf-8
# 豌豆PRO https://s2ykfzb.cn - FongMi/TVBox Spider
# HTML站：本地分类筛选、多线路详情、播放页直链优先解析
import re
import json
from urllib.parse import quote, unquote, urljoin

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
except Exception:
    BeautifulSoup = None
    NavigableString = str
    Tag = object

from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def __init__(self):
        self.host = 'https://s2ykfzb.cn'
        self.extend = ''
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': self.host + '/'
        }
        self.classes = [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '电视剧'},
            {'type_id': '3', 'type_name': '综艺'},
            {'type_id': '4', 'type_name': '动漫'},
            {'type_id': '9', 'type_name': '短视频'},
            {'type_id': '51', 'type_name': '即将上映'},
        ]
        self.type_filters = {
            '1': [('全部', '1'), ('喜剧片', '35'), ('动作片', '36'), ('爱情片', '37'), ('科幻片', '38'), ('恐怖片', '39'), ('剧情片', '40'), ('战争片', '41')],
            '2': [('全部', '2'), ('国产剧', '42'), ('港台剧', '43'), ('日韩剧', '44'), ('欧美剧', '45')],
            '3': [('全部', '3')],
            '4': [('全部', '4')],
            '9': [('全部', '9')],
            '51': [('全部', '51')],
        }
        self.years = ['2026', '2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017', '2016']
        self.letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        self.filters = self._make_filters()

    def getName(self):
        return '豌豆PRO'

    def getDependence(self):
        return []

    def init(self, extend=''):
        self.extend = extend or ''

    def homeContent(self, filter):
        return {'class': self.classes, 'filters': self.filters if filter else {}}

    def getHomeContent(self, filter):
        return self.homeContent(filter)

    def homeVideoContent(self):
        html = self._get_html(self.host + '/')
        return {'list': self._parse_list(html)[:36]}

    def categoryContent(self, tid, pg, filter, extend):
        page = self._safe_int(pg, 1)
        url = self._build_category_url(str(tid), page, extend or {})
        html = self._get_html(url)
        if self._is_no_result(html):
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 24, 'total': 0}
        videos = self._parse_list(html)
        pagecount = self._parse_pagecount(html)
        return {
            'list': videos,
            'page': page,
            'pagecount': pagecount,
            'limit': len(videos) if videos else 24,
            'total': pagecount * (len(videos) if videos else 24)
        }

    def detailContent(self, ids):
        raw = str(ids[0]) if isinstance(ids, list) and ids else str(ids)
        vod_id = self._real_id(raw)
        html = self._get_html(self.host + '/sykfgg/%s.html' % vod_id)
        soup = self._soup(html)
        vod = {
            'vod_id': vod_id,
            'vod_name': self._detail_title(soup, html),
            'vod_pic': self._detail_pic(soup),
            'type_name': self._extract_info(soup, '类型'),
            'vod_year': self._extract_year(soup, html),
            'vod_area': self._extract_info(soup, '地区'),
            'vod_remarks': self._extract_remark(soup),
            'vod_actor': self._extract_people(soup, ['main-actors2', 'actors5'], ['主演：', '主演', '演员：', '演员']),
            'vod_director': self._extract_people(soup, ['director1'], ['导演：', '导演']),
            'vod_content': self._extract_content(soup, html),
            'vod_play_from': '',
            'vod_play_url': ''
        }
        play_from, play_url = self._parse_play_sources(soup, html)
        vod['vod_play_from'] = '$$$'.join(play_from)
        vod['vod_play_url'] = '$$$'.join(play_url)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg='1'):
        page = self._safe_int(pg, 1)
        kw = quote(key or '')
        # 站内搜索表单是 GET: /search/-------------.html?wd=xxx
        # 不能用 /search/关键词------------.html，否则会落到伪详情/推荐页，出现货不对板。
        url = self.host + '/search/-------------.html?wd=%s' % kw
        if page > 1:
            url += '&page=%s' % page
        html = self._get_html(url)
        if self._is_no_result(html):
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 20, 'total': 0}
        videos = self._parse_search_list(html, key or '')
        pagecount = self._parse_pagecount(html)
        return {'list': videos, 'page': page, 'pagecount': pagecount, 'limit': len(videos) if videos else 20, 'total': pagecount * (len(videos) if videos else 20)}

    def playerContent(self, flag, id, vipFlags):
        play_url = unquote(id or '')
        if not play_url:
            return {'parse': 0, 'url': ''}
        if self.isVideoFormat(play_url):
            return {'parse': 0, 'url': play_url, 'header': self.headers}
        final_url, ref = self._resolve_play_url(play_url)
        if final_url:
            return {'parse': 0, 'url': final_url, 'header': self._media_headers(ref)}
        return {'parse': 1, 'url': play_url, 'header': self.headers}

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|m4v|mov)(\?|$)', url or '', re.I))

    def manualVideoCheck(self):
        return True

    def liveContent(self, url):
        return ''

    def localProxy(self, param):
        return [404, 'text/plain', 'not found']

    def action(self, action):
        return None

    def destroy(self):
        pass

    def _make_filters(self):
        data = {}
        for tid in [x['type_id'] for x in self.classes]:
            vals = [{'n': n, 'v': v} for n, v in self.type_filters.get(tid, [('全部', tid)])]
            years = [{'n': '全部', 'v': ''}] + [{'n': y, 'v': y} for y in self.years]
            letters = [{'n': '全部', 'v': ''}] + [{'n': c, 'v': c} for c in self.letters]
            data[tid] = [
                {'key': 'class', 'name': '类型', 'value': vals},
                {'key': 'year', 'name': '年份', 'value': years},
                {'key': 'letter', 'name': '字母', 'value': letters},
            ]
        return data

    def _fetch_text(self, url, headers=None):
        res = self.fetch(url, headers=headers or self.headers, timeout=10)
        try:
            return res.text
        except Exception:
            try:
                return res.content.decode('utf-8', errors='ignore')
            except Exception:
                return ''

    def _get_html(self, url):
        try:
            return self._fetch_text(url)
        except Exception as e:
            self._log({'action': 'fetch_fail', 'url': url, 'error': str(e)})
            return ''

    def _soup(self, html):
        if not BeautifulSoup:
            return None
        return BeautifulSoup(html or '', 'html.parser')

    def _log(self, data):
        try:
            self.log(data)
        except Exception:
            pass

    def _abs(self, url, base=None):
        if not url:
            return ''
        url = url.strip()
        if url.startswith('//'):
            return 'https:' + url
        return urljoin(base or self.host, url)

    def _clean(self, text):
        if not text:
            return ''
        text = re.sub(r'[\r\n\t]+', ' ', str(text))
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    def _safe_int(self, val, default=1):
        try:
            return int(val)
        except Exception:
            return default

    def _real_id(self, raw):
        m = re.search(r'(\d+)', raw or '')
        return m.group(1) if m else raw

    def _build_category_url(self, tid, page, extend):
        if isinstance(extend, str):
            try:
                extend = json.loads(extend)
            except Exception:
                extend = {}
        cls = str(extend.get('class') or extend.get('type') or tid)
        year = str(extend.get('year') or '')
        letter = str(extend.get('letter') or '')
        raw = str(extend.get('raw') or '')
        if raw:
            if page > 1:
                m = re.search(r'/sykfggshow/(\d+)', raw)
                cid = m.group(1) if m else cls
                return self.host + '/sykfggtype/%s-%s.html' % (cid, page)
            return self._abs(raw)
        if page > 1:
            return self.host + '/sykfggtype/%s-%s.html' % (cls, page)
        if letter:
            return self.host + '/sykfggshow/%s-----%s------.html' % (cls, letter)
        if year:
            return self.host + '/sykfggshow/%s----%s-------.html' % (cls, year)
        if cls != tid:
            return self.host + '/sykfggshow/%s-----------.html' % cls
        return self.host + '/sykfggtype/%s.html' % tid

    def _is_no_result(self, html):
        return bool(re.search(r'没有找到您想要的结果|没有找到.*?结果|搜索无结果|暂无数据', html or '', re.S))

    def _parse_list(self, html):
        soup = self._soup(html)
        if not soup:
            return []
        out, seen = [], set()
        for a in soup.find_all('a', href=re.compile(r'/sykfgg/\d+\.html')):
            try:
                href = a.get('href') or ''
                m = re.search(r'/sykfgg/(\d+)\.html', href)
                if not m:
                    continue
                vid = m.group(1)
                if vid in seen:
                    continue
                img = a.find('img')
                name, pic = '', ''
                if img:
                    name = img.get('alt') or ''
                    pic = img.get('data-src') or img.get('src') or ''
                if not name:
                    nt = a.find(class_=re.compile(r'ys-name|actor-name|name|title'))
                    name = nt.get_text(' ', strip=True) if nt else ''
                remark = ''
                rt = a.find(class_=re.compile(r'role|remark|last|num|score'))
                if rt:
                    remark = rt.get_text(' ', strip=True)
                name = self._clean(name)
                if not name or name.lower() == 'cover':
                    continue
                seen.add(vid)
                out.append({'vod_id': vid, 'vod_name': name, 'vod_pic': self._abs(pic), 'vod_remarks': self._clean(remark)})
            except Exception as e:
                self._log({'action': 'parse_list_item_fail', 'error': str(e)})
        return out

    def _parse_search_list(self, html, key):
        soup = self._soup(html)
        if not soup:
            return []
        box = None
        hot = soup.find(class_=re.compile(r'hot-class'))
        if hot:
            p = hot
            for _ in range(8):
                p = p.find_next_sibling() if p else None
                if not p:
                    break
                title = p.get_text(' ', strip=True)[:30]
                if '热门推荐' in title:
                    break
                cls = ' '.join(p.get('class') or []) if hasattr(p, 'get') else ''
                # 搜索结果区即使为空也要使用，不能继续串到下面热门推荐。
                if 'list-component6' in cls or p.find(class_=re.compile(r'ysList6')):
                    box = p
                    break
        if not box:
            box = soup.find(class_=re.compile(r'ysList6|list-component6'))
        if not box:
            return []
        videos = self._parse_list(str(box))
        nk = self._norm_key(key)
        if nk:
            strict = [v for v in videos if nk in self._norm_key(v.get('vod_name', ''))]
            if strict:
                return strict
        return videos

    def _norm_key(self, text):
        text = self._clean(text).lower()
        return re.sub(r'[\s\-—_\[\]【】()（）:：·,，.。]+', '', text)

    def _parse_pagecount(self, html):
        patterns = [
            r'class=["\']total["\'][^>]*>\s*(\d+)\s*<',
            r'<span[^>]+class=["\']now["\'][^>]*>\s*\d+\s*</span>\s*/\s*<span[^>]+class=["\']total["\'][^>]*>\s*(\d+)',
            r'/sykfggtype/\d+-(\d+)\.html[^>]*>\s*<div>\s*尾页',
            r'共\s*(\d+)\s*页'
        ]
        for p in patterns:
            m = re.search(p, html or '', re.S)
            if m:
                return self._safe_int(m.group(1), 1)
        return 1

    def _detail_title(self, soup, html):
        if soup:
            for cls in [r'ys-name18|ys-name21', r'title|name']:
                t = soup.find(class_=re.compile(cls))
                if t:
                    return self._clean(t.get_text(' ', strip=True))
            h1 = soup.find('h1')
            if h1:
                return self._clean(h1.get_text(' ', strip=True))
            mt = soup.find('meta', attrs={'name': 'keywords'})
            if mt:
                return self._clean((mt.get('content') or '').split('完整版')[0].split('在线')[0])
        m = re.search(r'<title>《?([^《》<]+)》?', html or '')
        return self._clean(m.group(1)) if m else ''

    def _detail_pic(self, soup):
        if not soup:
            return ''
        img = soup.select_one('.poster5 img') or soup.find('img', attrs={'data-src': re.compile(r'upload/vod|cover|pic')}) or soup.find('img')
        return self._abs((img.get('data-src') or img.get('src') or '') if img else '')

    def _extract_people(self, soup, class_names, labels):
        if not soup:
            return ''
        for cls in class_names:
            tag = soup.find(class_=re.compile(cls))
            if not tag:
                continue
            # 主演/导演块里有“更多...”展开按钮，不能当演员名；优先只取 a 标签人名。
            names = []
            for a in tag.find_all('a'):
                name = self._clean(a.get_text(' ', strip=True).replace('\xa0', ' '))
                if name and not re.search(r'更多|展开|收起', name):
                    names.append(name)
            if names:
                return self._clean(' '.join(names))
            text = tag.get_text(' ', strip=True)
            for lab in labels:
                text = text.replace(lab, '')
            text = re.sub(r'更多\s*\.*|展开|收起', '', text)
            return self._clean(text)
        return ''

    def _extract_info(self, soup, label):
        if not soup:
            return ''
        nodes = soup.find_all(string=re.compile(label))
        for node in nodes:
            p = getattr(node, 'parent', None)
            if not p:
                continue
            text = p.get_text(' ', strip=True)
            if label in text and len(text) < 80:
                text = text.replace(label + '：', '').replace(label + ':', '').replace(label, '')
                return self._clean(text)
        return ''

    def _extract_year(self, soup, html):
        if soup:
            tag = soup.find(class_=re.compile(r'year1|update-time'))
            if tag:
                m = re.search(r'(19|20)\d{2}', tag.get_text(' ', strip=True))
                if m:
                    return m.group(0)
        m = re.search(r'(19|20)\d{2}', html or '')
        return m.group(0) if m else ''

    def _extract_remark(self, soup):
        if not soup:
            return ''
        tag = soup.find(class_=re.compile(r'role|remark|last|update'))
        return self._clean(tag.get_text(' ', strip=True)) if tag else ''

    def _extract_content(self, soup, html):
        if soup:
            tag = soup.find(class_=re.compile(r'Synopsis-word')) or soup.find(class_=re.compile(r'vod-descri'))
            if tag:
                # 该站简介里常混入图片、相关搜索、网友评论；用整块文本切割，比只取首个子节点更完整。
                text = tag.get_text(' ', strip=True)
                text = re.split(r'(?:[\u4e00-\u9fa5A-Za-z0-9]{0,12})网友评论|影院网友|电影网网友|热门', text)[0]
                text = re.split(r'相关搜索[:：]?', text)[0]
                text = re.sub(r'\s+', ' ', text)
                text = self._clean(text)
                if text:
                    return text
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta:
                text = meta.get('content') or ''
                text = re.sub(r'^.*?剧情介绍[:：]', '', text)
                return self._clean(text.replace('...', ''))
        return ''
    def _parse_play_sources(self, soup, html):
        play_from, play_urls = [], []
        if soup:
            # 详情页真实结构是：list-name23(name17=线路名) 后面紧跟 list-number1(该线路剧集)。
            # 注意该站 sid 与显示线路名不一定一致，例如 sid=1 页面标题/详情显示“线路2”，不能按 sid 排序硬改名。
            title_blocks = soup.find_all('div', class_=re.compile(r'list-name23'))
            for title_block in title_blocks:
                title_tag = title_block.find('div', class_=re.compile(r'name17'))
                if not title_tag:
                    continue
                source_name = self._clean(title_tag.get_text(' ', strip=True))
                if not source_name or re.search(r'演员表|剧情介绍|相关推荐|热门推荐|友情链接|网站地图', source_name):
                    continue

                block = None
                probe = title_block
                for _ in range(8):
                    probe = probe.find_next_sibling() if probe else None
                    if not probe:
                        break
                    # 遇到下一个标题块说明当前线路没有剧集，停止，避免串到下一组。
                    cls = ' '.join(probe.get('class') or []) if hasattr(probe, 'get') else ''
                    if 'list-name23' in cls:
                        break
                    if probe.find('a', href=re.compile(r'/sykfggplay/\d+-\d+-\d+\.html')):
                        block = probe
                        break
                if not block:
                    continue

                eps, seen = [], set()
                for a in block.find_all('a', href=re.compile(r'/sykfggplay/\d+-\d+-\d+\.html')):
                    href = a.get('href') or ''
                    full = self._abs(href)
                    if full in seen:
                        continue
                    seen.add(full)
                    name = self._clean(a.get_text(' ', strip=True))
                    if not name:
                        mm = re.search(r'-(\d+)\.html', href)
                        name = '第%s集' % mm.group(1) if mm else '播放'
                    eps.append('%s$%s' % (name, full))
                if eps:
                    play_from.append(source_name)
                    play_urls.append('#'.join(eps))
        if play_from:
            return play_from, play_urls


        links = re.findall(r'/sykfggplay/(\d+)-(\d+)-(\d+)\.html', html or '')
        source_map = {}
        for vid, sid, nid in links:
            source_map.setdefault(sid, set()).add((self._safe_int(nid, 1), '/sykfggplay/%s-%s-%s.html' % (vid, sid, nid)))
        for sid in sorted(source_map.keys(), key=lambda x: self._safe_int(x, 999)):
            eps = []
            for nid, href in sorted(list(source_map[sid]), key=lambda x: x[0]):
                eps.append('第%s集$%s' % (nid, self._abs(href)))
            if eps:
                play_from.append('线路%s' % sid)
                play_urls.append('#'.join(eps))
        return play_from, play_urls

    def _resolve_play_url(self, play_url):
        url = self._abs(play_url)
        html = self._get_html(url)
        candidates = []
        m = re.search(r'player_aaaa\s*=\s*({.*?})\s*</script>', html or '', re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                pu = unquote(data.get('url') or '')
                if pu:
                    candidates.append(pu)
            except Exception as e:
                self._log({'action': 'player_json_fail', 'error': str(e)})
        for p in [
            r'["\']url["\']\s*:\s*["\']([^"\']+)["\']',
            r'MacPlayer\.PlayUrl\s*=\s*["\']([^"\']+)["\']',
            r'now\s*=\s*["\']([^"\']+)["\']',
            r'(https?://[^\s"\'<>]+?\.(?:m3u8|mp4)[^\s"\'<>]*)'
        ]:
            for x in re.findall(p, html or '', re.S):
                if x and x not in candidates:
                    candidates.append(unquote(x))
        for c in candidates:
            c = self._abs(c, url)
            if self.isVideoFormat(c):
                return c, url
            if re.search(r'(player|jx|api\.php|share|url=)', c, re.I):
                final = self._resolve_second(c)
                if final:
                    return final, c
        return '', url

    def _resolve_second(self, url):
        html = self._get_html(url)
        for p in [
            r'var\s+main\s*=\s*["\']([^"\']+)["\']',
            r'["\'](?:url|video|src)["\']\s*:\s*["\']([^"\']+)["\']',
            r'(https?://[^\s"\'<>]+?\.(?:m3u8|mp4)[^\s"\'<>]*)'
        ]:
            for x in re.findall(p, html or '', re.S):
                x = unquote(x)
                full = self._abs(x, url)
                if self.isVideoFormat(full):
                    return full
        return ''

    def _media_headers(self, referer):
        h = dict(self.headers)
        if referer:
            h['Referer'] = referer
        return h