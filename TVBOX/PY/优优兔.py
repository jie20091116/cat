# OK影视专用爬虫插件 - 优优兔（三列布局优化版）
import sys
import re
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
requests.packages.urllib3.disable_warnings()

from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "优优兔"

    def init(self, extend=""):
        super().init(extend)
        self.site_url = "https://api.uutu.top"
        self.headers = {
            "user-agent": "YouYouTu/1.0 Mobile",
            "x-device-fingerprint": "1d13acddbcdd215dea1d7f6197101ec23b0deb0ddd6620c9d76b71b456630426",
            "x-app-version-code": "163",
            "x-app-version-name": "1.6.3",
            "x-client-platform": "mobile",
            "x-app-pkg": "com.yf.lelian.uututv"
        }
        self.sess = requests.Session()
        self.sess.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])))
        self.sess.mount("http://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])))
        self.refresh_token()

    def refresh_token(self):
        refresh_url = self.site_url + "/api/v1/auth/refresh"
        body = json.dumps({
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjozNiwidXNlcm5hbWUiOiJndWVzdF8xZDEzYWNkZGJjZGQyMTVkZWExZDdmNjE5NyIsImRldmljZV9mcCI6IjFkMTNhY2RkYmNkZDIxNWRlYTFkN2Y2MTk3MTAxZWMyM2IwZGViMGRkZDY2MjBjOWQ3NmI3MWI0NTY2MzA0MjYiLCJleHAiOjE3ODQ5NzUyMDgsImlhdCI6MTc4NDM3MDQwOH0.XfYPY5alehhYJmPji_LZa0PrAppwwTQF7_t52-FAC84",
            "device_fingerprint": "1d13acddbcdd215dea1d7f6197101ec23b0deb0ddd6620c9d76b71b456630426"
        })
        temp_headers = self.headers.copy()
        temp_headers["Content-Type"] = "application/json"
        try:
            res = self.sess.post(refresh_url, headers=temp_headers, data=body, timeout=10, verify=False)
            if res.status_code == 200:
                data = res.json()
                if data.get("data") and data["data"].get("access_token"):
                    self.headers["authorization"] = "Bearer " + data["data"]["access_token"]
                    return
        except Exception:
            pass
        self.headers["authorization"] = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjozNiwidXNlcm5hbWUiOiJndWVzdF8xZDEzYWNkZGJjZGQyMTVkZWExZDdmNjE5NyIsImRldmljZV9mcCI6IjFkMTNhY2RkYmNkZDIxNWRlYTFkN2Y2MTk3MTAxZWMyM2IwZGViMGRkZDY2MjBjOWQ3NmI3MWI0NTY2MzA0MjYiLCJzdWIiOiIzNiIsImV4cCI6MTc4NDM3NzcwOSwiaWF0IjoxNzg0MzcwNTA5fQ.AvziKla_h2yQQGsmwn6r12AHwx12xoY8U7wkSZhAHDA"

    def fetch(self, url, timeout=10):
        try:
            res = self.sess.get(url, headers=self.headers, timeout=timeout, verify=False)
            if res.status_code == 401:
                self.refresh_token()
                res = self.sess.get(url, headers=self.headers, timeout=timeout, verify=False)
            return res
        except Exception:
            return None

    def homeContent(self, filter):
        cate_list = []
        names = "电视剧&电影&动漫&综艺&少儿&纪录片&短剧".split("&")
        ids = "20&21&22&23&24&25&26".split("&")
        for name, tid in zip(names, ids):
            cate_list.append({"type_name": name, "type_id": tid})
        cate_list.append({"type_name": "🔥热门推荐", "type_id": "hot"})
        return {"class": cate_list}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        video_list = []
        if tid == "hot":
            url = self.site_url + "/api/v1/rank/search-hot?type_id=0"
            res = self.fetch(url)
            if res and res.ok:
                data = res.json()
                for item in data.get("data", {}).get("list", []):
                    vod = item.get("vod")
                    if vod:
                        video_list.append({
                            "vod_id": str(vod.get("vod_id", "")),
                            "vod_name": vod.get("vod_name", ""),
                            "vod_pic": vod.get("vod_pic", ""),
                            "vod_remarks": vod.get("vod_remarks", ""),
                            "style": {"type": "rect", "ratio": 0.75}   # 三列布局
                        })
        else:
            url = f"{self.site_url}/api/v1/video/list?type_id={tid}&page={pg}&size=18&order=hits"
            res = self.fetch(url)
            if res and res.ok:
                data = res.json()
                for item in data.get("data", {}).get("list", []):
                    video_list.append({
                        "vod_id": str(item.get("vod_id", "")),
                        "vod_name": item.get("vod_name", ""),
                        "vod_pic": item.get("vod_pic", ""),
                        "vod_remarks": item.get("vod_remarks", ""),
                        "style": {"type": "rect", "ratio": 0.75}
                    })
        pagecount = pg + 1 if len(video_list) else pg
        return {
            "list": video_list,
            "page": pg,
            "pagecount": pagecount,
            "limit": 18,
            "total": 9999
        }

    def detailContent(self, ids):
        vod_id = ids[0] if ids else ""
        if not vod_id:
            return {"list": [{"vod_name": "视频ID为空"}]}
        url = f"{self.site_url}/api/v1/video/{vod_id}"
        res = self.fetch(url)
        if not (res and res.ok):
            return {"list": [{"vod_id": vod_id, "vod_name": "详情加载失败"}]}
        data = res.json().get("data")
        if not data:
            return {"list": [{"vod_name": "未找到视频"}]}

        detail = {
            "vod_id": str(data.get("vod_id", "")),
            "vod_name": data.get("vod_name", ""),
            "vod_pic": data.get("vod_pic", ""),
            "type_name": data.get("type_name", ""),
            "vod_year": data.get("vod_year", ""),
            "vod_area": data.get("vod_area", ""),
            "vod_remarks": data.get("vod_remarks", ""),
            "vod_actor": data.get("vod_actor", ""),
            "vod_director": data.get("vod_director", ""),
            "vod_content": data.get("vod_content") or data.get("vod_blurb", "")
        }

        play_from = []
        play_url = []
        for source in data.get("play_sources", []):
            name = source.get("name", "")
            from_id = source.get("from", "")
            episodes = source.get("episodes", [])
            if not name or not episodes:
                continue
            play_from.append(name)
            ep_parts = []
            for idx, ep in enumerate(episodes):
                ep_name = ep.get("name", "")
                ep_parts.append(f"{ep_name}${vod_id}::{from_id}::{idx}")
            play_url.append("#".join(ep_parts))

        detail["vod_play_from"] = "$$$".join(play_from)
        detail["vod_play_url"] = "$$$".join(play_url)
        return {"list": [detail]}

    def searchContent(self, key, quick, pg=1):
        pg = int(pg) if str(pg).isdigit() else 1
        url = f"{self.site_url}/api/v1/search?q={requests.utils.quote(key)}&page={pg}&size=40"
        res = self.fetch(url)
        video_list = []
        if res and res.ok:
            data = res.json()
            for item in data.get("data", {}).get("list", []):
                video_list.append({
                    "vod_id": str(item.get("vod_id", "")),
                    "vod_name": item.get("vod_name", ""),
                    "vod_pic": item.get("vod_pic", ""),
                    "vod_remarks": item.get("vod_remarks", ""),
                    "style": {"type": "rect", "ratio": 0.75}
                })
        pagecount = pg + 1 if len(video_list) else pg
        return {
            "list": video_list,
            "page": pg,
            "pagecount": pagecount,
            "limit": 40,
            "total": len(video_list) if len(video_list) < 9999 else 9999
        }

    def playerContent(self, flag, id, vipFlags):
        parts = id.split("::")
        if len(parts) != 3:
            return {"parse": 0, "url": "", "header": self.headers}
        vod_id, source, epIdx = parts
        url = f"{self.site_url}/api/v1/play/url?vod_id={vod_id}&source={source}&episode={epIdx}"
        res = self.fetch(url)
        if res and res.ok:
            data = res.json()
            play_url = data.get("data", {}).get("play_url", "")
            if play_url:
                return {"parse": 0, "url": play_url, "header": self.headers}
        return {"parse": 0, "url": "", "header": self.headers}

    def homeVodContent(self):
        url = self.site_url + "/api/v1/rank/search-hot?type_id=0"
        res = self.fetch(url)
        video_list = []
        if res and res.ok:
            data = res.json()
            for item in data.get("data", {}).get("list", []):
                vod = item.get("vod")
                if vod:
                    video_list.append({
                        "vod_id": str(vod.get("vod_id", "")),
                        "vod_name": vod.get("vod_name", ""),
                        "vod_pic": vod.get("vod_pic", ""),
                        "vod_remarks": vod.get("vod_remarks", ""),
                        "style": {"type": "rect", "ratio": 0.75}   # 三列布局
                    })
        return video_list