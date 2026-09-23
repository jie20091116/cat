# -*- coding:utf-8 -*-
from asyncio import CancelledError
from telethon.errors import FileReferenceExpiredError
from telethon.tl.types import MessageMediaDocument
from telethon import TelegramClient
from typing import Union
import os
import re
import sys
import json
import requests
import subprocess
import platform
import demoji
from tqdm import tqdm
import ssl

# API 密钥
PHONE = os.environ["PHONE"]
API_ID = os.environ["API_ID"]
API_HASH = os.environ["API_HASH"]
GIT_TOKEN = os.environ["GIT_TOKEN"]

ssl._create_default_https_context = ssl._create_unverified_context

keep = ['TG豆瓣', '网盘及彈幕配置', '荐片', '🐼️┃电视┃直播', '115云盘分享', '南瓜', 'TG频道搜索', 'TG群组搜索', '蜡笔|网盘', '小米UC网盘', '小米|网盘', '玩偶哥哥|网盘', '网盘分享合集', '阿里云盘影视分享', '夸克云盘分享', 'UC云盘分享', 'lf_p2p']

class TqdmUpTo(tqdm):
    total = None
    now_size = 0
    bar_format = '{l_bar}{bar}| {n_fmt}/{total_fmt} [已用时：{elapsed}预计剩余：{remaining}, {rate_fmt}{postfix}]'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.unit = 'B'
        self.unit_scale = True
        self.unit_divisor = 1024
        self.bar_format = TqdmUpTo.bar_format

    def update_to(self, current, total):
        """更新进度条
        :param current: 已传输
        :param total: 总大小
        :return:
        """
        self.total = total
        if current != 0:
            self.update(current - self.now_size)
        self.now_size = current
async def GetChatTitle(client: TelegramClient, chat_id: int) -> Union[str, None]:
    entity = await client.get_entity(chat_id)
    return entity.title
async def getHistoryMessage(client: TelegramClient, chat_id: int, from_user=None, limit=10):
    channel_title = await GetChatTitle(client, chat_id)
    if from_user is not None and from_user.isdecimal():
        from_user = int(from_user)
    # 取最近2条消息
    messages = client.iter_messages(chat_id, from_user=from_user, limit=limit)
    return channel_title, messages
async def GetChatId(client: TelegramClient, chat_id: str) -> int:
    # 检测chat_id是id还是昵称
    isId = re.match(r'-?[1-9][0-9]{4,}', chat_id)
    if isId is None:
        entity = await client.get_entity(chat_id)
        chat_id = entity.id
    else:
        chat_id = int(chat_id)
    return chat_id
def shorten_filename(filename, limit=50):
    filename = filename.replace('\n', ' ')
    """返回合适长度文件名，中间用...显示"""
    if len(filename) <= limit:
        return filename
    else:
        return filename[:int(limit / 2) - 3] + '...' + filename[len(filename) - int(limit / 2):]
def GetFileId(message) -> str:
    _id = 'unknown'
    if hasattr(message.media, 'document'):
        _id = message.media.document.id
    elif hasattr(message.media, 'photo'):
        _id = message.media.photo.id
    return str(_id)
def GetFileName(message) -> str:
    # 取名优先级，文件名>描述>ID
    if message.file.name:
        return message.file.name
    file_ext = '.jpg' if message.file.ext in ['.jpe','jpeg'] else message.file.ext
    if len(message.message) != 0:
        sName = shorten_filename(demoji.replace(message.message, '[emoji]'))
        return re.sub(r'[\\/:*?"<>|]', '_', sName) + file_ext
    return GetFileId(message) + file_ext
# fileExist 检查文件是否存在（文件名和大小都相等），如果不存在重名文件加序号
def fileExist(file_path: str, file_size):
    i = 2
    ix = file_path.rfind('.', 1)
    fileName = file_path[:ix]
    fileType = file_path[ix:]
    temp = file_path
    while os.path.exists(temp):
        if os.path.getsize(temp) == file_size:
            return True, temp
        temp = f'{fileName}({i}){fileType}'
        i += 1
    return False, temp
def GetFileSuffix(message) -> list:
    mime_type = 'unknown/unknown'
    if hasattr(message.media, 'document'):
        mime_type = message.media.document.mime_type
    elif hasattr(message.media, 'photo'):
        mime_type = 'image/jpg'
    return mime_type.split('/')
