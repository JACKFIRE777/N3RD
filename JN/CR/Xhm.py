# -*- coding: utf-8 -*-
# by @嗷呜
# Xhamster视频网站爬虫类，用于获取视频列表、详情和播放地址

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
    """Xhamster视频爬虫类，继承自基础Spider类"""

    def init(self, extend=""):
        """
        初始化爬虫配置
        Args:
            extend: 扩展配置，JSON格式的代理设置
        """
        # 尝试解析代理配置
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}
        
        # 设置HTTP请求头，模拟真实浏览器
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
            'referer': f'',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'priority': 'u=1, i',
        }
        
        # 获取实际的主站域名
        self.host = self.gethost()
        
        # 创建会话对象，保持连接状态
        self.session = Session()
        self.headers.update({'origin': self.host,'referer': f'{self.host}/'})
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)

    def getName(self):
        """获取爬虫名称（未实现）"""
        pass

    def isVideoFormat(self, url):
        """判断是否为视频格式（未实现）"""
        pass

    def manualVideoCheck(self):
        """手动视频检查（未实现）"""
        pass

    def destroy(self):
        """销毁爬虫实例（未实现）"""
        pass

    def homeContent(self, filter):
        """
        获取首页分类内容
        Returns:
            dict: 包含分类列表和筛选器的字典
        """
        result = {}
        
        # 定义手动分类映射表
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
        
        # 遍历分类，构建分类列表和筛选器
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
            # 为非4K分类添加4K筛选选项
            if k != '4K': 
                filters[cateManual[k]] = [{'key': 'type', 'name': '类型', 'value': [{'n': '4K', 'v': '/4k'}]}]
        
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        """
        获取首页视频列表
        Returns:
            dict: 包含视频列表的字典
        """
        data = self.getpq()
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item"))}

    def categoryContent(self, tid, pg, filter, extend):
        """
        获取分类页面内容
        Args:
            tid: 分类ID
            pg: 页码
            filter: 筛选条件
            extend: 扩展参数
        Returns:
            dict: 包含视频列表和分页信息的字典
        """
        vdata = []
        result = {}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        
        # 处理视频列表类型分类（4K、最新、最佳）
        if tid in ['/4k', '/newest', '/best'] or 'two_click_' in tid:
            if 'two_click_' in tid: 
                tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}{extend.get("type", "")}/{pg}')
            vdata = self.getlist(data(".thumb-list--sidebar .thumb-list__item"))
        
        # 处理频道列表
        elif tid == '/channels':
            data = self.getpq(f'{tid}/{pg}')
            jsdata = self.getjsdata(data)
            for i in jsdata['channels']:
                vdata.append({
                    'vod_id': f"two_click_" + i.get('channelURL'),
                    'vod_name': i.get('channelName'),
                    'vod_pic': self.proxy(i.get('siteLogoURL')),
                    'vod_year': f'videos:{i.get("videoCount")}',
                    'vod_tag': 'folder',
                    'vod_remarks': f'subscribers:{i["subscriptionModel"].get("subscribers")}',
                    'style': {'ratio': 1.778, 'type': 'rect'}
                })
        
        # 处理类别列表
        elif tid == '/categories':
            result['pagecount'] = pg
            data = self.getpq(tid)
            self.cdata = self.getjsdata(data)
            for i in self.cdata['layoutPage']['store']['popular']['assignable']:
                vdata.append({
                    'vod_id': "one_click_" + i.get('id'),
                    'vod_name': i.get('name'),
                    'vod_pic': '',
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.778, 'type': 'rect'}
                })
        
        # 处理明星列表
        elif tid == '/pornstars':
            data = self.getpq(f'{tid}/{pg}')
            pdata = self.getjsdata(data)
            for i in pdata['pagesPornstarsComponent']['pornstarListProps']['pornstars']:
                vdata.append({
                    'vod_id': f"two_click_" + i.get('pageURL'),
                    'vod_name': i.get('name'),
                    'vod_pic': self.proxy(i.get('imageThumbUrl')),
                    'vod_remarks': i.get('translatedCountryName'),
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.778, 'type': 'rect'}
                })
        
        # 处理子类别（二级分类）
        elif 'one_click' in tid:
            result['pagecount'] = pg
            tid = tid.split('click_')[-1]
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
        
        result['list'] = vdata
        return result

    def detailContent(self, ids):
        """
        获取视频详情和播放地址（核心方法）
        Args:
            ids: 视频ID列表
        Returns:
            dict: 包含视频详细信息和播放地址的字典
        """
        # 获取页面数据
        data = self.getpq(ids[0])
        djs = self.getjsdata(data)
        
        # 提取视频标题
        vn = data('meta[property="og:title"]').attr('content')
        
        # 提取标签信息
        dtext = data('#video-tags-list-container')
        href = dtext('a').attr('href')
        title = dtext('span[class*="body-bold-"]').eq(0).text()
        
        # 构建制作者标题链接
        pdtitle = ''
        if href:
            pdtitle = '[a=cr:' + json.dumps({'id': 'two_click_' + href, 'name': title}) + '/]' + title + '[/a]'
        
        # 构建视频信息对象
        vod = {
            'vod_name': vn,
            'vod_director': pdtitle,
            'vod_remarks': data('.rb-new__info').text(),
            'vod_play_from': 'Xhamster',
            'vod_play_url': ''
        }
        
        try:
            # ========== 视频地址处理核心逻辑 ==========
            plist = []
            
            # 从页面JS数据中提取视频源信息
            d = djs['xplayerSettings']['sources']
            f = d.get('standard')  # 标准格式视频源
            
            # 自定义排序函数：按清晰度数字降序排列
            def custom_sort_key(url):
                quality = url.split('$')[0]  # 提取清晰度标签
                number = ''.join(filter(str.isdigit, quality))  # 提取数字
                number = int(number) if number else 0
                return -number, quality  # 负数实现降序
            
            # 处理标准格式视频源（MP4等）
            if f:
                for key, value in f.items():
                    if isinstance(value, list):
                        for info in value:
                            # 获取视频URL，优先使用url字段，否则使用fallback
                            video_url = info.get("url") or info.get("fallback")
                            
                            # 编码格式：0@@@@视频URL
                            # 0表示不需要解析，直接播放
                            id = self.e64(f'{0}@@@@{video_url}')
                            
                            # 格式：清晰度$base64编码的播放信息
                            quality_label = info.get('label') or info.get('quality')
                            plist.append(f"{quality_label}${id}")
            
            # 按清晰度排序（高清晰度在前）
            plist.sort(key=custom_sort_key)
            
            # 处理HLS格式视频源（m3u8流媒体）
            if d.get('hls'):
                for format_type, info in d['hls'].items():
                    if url := info.get('url'):
                        # 编码HLS地址，格式同上
                        encoded = self.e64(f'{0}@@@@{url}')
                        plist.append(f"{format_type}${encoded}")
        
        except Exception as e:
            # 如果解析失败，使用备用方案：标记为需要解析的页面
            # 1表示需要通过页面解析获取视频地址
            plist = [f"{vn}${self.e64(f'{1}@@@@{ids[0]}')}"]
            print(f"获取视频信息失败: {str(e)}")
        
        # 用#连接多个清晰度选项
        vod['vod_play_url'] = '#'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        """
        搜索视频内容
        Args:
            key: 搜索关键词
            quick: 是否快速搜索
            pg: 页码
        Returns:
            dict: 包含搜索结果列表的字典
        """
        data = self.getpq(f'/search/{key}?page={pg}')
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item")), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        """
        处理播放器内容，解码视频地址
        Args:
            flag: 播放源标识
            id: base64编码的播放信息
            vipFlags: VIP标识
        Returns:
            dict: 包含解析类型、播放URL和请求头的字典
        """
        # 解码播放信息：格式为 "解析类型@@@@视频URL"
        ids = self.d64(id).split('@@@@')
        
        # 如果是m3u8流媒体，需要通过代理处理
        if '.m3u8' in ids[1]: 
            ids[1] = self.proxy(ids[1], 'm3u8')
        
        return {
            'parse': int(ids[0]),  # 0=直接播放，1=需要解析
            'url': ids[1],          # 视频播放地址
            'header': self.headers  # 请求头
        }

    def localProxy(self, param):
        """
        本地代理方法，处理m3u8和ts文件
        Args:
            param: 包含url和type的参数字典
        Returns:
            list: [状态码, Content-Type, 内容]
        """
        url = self.d64(param['url'])
        if param.get('type') == 'm3u8':
            return self.m3Proxy(url)  # 处理m3u8索引文件
        else:
            return self.tsProxy(url)  # 处理ts视频片段

    def gethost(self):
        """
        获取实际的主站域名（处理地区重定向）
        Returns:
            str: 主站域名URL
        """
        try:
            response = requests.get('https://xhamster.com',
                                  proxies=self.proxies,
                                  headers=self.headers,
                                  allow_redirects=False)
            return response.headers['Location']
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            return "https://zn.xhamster.com"

    def e64(self, text):
        """
        Base64编码
        Args:
            text: 待编码的文本
        Returns:
            str: Base64编码后的字符串
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
        Base64解码
        Args:
            encoded_text: Base64编码的文本
        Returns:
            str: 解码后的原始字符串
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
        解析视频列表数据
        Args:
            data: PyQuery对象
        Returns:
            list: 视频信息列表
        """
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
        """
        获取页面并返回PyQuery对象
        Args:
            path: 页面路径
        Returns:
            PyQuery: 页面解析对象
        """
        h = '' if path.startswith('http') else self.host
        response = self.session.get(f'{h}{path}').text
        try:
            return pq(response)
        except Exception as e:
            print(f"{str(e)}")
            return pq(response.encode('utf-8'))

    def getjsdata(self, data):
        """
        从页面中提取JavaScript初始化数据
        Args:
            data: PyQuery对象
        Returns:
            dict: 解析后的JSON数据
        """
        vhtml = data("script[id='initials-script']").text()
        jst = json.loads(vhtml.split('initials=')[-1][:-1])
        return jst

    def m3Proxy(self, url):
        """
        处理m3u8索引文件，转换其中的ts片段URL为代理URL
        Args:
            url: m3u8文件的URL
        Returns:
            list: [状态码, Content-Type, 处理后的m3u8内容]
        """
        # 请求m3u8文件
        ydata = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=False)
        data = ydata.content.decode('utf-8')
        
        # 处理重定向
        if ydata.headers.get('Location'):
            url = ydata.headers['Location']
            data = requests.get(url, headers=self.headers, proxies=self.proxies).content.decode('utf-8')
        
        # 解析m3u8文件内容
        lines = data.strip().split('\n')
        last_r = url[:url.rfind('/')]  # 获取URL的目录部分
        parsed_url = urlparse(url)
        durl = parsed_url.scheme + "://" + parsed_url.netloc  # 获取域名部分
        
        # 遍历每一行，转换相对路径为代理URL
        for index, string in enumerate(lines):
            if '#EXT' not in string:  # 跳过m3u8的元数据行
                if 'http' not in string:  # 处理相对路径
                    # 判断使用完整路径还是域名拼接
                    domain = last_r if string.count('/') < 2 else durl
                    string = domain + ('' if string.startswith('/') else '/') + string
                # 将ts片段URL转换为代理URL
                lines[index] = self.proxy(string, string.split('.')[-1].split('?')[0])
        
        # 重新组合m3u8文件内容
        data = '\n'.join(lines)
        return [200, "application/vnd.apple.mpegur", data]

    def tsProxy(self, url):
        """
        代理ts视频片段请求
        Args:
            url: ts文件的URL
        Returns:
            list: [状态码, Content-Type, 文件内容]
        """
        data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True)
        return [200, data.headers['Content-Type'], data.content]

    def proxy(self, data, type='img'):
        """
        生成代理URL
        Args:
            data: 原始URL
            type: 资源类型（img/m3u8/ts等）
        Returns:
            str: 代理URL或原始URL
        """
        if data and len(self.proxies):
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else:
            return data
