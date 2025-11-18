# -*- coding: utf-8 -*-
# by @嗷呜
import json
import re
import sys
from base64 import b64decode, b64encode
from urllib.parse import urlparse

import requests
from pyquery import PyQuery as pq
from requests import Session
sys.path.append('..')
from base.spider import Spider

# 继承基础 Spider 类
class Spider(Spider):

    def init(self, extend=""):
        '''
        初始化方法（配置代理、请求头、session 等）
        extend 传入的 JSON 会作为代理配置

        配置示例：
        {
            "http": "http://127.0.0.1:1072",
            "https": "http://127.0.0.1:1072"
        }
        '''
        # 解析代理参数
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}

        # 默认 headers，用于伪装浏览器
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36',
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'dnt': '1',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'priority': 'u=1, i',
        }

        # 自动检测主域名
        self.host = self.gethost()

        # 加上 referer 和 origin
        self.headers.update({'referer': f'{self.host}/', 'origin': self.host})

        # 创建 session 对象（更快、更稳定）
        self.session = Session()
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)

    # 留空接口（影视仓要求存在）
    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    # 首页分类
    def homeContent(self, filter):
        result = {}

        # 手动定义一级分类
        cateManual = {
            "视频": "/video",
            "片单": "/playlists",
            "频道": "/channels",
            "分类": "/categories",
            "明星": "/pornstars"
        }

        classes = []
        filters = {}

        # 生成结构
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })

        result['class'] = classes
        result['filters'] = filters
        return result

    # 首页推荐视频
    def homeVideoContent(self):
        data = self.getpq('/recommended')
        vhtml = data("#recommendedListings .pcVideoListItem .phimage")
        return {'list': self.getlist(vhtml)}

    # 分类页面
    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

        # ---------------- 视频分类 ----------------
        if tid == '/video' or '_this_video' in tid:
            pagestr = '&' if '?' in tid else '?'
            tid = tid.split('_this_video')[0]
            data = self.getpq(f'{tid}{pagestr}page={pg}')
            vdata = self.getlist(data('#videoCategory .pcVideoListItem'))

        # ---------------- 片单 ----------------
        elif tid == '/playlists':
            data = self.getpq(f'{tid}?page={pg}')
            vhtml = data('#playListSection li')
            for i in vhtml.items():
                vdata.append({
                    'vod_id': 'playlists_click_' + i('.thumbnail-info-wrapper .display-block a').attr('href'),
                    'vod_name': i('.thumbnail-info-wrapper .display-block a').attr('title'),
                    'vod_pic': self.proxy(i('.largeThumb').attr('src')),
                    'vod_tag': 'folder',
                    'vod_remarks': i('.playlist-videos .number').text(),
                    'style': {"type": "rect", "ratio": 1.33}
                })

        # ---------------- 频道 ----------------
        elif tid == '/channels':
            data = self.getpq(f'{tid}?o=rk&page={pg}')
            vhtml = data('#filterChannelsSection li .description')
            for i in vhtml.items():
                vdata.append({
                    'vod_id': 'director_click_' + i('.avatar a').attr('href'),
                    'vod_name': i('.avatar img').attr('alt'),
                    'vod_pic': self.proxy(i('.avatar img').attr('src')),
                    'vod_tag': 'folder',
                    'vod_remarks': i('.descriptionContainer ul li').eq(-1).text(),
                    'style': {"type": "rect", "ratio": 1.33}
                })

        # ---------------- 分类（只第一页） ----------------
        elif tid == '/categories' and pg == '1':
            result['pagecount'] = 1
            data = self.getpq(f'{tid}')
            vhtml = data('.categoriesListSection li .relativeWrapper')
            for i in vhtml.items():
                vdata.append({
                    'vod_id': i('a').attr('href') + '_this_video',
                    'vod_name': i('a').attr('alt'),
                    'vod_pic': self.proxy(i('a img').attr('src')),
                    'vod_tag': 'folder',
                    'style': {"type": "rect", "ratio": 1.33}
                })

        # ---------------- 明星 ----------------
        elif tid == '/pornstars':
            data = self.getpq(f'{tid}?o=t&page={pg}')
            vhtml = data('#popularPornstars .performerCard .wrap')
            for i in vhtml.items():
                vdata.append({
                    'vod_id': 'pornstars_click_' + i('a').attr('href'),
                    'vod_name': i('.performerCardName').text(),
                    'vod_pic': self.proxy(i('a img').attr('src')),
                    'vod_tag': 'folder',
                    'vod_year': i('.performerVideosViewsCount span').eq(0).text(),
                    'vod_remarks': i('.performerVideosViewsCount span').eq(-1).text(),
                    'style': {"type": "rect", "ratio": 1.33}
                })

        # ---------------- 片单内点击 ----------------
        elif 'playlists_click' in tid:
            tid = tid.split('click_')[-1]
            # 第一页需要读取 token
            if pg == '1':
                hdata = self.getpq(tid)
                self.token = hdata('#searchInput').attr('data-token')
                vdata = self.getlist(hdata('#videoPlaylist .pcVideoListItem .phimage'))
            else:
                tid = tid.split('playlist/')[-1]
                data = self.getpq(f'/playlist/viewChunked?id={tid}&token={self.token}&page={pg}')
                vdata = self.getlist(data('.pcVideoListItem .phimage'))

        # ---------------- 频道内点击 ----------------
        elif 'director_click' in tid:
            tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}/videos?page={pg}')
            vdata = self.getlist(data('#showAllChanelVideos .pcVideoListItem .phimage'))

        # ---------------- 明星内点击 ----------------
        elif 'pornstars_click' in tid:
            tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}/videos?page={pg}')
            vdata = self.getlist(data('#mostRecentVideosSection .pcVideoListItem .phimage'))

        result['list'] = vdata
        return result

    # 视频详情页
    def detailContent(self, ids):
        url = f"{self.host}{ids[0]}"
        data = self.getpq(ids[0])

        # 标题
        vn = data('meta[property="og:title"]').attr('content')

        # 作者信息
        dtext = data('.userInfo .usernameWrap a')
        pdtitle = '[a=cr:' + json.dumps(
            {'id': 'director_click_' + dtext.attr('href'), 'name': dtext.text()}) + '/]' + dtext.text() + '[/a]'

        vod = {
            'vod_name': vn,
            'vod_director': pdtitle,
            'vod_remarks': (data('.userInfo').text() + ' / ' + data('.ratingInfo').text()).replace('\n', ' / '),
            'vod_play_from': 'Pornhub',
            'vod_play_url': ''
        }

        # 获取 JS 里的 mediaDefinitions（真实视频地址）
        js_content = data("#player script").eq(0).text()

        # 初始播放列表（失败兜底）
        plist = [f"{vn}${self.e64(f'{1}@@@@{url}')}"]

        try:
            pattern = r'"mediaDefinitions":\s*(\[.*?\]),\s*"isVertical"'
            match = re.search(pattern, js_content, re.DOTALL)
            if match:
                # 解析多个清晰度
                json_str = match.group(1)
                udata = json.loads(json_str)
                plist = [
                    f"{media['height']}${self.e64(f'{0}@@@@{url}')}"
                    for media in udata[:-1]
                    if (url := media.get('videoUrl'))
                ]
        except Exception as e:
            print(f"提取mediaDefinitions失败: {str(e)}")

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    # 关键词搜索
    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f'/video/search?search={key}&page={pg}')
        return {'list': self.getlist(data('#videoSearchResult .pcVideoListItem .phimage'))}

    # 播放器接口
    def playerContent(self, flag, id, vipFlags):
        ids = self.d64(id).split('@@@@')
        if '.m3u8' in ids[1]:
            ids[1] = self.proxy(ids[1], 'm3u8')
        return {'parse': int(ids[0]), 'url': ids[1], 'header': self.headers}

    # 本地代理（m3u8 / ts）
    def localProxy(self, param):
        url = self.d64(param.get('url'))
        if param.get('type') == 'm3u8':
            return self.m3Proxy(url)
        else:
            return self.tsProxy(url)

    # m3u8 代理重写 ts 链接
    def m3Proxy(self, url):
        ydata = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=False)
        data = ydata.content.decode('utf-8')

        # 有跳转 Location
        if ydata.headers.get('Location'):
            url = ydata.headers['Location']
            data = requests.get(url, headers=self.headers, proxies=self.proxies).content.decode('utf-8')

        lines = data.strip().split('\n')

        # 解析域名路径
        last_r = url[:url.rfind('/')]
        parsed_url = urlparse(url)
        durl = parsed_url.scheme + "://" + parsed_url.netloc

        # 重写每个 ts 链接为代理转发
        for index, string in enumerate(lines):
            if '#EXT' not in string:
                if 'http' not in string:
                    domain = last_r if string.count('/') < 2 else durl
                    string = domain + ('' if string.startswith('/') else '/') + string
                lines[index] = self.proxy(string, string.split('.')[-1].split('?')[0])

        data = '\n'.join(lines)
        return [200, "application/vnd.apple.mpegur", data]

    # ts 文件代理
    def tsProxy(self, url):
        data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True)
        return [200, data.headers['Content-Type'], data.content]

    # 自动获取 host（避免被地区跳转）
    def gethost(self):
        try:
            response = requests.get('https://www.pornhub.com', headers=self.headers, proxies=self.proxies,
                                    allow_redirects=False)
            return response.headers['Location'][:-1]
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            return "https://www.pornhub.com"

    # Base64 编码
    def e64(self, text):
        try:
            return b64encode(text.encode('utf-8')).decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    # Base64 解码
    def d64(self, encoded_text):
        try:
            return b64decode(encoded_text.encode('utf-8')).decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    # 统一处理列表视频结构
    def getlist(self, data):
        vlist = []
        for i in data.items():
            vlist.append({
                'vod_id': i('a').attr('href'),
                'vod_name': i('a').attr('title'),
                'vod_pic': self.proxy(i('img').attr('src')),
                'vod_remarks': i('.bgShadeEffect').text() or i('.duration').text(),
                'style': {'ratio': 1.33, 'type': 'rect'}
            })
        return vlist

    # 统一请求 + 解析
    def getpq(self, path):
        try:
            response = self.session.get(f'{self.host}{path}').text
            return pq(response.encode('utf-8'))
        except Exception as e:
            print(f"请求失败: , {str(e)}")
            return None

    # 代理图片/视频（若有代理）
    def proxy(self, data, type='img'):
        if data and len(self.proxies):
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else:
            return data
