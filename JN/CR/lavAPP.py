# -*- coding: utf-8 -*-
# 声明文件编码为 UTF-8

# by @嗷呜
# 作者标识（通常）

import sys
# 导入系统模块，用于访问系统相关功能

from base64 import b64encode, b64decode
# 导入 base64 模块，用于 Base64 编码和解码，主要用于处理 URL

from Crypto.Hash import MD5, SHA256
# 从 pycryptodome 库导入 MD5 和 SHA256 哈希算法

sys.path.append('..')
# 将上一级目录添加到系统路径，以便导入自定义模块

from base.spider import Spider
# 从自定义的 base 模块中导入基类 Spider

from Crypto.Cipher import AES
# 从 pycryptodome 库导入 AES 加密算法

import json
# 导入 json 模块，用于处理 JSON 格式数据

import time
# 导入 time 模块，用于获取时间戳

# 爬虫主类，继承自基类 Spider
class Spider(Spider):

    # 获取爬虫名称
    def getName(self):
        return "lav"

    # 初始化方法，在爬虫加载时调用
    def init(self, extend=""):
        # 生成一个基于当前时间戳（毫秒级）MD5值的16位ID，用作 oauth_id
        self.id = self.ms(str(int(time.time() * 1000)))[:16]
        pass # 无额外初始化操作

    # 检查 URL 是否为视频格式（未实现）
    def isVideoFormat(self, url):
        pass

    # 手动视频检查（未实现）
    def manualVideoCheck(self):
        pass

    # 执行特定动作（未实现）
    def action(self, action):
        pass

    # 销毁方法（爬虫卸载时调用，未实现）
    def destroy(self):
        pass

    # 网站主机地址
    host = "http://sir_new.tiansexyl.tv"
    
    # 当前时间戳（毫秒级），在类定义时获取一次
    t = str(int(time.time() * 1000))
    
    # 请求头
    headers = {'User-Agent': 'okhttp-okgo/jeasonlzy', 'Connection': 'Keep-Alive',
               'Content-Type': 'application/x-www-form-urlencoded'}
    
    # 获取首页分类内容
    def homeContent(self, filter):
        # 预设手动分类，如 演员 和 分类
        cateManual = {"演员": "actor", "分类": "avsearch", }
        classes = []
        # 将手动分类添加到 classes 列表中
        for k in cateManual:
            classes.append({'type_name': k, 'type_id': cateManual[k]})
        
        # 构造请求参数的 JSON 对象，用于获取首页数据，包括分类标签
        j = {'code': 'homePage', 'mod': 'down', 'channel': 'self', 'via': 'agent', 'bundleId': 'com.tvlutv',
             'app_type': 'rn', 'os_version': '12.0.5', 'version': '3.2.3', 'oauth_type': 'android_rn',
             'oauth_id': self.id}

        # 使用 AES 加密请求参数 j
        body = self.aes(j)
        
        # 发送 POST 请求到 API，携带加密后的 body 数据
        # URL 包含最新的时间戳
        data = self.post(f'{self.host}/api.php?t={str(int(time.time() * 1000))}', data=body, headers=self.headers).json()['data']
        
        # 解密响应数据 data，获取实际内容 data1
        data1 = self.aes(data, False)['data']
        
        # 提取并保存响应中的 r 字段（可能是 Referer 或其他标识）
        self.r = data1['r']
        
        # 遍历响应数据中的 avTag（视频标签），将它们作为分类添加到 classes 列表中
        for i, d in enumerate(data1['avTag']):
            # if i == 4: # 示例注释，用于控制添加数量
            #     break
            classes.append({'type_name': d['name'], 'type_id': d['tag']})
            
        # 构造返回结果
        resutl = {}
        resutl["class"] = classes
        return resutl

    # 获取首页视频内容（未实现）
    def homeVideoContent(self):
        pass

    # 获取分类详情内容（列表页）
    def categoryContent(self, tid, pg, filter, extend):
        # tid 可能是复合 ID，以 @@ 分割
        id = tid.split("@@")
        
        # 初始化结果结构，设置分页信息
        result = {}
        result["page"] = pg
        result["pagecount"] = 9999
        result["limit"] = 90
        result["total"] = 999999
        
        # 根据分类 ID 构造请求的 JSON 对象 j
        if id[0] == 'avsearch':
            if pg == '1':
                # 'avsearch' 页面第一页的请求参数
                j = {'code': 'avsearch', 'mod': 'search', 'channel': 'self', 'via': 'agent', 'bundleId': 'com.tvlutv',
                     'app_type': 'rn', 'os_version': '12.0.5', 'version': '3.2.3', 'oauth_type': 'android_rn',
                     'oauth_id': self.id}
            if len(id) > 1:
                # 'avsearch' 下二级标签（tag）的请求参数
                j = {'code': 'find', 'mod': 'tag', 'channel': 'self', 'via': 'agent', 'bundleId': 'com.tvlutv',
                     'app_type': 'rn', 'os_version': '12.0.5', 'version': '3.2.3', 'oauth_type': 'android_rn',
                     'oauth_id': self.id, 'type': 'av', 'dis': 'new', 'page': str(pg), 'tag': id[1]}
        elif id[0] == 'actor':
            # 'actor'（演员）列表页的请求参数
            j = {'mod': 'actor', 'channel': 'self', 'via': 'agent', 'bundleId': 'com.tvlutv', 'app_type': 'rn',
                 'os_version': '12.0.5', 'version': '3.2.3', 'oauth_type': 'android_rn', 'oauth_id': self.id,
                 'page': str(pg), 'filter': ''}
            if len(id) > 1:
                # 演员详情页的请求参数（获取该演员下的视频）
                j = {'code': 'eq', 'mod': 'actor', 'channel': 'self', 'via': 'agent', 'bundleId': 'com.tvlutv',
                     'app_type': 'rn', 'os_version': '12.0.5', 'version': '3.2.3', 'oauth_type': 'android_rn',
                     'oauth_id': self.id, 'page': str(pg), 'id': id[1], 'actor': id[2]}
        else:
            # 普通标签（avTag）分类的请求参数
            j = {'code': 'search', 'mod': 'av', 'channel': 'self', 'via': 'agent', 'bundleId': 'com.tvlutv',
                 'app_type': 'rn', 'os_version': '12.0.5', 'version': '3.2.3', 'oauth_type': 'android_rn',
                 'oauth_id': self.id, 'page': str(pg), 'tag': id[0]}

        # 加密请求参数
        body = self.aes(j)
        
        # 发送请求并获取响应数据
        data = self.post(f'{self.host}/api.php?t={str(int(time.time() * 1000))}', data=body, headers=self.headers).json()['data']
        
        # 解密响应数据
        data1 = self.aes(data, False)['data']
        videos = []
        
        # 根据不同的分类 ID 解析 data1 并构造视频列表
        if tid == 'avsearch' and len(id) == 1:
            # 处理一级 'avsearch' 结果（返回标签/文件夹列表）
            for item in data1:
                videos.append({"vod_id": id[0] + "@@" + str(item.get('tags')), 'vod_name': item.get('name'),
                               'vod_pic': self.imgs(item.get('ico')), 'vod_tag': 'folder',
                               'style': {"type": "rect", "ratio": 1.33}})
        elif tid == 'actor' and len(id) == 1:
            # 处理一级 'actor' 结果（返回演员列表）
            for item in data1:
                videos.append({"vod_id": id[0] + "@@" + str(item.get('id')) + "@@" + item.get('name'),
                               'vod_name': item.get('name'), 'vod_pic': self.imgs(item.get('cover')),
                               'vod_tag': 'folder', 'style': {"type": "oval"}})
        else:
            # 处理其他分类或二级详情的结果（返回视频列表）
            for item in data1:
                if item.get('_id'): # 检查是否有视频ID（筛选掉非视频数据）
                    videos.append({"vod_id": str(item.get('id')), 'vod_name': item.get('title'),
                                   'vod_pic': self.imgs(item.get('cover_thumb') or item.get('cover_full')),
                                   'vod_remarks': item.get('good'), 'style': {"type": "rect", "ratio": 1.33}})
                                   
        # 将视频列表添加到结果中
        result["list"] = videos
        return result

    # 获取视频详情内容
    def detailContent(self, ids):
        id = ids[0] # 提取视频 ID
        
        # 构造获取视频详情的请求 JSON 对象 j
        j = {'code': 'detail', 'mod': 'av', 'channel': 'self', 'via': 'agent', 'bundleId': 'com.tvlutv',
             'app_type': 'rn', 'os_version': '12.0.5', 'version': '3.2.3', 'oauth_type': 'android_rn',
             'oauth_id': self.id, 'id': id}
             
        # 加密请求参数
        body = self.aes(j)
        
        # 发送请求并获取响应数据
        data = self.post(f'{self.host}/api.php?t={str(int(time.time() * 1000))}', data=body, headers=self.headers).json()['data']
        
        # 解密响应数据，并提取 'line' 字段（包含播放链接）
        data1 = self.aes(data, False)['line']
        vod = {}
        play = []
        
        # 遍历播放线路，提取播放 URL
        for itt in data1:
            # 尝试获取 720p 线路的 URL
            a = itt['line'].get('s720')
            if a:
                # 尝试将 URL 的协议头修改为 https://m3u8
                b = a.split('.')
                b[0] = 'https://m3u8'
                a = '.'.join(b)
                # 构造播放源名称和 URL
                play.append(itt['info']['tips'] + "$" + a)
                break # 找到第一个可用的播放链接后退出
                
        # 构造播放信息
        vod["vod_play_from"] = 'LAV' # 播放源名称
        vod["vod_play_url"] = "#".join(play) # 播放地址列表
        
        result = {"list": [vod]}
        return result

    # 搜索内容（未实现）
    def searchContent(self, key, quick, pg="1"):
        pass

    # 获取播放内容（播放前调用）
    def playerContent(self, flag, id, vipFlags):
        # 构造代理 URL，将实际的播放 ID（即 m3u8 URL）进行 Base64 编码后作为参数
        url = self.getProxyUrl() + "&url=" + b64encode(id.encode('utf-8')).decode('utf-8') + "&type=m3u8"
        
        # 设置请求头，特别是 Referer 使用之前保存的 self.r
        self.hh = {'User-Agent': 'dd', 'Connection': 'Keep-Alive', 'Referer': self.r}
        
        # 构造播放结果
        result = {}
        result["parse"] = 0 # 0 表示不使用第三方解析，直接播放
        result["url"] = url
        result["header"] = self.hh # 携带自定义请求头
        return result

    # 本地代理，用于处理图片和视频（m3u8）请求
    def localProxy(self, param):
        url = param["url"]
        if param.get('type') == "m3u8":
            # 如果类型是 m3u8，则解码 URL 并调用 vod 方法处理
            return self.vod(b64decode(url).decode('utf-8'))
        else:
            # 否则作为图片处理
            return self.img(url)

    # 视频（m3u8）内容处理
    def vod(self, url):
        # 请求 m3u8 内容
        data = self.fetch(url, headers=self.hh).text
        
        # 定义 AES 密钥（从十六进制字符串转换）
        key = bytes.fromhex("13d47399bda541b85e55830528d4e66f1791585b2d2216f23215c4c63ebace31")
        
        # 提取数据前 32 位作为 IV（初始化向量）
        iv = bytes.fromhex(data[:32])
        data = data[32:] # 剩余部分为加密后的数据
        
        # 初始化 AES 解密器，使用 CFB 模式
        cipher = AES.new(key, AES.MODE_CFB, iv, segment_size=128)
        
        # 将加密数据从十六进制转换为字节
        data_bytes = bytes.fromhex(data)
        
        # 解密
        decrypted = cipher.decrypt(data_bytes)
        
        # 解码为 UTF-8 字符串，并去除填充字符（\x08）
        encoded = decrypted.decode("utf-8").replace("\x08", "")
        
        # 返回结果：状态码、内容类型和解密后的 m3u8 内容
        return [200, "application/vnd.apple.mpegur", encoded]

    # 图片代理 URL 封装
    def imgs(self, url):
        # 返回一个带有图片 URL 的代理链接
        return self.getProxyUrl() + '&url=' + url

    # 图片内容处理
    def img(self, url):
        type = url.split('.')[-1] # 提取图片类型（扩展名）
        data = self.fetch(url).text # 请求图片内容（可能是加密的十六进制字符串）
        
        # 定义 AES 密钥（与 vod 方法不同）
        key = bytes.fromhex("ba78f184208d775e1553550f2037f4af22cdcf1d263a65b4d5c74536f084a4b2")
        
        # 提取 IV 和加密数据（与 vod 方法逻辑相同）
        iv = bytes.fromhex(data[:32])
        data = data[32:]
        
        # 初始化 AES 解密器，使用 CFB 模式
        cipher = AES.new(key, AES.MODE_CFB, iv, segment_size=128)
        
        # 解密
        data_bytes = bytes.fromhex(data)
        decrypted = cipher.decrypt(data_bytes)
        
        # 返回结果：状态码、内容类型和解密后的图片字节数据
        return [200, f"image/{type}", decrypted]

    # MD5 或 SHA256 哈希计算
    # data: 要计算哈希的字符串
    # m: True 使用 SHA256，False 使用 MD5（默认）
    def ms(self, data, m=False):
        h = MD5.new()
        if m:
            h = SHA256.new()
        h.update(data.encode('utf-8'))
        return h.hexdigest()

    # AES 加密/解密方法
    # data: 要加密的 JSON 对象 或 要解密的字符串
    # operation: True 为加密（默认），False 为解密
    def aes(self, data, operation=True):
        # 定义 AES 密钥
        key = bytes.fromhex("620f15cfdb5c79c34b3940537b21eda072e22f5d7151456dec3932d7a2b22c53")
        
        # 获取当前时间戳（秒级）
        t = str(int(time.time()))
        
        # 计算时间戳的 MD5 值作为 IV（初始化向量）的种子
        ivt = self.ms(t)
        
        if operation:
            # 加密操作
            
            # 将 JSON 对象转换为紧凑的 JSON 字符串
            data = json.dumps(data, separators=(',', ':'))
            # 使用时间戳 MD5 作为 IV
            iv = bytes.fromhex(ivt)
        else:
            # 解密操作
            
            # 提取数据前 32 位作为 IV
            iv = bytes.fromhex(data[:32])
            data = data[32:] # 剩余部分为密文
            
        # 初始化 AES 解密/加密器，使用 CFB 模式
        cipher = AES.new(key, AES.MODE_CFB, iv, segment_size=128)
        
        if operation:
            # 执行加密
            data_bytes = data.encode('utf-8')
            encrypted = cipher.encrypt(data_bytes)
            
            # 构造加密后的数据字符串 ep：IV 的 MD5值 + 密文的十六进制
            ep = f'{ivt}{encrypted.hex()}'
            
            # 构造用于计算签名的字符串 edata
            # 固定后缀 "0d27dfacef1338483561a46b246bf36d"
            edata = f"data={ep}&timestamp={t}0d27dfacef1338483561a46b246bf36d"
            
            # 计算签名：两次 SHA256 哈希
            sign = self.ms(self.ms(edata, True), True)
            
            # 构造最终的请求 body（URL 编码格式）
            edata = f"timestamp={t}&data={ep}&sign={sign}"
            return edata
        else:
            # 执行解密
            data_bytes = bytes.fromhex(data)
            decrypted = cipher.decrypt(data_bytes)
            
            # 解码为 UTF-8 字符串并解析为 JSON
            return json.loads(decrypted.decode('utf-8'))