async def download_file(client: TelegramClient, channel_title, channel_id, message, old=False, output='PG'):
    file_name = GetFileName(message)
    file_path = f'{output}/{file_name}'
    file_size = message.file.size
    ret, file_path = fileExist(file_path, file_size)
    if not ret:
        # 已经判断文件不存在，并且保证了文件名不重复
        download_path = file_path + '.downloading'
        print(f"开始下载：{file_name}")
        try:
            with TqdmUpTo(total=file_size, bar_format=TqdmUpTo.bar_format, desc=file_name[:10]) as bar:
                await message.download_media(download_path, progress_callback=bar.update_to)
        except CancelledError:
            print("取消下载")
            os.remove(download_path)
            sys.exit()
        except FileReferenceExpiredError:
            if old:
                print('重试失败，退出下载')
                exit(1)
            print('下载超时，重试中')
            channelData = await client.get_entity(int(channel_id))
            newMessages = client.iter_messages(entity=channelData, ids=message.id)
            async for newMessage in newMessages:
                await download_file(client, channel_title, channel_id, newMessage, old=True)
        except Exception as e:
            print("下载出错", e.__class__.__name__)
            os.remove(download_path)
        else:
            os.rename(download_path, file_path)
    else:
        print(f"文件已存在：{file_path}")


