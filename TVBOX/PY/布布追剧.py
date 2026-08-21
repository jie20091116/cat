# -*- coding: utf-8 -*-
"""
TVBox本地Spider脚本，兼容FongMi/PeekPro/WebHomeTV
调用方式：python3 duoduo_spider.py home
         python3 duoduo_spider.py category {"tid":"1","pg":1}
         python3 duoduo_spider.py detail {"ids":"xxx"}
         python3 duoduo_spider.py play {"flag":"多多线路","id":"xxx"}
         python3 duoduo_spider.py search {"key":"xxx","pg":1}
"""
import sys
import json
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional

HEADERS = {
    "User‑Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Referer": "https://323433ssdfd.top/"
}
BASE_URL = "https://323433ssdfd.top/"
TIMEOUT = 15


class Spider:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _resp(self, code: int = 0, msg: str = "", data: Optional[Dict] = None) -> Dict:
        return {
            "code": code,
            "msg": msg,
            "data": data if data is not None else {}
        }

    def home(self) -> Dict:
        """首页 home"""
        try:
            resp = self.session.get(BASE_URL, timeout=TIMEOUT)
            resp.encoding = "utf‑8"
            soup = BeautifulSoup(resp.text, "lxml")

            cls_list = [
                {"type_id": "1", "type_name": "电影"},
                {"type_id": "2", "type_name": "剧集"},
                {"type_id": "3", "type_name": "动漫"},
                {"type_id": "4", "type_name": "综艺"}
            ]
            vod_list = []
            # 示例：需要根据真实页面css选择器修改下面解析部分
            for item in soup.select(".vod-item"):
                a_tag = item.select_one("a")
                if not a_tag:
                    continue
                href = a_tag.get("href", "")
                vod_id = href.split("id=")[-1] if "id=" in href else ""
                title = item.select_one(".vod-name")
                pic = item.select_one("img")
                remark = item.select_one(".vod‑remarks")
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title.get_text(strip=True) if title else "",
                    "vod_pic": pic.get("data‑src", pic.get("src", "")) if pic else "",
                    "vod_remarks": remark.get_text(strip=True) if remark else ""
                })
            home_data = {"class": cls_list, "list": vod_list}
            return self._resp(data=home_data)
        except Exception as e:
            return self._resp(code=-1, msg=f"首页异常:{str(e)}")

    def category(self, tid: str, pg: int) -> Dict:
        """分类页"""
        try:
            url = f"{BASE_URL}index.php/vod/show/id/{tid}/page/{pg}.html"
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.encoding = "utf‑8"
            soup = BeautifulSoup(resp.text, "lxml")
            vod_list = []
            for item in soup.select(".vod-item"):
                a_tag = item.select_one("a")
                if not a_tag:
                    continue
                href = a_tag.get("href", "")
                vod_id = href.split("id=")[-1] if "id=" in href else ""
                title = item.select_one(".vod-name")
                pic = item.select_one("img")
                remark = item.select_one(".vod‑remarks")
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title.get_text(strip=True) if title else "",
                    "vod_pic": pic.get("data‑src", pic.get("src", "")) if pic else "",
                    "vod_remarks": remark.get_text(strip=True) if remark else ""
                })
            cat_data = {
                "page": pg,
                "pagecount": 10,
                "limit": 20,
                "total": 200,
                "list": vod_list
            }
            return self._resp(data=cat_data)
        except Exception as e:
            return self._resp(code=-1, msg=f"分类异常:{str(e)}")

    def detail(self, ids: str) -> Dict:
        """详情页"""
        try:
            url = f"{BASE_URL}index.php/vod/detail/id/{ids}.html"
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.encoding = "utf‑8"
            soup = BeautifulSoup(resp.text, "lxml")
            vod_name = soup.select_one(".vod-title")
            vod_pic = soup.select_one(".vod-pic img")
            vod_content = soup.select_one(".vod-desc")
            vod_remarks = soup.select_one(".vod-update")
            # 集数列表解析，拼装TVBox标准 vod_play_url
            play_items = []
            for ep in soup.select(".play-list a"):
                ep_name = ep.get_text(strip=True)
                ep_href = ep.get("href", "")
                play_items.append(f"{ep_name}${ep_href}")
            play_from = "多多线路"
            play_url = "$$$".join(play_items)
            item = {
                "vod_id": ids,
                "vod_name": vod_name.get_text(strip=True) if vod_name else "",
                "vod_pic": vod_pic.get("src", "") if vod_pic else "",
                "vod_year": "",
                "vod_area": "",
                "vod_remarks": vod_remarks.get_text(strip=True) if vod_remarks else "",
                "vod_content": vod_content.get_text(strip=True) if vod_content else "",
                "vod_play_from": play_from,
                "vod_play_url": play_url
            }
            return self._resp(data={"list": [item]})
        except Exception as e:
            return self._resp(code=-1, msg=f"详情异常:{str(e)}")

    def play(self, flag: str, sid: str) -> Dict:
        """播放解析，sid来自vod_play_url拆分后的片段"""
        try:
            # sid格式示例："第01集$/play/id/xxx.html"
            ep_real_url = sid.split("$")[-1]
            if not ep_real_url.startswith("http"):
                ep_real_url = BASE_URL.rstrip("/") + ep_real_url
            resp = self.session.get(ep_real_url, timeout=TIMEOUT)
            resp.encoding = "utf‑8"
            soup = BeautifulSoup(resp.text, "lxml")
            # 需要自己抓页面里真实m3u8/mp4播放地址，这里占位
            real_play_url = ""
            # 示例正则提取m3u8：re.search(r'https?://[^"\']+\.m3u8', resp.text)
            return self._resp(data={"parse":0, "url": real_play_url})
        except Exception as e:
            return self._resp(code=-1, msg=f"播放解析异常:{str(e)}")

    def search(self, key: str, pg: int) -> Dict:
        """搜索"""
        try:
            url = f"{BASE_URL}index.php/vod/search/page/{pg}/wd/{key}.html"
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.encoding = "utf‑8"
            soup = BeautifulSoup(resp.text, "lxml")
            vod_list = []
            for item in soup.select(".vod-item"):
                a_tag = item.select_one("a")
                if not a_tag:
                    continue
                href = a_tag.get("href","")
                vod_id = href.split("id=")[-1] if "id=" in href else ""
                title = item.select_one(".vod-name")
                pic = item.select_one("img")
                remark = item.select_one(".vod‑remarks")
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title.get_text(strip=True) if title else "",
                    "vod_pic": pic.get("data‑src", pic.get("src","")) if pic else "",
                    "vod_remarks": remark.get_text(strip=True) if remark else ""
                })
            search_data = {
                "page": pg,
                "pagecount": 1,
                "limit": 20,
                "total": len(vod_list),
                "list": vod_list
            }
            return self._resp(data=search_data)
        except Exception as e:
            return self._resp(code=-1, msg=f"搜索异常:{str(e)}")


def main():
    sp = Spider()
    if len(sys.argv) <2:
        print(json.dumps(sp._resp(code=-2, msg="缺少动作参数"), ensure_ascii=False))
        return
    act = sys.argv[1]
    params = {}
    if len(sys.argv)>=3:
        try:
            params = json.loads(sys.argv[2])
        except:
            pass
    res = {}
    if act == "home":
        res = sp.home()
    elif act == "category":
        res = sp.category(tid=str(params.get("tid","1")), pg=int(params.get("pg",1)))
    elif act == "detail":
        res = sp.detail(ids=str(params.get("ids","")))
    elif act == "play":
        res = sp.play(flag=str(params.get("flag","")), sid=str(params.get("id","")))
    elif act == "search":
        res = sp.search(key=str(params.get("key","")), pg=int(params.get("pg",1)))
    else:
        res = sp._resp(code=-3, msg=f"不支持动作：{act}")
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
