# -*- coding: utf-8 -*-
# Auto‑generated Pornhub Spider with Auto Categories
# by ChatGPT (Auto Category Version)

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

# --------------------------------------------------------------
# 🔥 自动从 Pornhub 获取分类/标签，构建多级分类
# --------------------------------------------------------------

class Spider(Spider):

    def init(self, extend=""):
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }

        self.host = self.gethost()
        self.headers.update({'referer': f'{self.host}/', 'origin': self.host})

        self.session = Session()
        self.session.headers.update(self.headers)
        self.session.proxies.update(self.proxies)

    # ----------------------------------------------------------
    # 首页自动分类（标签、频道、分类、pornstars 自动识别）
    # ----------------------------------------------------------
    def homeContent(self, filter):
        classes = []
        filters = {}

        # ---- 原始静态分类 ----
        classes.append({"type_name": "推荐", "type_id": "/recommended"})
        classes.append({"type_name": "视频", "type_id": "/video"})
        classes.append({"type_name": "分类", "type_id": "ph_category_root"})
        classes.append({"type_name": "标签", "type_id": "ph_tag_root"})
        classes.append({"type_name": "Pornstars", "type_id": "/pornstars"})
        classes.append({"type_name": "频道", "type_id": "/channels"})

        return {"class": classes, "filters": filters}

    # ----------------------------------------------------------
    # 自动抓取 Pornhub 分类页（一级→二级）
    # ----------------------------------------------------------
    def categoryContent(self, tid, pg, filter, extend):
        result = {
            'page': pg,
            'pagecount': 999,
            'limit': 90,
            'total': 99999
        }

        # ---------------- 推荐 ----------------
        if tid == "/recommended":
            data = self.getpq('/recommended?page=' + pg)
            vlist = self.getlist(data('.pcVideoListItem .phimage'))
            result['list'] = vlist
            return result

        # ---------------- 视频 ----------------
        if tid == "/video":
            data = self.getpq('/video?page=' + pg)
            result['list'] = self.getlist(data('.pcVideoListItem .phimage'))
            return result

        # ---------------- 分类（一级分类列表） ----------------
        if tid == "ph_category_root":
            data = self.getpq('/categories')
            classes = []
            for i in data('.categoriesListSection li .relativeWrapper').items():
                name = i('a').attr('alt')
                href = i('a').attr('href')
                classes.append({
                    'type_name': name,
                    'type_id': f"ph_category::{href}",
                    'style': {"type": "rect", "ratio": 1.33}
                })
            result['list'] = classes
            return result

        # ---------------- 单个分类 → 视频结果页 ----------------
        if tid.startswith("ph_category::"):
            real = tid.replace("ph_category::", "")
            data = self.getpq(f"{real}?page={pg}")
            result['list'] = self.getlist(data('.pcVideoListItem .phimage'))
            return result

        # ---------------- 标签（一级标签页） ----------------
        if tid == "ph_tag_root":
            data = self.getpq('/tags')
            tags = []
            for i in data('.tagContainer li a').items():
                name = i.text()
                href = i.attr('href')
                tags.append({
                    'type_name': name,
                    'type_id': f"ph_tag::{href}",
                    'style': {"type": "rect", "ratio": 1.33}
                })
            result['list'] = tags
            return result

        # ---------------- 单个标签 → 视频结果页 ----------------
        if tid.startswith("ph_tag::"):
            real = tid.replace("ph_tag::", "")
            data = self.getpq(f"{real}?page={pg}")
            result['list'] = self.getlist(data('.pcVideoListItem .phimage'))
            return result

        # ---------------- Pornstars ----------------
        if tid == "/pornstars":
            data = self.getpq(f"/pornstars?o=t&page={pg}")
            vlist = []
            for i in data('.performerCard').items():
                vlist.append({
                    'vod_id': 'pornstar_click_' + i('a').attr('href'),
                    'vod_name': i('.performerCardName').text(),
                    'vod_pic': self.proxy(i('img').attr('src')),
                    'vod_tag': 'folder',
                    'style': {"type": "rect", "ratio": 1.33}
                })
            result['list'] = vlist
            return result

        # ---------------- Pornstar 详情 → 视频 ----------------
        if tid.startswith("pornstar_click_"):
            real = tid.replace('pornstar_click_', '')
            data = self.getpq(f"{real}/videos?page={pg}")
            result['list'] = self.getlist(data('.pcVideoListItem .phimage'))
            return result

        # ---------------- 频道 ----------------
        if tid == "/channels":
            data = self.getpq(f"/channels?o=mv&page={pg}")
            vlist = []
            for i in data('#filterChannelsSection li .description').items():
                vlist.append({
                    'vod_id': 'channel_click_' + i('.avatar a').attr('href'),
                    'vod_name': i('.avatar img').attr('alt'),
                    'vod_pic': self.proxy(i('.avatar img').attr('src')),
                    'vod_tag': 'folder',
                    'style': {"type": "rect", "ratio": 1.33}
                })
            result['list'] = vlist
            return result

        # ---------------- 频道 → 视频 ----------------
        if tid.startswith("channel_click_"):
            real = tid.replace('channel_click_', '')
            data = self.getpq(f"{real}/videos?page={pg}")
            result['list'] = self.getlist(data('.pcVideoListItem .phimage'))
            return result

        return result

    # ----------------------------------------------------------
    # 搜索
    # ----------------------------------------------------------
    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f'/video/search?search={key}&page={pg}')
        return {'list': self.getlist(data('#videoSearchResult .pcVideoListItem .phimage'))}

    # ----------------------------------------------------------
    # 视频详情 + 播放解析
    # ----------------------------------------------------------
    def detailContent(self, ids):
        url = f"{self.host}{ids[0]}"
        data = self.getpq(ids[0])

        title = data('meta[property="og:title"]').attr('content')

        # 解析真实视频地址
        js = data('#player script').eq(0).text()
        pattern = r'"mediaDefinitions":\s*(\[.*?\])'

        play_list = []

        try:
            arr = json.loads(re.search(pattern, js, re.S).group(1))
            for m in arr:
                if m.get('videoUrl'):
                    urlx = m['videoUrl']
                    h = m.get('height', 'HD')
                    play_list.append(f"{h}${self.e64('0@@@@' + urlx)}")
        except:
            play_list.append(f"720P${self.e64('1@@@@' + url)}")

        vod = {
            'vod_name': title,
            'vod_play_from': 'Pornhub',
            'vod_play_url': '#'.join(play_list)
        }
        return {'list': [vod]}

    # ----------------------------------------------------------
    # 播放接口
    # ----------------------------------------------------------
    def playerContent(self, flag, id, vipFlags):
        ids = self.d64(id).split('@@@@')
        return {'parse': int(ids[0]), 'url': ids[1], 'header': self.headers}

    # ----------------------------------------------------------
    # 工具函数
    # ----------------------------------------------------------
    def getlist(self, items):
        v = []
        for i in items.items():
            v.append({
                'vod_id': i('a').attr('href'),
                'vod_name': i('a').attr('title'),
                'vod_pic': self.proxy(i('img').attr('src')),
                'vod_remarks': i('.duration').text(),
                'style': {'type': 'rect', 'ratio': 1.33}
            })
        return v

    def getpq(self, path):
        try:
            html = self.session.get(self.host + path).text
            return pq(html)
        except:
            return pq('')

    def e64(self, s):
        return b64encode(s.encode()).decode()

    def d64(self, s):
        return b64decode(s.encode()).decode()

    def gethost(self):
        try:
            r = requests.get('https://www.pornhub.com', headers=self.headers, allow_redirects=False)
            return r.headers.get('Location', 'https://www.pornhub.com').rstrip('/')
        except:
            return "https://www.pornhub.com"

    def proxy(self, url, type='img'):
        if url and self.proxies:
            return f"{self.getProxyUrl()}&url={self.e64(url)}&type={type}"
        return url
