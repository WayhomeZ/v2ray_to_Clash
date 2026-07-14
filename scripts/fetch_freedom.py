#!/usr/bin/env python3
import urllib.request
import urllib.error
import re
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_freedom.py <output_file>")
        sys.exit(1)
    
    output_file = sys.argv[1]
    url = 'https://vpn.freedom8964.com/'
    
    print(f"Fetching additional nodes from {url} ...")
    try:
        # 伪装 User-Agent 防止基础拦截
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        response = urllib.request.urlopen(req, timeout=15)
        html = response.read().decode('utf-8')
        
        # 正则提取主流节点链接
        nodes = re.findall(r'(?:vmess|vless|ss|trojan)://[^\s"\'<>]+', html)
        
        # 去重保持顺序
        unique_nodes = list(dict.fromkeys(nodes))
        
        if unique_nodes:
            with open(output_file, 'w', encoding='utf-8') as f:
                for node in unique_nodes:
                    f.write(node + '\n')
            print(f"Successfully extracted {len(unique_nodes)} unique nodes to {output_file}.")
        else:
            print(f"Warning: No valid nodes found on {url}.")
            
    except Exception as e:
        # 捕获所有异常并打印，确保不以非0状态码退出，从而不妨碍整体流程
        print(f"Warning: Failed to fetch nodes from {url} - {e}")
        
if __name__ == "__main__":
    main()
