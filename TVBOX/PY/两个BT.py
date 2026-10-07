import sys
import urllib.parse
import re
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "两个BT影视"

    def init(self, extend=""):
        self.host = 'https://www.bttwo.life'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': self.host
        }
        # 预加载筛选ID映射
        self._filter_ids = None

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _load_filter_ids(self):
        """加载筛选ID映射"""
        if self._filter_ids is not None:
            return
            
        print("[两个BT] 加载筛选ID映射...")
        
        # 默认映射（兜底）
        self._filter_ids = {
            'areas': {
                '全部': '', '美国': '5', '日本': '11', '韩国': '12', '中国大陆': '52',
                '中国香港': '14', '中国台湾': '21', '法国': '6', '英国': '30', '加拿大': '32',
                '德国': '18', '意大利': '19', '西班牙': '24', '俄罗斯': '16', '印度': '34',
                '澳大利亚': '22', '泰国': '33', '其他': '78'
            },
            'types': {
                '全部': '', '剧情': '1', '悬疑': '2', '恐怖': '3', '惊悚': '4',
                '喜剧': '5', '爱情': '6', '犯罪': '9', '动作': '10', '动画': '11',
                '奇幻': '12', '科幻': '14', '历史': '15', '战争': '16', '冒险': '18',
                '家庭': '19', '纪录': '20', '传记': '28', '运动': '30', '武侠': '31'
            },
            'years': {
                '全部': '', '2026': '1', '2025': '3', '2024': '4', '2023': '56',
                '2022': '13', '2021': '2', '2020': '6', '2019': '8', '2018': '9',
                '2010-2014': '11', '2000-2009': '12', '1990-1999': '13', '1980-1989': '14',
                '1970-1979': '15', '1960-1969': '16', '1950-1959': '17', '1940-1949': '18',
                '1930-1939': '19', '1920-1929': '20'
            }
        }
        
        # 尝试从网站动态获取（可选）
        try:
            html = self.fetch(f'{self.host}/filter?classify=3', headers=self.headers).text
            
            # 提取地区ID
            area_matches = re.findall(r'href="\?classify=\d+&amp;areas=(\d+)"[^>]*>([^<]+)</a>', html)
            for vid, vn in area_matches:
                name = vn.strip()
                if name.lower() == 'unknown':
                    name = '其他'
                self._filter_ids['areas'][name] = vid
                
            # 提取类型ID
            type_matches = re.findall(r'href="\?classify=\d+&amp;(?:areas=\d+&amp;)?types=(\d+)"[^>]*>([^<]+)</a>', html)
            for vid, vn in type_matches:
                name = vn.strip()
                self._filter_ids['types'][name] = vid
                
            # 提取年份ID
            year_matches = re.findall(r'href="\?classify=\d+&amp;(?:areas=\d+&amp;)?years=(\d+)"[^>]*>([^<]+)</a>', html)
            for vid, vn in year_matches:
                name = vn.strip()
                self._filter_ids['years'][name] = vid
                
            print(f"[两个BT] 筛选ID加载完成: 地区{len(self._filter_ids['areas'])}, 类型{len(self._filter_ids['types'])}, 年份{len(self._filter_ids['years'])}")
        except Exception as e:
            print(f"[两个BT] 动态加载筛选ID失败，使用默认映射: {e}")

    def homeContent(self, filter):
        self._load_filter_ids()
        result = {}
        result['class'] = [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '电视剧'},
            {'type_id': '3', 'type_name': '动漫'}
        ]
        result['filters'] = self._get_filters()
        return result

    def homeVideoContent(self):
        try:
            rsp = self.fetch(self.host, headers=self.headers)
            doc = self.html(rsp.text)
            return {'list': self._get_videos(doc)}
        except Exception as e:
            print(f'homeVideoContent 错误: {e}')
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            self._load_filter_ids()
            
            # 构建筛选参数（将中文转换为数字ID）
            params = []
            
            # classify参数：1=电影, 2=电视剧, 3=动漫
            classify_map = {'1': '1', '2': '2', '3': '3'}
            classify = classify_map.get(tid, '1')
            params.append(f"classify={classify}")
            
            # 地区筛选
            if extend.get('area'):
                area_name = extend['area']
                area_id = self._filter_ids['areas'].get(area_name, '')
                if area_id:
                    params.append(f"areas={area_id}")
            
            # 类型筛选
            if extend.get('type'):
                type_name = extend['type']
                type_id = self._filter_ids['types'].get(type_name, '')
                if type_id:
                    params.append(f"types={type_id}")
            
            # 年份筛选
            if extend.get('year'):
                year_name = extend['year']
                year_id = self._filter_ids['years'].get(year_name, '')
                if year_id:
                    params.append(f"years={year_id}")
            
            # 分页参数
            if str(pg) != '1':
                params.append(f"page={pg}")
            
            # 构建URL
            url = f"{self.host}/filter"
            if params:
                url += "?" + "&".join(params)
            
            print(f'[两个BT] 分类请求: {url}')
            
            rsp = self.fetch(url, headers=self.headers)
            doc = self.html(rsp.text)
            return {
                'list': self._get_videos(doc),
                'page': int(pg),
                'pagecount': 9999,
                'limit': 20
            }
        except Exception as e:
            print(f'categoryContent 错误: {e}')
            return {'list': []}

    def detailContent(self, ids):
        try:
            vid = ids[0]
            detail_url = f"{self.host}{vid}" if str(vid).startswith('/') else f"{self.host}/play/{vid}"
            
            rsp = self.fetch(detail_url, headers=self.headers)
            doc = self.html(rsp.text)
            
            # 修复标题提取逻辑 - 按优先级尝试不同的选择器
            title = "未知"
            
            # 1. 首先尝试h1标题（最常见）
            title_nodes = doc.xpath('//h1[contains(@class,"text-lg")]/text()')
            if title_nodes and title_nodes[0].strip():
                title = title_nodes[0].strip()
            else:
                # 2. 尝试h2标题
                title_nodes = doc.xpath('//h2[contains(@class,"text-xl")]/text()')
                if title_nodes and title_nodes[0].strip():
                    title = title_nodes[0].strip()
                else:
                    # 3. 尝试title标签
                    title_nodes = doc.xpath('//title/text()')
                    if title_nodes and title_nodes[0].strip():
                        title = title_nodes[0].strip()
                        # 清理title中的网站后缀
                        title = re.sub(r'\s*-\s*两个BT.*$', '', title)
                        title = re.sub(r'\s*\|\s*两个BT.*$', '', title)
                    else:
                        # 4. 尝试meta标签
                        meta_nodes = doc.xpath('//meta[@property="og:title"]/@content')
                        if meta_nodes and meta_nodes[0].strip():
                            title = meta_nodes[0].strip()
            
            # 最终清理标题
            title = title.strip()
            # 移除多余的空格和特殊字符
            title = re.sub(r'\s+', ' ', title)
            # 移除常见的网站后缀
            title = re.sub(r'\s*-\s*两个BT.*$', '', title)
            title = re.sub(r'\s*\|\s*两个BT.*$', '', title)
            title = re.sub(r'\s*-\s*TwoBT.*$', '', title)
            title = re.sub(r'\s*\|\s*TwoBT.*$', '', title)
            
            print(f'[两个BT] 提取标题: {title}')
            
            img_nodes = doc.xpath('//div[contains(@class,"movie-poster")]//img/@src | //div[contains(@class,"movie-poster")]//img/@data-src | //meta[@property="og:image"]/@content')
            pic = ""
            for img in img_nodes:
                if "placeholder" not in img.lower():
                    pic = img
                    break
            if not pic and img_nodes:
                pic = img_nodes[0]
                
            remarks_nodes = doc.xpath('//span[contains(text(),"共") and contains(text(),"集")]/text()')
            remarks = remarks_nodes[0].strip() if remarks_nodes else ""
            
            director_nodes = doc.xpath('//div[text()="导演"]/following-sibling::div[1]/text()')
            director = director_nodes[0].strip() if director_nodes else ""
            
            actor_nodes = doc.xpath('//div[text()="主演"]/following-sibling::div[1]/text()')
            actor = actor_nodes[0].strip() if actor_nodes else ""
            
            content_nodes = doc.xpath('//h3[contains(text(),"剧情简介")]/parent::div/p/text()')
            content = content_nodes[0].strip() if content_nodes else ""
            
            episodes = []
            
            # 尝试缩小选择范围，优先寻找播放列表区块
            list_nodes = doc.xpath('//div[contains(@class, "episode")] | //div[contains(@class, "playlist")] | //div[contains(@class, "video-list")]')
            
            if list_nodes:
                links = list_nodes[0].xpath('.//a[contains(@href, "/play/")] | .//a[contains(@class, "episode-link")]')
            else:
                links = doc.xpath('//a[contains(@class, "episode-link")] | //a[contains(@href, "/play/")]')
                
            seen_hrefs = set()
            
            # 提取当前视频的核心ID，用于二次校验，阻断无关剧集的链接
            core_id = "".join([c for c in str(vid) if c.isdigit()])
            if not core_id:
                core_id = str(vid).split('/')[-1].split('-')[0].split('.')[0]
            
            for link in links:
                href = link.xpath('./@href')[0]
                
                if href in seen_hrefs or not href.startswith('/play/'):
                    continue
                    
                # 若提取到了核心ID且链接中不包含该ID，跳过（防止抓到推荐视频）
                if core_id and core_id not in href:
                    continue
                    
                seen_hrefs.add(href)
                
                # 直接提取标签内所有文本
                name_list = link.xpath('.//text()')
                name = "".join([n.strip() for n in name_list if n.strip()])
                name = " ".join(name.split())
                
                if not name:
                    name = link.xpath('./@data-episode')[0] if link.xpath('./@data-episode') else f"第{len(episodes)+1}集"
                
                episodes.append(f"{name}${href}")
                
            return {
                'list': [{
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': remarks,
                    'vod_director': director,
                    'vod_actor': actor,
                    'vod_content': content,
                    'vod_play_from': '两个BT',
                    'vod_play_url': '#'.join(episodes) if episodes else f"正片${detail_url.replace(self.host, '')}"
                }]
            }
        except Exception as e:
            print(f'detailContent 错误: {e}')
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        try:
            url = f"{self.host}/search?q={urllib.parse.quote(key)}"
            if pg != "1":
                url += f"&page={pg}"
            rsp = self.fetch(url, headers=self.headers)
            doc = self.html(rsp.text)
            return {
                'list': self._get_search_videos(doc),
                'page': int(pg),
                'pagecount': 9999,
                'limit': 20
            }
        except Exception as e:
            print(f'searchContent 错误: {e}')
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        # WASM 播放器直连
        play_url = id if id.startswith('http') else self.host + id
        return {'parse': 1, 'url': play_url, 'header': self.headers}

    def localProxy(self, param):
        return [200, "video/MP2T", ""]

    def _get_videos(self, doc):
        videos = []
        nodes = doc.xpath('//div[@data-vod-id] | //a[contains(@href, "/play/")]/ancestor::div[contains(@class, "group")][1]')
        seen_ids = set()
        
        for node in nodes:
            v_id = ""
            if node.xpath('./@data-vod-id'):
                v_id = f"/play/{node.xpath('./@data-vod-id')[0]}"
            else:
                hrefs = node.xpath('.//a[contains(@href, "/play/")]/@href')
                if hrefs:
                    v_id = hrefs[0]
            
            if not v_id or v_id in seen_ids:
                continue
            seen_ids.add(v_id)

            # 修复列表页标题提取
            name = "未知"
            
            # 1. 尝试h3标签
            name_nodes = node.xpath('.//h3/text()')
            if name_nodes and name_nodes[0].strip():
                name = name_nodes[0].strip()
            else:
                # 2. 尝试a标签的title属性
                name_nodes = node.xpath('.//a[contains(@href, "/play/")]/@title')
                if name_nodes and name_nodes[0].strip():
                    name = name_nodes[0].strip()
                else:
                    # 3. 尝试img的alt属性
                    name_nodes = node.xpath('.//img/@alt')
                    if name_nodes and name_nodes[0].strip():
                        name = name_nodes[0].strip()
            
            # 清理名称
            name = re.sub(r'\s+', ' ', name).strip()
            
            img_nodes = node.xpath('.//img/@src | .//img/@data-src | .//img/@data-original')
            v_pic = ""
            for img in img_nodes:
                if "placeholder" not in img.lower():
                    v_pic = img
                    break
            if not v_pic and img_nodes:
                v_pic = img_nodes[0]
                
            remarks_nodes = node.xpath('.//span[contains(@class,"text-text-secondary")]/text() | .//span[contains(text(),"更新")]/text() | .//span[contains(@class,"bg-gradient-to-r")]/text() | .//div[contains(@class,"text-green-500")]/text()')
            v_remarks = remarks_nodes[0].strip().replace('更新', '') if remarks_nodes else ""
            
            videos.append({
                'vod_id': v_id,
                'vod_name': name,
                'vod_pic': v_pic,
                'vod_remarks': v_remarks
            })
        return videos

    def _get_search_videos(self, doc):
        return self._get_videos(doc)

    def _get_filters(self):
        """生成筛选器配置（使用中文名称，但实际会使用数字ID）"""
        # 从映射中提取选项
        areas = [{'n': k, 'v': k} for k in self._filter_ids['areas'].keys()]
        types = [{'n': k, 'v': k} for k in self._filter_ids['types'].keys()]
        years = [{'n': k, 'v': k} for k in self._filter_ids['years'].keys()]
        
        # 排序：全部放在第一位
        areas.sort(key=lambda x: (x['v'] != '', x['n']))
        types.sort(key=lambda x: (x['v'] != '', x['n']))
        years.sort(key=lambda x: (x['v'] != '', x['n']))
        
        base = [
            {'key': 'area', 'name': '地区', 'value': areas},
            {'key': 'type', 'name': '类型', 'value': types},
            {'key': 'year', 'name': '年份', 'value': years}
        ]
        return {'1': base, '2': base, '3': base}
