# -*- coding: utf-8 -*-
# 声明文件编码为 UTF-8
# by @嗷呜
# 作者标识

import json 
import random
import string
import sys
import time
from base64 import b64decode # 导入 Base64 解码
from urllib.parse import quote # 导入 URL 编码（用于搜索关键词）
from Crypto.Cipher import AES # 导入 AES 加密算法
from Crypto.Hash import MD5 # 导入 MD5 哈希算法
from Crypto.Util.Padding import unpad # 导入 AES 解密后的去填充工具
sys.path.append('..') # 将上一级目录添加到系统路径
from base.spider import Spider # 导入基类 Spider


class Spider(Spider):
    
    # 爬虫初始化方法，在爬虫加载时调用
    def init(self, extend=""):
        # 获取或生成设备ID (did)
        self.did = self.getdid()
        # 获取认证 token、图片域名(phost)和 API 主域名(host)
        self.token,self.phost,self.host = self.gettoken()
        pass

    # 检查 URL 是否为视频格式（未实现）
    def isVideoFormat(self, url):
        pass

    # 手动视频检查（未实现）
    def manualVideoCheck(self):
        pass

    # 执行特定动作（未实现）
    def action(self, action):
        pass

    # 销毁方法（未实现）
    def destroy(self):
        pass

    # 潜在的域名后缀列表
    hs=['wcyfhknomg','pdcqllfomw','alxhzjvean','bqeaaxzplt','hfbtpixjso']

    # 固定的 User-Agent 字符串，伪装成特定移动应用请求
    ua='Mozilla/5.0 (Linux; Android 11; M2012K10C Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/87.0.4280.141 Mobile Safari/537.36;SuiRui/twitter/ver=1.4.4'

# ---

## 首页和分类内容

    # 获取首页分类内容
    def homeContent(self, filter):
        # 1. 请求分类列表 API
        data = self.fetch(f'{self.host}/api/video/classifyList', headers=self.headers()).json()['encData']
        
        # 2. 解密响应数据 (encData)
        data1 = self.aes(data)
        
        # 3. 初始化结果，手动构造了分类过滤菜单（用于不同分类页的排序）
        result = {'filters': {"1": [{"key": "fl", "name": "分类", # ... 略 ...
                                     "value": [{"n": "最近更新", "v": "1"}, {"n": "最多播放", "v": "2"},
                                               {"n": "好评榜", "v": "3"}]}], 
                                     # ... 为 ID 1 到 7 以及 jx 定义了过滤器 ...
                                     "jx": [{"key": "type", "name": "精选",
                                             "value": [{"n": "日榜", "v": "1"},
                                                       {"n": "周榜", "v": "2"},
                                                       {"n": "月榜", "v": "3"},
                                                       {"n": "总榜", "v": "4"}]}]}}
                                                       
        # 4. 构造分类列表 (classes)
        classes = [{'type_name': "精选", 'type_id': "jx"}] # 手动添加 "精选" 分类
        for k in data1['data']:
            # 添加从 API 获取的分类
            classes.append({'type_name': k['classifyTitle'], 'type_id': k['classifyId']})
            
        result['class'] = classes
        return result

    # 获取首页视频内容（未实现）
    def homeVideoContent(self):
        pass

    # 获取分类视频列表内容
    def categoryContent(self, tid, pg, filter, extend):
        # 默认路径：按分类ID查询视频
        path = f'/api/video/queryVideoByClassifyId?pageSize=20&page={pg}&classifyId={tid}&sortType={extend.get("fl", "1")}'
        
        # 如果 tid 包含 'click'，则按用户ID查询该用户下的视频
        if 'click' in tid:
            path = f'/api/video/queryPersonVideoByType?pageSize=20&page={pg}&userId={tid.replace("click", "")}'
        
        # 如果 tid 是 'jx'，则查询精选排行榜
        if tid == 'jx':
            path = f'/api/video/getRankVideos?pageSize=20&page={pg}&type={extend.get("type", "1")}'
            
        # 1. 请求 API 并获取加密数据
        data = self.fetch(f'{self.host}{path}', headers=self.headers()).json()['encData']
        
        # 2. 解密响应数据
        data1 = self.aes(data)['data']
        result = {}
        videos = []
        
        # 3. 构造视频列表
        for k in data1:
            # 拼接 vod_id: 视频ID?用户ID?用户昵称
            id = f'{k.get("videoId")}?{k.get("userId")}?{k.get("nickName")}'
            if 'click' in tid:
                id = id + 'click' # 如果是用户页，则加上 click 标识
            
            videos.append({"vod_id": id, 
                           'vod_name': k.get('title'), 
                           # 图片 URL 使用代理封装，并只取第一个封面图 [0]
                           'vod_pic': self.getProxyUrl() + f"&url={k.get('coverImg')[0]}",
                           # vod_remarks 设为格式化后的播放时长
                           'vod_remarks': self.dtim(k.get('playTime')),
                           # 设置图片显示比例为 16:9 (1.778)
                           'style': {"type": "rect", "ratio": 1.778}}) 
                           
        result["list"] = videos
        # 设置分页信息
        result["page"] = pg
        result["pagecount"] = 9999
        result["limit"] = 90
        result["total"] = 999999
        return result

