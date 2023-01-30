#coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
import json
import math
import re

class Spider(Spider):
	def getName(self):
		return "企鹅体育"
	def init(self,extend=""):
		pass
	def isVideoFormat(self,url):
		pass
	def manualVideoCheck(self):
		pass
	def homeContent(self,filter):
		result = {}
		cateManual = {
			"全部": "",
			"足球": "Football",
			"篮球": "Basketball",
			"NBA": "NBA",
			"台球": "Billiards",
			"搏击": "Fight",
			"网排": "Tennis",
			"游戏": "Game",
			"其他": "Others",
			"橄棒冰": "MLB"
		}
		classes = []
		for k in cateManual:
			classes.append({
				'type_name': k,
				'type_id': cateManual[k]
			})

		result['class'] = classes
		if (filter):
			result['filters'] = self.config['filter']
		return result
	def homeVideoContent(self):
		result = {}
		return result

	def categoryContent(self,tid,pg,filter,extend):
		result = {}
		url = 'https://live.qq.com/api/live/vlist?page_size=60&shortName={0}&page={1}'.format(tid, pg)
		rsp = self.fetch(url)
		content = rsp.text
		jo = json.loads(content)
		videos = []
		vodList = jo['data']['result']
		numvL = len(vodList)
		pgc = math.ceil(numvL/15)
		for vod in vodList:
			aid = (vod['room_id'])
			title = vod['room_name'].strip()
			img = vod['room_src']
			remark = (vod['game_name']).strip()
			videos.append({
				"vod_id": aid,
				"vod_name": title,
				"vod_pic": img,
				"vod_remarks": remark
			})
		result['list'] = videos
		result['page'] = pg
		result['pagecount'] = pgc
		result['limit'] = numvL
		result['total'] = numvL
		return result

	def detailContent(self,array):
		aid = array[0]
		url = "https://m.live.qq.com/{0}".format(aid)
		rsp = self.fetch(url)
		m = re.search(r"ROOM_INFO = (.*);<", rsp.text, re.MULTILINE)
		data = json.loads(m.group(1))
		data['show_status']
		if data['show_status'] == '1':
			title = data['room_name']
			pic = data['room_src']
			typeName = data['game_name']
			remark = data['nickname']
			purl = data['rtmp_url'] + '/' + data['rtmp_live'].replace('wsAuth','txSecret').replace('time','txTime')
		else:
			return {}
		vod = {
			"vod_id": aid,
			"vod_name": title,
			"vod_pic": pic,
			"type_name": typeName,
			"vod_year": "",
			"vod_area": "",
			"vod_remarks": remark,
			"vod_actor": '',
			"vod_director":'',
			"vod_content": ''
		}
		playUrl = '{0}${1}#'.format(typeName, purl)
		vod['vod_play_from'] = '企鹅体育'
		vod['vod_play_url'] = playUrl

		result = {
			'list': [
				vod
			]
		}
		return result

	def searchContent(self,key,quick):
		result = {}
		return result
	def playerContent(self,flag,id,vipFlags):
		result = {}
		url = id
		result["parse"] = 0
		result["playUrl"] = ''
		result["url"] = url
		result["header"] = ''
		return result

	config = {
		"player": {},
		"filter": {}
	}
	header = {}

	def localProxy(self,param):
		action = {
			'url':'',
			'header':'',
			'param':'',
			'type':'string',
			'after':''
		}
		return [200, "video/MP2T", action, ""]