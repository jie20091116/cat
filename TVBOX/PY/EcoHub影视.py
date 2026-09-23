# coding=utf-8


import re
import json
import sys
import time
import random
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, urljoin

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    # 本地自测兜底：最小化 BaseSpider
    import requests
    from lxml import etree

    class BaseSpider:
        def fetch(self, url, headers=None, timeout=20, verify=False):
            s = requests.Session()
            s.trust_env = False
            return s.get(url, headers=headers, timeout=timeout, verify=verify)

        def html(self, content):
            return etree.HTML(content)

try:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass


class Spider(BaseSpider):
    name = 'EcoHub'
    host = 'https://eco.fe-spark.cn'
    api = 'https://eco.fe-spark.cn/api'

    # 父分类兜底(网络异常时使用, 正常走 /api/index 动态获取)
    CATEGORIES = [
        ('1', '动漫'),
        ('8', '电影'),
        ('26', '连续剧'),
        ('36', '综艺'),
        ('41', '体育'),
        ('43', 'AI漫剧'),
    ]

    # 服务端固定分页大小
    PER_PAGE = 49
    SEARCH_PER_PAGE = 10

    # 筛选器允许透传的查询字段(即 search.sortList 的全集)
    FILTER_KEYS = ('Category', 'Plot', 'Area', 'Language', 'Year', 'Sort')

    # 首页数据缓存时长(秒), 避免 init/homeContent/homeVideoContent 重复打 /api/index
    INDEX_TTL = 300

    _debug = False
    _categories = []
    _filter_cache = {}
    _detail_cache = {}
    _index_cache = None
    _index_ts = 0

    def _log(self, msg):
        if self._debug:
            print(f'[{self.name}] {msg}')

    # ========== TVBox 固定接口 ==========
    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        if not url:
            return False
        url = str(url).lower().split('?')[0]
        return any(url.endswith(fmt) for fmt in
                   ['.m3u8', '.mp4', '.flv', '.ts', '.mkv', '.avi', '.mov', '.wmv'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # ---------- HTTP 工具 ----------
    def _get_headers(self, referer=None):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer or self.host + '/',
            'Origin': self.host,
        }

    def _get_json(self, path, params=None, retries=3, timeout=20):
        """GET /api/xxx 并返回 data 字段(dict/list)，失败返回 None。"""
        url = self.api + path
        if params:
            clean = {k: v for k, v in params.items() if v not in (None, '')}
            if clean:
                url += '?' + urlencode(clean, encoding='utf-8')
        for attempt in range(retries):
            try:
                if attempt > 0:
                    time.sleep(random.uniform(0.5, 1.2))
                r = self.fetch(url, headers=self._get_headers(), timeout=timeout, verify=False)
                if getattr(r, 'status_code', 0) != 200:
                    self._log(f'请求失败 [{getattr(r, "status_code", "?")}] {url}')
                    continue
                text = r.text or ''
                if not text.strip().startswith('{'):
                    # Gin 未命中路由会返回纯文本 "404 page not found"
                    self._log(f'非 JSON 响应 [{url}]: {text[:80]}')
                    continue
                obj = json.loads(text)
                if obj.get('code') not in (0, 200):
                    self._log(f'接口异常 code={obj.get("code")} msg={obj.get("msg")}')
                return obj.get('data')
            except Exception as e:
                self._log(f'请求异常 [{url}]: {e}，重试 {attempt + 1}/{retries}')
                continue
        return None

    def _fix_url(self, url):
        if not url:
            return ''
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return self.host + url
        if not url.startswith('http'):
            return urljoin(self.host + '/', url)
        return url

    @staticmethod
    def _clean(text):
        if not text:
            return ''
        text = re.sub(r'<[^>]+>', ' ', str(text))
        return re.sub(r'\s+', ' ', text).replace('&nbsp;', ' ').strip()

    @staticmethod
    def _line_name(i):
       
        return f'酷鱼{i + 1}线'

    # ---------- 初始化 ----------
    def init(self, extend=''):
        try:
            if extend:
                if isinstance(extend, str):
                    try:
                        extend = json.loads(extend)
                    except Exception:
                        extend = {}
                if isinstance(extend, dict):
                    self._debug = bool(extend.get('debug', False))
        except Exception:
            pass
        self._categories = self._load_categories()
        self._log(f'初始化完成，父分类 {len(self._categories)} 个')

    def _index(self):
        """/api/index 带 TTL 缓存(首页推荐 + 分类树都从这里来)。"""
        now = time.time()
        if self._index_cache is not None and now - self._index_ts < self.INDEX_TTL:
            return self._index_cache
        data = self._get_json('/index')
        if data:
            self._index_cache = data
            self._index_ts = now
        return data or self._index_cache or {}

    def _load_categories(self):
        """从 /api/index 动态取父分类(顺带缓存子分类树)。"""
        data = self._index()
        cats = []
        try:
            for c in ((data or {}).get('category') or {}).get('children') or []:
                if c.get('show') is False:
                    continue
                cats.append({'type_id': str(c.get('id')), 'type_name': self._clean(c.get('name'))})
        except Exception as e:
            self._log(f'分类解析异常: {e}')
        if not cats:
            cats = [{'type_id': k, 'type_name': v} for k, v in self.CATEGORIES]
        return cats

    # ---------- 筛选器(每个父分类下的子分类) ----------
    def _build_filter_groups(self, search):
        """把服务端下发的 search{sortList,tags,titles} 转成 TVBox filters 结构。"""
        groups = []
        try:
            order = (search or {}).get('sortList') or list(self.FILTER_KEYS)
            tags = (search or {}).get('tags') or {}
            titles = (search or {}).get('titles') or {}
            for key in order:
                opts = tags.get(key) or []
                if not opts:
                    continue
                values = []
                for o in opts:
                    n = self._clean(o.get('Name'))
                    v = str(o.get('Value', ''))
                    if not n:
                        continue
                    values.append({'n': n, 'v': v})
                if len(values) <= 1:
                    continue
                groups.append({
                    'key': key,
                    'name': self._clean(titles.get(key) or key),
                    'value': values,
                })
        except Exception as e:
            self._log(f'筛选器解析异常: {e}')
        return groups

    def _fetch_filter(self, tid):
        """拉取单个父分类的筛选器。服务端在列表接口里直接下发 search.sortList/tags/titles。"""
        tid = str(tid)
        if tid in self._filter_cache:
            return self._filter_cache[tid]
        data = self._get_json('/filmClassifySearch', {'Pid': tid})
        groups = self._build_filter_groups((data or {}).get('search'))
        self._filter_cache[tid] = groups
        return groups

    def _filters(self):
        """并发拉取全部父分类的筛选器。"""
        tids = [c['type_id'] for c in (self._categories or
                                       [{'type_id': k} for k, _ in self.CATEGORIES])]
        result = {}
        try:
            with ThreadPoolExecutor(max_workers=6) as pool:
                for tid, groups in zip(tids, pool.map(self._fetch_filter, tids)):
                    if groups:
                        result[tid] = groups
        except Exception as e:
            self._log(f'并发拉取筛选器异常: {e}')
            for tid in tids:
                g = self._fetch_filter(tid)
                if g:
                    result[tid] = g
        return result

    # ========== 卡片解析(列表/首页/搜索通用) ==========
    def _parse_cards(self, arr):
        items, seen = [], set()
        for it in arr or []:
            try:
                vid = it.get('id') or it.get('mid')
                if not vid:
                    continue
                vid = str(vid)
                if vid in seen:
                    continue
                seen.add(vid)
                pic = it.get('picture') or it.get('poster') or it.get('pictureSlide') or ''
                remarks = self._clean(it.get('remarks') or it.get('remark') or it.get('state'))
                year = str(it.get('year') or '')
                # 站点部分老数据 year 字段脏(如 "4463"), 过滤掉非法年份
                if not re.fullmatch(r'(19|20)\d{2}', year):
                    year = ''
                items.append({
                    'vod_id': vid,
                    'vod_name': self._clean(it.get('name')),
                    'vod_pic': self._fix_url(pic),
                    'vod_remarks': remarks,
                    'vod_year': year,
                    'type_name': self._clean(it.get('cName')),
                })
            except Exception:
                continue
        return items

    # ========== 首页 ==========
    def homeContent(self, filter=False):
        try:
            if not self._categories:
                self.init()
            return {
                'class': self._categories,
                'filters': self._filters() if filter else None,
                'list': self._home_list(),
                'parse': 0,
                'jx': 0,
            }
        except Exception as e:
            self._log(f'homeContent 异常: {e}')
            return {'class': self._categories or
                    [{'type_id': k, 'type_name': v} for k, v in self.CATEGORIES],
                    'filters': None, 'list': [], 'parse': 0, 'jx': 0}

    def _home_list(self):
        """首页推荐 = banner(取 mid) + 各分类板块 hot/movies 合并去重。"""
        data = self._index() or {}
        arr = []
        for b in data.get('banners') or []:
            arr.append({
                'id': b.get('mid') or b.get('id'),
                'name': b.get('name'),
                'picture': b.get('picture') or b.get('poster'),
                'remarks': b.get('remark'),
                'cName': b.get('cName'),
                'year': b.get('year'),
            })
        for block in data.get('content') or []:
            arr.extend(block.get('hot') or [])
            arr.extend(block.get('movies') or [])
        return self._parse_cards(arr)

    def homeVideoContent(self):
        try:
            return {'list': self._home_list(), 'parse': 0, 'jx': 0}
        except Exception as e:
            self._log(f'homeVideoContent 异常: {e}')
            return {'list': [], 'parse': 0, 'jx': 0}

    # ========== 分类 / 子分类筛选 / 分页 ==========
    def categoryContent(self, tid, pg, flt=False, extend=''):
        page = 1
        try:
            page = int(pg) if pg else 1
        except Exception:
            page = 1
        try:
            params = {'Pid': str(tid), 'current': page}
            if extend:
                if isinstance(extend, str):
                    try:
                        extend = json.loads(extend)
                    except Exception:
                        extend = {}
                if isinstance(extend, dict):
                    for k, v in extend.items():
                        if v in (None, ''):
                            continue
                        # 兼容小写/别名写法
                        key = k if k in self.FILTER_KEYS else k.capitalize()
                        if key in self.FILTER_KEYS:
                            params[key] = str(v)

            self._log(f'category params={params}')
            data = self._get_json('/filmClassifySearch', params) or {}
            items = self._parse_cards(data.get('list'))
            pinfo = data.get('page') or {}
            pagecount = int(pinfo.get('pageCount') or 0) or max(page, 1)
            total = int(pinfo.get('total') or (pagecount * self.PER_PAGE))
            limit = int(pinfo.get('pageSize') or self.PER_PAGE)

            # 顺带缓存该分类的筛选器: 列表接口本身就带 search 字段, 省掉一次请求
            if str(tid) not in self._filter_cache and data.get('search'):
                self._filter_cache[str(tid)] = self._build_filter_groups(data.get('search'))

            return {
                'list': items,
                'page': page,
                'pagecount': pagecount,
                'limit': limit,
                'total': total,
                'parse': 0,
                'jx': 0,
            }
        except Exception as e:
            self._log(f'categoryContent 异常: {e}')
            return {'list': [], 'page': page, 'pagecount': 1,
                    'limit': self.PER_PAGE, 'total': 0, 'parse': 0, 'jx': 0}

    # ========== 详情 ==========
    def detailContent(self, ids):
        vod_id = ''
        try:
            vod_id = str(ids[0] if isinstance(ids, (list, tuple)) else ids)
            vod_id = re.sub(r'\D', '', vod_id) or vod_id
            detail = self._fetch_detail(vod_id)
            if not detail:
                return {'list': [{'vod_id': vod_id, 'vod_name': '获取失败',
                                  'vod_play_from': '默认', 'vod_play_url': ''}],
                        'parse': 0, 'jx': 0}
            return {'list': [self._build_detail(vod_id, detail)], 'parse': 0, 'jx': 0}
        except Exception as e:
            self._log(f'detailContent 异常: {e}')
            return {'list': [{'vod_id': vod_id or str(ids), 'vod_name': '错误',
                              'vod_play_from': '默认', 'vod_play_url': ''}],
                    'parse': 0, 'jx': 0}

    def _fetch_detail(self, vod_id):
        """取全量播放源。优先解析 /play 页 RSC flight(detail.list 含 8 路集合源),
        失败回退 /api/filmPlayInfo(仅 1 路原生源)。返回 detail dict 或 None。"""
        vod_id = str(vod_id)
        if vod_id in self._detail_cache:
            return self._detail_cache[vod_id]
        detail = None
        # 1) 主来源: /play 页面 RSC flight
        detail = self._parse_play_flight(vod_id)
        if detail and (detail.get('list') or detail.get('playList')):
            self._detail_cache[vod_id] = detail
            return detail
        # 2) 回退: JSON API(只有 detail.playFrom/playList 1 路原生源)
        data = self._get_json('/filmPlayInfo', {'id': vod_id}) or {}
        detail = data.get('detail') or {}
        self._detail_cache[vod_id] = detail
        return detail or None

    def _parse_play_flight(self, vod_id):
        """抓取 /play?id= 页面, 从 RSC flight 段提取 data.detail(含 list 8 路源)。"""
        url = self.host + '/play?id=' + str(vod_id)
        try:
            r = self.fetch(url, headers=self._get_headers(referer=self.host + '/'),
                           timeout=25, verify=False)
            if getattr(r, 'status_code', 0) != 200:
                self._log(f'RSC 请求失败 [{getattr(r, "status_code", "?")}] {url}')
                return None
            return self._extract_detail_from_html(r.text or '')
        except Exception as e:
            self._log(f'RSC 解析异常: {e}')
            return None

    def _extract_detail_from_html(self, html):
        """从 Next.js RSC flight 提取 detail。结构:
        self.__next_f.push([1,"6:[[\"$\",\"$L16\",\"<id>\",{\"data\":{\"detail\":{...list:[8源]...}}}]])"""
        segs = re.findall(r'self\.__next_f\.push\(\[1,\s*(\"(?:[^\"\\]|\\.)*\")', html or '')
        for s in segs:
            try:
                node = json.loads(s)
            except Exception:
                continue
            if not isinstance(node, str) or not node.startswith('6:'):
                continue
            try:
                inner = json.loads(node[2:])
                # inner = [["$","$L16","<id>",{"data":{...,"detail":{...}}}]]
                cand = inner[0][3]
                data = cand.get('data') if isinstance(cand, dict) else None
                detail = (data or {}).get('detail') or {}
            except Exception:
                continue
            if detail and (detail.get('list') or detail.get('playList')):
                return detail
        return None

    def _build_detail(self, vod_id, detail):
        d = detail.get('descriptor') or {}
        play_from, play_url = [], []
        
        sources = detail.get('list') or []
        if not sources:
            froms = detail.get('playFrom') or []
            lists = detail.get('playList') or []
            for i, eps in enumerate(lists):
                name = froms[i] if i < len(froms) else f'线路{i + 1}'
                sources.append({'name': name, 'linkList': eps})
        for src in sources:
            link_list = src.get('linkList') or []
            if not link_list:
                continue
            
            name = self._line_name(len(play_from))
            segs = []
            for idx, ep in enumerate(link_list):
                ep_name = self._clean(ep.get('episode')) or f'第{idx + 1:02d}集'
                link = (ep.get('link') or '').strip()
                if not link:
                    continue
                # $ 和 # 是 TVBox 分隔符, 需转义防止串集
                ep_name = ep_name.replace('$', ' ').replace('#', ' ')
                segs.append(f'{ep_name}${link}')
            if segs:
                play_from.append(name)
                play_url.append('#'.join(segs))
        if not play_from:
            play_from.append('默认')
            play_url.append('')

        year = str(d.get('year') or '')
        if not re.fullmatch(r'(19|20)\d{2}', year):
            year = ''
        score = str(d.get('dbScore') or '')
        remarks = self._clean(d.get('remarks') or d.get('state'))
        if score and score not in ('0.0', '0'):
            remarks = f'{remarks} 豆瓣{score}'.strip()

        content = self._clean(d.get('content') or d.get('blurb'))
        return {
            'vod_id': str(vod_id),
            'vod_name': self._clean(detail.get('name')) or '未知',
            'vod_pic': self._fix_url(detail.get('picture') or detail.get('pictureSlide') or ''),
            'vod_actor': self._clean(d.get('actor')),
            'vod_director': self._clean(d.get('director')),
            'vod_year': year,
            'vod_area': self._clean(d.get('area')),
            'vod_lang': self._clean(d.get('language')),
            'type_name': self._clean(d.get('classTag') or d.get('cName')),
            'vod_remarks': remarks,
            'vod_content': content,
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url),
        }

    # ========== 播放 ==========
    def playerContent(self, flag, pid, vipFlags=None):
        try:
            pid = str(pid or '').strip()
            play_header = json.dumps({
                'User-Agent': self._get_headers()['User-Agent'],
                'Referer': self.host + '/',
            })

            # 站点下发的就是 m3u8 直链, 直接播
            if pid.startswith('http'):
                parse_flag = 0 if self.isVideoFormat(pid) else 1
                return {'parse': parse_flag, 'playUrl': '', 'url': pid,
                        'header': play_header, 'jx': 0}

            # 兜底: 传进来的是影片 id / "id-集号", 回查一次取直链
            m = re.match(r'^(\d+)(?:[-_](\d+))?$', pid)
            if m:
                vid, epi = m.group(1), int(m.group(2) or 0)
                detail = self._fetch_detail(vid)
                if detail:
                    sources = detail.get('list') or []
                    if not sources:
                        froms = detail.get('playFrom') or []
                        lists = detail.get('playList') or []
                        sources = [{'name': self._line_name(i),
                                    'linkList': eps} for i, eps in enumerate(lists)]
                    # 优先按线路名(flag)匹配, 否则取第一个足够长的源
                    for src in sources:
                        sname = self._clean(src.get('name')) or ''
                        if flag and sname and flag not in sname and sname not in flag:
                            continue
                        eps = src.get('linkList') or []
                        if len(eps) > epi:
                            link = (eps[epi] or {}).get('link') or ''
                            if link:
                                return {'parse': 0 if self.isVideoFormat(link) else 1,
                                        'playUrl': '', 'url': link,
                                        'header': play_header, 'jx': 0}
                    for src in sources:
                        eps = src.get('linkList') or []
                        if len(eps) > epi:
                            link = (eps[epi] or {}).get('link') or ''
                            if link:
                                return {'parse': 0 if self.isVideoFormat(link) else 1,
                                        'playUrl': '', 'url': link,
                                        'header': play_header, 'jx': 0}

            return {'parse': 1, 'playUrl': '', 'url': self._fix_url(pid),
                    'header': play_header, 'jx': 0}
        except Exception as e:
            self._log(f'playerContent 异常: {e}')
            return {'parse': 0, 'playUrl': '', 'url': '', 'header': '', 'jx': 0}

    # ========== 搜索 ==========
    def searchContent(self, key, quick, pg='1'):
        page = 1
        try:
            page = int(pg) if pg else 1
        except Exception:
            page = 1
        try:
            # 后端只认 keyword, 传 search/wd/q 都会被忽略并返回全库数据
            data = self._get_json('/searchFilm', {'keyword': key, 'current': page}) or {}
            items = self._parse_cards(data.get('list'))
            pinfo = data.get('page') or {}
            pagecount = int(pinfo.get('pageCount') or 0) or max(page, 1)
            total = int(pinfo.get('total') or len(items))
            limit = int(pinfo.get('pageSize') or self.SEARCH_PER_PAGE)
            self._log(f'search [{key}] page={page} -> {len(items)} 条 / 共 {total}')
            return {
                'list': items,
                'page': page,
                'pagecount': pagecount,
                'limit': limit,
                'total': total,
                'parse': 0,
                'jx': 0,
            }
        except Exception as e:
            self._log(f'searchContent 异常: {e}')
            return {'list': [], 'page': page, 'pagecount': 1,
                    'limit': self.SEARCH_PER_PAGE, 'total': 0, 'parse': 0, 'jx': 0}

    def searchContentPage(self, key, quick, page):
        return self.searchContent(key, quick, page)

    # ---------- 本地代理(封面防盗链兜底) ----------
    def localProxy(self, param):
        if not param or not str(param).startswith('http'):
            return None
        try:
            r = self.fetch(param, headers={
                'User-Agent': self._get_headers()['User-Agent'],
                'Referer': self.host + '/',
            }, timeout=(10, 15), verify=False)
            ct = r.headers.get('Content-Type', 'application/octet-stream')
            return [200, ct, r.content]
        except Exception:
            return None


