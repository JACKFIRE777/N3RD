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

    def homeContent(self, filter):
        result = {}

        cateManual = {
            "视频": "/video",
            "片单": "/playlists",
            "频道": "/channels",
            "分类": "/categories",
            "明星": "/pornstars"
        }

        # 🔥 修复部分：使用标准列表格式定义筛选器
        # key: url参数名
        # name: 左侧显示的标题
        # value: 选项列表 (n=显示名, v=参数值)
        video_filters = [
            {
                "key": "o",
                "name": "排序方式",
                "value": [
                    {"n": "最新精选", "v": ""},
                    {"n": "最多次观看", "v": "mv"},
                    {"n": "最高评分", "v": "tr"},
                    {"n": "最热门", "v": "ht"},
                    {"n": "最长视频", "v": "lg"},
                    {"n": "最新发布", "v": "cm"}
                ]
            }
        ]

        classes = []
        filters = {}

        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
            # 仅为 '视频' 添加筛选器
            if k == '视频':
                filters[cateManual[k]] = video_filters

        # 自动加入 keyword_list 为一级分类
        for kw in keyword_list:
            classes.append({
                'type_name': kw,
                'type_id': f"keyword__{kw}"
            })

        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        data = self.getpq('/recommended')
        vhtml = data("#recommendedListings .pcVideoListItem .phimage")
        return {'list': self.getlist(vhtml)}

    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

        # ---------------- 关键字分类处理 ----------------
        if isinstance(tid, str) and tid.startswith('keyword__'):
            kw = tid.replace('keyword__', '')
            real_kw = keyword_map.get(kw, kw)
            return self.searchContent(real_kw, quick=False, pg=pg)

        # ---------------- 视频分类 ----------------
        if tid == '/video' or '_this_video' in tid:
            base_tid = tid.split('_this_video')[0]
            
            params = {}
            if '?' in base_tid:
                query_string = base_tid.split('?')[1]
                for p in query_string.split('&'):
                    if '=' in p:
                        key, value = p.split('=', 1)
                        params[key] = value

            params['page'] = pg

            # 处理筛选参数
            if extend and 'o' in extend:
                params['o'] = extend['o']

            query_parts = []
            for key, value in params.items():
                if value != '':
                    query_parts.append(f"{key}={value}")

            query_string = '&'.join(query_parts)
            request_path = f"{base_tid.split('?')[0]}?{query_string}"

            data = self.getpq(request_path)
            vdata = self.getlist(data('#videoCategory .pcVideoListItem'))
            result['list'] = vdata
            return result

        # ---------------- 片单 ----------------
        if tid == '/playlists':
            data = self.getpq(f'{tid}?page={pg}')
            vhtml = data('#playListSection li')
            for i in vhtml.items():
                pic_url = i('.largeThumb').attr('data-thumb_url') or i('.largeThumb').attr('src')
                vdata.append({
                    'vod_id': 'playlists_click_' + i('.thumbnail-info-wrapper .display-block a').attr('href'),
                    'vod_name': i('.thumbnail-info-wrapper .display-block a').attr('title'),
                    'vod_pic': self.proxy(pic_url),
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
                raw_views = i('.descriptionContainer ul li').eq(-1).text()
                digits = ''.join([c for c in raw_views if c.isdigit()])
                view_str = raw_views
                if digits:
                    num = int(digits)
                    if num >= 100000000:
                        view_str = f"播放量：{num / 100000000:.2f}亿"
                    elif num >= 10000:
                        view_str = f"播放量：{num / 10000:.2f}万"
                    else:
                        view_str = f"播放量：{num}"

                vdata.append({
                    'vod_id': 'director_click_' + i('.avatar a').attr('href'),
                    'vod_name': i('.avatar img').attr('alt'),
                    'vod_pic': self.proxy(i('.avatar img').attr('src')),
                    'vod_tag': 'folder',
                    'vod_remarks': view_str,
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
            data = self.getpq(f'{tid}?o=ms&page={pg}')
            vhtml = data('#popularPornstars .performerCard .wrap')
            for i in vhtml.items():
                raw_views = i('.performerVideosViewsCount span').eq(-1).text()
                clean_str = raw_views.replace(',', '').replace(' ', '').upper()
                match = re.search(r'([\d\.]+)([BMK]?)', clean_str)
                num = 0.0
                if match:
                    value = float(match.group(1))
                    unit = match.group(2)
                    if unit == 'B': num = value * 1000000000
                    elif unit == 'M': num = value * 1000000
                    elif unit == 'K': num = value * 1000
                    else: num = value
                
                if num >= 100000000:
                    view_str = f"播放量：{num / 100000000:.2f}亿"
                elif num >= 10000:
                    view_str = f"播放量：{num / 10000:.2f}万"
                else:
                    view_str = f"播放量：{int(num)}" if num > 0 else raw_views

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

        # ---------------- 内部点击处理 ----------------
        if 'playlists_click' in tid:
            tid = tid.split('click_')[-1]
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

        if 'director_click' in tid:
            tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}/videos?page={pg}')
            vdata = self.getlist(data('#showAllChanelVideos .pcVideoListItem .phimage'))
            result['list'] = vdata
            return result

        if 'pornstars_click' in tid:
            tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}/videos?page={pg}')
            vdata = self.getlist(data('#mostRecentVideosSection .pcVideoListItem .phimage'))
            result['list'] = vdata
            return result

        result['list'] = vdata
        return result

    def detailContent(self, ids):
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
                    if not videoUrl:
                        continue
                    height = media.get('height') or media.get('quality') or '0'
                    plist.append(f"{height}${self.e64(f'{0}@@@@{videoUrl}')}")
        except Exception as e:
            print(f"提取mediaDefinitions失败: {str(e)}")

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        real_key = keyword_map.get(key, key)
        data = self.getpq(f'/video/search?search={real_key}&page={pg}')
        return {'list': self.getlist(data('#videoSearchResult .pcVideoListItem .phimage'))}

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
        except Exception as e:
            return "https://www.pornhub.com"

    def e64(self, text):
        try:
            return b64encode(text.encode('utf-8')).decode('utf-8')
        except:
            return ""

    def d64(self, encoded_text):
        try:
            return b64decode(encoded_text.encode('utf-8')).decode('utf-8')
        except:
            return ""

    def getlist(self, data):
        vlist = []
        if data is None:
            return vlist
        for i in data.items():
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
