# -*- coding: utf-8 -*-
# by @嗷呜 (2025 完整修复版)

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


class Spider(Spider):
    api = "https://xhamster.com"
    session = Session()

    # UA
    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    }

    # Base64 编解码
    def e64(self, t):
        return str(b64encode(bytes(str(t), encoding='utf-8')), encoding='utf-8')

    def d64(self, t):
        return str(b64decode(t), encoding='utf-8')

    # 请求器
    def webread(self, url):
        try:
            return self.session.get(url, headers=self.header, timeout=10).text
        except:
            return ""

    # 读取 JSON
    def js(self, text):
        try:
            return json.loads(text)
        except:
            return {}

    #############################################
    # 解析新版 Xhamster window.initials JSON
    #############################################
    def getjsdata(self, pqhtml):
        # 结构1：<script data-initial>
        script = pqhtml("script[data-initial]").text()

        # 结构2：window.initials = {...}
        if not script:
            script = pqhtml("script:contains('initials')").text()

        if not script:
            return {}

        # 提取 JSON 部分
        if "initials =" in script:
            txt = script.split("initials =")[-1].strip()
        elif "initials=" in script:
            txt = script.split("initials=")[-1].strip()
        else:
            return {}

        if txt.endswith(";"):
            txt = txt[:-1]

        return self.js(txt)

    #################################################
    # 首页列表（一级菜单用它——已修复 2025新版结构）
    #################################################
    def getindex(self):
        url = f"{self.api}/videos"
        html = pq(self.webread(url))

        vlist = []

        # 新版 Xhamster 首页视频结构
        for i in html("a.video-thumb__link").items():
            title = i.attr("title")
            href = i.attr("href")
            img = i("img").attr("src") or i("img").attr("data-src")

            if not href:
                continue

            vlist.append({
                "vod_id": href,
                "vod_name": title,
                "vod_pic": img,
                "vod_remarks": ""
            })

        return vlist

    ##########################################
    # 分类（支持 2025 新结构）
    ##########################################
    def categoryContent(self, tid, pg, filter, extend):
        if tid == "home":
            return {"list": self.getindex(), "page": pg}

        url = f"{self.api}/categories/{tid}/{pg}"
        html = pq(self.webread(url))

        return {"list": self.getlist(html), "page": pg}

    ##########################################
    # 列表解析（通用）
    ##########################################
    def getlist(self, html):
        vlist = []

        for i in html("a.video-thumb__link").items():
            title = i.attr("title")
            href = i.attr("href")
            img = i("img").attr("src") or i("img").attr("data-src")

            if not href:
                continue

            vlist.append({
                "vod_id": href,
                "vod_name": title,
                "vod_pic": img,
                "vod_remarks": ""
            })

        return vlist

    ###################################
    # 关键函数：解析视频详情 + 播放地址
    ###################################
    def detailContent(self, ids):
        vid = ids[0]
        url = f"{self.api}{vid}"
        html = pq(self.webread(url))
        j = self.getjsdata(html)

        title = html("meta[property='og:title']").attr("content") or "Video"

        # 播放列表
        plist = []

        try:
            player = j["player"]["sources"]
        except:
            player = {}

        # mp4 源
        if "mp4" in player:
            for q in player["mp4"]:
                url = q.get("url")
                quality = q.get("quality", "mp4")
                if url:
                    plist.append(f"{quality}${self.e64('0@@@@' + url)}")

        # hls 源
        if "hls" in player:
            hls_url = player["hls"].get("url")
            if hls_url:
                plist.append(f"HLS${self.e64('0@@@@' + hls_url)}")

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": "",
                "vod_content": "",
                "vod_play_from": "xhamster",
                "vod_play_url": "#".join(plist)
            }]
        }

    ###################################
    # 播放器解码
    ###################################
    def playerContent(self, flag, id):
        raw = self.d64(id)
        if raw.startswith("0@@@@"):
            url = raw.replace("0@@@@", "")
        else:
            url = raw

        return {
            "parse": "0",
            "url": url,
            "header": self.header
        }

    ###################################
    # 搜索功能（已修复）
    ###################################
    def searchContent(self, key, quick, pg):
        url = f"{self.api}/search?q={key.replace(' ', '%20')}"
        html = pq(self.webread(url))
        return {"list": self.getlist(html)}

    ###################################
    # 首页分类菜单（一级菜单）
    ###################################
    def homeContent(self, filter):
        classes = [
            {"type_name": "首页推荐", "type_id": "home"},
            {"type_name": "最新", "type_id": "new"},
            {"type_name": "热门", "type_id": "best"},
            {"type_name": "高清", "type_id": "hd"},
            {"type_name": "分类", "type_id": "categories"},
        ]
        return {"class": classes, "list": self.getindex()}