if __name__ == '__main__':
    sp = Spider()
    sp._debug = True
    sp.init()

    print('\n=== 首页 / 分类 ===')
    home = sp.homeContent(True)
    print(f'父分类: {len(home.get("class", []))} 个 -> {home.get("class")}')
    print(f'首页推荐: {len(home.get("list", []))} 个')
    for v in home.get('list', [])[:3]:
        print(f'  {v["vod_name"]} (id={v["vod_id"]}) {v.get("type_name")} '
              f'{v.get("vod_remarks")} pic={v["vod_pic"][:58]}')

    print('\n=== 子分类筛选器(每个父分类) ===')
    for tid, groups in (home.get('filters') or {}).items():
        nm = next((c['type_name'] for c in home['class'] if c['type_id'] == tid), tid)
        print(f'  [{tid}] {nm}: ' + ' | '.join(
            f'{g["name"]}({len(g["value"])})' for g in groups))
    ani = (home.get('filters') or {}).get('1') or []
    for g in ani:
        if g['key'] == 'Category':
            print(f'  动漫-子分类: {[v["n"] for v in g["value"]]}')

    print('\n=== 分类: 动漫 第1页 ===')
    cat = sp.categoryContent('1', '1', True)
    print(f'结果 {len(cat.get("list", []))} 个, pagecount={cat.get("pagecount")}, total={cat.get("total")}')
    for v in cat.get('list', [])[:3]:
        print(f'  {v["vod_name"]} (id={v["vod_id"]}) {v.get("type_name")} {v.get("vod_remarks")}')

    print('\n=== 分类+子分类筛选: 动漫/国产动漫 + 2026年 + 人气排序 ===')
    cat2 = sp.categoryContent('1', '1', True, json.dumps(
        {'Category': '2', 'Year': '2026', 'Sort': 'hits'}))
    print(f'结果 {len(cat2.get("list", []))} 个, total={cat2.get("total")}')
    for v in cat2.get('list', [])[:5]:
        print(f'  {v["vod_name"]} (id={v["vod_id"]}) {v.get("type_name")} {v.get("vod_year")}')

    print('\n=== 分类分页: 动漫 第2页 ===')
    cat3 = sp.categoryContent('1', '2', False)
    a = set(x['vod_id'] for x in cat.get('list', []))
    b = set(x['vod_id'] for x in cat3.get('list', []))
    print(f'结果 {len(cat3.get("list", []))} 个, 与第1页不重复: {len(b - a)}/{len(b)}')

    print('\n=== 详情 ===')
    first = (cat.get('list') or [{'vod_id': '87207'}])[0]
    det = sp.detailContent([first['vod_id']])
    d = (det.get('list') or [{}])[0]
    print(f'  名称: {d.get("vod_name")}   年份: {d.get("vod_year")}  地区: {d.get("vod_area")}  语言: {d.get("vod_lang")}')
    print(f'  封面: {(d.get("vod_pic") or "")[:70]}')
    print(f'  主演: {(d.get("vod_actor") or "")[:50]}   导演: {(d.get("vod_director") or "")[:30]}')
    print(f'  类型: {d.get("type_name")}   状态: {d.get("vod_remarks")}')
    print(f'  简介: {(d.get("vod_content") or "")[:60]}')
    print(f'  线路: {d.get("vod_play_from")}')
    print(f'  选集数: {[len(u.split("#")) for u in (d.get("vod_play_url") or "").split("$$$")]}')
    print(f'  播放URL样例: {(d.get("vod_play_url") or "")[:110]}')

    print('\n=== 播放: 逐线路验证 ===')
    froms = (d.get('vod_play_from') or '').split('$$$')
    urls = (d.get('vod_play_url') or '').split('$$$')
    ok = 0
    for i, fu in enumerate(urls):
        if not fu:
            continue
        line_name = froms[i] if i < len(froms) else f'线路{i + 1}'
        ep_name, ep_url = fu.split('#')[0].split('$', 1)
        pl = sp.playerContent(line_name, ep_url)
        good = pl.get('parse') == 0 and pl.get('url')
        ok += 1 if good else 0
        print(f'  [{line_name}] {ep_name} -> {"OK" if good else "FAIL"} '
              f'parse={pl.get("parse")} url={pl.get("url", "")[:78]}')
    print(f'  线路可播: {ok}/{len([u for u in urls if u])}')

    print('\n=== 搜索: 斗罗 ===')
    sres = sp.searchContent('斗罗', False, '1')
    print(f'  结果 {len(sres.get("list", []))} 个, pagecount={sres.get("pagecount")}, total={sres.get("total")}')
    for v in sres.get('list', [])[:5]:
        print(f'    {v["vod_name"]} (id={v["vod_id"]}) {v.get("type_name")} {v.get("vod_remarks")}')
