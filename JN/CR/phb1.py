# -*- coding: utf-8 -*-
# by @嗷呜（最终决战版：修复 JS/CDN 质询导致的“假”200 错误）
import json
import re
import sys
from base64 import b64decode, b64encode
# 引入 quote 用于 URL 编码
from urllib.parse import urlparse, quote

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
            return "http://1.2.3.4:5555" # 示例

# 继承基础 Spider 类
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
        self.token = "" # 初始化 token，用于片单分页

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
        
        # 1. 先创建 session，并配置好代理
        self.session = Session()
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers) # 先载入基础 headers
        
        # 2. 调用 gethost (它将使用已配置好代理的 self.session)
        self.host = self.gethost(force_update=True) 
        
        # 3. 用获取到的 self.host 更新 session 的 referer/origin
        self.update_session_headers()

    def update_session_headers(self):
        '''统一更新 session 的 referer, origin 和其他默认 headers'''
        self.headers.update({'referer': f'{self.host}/', 'origin': self.host})
        self.session.headers.update(self.headers)

    # 留空接口（影视仓要求存在）
    def getName(self):
        return "Pornhub"

    def isVideoFormat(self, url):
        if not url: return False
        lower = url.lower()
        return any(lower.endswith(ext) for ext in ['.mp4', '.m3u8', '.ts', '.mov', '.webm'])

    def manualVideoCheck(self):
        pass

    def destroy(self):
        if hasattr(self, 'session'):
            self.session.close()

    # 首页分类 (增加关键词功能)
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

        # 自动生成“搜索：关键词”分类
        for kw in keyword_list:
            # 使用 URL 编码，以防中文关键词出错，并统一使用 /video/search?search= 的结构
            encoded_kw = quote(kw)
            cateManual[f"搜索：{kw}"] = f"/video/search?search={encoded_kw}"

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
        # 兼容性选择器：使用 .videoUList 确保找到推荐列表
        vhtml = data(".videoUList .pcVideoListItem .phimage")
        if vhtml is None:
            return {'list': []}
        return {'list': self.getlist(vhtml)}

    # 片单Token获取辅助方法
    def get_playlist_token(self, tid_real):
        hdata = self.getpq(tid_real)
        if hdata is not None:
            token_attr = hdata('#searchInput').attr('data-token') or hdata('body').attr('data-token')
            if token_attr:
                self.token = token_attr
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

        # -------------- 关键词搜索分类 --------------
        if isinstance(tid, str) and tid.startswith('/video/search?'):
            url_path = f'{tid}&page={pg}'
            data = self.getpq(url_path)
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
                    href = i('.thumbnail-info-wrapper .display-block a').attr('href') or ''
                    name = i('.thumbnail-info-wrapper .display-block a').attr('title') or ''
                    if href:
                        vdata.append({
                            'vod_id': 'playlists_click_' + href,
                            'vod_name': name,
                            'vod_pic': self.proxy(i('.largeThumb').attr('src')),
                            'vod_tag': 'folder',
                            'vod_remarks': i('.playlist-videos .number').text() or '',
                            'style': {"type": "rect", "ratio": 1.33}
                        })
        
        # ---------------- 频道 (优化选择器) ----------------
        elif tid == '/channels':
            data = self.getpq(f'{tid}?o=rk&page={pg}')
            if data is not None:
                vhtml = data('#filterChannelsSection li')
                for i in vhtml.items():
                    avatar = i('.description .avatar')
                    href = avatar.find('a').attr('href') or ''
                    img = avatar.find('img')
                    name = img.attr('alt') or i('.description .userLink a').text() or ''
                    remarks = i('.descriptionContainer ul li').eq(-1).text() or ''
                    
                    if href:
                         vdata.append({
                            'vod_id': 'director_click_' + href,
                            'vod_name': name,
                            'vod_pic': self.proxy(img.attr('src')),
                            'vod_tag': 'folder',
                            'vod_remarks': remarks,
                            'style': {"type": "rect", "ratio": 1.33}
                        })
        
        # ---------------- 分类（只第一页 - 优化选择器） ----------------
        elif tid == '/categories' and str(pg) == '1':
            result['pagecount'] = 1
            data = self.getpq(f'{tid}')
            if data is not None:
                vhtml = data('.categoriesListSection li .category-info') 
                for i in vhtml.items():
                    link = i.find('a').eq(0)
                    href = link.attr('href') or ''
                    name = link.text() or ''
                    img_src = i.parent().find('img').attr('src')
                    
                    if href:
                        vdata.append({
                            'vod_id': href + '_this_video',
                            'vod_name': name,
                            'vod_pic': self.proxy(img_src),
                            'vod_tag': 'folder',
                            'style': {"type": "rect", "ratio": 1.33}
                        })
        
        # ---------------- 明星 (优化选择器) ----------------
        elif tid == '/pornstars':
            data = self.getpq(f'{tid}?o=t&page={pg}')
            if data is not None:
                vhtml = data('#popularPornstars .performerCard')
                for i in vhtml.items():
                    link = i('.wrap a').eq(0)
                    href = link.attr('href') or ''
                    name = i('.performerCardName').text() or ''
                    img_src = link.find('img').attr('src')
                    year = i('.performerVideosViewsCount span').eq(0).text() or ''
                    remarks = i('.performerVideosViewsCount span').eq(-1).text() or ''
                    
                    if href:
                        vdata.append({
                            'vod_id': 'pornstars_click_' + href,
                            'vod_name': name,
                            'vod_pic': self.proxy(img_src),
                            'vod_tag': 'folder',
                            'vod_year': year,
                            'vod_remarks': remarks,
                            'style': {"type": "rect", "ratio": 1.33}
                        })
        
        # ---------------- 片单内点击 (健壮性增强) ----------------
        elif 'playlists_click' in (tid or ''):
            tid_real = (tid or '').split('click_')[-1]
            tid_id = tid_real.split('playlist/')[-1].split('?')[0]
            token_val = getattr(self, "token", "")
            
            if str(pg) == '1':
                if self.get_playlist_token(tid_real): 
                    token_val = self.token
                
                hdata = self.getpq(tid_real) 
                if hdata is not None:
                    vdata = self.getlist(hdata('#videoPlaylist .pcVideoListItem .phimage'))
            
            if str(pg) != '1' and not token_val and tid_id:
                if self.get_playlist_token(tid_real):
                    token_val = self.token
                
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


        result['list'] = vdata
        return result

    # 视频详情页
    def detailContent(self, ids):
        url = f"{self.host}{ids[0]}"
        data = self.getpq(ids[0])
        if data is None:
            return {'list': []}

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
                        # 0 表示需要解析
                        plist.append(f"{height}P${self.e64(f'{0}@@@@{video_url}')}") 
        except Exception as e:
            print(f"提取mediaDefinitions失败: {str(e)}")

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    # 关键词搜索（兼容直接搜索接口）
    def searchContent(self, key, quick, pg="1"):
        encoded_key = quote(key) 
        data = self.getpq(f'/video/search?search={encoded_key}&page={pg}')
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

    # m3u8 代理重写 ts 链接
    def m3Proxy(self, url):
        try:
            # 统一使用 self.session
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

    # ts 文件/图片代理
    def tsProxy(self, url):
        try:
            # 统一使用 self.session
            data = self.session.get(url, stream=True, timeout=15)
            content_type = data.headers.get('Content-Type', 'application/octet-stream')
            return [200, content_type, data.content]
        except Exception as e:
            print(f"tsProxy 请求失败: {e}")
            return [500, "text/plain", f"tsProxy error: {e}"]

    # 自动获取 host（关键修复）
    def gethost(self, force_update=False):
        if not force_update and hasattr(self, 'host') and self.host != self.default_host:
            return self.host
            
        try:
            # 临时设置 headers 访问
            temp_headers = self.headers.copy()
            temp_headers.update({'referer': f'{self.default_host}/', 'origin': self.default_host})
            
            # *** 必须使用 self.session 来发起请求，以确保代理生效 ***
            response = self.session.get(self.default_host, 
                                        headers=temp_headers,
                                        allow_redirects=False, 
                                        timeout=10)
            
            loc = response.headers.get('Location')
            if loc:
                new_host = loc[:-1] if loc.endswith('/') else loc
                self.host = new_host
            else:
                self.host = self.default_host
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            self.host = self.default_host # 失败则回滚到默认
        
        print(f"Host updated to: {self.host}")
        return self.host

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

    # 统一处理列表视频结构 (健壮性增强)
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

    # 统一请求 + 解析（*** 最终修复：增加 JS/CDN 质询检测 ***）
    def getpq(self, path, retry_count=0):
        if path.startswith('http://') or path.startswith('https://'):
            url = path
        else:
            url = f'{self.host}{path}'
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status() 
            response.encoding = response.apparent_encoding
            html_text = response.text
            
            # *** 核心修复：检测 JS/CDN 质询页面 ***
            # 如果页面返回 200 OK，但内容是质询页，则手动抛出异常以触发重试
            if ("Please enable JavaScript" in html_text or 
                "challenge-running" in html_text or 
                "Checking if the site connection is secure" in html_text or
                "Verifying you are human" in html_text):
                
                print(f"JS/CDN 质询页被检测到: {url}")
                # 手动抛出一个 HTTPError，以便被下面的 except 块捕获
                raise requests.exceptions.HTTPError("JS/Bot challenge page detected", response=response)
            
            return pq(html_text)
            
        except requests.exceptions.HTTPError as e:
            # 捕获 HTTP 错误（4xx/5xx）或我们手动抛出的“质询页”错误
            print(f"请求失败 (HTTP Error): {url}, {str(e)}")
            
            # 只要是第一次失败，就强制更新 Host 并重试
            if retry_count == 0:
                print("Host likely outdated or blocked. Forcing update and retry...")
                self.gethost(force_update=True) # 强制更新 self.host (会使用 session)
                self.update_session_headers()   # 更新 session 的 headers
                return self.getpq(path, retry_count=1) # 重试
            
            return None # 重试后仍然失败
            
        except requests.exceptions.RequestException as e:
            # 捕获其他请求错误（如连接失败、超时等）
            print(f"请求失败 (Request Exception): {url}, {str(e)}")
            
            if retry_count == 0:
                print("Connection failed. Forcing update and retry...")
                self.gethost(force_update=True) # 强制更新 self.host
                self.update_session_headers()   # 更新 headers
                return self.getpq(path, retry_count=1) # 重试
                
            return None # 重试后仍然失败

    # 代理图片/视频（若有代理）
    def proxy(self, data, type='img'):
        if data and isinstance(self.proxies, dict) and len(self.proxies):
            try:
                return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
            except:
                return data
        else:
            return data
