import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

def clean_channel_name(name):
    """清理频道名称：去除'-'、'高清'、'专区'等字眼"""
    # 去除"-"
    name = name.replace('-', '')
    
    # 去除"高清"字样
    name = name.replace('高清', '')
    
    # 去除"专区"字样
    name = name.replace('专区', '')
    
    # 去除多余空格
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

# 设置请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}

# 获取组播页面内容
url = "https://epg.51zmt.top:8001/sctvmulticast.html"
base_url = "https://epg.51zmt.top:8001/"

try:
    print(f"正在获取组播页面: {url}")
    response = requests.get(url, headers=headers, timeout=15)
    response.encoding = 'utf-8'
    response.raise_for_status()
except Exception as e:
    print(f"请求组播页面失败: {e}")
    exit()

# 解析HTML内容
soup = BeautifulSoup(response.text, 'html.parser')

# 定位表格
table = soup.find('table', {'id': 'mytable'})
if not table:
    table = soup.find('table', class_=re.compile(r'table'))
if not table:
    for t in soup.find_all('table'):
        if "频道名称" in t.text and "组播地址" in t.text:
            table = t
            break
if not table:
    table = soup.find('table')
    if not table:
        print("无法在页面中找到任何表格")
        exit()

# 处理直播流
live_count = 0
with open('iptv.m3u8', 'w', encoding='utf-8') as f_live:
    f_live.write("#EXTM3U\n")
    
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) < 6:
            continue
        
        try:
            index = int(cols[0].get_text(strip=True))
            if index < 1 or index > 186:
                continue
        except:
            continue
        
        status_col = cols[5].get_text(strip=True)
        if "未能播放" in status_col:
            continue
        
        # 提取原始频道名称
        original_name = cols[1].get_text(strip=True)
        
        # 清理频道名称
        channel_name = clean_channel_name(original_name)
        
        multicast_text = cols[2].get_text(strip=True)
        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}[^\s]*:\d+)', multicast_text)
        if not match:
            match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', multicast_text)
            if match:
                multicast_addr = match.group(1) + ":5140"
            else:
                continue
        else:
            multicast_addr = match.group(1)
        
        proxy_url = f"http://192.168.0.2:8888/udp/{multicast_addr}"
        
        # 写入m3u条目（使用清理后的频道名称）
        f_live.write(f'#EXTINF:-1, {channel_name}\n')
        f_live.write(f"{proxy_url}\n")
        live_count += 1

print(f"直播列表已写入iptv.m3u8文件，包含{live_count}个频道")
print(f"原始频道名称示例: {original_name} → 清理后: {channel_name}")

# 处理回放流
playback_count = 0
with open('iptv_playback.m3u8', 'w', encoding='utf-8') as f_playback:
    f_playback.write("#EXTM3U\n")
    
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) < 7:
            continue
        
        try:
            index = int(cols[0].get_text(strip=True))
            if index < 1 or index > 186:
                continue
        except:
            continue
        
        status_col = cols[5].get_text(strip=True)
        if "未能播放" in status_col:
            continue
        
        # 提取原始频道名称
        original_name = cols[1].get_text(strip=True)
        
        # 清理频道名称
        channel_name = clean_channel_name(original_name)
        
        playback_col = cols[6]
        playback_link = playback_col.find('a')
        if playback_link and playback_link.get('href'):
            playback_url = playback_link.get('href')
        else:
            playback_text = playback_col.get_text(strip=True)
            if playback_text and playback_text != "无":
                playback_url = playback_text
            else:
                continue
        
        if not playback_url.startswith(('http://', 'https://')):
            playback_url = urljoin(base_url, playback_url)
        
        # 写入m3u条目（使用清理后的频道名称）
        f_playback.write(f'#EXTINF:-1, {channel_name}\n')
        f_playback.write(f"{playback_url}\n")
        playback_count += 1

print(f"回放列表已写入iptv_playback.m3u8文件，包含{playback_count}个频道")
print("任务完成！")