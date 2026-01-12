# -*- coding: utf-8 -*-
# by @嗷呜 (Refined Filter Logic)
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
keyword_list = ["中国", "日本", "韩国", "4K", "中文字幕", "BLACKED", "素人", "音乐", "合辑", "PMV", "MartinPaola", "Reislin", "Lindsey Love", "ComerZ", "Yui Peachpie", "奶头乐", "大屁股"]

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

class Spider(Spider):

    def init(self, extend=""):
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        self.host = self.gethost()
        self.headers.update({'referer': f'{self.host}/', 'origin': self.host})

        self.session = Session()
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)

    def getName(self): pass
    def isVideoFormat(self, url): pass
    def manualVideoCheck(self): pass
    def destroy(self): pass

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
        
        # 筛选器配置 (完全匹配 HTML 源码)
        video_filters = [
            {"key": "o", "name": "排序", "value": [
                {"n": "最相关", "v": ""}, 
                {"n": "最新", "v": "mr"}, 
                {"n": "最多观看", "v": "mv"}, 
                {"n": "最高评分", "v": "tr"},
                {"n": "最长视频", "v": "lg"}
            ]},
            {"key": "t", "name": "时间区段", "value": [
                {"n": "全部", "v": "a"}, 
                {"n": "今日", "v": "t"}, 
                {"n": "本周", "v": "w"}, 
                {"n": "本月", "v": "m"}, 
                {"n": "今年", "v": "y"}
            ]},
            {"key": "p", "name": "出品", "value": [
                {"n": "全部", "v": ""}, 
                {"n": "专业", "v": "professional"}, 
                {"n": "自制", "v": "homemade"}
            ]}
        ]
        
        playlist_filters = [{"key": "o", "name": "排序", "value": [{"n": "最多观看", "v": "mv"}, {"n": "最高评分", "v": "tr"}, {"n": "最新", "v": "cm"}]}]
        channel_filters = [{"key": "o", "name": "排序", "value": [{"n": "综合排名", "v": "rk"}, {"n": "最多观看", "v": "mv"}, {"n": "最多订阅", "v": "ms"}]}]
        star_filters = [{"key": "o", "name": "排序", "value": [{"n": "最多订阅", "v": "ms"}, {"n": "最多观看", "v": "mv"}, {"n": "热门趋势", "v": "t"}]}]

        cateManual = {
            "视频": "/video",
            "片单": "/playlists",
            "频道": "/channels",
            "分类": "/categories",
            "明星": "/pornstars",
            "站内搜索": "manual_search_page"
        }

        classes = []
        filters = {}

        for k, v in cateManual.items():
            classes.append({'type_name': k, 'type_id': v})
            if k in ['视频', '站内搜索']: filters[v] = video_filters
            elif k == '片单': filters[v] = playlist_filters
            elif k == '频道': filters[v] = channel_filters
            elif k == '明星': filters[v] = star_filters

        for kw in keyword_list:
            tid = f"keyword__{kw}"
            classes.append({'type_name': kw, 'type_id': tid})
            filters[tid] = video_filters

        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        data = self.getpq('/recommended')
        return {'list': self.getlist(data(".pcVideoListItem"))}

    def categoryContent(self, tid, pg, filter, extend):
        result = {'page': pg, 'pagecount': 999, 'limit': 40}
        vdata = []

        # 1. 站内搜索主页
        if tid == 'manual_search_page':
            if pg != '1': return {'list': []}
            vdata.append({
                'vod_id': 'tip_search', 'vod_name': '👉 点击顶部搜索框输入关键词',
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

        # 2. 关键词分类 (由 homeContent 触发)
        if isinstance(tid, str) and tid.startswith('keyword__'):
            kw = tid.replace('keyword__', '')
            return self.searchContent(kw, quick=False, pg=pg, extend=extend)

        # 3. 视频/分类列表
        if tid == '/video' or '_this_video' in tid:
            base_tid = tid.split('_this_video')[0]
            url = f"{base_tid}?" if '?' not in base_tid else f"{base_tid}&"
            url += f"page={pg}"
            if extend:
                for k, v in extend.items():
                    if v: url += f"&{k}={v}"
            data = self.getpq(url)
            result['list'] = self.getlist(data('.pcVideoListItem'))
            return result

        # 4. 片单
        if tid == '/playlists':
            sort = extend.get('o', 'mv') if extend else 'mv'
            data = self.getpq(f'{tid}?o={sort}&page={pg}')
            for i in data('#playListSection li').items():
                pic = i('.largeThumb').attr('data-thumb_url') or i('.largeThumb').attr('src')
                vdata.append({
                    'vod_id': 'playlists_click_' + i('.thumbnail-info-wrapper a').attr('href'),
                    'vod_name': i('.thumbnail-info-wrapper a').attr('title'),
                    'vod_pic': self.proxy(pic), 'vod_tag': 'folder',
                    'vod_remarks': i('.playlist-videos .number').text(),
                    'style': {"type": "rect", "ratio": 1.778}
                })
            result['list'] = vdata
            return result

        # 5. 频道
        if tid == '/channels':
            sort = extend.get('o', 'rk') if extend else 'rk'
            data = self.getpq(f'{tid}?o={sort}&page={pg}')
            for i in data('#filterChannelsSection li .description').items():
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

        # 6. 分类总表
        if tid == '/categories' and pg == '1':
            data = self.getpq(f'{tid}')
            for i in data('.categoriesListSection li .relativeWrapper').items():
                vdata.append({
                    'vod_id': i('a').attr('href') + '_this_video',
                    'vod_name': i('a').attr('alt'),
                    'vod_pic': self.proxy(i('a img').attr('src')),
                    'vod_tag': 'folder', 'style': {"type": "rect", "ratio": 1.778}
                })
            result['list'] = vdata
            return result

        # 7. 明星
        if tid == '/pornstars':
            sort = extend.get('o', 'ms') if extend else 'ms'
            data = self.getpq(f'{tid}?o={sort}&page={pg}')
            for i in data('#popularPornstars .performerCard .wrap').items():
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

        # 8. 内部深度点击逻辑
        if 'playlists_click' in tid:
            tid = tid.split('click_')[-1]
            if pg == '1':
                hdata = self.getpq(tid)
                self.token = hdata('#searchInput').attr('data-token')
                result['list'] = self.getlist(hdata('.pcVideoListItem'))
            else:
                pid = tid.split('playlist/')[-1]
                data = self.getpq(f'/playlist/viewChunked?id={pid}&token={self.token}&page={pg}')
                result['list'] = self.getlist(data('.pcVideoListItem'))
            return result

        if 'director_click' in tid or 'pornstars_click' in tid:
            tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}/videos?page={pg}')
            result['list'] = self.getlist(data('.pcVideoListItem'))
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
        plist = []
        try:
            pattern = r'"mediaDefinitions":\s*(\[.*?\]),\s*"isVertical"'
            match = re.search(pattern, js_content, re.DOTALL)
            if match:
                udata = json.loads(match.group(1))
                for media in udata:
                    vUrl = media.get('videoUrl') or media.get('url')
                    if not vUrl: continue
                    quality = media.get('quality', '720')
                    plist.append(f"{quality}P${self.e64(f'0@@@@{vUrl}')}")
        except: pass
        
        if not plist: plist = [f"默认${self.e64(f'1@@@@{url}')}"]
        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1", extend=None):
        real_key = keyword_map.get(key, key)
        url = f'/video/search?search={real_key}&page={pg}'
        if extend:
            for k in ['o', 't', 'p']:
                if k in extend and extend[k]:
                    url += f"&{k}={extend[k]}"
        data = self.getpq(url)
        return {'list': self.getlist(data('.pcVideoListItem'))}

    def playerContent(self, flag, id, vipFlags):
        ids = self.d64(id).split('@@@@')
        url = ids[1]
        if '.m3u8' in url:
            url = self.proxy(url, 'm3u8')
        return {'parse': int(ids[0]), 'url': url, 'header': self.headers}

    def localProxy(self, param):
        url = self.d64(param.get('url'))
        if param.get('type') == 'm3u8': return self.m3Proxy(url)
        return self.tsProxy(url)

    def m3Proxy(self, url):
        ydata = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=False)
        data = ydata.content.decode('utf-8')
        if ydata.headers.get('Location'):
            url = ydata.headers['Location']
            data = requests.get(url, headers=self.headers, proxies=self.proxies).content.decode('utf-8')
        lines = data.strip().split('\n')
        last_r = url[:url.rfind('/')]
        durl = urlparse(url).scheme + "://" + urlparse(url).netloc
        for index, string in enumerate(lines):
            if '#EXT' not in string:
                if 'http' not in string:
                    domain = last_r if string.count('/') < 2 else durl
                    string = domain + ('' if string.startswith('/') else '/') + string
                lines[index] = self.proxy(string, string.split('.')[-1].split('?')[0])
        return [200, "application/vnd.apple.mpegur", '\n'.join(lines)]

    def tsProxy(self, url):
        data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True)
        return [200, data.headers.get('Content-Type', 'video/mp2t'), data.content]

    def gethost(self):
        try:
            res = requests.get('https://www.pornhub.com', headers=self.headers, proxies=self.proxies, timeout=5, allow_redirects=False)
            return res.headers['Location'][:-1] if 'Location' in res.headers else "https://www.pornhub.com"
        except: return "https://www.pornhub.com"

    def e64(self, text): return b64encode(text.encode('utf-8')).decode('utf-8')
    def d64(self, text): return b64decode(text.encode('utf-8')).decode('utf-8')

    def getlist(self, data):
        vlist = []
        if not data: return vlist
        for i in data.items():
            href = i('.phimage a').attr('href') or i('a').attr('href')
            if not href or 'view_video' not in href: continue
            
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
            res = self.session.get(f'{self.host}{path}', timeout=10).text
            return pq(res)
        except: return pq("<html></html>")

    def proxy(self, data, type='img'):
        if data and len(self.proxies):
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        return data
