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
import urllib3

# 禁用SSL警告，防止老旧设备报错
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    """Xhamster视频爬虫类"""

    def init(self, extend=""):
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}
        
        # [优化] 更新 User-Agent 为 Windows，保持指纹一致
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Chromium";v="122", "Google Chrome";v="122"',
            'dnt': '1',
            'sec-ch-ua-mobile': '?0',
            'origin': '',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': '',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        # [保留] 使用动态获取Host，确保列表能加载
        self.host = self.gethost()
        
        self.session = Session()
        self.headers.update({'origin': self.host, 'referer': f'{self.host}/'})
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)
        # 设置超时和重试
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
        # 恢复原版逻辑
        data = self.getpq()
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
                # 拼接URL时增加容错
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
                    for i in self.cdata.get('layoutPage', {}).get('store', {}).get('popular', {}).get('assignable', []):
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
                    for i in pdata.get('pagesPornstarsComponent', {}).get('pornstarListProps', {}).get('pornstars', []):
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
                if hasattr(self, 'cdata') and self.cdata:
                     for i in self.cdata.get('layoutPage', {}).get('store', {}).get('popular', {}).get('assignable', []):
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
        核心修复：视频地址解析
        """
        url = ids[0]
        data = self.getpq(url)
        djs = self.getjsdata(data)
        
        # 获取标题
        vn = data('meta[property="og:title"]').attr('content')
        if not vn: vn = data('h1').text()
        
        # 获取详情
        desc = data('.rb-new__info').text()
        
        vod = {
            'vod_name': vn,
            'vod_remarks': desc,
            'vod_play_from': 'Xhamster',
            'vod_play_url': ''
        }
        
        plist = []
        try:
            # 提取源数据 (兼容多种结构)
            sources = {}
            if djs:
                if 'xplayerSettings' in djs and 'sources' in djs['xplayerSettings']:
                    sources = djs['xplayerSettings']['sources']
                elif 'videoModel' in djs and 'sources' in djs['videoModel']:
                    sources = djs['videoModel']['sources']

            # 1. 优先提取 HLS (m3u8)，兼容性最好
            hls = sources.get('hls', {})
            # HLS 有时是字典 {fmt: url}，有时是嵌套 {fmt: {url: ...}}
            if hls:
                for fmt, info in hls.items():
                    link = ""
                    if isinstance(info, str):
                        link = info
                    elif isinstance(info, dict):
                        link = info.get('url', '')
                    
                    # 关键：必须是 http 开头，且不是被混淆的 hash
                    if link and link.startswith('http'):
                        # 0@@@@ 表示直接播放，不需要二次解析
                        encoded = self.e64(f'0@@@@{link}')
                        plist.append(f"HLS-{fmt}${encoded}")

            # 2. 提取 MP4 (Standard)
            std = sources.get('standard', {})
            if std:
                for fmt, info_list in std.items():
                    if isinstance(info_list, list):
                        for item in info_list:
                            link = item.get('url') or item.get('fallback')
                            label = item.get('label', fmt)
                            if link and link.startswith('http'):
                                encoded = self.e64(f'0@@@@{link}')
                                plist.append(f"{label}${encoded}")

            # 3. 如果没找到任何地址，可能需要登录或被风控
            if not plist:
                # 尝试提取页面中的 fallback 链接
                input_url = data('input#url-input').attr('value')
                if input_url and input_url.startswith('http'):
                    plist.append(f"Fallback${self.e64(f'0@@@@{input_url}')}")

        except Exception as e:
            print(f"Detail Error: {e}")
        
        if not plist:
            # 最后的保底：标记错误
            plist.append(f"解析失败(请重试)${self.e64(f'1@@@@{url}')}")
            
        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f'/search/{key}?page={pg}')
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item")), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        try:
            ids = self.d64(id).split('@@@@')
            parse_type = int(ids[0])
            url = ids[1]
            
            # m3u8 走代理解决跨域和 TS 拼接问题
            if '.m3u8' in url:
                url = self.proxy(url, 'm3u8')
            
            return {
                'parse': 0,
                'url': url,
                'header': self.headers
            }
        except:
            return {'parse': 1, 'url': '', 'header': self.headers}

    def localProxy(self, param):
        try:
            url = self.d64(param['url'])
            type_ = param.get('type')
            
            if type_ == 'm3u8':
                return self.m3Proxy(url)
            elif type_ == 'ts':
                return self.tsProxy(url)
            else: # 图片
                return self.imgProxy(url)
        except Exception as e:
            return [500, "text/plain", str(e)]

    def gethost(self):
        """
        恢复 1.py 的逻辑，但增加容错防止 crash
        """
        try:
            # 允许重定向，获取正确的地区域名
            response = requests.get('https://xhamster.com',
                                  proxies=self.proxies,
                                  headers=self.headers,
                                  allow_redirects=True, # 必须为True才能拿到跳转后的URL
                                  verify=False,
                                  timeout=5)
            return response.url.rstrip('/') # 使用 response.url 获取最终跳转地址
        except Exception as e:
            print(f"GetHost Error: {e}")
            return "https://xhamster.com"

    def e64(self, text):
        try:
            return b64encode(text.encode('utf-8')).decode('utf-8')
        except: return ""

    def d64(self, text):
        try:
            return b64decode(text.encode('utf-8')).decode('utf-8')
        except: return ""

    def getlist(self, data):
        vlist = []
        for i in data.items():
            try:
                href = i('.role-pop').attr('href')
                if not href: continue
                
                # 修复图片提取
                img = i('.role-pop img').attr('src')
                if not img: img = i('img.thumb-image-container__image').attr('src')
                
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

    def getpq(self, path=''):
        h = '' if path.startswith('http') else self.host
        url = f'{h}{path}'
        try:
            # 使用 session 保持 cookie，这对获取正确数据很重要
            response = self.session.get(url, timeout=10, verify=False)
            response.encoding = 'utf-8' # 防止乱码
            return pq(response.text)
        except Exception as e:
            print(f"PQ Error: {e}")
            return pq("")

    def getjsdata(self, data):
        """
        修复提取逻辑：使用正则替代脆弱的字符串分割
        """
        html = data("script[id='initials-script']").text()
        if not html:
            return {}
        try:
            # 优先正则匹配
            match = re.search(r'window\.initials\s*=\s*({.*?});', html, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # 备用方案
            part = html.split('initials=')[-1].strip()
            if part.endswith(';'): part = part[:-1]
            return json.loads(part)
        except:
            return {}

    def m3Proxy(self, url):
        try:
            # 获取 m3u8 内容
            r = self.session.get(url, allow_redirects=True, timeout=10, verify=False)
            content = r.text
            
            # 简单的 m3u8 处理逻辑
            base_url = url.rsplit('/', 1)[0]
            new_lines = []
            
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    new_lines.append(line)
                    continue
                
                # 拼接 TS 完整路径
                ts_url = line
                if not ts_url.startswith('http'):
                    if ts_url.startswith('/'):
                        # 根目录绝对路径
                        parsed = urlparse(url)
                        ts_url = f"{parsed.scheme}://{parsed.netloc}{ts_url}"
                    else:
                        # 相对路径
                        ts_url = f"{base_url}/{ts_url}"
                
                # 将 TS 地址转换为代理地址
                new_lines.append(self.proxy(ts_url, 'ts'))
            
            return [200, "application/vnd.apple.mpegur", '\n'.join(new_lines)]
        except Exception as e:
            return [500, "text/plain", str(e)]

    def tsProxy(self, url):
        try:
            r = self.session.get(url, stream=True, timeout=10, verify=False)
            return [200, "video/mp2t", r.content]
        except:
            return [404, "text/plain", ""]
    
    def imgProxy(self, url):
        try:
            r = self.session.get(url, stream=True, timeout=5, verify=False)
            return [200, "image/jpeg", r.content]
        except:
            return [404, "image/jpeg", ""]

    def proxy(self, data, type='img'):
        if data and len(self.proxies):
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else:
            return data
