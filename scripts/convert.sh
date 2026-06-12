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
python3 scripts/purify.py docs/proxies.yaml
python3 scripts/purify.py docs/config_monolithic.yaml

echo "Cleaning up..."
kill $HTTP_PID
docker rm -f subconverter >/dev/null 2>&1 || true
rm -rf sub_tmp

echo "Conversion completed successfully!"
