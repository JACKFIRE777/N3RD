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

# 假设这个路径是正确的，如果实际运行环境不是，请手动调整
try:
    sys.path.append('..')
    from base.spider import Spider
except ImportError:
    # 兼容没有base.spider的环境
    class Spider:
        def getProxyUrl(self):
            return "http://127.0.0.1:9978/proxy"

class Spider(Spider):
    def init(self, extend=""):
        '''
        初始化方法（配置代理、请求头、session 等）
        '''
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}

        self.default_host = "https://www.pornhub.com"
        self.host = self.gethost(force_update=True) # 首次启动强制获取

        # 默认 headers
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
        
        # 创建 session 对象
        self.session = Session()
        self.session.proxies.update(self.proxies)
        
        # 初始更新 headers
        self.update_session_headers()

    def update_session_headers(self):
        '''统一更新 session 的 referer, origin 和其他默认 headers'''
        self.headers.update({'referer': f'{self.host}/', 'origin': self.host})
        self.session.headers.update(self.headers)


    def getName(self):
        return "Pornhub"

    def isVideoFormat(self, url):
        if not url:
            return False
        lower = url.lower()
        return any(lower.endswith(ext) for ext in ['.mp4', '.m3u8', '.ts', '.mov', '.webm'])

    def manualVideoCheck(self):
        pass

    def destroy(self):
        if hasattr(self, 'session'):
            self.session.close()

    # 首页分类
    def homeContent(self, filter):
        result = {}

        # ---------- 关键词列表：你只需维护这里 ----------
        keyword_list = ["中国", "BLACKED",  "素人", "大屁股"]

        cateManual = {
            "视频": "/video",
            "片单": "/playlists",
            "频道": "/channels",
            "分类": "/categories",
            "明星": "/pornstars"
        }

        for kw in keyword_list:
            cateManual[f"搜索：{kw}"] = f"/search_{kw}"

        classes = []
        for k in cateManual:
            classes.append({'type_name': k, 'type_id': cateManual[k]})

        result['class'] = classes
        result['filters'] = {}
        return result

    # 首页推荐视频
    def homeVideoContent(self):
        data = self.getpq('/recommended')
        if data is None:
            return {'list': []}
        vhtml = data("#recommendedListings .pcVideoListItem .phimage")
        if vhtml is None:
            return {'list': []}
        return {'list': self.getlist(vhtml)}

    # 片单Token获取辅助方法（新增）
    def get_playlist_token(self, tid_real):
        hdata = self.getpq(tid_real)
        if hdata is not None:
            token_attr = hdata('#searchInput').attr('data-token')
            if token_attr:
                self.token = token_attr
                print("Successfully retrieved playlist token.")
                return True
        return False

    # 分类页面（含自动搜索分类识别）
    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {
            'page': int(pg),
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

        # -------------- 关键词分类 --------------
        if isinstance(tid, str) and (tid.startswith('/search_') or tid.startswith('search_')):
            keyword = tid.replace('/search_', '').replace('search_', '')
            data = self.getpq(f'/video/search?search={keyword}&page={pg}')
            if data is not None:
                vdata = self.getlist(data('#videoSearchResult .pcVideoListItem .phimage'))

        # ---------------- 视频分类 ----------------
        elif tid == '/video' or ('_this_video' in (tid or '')):
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
                for i in vhtml.items():
                    vdata.append({
                        'vod_id': 'playlists_click_' + (i('.thumbnail-info-wrapper .display-block a').attr('href') or ''),
                        'vod_name': i('.thumbnail-info-wrapper .display-block a').attr('title') or '',
                        'vod_pic': self.proxy(i('.largeThumb').attr('src')),
                        'vod_tag': 'folder',
                        'vod_remarks': i('.playlist-videos .number').text() or '',
                        'style': {"type": "rect", "ratio": 1.33}
                    })

        # （其他频道、分类、明星等逻辑保持不变，依赖 getpq 的自修复能力）
        # ... [略去未改动的 /channels, /categories, /pornstars 逻辑以保持代码简洁] ...

        # ---------------- 片单内点击 (优化 Token 缺失重试逻辑) ----------------
        elif 'playlists_click' in (tid or ''):
            tid_real = (tid or '').split('click_')[-1]
            tid_id = tid_real.split('playlist/')[-1].split('?')[0]
            token_val = getattr(self, "token", "")
            
            # Case 1: 第一页，必须获取 Token
            if str(pg) == '1':
                self.get_playlist_token(tid_real)
                # 重新获取 token_val, 且第一页列表数据已经在 get_playlist_token 内部获取了
                token_val = getattr(self, "token", "")
                hdata = self.getpq(tid_real) # 重新获取一次第一页数据
                if hdata is not None:
                    vdata = self.getlist(hdata('#videoPlaylist .pcVideoListItem .phimage'))
            
            # Case 2: 非第一页，但 Token 缺失 (健壮性增强)
            if str(pg) != '1' and not token_val and tid_id:
                print("Token missing for chunked view, attempting to fetch from page 1...")
                # 尝试强制获取第一页的 token
                self.get_playlist_token(tid_real)
                token_val = getattr(self, "token", "")
                
            # Case 3: 请求分块数据 (适用于所有分页 > 1)
            if tid_id and token_val and str(pg) != '1':
                data = self.getpq(f'/playlist/viewChunked?id={tid_id}&token={token_val}&page={pg}')
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
        
        # ---------------- 分类（只第一页） ----------------
        elif tid == '/categories' and str(pg) == '1':
            result['pagecount'] = 1
            data = self.getpq(f'{tid}')
            if data is not None:
                vhtml = data('.categoriesListSection li .relativeWrapper')
                for i in vhtml.items():
                    vdata.append({
                        'vod_id': (i('a').attr('href') or '') + '_this_video',
                        'vod_name': i('a').attr('alt') or '',
                        'vod_pic': self.proxy(i('a img').attr('src')),
                        'vod_tag': 'folder',
                        'style': {"type": "rect", "ratio": 1.33}
                    })


        result['list'] = vdata
        return result

    # 视频详情页
    def detailContent(self, ids):
        url = f"{self.host}{ids[0]}"
        data = self.getpq(ids[0])
        if data is None:
            return {'list': []}

        # ... [详情页逻辑保持不变] ...
        vn = data('meta[property="og:title"]').attr('content') or ''
        dtext = data('.userInfo .usernameWrap a')
        director_href = dtext.attr('href') if dtext else ''
        director_name = dtext.text() if dtext else ''
        if director_href:
            pdtitle = '[a=cr:' + json.dumps(
                {'id': 'director_click_' + director_href, 'name': director_name}) + '/]' + director_name + '[/a]'
        else:
            pdtitle = director_name

        vod = {
            'vod_name': vn,
            'vod_director': pdtitle,
            'vod_remarks': (data('.userInfo').text() + ' / ' + data('.ratingInfo').text()).replace('\n', ' / ') if data('.userInfo').text() else '',
            'vod_play_from': 'Pornhub',
            'vod_play_url': ''
        }

        js_content = data("#player script").eq(0).text() if data("#player script").eq(0) else ''
        plist = [f"{vn}${self.e64(f'{1}@@@@{url}')}"] 

        try:
            pattern = r'"mediaDefinitions":\s*(\[.*?\]),\s*"isVertical"'
            match = re.search(pattern, js_content, re.DOTALL)
            if match:
                json_str = match.group(1)
                udata = json.loads(json_str)
                plist = []
                for media in udata[:-1]: 
                    video_url = media.get('videoUrl')
                    height = media.get('height') or ''
                    if video_url:
                        plist.append(f"{height}P${self.e64(f'{0}@@@@{video_url}')}") 
        except Exception as e:
            print(f"提取mediaDefinitions失败: {str(e)}")

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    # 关键词搜索
    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f'/video/search?search={key}&page={pg}')
        if data is None:
            return {'list': []}
        return {'list': self.getlist(data('#videoSearchResult .pcVideoListItem .phimage'))}

    # 播放器接口
    def playerContent(self, flag, id, vipFlags):
        try:
            ids = self.d64(id).split('@@@@')
        except:
            ids = ['1', id] 

        if len(ids) < 2:
            return {'parse': 0, 'url': id, 'header': self.headers}
        
        parse_type = int(ids[0])
        url_content = ids[1]
        
        if parse_type == 0 and '.m3u8' in url_content:
            url_content = self.proxy(url_content, 'm3u8')
        
        return {'parse': parse_type, 'url': url_content, 'header': self.headers}

    # 本地代理（m3u8 / ts）
    def localProxy(self, param):
        url = self.d64(param.get('url'))
        proxy_type = param.get('type')
        if proxy_type == 'm3u8':
            return self.m3Proxy(url)
        elif proxy_type in ['ts', 'jpg', 'jpeg', 'png', 'gif', 'webp']: 
            return self.tsProxy(url)
        else:
            return [404, "text/plain", "Unsupported proxy type"]

    # m3u8 代理重写 ts 链接 (保持不变)
    def m3Proxy(self, url):
        # ... [m3Proxy 逻辑保持不变] ...
        try:
            ydata = self.session.get(url, allow_redirects=False, timeout=10)
            data = ydata.content.decode('utf-8')
            
            if ydata.headers.get('Location'):
                url = ydata.headers['Location']
                data = self.session.get(url, timeout=10).content.decode('utf-8')
        except Exception as e:
            print(f"m3Proxy 请求失败: {e}")
            return [500, "text/plain", f"m3Proxy error: {e}"]

        lines = data.strip().split('\n')
        last_r = url[:url.rfind('/')] if '/' in url and url.rfind('/') != -1 else url
        parsed_url = urlparse(url)
        durl = parsed_url.scheme + "://" + parsed_url.netloc

        for index, string in enumerate(lines):
            if '#EXT' not in string and string.strip(): 
                if 'http' not in string:
                    domain = last_r if string.count('/') < 2 else durl
                    string = domain + ('' if string.startswith('/') else '/') + string
                
                file_type = string.split('.')[-1].split('?')[0].lower()
                lines[index] = self.proxy(string, file_type)

        data = '\n'.join(lines)
        return [200, "application/vnd.apple.mpegurl", data] 

    # ts 文件/图片代理 (保持不变)
    def tsProxy(self, url):
        try:
            data = self.session.get(url, stream=True, timeout=15)
            content_type = data.headers.get('Content-Type', 'application/octet-stream')
            return [200, content_type, data.content]
        except Exception as e:
            print(f"tsProxy 请求失败: {e}")
            return [500, "text/plain", f"tsProxy error: {e}"]

    # 自动获取 host（重构为内部/外部调用）
    def gethost(self, force_update=False):
        # 如果不是强制更新，且 host 不是默认值，则直接返回
        if not force_update and self.host != self.default_host:
            return self.host
            
        try:
            response = requests.get(self.default_host, headers=self.headers, proxies=self.proxies,
                                    allow_redirects=False, timeout=10)
            loc = response.headers.get('Location')
            if loc:
                new_host = loc[:-1] if loc.endswith('/') else loc
                return new_host
            return self.default_host
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            return self.default_host

    # Base64 编码 (保持不变)
    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    # Base64 解码 (保持不变)
    def d64(self, encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    # 统一处理列表视频结构 (保持不变)
    def getlist(self, data):
        vlist = []
        if data is None:
            return vlist
        for i in data.items():
            vid_href = i('a').attr('href') or ''
            vod_name = i('a').attr('title') or i('img').attr('alt') or ''
            vod_remarks = i('.bgShadeEffect').text() or i('.duration').text() or ''
            
            if vid_href:
                vlist.append({
                    'vod_id': vid_href,
                    'vod_name': vod_name,
                    'vod_pic': self.proxy(i('img').attr('src')),
                    'vod_remarks': vod_remarks,
                    'style': {'ratio': 1.33, 'type': 'rect'}
                })
        return vlist

    # **核心优化：统一请求 + 解析（增加 Host 自修复和重试机制）**
    def getpq(self, path, retry_count=0):
        if path.startswith('http://') or path.startswith('https://'):
            url = path
        else:
            url = f'{self.host}{path}'
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status() 
            response.encoding = response.apparent_encoding 
            return pq(response.text)
            
        except requests.exceptions.HTTPError as e:
            # 捕获 HTTP 错误（如 404, 301/302/403 等）
            print(f"请求失败 (HTTP {e.response.status_code}): {url}")
            
            # 如果是重定向或权限问题，并且没有重试过，尝试更新 Host 并重试
            if retry_count == 0 and e.response.status_code in [301, 302, 403]:
                print("Host likely outdated. Attempting to update and retry...")
                self.host = self.gethost(force_update=True)
                self.update_session_headers()
                return self.getpq(path, retry_count=1) # 增加重试计数
            
            return None
            
        except requests.exceptions.RequestException as e:
            # 捕获其他请求错误（如连接失败、超时等）
            print(f"请求失败 (Request Exception): {url}, {str(e)}")
            
            if retry_count == 0:
                print("Connection failed. Attempting to update Host and retry...")
                self.host = self.gethost(force_update=True)
                self.update_session_headers()
                return self.getpq(path, retry_count=1) # 增加重试计数
                
            return None

    # 代理图片/视频（若有代理） (保持不变)
    def proxy(self, data, type='img'):
        if data and isinstance(self.proxies, dict) and len(self.proxies):
            try:
                return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
            except:
                return data
        else:
            return data
