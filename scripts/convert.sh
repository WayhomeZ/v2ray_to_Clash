#!/bin/bash
set -e

# Create output directories
mkdir -p docs

echo "Reading source URLs..."
# Extract URLs ignoring comments and empty lines
urls=$(grep -v '^#' config/source.txt | grep -v '^[[:space:]]*$')

if [ -z "$urls" ]; then
    echo "Error: No valid URLs found in config/source.txt"
    exit 1
fi

echo "Downloading and merging subscriptions..."
mkdir -p sub_tmp
rm -f sub_tmp/merged.txt sub_tmp/merged_final.txt

for u in $urls; do
    echo "Fetching: $u"
    curl -sL "$u" >> sub_tmp/merged.txt
    echo "" >> sub_tmp/merged.txt
done

# Check if the merged file contains plain text URIs like vless:// or trojan://
if grep -q "://" sub_tmp/merged.txt; then
    echo "Plaintext URIs detected! Base64 encoding for Subconverter compatibility..."
    base64 -w 0 sub_tmp/merged.txt > sub_tmp/merged_final.txt
else
    echo "No plaintext URIs detected, assuming it's already encoded or a standard config."
    cp sub_tmp/merged.txt sub_tmp/merged_final.txt
fi

echo "Starting local HTTP server to serve the merged subscription..."
cd sub_tmp
python3 -m http.server 8080 &
HTTP_PID=$!
cd ..

# Give the python server a second to start
sleep 2

echo "Starting Dockerized Subconverter..."
# Stop any existing container
docker rm -f subconverter >/dev/null 2>&1 || true
# Start metacubex/subconverter for VLESS/Reality support using host network so it can reach localhost:8080
docker run -d --name subconverter --network host -v "$(pwd)/config:/base/config" metacubex/subconverter:latest

# Run healthcheck
bash ./scripts/healthcheck.sh

# Point subconverter to our local HTTP server
local_url="http://127.0.0.1:8080/merged_final.txt"
encoded_urls=$(python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))" "$local_url")

echo "Generating pure proxies list (Proxy Provider mode)..."
http_code=$(curl -s -w "%{http_code}" -o docs/proxies.yaml "http://127.0.0.1:25500/sub?target=clash&list=true&url=${encoded_urls}")
if [ "$http_code" != "200" ]; then
    echo "Error: Subconverter failed with HTTP code $http_code. Response body:"
    cat docs/proxies.yaml
    kill $HTTP_PID
    exit 1
fi
echo "docs/proxies.yaml generated."

echo "Generating monolithic configuration..."
http_code=$(curl -s -w "%{http_code}" -o docs/config_monolithic.yaml "http://127.0.0.1:25500/sub?target=clash&config=config/flclash.ini&url=${encoded_urls}")
if [ "$http_code" != "200" ]; then
    echo "Error: Subconverter monolithic failed with HTTP code $http_code. Response body:"
    cat docs/config_monolithic.yaml
    kill $HTTP_PID
    exit 1
fi
echo "docs/config_monolithic.yaml generated."

echo "Fixing Subconverter YAML IPv6 unquoted formatting bug..."
python3 -c "
import yaml
import re

def fix_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = re.sub(r'server:\s+([^\s\"\'\{][^,\}\n]*)', r'server: \"\1\"', content)
    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', content)
    
    config = yaml.safe_load(content)
    
    if not config or 'proxies' not in config:
        return

    invalid_names = set()
    valid_proxies = []
    
    for p in config['proxies']:
        valid = True
        
        if p.get('cipher') == 'ss':
            valid = False
            
        if p.get('cipher') == 'chacha20-poly1305':
            p['cipher'] = 'chacha20-ietf-poly1305'
            
        if p.get('type') == 'vless':
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
            valid_proxies.append(p)
        else:
            invalid_names.add(p['name'])
            
    config['proxies'] = valid_proxies
    
    if 'proxy-groups' in config:
        for group in config['proxy-groups']:
            if 'proxies' in group and isinstance(group['proxies'], list):
                group['proxies'] = [name for name in group['proxies'] if name not in invalid_names]
                
    content = yaml.safe_dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    content = re.sub(r'server:\s+([^\s\"\'\{][^,\}\n]*)', r'server: \"\1\"', content)
    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

fix_yaml('docs/proxies.yaml')
fix_yaml('docs/config_monolithic.yaml')
"

echo "Cleaning up..."
kill $HTTP_PID
docker rm -f subconverter >/dev/null 2>&1 || true
rm -rf sub_tmp

echo "Conversion completed successfully!"
