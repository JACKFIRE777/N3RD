# -*- coding: utf-8 -*-
# by @嗷呜 (Restored: Views+Duration, Added: Search Category, Fixed: Dynamic Category Filters)
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
# ---------------------------
keyword_list = ["中国", "日本","韩国","4K","中文字幕","BLACKED", "素人", "音乐", "合辑", "MartinPaola", "Reislin", "Lindsey Love", "ComerZ", "Yui Peachpie", "奶头乐", "大屁股"]

keyword_map = {
    "中国": "中国", "日本": "日本", "韩国": "韩国", "BLACKED": "BLACKED", "素人": "素人",
    "合辑": "Compilation", "音乐": "porn music video", "奶头乐": "male nipple play", "大屁股": "big ass"
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
            'pragma': 'no-cache', 'cache-control': 'no-cache', 'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'dnt': '1', 'sec-ch-ua-mobile': '?0', 'sec-fetch-site': 'cross-site',
            'sec-fetch-mode': 'cors', 'sec-fetch-dest': 'empty', 'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'priority': 'u=1, i',
        }

        self.host = self.gethost()
        self.headers.update({'referer': f'{self.host}/', 'origin': self.host})

        self.session = Session()
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)
        
        # 锁定 Cookie 语言为中文
        self.session.cookies.set('language', 'zh_CN', domain='.pornhub.com')

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

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
        cateManual = {
            "视频": "/video",
            "片单": "/playlists",
            "频道": "/channels",
            "分类": "/categories",
            "明星": "/pornstars",
            "站内搜索": "manual_search_page"
        }

        # 根据源码构建的完整筛选器
        video_filters = [
            {"key": "o", "name": "分类依据于", "value": [
                {"n": "最新精选", "v": ""}, {"n": "最多次观看", "v": "mv"}, {"n": "最高分", "v": "tr"},
                {"n": "最热门", "v": "ht"}, {"n": "最长", "v": "lg"}, {"n": "最新", "v": "cm"}
            ]},
            {"key": "t", "name": "时间区段", "value": [
                {"n": "全部", "v": "a"}, {"n": "每日", "v": "t"}, {"n": "每周", "v": "w"},
                {"n": "每月", "v": "m"}, {"n": "每年", "v": "y"}
            ]},
            {"key": "p", "name": "出品", "value": [
                {"n": "全部", "v": ""}, {"n": "专业", "v": "professional"}, {"n": "自制", "v": "homemade"}
            ]}
        ]

        channel_filters = [{"key": "o", "name": "排序", "value": [
            {"n": "综合排名", "v": "rk"}, {"n": "最多观看", "v": "mv"}, {"n": "最多订阅", "v": "ms"}, {"n": "首字母", "v": "a"}
        ]}]

        star_filters = [{"key": "o", "name": "排序", "value": [
            {"n": "最多订阅", "v": "ms"}, {"n": "最多观看", "v": "mv"}, {"n": "热门趋势", "v": "t"}, {"n": "首字母", "v": "a"}
        ]}]
        
        classes = []
        filters = {}

        for k in cateManual:
            classes.append({'type_name': k, 'type_id': cateManual[k]})
            tid = cateManual[k]
            if k in ['视频', '站内搜索']: filters[tid] = video_filters
            elif k == '频道': filters[tid] = channel_filters
            elif k == '明星': filters[tid] = star_filters

        # 关键字分类筛选器
        for kw in keyword_list:
            tid = f"keyword__{kw}"
            classes.append({'type_name': kw, 'type_id': tid})
            filters[tid] = video_filters

        # 【核心修复】暴力预注册分类 ID (c=1 到 c=150) 的筛选器
        # 这样当你点击“熟女(c=28)”时，App 发现 ID 匹配，就会显示筛选按钮
        for i in range(1, 151):
            target_tid = f"/video?c={i}"
            filters[target_tid] = video_filters
            filters[f"{target_tid}_this_video"] = video_filters

        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        data = self.getpq('/recommended')
        return {'list': self.getlist(data("#recommendedListings .pcVideoListItem"))}

    def categoryContent(self, tid, pg, filter, extend):
        result = {'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}
        vdata = []
        
        sort = extend.get('o') if extend else None
        time = extend.get('t') if extend else None
        prod = extend.get('p') if extend else None

        if tid == 'manual_search_page':
            if pg != '1': return {'list': []}
            result['pagecount'] = 1
            vdata.append({
                'vod_id': 'tip_search', 'vod_name': '👉 点顶部🔍图标可输入任意文字',
                'vod_pic': 'https://ci.phncdn.com/www-static/images/pornhub_logo_straight.png',
                'vod_tag': 'folder', 'vod_remarks': '使用说明', 'style': {"type": "rect", "ratio": 1.778}
            })
            for kw in keyword_list:
                vdata.append({
                    'vod_id': f"keyword__{kw}", 'vod_name': kw,
                    'vod_pic': 'https://ci.phncdn.com/www-static/images/pornhub_logo_straight.png',
                    'vod_tag': 'folder', 'vod_remarks': '热门标签', 'style': {"type": "rect", "ratio": 1.778}
                })
            result['list'] = vdata
            return result

        if isinstance(tid, str) and tid.startswith('keyword__'):
            kw = tid.replace('keyword__', '')
            return self.searchContent(kw, quick=False, pg=pg, sort=sort, time=time, prod=prod)

        # 视频列表处理（包含一级视频分类和从“分类”点进去的动态二级列表）
        if tid == '/video' or '_this_video' in tid:
            # 第一页且无筛选时，/video 抓取真正的首页
            if pg == '1' and not sort and not time and not prod and tid == '/video':
                data = self.getpq('/')
                result['list'] = self.getlist(data('.pcVideoListItem'))
            else:
                # 清洗 ID 逻辑：把 _this_video 这种标记去掉
                base_tid = tid.split('_this_video')[0]
                
                # 拼接翻页和筛选参数
                params = []
                if '?' in base_tid:
                    path, query = base_tid.split('?', 1)
                    params.append(query)
                else:
                    path = base_tid
                
                params.append(f"page={pg}")
                if sort: params.append(f"o={sort}")
                if time: params.append(f"t={time}")
                if prod: params.append(f"p={prod}")
                
                url = f"{path}?{'&'.join(params)}"
                data = self.getpq(url)
                vlist = data('#videoCategory .pcVideoListItem') or data('.pcVideoListItem')
                result['list'] = self.getlist(vlist)
            return result

        if tid == '/channels':
            chan_sort = sort if sort else 'rk'
            data = self.getpq(f'{tid}?o={chan_sort}&page={pg}')
            vhtml = data('#filterChannelsSection li')
            for i in vhtml.items():
                if not i('.avatar a').attr('href'): continue
                views = self.format_views(i('.descriptionContainer ul li').eq(-1).text())
                vdata.append({
                    'vod_id': 'director_click_' + i('.avatar a').attr('href'),
                    'vod_name': i('.avatar img').attr('alt'),
                    'vod_pic': self.proxy(i('.avatar img').attr('src')),
                    'vod_tag': 'folder', 'vod_remarks': f"播放量：{views}",
                    'style': {"type": "rect", "ratio": 1}
                })
            result['list'] = vdata
            return result

        if tid == '/pornstars':
            star_sort = sort if sort else 'ms'
            data = self.getpq(f'{tid}?o={star_sort}&page={pg}')
            vhtml = data('#popularPornstars .performerCard')
            for i in vhtml.items():
                if not i('a').attr('href'): continue
                views = self.format_views(i('.performerVideosViewsCount span').eq(-1).text())
                vdata.append({
                    'vod_id': 'pornstars_click_' + i('a').attr('href'),
                    'vod_name': i('.performerCardName').text(),
                    'vod_pic': self.proxy(i('a img').attr('src')),
                    'vod_tag': 'folder', 'vod_remarks': f"播放量：{views}",
                    'style': {"type": "rect", "ratio": 1}
                })
            result['list'] = vdata
            return result

        if 'pornstars_click' in tid or 'director_click' in tid:
            base_url = tid.split('click_')[-1]
            url = f'{base_url}/videos?page={pg}'
            if sort: url += f"&o={sort}"
            if time: url += f"&t={time}"
            if prod: url += f"&p={prod}"
            data = self.getpq(url)
            vlist = data('#mostRecentVideosSection .pcVideoListItem') or data('#showAllChanelVideos .pcVideoListItem') or data('.pcVideoListItem')
            result['list'] = self.getlist(vlist)
            return result

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

        if tid == '/playlists':
            url = f'{tid}?page={pg}'
            if sort: url += f"&o={sort}"
            data = self.getpq(url)
            vhtml = data('#playListSection li')
            for i in vhtml.items():
                pic = i('.largeThumb').attr('data-thumb_url') or i('.largeThumb').attr('src')
                vdata.append({
                    'vod_id': 'playlists_click_' + i('.thumbnail-info-wrapper .display-block a').attr('href'),
                    'vod_name': i('.thumbnail-info-wrapper .display-block a').attr('title'),
                    'vod_pic': self.proxy(pic), 'vod_tag': 'folder',
                    'vod_remarks': i('.playlist-videos .number').text(), 'style': {"type": "rect", "ratio": 1.778}
                })
            result['list'] = vdata
            return result

        result['list'] = vdata
        return result

    def detailContent(self, ids):
        if ids[0] == 'tip_search': return {'list': []}
        url = f"{self.host}{ids[0]}"
        data = self.getpq(ids[0])
        vn = data('meta[property="og:title"]').attr('content')
        dtext = data('.userInfo .usernameWrap a')
        pdtitle = '[a=cr:' + json.dumps({'id': 'director_click_' + dtext.attr('href'), 'name': dtext.text()}) + '/]' + dtext.text() + '[/a]'
        vod = {
            'vod_name': vn, 'vod_director': pdtitle,
            'vod_remarks': (data('.userInfo').text() + ' / ' + data('.ratingInfo').text()).replace('\n', ' / '),
            'vod_play_from': 'Pornhub', 'vod_play_url': ''
        }
        js_content = data("#player script").eq(0).text()
        plist = [f"{vn}${self.e64(f'{1}@@@@{url}')}"]
        try:
            pattern = r'"mediaDefinitions":\s*(\[.*?\]),\s*"isVertical"'
            match = re.search(pattern, js_content, re.DOTALL)
            if match:
                udata = json.loads(match.group(1))
                plist = []
                for media in udata:
                    videoUrl = media.get('videoUrl') or media.get('videoUrlNoWatermark') or media.get('url')
                    if not videoUrl: continue
                    height = media.get('height') or media.get('quality') or '0'
                    plist.append(f"{height}${self.e64(f'{0}@@@@{videoUrl}')}")
        except: pass
        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1", sort=None, time=None, prod=None):
        real_key = keyword_map.get(key, key)
        url = f'/video/search?search={real_key}&page={pg}'
        if sort: url += f"&o={sort}"
        if time: url += f"&t={time}"
        if prod: url += f"&p={prod}"
        data = self.getpq(url)
        return {'list': self.getlist(data('#videoSearchResult .pcVideoListItem'))}

    def playerContent(self, flag, id, vipFlags):
        ids = self.d64(id).split('@@@@')
        if '.m3u8' in ids[1]: ids[1] = self.proxy(ids[1], 'm3u8')
        return {'parse': int(ids[0]), 'url': ids[1], 'header': self.headers}

    def localProxy(self, param):
        url = self.d64(param.get('url'))
        if param.get('type') == 'm3u8': return self.m3Proxy(url)
        else: return self.tsProxy(url)

    def m3Proxy(self, url):
        ydata = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=False)
        data = ydata.content.decode('utf-8')
        if ydata.headers.get('Location'):
            url = ydata.headers['Location']
            data = requests.get(url, headers=self.headers, proxies=self.proxies).content.decode('utf-8')
        lines = data.strip().split('\n')
        last_r = url[:url.rfind('/')]; parsed_url = urlparse(url); durl = parsed_url.scheme + "://" + parsed_url.netloc
        for index, string in enumerate(lines):
            if '#EXT' not in string:
                if 'http' not in string:
                    domain = last_r if string.count('/') < 2 else durl
                    string = domain + ('' if string.startswith('/') else '/') + string
                lines[index] = self.proxy(string, string.split('.')[-1].split('?')[0])
        return [200, "application/vnd.apple.mpegur", '\n'.join(lines)]

    def tsProxy(self, url):
        data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True)
        return [200, data.headers['Content-Type'], data.content]

    def gethost(self):
        return "https://cn.pornhub.com"

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
                'vod_id': href, 'vod_name': title, 'vod_pic': self.proxy(img),
                'vod_remarks': " · ".join(rem), 'style': {'ratio': 1.778, 'type': 'rect'}
            })
        return vlist

    def getpq(self, path):
        try:
            response = self.session.get(f'{self.host}{path}').text
            return pq(response.encode('utf-8'))
        except: return None

    def proxy(self, data, type='img'):
        if data and len(self.proxies):
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else: return data
