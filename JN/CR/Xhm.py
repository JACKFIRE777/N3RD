# -*- coding: utf-8 -*-
# 指定编码格式为 UTF-8，确保中文等字符正常显示
# by @嗷呜
# 作者标识

import json # 导入json库，用于处理JSON数据
import sys # 导入sys库，用于系统相关的操作，例如修改Python路径
from base64 import b64decode, b64encode # 导入base64编解码函数
from urllib.parse import urlparse # 导入urlparse，用于解析URL

import requests # 导入requests库，用于发送HTTP请求
from pyquery import PyQuery as pq # 导入PyQuery，用于HTML解析，类似于jQuery
from requests import Session # 导入requests.Session，用于保持会话和持久化参数
sys.path.append('..') # 将父目录添加到系统路径，可能为了导入自定义的模块
from base.spider import Spider # 从父目录的base模块导入自定义的Spider基类


class Spider(Spider):
    """
    爬虫类，继承自自定义的Spider基类。
    主要用于爬取特定网站（根据代码逻辑推测是 Xhamster）的数据。
    """

    def init(self, extend=""):
        """
        爬虫初始化方法。
        设置代理、HTTP请求头、会话（Session）等。
        """
        try:
            # 尝试将extend参数（预期为JSON字符串）解析为代理配置
            self.proxies = json.loads(extend)
        except:
            # 解析失败则设置为空代理
            self.proxies = {}
        # 设置默认的请求头，模拟浏览器访问
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36',
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'dnt': '1',
            'sec-ch-ua-mobile': '?0',
            'origin': '', # 初始为空
            'sec-fetch-site': 'cross-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': f'', # 初始为空
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'priority': 'u=1, i',
        }
        # 获取网站的主机地址，可能涉及到重定向（在gethost方法中实现）
        self.host = self.gethost()
        # 创建一个requests Session对象
        self.session = Session()
        # 更新请求头中的'origin'和'referer'字段为获取到的主机地址
        self.headers.update({'origin': self.host,'referer': f'{self.host}/'})
        # 为Session设置代理
        self.session.proxies.update(self.proxies)
        # 为Session设置请求头
        self.session.headers.update(self.headers)
        pass # 初始化结束

    def getName(self):
        """
        获取爬虫名称，未实现具体功能。
        """
        pass

    def isVideoFormat(self, url):
        """
        检查URL是否为视频格式，未实现具体功能。
        """
        pass

    def manualVideoCheck(self):
        """
        手动视频检查，未实现具体功能。
        """
        pass

    def destroy(self):
        """
        销毁方法，例如关闭Session等，未实现具体功能。
        """
        pass

    def homeContent(self, filter):
        """
        获取主页内容，主要用于定义分类列表和筛选器。
        :param filter: 是否开启筛选（未使用）
        :return: 包含分类和筛选器信息的字典
        """
        result = {}
        # 手动定义的分类列表，键为分类名，值为对应的路径或特殊标记
        cateManual = {
            "4K": "/4k",
            "国产": "two_click_/categories/chinese", # 包含特殊标记 'two_click_'
            "最新": "/newest",
            "最佳": "/best",
            "频道": "/channels",
            "类别": "/categories",
            "明星": "/pornstars"
        }
        classes = [] # 用于存储分类信息
        filters = {} # 用于存储筛选器信息
        for k in cateManual:
            # 遍历手动分类，构建classes列表
            classes.append({
                'type_name': k, # 分类名称
                'type_id': cateManual[k] # 分类ID/路径
            })
            # 如果不是'4K'分类，为其添加一个“4K”的筛选器（可能是通用筛选，但实现逻辑较简陋）
            if k != '4K': filters[cateManual[k]] = [{'key': 'type', 'name': '类型', 'value': [{'n': '4K', 'v': '/4k'}]}]
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        """
        获取主页视频内容（侧边栏的热门视频等）。
        :return: 包含视频列表的字典
        """
        # 获取主页的PyQuery对象
        data = self.getpq()
        # 调用getlist方法解析侧边栏（.thumb-list--sidebar）的视频列表
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item"))}

    def categoryContent(self, tid, pg, filter, extend):
        """
        获取分类页内容。
        :param tid: 分类ID
        :param pg: 页码
        :param filter: 是否启用筛选
        :param extend: 扩展参数，可能包含筛选条件
        :return: 包含视频列表和分页信息的字典
        """
        vdata = [] # 视频列表
        result = {}
        result['page'] = pg # 当前页码
        result['pagecount'] = 9999 # 总页数（设置为大数）
        result['limit'] = 90 # 每页限制数量
        result['total'] = 999999 # 总数据量（设置为大数）

        # 针对常规视频列表分类（4K、最新、最佳）和二级分类链接
        if tid in ['/4k', '/newest', '/best'] or 'two_click_' in tid:
            # 处理二级分类链接，提取实际路径
            if 'two_click_' in tid: tid = tid.split('click_')[-1]
            # 拼接URL并获取PyQuery对象，extend.get("type", "")用于处理4K筛选
            data = self.getpq(f'{tid}{extend.get("type", "")}/{pg}')
            # 解析视频列表
            vdata = self.getlist(data(".thumb-list--sidebar .thumb-list__item"))

        # 针对 '频道' 分类
        elif tid == '/channels':
            data = self.getpq(f'{tid}/{pg}')
            # 获取页面中的JS数据（通常是隐藏在script标签中的JSON数据）
            jsdata = self.getjsdata(data)
            # 遍历频道列表，构建视频列表（这里每个“视频”实际是频道文件夹）
            for i in jsdata['channels']:
                vdata.append({
                    'vod_id': f"two_click_" + i.get('channelURL'), # 频道URL作为ID，带二级点击标记
                    'vod_name': i.get('channelName'),
                    'vod_pic': self.proxy(i.get('siteLogoURL')), # 对图片URL进行代理处理
                    'vod_year': f'videos:{i.get("videoCount")}', # 备注：视频数量
                    'vod_tag': 'folder', # 标记为文件夹类型
                    'vod_remarks': f'subscribers:{i["subscriptionModel"].get("subscribers")}', # 备注：订阅数
                    'style': {'ratio': 1, 'type': 'rect'}
                })

        # 针对 '类别' 分类（一级分类）
        elif tid == '/categories':
            result['pagecount'] = pg # 类别通常只有一页，将页数设为当前页
            data = self.getpq(tid)
            self.cdata = self.getjsdata(data) # 存储类别数据供二级分类使用
            # 遍历热门分类列表，构建视频列表（这里每个“视频”实际是子类别文件夹）
            for i in self.cdata['layoutPage']['store']['popular']['assignable']:
                vdata.append({
                    'vod_id': "one_click_" + i.get('id'), # 类别ID作为ID，带一级点击标记
                    'vod_name': i.get('name'),
                    'vod_pic': '', # 无图片
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.33, 'type': 'rect'}
                })

        # 针对 '明星' 分类
        elif tid == '/pornstars':
            data = self.getpq(f'{tid}/{pg}')
            pdata = self.getjsdata(data)
            # 遍历明星列表，构建视频列表（这里每个“视频”实际是明星文件夹）
            for i in pdata['pagesPornstarsComponent']['pornstarListProps']['pornstars']:
                vdata.append({
                    'vod_id': f"two_click_" + i.get('pageURL'), # 明星页面URL作为ID，带二级点击标记
                    'vod_name': i.get('name'),
                    'vod_pic': self.proxy(i.get('imageThumbUrl')), # 对图片URL进行代理处理
                    'vod_remarks': i.get('translatedCountryName'), # 备注：国家/地区
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.33, 'type': 'rect'}
                })

        # 针对 '类别' 的二级分类（从 /categories 点击进入的子类别）
        elif 'one_click' in tid:
            result['pagecount'] = pg # 同样设为一页
            tid = tid.split('click_')[-1] # 提取实际类别ID
            # 在之前存储的类别数据 self.cdata 中查找匹配的子类别
            for i in self.cdata['layoutPage']['store']['popular']['assignable']:
                if i.get('id') == tid:
                    for j in i['items']:
                        # 遍历子类别下的具体链接，构建视频列表（这里每个“视频”实际是链接文件夹）
                        vdata.append({
                            'vod_id': f"two_click_" + j.get('url'), # URL作为ID，带二级点击标记
                            'vod_name': j.get('name'),
                            'vod_pic': self.proxy(j.get('thumb')),
                            'vod_tag': 'folder',
                            'style': {'ratio': 1.33, 'type': 'rect'}
                        })

        result['list'] = vdata
        return result

    def detailContent(self, ids):
        """
        获取视频详情内容。
        :param ids: 视频ID列表 (通常只有一个元素，即视频URL)
        :return: 包含视频详情信息的字典
        """
        # 传入的ids是列表，取第一个元素作为视频URL
        data = self.getpq(ids[0])
        # 获取页面中的JS数据，包含视频播放信息
        djs = self.getjsdata(data)
        # 获取视频名称 (使用og:title meta标签)
        vn = data('meta[property="og:title"]').attr('content')
        # 获取视频标签容器元素
        dtext = data('#video-tags-list-container')
        # 获取标签容器中的第一个链接 (可能是所属系列或演员)
        href = dtext('a').attr('href')
        # 获取标签容器中第一个加粗的文本（通常是标签的名称）
        title = dtext('span[class*="body-bold-"]').eq(0).text()
        pdtitle = ''
        # 如果获取到链接，则构造一个可点击的链接格式 (用于播放器跳转)
        if href:
            # 构建包含二级点击标记的链接
            pdtitle = '[a=cr:' + json.dumps({'id': 'two_click_' + href, 'name': title}) + '/]' + title + '[/a]'
        
        # 构造视频详情信息
        vod = {
            'vod_name': vn,
            'vod_director': pdtitle, # 将可点击链接作为导演/主演信息
            'vod_remarks': data('.rb-new__info').text(), # 备注信息
            'vod_play_from': 'Xhamster', # 播放源名称
            'vod_play_url': '' # 播放地址列表，待填充
        }

        try:
            plist = [] # 播放地址列表
            # 从JS数据中获取视频源信息
            d = djs['xplayerSettings']['sources']
            # 获取标清/高清源
            f = d.get('standard')

            def custom_sort_key(url):
                """
                自定义排序键，用于将播放地址按清晰度数字降序排列。
                """
                quality = url.split('$')[0] # 获取清晰度名称，例如 '720p'
                # 提取清晰度中的数字部分
                number = ''.join(filter(str.isdigit, quality))
                number = int(number) if number else 0
                # 返回负数数字 (实现降序) 和原始清晰度字符串 (数字相同则按字符串排序)
                return -number, quality

            if f:
                # 遍历标清/高清源
                for key, value in f.items():
                    if isinstance(value, list):
                        for info in value:
                            # 拼接播放地址信息，并进行 Base64 编码
                            # 0@@@@ 表示不进行二次解析（直接播放）
                            id = self.e64(f'{0}@@@@{info.get("url") or info.get("fallback")}')
                            # 格式：清晰度名称$Base64编码的URL
                            plist.append(f"{info.get('label') or info.get('quality')}${id}")
                # 对播放地址列表进行排序
                plist.sort(key=custom_sort_key)
            
            # 获取 HLS (m3u8) 源
            if d.get('hls'):
                for format_type, info in d['hls'].items():
                    if url := info.get('url'):
                        # 拼接 HLS 地址信息，并进行 Base64 编码
                        encoded = self.e64(f'{0}@@@@{url}')
                        # 格式：格式类型$Base64编码的URL
                        plist.append(f"{format_type}${encoded}")

        except Exception as e:
            # 如果获取视频信息失败，则使用原始URL作为备用播放地址
            # 1@@@@ 表示需要二次解析 (localProxy)
            plist = [f"{vn}${self.e64(f'{1}@@@@{ids[0]}')}"]
            print(f"获取视频信息失败: {str(e)}")
        
        # 将播放地址列表用 '#' 连接
        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        """
        搜索内容。
        :param key: 搜索关键词
        :param quick: 是否为快速搜索
        :param pg: 页码
        :return: 包含视频列表和分页信息的字典
        """
        # 拼接搜索URL并获取 PyQuery 对象
        data = self.getpq(f'/search/{key}?page={pg}')
        # 解析视频列表
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item")), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        """
        获取播放器内容（实际播放地址）。
        :param flag: 播放标识
        :param id: Base64编码的视频信息 (解析标识@@@@URL)
        :param vipFlags: VIP标识
        :return: 包含解析类型、URL和请求头的字典
        """
        # Base64 解码，获取 [解析标识, URL]
        ids = self.d64(id).split('@@@@')
        # 如果是 m3u8 地址，对其进行代理处理，确保内部 TS 文件地址正确
        if '.m3u8' in ids[1]: ids[1] = self.proxy(ids[1], 'm3u8')
        # 'parse': 0 表示直接播放，1 表示需要 localProxy 解析
        return {'parse': int(ids[0]), 'url': ids[1], 'header': self.headers}

    def localProxy(self, param):
        """
        本地代理处理，用于处理某些需要代理或地址修正的资源。
        :param param: 包含 url 和 type (例如 'm3u8') 的字典
        :return: 包含 HTTP 状态码、Content-Type 和内容的列表
        """
        # Base64 解码获取原始 URL
        url = self.d64(param['url'])
        # 如果是 m3u8 类型，调用 m3Proxy 处理
        if param.get('type') == 'm3u8':
            return self.m3Proxy(url)
        else:
            # 否则调用 tsProxy 处理 (用于处理 TS 文件或普通视频文件)
            return self.tsProxy(url)

    def gethost(self):
        """
        获取网站的主机地址（可能通过重定向获取真实域名）。
        :return: 网站主机地址
        """
        try:
            # 尝试访问 xhamster.com，并禁止自动重定向
            response = requests.get('https://xhamster.com',proxies=self.proxies,headers=self.headers,allow_redirects=False)
            # 返回重定向后的 Location 头信息作为真实主机地址
            return response.headers['Location']
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            # 失败时返回一个默认的备用地址
            return "https://zn.xhamster.com"

    def e64(self, text):
        """
        Base64 编码函数。
        """
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self, encoded_text):
        """
        Base64 解码函数。
        """
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    def getlist(self, data):
        """
        解析视频列表的通用方法。
        :param data: PyQuery 对象，包含多个视频项（.thumb-list__item）
        :return: 视频信息列表
        """
        vlist = []
        for i in data.items(): # 遍历每个视频项
            vlist.append({
                # 视频ID：链接 href
                'vod_id': i('.role-pop').attr('href'),
                # 视频名称：链接文本
                'vod_name': i('.video-thumb-info a').text(),
                # 视频图片：对图片的 src URL 进行代理处理
                'vod_pic': self.proxy(i('.role-pop img').attr('src')),
                # 视频年份/播放量：从文本中提取播放量（空格前部分）
                'vod_year': i('.video-thumb-info .video-thumb-views').text().split(' ')[0],
                # 视频备注：时长
                'vod_remarks': i('.role-pop div[data-role="video-duration"]').text(),
                # 样式
                'style': {'ratio': 1.33, 'type': 'rect'}
            })
        return vlist

    def getpq(self, path=''):
        """
        发送 HTTP GET 请求并返回 PyQuery 对象。
        :param path: 请求路径
        :return: PyQuery 对象
        """
        # 如果路径不是以 http 开头，则拼接 host
        h = '' if path.startswith('http') else self.host
        # 使用 Session 发送请求并获取文本内容
        response = self.session.get(f'{h}{path}').text
        try:
            # 尝试使用 PyQuery 解析
            return pq(response)
        except Exception as e:
            print(f"{str(e)}")
            # 失败时尝试使用 UTF-8 编码后再解析
            return pq(response.encode('utf-8'))

    def getjsdata(self, data):
        """
        从 HTML (PyQuery 对象) 中提取隐藏在 <script> 标签中的 JSON 数据。
        :param data: PyQuery 对象
        :return: 解析后的 JSON 字典
        """
        # 查找 id 为 'initials-script' 的 script 标签文本
        vhtml = data("script[id='initials-script']").text()
        # 截取 'initials=' 之后、末尾 ']' 之前的部分，即 JSON 字符串
        jst = json.loads(vhtml.split('initials=')[-1][:-1])
        return jst

    def m3Proxy(self, url):
        """
        M3U8 代理处理。
        用于修正 M3U8 文件中相对路径的 TS 文件地址，并对 TS 文件地址进行代理。
        :param url: M3U8 文件 URL
        :return: [200, Content-Type, 修正后的 M3U8 内容]
        """
        # 获取 M3U8 文件内容
        ydata = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=False)
        data = ydata.content.decode('utf-8')
        
        # 处理重定向
        if ydata.headers.get('Location'):
            url = ydata.headers['Location']
            data = requests.get(url, headers=self.headers, proxies=self.proxies).content.decode('utf-8')
            
        lines = data.strip().split('\n') # 按行分割 M3U8 内容
        last_r = url[:url.rfind('/')] # M3U8 文件所在目录路径
        parsed_url = urlparse(url)
        durl = parsed_url.scheme + "://" + parsed_url.netloc # M3U8 文件的域名根路径
        
        for index, string in enumerate(lines):
            # 忽略以 #EXT 开头的扩展标签行
            if '#EXT' not in string:
                # 处理非 http 开头的相对路径 (即 TS 文件路径)
                if 'http' not in string:
                    # 路径深度小于2时使用 M3U8 所在目录，否则使用域名根路径
                    domain = last_r if string.count('/') < 2 else durl
                    # 拼接完整的绝对路径
                    string = domain + ('' if string.startswith('/') else '/') + string
                # 对 TS 文件 URL 进行代理封装
                lines[index] = self.proxy(string, string.split('.')[-1].split('?')[0])
        
        data = '\n'.join(lines) # 重新组合 M3U8 内容
        # 返回状态码 200，M3U8 的 Content-Type，和修正后的内容
        return [200, "application/vnd.apple.mpegurl", data]

    def tsProxy(self, url):
        """
        TS 文件或其他资源的代理转发。
        直接请求资源并将 Content-Type 和内容返回。
        :param url: 资源 URL
        :return: [200, Content-Type, 资源内容]
        """
        # 使用 stream=True 进行流式请求，避免一次性加载大文件到内存
        data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True)
        # 返回状态码 200，Content-Type，和资源内容
        return [200, data.headers['Content-Type'], data.content]

    def proxy(self, data, type='img'):
        """
        通用代理封装方法。
        将原始 URL 封装成一个指向本地代理服务的 URL。
        :param data: 原始 URL
        :param type: 资源类型 (例如 'img', 'm3u8')
        :return: 代理 URL 或原始 URL
        """
        # 如果 URL 非空且配置了代理
        if data and len(self.proxies):
            # self.getProxyUrl() 应该是基类 Spider 提供的方法，获取代理服务地址
            # 返回格式：代理服务地址?url=Base64编码后的原始URL&type=资源类型
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else:
            # 未配置代理或 URL 为空时，返回原始 URL
            return data
