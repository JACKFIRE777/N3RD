# -*- coding: utf-8 -*-
# by @嗷呜 & 修复优化版
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

# 禁用SSL警告，防止安卓/TV盒子上报错
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}
        
        # 这里的 host 直接写死，不要去动态获取，否则启动会卡住
        self.host = "https://xhamster.com"
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.host}/',
            'Origin': self.host,
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        self.session = Session()
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)
        # 设置连接超时，防止无限转圈
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
        # 首页分类配置，不需要网络请求，应该能瞬间显示
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
        # 获取首页视频
        data = self.getpq("/")
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
            # 拼接URL时注意斜杠
            url = f'{tid}{extend.get("type", "")}/{pg}'
            data = self.getpq(url)
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
                        'vod_remarks': str(i.get("subscriptionModel", {}).get("subscribers", "")),
                        'style': {'ratio': 1.778, 'type': 'rect'}
                    })
        
        elif tid == '/categories':
            result['pagecount'] = pg
            data = self.getpq(tid)
            self.cdata = self.getjsdata(data)
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
                # 这里的逻辑依赖于之前缓存的cdata，如果session重置可能会有问题，建议重新获取一次
                if not hasattr(self, 'cdata'):
                     self.cdata = self.getjsdata(self.getpq('/categories'))
                
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
        # 获取视频详情
        url = ids[0]
        data = self.getpq(url)
        djs = self.getjsdata(data)
        
        # 标题兜底
        try:
            vn = data('h1').text()
            if not vn: vn = data('meta[property="og:title"]').attr('content')
        except: vn = "Unknown Video"

        # 视频信息提取
        vod = {
            'vod_name': vn,
            'vod_play_from': 'Xhamster',
            'vod_play_url': '',
            'vod_content': data('div.rb-new__info').text()
        }
        
        plist = []
        try:
            # 尝试多种路径获取 sources
            sources = {}
            if djs:
                if 'xplayerSettings' in djs and 'sources' in djs['xplayerSettings']:
                    sources = djs['xplayerSettings']['sources']
                elif 'videoModel' in djs and 'sources' in djs['videoModel']:
                    sources = djs['videoModel']['sources']

            # 1. 标准 MP4
            std = sources.get('standard', {})
            if std:
                for fmt, val in std.items():
                    if isinstance(val, list):
                        for v in val:
                            u = v.get('url') or v.get('fallback')
                            if u and u.startswith('http'):
                                label = v.get('label', fmt)
                                plist.append(f"{label}${self.e64('0@@@@'+u)}")

            # 2. HLS (m3u8) - 推荐
            hls = sources.get('hls', {})
            if hls:
                for fmt, val in hls.items():
                    u = ""
                    if isinstance(val, str): u = val
                    elif isinstance(val, dict): u = val.get('url')
                    
                    if u and u.startswith('http'):
                        # 把 m3u8 放前面
                        plist.insert(0, f"HLS-{fmt}${self.e64('0@@@@'+u)}")
            
            # 如果解析失败
            if not plist:
                plist.append(f"解析空(重试)${self.e64('1@@@@'+url)}")

        except Exception as e:
            print(f"Error detail: {e}")
            plist.append(f"Error${self.e64('1@@@@'+url)}")
        
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
            
            if '.m3u8' in url:
                url = self.proxy(url, 'm3u8')
            
            return {
                'parse': 0, # 直接播放
                'url': url,
                'header': self.headers
            }
        except:
            return {'parse': 1, 'url': '', 'header': {}}

    def localProxy(self, param):
        try:
            url = self.d64(param['url'])
            type_ = param.get('type')
            
            if type_ == 'm3u8':
                return self.m3Proxy(url)
            elif type_ == 'ts':
                return self.tsProxy(url)
            elif type_ == 'img':
                resp = self.session.get(url, stream=True, timeout=10, verify=False)
                return [200, "image/jpeg", resp.content]
        except Exception as e:
            return [500, "text/plain", str(e)]

    def gethost(self):
        # 已在 init 中硬编码，此方法留空或返回固定值
        return "https://xhamster.com"

    def getlist(self, data):
        vlist = []
        for i in data.items():
            try:
                href = i('.role-pop').attr('href')
                if not href: continue
                
                img = i('.role-pop img').attr('src')
                if not img: img = i('img').attr('src')
                
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

    def getpq(self, path):
        # 统一请求入口，处理域名拼接
        if path.startswith('http'):
            url = path
        else:
            if not path.startswith('/'): path = '/' + path
            url = f"{self.host}{path}"
            
        try:
            # verify=False 是关键，防止盒子系统老旧报错
            response = self.session.get(url, timeout=8, verify=False)
            response.encoding = 'utf-8'
            return pq(response.text)
        except Exception as e:
            print(f"Req Error: {e}")
            return pq("<div></div>") # 返回空节点防止崩溃

    def getjsdata(self, data):
        # 健壮的JSON提取
        try:
            txt = data("script[id='initials-script']").text()
            if not txt: return {}
            
            # 优先正则提取
            m = re.search(r'window\.initials\s*=\s*({.*});', txt)
            if m: return json.loads(m.group(1))
            
            # 备用分割法
            part = txt.split('initials=')[-1].strip()
            if part.endswith(';'): part = part[:-1]
            return json.loads(part)
        except:
            return {}

    def m3Proxy(self, url):
        try:
            r = self.session.get(url, allow_redirects=True, timeout=10, verify=False)
            content = r.text
            
            base_url = url.rsplit('/', 1)[0]
            new_lines = []
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    new_lines.append(line)
                    continue
                
                # 补全URL
                ts_url = line
                if not ts_url.startswith('http'):
                    if ts_url.startswith('/'):
                        p = urlparse(url)
                        ts_url = f"{p.scheme}://{p.netloc}{ts_url}"
                    else:
                        ts_url = f"{base_url}/{ts_url}"
                
                new_lines.append(self.proxy(ts_url, 'ts'))
            
            return [200, "application/vnd.apple.mpegur", '\n'.join(new_lines)]
        except:
            return [500, "text/plain", "error"]

    def tsProxy(self, url):
        try:
            r = self.session.get(url, stream=True, timeout=10, verify=False)
            return [200, "video/mp2t", r.content]
        except:
            return [404, "text/plain", ""]

    def e64(self, text):
        try:
            return b64encode(text.encode('utf-8')).decode('utf-8')
        except: return ""

    def d64(self, text):
        try:
            return b64decode(text.encode('utf-8')).decode('utf-8')
        except: return ""

    def proxy(self, data, type='img'):
        if data and self.proxies:
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        return data
