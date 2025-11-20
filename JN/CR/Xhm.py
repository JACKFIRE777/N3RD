# -*- coding: utf-8 -*-
# 最终修正版：恢复原始菜单逻辑 + 仅修复播放 302 跳转问题
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
        【保持原版】初始化逻辑，确保菜单能正常加载
        """
        try:
            self.proxies = json.loads(extend)
        except Exception:
            self.proxies = {}
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
        self.host = self.gethost()
        self.session = Session()
        # 如果 gethost 返回空，会使用默认
        if not self.host:
            self.host = "https://xhamster.com"
        self.headers.update({'origin': self.host, 'referer': f'{self.host}/'})
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)
        pass

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
        【保持原版】确保一级菜单显示
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
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        if tid in ['/4k', '/newest', '/best'] or 'two_click_' in tid:
            if 'two_click_' in tid:
                tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}{extend.get("type", "")}/{pg}')
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
        """
        【修复】优化播放源解析，兼容新版页面结构
        """
        data = self.getpq(ids[0])
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

            std = xsrc.get("standard", {}) or {}
            for qname, arr in std.items():
                if isinstance(arr, list):
                    for item in arr:
                        real = item.get("url") or item.get("fallback")
                        lbl = item.get("label") or item.get("quality") or qname
                        if real:
                            b64 = self.e64(f"0@@@@{real}")
                            plist.append(f"{lbl}${b64}")

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

            def sort_key(s):
                name = s.split('$')[0]
                num = ''.join(filter(str.isdigit, name))
                num = int(num) if num else 0
                return -num

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
                plist = [f"{vn}${self.e64(f'1@@@@{ids[0]}')}"]

        except Exception as e:
            print("播放源解析失败：", str(e))
            plist = [f"{vn}${self.e64(f'1@@@@{ids[0]}')}"]

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f'/search/{key}?page={pg}')
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item")), 'page': pg}

    # ==========================================
    # 核心修复：只修改 playerContent 和 m3Proxy
    # ==========================================

    def playerContent(self, flag, id, vipFlags):
        """
        【修复】增加 302 跳转支持，获取真实 token
        """
        ids = self.d64(id).split('@@@@')
        url = ids[1] if len(ids) > 1 else ''
        
        real_url = url
        
        if url and url.lower().endswith(".m3u8"):
            try:
                # 使用 session 处理跳转，超时设为10秒防止卡顿
                r = self.session.get(url, allow_redirects=True, timeout=10, stream=True)
                if r.status_code < 400:
                    real_url = r.url
                r.close()
            except Exception as e:
                print(f"Redirect Error: {e}")
                pass
            # 必须经过本地代理转发
            real_url = self.proxy(real_url, "m3u8")
        elif url:
            # MP4 也建议走代理
            real_url = self.proxy(url, "mp4")

        return {'parse': int(ids[0]) if ids and ids[0].isdigit() else 0, 'url': real_url, 'header': self.headers}

    def localProxy(self, param):
        url = self.d64(param['url'])
        if param.get('type') == 'm3u8':
            return self.m3Proxy(url)
        else:
            return self.tsProxy(url)
            
    def m3Proxy(self, url):
        """
        【修复】修复 m3u8 内部路径问题
        """
        try:
            # 同样使用 session
            r = self.session.get(url, allow_redirects=True, timeout=15)
            text = r.text
        except Exception as e:
            print(f"获取 m3u8 失败: {e}")
            return [500, "text/plain", ""]

        base = url.rsplit('/', 1)[0]
        parsed = urlparse(url)
        host = parsed.scheme + "://" + parsed.netloc

        lines = text.strip().split('\n')
        new_lines = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                new_lines.append(line)
                continue
            
            if line.startswith('http'):
                real = line
            elif line.startswith('/'):
                real = host + line
            else:
                real = base + "/" + line
            
            new_lines.append(self.proxy(real, 'ts'))
            
        data = '\n'.join(new_lines)
        return [200, "application/vnd.apple.mpegurl", data]

    def tsProxy(self, url):
        try:
            data = self.session.get(url, stream=True, timeout=20)
            return [200, data.headers.get('Content-Type', 'application/octet-stream'), data.content]
        except Exception as e:
            print(f"请求 TS 文件失败: {e}")
            return [500, "application/octet-stream", b'']

    # ==========================================

    def gethost(self):
        """
        【保持原版】保留原有的域名检测逻辑
        """
        try:
            try:
                response = requests.get('https://xhamster.com', proxies=self.proxies, headers=self.headers, allow_redirects=False, timeout=10)
                if response.status_code in (301, 302) and response.headers.get('Location'):
                    return response.headers['Location'].rstrip('/')
            except Exception:
                response = requests.get('https://xhamster.com', proxies=self.proxies, headers=self.headers, allow_redirects=True, timeout=10)
            if response and hasattr(response, 'url'):
                parsed = urlparse(response.url)
                return f"{parsed.scheme}://{parsed.netloc}"
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
        return "https://zn.xhamster.com"

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self, encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
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
                'vod_pic': self.proxy(pic),
                'vod_year': views_text.split(' ')[0] if views_text else '',
                'vod_remarks': duration,
                'style': {'ratio': 1.778, 'type': 'rect'}
            })
        return vlist

    def getpq(self, path=''):
        h = '' if path.startswith('http') else self.host
        try:
            response = self.session.get(f'{h}{path}', timeout=15)
            response.encoding = response.apparent_encoding
            text = response.text
        except Exception as e:
            print(f"请求失败 {h}{path} : {e}")
            text = ''
        try:
            return pq(text)
        except Exception as e:
            try:
                return pq(text.encode('utf-8'))
            except Exception:
                print(str(e))
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
                if jpart.endswith(';'):
                    jpart = jpart[:-1]
                return json.loads(jpart)
            return json.loads(vhtml)
        except Exception as e:
            print(f"解析页面内 JS 数据失败: {e}")
            return {}

    def proxy(self, data, type='img'):
        try:
            if data and len(self.proxies):
                return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
            else:
                return data
        except Exception as e:
            print(f"proxy 生成失败: {e}")
            return data
