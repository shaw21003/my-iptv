import requests
import json
import re

# 目标API URL
base_url = "http://www.51zmt.top"
api_url = f"{base_url}/multicast/api/channels/1/"  # sourceId=1 对应四川成都电信

# 设置请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'http://www.51zmt.top/multicast/',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

# 定义分组规则（4K优先级最高）
def classify_channel(channel_name, video_info):
    """
    根据频道名称和视频信息分类
    优先级：4K > 央视 > 卫视 > 其他
    """
    channel_name_lower = channel_name.lower()
    
    # 首先检查是否是4K频道
    is_4k = False
    
    # 检查视频信息中的分辨率
    if video_info:
        resolution = video_info.get('resolution', '').upper()
        if '4K' in resolution or 'UHD' in resolution:
            is_4k = True
    
    # 检查频道名称是否包含4K/UHD
    if not is_4k and ('4k' in channel_name_lower or 'uhd' in channel_name_lower or '2160' in channel_name_lower):
        is_4k = True
    
    if is_4k:
        return '4K'
    
    # 然后是央视分组
    cctv_keywords = ['cctv', 'cgtn', '央视']
    for keyword in cctv_keywords:
        if keyword in channel_name_lower:
            return '央视'
    
    # 然后是卫视分组
    satellite_keywords = ['卫视', 'tvb', '凤凰', '澳亚', '澳视']
    for keyword in satellite_keywords:
        if keyword in channel_name_lower:
            return '卫视'
    
    # 检查是否是卫视（以省份开头的频道）
    provinces = ['北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江', 
                 '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
                 '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾',
                 '内蒙古', '广西', '西藏', '宁夏', '新疆']
    for province in provinces:
        if channel_name.startswith(province):
            return '卫视'
    
    # 默认分组
    return '其他'

# 央视频道排序函数 - 修正版
def sort_cctv_channels(channels):
    """
    对央视频道进行排序：按CCTV后的数字大小排序
    CCTV-1, CCTV-2, ..., CCTV-9, CCTV-10, CCTV-11, ..., CCTV-16, CCTV-17, 其他央视
    """
    
    def extract_cctv_number(channel_name):
        """
        提取CCTV后面的数字
        返回：数字（如果找到），否则返回大数（用于排序）
        """
        name = channel_name.upper()
        
        # 尝试匹配 CCTV-数字 格式
        cctv_pattern = r'CCTV[-\s]*(\d+)'
        match = re.search(cctv_pattern, name)
        if match:
            try:
                return int(match.group(1))  # 返回数字
            except:
                pass
        
        # 尝试匹配 央视数字 格式
        cctv_chinese_pattern = r'央视\s*(\d+)'
        match = re.search(cctv_chinese_pattern, name)
        if match:
            try:
                return int(match.group(1))  # 返回数字
            except:
                pass
        
        # 特殊频道处理
        if 'CCTV-5+' in name or 'CCTV5+' in name or 'CCTV-5体育赛事' in name:
            return 5.5  # CCTV-5+ 排在 CCTV-5 和 CCTV-6 之间
        
        if 'CGTN' in name:
            return 9998  # CGTN 排在数字央视之后
        
        if 'CCTV' in name or '央视' in name:
            return 9999  # 其他央视排在最后
        
        return 10000  # 非央视，理论上不应该出现在这个分组
    
    # 按提取的数字排序
    return sorted(channels, key=lambda x: extract_cctv_number(x.get('channel_name', '')))

# 代理服务器地址（请根据实际情况修改）
PROXY_SERVER = "http://192.168.0.2:8888/udp/"

# 只爬取前N个频道
MAX_CHANNELS = 193

