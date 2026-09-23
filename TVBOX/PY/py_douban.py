#coding=utf-8
#!/usr/bin/python
import sys
import json
import urllib.parse
from datetime import date
sys.path.append('..') 
from base.spider import Spider

# 全局常量 与JS文件完全对齐
DOUBAN_API = "https://frodo.douban.com/api/v2"
API_KEY = "0ac44ae016490db2204ce0a042db2916"
USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36 MicroMessenger/7.0.9.501 NetType/WIFI MiniProgramEnv/Windows WindowsWechat"
REFERER = "https://servicewechat.com/wx2f9b06c1de1ccfca/84/page-frame.html"
# 图片防盗链后缀
PIC_SUFFIX = '@Referer=https://api.douban.com/@User-Agent=Mozilla/5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)%20Chrome/113.0.0.0%20Safari/537.36'
# 今日日期，用于判断是否上映
TODAY = date.today().isoformat()

class Spider(Spider):
    def getName(self):
        return "豆瓣"

    def init(self, extend=""):
        print("============{0}============".format(extend))
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    # 核心：判断影片是否已上映（对齐JS isReleased）
    def isReleased(self, item):
        if item.get("release_date"):
            return item["release_date"] <= TODAY
        if item.get("date"):
            return item["date"] <= TODAY
        return True

    # 核心：构建标准vod结构 对齐JS buildVod
    def buildVod(self, item):
        # 1. 解析类型 movie/剧集 tv/剧集
        rawType = (item.get("type") or "").strip().lower()
        typeName = ""
        if "movie" in rawType:
            typeName = "电影"
        elif "tv" in rawType:
            typeName = "剧集"

        # 2. 解析年份+地区 card_subtitle格式 2025 / 中国大陆
        card_subtitle = item.get("card_subtitle", "")
        year = ""
        region = ""
        import re
        match = re.match(r"^(\d{4})\s*\/\s*([^\/]+)", card_subtitle)
        if match:
            year = match.group(1)
            region = match.group(2).strip()

        # 3. 评分处理
        rating_val = "暂无"
        rating = item.get("rating")
        if rating and rating.get("value", 0) != 0:
            rating_val = str(rating["value"])

        # 4. 图片处理
        pic_url = ""
        pic = item.get("pic", {})
        if pic and pic.get("normal"):
            pic_url = pic["normal"] + PIC_SUFFIX

        return {
            "vod_id": str(item.get("id", "")),
            "vod_name": item.get("title", ""),
            "vod_pic": pic_url,
            "vod_remarks": f"{typeName}评分 {rating_val}",
            "vod_year": f"{year}{region}" if year else ""
        }

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "热播剧集": "tv_hot",
            "热门电影": "hot_movie",
            "热播综艺": "show_hot",
            "电影筛选": "movie",
            "电视筛选": "tv",
            "电影榜单": "rank_list_movie",
            "电视榜单": "rank_list_tv"
        }
        classes = []
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
        result['class'] = classes
        if filter:
            result['filters'] = self.config['filter']
        return result

    # 首页推荐列表（对齐JS homeVod）
    def homeVideoContent(self):
        try:
            params = {
                "apikey": API_KEY,
                "has_schedule": True,
                "count": 30
            }
            query = urllib.parse.urlencode(params)
            url = f"{DOUBAN_API}/subject_collection/subject_real_time_hotest/items?{query}"
            rsp = self.fetch(url, headers=self.header, timeout=4000)
            jo = json.loads(rsp.text)
            joList = jo.get("subject_collection_items", [])
            lists = []
            for item in joList:
                item_type = item.get("type", "")
                if item_type not in ["movie", "tv"]:
                    continue
                # 过滤未上映
                if not self.isReleased(item):
                    continue
                vod = self.buildVod(item)
                if vod["vod_pic"]:
                    lists.append(vod)
            return {"list": lists}
        except Exception as e:
            return {"list": []}

    # 分类列表（对齐JS category）
    def categoryContent(self, tid, pg, filter, extend):
        result = {
            "list": [],
            "page": int(pg),
            "pagecount": 9999,
            "limit": 30,
            "total": 999999
        }
        try:
            start = (int(pg) - 1) * 30
            path = ""
            req_params = {
                "apikey": API_KEY,
                "has_schedule": True,
                "start": start,
                "count": 30
            }
            # 分支逻辑完全对齐JS
            if tid == "hot_movie":
                path = "/movie/hot_gaia"
                req_params["sort"] = extend.get("sort", "recommend")
                req_params["area"] = extend.get("area", "全部")
                data_key = "items"
            elif tid in ["tv_hot", "show_hot"]:
                sub_type = extend.get("type", tid)
                path = f"/subject_collection/{sub_type}/items"
                data_key = "subject_collection_items"
            elif tid == "movie":
                tags = []
                if extend.get("类型"):
                    tags.append(extend["类型"])
                if extend.get("地区"):
                    tags.append(extend["地区"])
                if extend.get("年代"):
                    tags.append(extend["年代"])
                req_params["tags"] = ",".join([t for t in tags if t.strip()])
                req_params["sort"] = extend.get("sort", "T")
                path = "/movie/recommend"
                data_key = "items"
            elif tid == "tv":
                tags = []
                if extend.get("类型"):
                    tags.append(extend["类型"])
                if extend.get("电视剧形式"):
                    tags.append(extend["电视剧形式"])
                if extend.get("综艺形式"):
                    tags.append(extend["综艺形式"])
                if extend.get("地区"):
                    tags.append(extend["地区"])
                if extend.get("年代"):
                    tags.append(extend["年代"])
                if extend.get("平台"):
                    tags.append(extend["平台"])
                req_params["tags"] = ",".join([t for t in tags if t.strip()])
                req_params["sort"] = extend.get("sort", "T")
                path = "/tv/recommend"
                data_key = "items"
            elif tid in ["rank_list_movie", "rank_list_tv"]:
                # 默认榜单ID对齐JS
                default_rank = {
                    "rank_list_movie": "movie_real_time_hotest",
                    "rank_list_tv": "tv_real_time_hotest"
                }[tid]
                rank_id = extend.get("榜单", default_rank)
                path = f"/subject_collection/{rank_id}/items"
                data_key = "subject_collection_items"
            else:
                return result

            # 拼接请求URL
            query_str = urllib.parse.urlencode(req_params)
            url = f"{DOUBAN_API}{path}?{query_str}"
            rsp = self.fetch(url, headers=self.header, timeout=4000)
            jo = json.loads(rsp.text)
            jolist = jo.get(data_key, [])

            videos = []
            for vod_item in jolist:
                if not self.isReleased(vod_item):
                    continue
                vod = self.buildVod(vod_item)
                if vod["vod_pic"]:
                    videos.append(vod)
            result["list"] = videos
            return result
        except Exception as e:
            return result

    # 详情、播放、搜索 对齐JS空实现
    def detailContent(self, array):
        return []

    def searchContent(self, key, quick, pg=1):
        return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        return {}

    # 请求头 和JS完全一致
    header = {
        "Host": "frodo.douban.com",
        "Connection": "Keep-Alive",
        "Referer": REFERER,
        "User-Agent": USER_AGENT
    }

    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]

    # 筛选配置 完全复制JS filters
    config = {
        "player": {},
        "filter": {
            "hot_movie": [
                {"key": "sort", "name": "排序", "value": [
                    {"n": "热度", "v": "recommend"},
                    {"n": "最新", "v": "time"},
                    {"n": "评分", "v": "rank"}
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": "全部"},
                    {"n": "华语", "v": "华语"},
                    {"n": "欧美", "v": "欧美"},
                    {"n": "韩国", "v": "韩国"},
                    {"n": "日本", "v": "日本"}
                ]}
            ],
            "tv_hot": [
                {"key": "type", "name": "分类", "value": [
                    {"n": "综合", "v": "tv_hot"},
                    {"n": "国产剧", "v": "tv_domestic"},
                    {"n": "欧美剧", "v": "tv_american"},
                    {"n": "日剧", "v": "tv_japanese"},
                    {"n": "韩剧", "v": "tv_korean"},
                    {"n": "动画", "v": "tv_animation"}
                ]}
            ],
            "show_hot": [
                {"key": "type", "name": "分类", "value": [
                    {"n": "综合", "v": "show_hot"},
                    {"n": "国内", "v": "show_domestic"},
                    {"n": "国外", "v": "show_foreign"}
                ]}
            ],
            "movie": [
                {"key": "类型", "name": "类型", "value": [
                    {"n": "全部类型", "v": ""}, {"n": "喜剧", "v": "喜剧"}, {"n": "爱情", "v": "爱情"}, {"n": "动作", "v": "动作"}, {"n": "科幻", "v": "科幻"}, {"n": "动画", "v": "动画"}, {"n": "悬疑", "v": "悬疑"}, {"n": "犯罪", "v": "犯罪"}, {"n": "惊悚", "v": "惊悚"}, {"n": "冒险", "v": "冒险"}, {"n": "音乐", "v": "音乐"}, {"n": "历史", "v": "历史"}, {"n": "奇幻", "v": "奇幻"}, {"n": "恐怖", "v": "恐怖"}, {"n": "战争", "v": "战争"}, {"n": "传记", "v": "传记"}, {"n": "歌舞", "v": "歌舞"}, {"n": "武侠", "v": "武侠"}, {"n": "情色", "v": "情色"}, {"n": "灾难", "v": "灾难"}, {"n": "西部", "v": "西部"}, {"n": "纪录片", "v": "纪录片"}, {"n": "短片", "v": "短片"}
                ]},
                {"key": "地区", "name": "地区", "value": [
                    {"n": "全部地区", "v": ""}, {"n": "华语", "v": "华语"}, {"n": "欧美", "v": "欧美"}, {"n": "韩国", "v": "韩国"}, {"n": "日本", "v": "日本"}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "美国", "v": "美国"}, {"n": "中国香港", "v": "中国香港"}, {"n": "中国台湾", "v": "中国台湾"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"}, {"n": "意大利", "v": "意大利"}, {"n": "西班牙", "v": "西班牙"}, {"n": "印度", "v": "印度"}, {"n": "泰国", "v": "泰国"}, {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "加拿大", "v": "加拿大"}, {"n": "澳大利亚", "v": "澳大利亚"}, {"n": "爱尔兰", "v": "爱尔兰"}, {"n": "瑞典", "v": "瑞典"}, {"n": "巴西", "v": "巴西"}, {"n": "丹麦", "v": "丹麦"}
                ]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "近期热度", "v": "T"}, {"n": "首映时间", "v": "R"}, {"n": "高分优先", "v": "S"}
                ]},
                {"key": "年代", "name": "年代", "value": [
                    {"n": "全部年代", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2010年代", "v": "2010年代"}, {"n": "2000年代", "v": "2000年代"}, {"n": "90年代", "v": "90年代"}, {"n": "80年代", "v": "80年代"}, {"n": "70年代", "v": "70年代"}, {"n": "60年代", "v": "60年代"}, {"n": "更早", "v": "更早"}
                ]}
            ],
            "tv": [
                {"key": "类型", "name": "类型", "value": [
                    {"n": "不限", "v": ""}, {"n": "电视剧", "v": "电视剧"}, {"n": "综艺", "v": "综艺"}
                ]},
                {"key": "电视剧形式", "name": "电视剧形式", "value": [
                    {"n": "不限", "v": ""}, {"n": "喜剧", "v": "喜剧"}, {"n": "爱情", "v": "爱情"}, {"n": "悬疑", "v": "悬疑"}, {"n": "动画", "v": "动画"}, {"n": "武侠", "v": "武侠"}, {"n": "古装", "v": "古装"}, {"n": "家庭", "v": "家庭"}, {"n": "犯罪", "v": "犯罪"}, {"n": "科幻", "v": "科幻"}, {"n": "恐怖", "v": "恐怖"}, {"n": "历史", "v": "历史"}, {"n": "战争", "v": "战争"}, {"n": "动作", "v": "动作"}, {"n": "冒险", "v": "冒险"}, {"n": "传记", "v": "传记"}, {"n": "剧情", "v": "剧情"}, {"n": "奇幻", "v": "奇幻"}, {"n": "惊悚", "v": "惊悚"}, {"n": "灾难", "v": "灾难"}, {"n": "歌舞", "v": "歌舞"}, {"n": "音乐", "v": "音乐"}
                ]},
                {"key": "综艺形式", "name": "综艺形式", "value": [
                    {"n": "不限", "v": ""}, {"n": "真人秀", "v": "真人秀"}, {"n": "脱口秀", "v": "脱口秀"}, {"n": "音乐", "v": "音乐"}, {"n": "歌舞", "v": "歌舞"}
                ]},
                {"key": "地区", "name": "地区", "value": [
                    {"n": "全部地区", "v": ""}, {"n": "华语", "v": "华语"}, {"n": "欧美", "v": "欧美"}, {"n": "国外", "v": "国外"}, {"n": "韩国", "v": "韩国"}, {"n": "日本", "v": "日本"}, {"n": "中国大陆", "v": "中国大陆"}, {"n": "中国香港", "v": "中国香港"}, {"n": "美国", "v": "美国"}, {"n": "英国", "v": "英国"}, {"n": "泰国", "v": "泰国"}, {"n": "中国台湾", "v": "中国台湾"}, {"n": "意大利", "v": "意大利"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"}, {"n": "西班牙", "v": "西班牙"}, {"n": "俄罗斯", "v": "俄罗斯"}, {"n": "瑞典", "v": "瑞典"}, {"n": "巴西", "v": "巴西"}, {"n": "丹麦", "v": "丹麦"}, {"n": "印度", "v": "印度"}, {"n": "加拿大", "v": "加拿大"}, {"n": "爱尔兰", "v": "爱尔兰"}, {"n": "澳大利亚", "v": "Australia"}
                ]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "近期热度", "v": "T"}, {"n": "首播时间", "v": "R"}, {"n": "高分优先", "v": "S"}
                ]},
                {"key": "年代", "name": "年代", "value": [
                    {"n": "全部", "v": ""}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"}, {"n": "2010年代", "v": "2010年代"}, {"n": "2000年代", "v": "2000年代"}, {"n": "90年代", "v": "90年代"}, {"n": "80年代", "v": "80年代"}, {"n": "70年代", "v": "70年代"}, {"n": "60年代", "v": "60年代"}, {"n": "更早", "v": "更早"}
                ]},
                {"key": "平台", "name": "平台", "value": [
                    {"n": "全部", "v": ""}, {"n": "腾讯视频", "v": "腾讯视频"}, {"n": "爱奇艺", "v": "爱奇艺"}, {"n": "优酷", "v": "优酷"}, {"n": "湖南卫视", "v": "湖南卫视"}, {"n": "Netflix", "v": "Netflix"}, {"n": "HBO", "v": "HBO"}, {"n": "BBC", "v": "BBC"}, {"n": "NHK", "v": "NHK"}, {"n": "CBS", "v": "CBS"}, {"n": "NBC", "v": "NBC"}, {"n": "tvN", "v": "tvN"}
                ]}
            ],
            "rank_list_movie": [
                {"key": "榜单", "name": "榜单", "value": [
                    {"n": "实时热门电影", "v": "movie_real_time_hotest"},
                    {"n": "一周口碑电影榜", "v": "movie_weekly_best"},
                    {"n": "豆瓣电影Top250", "v": "movie_top250"}
                ]}
            ],
            "rank_list_tv": [
                {"key": "榜单", "name": "榜单", "value": [
                    {"n": "实时热门电视", "v": "tv_real_time_hotest"},
                    {"n": "华语口碑剧集榜", "v": "tv_chinese_best_weekly"},
                    {"n": "全球口碑剧集榜", "v": "tv_global_best_weekly"},
                    {"n": "国内口碑综艺榜", "v": "show_chinese_best_weekly"},
                    {"n": "国外口碑综艺榜", "v": "show_global_best_weekly"}
                ]}
            ]
        }
    }
