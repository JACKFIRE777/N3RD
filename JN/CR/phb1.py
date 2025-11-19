# -*- coding: utf-8 -*-
# by @嗷呜 (Modified by AI for Enhanced Stability and Functionality)
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

# =========================================================
# 🔥 用户可维护部分：一级分类关键字 & 搜索映射
# =========================================================

# 一级分类名称（用于首页分类显示）
keyword_list = ["中国", "日本", "韩国", "中文字幕", "BLACKED", "素人", "大屁股"]

# 搜索映射（若不需要映射，则键和值相同）
keyword_map = {
    "中国": "中国",
    "日本": "日本",
    "韩国": "韩国",
    "中文字幕": "Chinese Subtitle",
    "BLACKED": "BLACKED",
    "素人": "amateur",  # 优化搜索词
    "大屁股": "big ass"
}

# =========================================================


# 继承基础 Spider 类
class Spider(Spider):

    def init(self, extend=""):
        '''
        初始化方法（配置代理、请求头、session 等）
        extend 传入的 JSON 会作为代理配置
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

        # 手动定义一级分类（保留原有静态分类）
        cateManual = {
            "视频": "/video",
            "片单": "/playlists",
            "频道": "/channels",
            "分类": "/categories",
            "明星": "/pornstars"
        }

        classes = []
        filters = {}

        # 生成原有结构
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })

        # 🔥 自动加入 keyword_list 为一级分类（易维护）
        # type_id 使用 keyword__{kw} 形式以便在 categoryContent 区分
        for kw in keyword_list:
            classes.append({
                'type_name': kw,
                'type_id': f"keyword__{kw}"
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

        # ---------------- 如果是 keyword 类型的一级分类，转换为搜索 ----------------
        if isinstance(tid, str) and tid.startswith('keyword__'):
            kw = tid.replace('keyword__', '')
            # 从映射中获取实际搜索关键词（若无映射则使用原始 kw）
            real_kw = keyword_map.get(kw, kw)
            # 复用搜索接口（保证分页等逻辑）
            return self.searchContent(real_kw, quick=False, pg=pg)
        
        # ---------------- 🔥 新增：演员点击（actor_click_） ----------------
        if isinstance(tid, str) and tid.startswith("actor_click_"):
            href = tid.replace("actor_click_", "")  # /pornstar/xxx
            data = self.getpq(f"{href}/videos?page={pg}")
            vdata = self.getlist(data(".pcVideoListItem .phimage"))
            result['list'] = vdata
            return result

        # ---------------- 视频分类 ----------------
        if tid == '/video' or '_this_video' in tid:
            pagestr = '&' if '?' in tid else '?'
            tid = tid.split('_this_video')[0]
            data = self.getpq(f'{tid}{pagestr}page={pg}')
            vdata = self.getlist(data('#videoCategory .pcVideoListItem'))
            result['list'] = vdata
            return result

        # ---------------- 片单 ----------------
        if tid == '/playlists':
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
            result['list'] = vdata
            return result

        # ---------------- 频道 ----------------
        if tid == '/channels':
            data = self.getpq(f'{tid}?o=rk&page={pg}')
            vhtml = data('#filterChannelsSection li .description')
            for i in vhtml.items():
                vdata.append({
                    'vod_id': 'director_click_' + i('.avatar a').attr('href'),
                    'vod_name': i('.avatar img').attr('alt'),
                    'vod_pic': self.proxy(i('.avatar img').attr('src')),
                    'vod_tag': 'folder',
                    # 兼容第一个文件的 remarks 字段，第二个文件是 i('.descriptionContainer li').eq(-1).text()
                    'vod_remarks': i('.descriptionContainer ul li').eq(-1).text(),
                    'style': {"type": "rect", "ratio": 1.33}
                })
            result['list'] = vdata
            return result

        # ---------------- 分类（只第一页） ----------------
        if tid == '/categories' and pg == '1':
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
            result['list'] = vdata
            return result

        # ---------------- 明星 ----------------
        if tid == '/pornstars':
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
            result['list'] = vdata
            return result

        # ---------------- 片单内点击 ----------------
        if 'playlists_click' in tid:
            tid = tid.split('click_')[-1]
            # 第一页需要读取 token
            if pg == '1':
                hdata = self.getpq(tid)
                # 使用第一个文件的 token 提取方式，保持一致性
                self.token = hdata('#searchInput').attr('data-token')
                vdata = self.getlist(hdata('#videoPlaylist .pcVideoListItem .phimage'))
            else:
                tid = tid.split('playlist/')[-1]
                data = self.getpq(f'/playlist/viewChunked?id={tid}&token={self.token}&page={pg}')
                vdata = self.getlist(data('.pcVideoListItem .phimage'))
            result['list'] = vdata
            return result

        # ---------------- 频道内点击 ----------------
        if 'director_click' in tid:
            tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}/videos?page={pg}')
            vdata = self.getlist(data('#showAllChanelVideos .pcVideoListItem .phimage'))
            result['list'] = vdata
            return result

        # ---------------- 明星内点击 ----------------
        if 'pornstars_click' in tid:
            tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}/videos?page={pg}')
            vdata = self.getlist(data('#mostRecentVideosSection .pcVideoListItem .phimage'))
            result['list'] = vdata
            return result

        result['list'] = vdata
        return result

    # 视频详情页
    def detailContent(self, ids):
        url = f"{self.host}{ids[0]}"
        data = self.getpq(ids[0])

        # 标题
        vn = data('meta[property="og:title"]').attr('content')

        # ------------------- 导演（Uploader） -------------------
        dtext = data('.userInfo .usernameWrap a')
        pdtitle = '[a=cr:' + json.dumps(
            {'id': 'director_click_' + dtext.attr('href'), 'name': dtext.text()}) + '/]' + dtext.text() + '[/a]'
        
        # ------------------- 🔥 新增：演员 -------------------
        actors_html = ""
        # 使用第二个文件的 CSS 选择器
        actors = data(".pornstarsWrapper a.pstar-list-btn")
        for a in actors.items():
            name = a.text().strip()
            href = a.attr("href")
            if name and href:
                # 兼容第一个文件中的 'vod_actor' 字段和点击格式
                actors_html += "[a=cr:" + json.dumps({
                    "id": "actor_click_" + href,
                    "name": name
                }) + "/]" + name + "[/a], "
        
        actors_html = actors_html.rstrip(", ")

        vod = {
            'vod_name': vn,
            'vod_director': pdtitle,
            # 兼容第一个文件的 remarks 字段
            'vod_remarks': (data('.userInfo').text() + ' / ' + data('.ratingInfo').text()).replace('\n', ' / '),
            'vod_actor': actors_html, # 新增演员字段
            'vod_play_from': 'Pornhub',
            'vod_play_url': ''
        }

        # 获取 JS 里的 mediaDefinitions（真实视频地址）
        js_content = data("#player script").eq(0).text()

        # 初始播放列表（失败兜底）
        # 使用第一个文件的兜底逻辑
        plist = [f"{vn}${self.e64(f'{1}@@@@{url}')}"]

        try:
            # 使用第一个文件的正则提取
            pattern = r'"mediaDefinitions":\s*(\[.*?\]),\s*"isVertical"'
            match = re.search(pattern, js_content, re.DOTALL)
            if match:
                # 解析多个清晰度
                json_str = match.group(1)
                udata = json.loads(json_str)
                plist = []
                for media in udata:
                    videoUrl = media.get('videoUrl') or media.get('videoUrlNoWatermark') or media.get('url')
                    # 忽略空地址
                    if not videoUrl:
                        continue
                    height = media.get('height') or media.get('quality') or '0'
                    # parse flag 0 表示不走转码，1 失败回退
                    # 保持第一个文件的 Base64 格式： "{flag}@@@@{url}"
                    plist.append(f"{height}${self.e64(f'{0}@@@@{videoUrl}')}")
        except Exception as e:
            print(f"提取mediaDefinitions失败: {str(e)}")

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    # 关键词搜索
    def searchContent(self, key, quick, pg="1"):
        # key 传入可以是映射后的真实关键字，也可以是直接的搜索词
        real_key = keyword_map.get(key, key)
        data = self.getpq(f'/video/search?search={real_key}&page={pg}')
        return {'list': self.getlist(data('#videoSearchResult .pcVideoListItem .phimage'))}

    # 播放器接口
    def playerContent(self, flag, id, vipFlags):
        ids = self.d64(id).split('@@@@')
        
        # 保持第一个文件的 M3U8/TS 代理逻辑，确保播放稳定性
        if '.m3u8' in ids[1]:
            # ids[1] 是原始 URL，调用 proxy() 会生成代理 URL
            ids[1] = self.proxy(ids[1], 'm3u8')
            
        return {'parse': int(ids[0]), 'url': ids[1], 'header': self.headers}

    # 本地代理（m3u8 / ts）- 保持第一个文件的逻辑
    def localProxy(self, param):
        url = self.d64(param.get('url'))
        if param.get('type') == 'm3u8':
            return self.m3Proxy(url)
        else:
            return self.tsProxy(url)

    # m3u8 代理重写 ts 链接 - 保持第一个文件的逻辑
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

    # ts 文件代理 - 保持第一个文件的逻辑
    def tsProxy(self, url):
        data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True)
        return [200, data.headers['Content-Type'], data.content]

    # 自动获取 host（避免被地区跳转）
    def gethost(self):
        try:
            response = requests.get('https://www.pornhub.com', headers=self.headers, proxies=self.proxies,
                                    allow_redirects=False)
            # 确保返回的 host 没有末尾的斜杠
            return response.headers['Location'].rstrip('/') 
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
        # 兼容 getpq 返回 None 的情况
        if data is None:
            return vlist
        for i in data.items():
            # 有些元素属性位置不同，做容错处理
            href = i('a').attr('href') or ''
            title = i('a').attr('title') or i('img').attr('alt') or ''
            img = i('img').attr('src') or i('img').attr('data-src') or ''
            remarks = i('.bgShadeEffect').text() or i('.duration').text() or ''
            vlist.append({
                'vod_id': href,
                'vod_name': title,
                'vod_pic': self.proxy(img),
                'vod_remarks': remarks,
                'style': {'ratio': 1.33, 'type': 'rect'}
            })
        return vlist

    # 统一请求 + 解析
    def getpq(self, path):
        try:
            response = self.session.get(f'{self.host}{path}').text
            # 使用 response.text 而不是 response.content.decode('utf-8')，让 requests 自动处理编码
            return pq(response)
        except Exception as e:
            print(f"请求失败: , {str(e)}")
            return None

    # 代理图片/视频（若有代理）
    def proxy(self, data, type='img'):
        if data and len(self.proxies):
            # 假设您有一个代理服务地址（getProxyUrl()），这里保持第一个文件的实现方式
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else:
            return data
