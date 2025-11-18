# -*- coding: utf-8 -*-
# by @JackFire 简化注解版
import json
import re
import sys
from base64 import b64encode, b64decode
import requests
from pyquery import PyQuery as pq
from urllib.parse import urlparse, urlencode

from requests import Session
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    #############################################################
    # 初始化：设置代理、UA、Host
    #############################################################
    def init(self, extend=""):
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}

        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.pornhub.com/"
        }

        # 自动寻找真实跳转 host，如 cn.pornhub.com
        self.host = self.get_host()
        self.session = Session()
        self.session.headers.update(self.headers)
        self.session.proxies.update(self.proxies)

    #############################################################
    # 首页分类
    #############################################################
    def homeContent(self, filter):
        result = {}
        result['class'] = [
            {"type_name": "视频", "type_id": "/video"},
            {"type_name": "分类", "type_id": "/categories"}
        ]
        result['filters'] = {}
        return result

    #############################################################
    # 首页推荐
    #############################################################
    def homeVideoContent(self):
        data = self.getpq("/recommended")
        nodes = data("#recommendedListings .pcVideoListItem .phimage")
        return {"list": self.format_list(nodes)}

    #############################################################
    # 分类内容（分页）
    #############################################################
    def categoryContent(self, tid, pg, filter, extend):
        result = {"page": pg, "pagecount": 9999, "limit": 90, "total": 999999}

        if tid == "/video":
            url = f"/video?page={pg}"
            data = self.getpq(url)
            nodes = data("#videoCategory .pcVideoListItem .phimage")

        elif tid == "/categories":
            data = self.getpq("/categories")
            nodes = data(".categoriesListSection li .relativeWrapper")
            result["pagecount"] = 1  # 分类不分页

        else:
            nodes = []

        result['list'] = self.format_list(nodes)
        return result

    #############################################################
    # 搜索内容（支持关键词）
    #############################################################
    def searchContent(self, key, quick, pg="1"):
        # 关键字搜索
        url = f"/video/search?search={key}&page={pg}"
        data = self.getpq(url)
        nodes = data("#videoSearchResult .pcVideoListItem .phimage")
        return {"list": self.format_list(nodes)}

    #############################################################
    # 详情页：解析真实视频源
    #############################################################
    def detailContent(self, ids):
        path = ids[0]
        data = self.getpq(path)

        name = data('meta[property="og:title"]').attr("content")
        script = data("#player script").eq(0).text()

        play_list = []

        # 提取 mediaDefinitions
        try:
            match = re.search(r'"mediaDefinitions":\s*(\[.*?\])', script, re.S)
            arr = json.loads(match.group(1))

            for item in arr:
                if not item.get("videoUrl"):
                    continue

                height = item.get("quality") or item.get("height") or "HD"
                video = item.get("videoUrl")

                play_list.append(f"{height}${self.e64(f'0@@@@{video}')}")

        except:
            pass

        vod = {
            "vod_name": name,
            "vod_play_from": "Pornhub",
            "vod_play_url": "#".join(play_list)
        }

        return {"list": [vod]}

    #############################################################
    # 播放：处理 Base64 URL 和 m3u8 代理
    #############################################################
    def playerContent(self, flag, id, vipFlags):
        info = self.d64(id).split("@@@@")
        need_parse = int(info[0])
        url = info[1]

        return {
            "parse": need_parse,
            "url": url,
            "header": self.headers
        }

    #############################################################
    # 工具函数：构建 video 列表项
    #############################################################
    def format_list(self, nodes):
        result = []
        for i in nodes.items():
            result.append({
                "vod_id": i("a").attr("href"),
                "vod_name": i("a").attr("title"),
                "vod_pic": i("img").attr("src"),
                "vod_remarks": i(".duration").text(),
                "style": {"type": "rect", "ratio": 1.33}
            })
        return result

    #############################################################
    # 工具：PyQuery
    #############################################################
    def getpq(self, path):
        try:
            html = self.session.get(f"{self.host}{path}").text
            return pq(html)
        except:
            return pq("")

    #############################################################
    # host 自动判断
    #############################################################
    def get_host(self):
        try:
            r = requests.get("https://www.pornhub.com", headers=self.headers, proxies=self.proxies, allow_redirects=False)
            return r.headers["Location"].rstrip("/")
        except:
            return "https://www.pornhub.com"

    #############################################################
    # Base64 工具
    #############################################################
    def e64(self, s):
        return b64encode(s.encode()).decode()

    def d64(self, s):
        return b64decode(s.encode()).decode()
