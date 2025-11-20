# -*- coding: utf-8 -*-
# 修复版 by ChatGPT（基于你原始脚本改进）
# 作者标识：@嗷呜 （原作者） + ChatGPT 修复
import json
import sys
from base64 import b64decode, b64encode
from urllib.parse import urlparse

import requests
from pyquery import PyQuery as pq
from requests import Session

sys.path.append('..')
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    """
    修复版 Spider：兼容新版页面结构与播放器数据获取逻辑
    依赖 base.spider Spider 基类提供的一些方法（如 getProxyUrl 等）。
    """

    def init(self, extend=""):
        try:
            self.proxies = json.loads(extend) if extend else {}
        except:
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
        self.headers.update({'origin': self.host, 'referer': f'{self.host}/'})
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)

    def getName(self):
        return "Xhamster (修复版)"

    def isVideoFormat(self, url):
        # 简单判断：是否包含视频常见后缀或视频页面路径关键词
        url = url or ""
        return any(s in url for s in ('.m3u8', '.mp4', '/video/', '/watch/'))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        try:
            self.session.close()
        except:
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
        data = self.getpq()
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item"))}

    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}

        if tid in ['/4k', '/newest', '/best'] or 'two_click_' in tid:
            if 'two_click_' in tid:
                tid = tid.split('click_')[-1]
            # extend 可能为 None
            ext_type = extend.get("type", "") if isinstance(extend, dict) else ""
            data = self.getpq(f'{tid}{ext_type}/{pg}')
            vdata = self.getlist(data(".thumb-list--sidebar .thumb-list__item"))

        elif tid == '/channels':
            data = self.getpq(f'{tid}/{pg}')
            jsdata = self.getjsdata(data)
            if not jsdata:
                return {'list': [], 'page': pg}
            for i in jsdata.get('channels', []):
                vdata.append({
                    'vod_id': f"two_click_" + (i.get('channelURL') or ''),
                    'vod_name': i.get('channelName'),
                    'vod_pic': self.proxy(i.get('siteLogoURL')),
                    'vod_year': f'videos:{i.get("videoCount")}',
                    'vod_tag': 'folder',
                    'vod_remarks': f'subscribers:{i.get("subscriptionModel", {}).get("subscribers", 0)}',
                    'style': {'ratio': 1, 'type': 'rect'}
                })

        elif tid == '/categories':
            result['pagecount'] = pg
            data = self.getpq(tid)
            self.cdata = self.getjsdata(data) or {}
            for i in (self.cdata.get('layoutPage', {}).get('store', {}).get('popular', {}).get('assignable') or []):
                vdata.append({
                    'vod_id': "one_click_" + (i.get('id') or ''),
                    'vod_name': i.get('name'),
                    'vod_pic': '',
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.778, 'type': 'rect'}
                })

        elif tid == '/pornstars':
            data = self.getpq(f'{tid}/{pg}')
            pdata = self.getjsdata(data) or {}
            for i in (pdata.get('pagesPornstarsComponent', {}).get('pornstarListProps', {}).get('pornstars') or []):
                vdata.append({
                    'vod_id': f"two_click_" + (i.get('pageURL') or ''),
                    'vod_name': i.get('name'),
                    'vod_pic': self.proxy(i.get('imageThumbUrl')),
                    'vod_remarks': i.get('translatedCountryName'),
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.778, 'type': 'rect'}
                })

        elif 'one_click' in tid:
            result['pagecount'] = pg
            tid = tid.split('click_')[-1]
            for i in (self.cdata.get('layoutPage', {}).get('store', {}).get('popular', {}).get('assignable') or []):
                if i.get('id') == tid:
                    for j in (i.get('items') or []):
                        vdata.append({
                            'vod_id': f"two_click_" + (j.get('url') or ''),
                            'vod_name': j.get('name'),
                            'vod_pic': self.proxy(j.get('thumb')),
                            'vod_tag': 'folder',
                            'style': {'ratio': 1.778, 'type': 'rect'}
                        })

        result['list'] = vdata
        return result

    def detailContent(self, ids):
        """
        ids: 列表，通常第一个是视频页 URL 或带前缀的链接
        """
        url = ids[0]
        data = self.getpq(url)
        djs = self.getjsdata(data) or {}
        # 首先尝试从 meta 获取标题
        vn = data('meta[property="og:title"]').attr('content') or data('title').text() or url
        dtext = data('#video-tags-list-container')
        href = dtext('a').attr('href') if dtext else None
        title = dtext('span[class*="body-bold-"]').eq(0).text() if dtext else ''
        pdtitle = ''
        if href:
            pdtitle = '[a=cr:' + json.dumps({'id': 'two_click_' + href, 'name': title}) + '/]' + title + '[/a]'

        vod = {
            'vod_name': vn,
            'vod_director': pdtitle,
            'vod_remarks': data('.rb-new__info').text() or '',
            'vod_play_from': 'Xhamster',
            'vod_play_url': ''
        }

        plist = []
        try:
            # 新版可能放在 djs["player"]["sources"] 或 djs["xplayerSettings"]["sources"]
            d = {}
            if isinstance(djs, dict):
                if 'player' in djs and isinstance(djs['player'], dict):
                    d = djs['player'].get('sources', {}) or {}
                elif 'xplayerSettings' in djs:
                    d = djs['xplayerSettings'].get('sources', {}) or {}
                else:
                    # 有些页面直接把 sources 放在 initials['sources'] 或类似字段
                    # 尝试常见字段
                    for key in ('sources', 'videoSources', 'playerSources'):
                        if key in djs:
                            d = djs.get(key) or {}
                            break

            # 解析 mp4 列表（可能是数组或字典）
            mp4_list = []
            if isinstance(d.get('mp4'), list):
                mp4_list = d.get('mp4')
            elif isinstance(d.get('mp4'), dict):
                # 有时 mp4 是 dict keyed by quality
                for q, info in d.get('mp4', {}).items():
                    if isinstance(info, dict) and info.get('url'):
                        mp4_list.append({'quality': q, 'url': info.get('url')})
                    elif isinstance(info, list):
                        for it in info:
                            mp4_list.append({'quality': it.get('quality') or q, 'url': it.get('url')})

            # 有时 sources 里直接是各 label: url 格式 (standard/hls)
            # 处理 mp4_list
            for item in mp4_list:
                url_item = item.get('url') or item.get('src') or item.get('file')
                q = item.get('quality') or item.get('label') or 'mp4'
                if url_item:
                    plist.append((int(''.join(filter(str.isdigit, q)) or 0), q, url_item))

            # 处理标准/hd 等（你原来取 standard 字段）
            if isinstance(d.get('standard'), dict):
                for key, val in d.get('standard').items():
                    if isinstance(val, list):
                        for info in val:
                            url_item = info.get('url') or info.get('fallback')
                            label = info.get('label') or info.get('quality') or key
                            if url_item:
                                plist.append((int(''.join(filter(str.isdigit, label)) or 0), label, url_item))
                    elif isinstance(val, dict):
                        url_item = val.get('url') or val.get('fallback')
                        label = val.get('label') or val.get('quality') or key
                        if url_item:
                            plist.append((int(''.join(filter(str.isdigit, label)) or 0), label, url_item))

            # 处理 hls / m3u8
            if isinstance(d.get('hls'), dict):
                # hls 可能是 { 'url': '...', 'variants': {...} }
                hls = d.get('hls')
                if isinstance(hls.get('url'), str):
                    plist.append((9999, 'hls', hls.get('url')))
                else:
                    # 遍历可能存在的 variants
                    for fmt, info in hls.items():
                        if isinstance(info, dict) and info.get('url'):
                            label = fmt
                            plist.append((9999, label, info.get('url')))

            # 另外尝试直接从 djs 中获取常见字段
            if not plist:
                # 尝试 djs.get('sources') 直接为 list/dict
                if isinstance(djs.get('sources'), dict):
                    for k, info in djs.get('sources').items():
                        if isinstance(info, list):
                            for it in info:
                                url_item = it.get('url') or it.get('file')
                                label = it.get('quality') or k
                                if url_item:
                                    plist.append((int(''.join(filter(str.isdigit, label)) or 0), label, url_item))
                        elif isinstance(info, dict):
                            url_item = info.get('url') or info.get('file')
                            label = info.get('quality') or k
                            if url_item:
                                plist.append((int(''.join(filter(str.isdigit, label)) or 0), label, url_item))

            # 若还是没有，尝试页面内寻找直接的 video 标签或 source 标签
            if not plist:
                video_src = data('video source').attr('src') or data('video').attr('src')
                if video_src:
                    plist.append((0, 'video', video_src))

            # 排序：数字清晰度降序（大数字优先），hls 优先（9999）
            plist.sort(key=lambda x: (-x[0], x[1]))

            # 最终构造播放列表格式：label$Base64
            final_plist = []
            for _, label, u in plist:
                final_plist.append(f"{label}${self.e64(f'0@@@@{u}')}")
            plist = final_plist

        except Exception as e:
            # 出错时作为后备：把详情页当成需要二次解析的地址
            print(f"detailContent 解析异常: {str(e)}")
            plist = [f"{vn}${self.e64(f'1@@@@{url}')}"]

        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f'/search/{key}?page={pg}')
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item")), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        ids = self.d64(id).split('@@@@')
        # 如果 m3u8 地址，确保 proxy 处理
        if '.m3u8' in ids[1]:
            ids[1] = self.proxy(ids[1], 'm3u8')
        return {'parse': int(ids[0]), 'url': ids[1], 'header': self.headers}

    def localProxy(self, param):
        url = self.d64(param['url'])
        if param.get('type') == 'm3u8':
            return self.m3Proxy(url)
        else:
            return self.tsProxy(url)

    def gethost(self):
        """
        更健壮的获取主机：优先尝试直接访问并处理可能的重定向，回退到备用域名。
        """
        try:
            resp = requests.get('https://xhamster.com', proxies=self.proxies, headers=self.headers, allow_redirects=False, timeout=8)
            # 如果 Location 存在，返回 scheme://netloc
            if resp.status_code in (301, 302) and resp.headers.get('Location'):
                loc = resp.headers.get('Location')
                # 若 Location 是完整 URL，取其 scheme+netloc
                parsed = urlparse(loc)
                if parsed.scheme and parsed.netloc:
                    return f"{parsed.scheme}://{parsed.netloc}"
                else:
                    # 非完整 URL 时尝试拼接
                    base = urlparse('https://xhamster.com')
                    return f"{base.scheme}://{base.netloc}"
            # 未重定向：使用当前请求的 URL 的主机
            parsed_req = urlparse(resp.url)
            return f"{parsed_req.scheme}://{parsed_req.netloc}"
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            return "https://zn.xhamster.com"

    def e64(self, text):
        try:
            return b64encode(text.encode('utf-8')).decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self, encoded_text):
        try:
            return b64decode(encoded_text.encode('utf-8')).decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    def getlist(self, data):
        vlist = []
        for i in data.items():
            # 新版页面常用链接选择器：a.video-thumb__link 或 .video-thumb-info a
            href = i("a.video-thumb__link").attr("href") or i('.video-thumb-info a').attr('href') or i('.role-pop').attr('href')
            name = i('.video-thumb-info a').text() or i('.role-pop').text() or i('a').text()
            img = i('.role-pop img').attr('src') or i('img').attr('src')
            views = i('.video-thumb-info .video-thumb-views').text().split(' ')[0] if i('.video-thumb-info .video-thumb-views').text() else ''
            duration = i('.role-pop div[data-role="video-duration"]').text() or ''
            vlist.append({
                'vod_id': href,
                'vod_name': name,
                'vod_pic': self.proxy(img),
                'vod_year': views,
                'vod_remarks': duration,
                'style': {'ratio': 1.778, 'type': 'rect'}
            })
        return vlist

    def getpq(self, path=''):
        h = '' if path.startswith('http') else self.host
        try:
            resp = self.session.get(f'{h}{path}', timeout=12)
            text = resp.text
            return pq(text)
        except Exception as e:
            # 二次尝试：直接 requests.get（不使用 session），并尝试不同编码
            try:
                resp = requests.get(f'{h}{path}', headers=self.headers, proxies=self.proxies, timeout=12)
                text = resp.text
                return pq(text)
            except Exception as e2:
                print(f"getpq 失败: {str(e2)}")
                return pq('')

    def getjsdata(self, data):
        """
        从页面中提取初始化 JSON。兼容多种可能的嵌入方式：
        - <script data-initial>...</script>
        - window.initials = {...};
        - <script id="initials-script">initials=...;</script>
        - 以及 pages 中可能直接有 player/sources 字段
        返回 dict 或 None
        """
        try:
            # 优先 data-initial 类型
            script = data("script[data-initial]").text()
            if script:
                # 有些站会把 JSON 直接放在 data-initial 中
                try:
                    return json.loads(script)
                except:
                    pass

            # 查找包含 window.initials 或 initials 的 script
            candidates = data("script").items()
            for s in candidates:
                txt = s.text() or ''
                if 'initials' in txt or 'window.initials' in txt or 'window._initials' in txt:
                    # 常见两种：initials = {...}; 或 window.initials = {...};
                    try:
                        # 提取第一个出现的左大括号到最后的闭合大括号（简单策略）
                        start = txt.find('{', txt.find('initials'))
                        if start != -1:
                            # 尝试找到对应结束位置：靠近末尾的 ; 前
                            # 这里采用从 "initials=" 后取到末尾然后去掉尾部的分号
                            part = txt.split('initials')[-1]
                            # 尝试用 等号分割
                            if '=' in part:
                                part = part.split('=', 1)[1].strip()
                            # 去掉尾部分号
                            if part.endswith(';'):
                                part = part[:-1]
                            # 有时会包裹在 ( ... )
                            part = part.strip()
                            # 尝试加载 JSON
                            return json.loads(part)
                    except Exception:
                        # 忽略，继续尝试其他脚本
                        continue

            # 备用：尝试直接 parse 页面中包含 player 字段的 JSON 片段
            # 查找 "player" 关键字附近的 { ... }
            body_text = data('body').text() or ''
            if '"player"' in body_text:
                try:
                    # 这是保守尝试，尽量不要抛异常
                    idx = body_text.find('"player"')
                    snippet = body_text[idx-200: idx+2000]  # 限定长度尝试解析
                    # 找第一个 { 开始
                    start = snippet.find('{')
                    if start != -1:
                        candidate = snippet[start:]
                        # 尝试修剪到最后一个 }
                        end = candidate.rfind('}')
                        if end != -1:
                            candidate = candidate[:end+1]
                            return json.loads(candidate)
                except Exception:
                    pass

        except Exception as e:
            print(f"getjsdata 出错: {str(e)}")
        return None

    def m3Proxy(self, url):
        ydata = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=False, timeout=12)
        data = None
        try:
            data = ydata.content.decode('utf-8')
        except:
            data = ydata.text
        if ydata.headers.get('Location'):
            try:
                url = ydata.headers['Location']
                data = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=12).content.decode('utf-8')
            except:
                pass

        lines = data.strip().split('\n')
        last_r = url[:url.rfind('/')] if '/' in url else url
        parsed_url = urlparse(url)
        durl = parsed_url.scheme + "://" + parsed_url.netloc

        for index, string in enumerate(lines):
            if '#EXT' not in string:
                if 'http' not in string:
                    domain = last_r if string.count('/') < 2 else durl
                    string = domain + ('' if string.startswith('/') else '/') + string
                lines[index] = self.proxy(string, string.split('.')[-1].split('?')[0])
        data = '\n'.join(lines)
        return [200, "application/vnd.apple.mpegurl", data]

    def tsProxy(self, url):
        data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True, timeout=20)
        return [200, data.headers.get('Content-Type', 'application/octet-stream'), data.content]

    def proxy(self, data, type='img'):
        if data and len(self.proxies):
            try:
                return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
            except:
                return data
        else:
            return data
