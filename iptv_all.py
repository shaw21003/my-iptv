import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

# 获取网页内容
url = "https://epg.51zmt.top:8001/sctvmulticast.html"
base_url = "https://epg.51zmt.top:8001/"  # 用于拼接相对URL
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = 'utf-8'
    response.raise_for_status()  # 检查请求是否成功
except requests.exceptions.RequestException as e:
    print(f"请求网页失败: {e}")
    exit()

# 解析HTML内容
soup = BeautifulSoup(response.text, 'html.parser')

# 尝试多种方式定位表格
table = soup.find('table', {'id': 'mytable'})  # 先尝试按ID查找

# 如果按ID找不到，尝试按class或其他特征查找
if not table:
    table = soup.find('table', class_=re.compile(r'table'))
    
if not table:
    # 如果还是找不到，尝试查找包含特定文本的表格
    for t in soup.find_all('table'):
        if "频道名称" in t.text and "组播地址" in t.text:
            table = t
            break

if not table:
    # 作为最后的手段，使用页面中的第一个表格
    table = soup.find('table')
    if not table:
        raise ValueError("无法在页面中找到任何表格")

# 处理直播流（组播地址）
with open('iptv.m3u8', 'w', encoding='utf-8') as f_live:
    f_live.write("#EXTM3U\n")  # 文件头部
    
    # 遍历表格行
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        # 确保有足够的列（至少6列）
        if len(cols) < 6:
            continue
        
        # 提取第一列（序号）
        try:
            index = int(cols[0].get_text(strip=True))
        except ValueError:
            continue  # 跳过无法转换为整数的行
        
        # 过滤序号：只保留1-186的频道
        if index < 1 or index > 186:
            continue
        
        # 检查第六列（清晰度/帧率/编码）是否包含"未能播放"
        status_col = cols[5].get_text(strip=True)  # 第六列是索引5
        if "未能播放" in status_col:
            continue  # 跳过不能播放的频道
        
        # 提取频道名称（第二列）
        channel_name = cols[1].get_text(strip=True)
        
        # 提取组播地址（第三列）
        multicast_text = cols[2].get_text(strip=True)
        
        # 使用正则提取IP:PORT格式的地址
        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}[^\s]*:\d+)', multicast_text)
        if not match:
            # 尝试其他可能的地址格式
            match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', multicast_text)
            if match:
                # 如果只有IP没有端口，尝试添加默认端口
                multicast_addr = match.group(1) + ":5140"  # 使用5140作为默认端口
            else:
                continue
        else:
            multicast_addr = match.group(1)
        
        # 转换为代理URL格式
        proxy_url = f"http://192.168.0.2:8888/udp/{multicast_addr}"
        
        # 写入m3u条目
        f_live.write(f"#EXTINF:-1, {channel_name}\n")
        f_live.write(f"{proxy_url}\n")

print(f"直播列表已写入iptv.m3u8文件")

# 处理回放流
with open('iptv_playback.m3u8', 'w', encoding='utf-8') as f_playback:
    f_playback.write("#EXTM3U\n")  # 文件头部
    
    # 遍历表格行
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        # 确保有足够的列（至少7列）
        if len(cols) < 7:
            continue
        
        # 提取第一列（序号）
        try:
            index = int(cols[0].get_text(strip=True))
        except ValueError:
            continue  # 跳过无法转换为整数的行
        
        # 过滤序号：只保留1-186的频道
        if index < 1 or index > 186:
            continue
        
        # 检查第六列（清晰度/帧率/编码）是否包含"未能播放"
        status_col = cols[5].get_text(strip=True)  # 第六列是索引5
        if "未能播放" in status_col:
            continue  # 跳过不能播放的频道
        
        # 提取频道名称（第二列）
        channel_name = cols[1].get_text(strip=True)
        
        # 提取回放地址（第七列）
        playback_col = cols[6]
        
        # 尝试从链接中获取回放地址
        playback_link = playback_col.find('a')
        if playback_link and playback_link.get('href'):
            playback_url = playback_link.get('href')
        else:
            # 如果没有链接，尝试获取文本内容
            playback_text = playback_col.get_text(strip=True)
            if playback_text and playback_text != "无":
                playback_url = playback_text
            else:
                continue  # 没有有效的回放地址
        
        # 确保回放地址是完整的URL
        if not playback_url.startswith(('http://', 'https://')):
            playback_url = urljoin(base_url, playback_url)
        
        # 写入m3u条目
        f_playback.write(f"#EXTINF:-1, {channel_name}\n")
        f_playback.write(f"{playback_url}\n")

print(f"回放列表已写入iptv_playback.m3u8文件")
print(f"任务完成！共处理序号1-186的可播放频道")