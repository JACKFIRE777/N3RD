# -*- coding: utf-8 -*-
# by @嗷呜 (Enhanced Pornhub Spider: Keyword Categories + Actor Support)

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
keyword_list = ["中国", "BLACKED", "素人", "大屁股"]

# 搜索映射（如“大屁股”实际搜索 Pornhub 的 "big ass"）
keyword_map = {
    "中国": "中国",
    "BLACKED": "BLACKED",
    "素人": "amateur",
    "大屁股": "big ass",
}

# =========================================================


class Spider(Spider):

    def init(self, extend=""):
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121 Safari/537.36",
            "Referer": "https://cn.pornhub.com/",
            "Origin": "https://cn.pornhub.com",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        self.host = self.gethost()
        self.session = Session()
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)


    # -------------------------------------------------------
    # 基础函数
    # -------------------------------------------------------

    def proxy(self, url):
        if not url:
            return url
        return url.replace(" ", "%20")

    def getpq(self, url):
        if not url.startswith("http"):
            url = self.host + url
        r = self.session.get(url, timeout=10)
        return pq(r.text)

    def e64(self, text):
        return b64encode(text.encode()).decode()

    def d64(self, text):
        return b64decode(text).decode()

    def get(list_obj, i, default=""):
        return list_obj[i] if i < len(list_obj) else default


    # -------------------------------------------------------
    # 首页分类
    # -------------------------------------------------------

    def homeContent(self, filter):
        cateManual = {
            "视频": "/video",
            "片单": "/playlists",
            "频道": "/channels",
            "分类": "/categories",
            "明星": "/pornstars",
        }

        classes = []

        # 固定分类
        for name, link in cateManual.items():
            classes.append({"type_name": name, "type_id": link})

        # 自动补充关键词一级分类
        for kw in keyword_list:
            classes.append({
                "type_name": kw,
                "type_id": f"keyword__{kw}",
            })

        return {"class": classes, "filters": {}}


    # -------------------------------------------------------
    # 推荐视频
    # -------------------------------------------------------

    def homeVideoContent(self):
        data = self.getpq("/recommended")
        vhtml = data("#recommendedListings .pcVideoListItem .phimage")
        return {"list": self.getlist(vhtml)}


    # -------------------------------------------------------
    # 分类入口
    # -------------------------------------------------------

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg)
        result = {
            "page": pg,
            "pagecount": 9999,
            "limit": 90,
            "total": 999999,
        }

        # ---------- 关键字分类：keyword__xxxx ----------
        if isinstance(tid, str) and tid.startswith("keyword__"):
            kw = tid.replace("keyword__", "")
            real_kw = keyword_map.get(kw, kw)
            return self.searchContent(real_kw, quick=False, pg=pg)

        # ---------- 演员点击 ----------
        if isinstance(tid, str) and tid.startswith("actor_click_"):
            href = tid.replace("actor_click_", "")  # /pornstar/mike-angelo
            data = self.getpq(f"{href}/videos?page={pg}")
            vlist = self.getlist(data(".pcVideoListItem .phimage"))
            return {
                "page": pg,
                "pagecount": 9999,
                "limit": 90,
                "total": 999999,
                "list": vlist,
            }

        # ---------- 片单 ----------
        if tid == "/playlists":
            data = self.getpq(f"/playlists?page={pg}")
            vhtml = data("#playListSection li")
            vlist = []
            for i in vhtml.items():
                vlist.append({
                    "vod_id": "playlists_click_" + i(".thumbnail-info-wrapper a").attr("href"),
                    "vod_name": i(".thumbnail-info-wrapper a").attr("title"),
                    "vod_pic": self.proxy(i(".largeThumb").attr("src")),
                    "vod_tag": "folder",
                    "vod_remarks": i(".playlist-videos .number").text(),
                    "style": {"type": "rect", "ratio": 1.33}
                })
            result["list"] = vlist
            return result

        # ---------- 频道 ----------
        if tid == "/channels":
            data = self.getpq(f"/channels?o=rk&page={pg}")
            vhtml = data("#filterChannelsSection li .description")
            vlist = []
            for i in vhtml.items():
                vlist.append({
                    "vod_id": "director_click_" + i(".avatar a").attr("href"),
                    "vod_name": i(".avatar img").attr("alt"),
                    "vod_pic": self.proxy(i(".avatar img").attr("src")),
                    "vod_tag": "folder",
                    "vod_remarks": i(".descriptionContainer li").eq(-1).text(),
                    "style": {"type": "rect", "ratio": 1.33}
                })
            result["list"] = vlist
            return result

        # ---------- 明星（Pornstars） ----------
        if tid == "/pornstars":
            data = self.getpq(f"/pornstars?o=t&page={pg}")
            vhtml = data("#popularPornstars .performerCard")
            vlist = []
            for i in vhtml.items():
                vlist.append({
                    "vod_id": "pornstars_click_" + i("a").attr("href"),
                    "vod_name": i(".performerCardName").text(),
                    "vod_pic": self.proxy(i("a img").attr("src")),
                    "vod_tag": "folder",
                    "vod_remarks": i(".videosNumber").text(),
                    "style": {"type": "rect", "ratio": 1.33}
                })
            result["list"] = vlist
            return result

        # ---------- 明星 → 影片 ----------
        if "pornstars_click_" in tid:
            tid = tid.replace("pornstars_click_", "")
            data = self.getpq(f"{tid}/videos?page={pg}")
            vlist = self.getlist(data(".pcVideoListItem .phimage"))
            result["list"] = vlist
            return result

        # ---------- 导演（Uploader）影片 ----------
        if "director_click_" in tid:
            tid = tid.replace("director_click_", "")
            data = self.getpq(f"{tid}/videos?page={pg}")
            vlist = self.getlist(data("#showAllChanelVideos .pcVideoListItem .phimage"))
            result["list"] = vlist
            return result

        # ---------- 普通分类 ----------
        data = self.getpq(f"{tid}?page={pg}")
        vlist = self.getlist(data(".pcVideoListItem .phimage"))
        result["list"] = vlist
        return result


    # -------------------------------------------------------
    # 视频详情页解析（含演员 & 导演）
    # -------------------------------------------------------

    def detailContent(self, ids):
        url = ids[0]
        data = self.getpq(url)

        title = data('meta[property="og:title"]').attr("content")

        # ------------------- 导演（Uploader） -------------------
        d = data(".userInfo .usernameWrap a")
        director = ""
        if d:
            director = "[a=cr:" + json.dumps({
                "id": "director_click_" + d.attr("href"),
                "name": d.text()
            }) + "/]" + d.text() + "[/a]"

        # ------------------- 🔥 新增：演员 -------------------
        actors_html = ""
        actors = data(".pornstarsWrapper a.pstar-list-btn")

        for a in actors.items():
            name = a.text().strip()
            href = a.attr("href")
            if name and href:
                actors_html += "[a=cr:" + json.dumps({
                    "id": "actor_click_" + href,
                    "name": name
                }) + "/]" + name + "[/a], "

        actors_html = actors_html.rstrip(", ")

        # ------------------- 播放地址解析 -------------------
        js_content = data("#player script").eq(0).text()
        play_list = []

        try:
            match = re.search(r'"mediaDefinitions":\s*(\[.*?\])', js_content, re.S)
            if match:
                arr = json.loads(match.group(1))
                for m in arr:
                    link = m.get("videoUrl") or m.get("url")
                    if link:
                        q = m.get("quality") or m.get("height") or "HD"
                        play_list.append(f"{q}${self.e64('0@@@@' + link)}")
        except:
            pass

        # 默认：无清晰度时给一个 URL
        if not play_list:
            play_list.append(f"HD${self.e64('1@@@@' + url)}")

        vod = {
            "vod_name": title,
            "vod_director": director,
            "vod_actor": actors_html,
            "vod_remarks": data(".ratingInfo").text(),
            "vod_play_from": "Pornhub",
            "vod_play_url": "#".join(play_list),
        }

        return {"list": [vod]}


    # -------------------------------------------------------
    # 搜索功能
    # -------------------------------------------------------

    def searchContent(self, key, quick, pg="1"):
        real_kw = keyword_map.get(key, key)
        data = self.getpq(f"/video/search?search={real_kw}&page={pg}")
        vlist = self.getlist(data("#videoSearchResult .pcVideoListItem .phimage"))
        return {"list": vlist}


    # -------------------------------------------------------
    # 播放器
    # -------------------------------------------------------

    def playerContent(self, flag, id, vipFlags):
        ids = self.d64(id).split("@@@@")
        mode = ids[0]
        url = ids[1]
        return {
            "parse": mode,
            "playUrl": "",
            "url": url,
            "header": self.headers
        }
