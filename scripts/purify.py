import sys
import os
import re
import time
import yaml

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

def purify_yaml(file_path):
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
    
    # Define metric trackers
    layer1 = FilterMetrics("Server 主机过滤")
    layer2 = FilterMetrics("Port 端口过滤")
    layer3 = FilterMetrics("Protocol 协议过滤")
    layer4 = FilterMetrics("Identity 节点去重")
    
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
    
    # ------------------ Layer 3: Protocol ------------------
    layer3.start(len(l2_proxies))
    l3_proxies = []
    for p in l2_proxies:
        valid = True
        ptype = p.get('type')
        
        cipher = p.get('cipher')
        if cipher == 'ss':
            valid = False
        elif cipher == 'chacha20-poly1305':
            p['cipher'] = 'chacha20-ietf-poly1305'
            
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
                    
        if ptype in ('vmess', 'vless'):
            uuid_str = p.get('uuid')
            if not uuid_str or not isinstance(uuid_str, str) or len(uuid_str) != 36:
                valid = False
                
        if valid:
            l3_proxies.append(p)
    layer3.end(len(l3_proxies))
    
    # ------------------ Layer 4: Identity Deduplication ------------------
    layer4.start(len(l3_proxies))
    l4_proxies = []
    seen_keys = set()
    invalid_names = set()
    
    for p in l3_proxies:
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
            l4_proxies.append(p)
        else:
            invalid_names.add(p['name'])
            
    l4_names = {p['name'] for p in l4_proxies}
    for p in proxies:
        if p['name'] not in l4_names:
            invalid_names.add(p['name'])
            
    layer4.end(len(l4_proxies))
    
    config['proxies'] = l4_proxies
    
    if 'proxy-groups' in config:
        for group in config['proxy-groups']:
            if 'proxies' in group and isinstance(group['proxies'], list):
                group['proxies'] = [name for name in group['proxies'] if name not in invalid_names]
                
    output_content = yaml.safe_dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)
    output_content = re.sub(r'server:\s+([^\s\"\'\{][^,\}\n]*)', r'server: "\1"', output_content)
    output_content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', output_content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(output_content)
        
    print(f"Purification completed. Remaining proxies: {len(l4_proxies)} / {total_initial}")
    return [layer1, layer2, layer3, layer4], total_initial, len(l4_proxies)

def generate_report(metrics_list, initial, final):
    report_path = 'docs/filter_report.md'
    total_duration = sum(m.duration_ms for m in metrics_list)
    total_filtered = initial - final
    total_rate = (total_filtered / initial * 100.0) if initial > 0 else 0.0
    
    report_content = f"""# 节点过滤与评估报告 (Node Filtering Evaluation Report)

*生成时间 (UTC): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}*

### 📊 过滤层级度量数据 (Metrics by Filtering Layer)

| 过滤层级 (Filter Layer) | 输入节点数 | 留存节点数 | 过滤节点数 | 过滤占比 | 耗时 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 1. {metrics_list[0].name} | {metrics_list[0].input_count} | {metrics_list[0].output_count} | {metrics_list[0].filtered_count} | {metrics_list[0].filter_rate_pct:.2f}% | {metrics_list[0].duration_ms:.4f} ms |
| 2. {metrics_list[1].name} | {metrics_list[1].input_count} | {metrics_list[1].output_count} | {metrics_list[1].filtered_count} | {metrics_list[1].filter_rate_pct:.2f}% | {metrics_list[1].duration_ms:.4f} ms |
| 3. {metrics_list[2].name} | {metrics_list[2].input_count} | {metrics_list[2].output_count} | {metrics_list[2].filtered_count} | {metrics_list[2].filter_rate_pct:.2f}% | {metrics_list[2].duration_ms:.4f} ms |
| 4. {metrics_list[3].name} | {metrics_list[3].input_count} | {metrics_list[3].output_count} | {metrics_list[3].filtered_count} | {metrics_list[3].filter_rate_pct:.2f}% | {metrics_list[3].duration_ms:.4f} ms |

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
        print("Usage: python purify.py <path_to_yaml>")
        sys.exit(1)
        
    target_file = sys.argv[1]
    metrics, initial, final = purify_yaml(target_file)
    
    if metrics and 'proxies.yaml' in target_file:
        generate_report(metrics, initial, final)
