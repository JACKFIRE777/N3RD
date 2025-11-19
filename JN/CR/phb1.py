# -*- coding: utf-8 -*-
# by @嗷呜 (modified to add keyword-driven top-level categories)
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

# ---------------------------
# 用户可维护：一级关键字列表 & 映射（中文->实际搜索词）
# 只需修改下面两项即可添加/调整一级分类与实际搜索词
# ---------------------------
# 【保持】: 从 keyword_list 中移除 "站内搜索"
keyword_list = ["中国", "日本","韩国","中文字幕","BLACKED", "素人", "音乐", "合辑", "MartinPaola", "Reislin", "Lindsey Love", "ComerZ", "Yui Peachpie", "奶头乐", "大屁股"]


keyword_map = {
    "中国": "中国",
    "日本": "日本",
    "韩国": "韩国",
    "BLACKED": "BLACKED",
    "素人": "素人",
     "合辑": "Compilation",
    "音乐": "porn music video", 
    "奶头乐": "male nipple play", 
    # 演示示例：中文 '大屁股' 实际搜索使用英文 'big ass'
    "大屁股": "big ass"
}
# ---------------------------


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

        # 手动定义静态一级分类
        cateManual = {
            "视频": "/video",
            "片单": "/playlists",
            "频道": "/channels",
            "分类": "/categories",
            "明星": "/pornstars",
            # 【修改点 1】: 手动添加 "站内搜索" 分类，位于 "明星" 之后
            # 使用 '*' 作为 type_id，强制 TVbox 识别为搜索入口
            "站内搜索": "*" 
        }

        classes = []
        filters = {}

        # 生成原有静态结构 + 站内搜索
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })

        # 🔥 自动加入 keyword_list 为一级分类（位于 "站内搜索" 之后）
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
                # --- 修改重点 ---
                # 源码显示真实地址在 data-thumb_url 中
                # 逻辑：优先取 data-thumb_url，如果没有再取 src
                pic_url = i('.largeThumb').attr('data-thumb_url') or i('.largeThumb').attr('src')
                # --- 修改结束 ---

                vdata.append({
                    'vod_id': 'playlists_click_' + i('.thumbnail-info-wrapper .display-block a').attr('href'),
                    'vod_name': i('.thumbnail-info-wrapper .display-block a').attr('title'),
                    'vod_pic': self.proxy(pic_url),  # 使用修正后的变量
                    'vod_tag': 'folder',
                    'vod_remarks': i('.playlist-videos .number').text(),
                    'style': {"type": "rect", "ratio": 1.778}
                })
            result['list'] = vdata
            return result

# ---------------- 频道 ----------------
        if tid == '/channels':
            data = self.getpq(f'{tid}?o=rk&page={pg}')
            vhtml = data('#filterChannelsSection li .description')
            for i in vhtml.items():
                
                # --- 数字转换逻辑 ---
                raw_views = i('.descriptionContainer ul li').eq(-1).text()
                # 提取纯数字
                digits = ''.join([c for c in raw_views if c.isdigit()])
                
                view_str = raw_views # 兜底默认值
                if digits:
                    num = int(digits)
                    if num >= 100000000:
                        # 修改点：增加前缀
                        view_str = f"播放量：{num / 100000000:.2f}亿"
                    elif num >= 10000:
                        # 修改点：增加前缀
                        view_str = f"播放量：{num / 10000:.2f}万"
                    else:
                        # 修改点：增加前缀
                        view_str = f"播放量：{num}"
                # ------------------

                vdata.append({
                    'vod_id': 'director_click_' + i('.avatar a').attr('href'),
                    'vod_name': i('.avatar img').attr('alt'),
                    'vod_pic': self.proxy(i('.avatar img').attr('src')),
                    'vod_tag': 'folder',
                    'vod_remarks': view_str, # 显示如：播放量：100.68亿
                    'style': {"type": "rect", "ratio": 1}
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
                    'style': {"type": "rect", "ratio": 1.778}
                })
            result['list'] = vdata
            return result

# ---------------- 明星 ----------------
        if tid == '/pornstars':
            # 【优化】这里删除了 import re，因为文件开头已经导入过了
            
            data = self.getpq(f'{tid}?o=ms&page={pg}')
            vhtml = data('#popularPornstars .performerCard .wrap')
            
            for i in vhtml.items():
                # --- 播放量 B/M/K 换算逻辑 ---
                raw_views = i('.performerVideosViewsCount span').eq(-1).text()
                clean_str = raw_views.replace(',', '').replace(' ', '').upper()
                
                # 直接使用 re 即可
                match = re.search(r'([\d\.]+)([BMK]?)', clean_str)
                
                num = 0.0
                if match:
                    value = float(match.group(1))
                    unit = match.group(2)
                    
                    if unit == 'B':      # Billion 10亿
                        num = value * 1000000000
                    elif unit == 'M':    # Million 百万
                        num = value * 1000000
                    elif unit == 'K':    # Kilo 千
                        num = value * 1000
                    else:                
                        num = value
                
                if num >= 100000000:
                    view_str = f"播放量：{num / 100000000:.2f}亿"
                elif num >= 10000:
                    view_str = f"播放量：{num / 10000:.2f}万"
                else:
                    view_str = f"播放量：{int(num)}" if num > 0 else raw_views
                # ---------------------------------------

                vdata.append({
                    'vod_id': 'pornstars_click_' + i('a').attr('href'),
                    'vod_name': i('.performerCardName').text(),
                    'vod_pic': self.proxy(i('a img').attr('src')),
                    'vod_tag': 'folder',
                    'vod_year': i('.performerVideosViewsCount span').eq(0).text(),
                    'vod_remarks': view_str,
                    'style': {"type": "rect", "ratio": 1, "width": "150%"}
                })
            result['list'] = vdata
            return result

        # ---------------- 片单内点击 ----------------
        if 'playlists_click' in tid:
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
                plist = []
                for media in udata:
                    videoUrl = media.get('videoUrl') or media.get('videoUrlNoWatermark') or media.get('url')
                    # 忽略空地址
                    if not videoUrl:
                        continue
                    height = media.get('height') or media.get('quality') or '0'
                    # parse flag 0 表示不走转码，1 失败回退
                    # 使用 e64 格式保持原来行为： "{flag}@@@@{url}"
                    plist.append(f"{height}${self.e64(f'{0}@@@@{videoUrl}')}")
        except Exception as e:
            print(f"提取mediaDefinitions失败: {str(e)}")

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    # 关键词搜索
    def searchContent(self, key, quick, pg="1"):
        # 【修改点 2】: 明确检查 key 是否为空，如果为空，则返回一个带搜索参数的空列表。
        # 当 type_id='*' 被点击时，客户端会直接调用 searchContent(key="")。
        # 返回空列表通常可以触发 TVbox 弹出输入框。
        if not key:
             return {'list': [], 'page': 0, 'pagecount': 0, 'total': 0, 'limit': 90}
        
        # key 传入可以是映射后的真实关键字，也可以是用户输入的搜索词
        # 如果是映射后的关键字，使用映射结果；如果是用户输入的词，直接使用 key
        real_key = keyword_map.get(key, key)
        final_key = real_key if real_key else key

        data = self.getpq(f'/video/search?search={final_key}&page={pg}')
        # 搜索结果需要返回完整的分页信息，即使是搜索页本身
        return {
            'list': self.getlist(data('#videoSearchResult .pcVideoListItem .phimage')),
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

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
                'style': {'ratio': 1.778, 'type': 'rect'}
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