# ---

## 详情、搜索与播放

    # 获取视频详情内容
    def detailContent(self, ids):
        # 1. 从 vod_id 中提取视频 ID, 用户 ID 和昵称
        vid = ids[0].replace('click', '').split('?')
        
        # 2. 请求 API 获取播放链接
        path = f'/api/video/can/watch?videoId={vid[0]}'
        data = self.fetch(f'{self.host}{path}', headers=self.headers()).json()['encData']
        data1 = self.aes(data)['playPath'] # 解密后获取播放路径
        
        # 3. 构造 vod_director 字段，包含一个可点击的作者链接
        clj = '[a=cr:' + json.dumps({'id': vid[1] + 'click', 'name': vid[2]}) + '/]' + vid[2] + '[/a]' + " " # [a=cr:...] 是自定义跳转格式
        if 'click' in ids[0]:
            # 如果已经是用户页面，则不显示可点击链接
            clj = vid[2]
            
        # 4. 构造详情结果
        vod = {'vod_director': clj, 
               'vod_play_from': "推特", 
               # 播放 URL 格式：昵称$播放路径
               'vod_play_url': vid[2] + "$" + data1}
        result = {"list": [vod]}
        return result

    # 搜索内容
    def searchContent(self, key, quick, pg='1'):
        # 1. 构造搜索 API 路径，对关键词进行 URL 编码
        path = f'/api/search/keyWord?pageSize=20&page={pg}&searchWord={quote(key)}&searchType=1'
        
        # 2. 请求 API 并解密数据
        data = self.fetch(f'{self.host}{path}', headers=self.headers()).json()['encData']
        data1 = self.aes(data)['videoList']
        
        result = {}
        videos = []
        
        # 3. 构造搜索结果视频列表 (与 categoryContent 逻辑类似)
        for k in data1:
            id = f'{k.get("videoId")}?{k.get("userId")}?{k.get("nickName")}'
            videos.append({"vod_id": id, 'vod_name': k.get('title'), 
                           'vod_pic': self.getProxyUrl() + f"&url={k.get('coverImg')[0]}",
                           'vod_remarks': self.dtim(k.get('playTime')), 'style': {"type": "rect", "ratio": 1.778}})
                           
        result["list"] = videos
        # 设置分页信息
        result["page"] = pg
        result["pagecount"] = 9999
        result["limit"] = 90
        result["total"] = 999999
        return result

    # 获取播放地址 (播放器内容)
    def playerContent(self, flag, id, vipFlags):
        # 直接返回 URL，设置 parse=0 (不使用第三方解析)
        return {"parse": 0, "url": id, "header": self.headers()}

    # 本地代理 (用于图片/封面)
    def localProxy(self, param):
        # 实际调用 imgs 方法处理图片代理
        return self.imgs(param)

# ---

