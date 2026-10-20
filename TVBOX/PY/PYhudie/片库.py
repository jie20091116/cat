# -*- coding: utf-8 -*-
# 片库 Spider
# 兼容 FongMi/TV (T3) & WebHomeTV / PeekPro (T4)
#
# 站点: 4k01.pianku.online (MacCMS v10)
# 分类: /vodtype/{tid}-{pg}.html  详情: /voddetail/{id}.html
# 播放: /vodplay/{id}-{sid}-{nid}.html  搜索: /vodsearch/-------------.html?wd=xx

import sys
import json
import re
import time
import base64
import urllib.parse

sys.path.append('..')

try:
    from base.spider import Spider
except ImportError:
    import requests as rq

    class Spider:
        def fetch(self, url, headers=None, **kw):
            t = kw.pop('timeout', 15)
            r = rq.get(url, headers=headers, timeout=t, **kw)
            r.encoding = 'utf-8'
            return r


class Spider(Spider):
    host = 'https://4k01.pianku.online'

    header = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    classes = [
        {'type_name': '电影', 'type_id': '20'},
        {'type_name': '剧集', 'type_id': '37'},
        {'type_name': '动漫', 'type_id': '43'},
        {'type_name': '综艺', 'type_id': '45'},
        {'type_name': '短剧', 'type_id': 'duanju'},
        {'type_name': '万视直链', 'type_id': 'wsy'},
    ]

    filters = {
        'wsy': [{'key': 't', 'name': '分类', 'value': [
            {'n': '电影', 'v': 'movie'},
            {'n': '剧集', 'v': 'tv'},
            {'n': '动漫', 'v': 'anime'},
            {'n': '综艺', 'v': 'variety'},
            {'n': '短剧', 'v': 'duanju'},
        ]}],
    }

    wsy_tmap = {
        'movie': '6,7,8,9,10,11,12',
        'tv': '13,14,15,16,17,18,19,23',
        'anime': '29,30,31,39,44,45',
        'variety': '25,26,27,28',
        'duanju': '54,64,65,76',
    }


    parser_map = {
        'qq': 'https://bfq.txnp.cn/player?url=',
        'qiyi': 'https://bfq.txnp.cn/player?url=',
        'youku': 'https://bfq.txnp.cn/player?url=',
        'mgtv': 'https://bfq.txnp.cn/player?url=',
        'bilibili': 'https://bfq.txnp.cn/player?url=',
        '360zy': 'https://bfq.txnp.cn/player?url=',
        'mjzy': 'https://mujizybf.com/m3u8/?url=',
        'wsym3u8': 'https://wsyzy.top/m3u8/?url=',
    }

    def getName(self):
        return '片库'

    def init(self, extend=''):
        self.extend = extend or ''

    def isVideoFormat(self, url):
        return any(x in url for x in ['.m3u8', '.mp4', '.flv', '.mkv', '.avi'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def _get(self, url, ref=None, timeout=15):
        h = dict(self.header)
        if ref:
            h['Referer'] = ref
        r = self.fetch(url, headers=h, timeout=timeout)
        if isinstance(r, str):
            return r
        return r.text if hasattr(r, 'text') else r.content.decode('utf-8', 'ignore')
    def _post_json(self, url, data, timeout=10):
        try:
            import requests as _r
            r = _r.post(url, json=data, headers={
                'User-Agent': self.header['User-Agent'], 'Referer': 'https://l98.cn/'}, timeout=timeout)
            return r.json()
        except Exception:
            return {}
    def _wsy_list(self, pg, t=None):
        try:
            pg = int(pg or 1)
            url = 'https://api.wsyzy.net/api.php/provide/vod?ac=videolist&pg=%d' % pg
            if t:
                url += '&t=%d' % int(t)
            d = json.loads(self._get(url, timeout=12))
            lst = [{'vod_id': 'wsy$' + str(x.get('vod_id')), 'vod_name': x.get('vod_name', ''),
                    'vod_pic': x.get('vod_pic', ''), 'vod_remarks': x.get('vod_remarks', '')}
                   for x in (d.get('list') or [])]
            pc = int(d.get('pagecount') or 1)
            return {'page': pg, 'pagecount': pc, 'limit': len(lst), 'total': pc * len(lst), 'list': lst}
        except Exception:
            return {'page': pg or 1, 'pagecount': 1, 'limit': 0, 'total': 0, 'list': []}
    def _wsy_cat(self, pg, t):
        tids = (self.wsy_tmap.get(str(t or '')) or '').split(',')
        if not tids or not tids[0]:
            return self._wsy_list(pg)
        from concurrent.futures import ThreadPoolExecutor

        def fetch(tid):
            return self._wsy_list(pg, t=int(tid)).get('list') or []
        try:
            with ThreadPoolExecutor(max_workers=len(tids)) as ex:
                res = list(ex.map(fetch, tids))
        except Exception:
            return self._wsy_list(pg)
        out, seen = [], set()
        for lst in res:
            for it in lst:
                if it['vod_id'] in seen:
                    continue
                seen.add(it['vod_id'])
                out.append(it)
        return {'page': pg, 'pagecount': 1000, 'limit': len(out),
                'total': len(out) * len(tids), 'list': out}
    def _wsy_detail(self, rid):
        try:
            d = json.loads(self._get('https://api.wsyzy.net/api.php/provide/vod?ac=detail&ids=' + str(rid), timeout=12))
            li = (d.get('list') or [{}])[0]
            vod = {'vod_id': 'wsy$' + str(rid), 'vod_name': li.get('vod_name', ''),
                   'vod_pic': li.get('vod_pic', ''), 'vod_remarks': li.get('vod_remarks', '')}
            vod['vod_play_from'] = '万视'
            vod['vod_play_url'] = li.get('vod_play_url', '')
            return {'list': [vod]}
        except Exception:
            return {'list': []}
    def _l98_enc(self, key, rid, name=''):
        raw = key + '|' + str(rid) + ('|' + urllib.parse.quote(name) if name else '')
        return base64.urlsafe_b64encode(raw.encode()).decode().rstrip('=')
    def _l98_dec(self, vid):
        try:
            p = base64.urlsafe_b64decode(vid + '=' * (-len(vid) % 4)).decode().split('|')
            if len(p) >= 2:
                return p[0], p[1], urllib.parse.unquote(p[2]) if len(p) > 2 else ''
        except Exception:
            pass
        return 'source-a45d5761c9', vid, ''
    def _res_rank(self, pairs):
        keys = ('4k', '2160', '1080', '蓝光', '超清', '高清', '720', 'hd', 'tc', 'ts', '抢先', '预告')
        def score(fu):
            f, u = fu
            s = (f + ' ' + u).lower()
            for i, k in enumerate(keys):
                if k in s:
                    return i
            return len(keys)
        return sorted(pairs, key=score)
    def _l98_detail(self, enc):
        try:
            key, rid, _ = self._l98_dec(enc)
            d = self._post_json('https://l98.cn/api/detail',
                                {'api': 'tvbox-py://' + key, 'ids': rid}, timeout=10)
            dd = d.get('data') if isinstance(d, dict) else d
            if not dd or not dd.get('vod_play_url'):
                return {'list': []}
            vod = {'vod_id': 'l98$' + enc, 'vod_name': dd.get('vod_name', '') or _,
                   'vod_pic': dd.get('vod_pic', '') or '', 'vod_remarks': dd.get('vod_remarks', '') or ''}
            fs = (dd.get('vod_play_from') or '').split('$$$')
            us = (dd.get('vod_play_url') or '').split('$$$')
            if len(fs) != len(us):
                fs = ['线路%d' % (i + 1) for i in range(len(us))]
            pairs = self._res_rank([(f, u) for f, u in zip(fs, us) if u])
            vod['vod_play_from'] = '$$$'.join(f for f, _ in pairs)
            vod['vod_play_url'] = '$$$'.join(u for _, u in pairs)
            return {'list': [vod]}
        except Exception:
            return {'list': []}
    def _l98_play(self, id):
        try:
            u = urllib.parse.unquote(str(id)).strip()
            if '#' in u:
                u = u.split('#')[0]
            if '$' in u:
                u = u.split('$')[-1].strip()
            if u.startswith('http'):
                if 'tvbox_ep_' not in u:
                    return {'parse': 0, 'url': u}
                u = urllib.parse.urlparse(u).path
            if not u.startswith('/'):
                u = '/' + u
            key = 'source-a45d5761c9'
            if 'tvbox_ep_' in u:
                tok = u.split('tvbox_ep_')[-1].split('?')[0]
                try:
                    key = json.loads(base64.urlsafe_b64decode(tok + '=' * (-len(tok) % 4)).decode()).get('s') or key
                except Exception:
                    pass
            jurl = 'enc_' + base64.b64encode(urllib.parse.quote('tvbox-play://' + key, safe='').encode()).decode() + '_' + format(int(time.time() * 1000), 'x')
            d = {}
            for _ in range(2):
                d = self._post_json('https://l98.cn/api/json', {'jsonUrl': jurl, 'movieUrl': u}, timeout=15)
                if isinstance(d, dict) and d.get('success') and d.get('url'):
                    break
                time.sleep(1)
            if not (isinstance(d, dict) and d.get('success') and d.get('url')) or d.get('parse') == 1:
                return {'parse': 0, 'url': ''}
            m = d['url']
            return {'parse': 0, 'url': m if m.startswith('http') else 'https://l98.cn' + (m if m.startswith('/') else '/' + m)}
        except Exception:
            return {'parse': 0, 'url': ''}
    def _l98_cat(self, tid, pg):
        try:
            pg = int(pg or 1)
            srcs = (('source-a45d5761c9', '瓜子', str(tid)), ('source-37dc8f3871', '独播', str(tid)),
                    ('source-0ad659640c', '泥巴', str(tid)))
            if str(tid) == '64':
                srcs = (('source-a45d5761c9', '瓜子', '64'), ('source-c6eef9d264', '星芽', '1'))

            def fetch(kn):
                key, nm, t = kn
                try:
                    d = self._post_json('https://l98.cn/api/tvbox/category',
                                        {'api': 'tvbox-py://' + key, 'tid': t, 'page': pg,
                                         'filter': {}, 'extend': {}}, timeout=8)
                except Exception:
                    return key, nm, []
                lst = d.get('list') if isinstance(d, dict) else None
                if not lst and isinstance(d, dict) and isinstance(d.get('data'), dict):
                    lst = (d.get('data') or {}).get('list')
                return key, nm, lst or []
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=3) as ex:
                res = list(ex.map(fetch, srcs))
            out, seen = [], set()
            for key, nm, lst in res:
                for x in lst:
                    vid = 'l98$' + self._l98_enc(key, x.get('vod_id'), x.get('vod_name', ''))
                    if vid in seen:
                        continue
                    seen.add(vid)
                    out.append({'vod_id': vid, 'vod_name': x.get('vod_name', ''),
                                'vod_pic': x.get('vod_pic', ''), 'vod_remarks': (x.get('vod_remarks') or '') + '·' + nm})
            return {'page': pg, 'pagecount': 1, 'limit': len(out), 'total': len(out), 'list': out}
        except Exception:
            return {'page': pg or 1, 'pagecount': 1, 'limit': 0, 'total': 0, 'list': []}
    def _mix_extra(self, tid, pg=1):
        extra, seen = [], set()
        l98_tid = {'20': '1', '37': '2', '43': '4', '45': '3', 'duanju': '64'}.get(str(tid))
        from concurrent.futures import ThreadPoolExecutor

        def job_l98():
            if not l98_tid:
                return []
            return self._l98_cat(l98_tid, pg).get('list') or []

        def job_src(sr, base):
            try:
                dd = json.loads(self._get(base, timeout=8))
            except Exception:
                return []
            return [{'vod_id': sr + '$' + str(x.get('vod_id')), 'vod_name': x.get('vod_name', ''),
                     'vod_pic': x.get('vod_pic', ''), 'vod_remarks': (x.get('vod_remarks') or '') or sr}
                    for x in (dd.get('list') or [])[:12]]
        with ThreadPoolExecutor(max_workers=3) as ex:
            fs = [ex.submit(job_l98)]
            fs += [ex.submit(job_src, s, b) for s, b in (
                ('jisu', 'https://jisuziyuan.com/api.php/provide/vod/?ac=videolist&pg=1'),
                ('lz', 'https://cj.lziapi.com/api.php/provide/vod/?ac=videolist&pg=1'))]
            for f in fs:
                for it in f.result():
                    if it['vod_id'] in seen:
                        continue
                    seen.add(it['vod_id'])
                    extra.append(it)
        return extra
    def _duanju_list(self, pg):
        try:
            pg = int(pg or 1)
            out, seen = [], set()
            for t in ('54', '64', '65', '76'):
                try:
                    d = json.loads(self._get('https://api.wsyzy.net/api.php/provide/vod?ac=videolist&t=%s&pg=%d' % (t, pg), timeout=10))
                except Exception:
                    continue
                for x in (d.get('list') or []):
                    vid = str(x.get('vod_id'))
                    if vid in seen:
                        continue
                    seen.add(vid)
                    out.append({'vod_id': 'wsy$' + vid, 'vod_name': x.get('vod_name', ''),
                                'vod_pic': x.get('vod_pic', ''), 'vod_remarks': (x.get('vod_remarks') or '') or '短剧'})
            if pg <= 1:
                for it in self._mix_extra('duanju', 1):
                    if it['vod_id'] in seen:
                        continue
                    seen.add(it['vod_id'])
                    out.append(it)
            return {'page': pg, 'pagecount': 1000, 'limit': len(out), 'total': 20000, 'list': out}
        except Exception:
            return {'page': pg or 1, 'pagecount': 1, 'limit': 0, 'total': 0, 'list': []}
    def _jisu_list(self, pg):
        try:
            pg = int(pg or 1)
            d = json.loads(self._get('https://jisuziyuan.com/api.php/provide/vod/?ac=videolist&pg=%d' % pg, timeout=12))
            lst = [{'vod_id': 'jisu$' + str(x.get('vod_id')), 'vod_name': x.get('vod_name', ''),
                    'vod_pic': x.get('vod_pic', ''), 'vod_remarks': x.get('vod_remarks', '')}
                   for x in (d.get('list') or [])]
            pc = int(d.get('pagecount') or 1)
            return {'page': pg, 'pagecount': pc, 'limit': len(lst), 'total': pc * len(lst), 'list': lst}
        except Exception:
            return {'page': pg or 1, 'pagecount': 1, 'limit': 0, 'total': 0, 'list': []}
    def _jisu_detail(self, rid):
        try:
            d = json.loads(self._get('https://jisuziyuan.com/api.php/provide/vod/?ac=detail&ids=' + str(rid), timeout=12))
            li = (d.get('list') or [{}])[0]
            vod = {'vod_id': 'jisu$' + str(rid), 'vod_name': li.get('vod_name', ''),
                   'vod_pic': li.get('vod_pic', ''), 'vod_remarks': li.get('vod_remarks', '')}
            vod['vod_play_from'] = 'jisu'
            vod['vod_play_url'] = li.get('vod_play_url', '')
            return {'list': [vod]}
        except Exception:
            return {'list': []}
    def _lz_list(self, pg):
        try:
            pg = int(pg or 1)
            d = json.loads(self._get('https://cj.lziapi.com/api.php/provide/vod/?ac=videolist&pg=%d' % pg, timeout=12))
            lst = [{'vod_id': 'lz$' + str(x.get('vod_id')), 'vod_name': x.get('vod_name', ''),
                    'vod_pic': x.get('vod_pic', ''), 'vod_remarks': x.get('vod_remarks', '')}
                   for x in (d.get('list') or [])]
            pc = int(d.get('pagecount') or 1)
            return {'page': pg, 'pagecount': pc, 'limit': len(lst), 'total': pc * len(lst), 'list': lst}
        except Exception:
            return {'page': pg or 1, 'pagecount': 1, 'limit': 0, 'total': 0, 'list': []}
    def _lz_detail(self, rid):
        try:
            d = json.loads(self._get('https://cj.lziapi.com/api.php/provide/vod/?ac=detail&ids=' + str(rid), timeout=12))
            li = (d.get('list') or [{}])[0]
            vod = {'vod_id': 'lz$' + str(rid), 'vod_name': li.get('vod_name', ''),
                   'vod_pic': li.get('vod_pic', ''), 'vod_remarks': li.get('vod_remarks', '')}
            vod['vod_play_from'] = 'lz'
            vod['vod_play_url'] = li.get('vod_play_url', '')
            return {'list': [vod]}
        except Exception:
            return {'list': []}
    def _parse_list(self, html):
        out, seen = [], set()
        for m in re.finditer(
                r'<a href="/voddetail/(\d+)\.html"[^>]*title="([^"]+)"[^>]*>.*?'
                r'<img src="([^"]+)"[^>]*>.*?<span class="remarks">([^<]*)</span>',
                html, re.S):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            out.append({
                'vod_id': vid,
                'vod_name': m.group(2),
                'vod_pic': m.group(3),
                'vod_remarks': m.group(4),
            })
        return out

    def _has_source(self, vid):
        try:
            d = self._get('%s/voddetail/%s.html' % (self.host, vid))
            return 'url-grid-play' in d
        except Exception:
            return False

    def _filter_src(self, items):
        if not items:
            return items
        try:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=8) as ex:
                flags = list(ex.map(lambda it: self._has_source(it['vod_id']), items))
            return [it for it, ok in zip(items, flags) if ok]
        except Exception:
            return items

    def _search_all(self, key):
        if not key:
            return []
        plat_k = ('qq', 'qiyi', 'youku', 'mgtv', 'bilibili')

        def qh():
            try:
                d = json.loads(self._get('https://movie.qhdaohang.cn/api.php/provide/vod/?ac=detail&wd=' + urllib.parse.quote(key), timeout=8))
                best, fallback = None, None
                for it in d.get('list') or []:
                    plats, dires = [], []
                    for f, u in zip((it.get('vod_play_from') or '').split('$$$'), (it.get('vod_play_url') or '').split('$$$')):
                        f = f.strip()
                        if '$' not in u.split('#')[0]:
                            continue
                        first = u.split('#')[0].split('$', 1)[-1].strip()
                        if not first.startswith('http'):
                            continue
                        if f in plat_k:
                            plats.append(u)
                        elif f == 'mjzy' or '.m3u8' in first:
                            dires.append(u)
                    if best is None and plats:
                        best = (plats, dires)
                    if fallback is None and dires:
                        fallback = (plats, dires)
                out = []
                if best:
                    best[0].sort(key=lambda u: u.count('#'), reverse=True)
                    out.append({'name': '高清', 'kind': 'parse', 'eps': best[0][0]})
                dire_pool = (best and best[1]) or (fallback and fallback[1]) or []
                if dire_pool:
                    dire_pool.sort(key=lambda u: u.count('#'), reverse=True)
                    out.append({'name': '直链', 'kind': 'direct', 'eps': dire_pool[0]})
                return out
            except Exception:
                return []

        def lz():
            try:
                d = json.loads(self._get('https://cj.lziapi.com/api.php/provide/vod/?ac=detail&wd=' + urllib.parse.quote(key), timeout=8))
                for it in d.get('list') or []:
                    best, best_n = None, -1
                    for f, u in zip((it.get('vod_play_from') or '').split('$$$'), (it.get('vod_play_url') or '').split('$$$')):
                        first = u.split('#')[0].split('$', 1)[-1].strip() if '$' in u.split('#')[0] else u.strip()
                        if first.startswith('http') and ('.m3u8' in first or '.mp4' in first):
                            n = u.count('#')
                            if n > best_n:
                                best_n, best = n, u
                    if best:
                        return [{'name': '量子', 'kind': 'direct', 'eps': best}]
                return []
            except Exception:
                return []

        def js():
            try:
                d = json.loads(self._get('https://jisuziyuan.com/api.php/provide/vod/?ac=detail&wd=' + urllib.parse.quote(key), timeout=8))
                for it in d.get('list') or []:
                    best, best_n = None, -1
                    for f, u in zip((it.get('vod_play_from') or '').split('$$$'), (it.get('vod_play_url') or '').split('$$$')):
                        first = u.split('#')[0].split('$', 1)[-1].strip() if '$' in u.split('#')[0] else u.strip()
                        if first.startswith('http') and ('.m3u8' in first or '.mp4' in first):
                            n = u.count('#')
                            if n > best_n:
                                best_n, best = n, u
                    if best:
                        return [{'name': '短剧', 'kind': 'direct', 'eps': best}]
                return []
            except Exception:
                return []

        try:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=3) as ex:
                f1, f2, f3 = ex.submit(qh), ex.submit(lz), ex.submit(js)
                out = f1.result(timeout=10) + f2.result(timeout=10) + f3.result(timeout=10)
            seen, res = set(), []
            for q in out:
                if q['eps'] in seen:
                    continue
                seen.add(q['eps'])
                res.append(q)
            return res
        except Exception:
            return []

    def homeContent(self, filter):
        return {'class': self.classes, 'filters': self.filters}

    def homeVideoContent(self):
        try:
            html = self._get(self.host + '/')
            lst = self._parse_list(html)
            if lst:
                out = self._filter_src(lst[:60])
                if len(out) < 30:
                    seen = set(x['vod_id'] for x in out)
                    out += [x for x in self._agg_home() if x['vod_id'] not in seen][:30 - len(out)]
                return {'list': out[:30]}
        except Exception:
            pass
        return {'list': self._agg_home()}

    def _agg_home(self):
        out, seen = [], set()
        from concurrent.futures import ThreadPoolExecutor

        def job(src, base):
            try:
                d = json.loads(self._get(base, timeout=10))
            except Exception:
                return []
            return [{'vod_id': src + '$' + str(x.get('vod_id')), 'vod_name': x.get('vod_name', ''),
                     'vod_pic': x.get('vod_pic', ''), 'vod_remarks': (x.get('vod_remarks') or '') or src}
                    for x in (d.get('list') or [])]
        try:
            with ThreadPoolExecutor(max_workers=2) as ex:
                for lst in ex.map(job, ('jisu', 'lz'),
                                  ('https://jisuziyuan.com/api.php/provide/vod/?ac=videolist&pg=1',
                                   'https://cj.lziapi.com/api.php/provide/vod/?ac=videolist&pg=1')):
                    for it in lst:
                        if it['vod_id'] in seen:
                            continue
                        seen.add(it['vod_id'])
                        out.append(it)
        except Exception:
            pass
        return out[:30]

    def _cat_fallback(self, tid, pg):
        try:
            d = self._wsy_list(pg, t=tid)
            lst, seen = list(d.get('list') or []), set(x['vod_id'] for x in (d.get('list') or []))
            if pg <= 1:
                for it in self._mix_extra(tid, 1):
                    if it['vod_id'] in seen:
                        continue
                    seen.add(it['vod_id'])
                    lst.append(it)
            pc = int(d.get('pagecount') or 1)
            return {'page': pg, 'pagecount': pc, 'limit': len(lst), 'total': pc * len(lst), 'list': lst}
        except Exception:
            return {'page': pg or 1, 'pagecount': 1, 'limit': 0, 'total': 0, 'list': []}

    def _main_cat(self, tid, pg):
        try:
            pg = int(pg or 1)
            try:
                html = self._get('%s/vodtype/%s-%s.html' % (self.host, tid, pg))
                vlist = self._parse_list(html)
            except Exception:
                html, vlist = '', []
            if not vlist:
                return self._cat_fallback(tid, pg)
            total = len(vlist)
            m = re.search(r'/vodtype/%s-(\d+)\.html"[^>]*>尾页' % tid, html)
            pagecount = int(m.group(1)) if m else max(1, pg)
            if pg <= 1:
                try:
                    seen = set(x['vod_id'] for x in vlist)
                    vlist = vlist + [x for x in self._mix_extra(tid, 1) if x['vod_id'] not in seen]
                except Exception:
                    pass
            main_part = self._filter_src(vlist[:total])
            vlist = main_part + vlist[total:]
            return {'page': pg, 'pagecount': pagecount, 'limit': len(vlist),
                    'total': pagecount * total, 'list': vlist}
        except Exception:
            return {'page': pg or 1, 'pagecount': 1, 'limit': 0, 'total': 0, 'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            if str(tid) == 'duanju':
                return self._duanju_list(pg)
            if str(tid) == 'jisu':
                return self._jisu_list(pg)
            if str(tid) == 'lz':
                return self._lz_list(pg)
            if str(tid) == 'wsy':
                t = ''
                if isinstance(extend, dict):
                    t = extend.get('t') or t
                if isinstance(filter, dict):
                    t = filter.get('t') or t
                return self._wsy_cat(pg, t)
            if str(tid) in ('20', '37', '43', '45'):
                return self._main_cat(tid, pg)
            pg = int(pg or 1)
            try:
                html = self._get('%s/vodtype/%s-%s.html' % (self.host, tid, pg))
                vlist = self._parse_list(html)
            except Exception:
                html, vlist = '', []
            if not vlist and str(tid) in ('20', '37', '43', '45'):
                return self._cat_fallback(tid, pg)
            total = len(vlist)
            m = re.search(r'/vodtype/%s-(\d+)\.html"[^>]*>尾页' % tid, html)
            pagecount = int(m.group(1)) if m else max(1, pg)
            vlist = self._filter_src(vlist)
            return {
                'page': pg,
                'pagecount': pagecount,
                'limit': len(vlist),
                'total': pagecount * total,
                'list': vlist,
            }
        except Exception:
            return {'page': pg or 1, 'pagecount': 1, 'limit': 20, 'total': 0, 'list': []}

    def _attach_search(self, vod):
        froms, urls = [], []
        try:
            from concurrent.futures import ThreadPoolExecutor

            def job(k, nm):
                try:
                    d = self._post_json('https://l98.cn/api/search',
                                        {'api': 'tvbox-py://' + k, 'keyword': vod['vod_name'], 'page': 1}, timeout=8)
                    d = d.get('data') if isinstance(d, dict) else d
                    for it in (d if isinstance(d, list) else [])[:2]:
                        dd = None
                        for _ in range(2):
                            dd = self._post_json('https://l98.cn/api/detail',
                                                 {'api': 'tvbox-py://' + k, 'ids': it.get('vod_id')}, timeout=12)
                            if isinstance(dd, dict) and isinstance(dd.get('data'), dict) and (dd.get('data') or {}).get('vod_play_url'):
                                break
                            time.sleep(1)
                        dd = dd.get('data') if isinstance(dd, dict) else dd
                        if not (dd or {}).get('vod_play_url'):
                            continue
                        fs = (dd.get('vod_play_from') or '').split('$$$')
                        us = (dd.get('vod_play_url') or '').split('$$$')
                        if len(fs) != len(us):
                            fs = ['线路%d' % (i + 1) for i in range(len(us))]
                        pairs = self._res_rank([(f, u) for f, u in zip(fs, us) if u])
                        res = []
                        for f, u in pairs[:3]:
                            eps = [s for s in u.split('#') if '$' in s]
                            if not eps:
                                continue
                            res.append((f, '#'.join('%s$l98$%s' % (s.split('$', 1)[0], s.split('$', 1)[1]) for s in eps)))
                        if res:
                            return nm, res
                except Exception:
                    pass
                return None
            with ThreadPoolExecutor(max_workers=1) as ex:
                fsr = [ex.submit(job, k, nm) for k, nm in
                       (('source-ba3403d123', '山楂影视'), ('source-0ad659640c', '泥巴影视'), ('wencai', '文才影视'))]
                from concurrent.futures import FIRST_COMPLETED, wait
                done, pending = wait(fsr, timeout=30, return_when=FIRST_COMPLETED)
                r = None
                while done and not r:
                    for f in done:
                        rr = f.result()
                        if rr:
                            r = rr
                            break
                    if r or not pending:
                        break
                    done, pending = wait(pending, timeout=30, return_when=FIRST_COMPLETED)
                if r:
                    nm, segs = r
                    for fname, u in segs:
                        froms.append('l98·%s·%s' % (nm, fname))
                        urls.append(u)
        except Exception:
            pass
        for q in self._search_all(vod['vod_name']):
            segs = [s for s in q['eps'].split('#') if '$' in s]
            if not segs:
                continue
            froms.append(q['name'])
            urls.append('#'.join('%s$%s$%s' % (s.split('$', 1)[0], q['kind'], s.split('$', 1)[1]) for s in segs))
        return froms, urls

    def detailContent(self, ids):
        try:
            vid = ids[0] if isinstance(ids, list) else str(ids)
            if str(vid).startswith('wsy$'):
                return self._wsy_detail(str(vid)[4:])
            if str(vid).startswith('jisu$'):
                return self._jisu_detail(str(vid)[5:])
            if str(vid).startswith('lz$'):
                return self._lz_detail(str(vid)[3:])
            if str(vid).startswith('l98$'):
                return self._l98_detail(str(vid)[4:])
            html = self._get('%s/voddetail/%s.html' % (self.host, vid))
            vod = {'vod_id': vid}
            m = re.search(r'<h1 class="detail-title">([^<]+)<span class="detail-remarks">([^<]*)</span>', html)
            if m:
                vod['vod_name'] = m.group(1)
                vod['vod_remarks'] = m.group(2)
            else:
                m = re.search(r'<h1 class="detail-title">([^<]+)</h1>', html)
                vod['vod_name'] = m.group(1) if m else ''
                vod['vod_remarks'] = ''
            m = re.search(r'<div class="detail-poster"><img src="([^"]+)"', html)
            vod['vod_pic'] = m.group(1) if m else ''

            def meta(key):
                m = re.search(r'<span>%s：([^<]+)</span>' % key, html)
                return m.group(1) if m else ''

            vod['type_name'] = meta('分类')
            vod['vod_director'] = meta('导演')
            vod['vod_actor'] = meta('主演')
            m = re.search(r'<div class="detail-desc">.*?<p>(.*?)</p>', html, re.S)
            vod['vod_content'] = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''
            tabs = re.findall(r'<span class="source-tab-item" data-target="(playlist-\d+)">([^<]+)</span>', html)
            panes = dict(re.findall(r'<div class="source-pane" id="(playlist-\d+)"[^>]*>(.*?)</div>', html, re.S))
            froms, urls = [], []
            for pane_id, name in tabs:
                eps = re.findall(r'<a href="(/vodplay/%s-\d+-\d+\.html)"[^>]*title="([^"]+)"' % vid, panes.get(pane_id, ''))
                if eps:
                    u = '#'.join('%s$%s' % (t, x) for x, t in eps)
                    if name in ('腾讯', '奇异', '优酷', '芒果', 'B站'):
                        froms += [name, name + '-直连']
                        urls += [u, u]
                    else:
                        froms.append(name)
                        urls.append(u)
            if not froms:
                froms, urls = self._attach_search(vod)
            vod['vod_play_from'] = '$$$'.join(froms)
            vod['vod_play_url'] = '$$$'.join(urls)
            return {'list': [vod]}
        except Exception:
            return {'list': []}

    def searchContent(self, key, quick, pg=1):
        try:
            html = self._get('%s/vodsearch/-------------.html?wd=%s' % (self.host, urllib.parse.quote(key)))
            out = self._parse_list(html)
            try:
                for k, nm in (('source-0ad659640c', '泥巴影视'), ('wencai', '文才影视'), ('source-ba3403d123', '山楂影视')):
                    d = self._post_json('https://l98.cn/api/search',
                                        {'api': 'tvbox-py://' + k, 'keyword': key, 'page': 1}, timeout=6)
                    d = d.get('data') if isinstance(d, dict) else d
                    for it in (d if isinstance(d, list) else [])[:3]:
                        nmv = it.get('vod_name', '')
                        if not nmv:
                            continue
                        out.append({'vod_id': 'l98$' + self._l98_enc(k, it.get('vod_id'), nmv),
                                    'vod_name': nmv, 'vod_pic': it.get('vod_pic', ''),
                                    'vod_remarks': (it.get('vod_remarks', '') or '') + '·' + nm})
            except Exception:
                pass
            return {'list': out}
        except Exception:
            return {'list': []}

    def _bfq(self, purl):
        try:
            from Crypto.Cipher import AES
            html = self._get('https://bfq.txnp.cn/player?url=' + urllib.parse.quote(purl, safe=''))
            m = re.search(r'let result = "([^"]+)"', html)
            if m:
                r = m.group(1)
                pad = AES.new(r[-32:-16].encode(), AES.MODE_CBC, r[-16:].encode()).decrypt(
                    __import__('base64').b64decode(r[:-32]))
                vurl = json.loads(pad[:-pad[-1]].decode('utf-8'))['video_info']['video']['url']
                if vurl and vurl != purl and not any(x in vurl for x in
                        ('qq.com', 'iqiyi.com', 'youku.com', 'mgtv.com', 'bilibili.com')):
                    ph = {'User-Agent': self.header['User-Agent'], 'Referer': 'https://bfq.txnp.cn/'}
                    return {'parse': 0, 'url': vurl, 'header': ph, 'MiaiHeader': json.dumps(ph)}
        except Exception:
            pass
        return {'parse': 1, 'url': 'https://bfq.txnp.cn/player?url=' + urllib.parse.quote(purl, safe='')}

    def playerContent(self, flag, id, vipFlags):
        try:
            if flag == '万视':
                u = str(id).split('$')[-1].strip() if '$' in str(id) else str(id)
                ph = {'User-Agent': self.header['User-Agent'], 'Referer': 'https://api.wsyzy.net/'}
                return {'parse': 0, 'url': u, 'header': ph, 'MiaiHeader': json.dumps(ph)}
            if flag == 'jisu':
                u = str(id).split('$')[-1].strip() if '$' in str(id) else str(id)
                if 'jisuzyv.com/play/' in u and not u.split('?')[0].endswith('.m3u8'):
                    u = u.rstrip('/') + '/index.m3u8'
                ph = {'User-Agent': self.header['User-Agent'], 'Referer': 'https://jisuziyuan.com/'}
                return {'parse': 0, 'url': u, 'header': ph, 'MiaiHeader': json.dumps(ph)}
            if flag == 'lz':
                u = str(id).split('$')[-1].strip() if '$' in str(id) else str(id)
                try:
                    h = self._get(u, ref='https://v.lz15uu.com/', timeout=10)
                    m = re.search(r'var\s+main\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']', h)
                    if m:
                        p = m.group(1)
                        if p.startswith('/'):
                            p = 'https://' + urllib.parse.urlsplit(u).netloc + p
                        ph = {'User-Agent': self.header['User-Agent'], 'Referer': 'https://v.lz15uu.com/'}
                        return {'parse': 0, 'url': p, 'header': ph, 'MiaiHeader': json.dumps(ph)}
                except Exception:
                    pass
                ph = {'User-Agent': self.header['User-Agent'], 'Referer': 'https://cj.lziapi.com/'}
                return {'parse': 0, 'url': u, 'header': ph, 'MiaiHeader': json.dumps(ph)}
            if 'l98$' in str(id) or flag.startswith('l98'):
                return self._l98_play(id)
            if id.startswith('direct$'):
                _, _, u = id.partition('$')
                ph = {'User-Agent': self.header['User-Agent'],
                      'Referer': 'https://jisuziyuan.com/' if 'jisuzyv.com' in u else 'https://movie.qhdaohang.cn/'}
                return {'parse': 0, 'url': u, 'header': ph, 'MiaiHeader': json.dumps(ph)}
            if id.startswith('parse$'):
                return self._bfq(id.partition('$')[2])
            url = id if id.startswith('http') else self.host + id
            html = self._get(url, ref=self.host + '/')
            m = re.search(r'player_aaaa=({.*?})</script>', html, re.S)
            if not m:
                m2 = re.search(r'<iframe[^>]+src="([^"]+)"', html)
                return {'parse': 1, 'url': m2.group(1)} if m2 else {}
            data = json.loads(m.group(1))
            purl = data.get('url', '')
            pfrom = data.get('from', '')
            if not purl:
                m2 = re.search(r'<iframe[^>]+src="([^"]+)"', html)
                return {'parse': 1, 'url': m2.group(1)} if m2 else {}
            if pfrom == 'mjzy' or 'mujizy' in purl:
                return {
                    'parse': 1,
                    'url': 'https://mujizybf.com/m3u8/?url=' + urllib.parse.quote(purl, safe=''),
                    'header': {'User-Agent': self.header['User-Agent']},
                }
            if self.isVideoFormat(purl):
                if not purl.startswith('http'):
                    purl = self.host + purl
                ph = {
                    'User-Agent': self.header['User-Agent'],
                    'Referer': self.host + '/',
                }
                return {
                    'parse': 0,
                    'url': purl,
                    'header': ph,
                    'MiaiHeader': json.dumps(ph),
                }
            if flag.endswith('-直连'):
                return self._bfq(purl)
            return {
                'parse': 1,
                'url': 'https://bfq.txnp.cn/player?url=' + urllib.parse.quote(purl, safe=''),
                'header': {'User-Agent': self.header['User-Agent']},
            }
        except Exception:
            return {}
