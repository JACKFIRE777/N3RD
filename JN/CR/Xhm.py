# -*- coding: utf-8 -*-
# 完整修复版（菜单已恢复，播放已修复）
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
        初始化
        """
        try:
            self.proxies = json.loads(extend)
        except Exception:
            self.proxies = {}
        
        # 恢复原版 Headers 配置，并确保 Session 统一
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36',
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'dnt': '1',
            'sec-ch-ua-mobile': '?0',
            'origin': '',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': '',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'priority': 'u=1, i',
        }
        
        self.session = Session()
        self.host = self.gethost()
        if not self.host:
            self.host = "https://xhamster.com"
            
        self.headers.update({'origin': self.host, 'referer': f'{self.host}/'})
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)

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
        """
        一级菜单逻辑（完全恢复原版）
        """
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
        pg = str(pg) # 确保 pg 是字符串
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        
        if tid in ['/4k', '/newest', '/best'] or 'two_click_' in tid:
            if 'two_click_' in tid:
                tid = tid.split('click_')[-1]
            # 拼接 URL，处理 extend
            suffix = extend.get("type", "")
            url_path = f'{tid}{suffix}/{pg}'
            data = self.getpq(url_path)
            vdata = self.getlist(data(".thumb-list--sidebar .thumb-list__item"))
            
        elif tid == '/channels':
            data = self.getpq(f'{tid}/{pg}')
            jsdata = self.getjsdata(data)
            for i in jsdata.get('channels', []):
                vdata.append({
                    'vod_id': f"two_click_" + i.get('channelURL', ''),
                    'vod_name': i.get('channelName', ''),
                    'vod_pic': self.proxy(i.get('siteLogoURL')),
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
                    'vod_pic': self.proxy(i.get('imageThumbUrl')),
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
                                'vod_pic': self.proxy(j.get('thumb')),
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
        if href and title:
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

            # 解析 standard (mp4/直链)
            std = xsrc.get("standard", {}) or {}
            for qname, arr in std.items():
                if isinstance(arr, list):
                    for item in arr:
                        real = item.get("url") or item.get("fallback")
                        lbl = item.get("label") or item.get("quality") or qname
                        if real:
                            # 0@@@@url 表示直接播放
                            b64 = self.e64(f"0@@@@{real}")
                            plist.append(f"{lbl}${b64}")

            # 解析 hls (m3u8)
            hls = xsrc.get("hls", {}) or {}
            for qname, obj in hls.items():
                real = None
                if isinstance(obj, dict):
                    real = obj.get("url") or obj.get("src") or obj.get("file")
                elif isinstance(obj, str):
                    real = obj
                if real:
                    # 0@@@@url
                    b64 = self.e64(f"0@@@@{real}")
                    plist.append(f"{qname}${b64}")

            # 去重逻辑
            seen_urls = set()
            unique_plist = []
            for entry in plist:
                try:
                    q, b64 = entry.split('$', 1)
                    raw = self.d64(b64).split('@@@@', 1)
                    url = raw[1] if len(raw) > 1 else ""
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        unique_plist.append(entry)
                except:
                    pass
            
            # 排序
            def sort_key(s):
                name = s.split('$')[0]
                import re
                num = re.findall(r'\d+', name)
                return -int(num[0]) if num else 0
            
            unique_plist.sort(key=sort_key)
            plist = unique_plist

            # 兜底
            if not plist:
                plist = [f"{vn}${self.e64(f'1@@@@{ids}')}"]

        except Exception as e:
            print(f"解析播放源错误: {e}")
            plist = [f"{vn}${self.e64(f'1@@@@{ids}')}"]

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg)
        data = self.getpq(f'/search/{key}?page={pg}')
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item")), 'page': pg}

    # ==========================================
    # 核心修复区域：playerContent 和 m3Proxy
    # ==========================================

    def playerContent(self, flag, id, vipFlags):
        """
        核心修复：对 m3u8 进行预请求，跟随重定向获取带 Token 的真实 URL，然后再代理。
        """
        ids = self.d64(id).split('@@@@')
        url = ids[1] if len(ids) > 1 else ''
        
        final_url = url
        
        # 如果是 m3u8，尝试跟随跳转获取真实地址 (Token)
        if url and url.lower().endswith('.m3u8'):
            try:
                # 必须使用 Session 保持连接状态，allow_redirects=True 自动跳转
                r = self.session.get(url, allow_redirects=True, timeout=10)
                # 如果跳转成功，r.url 就是带 token 的地址
                if r.status_code < 400:
                    final_url = r.url
                else:
                    final_url = url
            except Exception as e:
                print(f"m3u8 跳转获取失败: {e}")
                final_url = url
            
            # 最终地址必须经过本地代理处理，以便后续解析 TS
            final_url = self.proxy(final_url, "m3u8")
            
        elif url:
            # MP4 直链或其他，也建议走代理以隐藏 IP 或处理 Headers
            ext = url.split('.')[-1] if '.' in url else 'video'
            final_url = self.proxy(url, ext)

        return {
            'parse': int(ids[0]) if ids and ids[0].isdigit() else 0,
            'url': final_url,
            'header': self.headers
        }

    def localProxy(self, param):
        url = self.d64(param['url'])
        type_ = param.get('type')
        
        if type_ == 'm3u8':
            return self.m3Proxy(url)
        else:
            return self.tsProxy(url)

    def m3Proxy(self, url):
        """
        m3u8 本地代理：下载列表，将所有切片路径转换为本地代理地址
        """
        try:
            # 使用 session 获取内容
            r = self.session.get(url, allow_redirects=True, timeout=15)
            content = r.text
            
            # 修正 m3u8 中的 URL
            base_url = url.rsplit('/', 1)[0]
            parsed = urlparse(url)
            host_url = f"{parsed.scheme}://{parsed.netloc}"
            
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    new_lines.append(line)
                    continue
                
                # 计算绝对路径
                real_ts_url = line
                if not line.startswith('http'):
                    if line.startswith('/'):
                        real_ts_url = host_url + line
                    else:
                        real_ts_url = base_url + '/' + line
                
                # 将 TS 地址封装进本地代理
                new_lines.append(self.proxy(real_ts_url, "ts"))
            
            return [200, "application/vnd.apple.mpegurl", '\n'.join(new_lines)]
            
        except Exception as e:
            print(f"m3Proxy Error: {e}")
            return [500, "text/plain", "Error loading m3u8"]

    def tsProxy(self, url):
        """
        TS 切片代理：流式传输二进制数据
        """
        try:
            r = self.session.get(url, stream=True, timeout=20)
            return [200, r.headers.get('Content-Type', 'video/MP2T'), r.content]
        except Exception as e:
            print(f"tsProxy Error: {e}")
            return [500, "application/octet-stream", b'']

    def proxy(self, data, type='img'):
        try:
            if data and len(self.proxies) > 0:
                return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
            else:
                return data
        except Exception:
            return data

    def gethost(self):
        try:
            try:
                r = requests.get('https://xhamster.com', headers=self.headers, proxies=self.proxies, allow_redirects=False, timeout=5)
                if r.status_code in [301, 302] and 'Location' in r.headers:
                    return r.headers['Location'].rstrip('/')
            except:
                pass
            r = requests.get('https://xhamster.com', headers=self.headers, proxies=self.proxies, timeout=10)
            p = urlparse(r.url)
            return f"{p.scheme}://{p.netloc}"
        except:
            return "https://xhamster.com"

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
            href = i('.role-pop').attr('href')
            if not href: continue
            
            name = i('.video-thumb-info a').text()
            img = i('.role-pop img')
            pic = img.attr('src') or img.attr('data-src') or ''
            
            views = i('.video-thumb-info .video-thumb-views').text()
            dur = i('.role-pop div[data-role="video-duration"]').text()
            
            vlist.append({
                'vod_id': href,
                'vod_name': name,
                'vod_pic': self.proxy(pic),
                'vod_year': views.split()[0] if views else '',
                'vod_remarks': dur,
                'style': {'ratio': 1.778, 'type': 'rect'}
            })
        return vlist

    def getpq(self, path=''):
        try:
            url = path if path.startswith('http') else f'{self.host}{path}'
            r = self.session.get(url, timeout=15)
            r.encoding = r.apparent_encoding
            return pq(r.text)
        except:
            return pq('')

    def getjsdata(self, data):
        try:
            txt = ""
            script = data("script[id='initials-script']")
            if script:
                txt = script.text()
            else:
                for s in data("script").items():
                    if 'initials=' in s.text():
                        txt = s.text()
                        break
            
            if not txt: return {}
            
            if 'initials=' in txt:
                json_str = txt.split('initials=', 1)[1].strip()
                if json_str.endswith(';'): json_str = json_str[:-1]
                if json_str.endswith(')'): 
                     json_str = json_str.rsplit('}', 1)[0] + '}'
                return json.loads(json_str)
            return json.loads(txt)
        except:
            return {}
