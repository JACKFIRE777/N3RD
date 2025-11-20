# -*- coding: utf-8 -*-
# by @嗷呜 & 修复播放版
# Xhamster视频网站爬虫类

import json
import re
import sys
from base64 import b64decode, b64encode
from urllib.parse import urlparse

import requests
from pyquery import PyQuery as pq
from requests import Session

# 禁用SSL警告，防止老旧设备报错
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    """Xhamster视频爬虫类"""

    def init(self, extend=""):
        """初始化爬虫配置 - 恢复原版逻辑以保证列表加载"""
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}
        
        # [修复] 统一使用 Windows Chrome 123 的指纹，避免服务器返回假数据
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'Upgrade-Insecure-Requests': '1',
            'dnt': '1',
        }
        
        # 获取实际的主站域名 (原版逻辑，但增加了异常处理防止卡死)
        self.host = self.gethost()
        
        # 创建会话对象
        self.session = Session()
        self.headers.update({'origin': self.host, 'referer': f'{self.host}/'})
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)
        # 增加重试机制
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=2))

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
        data = self.getpq("/")
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item"))}

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
                # 增加容错，防止cdata丢失
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
        """
        [核心修复] 获取视频详情和播放地址
        """
        url = ids[0]
        data = self.getpq(url)
        djs = self.getjsdata(data)
        
        vn = data('meta[property="og:title"]').attr('content')
        if not vn: vn = data('h1').text()
        
        vod = {
            'vod_name': vn,
            'vod_remarks': data('.rb-new__info').text(),
            'vod_play_from': 'Xhamster',
            'vod_play_url': ''
        }
        
        plist = []
        try:
            # 尝试从不同路径获取源数据
            sources = {}
            if djs:
                if 'xplayerSettings' in djs and 'sources' in djs['xplayerSettings']:
                    sources = djs['xplayerSettings']['sources']
                elif 'videoModel' in djs and 'sources' in djs['videoModel']:
                    sources = djs['videoModel']['sources']

            # 1. 优先提取 HLS (m3u8) - 最稳定
            hls = sources.get('hls', {})
            if hls:
                for fmt, info in hls.items():
                    link = ""
                    if isinstance(info, str):
                        link = info
                    elif isinstance(info, dict):
                        link = info.get('url', '')
                    
                    # [关键] 必须以 http 开头，防止获取到哈希值
                    if link and link.startswith('http'):
                        # 0@@@@ 表示无需二次解析
                        encoded = self.e64(f'0@@@@{link}')
                        plist.append(f"HLS-{fmt}${encoded}")

            # 2. 提取 MP4 (Standard)
            std = sources.get('standard', {})
            if std:
                # standard 下通常是 {h264: [...], av1: [...]}
                for fmt, info_list in std.items():
                    if isinstance(info_list, list):
                        for item in info_list:
                            link = item.get('url') or item.get('fallback')
                            label = item.get('label', fmt)
                            # 同样过滤无效链接
                            if link and link.startswith('http'):
                                encoded = self.e64(f'0@@@@{link}')
                                plist.append(f"{label}${encoded}")
            
            # 3. 备用方案：如果JSON提取失败，尝试从页面 input 获取
            if not plist:
                inp = data('input#url-input').attr('value')
                if inp and inp.startswith('http'):
                    plist.append(f"备用线路${self.e64(f'0@@@@{inp}')}")

        except Exception as e:
            print(f"Detail Error: {e}")
        
        if not plist:
            plist.append(f"解析失败(需更新)${self.e64(f'1@@@@{url}')}")

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f'/search/{key}?page={pg}')
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item")), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        try:
            ids = self.d64(id).split('@@@@')
            url = ids[1]
            
            # m3u8 走本地代理处理，解决跨域和TS流问题
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

    def gethost(self):
        """获取真实域名 - 增加容错处理"""
        try:
            # 3秒超时，如果失败则返回备用域名，防止APP卡死
            response = requests.get('https://xhamster.com',
                                  proxies=self.proxies,
                                  headers=self.headers,
                                  allow_redirects=False,
                                  verify=False,
                                  timeout=3)
            if 'Location' in response.headers:
                return response.headers['Location'].rstrip('/')
            return "https://xhamster.com"
        except:
            # 如果请求失败，直接返回常用的备用域名，确保APP能进界面
            return "https://zn.xhamster.com"

    def getpq(self, path=''):
        h = '' if path.startswith('http') else self.host
        url = f'{h}{path}'
        try:
            # verify=False 很重要，解决盒子SSL报错
            response = self.session.get(url, timeout=10, verify=False)
            response.encoding = 'utf-8'
            return pq(response.text)
        except Exception as e:
            print(f"PQ Error: {e}")
            return pq("")

    def getjsdata(self, data):
        """
        [优化] 使用正则提取JSON，比字符串分割更健壮
        """
        html = data("script[id='initials-script']").text()
        if not html: return {}
        try:
            # 尝试正则匹配
            match = re.search(r'window\.initials\s*=\s*({.*?});', html, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # 尝试分割
            part = html.split('initials=')[-1].strip()
            if part.endswith(';'): part = part[:-1]
            return json.loads(part)
        except:
            return {}

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