## 工具方法 (加密、解密、工具函数)

    # 获取签名
    def getsign(self):
        # 获取毫秒级时间戳
        t = str(int(time.time() * 1000))
        # 计算时间戳的 MD5 值作为签名
        sign = self.md5(t)
        return sign, t

    # 构造请求头
    def headers(self):
        sign, t = self.getsign()
        # 请求头包含 User-Agent, 设备 ID, 时间戳, 签名, 和认证 Token
        return {'User-Agent': self.ua,'deviceid': self.did, 't': t, 's': sign, 'aut': self.token}

    # AES 解密
    def aes(self, word):
        # Base64 解码密钥: JmhiR2NpT2lKSVV6STFOaQ== -> JhiBGciOiIJUzINi
        key = b64decode("SmhiR2NpT2lKSVV6STFOaQ==")
        iv = key # IV (初始向量) 与 Key 相同
        
        # 初始化 AES 解密器，使用 CBC 模式
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        # 1. Base64 解码密文 (word)
        # 2. AES 解密
        # 3. unpad 去除填充
        decrypted = unpad(cipher.decrypt(b64decode(word)), AES.block_size)
        
        # 4. 解码为 UTF-8 字符串并解析为 JSON
        return json.loads(decrypted.decode('utf-8'))

    # 格式化秒数为 [小时:]分:秒
    def dtim(self, seconds):
        try:
            seconds = int(seconds)
            hours = seconds // 3600
            remaining_seconds = seconds % 3600
            minutes = remaining_seconds // 60
            remaining_seconds = remaining_seconds % 60

            formatted_minutes = str(minutes).zfill(2)
            formatted_seconds = str(remaining_seconds).zfill(2)

            if hours > 0:
                formatted_hours = str(hours).zfill(2)
                return f"{formatted_hours}:{formatted_minutes}:{formatted_seconds}"
            else:
                return f"{formatted_minutes}:{formatted_seconds}"
        except:
            return "666" # 错误时返回固定值

    # 获取 Token、图片域名和主域名
    def gettoken(self, i=0, max_attempts=10):
        # 递归尝试不同的域名后缀直到成功
        if i >= len(self.hs) or i >= max_attempts:
            return ''
            
        # 随机生成一个子域名并拼接域名后缀
        random_sub = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(5, 10)))
        current_domain = f"https://{random_sub}.{self.hs[i]}.work"
        
        try:
            url = f'{current_domain}/api/user/traveler' # 游客登录 API
            sign, t = self.getsign()
            
            # 构造请求头
            headers = {
                'User-Agent': self.ua, 'Accept': 'application/json',
                'deviceid': self.did, 't': t, 's': sign,
            }
            # 构造请求体
            data = {
                'deviceId': self.did, 'tt': 'U', 
                'code': '##X-4m6Goo4zzPi1hF##', # 看起来是固定的验证码/代码
                'chCode': 'tt09' # 渠道代码
            }
            response = self.post(url, json=data, headers=headers)
            response.raise_for_status() # 检查 HTTP 状态码
            
            data1 = response.json()['data']
            # 返回 token, 图片域名, 和当前成功的主域名
            return data1['token'], data1['imgDomain'], current_domain
        except Exception as e:
            # 失败则递归尝试下一个域名
            return self.gettoken(i + 1, max_attempts)

    # 获取或生成设备 ID (did)
    def getdid(self):
        # 尝试从缓存获取 did
        did = self.getCache('did')
        if not did:
            # 缓存不存在则生成一个新的 did (当前时间戳的 MD5)
            t = str(int(time.time()))
            did = self.md5(t)
            self.setCache('did', did) # 存入缓存
        return did

    # MD5 哈希计算
    def md5(self, text):
        h = MD5.new()
        h.update(text.encode('utf-8'))
        return h.hexdigest()

    # 图片代理处理 (获取图片数据)
    def imgs(self, param):
        headers = {'User-Agent': self.ua}
        url = param['url'] # 图片路径，不包含域名
        
        # 1. 从图片域名 (self.phost) 获取图片数据
        data = self.fetch(f"{self.phost}{url}",headers=headers)
        
        # 2. 调用 img 方法对图片内容进行解密
        # key: '2020-zq3-888'
        # length: 100 (只对前 100 字节进行异或解密)
        bdata = self.img(data.content, 100, '2020-zq3-888')
        
        # 3. 返回结果：状态码、内容类型和解密后的图片字节数据
        return [200, data.headers.get('Content-Type'), bdata]

    # 图片解密 (异或解密)
    # data: 图片的原始字节数据
    # length: 异或解密的字节长度
    # key: 异或解密的密钥
    def img(self, data: bytes, length: int, key: str):
        # 常用图片格式的头部魔术字节
        GIF = b'\x47\x49\x46'
        JPG = b'\xFF\xD8\xFF'
        PNG = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'

        # 检查是否为 GIF 格式（不需要解密）
        def is_dont_need_decode_for_gif(data):
            return len(data) > 2 and data[:3] == GIF

        # 检查是否为 JPG 格式（不需要解密）
        def is_dont_need_decode_for_jpg(data):
            return len(data) > 7 and data[:3] == JPG

        # 检查是否为 PNG 格式（不需要解密）
        def is_dont_need_decode_for_png(data):
            # 注意这里只检查了从第 1 字节开始的 7 字节，这是对 PNG 头部特征的一个判断
            return len(data) > 7 and data[1:8] == PNG[1:8]

        # 如果图片头符合标准格式，则直接返回原始数据（不进行异或解密）
        if is_dont_need_decode_for_png(data):
            return data
        elif is_dont_need_decode_for_gif(data):
            return data
        elif is_dont_need_decode_for_jpg(data):
            return data
        else:
            # 如果图片头不符合标准格式，则认为它是被异或加密的
            key_bytes = key.encode('utf-8')
            result = bytearray(data) # 转换为可修改的 bytearray
            # 对图片的前 'length' (100) 个字节进行异或解密
            for i in range(length):
                # result[i] = result[i] XOR key_bytes[i % len(key_bytes)]
                result[i] ^= key_bytes[i % len(key_bytes)]
            return bytes(result) # 返回解密后的字节数据
