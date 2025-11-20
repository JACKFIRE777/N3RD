# -*- coding: utf-8 -*-
# 完整修复版（保留原有一级菜单逻辑）
# by @嗷呜 （已由 ChatGPT 修复播放/代理/解析相关问题）
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
        初始化：设置代理、Session 和默认 headers
        extend: json 字符串形式的 proxies 配置
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
        # 可自定义爬虫名
        return "XHamster"

    def isVideoFormat(self, url):
        # 简单判断是否为视频文件
        try:
            url = url.lower()
            return any(url.endswith(ext) for ext in ['.m3u8', '.mp4', '.ts'])
        except Exception:
            return False

    def manualVideoCheck(self):
        # 可选实现：手动视频校验逻辑
        return []

    def destroy(self):
        # 清理资源
        try:
            self.session.close()
        except Exception:
            pass

    def homeContent(self, filter):
        """
        保留用户要求的一级菜单（cateManual），并返回 filters（保持原逻辑）
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
            # 原代码对非 4K 添加 filters（保持）
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
        关键修复点：兼容 xplayerSettings.sources 新结构（standard + hls），优先使用标准 URL（standard.list）和 hls
        输出格式： quality$base64(flag@@@@url)
        flag 使用 0 表示直接播放器可播放，备用 fallback 使用 1 表示页面地址
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

            # standard 可能是一个字典，里面每个 key 对应一个质量数组
            std = xsrc.get("standard", {}) or {}
            for qname, arr in std.items():
                if isinstance(arr, list):
                    for item in arr:
                        real = item.get("url") or item.get("fallback")
                        lbl = item.get("label") or item.get("quality") or qname
                        if real:
                            b64 = self.e64(f"0@@@@{real}")
                            plist.append(f"{lbl}${b64}")

            # hls 字段通常是一个字典，key = 质量，value = {url: '...'}
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

            # 去重并排序：按质量名中数字降序（例如 1080, 720 ...）
            def sort_key(s):
                name = s.split('$')[0]
                num = ''.join(filter(str.isdigit, name))
                num = int(num) if num else 0
                return -num

            # 先尝试去重（以 URL 为准）
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

            # 如果没有任何解析到的播放源，作为兜底使用页面地址
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


def playerContent(self, flag, id, vipFlags):
    ids = self.d64(id).split('@@@@')
    url = ids[1] if len(ids) > 1 else ''

    # 判断是否为 m3u8
    if url.endswith(".m3u8"):
        try:
            # 第一次请求，用于获取真正的跳转 URL
            r = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=True, timeout=10)
            real_url = r.url     # 最终跳转后的带 token 的 m3u8

            # 交给本地代理解析 ts
            real_url = self.proxy(real_url, "m3u8")
        except Exception as e:
            print("m3u8跳转失败：", e)
            real_url = url
    else:
        real_url = url

    return {
        'parse': int(ids[0]) if ids and ids[0].isdigit() else 0,
        'url': real_url,
        'header': self.headers
    }



    
    def localProxy(self, param):
        """
        本地代理入口：区分 m3u8 和 ts（或其他）
        """
        url = self.d64(param['url'])
        if param.get('type') == 'm3u8':
            return self.m3Proxy(url)
        else:
            return self.tsProxy(url)

    def gethost(self):
        """
        更稳健的获取主域名方法：优先尝试请求并处理 3xx 重定向 Location，否则退回默认
        """
        try:
            # 使用 allow_redirects=False 来获取 Location header，如果没有再尝试 allow_redirects=True
            try:
                response = requests.get('https://xhamster.com', proxies=self.proxies, headers=self.headers, allow_redirects=False, timeout=10)
                if response.status_code in (301, 302) and response.headers.get('Location'):
                    return response.headers['Location'].rstrip('/')
                # 如果没有 Location，则直接使用最终 URL（有时会被重定向到区域站点）
            except Exception:
                response = requests.get('https://xhamster.com', proxies=self.proxies, headers=self.headers, allow_redirects=True, timeout=10)
            # 尝试从 response.url 提取主机
            if response and hasattr(response, 'url'):
                parsed = urlparse(response.url)
                return f"{parsed.scheme}://{parsed.netloc}"
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
        # 兜底
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
            # 使用更健壮的选择器和空值保护
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
        """
        获取页面并返回 PyQuery 对象。path 可以是完整 URL 或相对 path。
        """
        h = '' if path.startswith('http') else self.host
        try:
            response = self.session.get(f'{h}{path}', timeout=15)
            response.encoding = response.apparent_encoding
            text = response.text
        except Exception as e:
            print(f"请求失败 {h}{path} : {e}")
            # 兜底返回空文档
            text = ''
        try:
            return pq(text)
        except Exception as e:
            # 如果解析失败，尝试以 utf-8 bytes 再解析
            try:
                return pq(text.encode('utf-8'))
            except Exception:
                print(str(e))
                return pq('')

    def getjsdata(self, data):
        """
        从页面中提取 id='initials-script' 的脚本内 JSON 数据，兼容多种写法
        """
        try:
            vhtml = data("script[id='initials-script']").text()
            if not vhtml:
                # 尝试匹配包含 initials= 的脚本
                scripts = data("script").items()
                for s in scripts:
                    txt = s.text()
                    if 'initials=' in txt:
                        vhtml = txt
                        break
            if not vhtml:
                return {}
            # 找到 initials= 后取 JSON
            if 'initials=' in vhtml:
                jpart = vhtml.split('initials=', 1)[-1].strip()
                # 去掉结尾的 ; 或 var 等
                if jpart.endswith(';'):
                    jpart = jpart[:-1]
                return json.loads(jpart)
            # fallback 直接尝试 json.loads
            return json.loads(vhtml)
        except Exception as e:
            print(f"解析页面内 JS 数据失败: {e}")
            return {}

def m3Proxy(self, url):
    try:
        # 直接获取真实 m3u8 内容
        r = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=True, timeout=10)
        text = r.text
    except:
        return [500, "text/plain", ""]

    base = url.rsplit('/', 1)[0]
    host = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    lines = text.split("\n")
    new = []

    for line in lines:
        if line.startswith("#") or not line.strip():
            new.append(line)
            continue

        # 绝对路径
        if line.startswith("http"):
            new.append(self.proxy(line, "ts"))
        else:
            # 相对路径转绝对
            if line.startswith("/"):
                real = host + line
            else:
                real = base + "/" + line

            new.append(self.proxy(real, "ts"))

    return [200, "application/vnd.apple.mpegurl", "\n".join(new)]


    def tsProxy(self, url):
        """
        代理 ts 或其他媒体片段：直接请求并返回二进制
        返回 [status_code, content_type, content_bytes]
        """
        try:
            data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True, timeout=20)
            return [200, data.headers.get('Content-Type', 'application/octet-stream'), data.content]
        except Exception as e:
            print(f"请求 TS 文件失败: {e}")
            return [500, "application/octet-stream", b'']

    def proxy(self, data, type='img'):
        """
        生成代理链接（如果配置了 self.proxies 则返回本地代理地址，否则返回原始地址）
        约定：getProxyUrl() 应由运行环境/框架实现，返回本地代理基础 URL（例如 http://127.0.0.1:12010/proxy?）
        生成格式：<getProxyUrl()>&url=<base64>&type=<type>
        """
        try:
            if data and len(self.proxies):
                # 如果存在 proxies，则走本地代理（通过 base64 编码）
                return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
            else:
                # 没有代理则直接返回原始链接
                return data
        except Exception as e:
            print(f"proxy 生成失败: {e}")
            return data
