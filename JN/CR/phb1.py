# -*- coding: utf-8 -*-
# by @嗷呜 (Restored: Views+Duration, Added: Search Category)
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
# 用户可维护：一级关键字列表 & 映射
# 这些词会显示在【站内搜索】分类里，方便快速点击
# ---------------------------
keyword_list = ["中国", "日本","韩国","4K","中文字幕","BLACKED", "素人", "音乐", "合辑", "MartinPaola", "Reislin", "Lindsey Love", "ComerZ", "Yui Peachpie", "奶头乐", "大屁股"]

keyword_map = {
    "中国": "中国",
    "日本": "日本",
    "韩国": "韩国",
    "BLACKED": "BLACKED",
    "素人": "素人",
    "合辑": "Compilation",
    "音乐": "porn music video", 
    "奶头乐": "male nipple play", 
    "大屁股": "big ass"
}
# ---------------------------


class Spider(Spider):

    def init(self, extend=""):
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}

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

        self.host = self.gethost()
        self.headers.update({'referer': f'{self.host}/', 'origin': self.host})

        self.session = Session()
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    # 工具函数：格式化播放量
    def format_views(self, raw_views):
        if not raw_views: return ""
        clean_str = raw_views.replace(',', '').replace(' ', '').upper()
        match = re.search(r'([\d\.]+)([BMK]?)', clean_str)
        if not match: return raw_views
        value = float(match.group(1))
        unit = match.group(2)
        num = value
        if unit == 'B': num = value * 1000000000
        elif unit == 'M': num = value * 1000000
        elif unit == 'K': num = value * 1000
        
        if num >= 100000000: return f"{num / 100000000:.2f}亿"
        elif num >= 10000: return f"{num / 10000:.2f}万"
        else: return f"{int(num)}"

    def homeContent(self, filter):
        result = {}
        
        # 手动分类
        cateManual = {
            "视频": "/video",
            "片单": "/playlists",
            "频道": "/channels",
            "分类": "/categories",
            "明星": "/pornstars",
            "站内搜索": "manual_search_page"  # 🔥 新增：站内搜索分类
        }

        # 筛选器配置
        video_filters = [{"key": "o", "name": "排序", "value": [
            {"n": "最新精选", "v": ""}, {"n": "最多观看", "v": "mv"}, {"n": "最高评分", "v": "tr"},
            {"n": "最热门", "v": "ht"}, {"n": "最长视频", "v": "lg"}, {"n": "最新发布", "v": "cm"}
        ]}]
        
        playlist_filters = [{"key": "o", "name": "排序", "value": [
            {"n": "最多观看", "v": "mv"}, {"n": "最高评分", "v": "tr"}, {"n": "最新创建", "v": "cm"}, {"n": "首字母", "v": "a"}
        ]}]

        channel_filters = [{"key": "o", "name": "排序", "value": [
            {"n": "综合排名", "v": "rk"}, {"n": "最多观看", "v": "mv"}, {"n": "最多订阅", "v": "ms"}, {"n": "首字母", "v": "a"}
        ]}]

        star_filters = [{"key": "o", "name": "排序", "value": [
            {"n": "最多订阅", "v": "ms"}, {"n": "最多观看", "v": "mv"}, {"n": "热门趋势", "v": "t"}, {"n": "首字母", "v": "a"}
        ]}]

        classes = []
        filters = {}

        # 添加常规分类
        for k in cateManual:
            classes.append({'type_name': k, 'type_id': cateManual[k]})
            if k == '视频': filters[cateManual[k]] = video_filters
            elif k == '片单': filters[cateManual[k]] = playlist_filters
            elif k == '频道': filters[cateManual[k]] = channel_filters
            elif k == '明星': filters[cateManual[k]] = star_filters
            elif k == '站内搜索': 
                # 为站内搜索页添加一个简单的视频排序筛选（因为点进去是关键词，再点进去是视频列表）
                filters[cateManual[k]] = video_filters

        # 自动加入 keyword_list 为一级分类（如果你还想保留顶部的一级入口的话，如果不想要可以注释掉下面这段）
        for kw in keyword_list:
            tid = f"keyword__{kw}"
            classes.append({'type_name': kw, 'type_id': tid})
            filters[tid] = video_filters

        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        data = self.getpq('/recommended')
        return {'list': self.getlist(data("#recommendedListings .pcVideoListItem"))}

    def categoryContent(self, tid, pg, filter, extend):
        result = {'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}
        vdata = []

        # ---------------- 站内搜索 (显示关键词列表) ----------------
        if tid == 'manual_search_page':
            # 这是一个特殊的分类，它不抓取网站，而是展示 keyword_list
            # 只有第一页
            if pg != '1':
                return {'list': []}
            
            result['pagecount'] = 1
            
            # 提示项
            vdata.append({
                'vod_id': 'tip_search',
                'vod_name': '👉 点顶部🔍图标可输入任意文字',
                'vod_pic': 'https://ci.phncdn.com/www-static/images/pornhub_logo_straight.png',
                'vod_tag': 'folder',
                'vod_remarks': '使用说明',
                'style': {"type": "rect", "ratio": 1.778}
            })

            # 遍历关键词生成“文件夹”
            for kw in keyword_list:
                vdata.append({
                    'vod_id': f"keyword__{kw}", # 点击后复用 keyword__ 逻辑
                    'vod_name': kw,
                    'vod_pic': 'https://ci.phncdn.com/www-static/images/pornhub_logo_straight.png', # 使用默认Logo
                    'vod_tag': 'folder',
                    'vod_remarks': '热门标签',
                    'style': {"type": "rect", "ratio": 1.778}
                })
            
            result['list'] = vdata
            return result

        # ---------------- 关键字分类处理 ----------------
        if isinstance(tid, str) and tid.startswith('keyword__'):
            kw = tid.replace('keyword__', '')
            real_kw = keyword_map.get(kw, kw)
            sort_opt = extend.get('o') if extend else None
            return self.searchContent(real_kw, quick=False, pg=pg, sort=sort_opt)

        # ---------------- 视频分类 ----------------
        if tid == '/video' or '_this_video' in tid:
            base_tid = tid.split('_this_video')[0]
            params = {}
            if '?' in base_tid:
                for p in base_tid.split('?')[1].split('&'):
                    if '=' in p: k, v = p.split('=', 1); params[k] = v
            params['page'] = pg
            if extend and 'o' in extend: params['o'] = extend['o']
            
            q_str = '&'.join([f"{k}={v}" for k, v in params.items() if v != ''])
            data = self.getpq(f"{base_tid.split('?')[0]}?{q_str}")
            result['list'] = self.getlist(data('#videoCategory .pcVideoListItem'))
            return result

        # ---------------- 片单 ----------------
        if tid == '/playlists':
            sort = extend.get('o', '') if extend else ''
            url = f'{tid}?page={pg}' + (f"&o={sort}" if sort else "")
            data = self.getpq(url)
            vhtml = data('#playListSection li')
            for i in vhtml.items():
                pic = i('.largeThumb').attr('data-thumb_url') or i('.largeThumb').attr('src')
                vdata.append({
                    'vod_id': 'playlists_click_' + i('.thumbnail-info-wrapper .display-block a').attr('href'),
                    'vod_name': i('.thumbnail-info-wrapper .display-block a').attr('title'),
                    'vod_pic': self.proxy(pic),
                    'vod_tag': 'folder',
                    'vod_remarks': i('.playlist-videos .number').text(),
                    'style': {"type": "rect", "ratio": 1.778}
                })
            result['list'] = vdata
            return result

        # ---------------- 频道 ----------------
        if tid == '/channels':
            sort = extend.get('o', 'rk') if extend else 'rk'
            data = self.getpq(f'{tid}?o={sort}&page={pg}')
            vhtml = data('#filterChannelsSection li .description')
            for i in vhtml.items():
                views = self.format_views(i('.descriptionContainer ul li').eq(-1).text())
                vdata.append({
                    'vod_id': 'director_click_' + i('.avatar a').attr('href'),
                    'vod_name': i('.avatar img').attr('alt'),
                    'vod_pic': self.proxy(i('.avatar img').attr('src')),
                    'vod_tag': 'folder',
                    'vod_remarks': f"播放量：{views}" if views else "",
                    'style': {"type": "rect", "ratio": 1}
                })
            result['list'] = vdata
            return result

        # ---------------- 分类 ----------------
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
            sort = extend.get('o', 'ms') if extend else 'ms'
            data = self.getpq(f'{tid}?o={sort}&page={pg}')
            vhtml = data('#popularPornstars .performerCard .wrap')
            for i in vhtml.items():
                views = self.format_views(i('.performerVideosViewsCount span').eq(-1).text())
                vdata.append({
                    'vod_id': 'pornstars_click_' + i('a').attr('href'),
                    'vod_name': i('.performerCardName').text(),
                    'vod_pic': self.proxy(i('a img').attr('src')),
                    'vod_tag': 'folder',
                    'vod_year': i('.performerVideosViewsCount span').eq(0).text(),
                    'vod_remarks': f"播放量：{views}" if views else "",
                    'style': {"type": "rect", "ratio": 1, "width": "150%"}
                })
            result['list'] = vdata
            return result

        # ---------------- 内部点击 ----------------
        if 'playlists_click' in tid:
            tid = tid.split('click_')[-1]
            if pg == '1':
                hdata = self.getpq(tid)
                self.token = hdata('#searchInput').attr('data-token')
                result['list'] = self.getlist(hdata('#videoPlaylist .pcVideoListItem'))
            else:
                tid = tid.split('playlist/')[-1]
                data = self.getpq(f'/playlist/viewChunked?id={tid}&token={self.token}&page={pg}')
                result['list'] = self.getlist(data('.pcVideoListItem'))
            return result

        if 'director_click' in tid:
            tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}/videos?page={pg}')
            result['list'] = self.getlist(data('#showAllChanelVideos .pcVideoListItem'))
            return result

        if 'pornstars_click' in tid:
            tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}/videos?page={pg}')
            result['list'] = self.getlist(data('#mostRecentVideosSection .pcVideoListItem'))
            return result

        result['list'] = vdata
        return result

    def detailContent(self, ids):
        if ids[0] == 'tip_search':
            return {'list': []}

        url = f"{self.host}{ids[0]}"
        data = self.getpq(ids[0])
        vn = data('meta[property="og:title"]').attr('content')
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

        js_content = data("#player script").eq(0).text()
        plist = [f"{vn}${self.e64(f'{1}@@@@{url}')}"]

        try:
            pattern = r'"mediaDefinitions":\s*(\[.*?\]),\s*"isVertical"'
            match = re.search(pattern, js_content, re.DOTALL)
            if match:
                json_str = match.group(1)
                udata = json.loads(json_str)
                plist = []
                for media in udata:
                    videoUrl = media.get('videoUrl') or media.get('videoUrlNoWatermark') or media.get('url')
                    if not videoUrl: continue
                    height = media.get('height') or media.get('quality') or '0'
                    # 简单的排序逻辑，避免复杂的 4K 检查导致问题
                    plist.append(f"{height}${self.e64(f'{0}@@@@{videoUrl}')}")
        except Exception as e:
            print(f"提取mediaDefinitions失败: {str(e)}")

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1", sort=None):
        real_key = keyword_map.get(key, key)
        url = f'/video/search?search={real_key}&page={pg}'
        if sort: url += f"&o={sort}"
        data = self.getpq(url)
        return {'list': self.getlist(data('#videoSearchResult .pcVideoListItem'))}

    def playerContent(self, flag, id, vipFlags):
        ids = self.d64(id).split('@@@@')
        if '.m3u8' in ids[1]:
            ids[1] = self.proxy(ids[1], 'm3u8')
        return {'parse': int(ids[0]), 'url': ids[1], 'header': self.headers}

    def localProxy(self, param):
        url = self.d64(param.get('url'))
        if param.get('type') == 'm3u8':
            return self.m3Proxy(url)
        else:
            return self.tsProxy(url)

    def m3Proxy(self, url):
        ydata = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=False)
        data = ydata.content.decode('utf-8')
        if ydata.headers.get('Location'):
            url = ydata.headers['Location']
            data = requests.get(url, headers=self.headers, proxies=self.proxies).content.decode('utf-8')

        lines = data.strip().split('\n')
        last_r = url[:url.rfind('/')]
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

    def tsProxy(self, url):
        data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True)
        return [200, data.headers['Content-Type'], data.content]

    def gethost(self):
        try:
            response = requests.get('https://www.pornhub.com', headers=self.headers, proxies=self.proxies,
                                    allow_redirects=False)
            return response.headers['Location'][:-1]
        except:
            return "https://www.pornhub.com"

    def e64(self, text):
        try: return b64encode(text.encode('utf-8')).decode('utf-8')
        except: return ""

    def d64(self, encoded_text):
        try: return b64decode(encoded_text.encode('utf-8')).decode('utf-8')
        except: return ""

    def getlist(self, data):
        vlist = []
        if data is None: return vlist
        for i in data.items():
            href = i('.phimage a').attr('href')
            if not href: continue
            
            title = i('.phimage img').attr('alt') or i('.title a').text() or i('a').attr('title')
            img = i('.phimage img').attr('data-src') or i('.phimage img').attr('src') or i('img').attr('src')
            
            views = self.format_views(i('.views var').text() or i('.views').text())
            duration = i('.duration').text()
            
            rem = []
            if views: rem.append(f"👁 {views}")
            if duration: rem.append(f"⏱ {duration}")

            vlist.append({
                'vod_id': href,
                'vod_name': title,
                'vod_pic': self.proxy(img),
                'vod_remarks': " · ".join(rem),
                'style': {'ratio': 1.778, 'type': 'rect'}
            })
        return vlist

    def getpq(self, path):
        try:
            response = self.session.get(f'{self.host}{path}').text
            return pq(response.encode('utf-8'))
        except:
            return None

    def proxy(self, data, type='img'):
        if data and len(self.proxies):
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else:
            return data
