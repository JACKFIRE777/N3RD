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
        extend 传入的 JSON 会作为代理配置
        '''
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

        # 初始化 host 为默认值，在 gethost 中尝试获取真实值
        self.default_host = "https://www.pornhub.com"
        self.host = self.gethost()

        # 加上 referer 和 origin
        self.headers.update({'referer': f'{self.host}/', 'origin': self.host})

        # 创建 session 对象（更快、更稳定）
        self.session = Session()
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)

    # **新增方法：检查并更新 Host**
    def check_host_and_update(self):
        # 如果 host 仍是默认值，或者 session headers 中的 referer/origin 与当前 host 不符，则尝试重新获取
        if self.host == self.default_host or not self.session.headers.get('origin', '').startswith(self.host):
            new_host = self.gethost()
            if new_host and new_host != self.host:
                self.host = new_host
                # 重新更新 session 的 headers
                self.session.headers.update({'referer': f'{self.host}/', 'origin': self.host})
                print(f"Host updated to: {self.host}")

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
        # 销毁 session
        if hasattr(self, 'session'):
            self.session.close()

    # 首页分类
    def homeContent(self, filter):
        # **调用检查**：确保 host 在开始前是正确的
        self.check_host_and_update()
        
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

        # 自动生成“搜索：关键词”分类
        for kw in keyword_list:
            cateManual[f"搜索：{kw}"] = f"/search_{kw}"

        classes = []
        filters = {}

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
        # **调用检查**：确保 host 在开始前是正确的
        self.check_host_and_update()
        
        data = self.getpq('/recommended')
        if data is None:
            return {'list': []}
        vhtml = data("#recommendedListings .pcVideoListItem .phimage")
        # 兼容没有推荐列表的情况（返回 None 或空集）
        if vhtml is None:
            return {'list': []}
        return {'list': self.getlist(vhtml)}

    # 分类页面（含自动搜索分类识别）
    def categoryContent(self, tid, pg, filter, extend):
        # **调用检查**：确保 host 在开始前是正确的
        self.check_host_and_update()
        
        vdata = []
        result = {
            'page': int(pg), # 确保 pg 是整数，虽然作为参数给 getpq 是字符串
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

        # -------------- 处理以 /search_ 开头的关键词分类 --------------
        if isinstance(tid, str) and (tid.startswith('/search_') or tid.startswith('search_')):
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
                for i in vhtml.items():
                    vdata.append({
                        'vod_id': 'playlists_click_' + (i('.thumbnail-info-wrapper .display-block a').attr('href') or ''),
                        'vod_name': i('.thumbnail-info-wrapper .display-block a').attr('title') or '',
                        'vod_pic': self.proxy(i('.largeThumb').attr('src')),
                        'vod_tag': 'folder',
                        'vod_remarks': i('.playlist-videos .number').text() or '',
                        'style': {"type": "rect", "ratio": 1.33}
                    })
        
        # ---------------- 频道 ----------------
        elif tid == '/channels':
            data = self.getpq(f'{tid}?o=rk&page={pg}')
            if data is not None:
                vhtml = data('#filterChannelsSection li .description')
                for i in vhtml.items():
                    vdata.append({
                        'vod_id': 'director_click_' + (i('.avatar a').attr('href') or ''),
                        'vod_name': i('.avatar img').attr('alt') or '',
                        'vod_pic': self.proxy(i('.avatar img').attr('src')),
                        'vod_tag': 'folder',
                        'vod_remarks': i('.descriptionContainer ul li').eq(-1).text() or '',
                        'style': {"type": "rect", "ratio": 1.33}
                    })
        
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
        
        # ---------------- 明星 ----------------
        elif tid == '/pornstars':
            data = self.getpq(f'{tid}?o=t&page={pg}')
            if data is not None:
                vhtml = data('#popularPornstars .performerCard .wrap')
                for i in vhtml.items():
                    vdata.append({
                        'vod_id': 'pornstars_click_' + (i('a').attr('href') or ''),
                        'vod_name': i('.performerCardName').text() or '',
                        'vod_pic': self.proxy(i('a img').attr('src')),
                        'vod_tag': 'folder',
                        'vod_year': i('.performerVideosViewsCount span').eq(0).text() or '',
                        'vod_remarks': i('.performerVideosViewsCount span').eq(-1).text() or '',
                        'style': {"type": "rect", "ratio": 1.33}
                    })
        
        # ---------------- 片单内点击 ----------------
        elif 'playlists_click' in (tid or ''):
            tid_real = (tid or '').split('click_')[-1]
            # 兼容 self.token 可能不存在的情况
            token_val = getattr(self, "token", "")
            
            if str(pg) == '1':
                hdata = self.getpq(tid_real)
                if hdata is not None:
                    # 尝试更新 token
                    token_attr = hdata('#searchInput').attr('data-token')
                    if token_attr:
                        self.token = token_attr
                        token_val = self.token
                    vdata = self.getlist(hdata('#videoPlaylist .pcVideoListItem .phimage'))
            
            # 使用 split 分离 id
            tid_id = tid_real.split('playlist/')[-1].split('?')[0] # 确保只取 ID
            if tid_id and token_val:
                data = self.getpq(f'/playlist/viewChunked?id={tid_id}&token={token_val}&page={pg}')
                if data is not None:
                    # 仅在非第一页或第一页失败时才尝试从 viewChunked 获取数据
                    if str(pg) != '1' or not vdata: 
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

    # 视频详情页
    def detailContent(self, ids):
        # **调用检查**：确保 host 在开始前是正确的
        self.check_host_and_update()
        
        url = f"{self.host}{ids[0]}"
        data = self.getpq(ids[0])
        if data is None:
            return {'list': []}

        vn = data('meta[property="og:title"]').attr('content') or ''
        dtext = data('.userInfo .usernameWrap a')
        director_href = dtext.attr('href') if dtext else ''
        director_name = dtext.text() if dtext else ''
        # 确保 director_href 存在时才生成链接
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

        # 获取 JS 里的 mediaDefinitions（真实视频地址）
        js_content = data("#player script").eq(0).text() if data("#player script").eq(0) else ''

        # 初始播放列表（失败兜底）
        plist = [f"{vn}${self.e64(f'{1}@@@@{url}')}"] # 1 表示不需要解析，直接播放

        try:
            pattern = r'"mediaDefinitions":\s*(\[.*?\]),\s*"isVertical"'
            match = re.search(pattern, js_content, re.DOTALL)
            if match:
                json_str = match.group(1)
                udata = json.loads(json_str)
                plist = []
                # udata[:-1] 排除最后一个可能是 HLS 或其他不直接可用的格式
                for media in udata[:-1]: 
                    video_url = media.get('videoUrl')
                    height = media.get('height') or ''
                    if video_url:
                        # 0 表示需要解析（播放器接口会处理），用 Base64 编码 video_url
                        plist.append(f"{height}P${self.e64(f'{0}@@@@{video_url}')}") 
        except Exception as e:
            print(f"提取mediaDefinitions失败: {str(e)}")

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    # 关键词搜索
    def searchContent(self, key, quick, pg="1"):
        # **调用检查**：确保 host 在开始前是正确的
        self.check_host_and_update()
        
        data = self.getpq(f'/video/search?search={key}&page={pg}')
        if data is None:
            return {'list': []}
        return {'list': self.getlist(data('#videoSearchResult .pcVideoListItem .phimage'))}

    # 播放器接口
    def playerContent(self, flag, id, vipFlags):
        try:
            ids = self.d64(id).split('@@@@')
        except:
            ids = ['1', id] # 无法解码时，使用兜底逻辑

        if len(ids) < 2:
            return {'parse': 0, 'url': id, 'header': self.headers}
        
        parse_type = int(ids[0])
        url_content = ids[1]
        
        # 如果是需要解析的类型（0），且是 m3u8，则走本地代理
        if parse_type == 0 and '.m3u8' in url_content:
            url_content = self.proxy(url_content, 'm3u8')
        # 如果是无需解析的类型（1），则直接返回 URL
        
        return {'parse': parse_type, 'url': url_content, 'header': self.headers}

    # 本地代理（m3u8 / ts）
    def localProxy(self, param):
        url = self.d64(param.get('url'))
        proxy_type = param.get('type')
        if proxy_type == 'm3u8':
            return self.m3Proxy(url)
        elif proxy_type in ['ts', 'jpg', 'jpeg', 'png', 'gif', 'webp']: # 增加了图片类型代理
            return self.tsProxy(url)
        else:
            return [404, "text/plain", "Unsupported proxy type"]

    # m3u8 代理重写 ts 链接
    def m3Proxy(self, url):
        try:
            # 使用 session 确保 headers/proxies 一致
            ydata = self.session.get(url, allow_redirects=False, timeout=10)
            data = ydata.content.decode('utf-8')
            
            # 有跳转 Location
            if ydata.headers.get('Location'):
                url = ydata.headers['Location']
                # 再次请求跳转后的地址
                data = self.session.get(url, timeout=10).content.decode('utf-8')
        except Exception as e:
            print(f"m3Proxy 请求失败: {e}")
            return [500, "text/plain", f"m3Proxy error: {e}"]

        lines = data.strip().split('\n')
        # 修复：确保 url.rfind('/') 能找到
        last_r = url[:url.rfind('/')] if '/' in url and url.rfind('/') != -1 else url
        parsed_url = urlparse(url)
        durl = parsed_url.scheme + "://" + parsed_url.netloc

        for index, string in enumerate(lines):
            if '#EXT' not in string and string.strip(): # 排除 EXT 标签和空行
                if 'http' not in string:
                    # 兼容相对路径和绝对路径
                    domain = last_r if string.count('/') < 2 else durl
                    string = domain + ('' if string.startswith('/') else '/') + string
                
                # 提取文件类型（ts, jpg, png 等）
                file_type = string.split('.')[-1].split('?')[0].lower()
                lines[index] = self.proxy(string, file_type)

        data = '\n'.join(lines)
        return [200, "application/vnd.apple.mpegurl", data] # 修正 Content-Type

    # ts 文件/图片代理
    def tsProxy(self, url):
        try:
            data = self.session.get(url, stream=True, timeout=15)
            # 使用 data.headers.get 避免 KeyError
            content_type = data.headers.get('Content-Type', 'application/octet-stream')
            return [200, content_type, data.content]
        except Exception as e:
            print(f"tsProxy 请求失败: {e}")
            return [500, "text/plain", f"tsProxy error: {e}"]

    # 自动获取 host（避免被地区跳转）
    def gethost(self):
        try:
            # 增加 headers，使用 requests 库而不是 session，避免循环依赖
            response = requests.get(self.default_host, headers=self.headers, proxies=self.proxies,
                                    allow_redirects=False, timeout=10)
            loc = response.headers.get('Location')
            if loc:
                return loc[:-1] if loc.endswith('/') else loc
            return self.default_host
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            return self.default_host

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
        if data is None:
            return vlist
        for i in data.items():
            # 健壮性增强：确保 attr 返回值不为 None
            vid_href = i('a').attr('href') or ''
            vod_name = i('a').attr('title') or i('img').attr('alt') or ''
            vod_remarks = i('.bgShadeEffect').text() or i('.duration').text() or ''
            
            # 只有当有 vod_id 时才添加
            if vid_href:
                vlist.append({
                    'vod_id': vid_href,
                    'vod_name': vod_name,
                    'vod_pic': self.proxy(i('img').attr('src')),
                    'vod_remarks': vod_remarks,
                    'style': {'ratio': 1.33, 'type': 'rect'}
                })
        return vlist

    # 统一请求 + 解析（使用 session）
    def getpq(self, path):
        try:
            # 确保使用 session
            if path.startswith('http://') or path.startswith('https://'):
                url = path
            else:
                url = f'{self.host}{path}'
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status() # 抛出 HTTP 错误，提高健壮性
            
            # 尝试使用内容编码，但优先使用 apparent_encoding
            response.encoding = response.apparent_encoding 
            return pq(response.text)
        except Exception as e:
            print(f"请求失败: {url}, {str(e)}")
            return None

    # 代理图片/视频（若有代理）
    def proxy(self, data, type='img'):
        if data and isinstance(self.proxies, dict) and len(self.proxies):
            try:
                # 尝试调用基础类的 getProxyUrl
                return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
            except:
                # 如果调用失败，则返回原始链接
                return data
        else:
            return data
