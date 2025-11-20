# -*- coding: utf-8 -*-
# by @嗷呜 & 终极修复版
# Xhamster视频网站爬虫类

import json
import re
import sys
from base64 import b64decode, b64encode
from urllib.parse import urlparse

import requests
from pyquery import PyQuery as pq
from requests import Session
import urllib3

# 禁用SSL证书验证警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}
        
        # 【关键修复1】不要在这里发请求！直接设置默认值，保证APP秒开
        self.host = "https://xhamster.com"
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            # Referer 留空，在 Session 中自动管理
        }
        
        self.session = Session()
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)
        # 设置重试机制
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=2))

    def homeContent(self, filter):
        # 纯静态数据，秒加载
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
            classes.append({'type_name': k, 'type_id': cateManual[k]})
            if k != '4K': 
                filters[cateManual[k]] = [{'key': 'type', 'name': '类型', 'value': [{'n': '4K', 'v': '/4k'}]}]
        
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        try:
            # 获取首页数据
            data = self.getpq("/")
            return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item"))}
        except Exception as e:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        
        try:
            if tid in ['/4k', '/newest', '/best'] or 'two_click_' in tid:
                if 'two_click_' in tid: 
                    tid = tid.split('click_')[-1]
                path = f'{tid}{extend.get("type", "")}/{pg}'
                data = self.getpq(path)
                vdata = self.getlist(data(".thumb-list--sidebar .thumb-list__item"))
            
            elif tid == '/channels':
                data = self.getpq(f'{tid}/{pg}')
                jsdata = self.getjsdata(data)
                if jsdata and 'channels' in jsdata:
                    for i in jsdata['channels']:
                        vdata.append({
                            'vod_id': f"two_click_" + i.get('channelURL'),
                            'vod_name': i.get('channelName'),
                            'vod_pic': self.proxy(i.get('siteLogoURL')),
                            'vod_year': f'videos:{i.get("videoCount")}',
                            'vod_tag': 'folder',
                            'style': {'ratio': 1.778, 'type': 'rect'}
                        })
            
            elif tid == '/categories':
                result['pagecount'] = pg
                data = self.getpq(tid)
                self.cdata = self.getjsdata(data)
                if self.cdata:
                    items = self.cdata.get('layoutPage', {}).get('store', {}).get('popular', {}).get('assignable', [])
                    for i in items:
                        vdata.append({
                            'vod_id': "one_click_" + i.get('id'),
                            'vod_name': i.get('name'),
                            'vod_pic': '',
                            'vod_tag': 'folder',
                            'style': {'ratio': 1.778, 'type': 'rect'}
                        })
            
            elif tid == '/pornstars':
                data = self.getpq(f'{tid}/{pg}')
                pdata = self.getjsdata(data)
                if pdata:
                    items = pdata.get('pagesPornstarsComponent', {}).get('pornstarListProps', {}).get('pornstars', [])
                    for i in items:
                        vdata.append({
                            'vod_id': f"two_click_" + i.get('pageURL'),
                            'vod_name': i.get('name'),
                            'vod_pic': self.proxy(i.get('imageThumbUrl')),
                            'vod_tag': 'folder',
                            'style': {'ratio': 1.778, 'type': 'rect'}
                        })

            elif 'one_click' in tid:
                result['pagecount'] = pg
                tid = tid.split('click_')[-1]
                # 这里如果不重新获取可能会丢失cdata，加上简单的容错
                if not hasattr(self, 'cdata'):
                     self.cdata = self.getjsdata(self.getpq('/categories'))
                
                if hasattr(self, 'cdata') and self.cdata:
                    items = self.cdata.get('layoutPage', {}).get('store', {}).get('popular', {}).get('assignable', [])
                    for i in items:
                        if i.get('id') == tid:
                            for j in i.get('items', []):
                                vdata.append({
                                    'vod_id': f"two_click_" + j.get('url'),
                                    'vod_name': j.get('name'),
                                    'vod_pic': self.proxy(j.get('thumb')),
                                    'vod_tag': 'folder',
                                    'style': {'ratio': 1.778, 'type': 'rect'}
                                })
        except Exception as e:
            print(f"Category Error: {e}")

        result['list'] = vdata
        return result

    def detailContent(self, ids):
        url = ids[0]
        data = self.getpq(url)
        djs = self.getjsdata(data)
        
        vn = data('meta[property="og:title"]').attr('content')
        if not vn: vn = data('h1').text()
        
        vod = {
            'vod_name': vn,
            'vod_play_from': 'Xhamster',
            'vod_play_url': ''
        }
        
        plist = []
        try:
            # 提取逻辑
            sources = {}
            if djs:
                if 'xplayerSettings' in djs and 'sources' in djs['xplayerSettings']:
                    sources = djs['xplayerSettings']['sources']
                elif 'videoModel' in djs and 'sources' in djs['videoModel']:
                    sources = djs['videoModel']['sources']

            # HLS (优先)
            hls = sources.get('hls', {})
            if hls:
                for fmt, info in hls.items():
                    link = info if isinstance(info, str) else info.get('url', '')
                    if link and link.startswith('http'):
                        plist.append(f"HLS-{fmt}${self.e64(f'0@@@@{link}')}")

            # MP4
            std = sources.get('standard', {})
            if std:
                for fmt, info_list in std.items():
                    if isinstance(info_list, list):
                        for item in info_list:
                            link = item.get('url') or item.get('fallback')
                            label = item.get('label', fmt)
                            if link and link.startswith('http'):
                                plist.append(f"{label}${self.e64(f'0@@@@{link}')}")
            
            # Fallback
            if not plist:
                inp = data('input#url-input').attr('value')
                if inp and inp.startswith('http'):
                    plist.append(f"Line-1${self.e64(f'0@@@@{inp}')}")

        except Exception as e:
            pass
        
        if not plist:
            plist.append(f"无可用线路${self.e64(f'1@@@@{url}')}")

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f'/search/{key}?page={pg}')
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item")), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        try:
            ids = self.d64(id).split('@@@@')
            url = ids[1]
            if '.m3u8' in url:
                url = self.proxy(url, 'm3u8')
            return {'parse': 0, 'url': url, 'header': self.headers}
        except:
            return {'parse': 1, 'url': '', 'header': self.headers}

    def localProxy(self, param):
        try:
            url = self.d64(param['url'])
            type_ = param.get('type')
            if type_ == 'm3u8': return self.m3Proxy(url)
            elif type_ == 'ts': return self.tsProxy(url)
            else: return self.imgProxy(url)
        except: return [500, "text/plain", "error"]

    def getpq(self, path=''):
        """
        【关键修复2】智能请求处理
        1. 自动拼接 host
        2. 自动更新 host (解决跳转后找不到数据的问题)
        3. SSL 忽略
        """
        if path.startswith('http'):
            url = path
        else:
            if not path.startswith('/'): path = '/' + path
            url = f'{self.host}{path}'
            
        try:
            # 允许重定向 allow_redirects=True
            response = self.session.get(url, timeout=10, verify=False, allow_redirects=True)
            
            # 【核心】检测是否发生了重定向（例如跳转到了地区域名）
            # 如果发生了跳转，更新 self.host，这样后续请求就会带上正确的 Referer
            if response.history or response.url != url:
                new_parsed = urlparse(response.url)
                new_host = f"{new_parsed.scheme}://{new_parsed.netloc}"
                if new_host != self.host:
                    self.host = new_host
                    # 更新 Session 的 header，防止后续请求 403
                    self.session.headers.update({'Origin': self.host, 'Referer': f'{self.host}/'})
            
            response.encoding = 'utf-8'
            return pq(response.text)
        except Exception as e:
            print(f"PQ Error: {e}")
            return pq("")

    def getjsdata(self, data):
        try:
            txt = data("script[id='initials-script']").text()
            if not txt: return {}
            m = re.search(r'window\.initials\s*=\s*({.*?});', txt, re.DOTALL)
            if m: return json.loads(m.group(1))
            part = txt.split('initials=')[-1].strip()
            if part.endswith(';'): part = part[:-1]
            return json.loads(part)
        except: return {}

    def getlist(self, data):
        vlist = []
        for i in data.items():
            try:
                href = i('.role-pop').attr('href')
                if not href: continue
                img = i('.role-pop img').attr('src') or i('img').attr('src')
                vlist.append({
                    'vod_id': href,
                    'vod_name': i('.video-thumb-info a').text(),
                    'vod_pic': self.proxy(img),
                    'vod_year': i('.video-thumb-info .video-thumb-views').text().split(' ')[0],
                    'vod_remarks': i('.role-pop div[data-role="video-duration"]').text(),
                    'style': {'ratio': 1.778, 'type': 'rect'}
                })
            except: continue
        return vlist

    def m3Proxy(self, url):
        try:
            r = self.session.get(url, timeout=10, verify=False)
            base_url = url.rsplit('/', 1)[0]
            lines = []
            for line in r.text.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    lines.append(line)
                    continue
                if not line.startswith('http'):
                    if line.startswith('/'):
                        p = urlparse(url)
                        line = f"{p.scheme}://{p.netloc}{line}"
                    else:
                        line = f"{base_url}/{line}"
                lines.append(self.proxy(line, 'ts'))
            return [200, "application/vnd.apple.mpegur", '\n'.join(lines)]
        except: return [500, "text/plain", ""]

    def tsProxy(self, url):
        try:
            r = self.session.get(url, stream=True, timeout=10, verify=False)
            return [200, "video/mp2t", r.content]
        except: return [404, "", ""]
        
    def imgProxy(self, url):
        try:
            r = self.session.get(url, stream=True, timeout=5, verify=False)
            return [200, "image/jpeg", r.content]
        except: return [404, "", ""]

    def e64(self, text):
        try: return b64encode(text.encode('utf-8')).decode('utf-8')
        except: return ""

    def d64(self, text):
        try: return b64decode(text.encode('utf-8')).decode('utf-8')
        except: return ""

    def proxy(self, data, type='img'):
        if data and self.proxies:
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        return data
    
    def getName(self): pass
    def isVideoFormat(self, url): pass
    def manualVideoCheck(self): pass
    def destroy(self): pass