class TGDown:
    def __init__(self,api_id,api_hash,phone,username,repo,token,filter,filter2,local_target=None,channel=None,tdl=False,tip=None):
        self.client = TelegramClient('TG', api_id, api_hash)
        self.phone = phone
        self.registry = 'github.com'
        self.username = username
        self.repo = repo
        self.token = token
        self.branch = 'main'
        self.local_target = local_target
        self.filter = filter
        self.filter2 = filter2
        self.channel = channel
        self.tdl = tdl # 加速下载工具 docs.iyear.me/tdl  先tdl login -T code
        self.tip = tip # 替换set_version里的newname
        self.gh = [
            'https://gh.clun.top/raw.githubusercontent.com',
        ]

    def in_git_exist(self,file):
        is_exist = False
        file_url = f'https://gh.clun.top/raw.githubusercontent.com/{self.username}/{self.repo}/{self.branch}/{file}'
        # 发送 HEAD 请求
        response = requests.head(file_url)
        # 检查响应状态码
        if response.status_code == 200:
            is_exist = True
        return is_exist
    def git_clone(self):
        self.domain = f'https://{self.token}@{self.registry}/{self.username}/{self.repo}.git'
        if os.path.exists(self.repo):
            subprocess.call(['rm', '-rf', self.repo])
        try:
            print(f'开始克隆：git clone https://{self.registry}/{self.username}/{self.repo}.git')
            subprocess.check_call(['git', 'clone', '--depth', '1', self.domain, self.repo])
        except Exception as e:
            try:
                self.registry = 'https://gh.clun.top/'
                self.domain = f'https://{self.token}@{self.registry}/https://github.com/{self.username}/{self.repo}.git'
                if os.path.exists(self.repo):
                    subprocess.call(['rm', '-rf', self.repo])
                subprocess.check_call(['git', 'clone', '--depth', '1', self.domain, self.repo])
            except Exception as e:
                print(222222, e)
    def get_local_repo(self):
        # 设置 git 用户信息
        subprocess.call(['git', 'config', 'user.name', self.username])
        subprocess.call(['git', 'config', 'user.email', self.username])
        os.chdir(self.repo)
        subprocess.call(['git', 'config', 'user.name', self.username])
        subprocess.call(['git', 'config', 'user.email', self.username])
        subprocess.call(['git', 'config', 'http.postBuffer', '104857600'])
        # 获取主分支
        result = subprocess.run(['git', 'branch', '-r'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            name = line.strip()
            if name == 'origin/master' or name == 'origin/main':
                self.branch = name.split('/')[-1]
                break
        return True
    def reset_commit(self, repo):
        # 重置commit
        try:
            os.chdir(self.repo)
            # print('开始清理git',os.getcwd())
            subprocess.call(['git', 'checkout', '--orphan', 'tmp_branch'])
            subprocess.call(['git', 'add', '-A'])
            subprocess.call(['git', 'commit', '-m', 'update'])
            subprocess.call(['git', 'branch', '-D', self.branch])
            subprocess.call(['git', 'branch', '-m', self.branch])
            subprocess.call(['git', 'push', '-f', 'origin', self.branch])
        except Exception as e:
            print('git清理异常', e)
    def git_push(self, repo):
        # 推送并重置commit计数
        print(f'开始推送：git push https://{self.registry}/{self.username}/{self.repo}.git')
        try:
            subprocess.call(['git', 'add', '-A'])
            subprocess.call(['git', 'commit', '-m', 'update'])
            subprocess.call(['git', 'push'])
            self.reset_commit(repo)
        except Exception as e:
            try:
                subprocess.call(['git', 'push', '--set-upstream', 'origin', self.branch])
                self.reset_commit(repo)
            except Exception as e:
                print('git推送异常', e)
    def set_version(self,filename,targetjson):
        newname = self.tip
        if not newname:
            # 去掉前缀 'pg.' 和后缀 '-.zip'，然后替换中间的 '-' 为 ''
            match = re.match(self.filter, filename)
            if match:
                newname = f"{match.group(1)}{match.group(2)}"
        # 载入jsm.json文件
        with open(f'{self.local_target}/{targetjson}', 'r', encoding='utf-8') as file:
            data = json.load(file)
        # logo
        data["logo"] = "https://gh.clun.top/raw.githubusercontent.com/fish2018/lib/refs/heads/main/imgs/pg.gif"
        # 配置parses解析器
        data["parses"] = [
            {
                "name": "聚合",
                "type": 3,
                "url": "Demo"
            },
            {
                "name": "web",
                "type": 3,
                "url": "Web"
            },
            {
                "name": "看看",
                "type": 0,
                "url": "https://jx.m3u8.pw/?url=",
                "ext": {
                    "flag": [
                        "qq",
                        "腾讯",
                        "qiyi",
                        "爱奇艺",
                        "奇艺",
                        "youku",
                        "优酷",
                        "mgtv",
                        "芒果",
                        "imgo",
                        "letv",
                        "乐视",
                        "pptv",
                        "PPTV",
                        "sohu",
                        "bilibili",
                        "哔哩哔哩",
                        "哔哩"
                    ],
                    "header": {
                        "User-Agent": "okhttp/4.1.0"
                    }
                }
            },
            {
                "name": "FreeOK",
                "type": 0,
                "url": "https://play.86516.tk/OKPlayer/?url=",
                "ext": {
                    "flag": [
                        "qq",
                        "腾讯",
                        "qiyi",
                        "爱奇艺",
                        "奇艺",
                        "youku",
                        "优酷",
                        "mgtv",
                        "芒果",
                        "imgo",
                        "letv",
                        "乐视",
                        "pptv",
                        "PPTV",
                        "sohu",
                        "bilibili",
                        "哔哩哔哩",
                        "哔哩"
                    ],
                    "header": {
                        "User-Agent": "okhttp/4.1.0"
                    }
                }
            },
            {
                "name": "free",
                "type": 0,
                "url": "https://h5.freejson.xyz/player/?url=",
                "ext": {
                    "flag": [
                        "qq",
                        "腾讯",
                        "qiyi",
                        "爱奇艺",
                        "奇艺",
                        "youku",
                        "优酷",
                        "mgtv",
                        "芒果",
                        "imgo",
                        "letv",
                        "乐视",
                        "pptv",
                        "PPTV",
                        "sohu",
                        "bilibili",
                        "哔哩哔哩",
                        "哔哩"
                    ],
                    "header": {
                        "User-Agent": "okhttp/4.1.0"
                    }
                }
            }
        ]
        # 配置rules，添加域名
        hosts = ["content.stream-link.org"]
        data["rules"][0]["hosts"].extend(hosts)
        # 配置lives直播
        lives_extend = [
            {
                "name": "stream直播",
                "url": "http://127.0.0.1:10079/p/0/proxy/https://www.stream-link.org/stream-link.m3u",
                "type": 0,
                "ua": "okhttp/3.15",
                "epg": "http://127.0.0.1:10079/p/0/proxy/http://content.stream-link.org/epg/guide.xml/?ch={name}&date={date}",
                "logo": "http://127.0.0.1:10079/p/0/proxy/http://content.stream-link.org/epg/guide.xml/logo/{name}.png"
            }]
        data["lives"] = data["lives"]+lives_extend
        # 查找直播转点播
        live2vod_index = next((index for (index, d) in enumerate(data["sites"]) if d["key"] == "直播转点播"), None)
        if live2vod_index is not None:
            data["sites"][live2vod_index]["ext"] = "../feimaolive.json"
        # 查找115Share
        share115_index = next((index for (index, d) in enumerate(data["sites"]) if d["key"] == "115Share"), None)
        if share115_index is not None:
            data["sites"][share115_index]["ext"] = "./lib/tokenm.json$$$https://ghp.ci/https://raw.githubusercontent.com/fish2018/lib/refs/heads/main/txt/115share.txt$$$db$$$1"
        # 查找 "南瓜" 对象并替换
        nangua_index = next((index for (index, d) in enumerate(data["sites"]) if d["key"] == "NanGua"), None)
        if nangua_index is not None:
            item = {
              "key": "nangua",
              "name": "南瓜",
              "type": 3,
              "playerType": "2",
              "api": "http://js.xn--z7x900a.com/js/ng_open.js"
            }
            data["sites"][nangua_index] = item
        # 查找 "豆瓣" 对象并追加新的对象
        douban_index = next((index for (index, d) in enumerate(data["sites"]) if d["key"] == "豆瓣"), None)
        if douban_index is not None:
            item = {
                "key": "https://github.com/fish2018/PG",
                "name": newname,
                "type": 3,
                "api": "csp_Douban",
                "searchable": 1,
                "changeable": 1,
                "indexs": 1,
                "ext": "./lib/douban.json"
            }
            data["sites"].insert(douban_index + 1, item)
        # 查找"TG豆瓣" 对象并更新 "ext"
        TGDouban_index = next((index for (index, d) in enumerate(data["sites"]) if d["key"] == "TGDouban"), None)
        if TGDouban_index is not None:
            data["sites"][TGDouban_index]["ext"] = {
                    "token":"./lib/tokenm.json",
                    "json":"./lib/tgsearch.json",
                    "keywords":"名称,片名,推荐",
                    "tgsearch_url":"http://127.0.0.1:10199",
                    "tgsearch_media_url":"http://127.0.0.1:10199",
                    "channellist":"alypzyhzq|1000,Mbox115|1000,shares_115|1000,Quark_Share_Channel|1000,Aliyundrive_Share_Channel|1000,wanwansubchat|1000,tgsearchers",
                    "proxy":"noproxy",
                    "douban":"./lib/douban.json",
                    "danmu":False
                }
        # 查找 "TG搜索Local" 对象并更新 "ext"
        tg_localsearch_index = next((index for (index, d) in enumerate(data["sites"]) if d["key"] == "TGYunPanLocal"),None)
        if tg_localsearch_index is not None:
            data["sites"][tg_localsearch_index]["ext"] = {
                    "token":"./lib/tokenm.json",
                    "json":"./lib/tgsearch.json",
                    "keywords":"名称,片名,推荐",
                    "tgsearch_url":"http://127.0.0.1:10199",
                    "tgsearch_media_url":"http://127.0.0.1:10199",
                    "channellist":"guaguale115,dianyingshare,XiangxiuNB,kuakeyun",
                    "proxy":"proxy",
                    "danmu": True
                }
        # 查找 "TG网盘搜索" 对象并更新 "ext"
        tg_search_index = next((index for (index, d) in enumerate(data["sites"]) if d["key"] == "TGYunPan"), None)
        if tg_search_index is not None:
            data["sites"][tg_search_index]["ext"] = {
                    "token":"./lib/tokenm.json",
                    "json":"./lib/tgsearch.json",
                    "keywords":"名称,片名,推荐",
                    "tgsearch_url":"http://127.0.0.1:10199",
                    "tgsearch_media_url":"http://127.0.0.1:10199",
                    "channellist":"XiangxiuNB|1000,Aliyundrive_Share_Channel|1000,Quark_Share_Channel|1000,yunpanshare|1000,Aliyun_4K_Movies|1000,hao115|1000,alyp_4K_Movies|1000",
                    "proxy":"noproxy",
                    "danmu": True
                }
            with open(f'{self.local_target}/{targetjson}', 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            items = [
                {
                    "key": "lf_js_p2p",
                    "name": "lf_p2p",
                    "type": 3,
                    "searchable": 1,
                    "changeable": 1,
                    "quickSearch": 1,
                    "filterable": 1,
                    "api": "https://ghp.ci/https://raw.githubusercontent.com/fish2018/lib/refs/heads/main/js/lf_p2p2_min.js",
                    "ext": "18+"
                },
                {
                    "key": "小米UC",
                    "name": "小米UC网盘",
                    "type": 3,
                    "api": "csp_Wobg",
                    "quickSearch": 1,
                    "changeable": 1,
                    "filterable": 1,
                    "timeout": 60,
                    "ext": "./lib/tokenm.json$$$http://www.mucpan.cc/$$$noproxy$$$1$$$./lib/wogg.json$$$"
                }
            ]
            for item in items:
                data["sites"].insert(tg_search_index + 1, item)
        # 精简排序
        # 用于存放筛选后的结果
        items = data["sites"]
        filtered_items = []
        # 保留第二个元素
        second_item = items[1]
        # 遍历 keep 列表，并根据其中的元素筛选 items 中的数据
        for name in keep:
            for item in items:
                if item['name'] == name:
                    filtered_items.append(item)
                    break
        # 将第二个元素始终放在第二个位置
        if second_item in filtered_items:
            filtered_items.remove(second_item)
        # 在第二个位置插入第二个元素
        filtered_items.insert(1, second_item)
        # 输出最终结果
        data["sites"] = filtered_items
        # 替换壁纸
        data["wallpaper"] = "https://jiduo.serv00.net/image"
        # 将更新后的数据写回jsm.json文件
        with open(f'{self.local_target}/{targetjson}-custom', 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
    def readme(self,pg_zip_name='',tgsearch_zip_name='',pg_message='',tgsearch_message=''):
        readme = f'{self.repo}/README.md'
        # 读取 README.md 文件内容
        with open(readme, 'r') as file:
            content = file.read()

        if pg_zip_name:
            # 替换PG包下载链接
            def replace_urls(match):
                new_urls = [f"{gh_base}/{self.username}/{self.repo}/{self.branch}/{pg_zip_name}" for gh_base in self.gh]
                return '```bash\n' + '\n'.join(new_urls) + '\n```'
            content = re.sub(
                r'```bash\s*\n(.*?)\s*```',
                replace_urls,
                content,
                flags=re.DOTALL
            )
            # 替换PG包更新说明
            def replace_pg_message(match):
                return f"{match.group(1)}{pg_message}{match.group(3)}"
            content = re.sub(
                r'(```text\s*\n)(.*?)(\s*\n```)',
                replace_pg_message,
                content,
                flags=re.DOTALL
            )

        if tgsearch_zip_name:
            # 替换tgsearch包
            def replace_urls(match):
                new_urls = [f"{gh_base}/{self.username}/{self.repo}/{self.branch}/{tgsearch_zip_name}" for gh_base in self.gh]
                return '```shell\n' + '\n'.join(new_urls) + '\n```'
            content = re.sub(
                r'```shell\s*\n(.*?)\s*```',
                replace_urls,
                content,
                flags=re.DOTALL
            )
            # 替换tgsearch包更新说明
            def replace_tgsearch_message(match):
                return f"{match.group(1)}{tgsearch_message}{match.group(3)}"
            content = re.sub(
                r'(```yaml\s*\n)(.*?)(\s*\n```)',
                replace_tgsearch_message,
                content,
                flags=re.DOTALL
            )

        # 写回新的 README.md 文件内容
        with open(readme, 'w') as file:
            file.write(content)

    async def down_group(self, client: TelegramClient, chat_id, from_user=None):
        chat_id = await GetChatId(client, chat_id)
        channel_title, messages = await getHistoryMessage(client, chat_id, from_user=from_user)
        # 正则表达式
        has_clone = False
        pg_hit = False
        tgsearch_hit = False
        pg_zip_name=''
        tgsearch_zip_name=''
        pg_message=''
        tgsearch_message=''
        has_update = False
        async for message in messages:
            if message is None:
                continue
            # 判定消息中是否存在媒体内容 MessageMediaDocument:文件
            if not isinstance(message.media, (MessageMediaDocument)):
                continue
            # 匹配zip，如果是pg，如果是tgsearch，下载
            for pattern in [self.filter,self.filter2]:
                match = re.match(pattern, message.file.name)
                if match:
                    # hit说明已经更新过
                    if (message.file.name.split(".")[0] == 'pg' and pg_hit) or (message.file.name.split(".")[0] == 'tgsearchpack' and tgsearch_hit):
                        print(f'忽略老版本包: {message.file.name}')
                        continue
                    # 检测github上是否已经存在该包
                    is_exist = self.in_git_exist(message.file.name)
                    if is_exist:
                        print(f'{message.file.name} 已经是最新包')
                        # 已经更新过的包标记hit
                        if message.file.name.split(".")[0] == 'pg':
                            pg_hit = True
                        elif message.file.name.split(".")[0] == 'tgsearchpack':
                            tgsearch_hit = True
                    else:
                        print(f'发现更新包：{message.file.name}')
                        has_update = True
                        if not has_clone:
                            self.git_clone()
                            if os.path.exists(self.repo):
                                has_clone = True
                        subprocess.call(f'rm -rf {self.repo}/{message.file.name.split(".")[0]}*.zip', shell=True)
                        if self.tdl:
                            cmd = f'tdl dl -i zip -u https://t.me/{self.channel.split("/")[-1]}/{message.id} -d {self.repo} --template "{{{{ .FileName }}}}"'
                            print(cmd)
                            subprocess.call(f'{cmd}', shell=True)
                        else:
                            await download_file(client, channel_title, chat_id, message, self.repo)
                        print(f'TG群组({channel_title}) - 本地包{message.file.name}下载完成')
                        # 更新本地目录中的pg包并解压
                        if message.file.name.split(".")[0] == 'pg':
                            pg_zip_name = message.file.name
                            pg_message=message.message
                            pg_hit = True
                            if self.local_target:
                                try:
                                    print(f'开始更新{self.local_target}目录PG在线接口到最新版本')
                                    # 修改配置
                                    sed_command = f'sed -i "" "s@http://127.0.0.1:10199/@http://tg.fish2018.us.kg/@g" lib/tokenm.json' if platform.system() == "Darwin" else f'sed -i "s@http://127.0.0.1:10199/@http://tg.fish2018.us.kg/@g" lib/tokenm.json'
                                    subprocess.call(
                                        f'rm -rf {self.local_target}/* && '
                                        f'cp -a {self.repo}/{message.file.name} {self.local_target}/ && '
                                        f'cd {self.local_target} && '
                                        f'unzip -o -q {message.file.name} && '
                                        f'cp -a lib/tokentemplate.json lib/tokenm.json && '
                                        f'rm -rf {message.file.name} && '
                                        f'{sed_command}',
                                        shell=True
                                    )
                                    # 在jsm.json中加入版本号
                                    self.set_version(filename=message.file.name, targetjson='jsm.json')
                                except Exception as e:
                                    print(e)
                        elif message.file.name.split(".")[0] == 'tgsearchpack':
                            tgsearch_zip_name = message.file.name
                            tgsearch_message = message.message
                            tgsearch_hit = True
                            # 更新服务器tgsearch二进制包
                            print(f'更新tgsearch二进制包，重启supervisor')
                            subprocess.call(
                                f'supervisorctl stop tg && '
                                f'cp -a {self.repo}/{tgsearch_zip_name} ./  && '
                                f'unzip -o {tgsearch_zip_name} && '
                                f'rm -rf runtgsearch.sh tgsearch.arm32v7 tgsearch.arm64v8 tgsearch.exe && '
                                f'chmod +x tgsearch.x86_64 && '
                                f'supervisorctl start tg &&'
                                f'rm -rf {tgsearch_zip_name}',
                                shell=True
                            )

        if has_update:
            # 更新README.md
            self.readme(pg_zip_name, tgsearch_zip_name, pg_message, tgsearch_message)
            # 推送
            repo = self.get_local_repo()
            self.git_push(repo)

    def run(self):
        with self.client.start(phone=self.phone):
            self.client.loop.run_until_complete(self.down_group(self.client, self.channel))


if __name__ == '__main__':
    api_id = {API_ID}
    api_hash = '{API_HASH}'
    phone = '{PHONE}'
    channel = 'https://t.me/PandaGroovePG'
    username = 'cluntop' # github username
    repo = 'cluntop.github.io' # github repo
    token = '{GIT_TOKEN}' # github token
    local_target = './' # zip解压提供在线接口的目录
    filter = r"pg\.(\d{8})-(\d{4})\.zip"
    filter2 = r'tgsearchpack\.(\d{8})-(\d{4})\.zip'
    tdl = False # 加速TG文件下载的工具
    tip = None
    TGDown(api_id,api_hash,phone,username,repo,token,filter,filter2,local_target,channel,tdl,tip).run()
