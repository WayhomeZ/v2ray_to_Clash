import sys
import os
import re
import time
import socket
import concurrent.futures
import yaml
import maxminddb

class FilterMetrics:
    def __init__(self, name):
        self.name = name
        self.start_time = 0.0
        self.end_time = 0.0
        self.input_count = 0
        self.output_count = 0
        
    def start(self, count):
        self.start_time = time.perf_counter()
        self.input_count = count
        
    def end(self, count):
        self.end_time = time.perf_counter()
        self.output_count = count
        
    @property
    def duration_ms(self):
        return (self.end_time - self.start_time) * 1000.0
        
    @property
    def filtered_count(self):
        return self.input_count - self.output_count
        
    @property
    def filter_rate_pct(self):
        if self.input_count == 0:
            return 0.0
        return (self.filtered_count / self.input_count) * 100.0

class GeoIPLookup:
    def __init__(self, db_path):
        self.db_path = db_path
        self.reader = None
        
    def __enter__(self):
        if os.path.exists(self.db_path):
            try:
                self.reader = maxminddb.open_database(self.db_path)
            except Exception as e:
                print(f"Error opening GeoIP DB: {e}")
        else:
            print(f"GeoIP Database not found at: {self.db_path}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.reader:
            self.reader.close()
            
    def lookup(self, ip):
        if not self.reader or not ip:
            return 'UN'
        try:
            res = self.reader.get(ip)
            if res:
                code = res.get('country', {}).get('iso_code')
                if code:
                    return code.upper()
        except Exception:
            pass
        return 'UN'

def check_tcp_port(server, port, timeout=2.0):
    try:
        addr_info = socket.getaddrinfo(server, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for res in addr_info:
            af, socktype, proto, canonname, sa = res
            s = socket.socket(af, socktype, proto)
            s.settimeout(timeout)
            try:
                s.connect(sa)
                s.close()
                return True, sa[0]
            except Exception:
                continue
        return False, None
    except Exception:
        return False, None

def check_all_proxies_connectivity(proxies, max_workers=100):
    alive_proxies = []
    
    def worker(p):
        server = p.get('server')
        port = p.get('port')
        if not server or not port:
            return None, None
        
        # Exclude loopback
        if server in ('127.0.0.1', 'localhost', '::1'):
            return None, None
            
        success, ip = check_tcp_port(server, port, timeout=2.0)
        if success:
            return p, ip
        return None, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(worker, proxies)
        
    for p, ip in results:
        if p is not None:
            alive_proxies.append((p, ip))
            
    return alive_proxies

def purify_yaml(file_path, db_path):
    print(f"Purifying {file_path}...")
    if not os.path.exists(file_path):
        print(f"Error: {file_path} does not exist.")
        return None, 0, 0
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Pre-process raw text to fix unquoted IPv6 and remove control characters
    content = re.sub(r'server:\s+([^\s\"\'\{][^,\}\n]*)', r'server: "\1"', content)
    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', content)
    
    config = yaml.safe_load(content)
    if not config or 'proxies' not in config:
        print("No proxies found in configuration.")
        return None, 0, 0
        
    proxies = config['proxies']
    total_initial = len(proxies)
    
    # Store initial name map to rename references in proxy-groups later
    name_map = {p['name']: p['name'] for p in proxies}
    
    # Define metric trackers for 8 distinct layers
    layer1 = FilterMetrics("Server 主机过滤")
    layer2 = FilterMetrics("Port 端口过滤")
    layer3 = FilterMetrics("TCP 连通性过滤")
    layer4 = FilterMetrics("GeoIP 地区标记")
    layer5 = FilterMetrics("SS Cipher 过滤")
    layer6 = FilterMetrics("Reality Short-ID 过滤")
    layer7 = FilterMetrics("UUID 格式过滤")
    layer8 = FilterMetrics("Identity 节点去重")
    
    # ------------------ Layer 1: Server ------------------
    layer1.start(len(proxies))
    l1_proxies = []
    for p in proxies:
        server = p.get('server')
        if not server or not isinstance(server, str):
            continue
        if server in ('127.0.0.1', 'localhost', '::1'):
            continue
        l1_proxies.append(p)
    layer1.end(len(l1_proxies))
    
    # ------------------ Layer 2: Port ------------------
    layer2.start(len(l1_proxies))
    l2_proxies = []
    for p in l1_proxies:
        port = p.get('port')
        try:
            port_val = int(port)
            if 0 < port_val <= 65535:
                p['port'] = port_val
                l2_proxies.append(p)
        except (ValueError, TypeError):
            continue
    layer2.end(len(l2_proxies))
    
    # ------------------ Layer 3: TCP Connectivity ------------------
    layer3.start(len(l2_proxies))
    print(f"Performing TCP connectivity checks on {len(l2_proxies)} endpoints...")
    l3_results = check_all_proxies_connectivity(l2_proxies)
    l3_proxies = [item[0] for item in l3_results]
    layer3.end(len(l3_proxies))
    
    # Map from proxy index in l3_proxies to resolved IP
    proxy_ips = {id(item[0]): item[1] for item in l3_results}
    
    # ------------------ Layer 4: GeoIP Tagging ------------------
    layer4.start(len(l3_proxies))
    l4_proxies = []
    with GeoIPLookup(db_path) as geoip:
        for p in l3_proxies:
            ip = proxy_ips.get(id(p))
            country = geoip.lookup(ip)
            
            # Rename the proxy to prefix country code
            old_name = p['name']
            new_name = f"[{country}] {old_name}"
            p['name'] = new_name
            name_map[old_name] = new_name
            
            l4_proxies.append(p)
    layer4.end(len(l4_proxies))
    
    # ------------------ Layer 5: SS Cipher ------------------
    layer5.start(len(l4_proxies))
    l5_proxies = []
    for p in l4_proxies:
        cipher = p.get('cipher')
        if cipher == 'ss':
            continue
        if cipher == 'chacha20-poly1305':
            p['cipher'] = 'chacha20-ietf-poly1305'
        l5_proxies.append(p)
    layer5.end(len(l5_proxies))
    
    # ------------------ Layer 6: Reality Short-ID ------------------
    layer6.start(len(l5_proxies))
    l6_proxies = []
    for p in l5_proxies:
        ptype = p.get('type')
        valid = True
        if ptype == 'vless':
            opts = p.get('reality-opts', {})
            sid = opts.get('short-id')
            if sid is not None:
                sid_str = str(sid)
                try:
                    bytes.fromhex(sid_str)
                    if len(sid_str) % 2 != 0 or len(sid_str) > 16:
                        valid = False
                except Exception:
                    valid = False
        if valid:
            l6_proxies.append(p)
    layer6.end(len(l6_proxies))
    
    # ------------------ Layer 7: UUID ------------------
    layer7.start(len(l6_proxies))
    l7_proxies = []
    for p in l6_proxies:
        ptype = p.get('type')
        valid = True
        if ptype in ('vmess', 'vless'):
            uuid_str = p.get('uuid')
            if not uuid_str or not isinstance(uuid_str, str) or len(uuid_str) != 36:
                valid = False
        if valid:
            l7_proxies.append(p)
    layer7.end(len(l7_proxies))
    
    # ------------------ Layer 8: Identity Deduplication ------------------
    layer8.start(len(l7_proxies))
    l8_proxies = []
    seen_keys = set()
    
    for p in l7_proxies:
        ptype = p.get('type')
        server = p.get('server')
        port = p.get('port')
        
        cred = ""
        if ptype in ('vless', 'vmess'):
            cred = p.get('uuid', '')
        elif ptype in ('ss', 'trojan'):
            cred = p.get('password', '')
            
        identity_key = (ptype, server, port, cred)
        
        if identity_key not in seen_keys:
            seen_keys.add(identity_key)
            l8_proxies.append(p)
            
    layer8.end(len(l8_proxies))
    
    # Save the cleaned proxies
    config['proxies'] = l8_proxies
    valid_names_new = {p['name'] for p in l8_proxies}
    
    # Define mapping from regional group names to country code prefix
    regional_groups_map = {
        '🇭🇰 香港节点': 'HK',
        '🇹🇼 台湾节点': 'TW',
        '🇯🇵 日本节点': 'JP',
        '🇸🇬 狮城节点': 'SG',
        '🇺🇸 美国节点': 'US'
    }
    
    # Update proxy names, regroup regional groups, and remove dropped ones
    if 'proxy-groups' in config:
        for group in config['proxy-groups']:
            gname = group.get('name')
            if gname in regional_groups_map:
                # Regroup regional groups using GeoIP tags from purified proxies
                target_code = regional_groups_map[gname]
                group['proxies'] = [p['name'] for p in l8_proxies if p['name'].startswith(f"[{target_code}]")]
            elif 'proxies' in group and isinstance(group['proxies'], list):
                # For non-regional groups, update names and remove dropped ones
                new_group_proxies = []
                for name in group['proxies']:
                    if name in name_map:
                        new_name = name_map[name]
                        if new_name in valid_names_new:
                            new_group_proxies.append(new_name)
                    else:
                        new_group_proxies.append(name)
                group['proxies'] = new_group_proxies
                
    output_content = yaml.safe_dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)
    output_content = re.sub(r'server:\s+([^\s\"\'\{][^,\}\n]*)', r'server: "\1"', output_content)
    output_content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', output_content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(output_content)
        
    print(f"Purification completed. Remaining proxies: {len(l8_proxies)} / {total_initial}")
    return [layer1, layer2, layer3, layer4, layer5, layer6, layer7, layer8], total_initial, len(l8_proxies)

def generate_report(metrics_list, initial, final):
    report_path = 'docs/filter_report.md'
    total_duration = sum(m.duration_ms for m in metrics_list)
    total_filtered = initial - final
    total_rate = (total_filtered / initial * 100.0) if initial > 0 else 0.0
    
    rows = []
    for i, m in enumerate(metrics_list):
        rows.append(
            f"| {i+1}. {m.name} | {m.input_count} | {m.output_count} | {m.filtered_count} | {m.filter_rate_pct:.2f}% | {m.duration_ms:.4f} ms |"
        )
    table_content = "\n".join(rows)
    
    report_content = f"""# 节点过滤与评估报告 (Node Filtering Evaluation Report)

*生成时间 (UTC): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}*

### 📊 过滤层级度量数据 (Metrics by Filtering Layer)

| 过滤层级 (Filter Layer) | 输入节点数 | 留存节点数 | 过滤节点数 | 过滤占比 | 耗时 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
{table_content}

### 📈 过滤效果综合评价 (Overall Evaluation)

- **原始节点总数 (Initial Nodes)**: `{initial}`
- **净化后有效节点数 (Retained Nodes)**: `{final}`
- **过滤及去重节点总数 (Filtered Total)**: `{total_filtered}`
- **整体过滤/去重率 (Overall Filtering Rate)**: `{total_rate:.2f}%`
- **总处理耗时 (Total Duration)**: `{total_duration:.4f} ms`

---
*注：本报告由自动化节点净化脚本自动生成。*
"""
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"Report generated at {report_path}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python purify.py <path_to_yaml> [path_to_mmdb]")
        sys.exit(1)
        
    target_file = sys.argv[1]
    db_file = sys.argv[2] if len(sys.argv) > 2 else 'config/GeoLite2-Country.mmdb'
    metrics, initial, final = purify_yaml(target_file, db_file)
    
    if metrics and 'proxies.yaml' in target_file:
        generate_report(metrics, initial, final)
