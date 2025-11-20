# -*- coding: utf-8 -*-
# 最终修正版：直连模式 + 移交播放器处理 (修复播放失败)
import json
import sys
from base64 import b64decode, b64encode
from urllib.parse import urlparse

import requests
from pyquery import PyQuery as pq
from requests import Session
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        """
        初始化：直连模式，设置通用伪装头
        """
        self.proxies = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://xhamster.com/',
            'Origin': 'https://xhamster.com',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.session = Session()
        self.session.headers.update(self.headers)
        # 固定 Host，避免网络请求导致菜单加载失败
        self.host = "https://xhamster.com"

    def getName(self):
        return "XHamster"

    def isVideoFormat(self, url):
        try:
            url = url.lower()
            return any(url.endswith(ext) for ext in ['.m3u8', '.mp4', '.ts'])
        except Exception:
            return False

    def manualVideoCheck(self):
        return []

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "4K": "/4k",
            "国产": "two_click_/categories/chinese",
            "最新": "/newest",
            "最佳": "/best",
            "频道": "/channels",
            "类别": "/categories",
            "明星": "/pornstars"
        }
        classes = []
        filters = {}
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
            if k != '4K':
                filters[cateManual[k]] = [{'key': 'type', 'name': '类型', 'value': [{'n': '4K', 'v': '/4k'}]}]
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        data = self.getpq()
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item"))}

    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {}
        pg = str(pg)
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        
        if tid in ['/4k', '/newest', '/best'] or 'two_click_' in tid:
            if 'two_click_' in tid:
                tid = tid.split('click_')[-1]
            suffix = extend.get("type", "")
            url_part = f'{tid}{suffix}/{pg}'
            data = self.getpq(url_part)
            vdata = self.getlist(data(".thumb-list--sidebar .thumb-list__item"))
            
        elif tid == '/channels':
            data = self.getpq(f'{tid}/{pg}')
            jsdata = self.getjsdata(data)
            for i in jsdata.get('channels', []):
                vdata.append({
                    'vod_id': f"two_click_" + i.get('channelURL', ''),
                    'vod_name': i.get('channelName', ''),
                    'vod_pic': i.get('siteLogoURL'),
                    'vod_year': f'videos:{i.get("videoCount", "")}',
                    'vod_tag': 'folder',
                    'vod_remarks': f'subscribers:{i.get("subscriptionModel", {}).get("subscribers", "")}',
                    'style': {'ratio': 1.778, 'type': 'rect'}
                })
        elif tid == '/categories':
            result['pagecount'] = pg
            data = self.getpq(tid)
            self.cdata = self.getjsdata(data)
            for i in self.cdata.get('layoutPage', {}).get('store', {}).get('popular', {}).get('assignable', []):
                vdata.append({
                    'vod_id': "one_click_" + i.get('id', ''),
                    'vod_name': i.get('name', ''),
                    'vod_pic': '',
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.778, 'type': 'rect'}
                })
        elif tid == '/pornstars':
            data = self.getpq(f'{tid}/{pg}')
            pdata = self.getjsdata(data)
            for i in pdata.get('pagesPornstarsComponent', {}).get('pornstarListProps', {}).get('pornstars', []):
                vdata.append({
                    'vod_id': f"two_click_" + i.get('pageURL', ''),
                    'vod_name': i.get('name', ''),
                    'vod_pic': i.get('imageThumbUrl'),
                    'vod_remarks': i.get('translatedCountryName', ''),
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.778, 'type': 'rect'}
                })
        elif 'one_click' in tid:
            result['pagecount'] = pg
            tid = tid.split('click_')[-1]
            if hasattr(self, 'cdata'):
                for i in self.cdata.get('layoutPage', {}).get('store', {}).get('popular', {}).get('assignable', []):
                    if i.get('id') == tid:
                        for j in i.get('items', []):
                            vdata.append({
                                'vod_id': f"two_click_" + j.get('url', ''),
                                'vod_name': j.get('name', ''),
                                'vod_pic': j.get('thumb'),
                                'vod_tag': 'folder',
                                'style': {'ratio': 1.778, 'type': 'rect'}
                            })
        result['list'] = vdata
        return result

    def detailContent(self, ids):
        if isinstance(ids, list):
            ids = ids[0]
        
        data = self.getpq(ids)
        djs = self.getjsdata(data)

        vn = data('meta[property="og:title"]').attr('content') or ''
        dtext = data('#video-tags-list-container')
        href = dtext('a').attr('href')
        title = dtext('span[class*="body-bold-"]').eq(0).text() if dtext else ''
        pdtitle = ''
        if href:
            pdtitle = '[a=cr:' + json.dumps({'id': 'two_click_' + href, 'name': title}) + '/]' + title + '[/a]'

        vod = {
            'vod_name': vn,
            'vod_director': pdtitle,
            'vod_remarks': data('.rb-new__info').text(),
            'vod_play_from': 'Xhamster',
            'vod_play_url': ''
        }

        plist = []

        try:
            xsrc = djs.get('xplayerSettings', {}).get('sources', {})
            
            # 1. 优先提取 Standard (MP4) 格式，通常直连更稳定
            std = xsrc.get("standard", {}) or {}
            for qname, arr in std.items():
                if isinstance(arr, list):
                    for item in arr:
                        real = item.get("url") or item.get("fallback")
                        lbl = item.get("label") or item.get("quality") or qname
                        if real:
                            # MP4 直连，通常不需要复杂处理
                            b64 = self.e64(f"0@@@@{real}")
                            plist.append(f"{lbl} (MP4)${b64}")

            # 2. 提取 HLS (m3u8)
            hls = xsrc.get("hls", {}) or {}
            for qname, obj in hls.items():
                real = None
                if isinstance(obj, dict):
                    real = obj.get("url") or obj.get("src") or obj.get("file")
                elif isinstance(obj, str):
                    real = obj
                if real:
                    b64 = self.e64(f"0@@@@{real}")
                    plist.append(f"{qname} (HLS)${b64}")

            # 排序：将 1080p 等高质量排在前面
            def sort_key(s):
                name = s.split('$')[0]
                import re
                num = re.findall(r'\d+', name)
                score = int(num[0]) if num else 0
                # 让 MP4 权重更高一点，防止 m3u8 播放失败
                if "MP4" in name: score += 10000
                return -score

            seen_urls = set()
            unique_plist = []
            for entry in plist:
                try:
                    _, b64 = entry.split('$', 1)
                    url = self.d64(b64).split('@@@@', 1)[1]
                except Exception:
                    url = entry
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_plist.append(entry)
            unique_plist.sort(key=sort_key)
            plist = unique_plist

            if not plist:
                plist = [f"{vn}${self.e64(f'1@@@@{ids}')}"]

        except Exception as e:
            print("播放源解析失败：", str(e))
            plist = [f"{vn}${self.e64(f'1@@@@{ids}')}"]

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg)
        data = self.getpq(f'/search/{key}?page={pg}')
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item")), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        """
        【纯净直连版】
        直接将 URL 和 Headers 传递给播放器，让播放器自己处理 302 跳转。
        不使用 Python 预解析，防止签名过期或 Cookie 丢失。
        """
        ids = self.d64(id).split('@@@@')
        url = ids[1] if len(ids) > 1 else ''
        
        # 确保 Headers 包含 Referer，防止防盗链
        headers = {
            'User-Agent': self.headers['User-Agent'],
            'Referer': 'https://xhamster.com/',
            'Origin': 'https://xhamster.com'
        }
        
        # parse: 0 表示直接播放 URL
        return {
            'parse': 0, 
            'url': url, 
            'header': headers
        }

    def getpq(self, path=''):
        h = '' if path.startswith('http') else self.host
        try:
            # 增加 verify=False 防止盒子 SSL 报错
            response = self.session.get(f'{h}{path}', timeout=15, verify=False)
            response.encoding = response.apparent_encoding
            text = response.text
        except Exception as e:
            text = ''
        try:
            return pq(text)
        except Exception:
            return pq('')

    def getjsdata(self, data):
        try:
            vhtml = data("script[id='initials-script']").text()
            if not vhtml:
                scripts = data("script").items()
                for s in scripts:
                    txt = s.text()
                    if 'initials=' in txt:
                        vhtml = txt
                        break
            if not vhtml:
                return {}
            if 'initials=' in vhtml:
                jpart = vhtml.split('initials=', 1)[-1].strip()
                if jpart.endswith(';'): jpart = jpart[:-1]
                return json.loads(jpart)
            return json.loads(vhtml)
        except:
            return {}

    def e64(self, text):
        try:
            return b64encode(text.encode('utf-8')).decode('utf-8')
        except:
            return ""

    def d64(self, text):
        try:
            return b64decode(text.encode('utf-8')).decode('utf-8')
        except:
            return ""

    def getlist(self, data):
        vlist = []
        for i in data.items():
            href = i('.role-pop').attr('href') or ''
            name = i('.video-thumb-info a').text() or ''
            # 尝试获取多种图片属性
            pic = i('.role-pop img').attr('src') or i('.role-pop img').attr('data-src') or ''
            views_text = i('.video-thumb-info .video-thumb-views').text() or ''
            duration = i('.role-pop div[data-role="video-duration"]').text() or ''
            
            vlist.append({
                'vod_id': href,
                'vod_name': name,
                'vod_pic': pic,
                'vod_year': views_text.split(' ')[0] if views_text else '',
                'vod_remarks': duration,
                'style': {'ratio': 1.778, 'type': 'rect'}
            })
        return vlist

    # 这里的 proxy 仅仅为了兼容类调用，实际只返回原数据
    def proxy(self, data, type='img'):
        return data
