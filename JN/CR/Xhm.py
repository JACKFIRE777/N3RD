# -*- coding: utf-8 -*-
# by @嗷呜 & 修复优化
# Xhamster视频网站爬虫类，用于获取视频列表、详情和播放地址

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
    """Xhamster视频爬虫类，继承自基础Spider类"""

    def init(self, extend=""):
        """
        初始化爬虫配置
        Args:
            extend: 扩展配置，JSON格式的代理设置
        """
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}
        
        # [修复1] 统一 User-Agent 和 sec-ch-ua 为 Windows Chrome 133，避免指纹冲突
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
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
            'referer': '',  # 在后面动态更新
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'priority': 'u=1, i',
        }
        
        self.host = self.gethost()
        
        self.session = Session()
        self.headers.update({'origin': self.host, 'referer': f'{self.host}/'})
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)

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
            # 增加判空处理
            if jsdata and 'channels' in jsdata:
                for i in jsdata['channels']:
                    vdata.append({
                        'vod_id': f"two_click_" + i.get('channelURL'),
                        'vod_name': i.get('channelName'),
                        'vod_pic': self.proxy(i.get('siteLogoURL')),
                        'vod_year': f'videos:{i.get("videoCount")}',
                        'vod_tag': 'folder',
                        'vod_remarks': f'subscribers:{i.get("subscriptionModel", {}).get("subscribers", "")}',
                        'style': {'ratio': 1.778, 'type': 'rect'}
                    })
        
        elif tid == '/categories':
            result['pagecount'] = pg
            data = self.getpq(tid)
            self.cdata = self.getjsdata(data)
            # 增加判空处理，防止结构变化导致报错
            try:
                items = self.cdata['layoutPage']['store']['popular']['assignable']
                for i in items:
                    vdata.append({
                        'vod_id': "one_click_" + i.get('id'),
                        'vod_name': i.get('name'),
                        'vod_pic': '',
                        'vod_tag': 'folder',
                        'style': {'ratio': 1.778, 'type': 'rect'}
                    })
            except: pass
        
        elif tid == '/pornstars':
            data = self.getpq(f'{tid}/{pg}')
            pdata = self.getjsdata(data)
            try:
                items = pdata['pagesPornstarsComponent']['pornstarListProps']['pornstars']
                for i in items:
                    vdata.append({
                        'vod_id': f"two_click_" + i.get('pageURL'),
                        'vod_name': i.get('name'),
                        'vod_pic': self.proxy(i.get('imageThumbUrl')),
                        'vod_remarks': i.get('translatedCountryName'),
                        'vod_tag': 'folder',
                        'style': {'ratio': 1.778, 'type': 'rect'}
                    })
            except: pass
        
        elif 'one_click' in tid:
            result['pagecount'] = pg
            tid = tid.split('click_')[-1]
            try:
                for i in self.cdata['layoutPage']['store']['popular']['assignable']:
                    if i.get('id') == tid:
                        for j in i['items']:
                            vdata.append({
                                'vod_id': f"two_click_" + j.get('url'),
                                'vod_name': j.get('name'),
                                'vod_pic': self.proxy(j.get('thumb')),
                                'vod_tag': 'folder',
                                'style': {'ratio': 1.778, 'type': 'rect'}
                            })
            except: pass
        
        result['list'] = vdata
        return result

    def detailContent(self, ids):
        """
        获取视频详情和播放地址（修复核心逻辑）
        """
        data = self.getpq(ids[0])
        djs = self.getjsdata(data)
        
        vn = data('meta[property="og:title"]').attr('content') or "Xhamster Video"
        
        dtext = data('#video-tags-list-container')
        href = dtext('a').attr('href')
        title = dtext('span[class*="body-bold-"]').eq(0).text()
        
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
        
        try:
            plist = []
            # [修复2] 增加对数据结构的兼容性检查
            sources = djs.get('xplayerSettings', {}).get('sources', {})
            if not sources:
                # 备用路径：有时候数据在 videoModel 中
                sources = djs.get('videoModel', {}).get('sources', {})

            standard_sources = sources.get('standard', {})
            hls_sources = sources.get('hls', {})

            # 自定义排序函数
            def custom_sort_key(url_item):
                quality = url_item.split('$')[0]
                number = ''.join(filter(str.isdigit, quality))
                number = int(number) if number else 0
                return -number, quality
            
            # 1. 处理 MP4 (Standard)
            if standard_sources:
                for fmt, value in standard_sources.items(): # fmt: av1, h264
                    if isinstance(value, list):
                        for info in value:
                            url = info.get("url") or info.get("fallback")
                            label = info.get('label') or info.get('quality') or fmt
                            
                            # [重要修复] 过滤无效的哈希字符串，必须是 http 开头
                            if url and isinstance(url, str) and url.startswith('http'):
                                id = self.e64(f'{0}@@@@{url}')
                                plist.append(f"{label}${id}")
            
            plist.sort(key=custom_sort_key)
            
            # 2. 处理 HLS (m3u8)，通常 HLS 最稳定
            if hls_sources:
                for fmt, info in hls_sources.items():
                    url = None
                    # HLS 数据结构有时是字符串直接 URL，有时是字典
                    if isinstance(info, str):
                        url = info
                    elif isinstance(info, dict):
                        url = info.get('url')
                    
                    # [重要修复] 校验 URL 有效性
                    if url and isinstance(url, str) and url.startswith('http'):
                        encoded = self.e64(f'{0}@@@@{url}')
                        # 将 HLS 放在列表前部，通常播放成功率更高
                        plist.insert(0, f"{fmt} (HLS)${encoded}")
            
            # 如果没有找到任何有效地址，尝试备用解析（虽然原代码逻辑未实现具体解析）
            if not plist:
                 plist = [f"解析失败(需验证)${self.e64(f'{1}@@@@{ids[0]}')}"]

        except Exception as e:
            plist = [f"错误${self.e64(f'{1}@@@@{ids[0]}')}"]
            print(f"获取视频信息失败: {str(e)}")
        
        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f'/search/{key}?page={pg}')
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item")), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        ids = self.d64(id).split('@@@@')
        url = ids[1]
        
        # m3u8 走本地代理处理跨域和 TS 拼接
        if '.m3u8' in url: 
            url = self.proxy(url, 'm3u8')
        
        return {
            'parse': int(ids[0]),
            'url': url,
            'header': self.headers
        }

    def localProxy(self, param):
        url = self.d64(param['url'])
        if param.get('type') == 'm3u8':
            return self.m3Proxy(url)
        else:
            return self.tsProxy(url)

    def gethost(self):
        try:
            response = requests.get('https://xhamster.com',
                                  proxies=self.proxies,
                                  headers=self.headers,
                                  allow_redirects=False,
                                  timeout=5)
            return response.headers.get('Location', 'https://xhamster.com')
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            return "https://zn.xhamster.com"

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except:
            return ""

    def d64(self, encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except:
            return ""

    def getlist(self, data):
        vlist = []
        for i in data.items():
            vlist.append({
                'vod_id': i('.role-pop').attr('href'),
                'vod_name': i('.video-thumb-info a').text(),
                'vod_pic': self.proxy(i('.role-pop img').attr('src')),
                'vod_year': i('.video-thumb-info .video-thumb-views').text().split(' ')[0],
                'vod_remarks': i('.role-pop div[data-role="video-duration"]').text(),
                'style': {'ratio': 1.778, 'type': 'rect'}
            })
        return vlist

    def getpq(self, path=''):
        h = '' if path.startswith('http') else self.host
        try:
            response = self.session.get(f'{h}{path}', timeout=10).text
            return pq(response)
        except Exception as e:
            print(f"Request Error: {str(e)}")
            return pq("")

    def getjsdata(self, data):
        """
        [修复3] 使用正则提取 JSON，比字符串分割更安全
        """
        vhtml = data("script[id='initials-script']").text()
        try:
            # 尝试使用正则匹配 window.initials = {...};
            pattern = r'window\.initials\s*=\s*({.+?});'
            match = re.search(pattern, vhtml, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # 如果正则失败，回退到原来的分割方法，但增加安全性
            part = vhtml.split('initials=')
            if len(part) > 1:
                content = part[-1].strip()
                if content.endswith(';'):
                    content = content[:-1]
                return json.loads(content)
            return {}
        except Exception as e:
            print(f"JSON解析错误: {str(e)}")
            return {}

    def m3Proxy(self, url):
        try:
            ydata = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=True, timeout=10)
            data = ydata.content.decode('utf-8')
            
            # 修正基础URL获取逻辑
            base_url = url.rsplit('/', 1)[0]
            
            lines = data.strip().split('\n')
            for index, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 处理 URL 拼接
                if not line.startswith('http'):
                    if line.startswith('/'):
                        parsed = urlparse(url)
                        line = f"{parsed.scheme}://{parsed.netloc}{line}"
                    else:
                        line = f"{base_url}/{line}"
                
                # 将分片地址转为代理地址
                lines[index] = self.proxy(line, 'ts')
            
            data = '\n'.join(lines)
            return [200, "application/vnd.apple.mpegur", data]
        except Exception as e:
            print(f"m3Proxy Error: {e}")
            return [500, "text/plain", str(e)]

    def tsProxy(self, url):
        try:
            # TS流需要 stream=True
            resp = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True, timeout=10)
            return [200, resp.headers.get('Content-Type', 'video/mp2t'), resp.content]
        except:
            return [404, "text/plain", ""]

    def proxy(self, data, type='img'):
        if data and len(self.proxies):
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else:
            return data
