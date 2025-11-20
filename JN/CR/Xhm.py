# -*- coding: utf-8 -*-
# 最终修复版（无代理 + 自动提取Cookie + 302跳转修复）
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
        初始化：无代理模式，直连配置
        """
        self.proxies = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36',
            'Referer': 'https://xhamster.com/',
            'Origin': 'https://xhamster.com',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.session = Session()
        self.session.headers.update(self.headers)
        # 默认 Host，避免初始化卡顿
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
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        
        if tid in ['/4k', '/newest', '/best'] or 'two_click_' in tid:
            if 'two_click_' in tid:
                tid = tid.split('click_')[-1]
            url_part = f'{tid}{extend.get("type", "")}/{pg}'
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

            # 标准 MP4 源
            std = xsrc.get("standard", {}) or {}
            for qname, arr in std.items():
                if isinstance(arr, list):
                    for item in arr:
                        real = item.get("url") or item.get("fallback")
                        lbl = item.get("label") or item.get("quality") or qname
                        if real:
                            b64 = self.e64(f"0@@@@{real}")
                            plist.append(f"{lbl}${b64}")

            # HLS 源
            hls = xsrc.get("hls", {}) or {}
            for qname, obj in hls.items():
                real = None
                if isinstance(obj, dict):
                    real = obj.get("url") or obj.get("src") or obj.get("file")
                elif isinstance(obj, str):
                    real = obj
                if real:
                    b64 = self.e64(f"0@@@@{real}")
                    plist.append(f"{qname}${b64}")

            # 排序与去重
            def sort_key(s):
                name = s.split('$')[0]
                import re
                num = re.findall(r'\d+', name)
                return -int(num[0]) if num else 0

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
                # 兜底：解析失败则使用 sniff
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
        【核心修复】
        1. 预请求获取跳转后的真实 m3u8 地址 (解决相对路径问题)
        2. 提取跳转过程中的 Cookie 并传给播放器 (解决 403 问题)
        """
        ids = self.d64(id).split('@@@@')
        url = ids[1] if len(ids) > 1 else ''
        
        real_url = url
        headers = self.headers.copy()
        
        if url:
            # 针对 m3u8 和 mp4 都进行预请求以获取 Cookie
            try:
                # 使用 session 跟随跳转
                r = self.session.get(url, headers=headers, allow_redirects=True, timeout=10, stream=True)
                
                if r.status_code < 400:
                    real_url = r.url
                    
                    # 【关键】提取 Cookie 转为字符串 header
                    cookies = r.cookies.get_dict()
                    if cookies:
                        cookie_str = '; '.join([f'{k}={v}' for k, v in cookies.items()])
                        headers['Cookie'] = cookie_str
                        
                r.close()
            except Exception as e:
                print(f"Redirect/Cookie Error: {e}")
                pass
        
        return {
            'parse': int(ids[0]) if ids and ids[0].isdigit() else 0, 
            'url': real_url, 
            'header': headers
        }

    # 辅助函数
    def getpq(self, path=''):
        h = '' if path.startswith('http') else self.host
        try:
            response = self.session.get(f'{h}{path}', timeout=15)
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
            pic = i('.role-pop img').attr('src') or ''
            views_text = i('.video-thumb-info .video-thumb-views').text() or ''
            duration = i('.role-pop div[data-role="video-duration"]').text() or ''
            vlist.append({
                'vod_id': href,
                'vod_name': name,
                'vod_pic': pic,  # 不再使用 proxy()
                'vod_year': views_text.split(' ')[0] if views_text else '',
                'vod_remarks': duration,
                'style': {'ratio': 1.778, 'type': 'rect'}
            })
        return vlist