try:
    # 发送请求获取频道数据
    print(f"正在请求API: {api_url}")
    response = requests.get(api_url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get('success'):
            # 提取数据
            source_info = data.get('source', {})
            channels = data.get('channels', [])
            
            print(f"成功获取数据:")
            print(f"地区: {source_info.get('name', '未知')}")
            print(f"总频道数量: {len(channels)}")
            
            # 只取前193个频道
            if len(channels) > MAX_CHANNELS:
                channels = channels[:MAX_CHANNELS]
                print(f"只处理前 {MAX_CHANNELS} 个频道")
            
            # 按分组统计
            group_stats = {'央视': 0, '卫视': 0, '4K': 0, '其他': 0}
            grouped_channels = {'央视': [], '卫视': [], '4K': [], '其他': []}
            
            # 对频道进行分组
            for channel in channels:
                channel_name = channel.get('channel_name', '')
                video_info = channel.get('video_info', {})
                group = classify_channel(channel_name, video_info)
                
                # 记录到对应分组
                channel['group'] = group
                grouped_channels[group].append(channel)
                group_stats[group] += 1
            
            # 对央视分组进行特殊排序
            if grouped_channels['央视']:
                grouped_channels['央视'] = sort_cctv_channels(grouped_channels['央视'])
            
            # 对其他分组按名称排序
            for group in ['卫视', '4K', '其他']:
                if grouped_channels[group]:
                    grouped_channels[group].sort(key=lambda x: x.get('channel_name', ''))
            
            # 打印分组统计
            print(f"\n分组统计（4K优先级最高）:")
            for group, count in group_stats.items():
                if count > 0:
                    print(f"  {group}: {count} 个频道")
            
            # 显示央视频道排序示例
            if grouped_channels['央视']:
                print(f"\n央视频道排序结果（按数字大小）:")
                for i, channel in enumerate(grouped_channels['央视'], 1):
                    name = channel.get('channel_name', '')
                    cctv_num = re.search(r'CCTV[-\s]*(\d+)', name.upper())
                    if cctv_num:
                        print(f"  {i:2d}. {name} (CCTV-{cctv_num.group(1)})")
                    else:
                        print(f"  {i:2d}. {name}")
            
            # 写入组播地址文件（使用HTTP代理格式）- 去掉分辨率信息
            with open("IPTV.m3u8", 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                
                # 按分组写入：央视 -> 卫视 -> 4K -> 其他
                for group in ['央视', '卫视', '4K', '其他']:
                    channels_in_group = grouped_channels[group]
                    
                    if not channels_in_group:
                        continue
                    
                    for i, channel in enumerate(channels_in_group, 1):
                        channel_name = channel.get('channel_name', '')
                        multicast_addr = channel.get('multicast_address', '')
                        
                        if not multicast_addr:
                            continue
                        
                        # 构建HTTP代理格式的播放地址
                        # 格式: http://192.168.0.2:8888/udp/239.94.0.31:5140
                        if ':' in multicast_addr:
                            play_url = f"{PROXY_SERVER}{multicast_addr}"
                        else:
                            continue
                        
                        # 构建EXTINF行 - 只保留频道名称，去掉分辨率信息
                        extinf_line = f'#EXTINF:-1 tvg-id="{i}" tvg-name="{channel_name}" group-title="{group}",{channel_name}'
                        
                        # 写入文件
                        f.write(extinf_line + '\n')
                        f.write(play_url + '\n')
            
            # 写入回放地址文件（保持原分组和排序）- 去掉时移信息
            with open("IPTV_Playback.m3u8", 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                
                for group in ['央视', '卫视', '4K', '其他']:
                    channels_in_group = grouped_channels[group]
                    
                    if not channels_in_group:
                        continue
                    
                    for i, channel in enumerate(channels_in_group, 1):
                        channel_name = channel.get('channel_name', '')
                        replay_url = channel.get('replay_url', '')
                        
                        if not replay_url or not replay_url.startswith('rtsp://'):
                            continue
                        
                        # 构建EXTINF行 - 只保留频道名称，去掉时移信息
                        extinf_line = f'#EXTINF:-1 tvg-id="{i}" tvg-name="{channel_name}" group-title="{group}",{channel_name}'
                        
                        f.write(extinf_line + '\n')
                        f.write(replay_url + '\n')
            
            # 计算实际写入的频道数
            multicast_count = sum(group_stats.values())
            replay_count = sum(1 for c in channels if c.get('replay_url') and c.get('replay_url').startswith('rtsp://'))
            
            print(f"\n文件生成完成:")
            print(f"1. IPTV.m3u8 - 包含 {multicast_count} 个组播频道")
            print(f"2. IPTV_Playback.m3u8 - 包含 {replay_count} 个回放频道")
            
            # 显示文件内容示例
            print(f"\nIPTV.m3u8 文件示例（前5个频道）:")
            with open("IPTV.m3u8", 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines[:10]):  # 显示前10行（5个频道）
                    if i < 10:
                        print(f"  {line.strip()}")
            
        else:
            print(f"API返回失败: {data.get('error', '未知错误')}")
    else:
        print(f"请求失败，状态码: {response.status_code}")
        print(f"响应内容: {response.text[:200]}")

except requests.exceptions.RequestException as e:
    print(f"网络请求错误: {e}")
except json.JSONDecodeError as e:
    print(f"JSON解析错误: {e}")
    print(f"原始响应: {response.text[:500]}")
except Exception as e:
    print(f"发生错误: {e}")
    import traceback
    traceback.print_exc()
