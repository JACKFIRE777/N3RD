# -*- coding: utf-8 -*-
# by @嗷呜（已增强：自动关键词搜索分类版，完整可替换文件）
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
        return "Pornhub"

    def isVideoFormat(self, url):
        # 简单判断视频后缀（可按需扩展）
        if not url:
            return False
        lower = url.lower()
        return any(lower.endswith(ext) for ext in ['.mp4', '.m3u8', '.ts', '.mov', '.webm'])

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    # 首页分类
    def homeContent(self, filter):
        result = {}

        # ---------- 关键词列表：你只需维护这里 ----------
        keyword_list = ["中国", "BLACKED",  "素人", "大屁股"]

        # 手动定义一级分类（基础分类）
        cateManual = {
            "视频": "/video",
            "片单": "/playlists",
            "频道": "/channels",
            "分类": "/categories",
            "明星": "/pornstars"
        }

        # 自动生成“搜索：关键词”分类（免手写多条）
        for kw in keyword_list:
            # 保持和 categoryContent 约定的前缀形式：/search_关键词
            cateManual[f"搜索：{kw}"] = f"/search_{kw}"

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
        if data is None:
            return {'list': []}
        vhtml = data("#recommendedListings .pcVideoListItem .phimage")
        return {'list': self.getlist(vhtml)}

    # 分类页面（含自动搜索分类识别）
    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

        # -------------- 处理以 /search_ 开头的关键词分类 --------------
        # 兼容带不带前导斜杠的两种情况
        if isinstance(tid, str) and (tid.startswith('/search_') or tid.startswith('search_')):
            # 统一去掉前导斜杠与前缀
            keyword = tid.replace('/search_', '').replace('search_', '')
            data = self.getpq(f'/video/search?search={keyword}&page={pg}')
            if data is not None:
                vdata = self.getlist(data('#videoSearchResult .pcVideoListItem .phimage'))
            result['list'] = vdata
            return result

        # ---------------- 视频分类 ----------------
        if tid == '/video' or ('_this_video' in (tid or '')):
            pagestr = '&' if '?' in (tid or '') else '?'
            tid_base = (tid or '').split('_this_video')[0]
            data = self.getpq(f'{tid_base}{pagestr}page={pg}')
            if data is not None:
                vdata = self.getlist(data('#videoCategory .pcVideoListItem'))
        # ---------------- 片单 ----------------
        elif tid == '/playlists':
            data = self.getpq(f'{tid}?page={pg}')
            if data is not None:
                vhtml = data('#playListSection li')
                vdata = []
                for i in vhtml.items():
                    vdata.append({
                        'vod_id': 'playlists_click_' + (i('.thumbnail-info-wrapper .display-block a').attr('href') or ''),
                        'vod_name': i('.thumbnail-info-wrapper .display-block a').attr('title'),
                        'vod_pic': self.proxy(i('.largeThumb').attr('src')),
                        'vod_tag': 'folder',
                        'vod_remarks': i('.playlist-videos .number').text(),
                        'style': {"type": "rect", "ratio": 1.33}
                    })
        # ---------------- 频道 ----------------
        elif tid == '/channels':
            data = self.getpq(f'{tid}?o=rk&page={pg}')
            if data is not None:
                vhtml = data('#filterChannelsSection li .description')
                vdata = []
                for i in vhtml.items():
                    vdata.append({
                        'vod_id': 'director_click_' + (i('.avatar a').attr('href') or ''),
                        'vod_name': i('.avatar img').attr('alt'),
                        'vod_pic': self.proxy(i('.avatar img').attr('src')),
                        'vod_tag': 'folder',
                        'vod_remarks': i('.descriptionContainer ul li').eq(-1).text(),
                        'style': {"type": "rect", "ratio": 1.33}
                    })
        # ---------------- 分类（只第一页） ----------------
        elif tid == '/categories' and str(pg) == '1':
            result['pagecount'] = 1
            data = self.getpq(f'{tid}')
            if data is not None:
                vhtml = data('.categoriesListSection li .relativeWrapper')
                vdata = []
                for i in vhtml.items():
                    vdata.append({
                        'vod_id': (i('a').attr('href') or '') + '_this_video',
                        'vod_name': i('a').attr('alt'),
                        'vod_pic': self.proxy(i('a img').attr('src')),
                        'vod_tag': 'folder',
                        'style': {"type": "rect", "ratio": 1.33}
                    })
        # ---------------- 明星 ----------------
        elif tid == '/pornstars':
            data = self.getpq(f'{tid}?o=t&page={pg}')
            if data is not None:
                vhtml = data('#popularPornstars .performerCard .wrap')
                vdata = []
                for i in vhtml.items():
                    vdata.append({
                        'vod_id': 'pornstars_click_' + (i('a').attr('href') or ''),
                        'vod_name': i('.performerCardName').text(),
                        'vod_pic': self.proxy(i('a img').attr('src')),
                        'vod_tag': 'folder',
                        'vod_year': i('.performerVideosViewsCount span').eq(0).text(),
                        'vod_remarks': i('.performerVideosViewsCount span').eq(-1).text(),
                        'style': {"type": "rect", "ratio": 1.33}
                    })
        # ---------------- 片单内点击 ----------------
        elif 'playlists_click' in (tid or ''):
            tid_real = (tid or '').split('click_')[-1]
            # 第一页需要读取 token
            if str(pg) == '1':
                hdata = self.getpq(tid_real)
                if hdata is not None:
                    self.token = hdata('#searchInput').attr('data-token')
                    vdata = self.getlist(hdata('#videoPlaylist .pcVideoListItem .phimage'))
            else:
                tid_id = tid_real.split('playlist/')[-1]
                data = self.getpq(f'/playlist/viewChunked?id={tid_id}&token={getattr(self, "token", "")}&page={pg}')
                if data is not None:
                    vdata = self.getlist(data('.pcVideoListItem .phimage'))
        # ---------------- 频道内点击 ----------------
        elif 'director_click' in (tid or ''):
            tid_real = (tid or '').split('click_')[-1]
            data = self.getpq(f'{tid_real}/videos?page={pg}')
            if data is not None:
                vdata = self.getlist(data('#showAllChanelVideos .pcVideoListItem .phimage'))
        # ---------------- 明星内点击 ----------------
        elif 'pornstars_click' in (tid or ''):
            tid_real = (tid or '').split('click_')[-1]
            data = self.getpq(f'{tid_real}/videos?page={pg}')
            if data is not None:
                vdata = self.getlist(data('#mostRecentVideosSection .pcVideoListItem .phimage'))

        result['list'] = vdata
        return result

    # 视频详情页（完整实现，解析 mediaDefinitions）
    def detailContent(self, ids):
        url = f"{self.host}{ids[0]}"
        data = self.getpq(ids[0])
        if data is None:
            return {'list': []}

        vn = data('meta[property="og:title"]').attr('content') or ''
        dtext = data('.userInfo .usernameWrap a')
        director_href = dtext.attr('href') if dtext else ''
        director_name = dtext.text() if dtext else ''
        pdtitle = '[a=cr:' + json.dumps(
            {'id': 'director_click_' + director_href, 'name': director_name}) + '/]' + director_name + '[/a]'

        vod = {
            'vod_name': vn,
            'vod_director': pdtitle,
            'vod_remarks': (data('.userInfo').text() + ' / ' + data('.ratingInfo').text()).replace('\n', ' / ') if data('.userInfo') is not None else '',
            'vod_play_from': 'Pornhub',
            'vod_play_url': ''
        }

        # 获取 JS 里的 mediaDefinitions（真实视频地址）
        js_content = ''
        try:
            js_content = data("#player script").eq(0).text()
        except:
            js_content = ''

        # 初始播放列表（失败兜底）
        plist = [f"{vn}${self.e64(f'{1}@@@@{url}')}"]

        try:
            pattern = r'"mediaDefinitions":\s*(\[.*?\]),\s*"isVertical"'
            match = re.search(pattern, js_content, re.DOTALL)
            if match:
                json_str = match.group(1)
                udata = json.loads(json_str)
                # udata 通常是不同清晰度的媒体对象
                plist = []
                for media in udata[:-1]:
                    video_url = media.get('videoUrl')
                    height = media.get('height') or ''
                    if video_url:
                        plist.append(f"{height}${self.e64(f'{0}@@@@{video_url}')}")
        except Exception as e:
            print(f"提取mediaDefinitions失败: {str(e)}")

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    # 关键词搜索（保留原接口形式）
    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f'/video/search?search={key}&page={pg}')
        if data is None:
            return {'list': []}
        return {'list': self.getlist(data('#videoSearchResult .pcVideoListItem .phimage'))}

    # 播放器接口
    def playerContent(self, flag, id, vipFlags):
        ids = self.d64(id).split('@@@@')
        if len(ids) < 2:
            return {'parse': 0, 'url': id, 'header': self.headers}
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
        try:
            ydata = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=False)
            data = ydata.content.decode('utf-8')
            # 有跳转 Location
            if ydata.headers.get('Location'):
                url = ydata.headers['Location']
                data = requests.get(url, headers=self.headers, proxies=self.proxies).content.decode('utf-8')
        except Exception as e:
            print(f"m3Proxy 请求失败: {e}")
            return [500, "text/plain", f"m3Proxy error: {e}"]

        lines = data.strip().split('\n')
        last_r = url[:url.rfind('/')] if '/' in url else url
        parsed_url = urlparse(url)
        durl = parsed_url.scheme + "://" + parsed_url.netloc

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
        try:
            data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True)
            return [200, data.headers.get('Content-Type', 'application/octet-stream'), data.content]
        except Exception as e:
            print(f"tsProxy 请求失败: {e}")
            return [500, "text/plain", f"tsProxy error: {e}"]

    # 自动获取 host（避免被地区跳转）
    def gethost(self):
        try:
            # 直接请求主站，获取最终跳转地址（省略末尾 /）
            response = requests.get('https://www.pornhub.com', headers=self.headers, proxies=self.proxies,
                                    allow_redirects=False, timeout=10)
            loc = response.headers.get('Location')
            if loc:
                return loc[:-1] if loc.endswith('/') else loc
            return "https://www.pornhub.com"
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            return "https://www.pornhub.com"

    # Base64 编码
    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    # Base64 解码
    def d64(self, encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    # 统一处理列表视频结构
    def getlist(self, data):
        vlist = []
        if data is None:
            return vlist
        for i in data.items():
            vid_href = i('a').attr('href') or ''
            # 保持和原来行为一致：vod_id 使用相对路径即可
            vlist.append({
                'vod_id': vid_href,
                'vod_name': i('a').attr('title') or i('img').attr('alt') or '',
                'vod_pic': self.proxy(i('img').attr('src')),
                'vod_remarks': i('.bgShadeEffect').text() or i('.duration').text() or '',
                'style': {'ratio': 1.33, 'type': 'rect'}
            })
        return vlist

    # 统一请求 + 解析（使用 session）
    def getpq(self, path):
        try:
            # path 可能已经是完整 URL，也可能是相对路径
            if path.startswith('http://') or path.startswith('https://'):
                url = path
            else:
                url = f'{self.host}{path}'
            response = self.session.get(url, timeout=15)
            response.encoding = response.apparent_encoding
            return pq(response.text)
        except Exception as e:
            print(f"请求失败: , {str(e)}")
            return None

    # 代理图片/视频（若有代理）
    def proxy(self, data, type='img'):
        if data and isinstance(self.proxies, dict) and len(self.proxies):
            # 依赖外部实现的 getProxyUrl() 方法（通常由基础 spider 提供）
            try:
                return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
            except:
                # 如果没有 getProxyUrl，直接返回原始链接
                return data
        else:
            return data
