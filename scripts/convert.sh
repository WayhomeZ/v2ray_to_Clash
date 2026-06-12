#!/bin/bash
set -e

mkdir -p docs sub_tmp

echo "Reading source URLs..."
SOURCE_FILE="config/source.txt"
mapfile -t URLS < <(grep -v '^#' "$SOURCE_FILE" | grep -v '^[[:space:]]*$')

if [ ${#URLS[@]} -eq 0 ]; then
    echo "Error: No valid URLs found in $SOURCE_FILE"
    exit 1
fi

echo "Downloading and merging subscriptions..."
rm -f sub_tmp/merged.txt sub_tmp/merged_final.txt

for u in "${URLS[@]}"; do
    echo "Fetching: $u"
    curl -sL "$u" >> sub_tmp/merged.txt
done

if grep -q "://" sub_tmp/merged.txt; then
    echo "Plaintext URIs detected! Base64 encoding..."
    base64 -w0 sub_tmp/merged.txt > sub_tmp/merged_final.txt
else
    echo "No plaintext URIs detected, assuming already encoded."
    cp sub_tmp/merged.txt sub_tmp/merged_final.txt
fi

echo "Starting local HTTP server to serve merged subscription..."
cd sub_tmp
python3 -m http.server 8080 &
HTTP_PID=$!
cd ..

echo "Starting Dockerized Subconverter..."
docker rm -f subconverter 2>/dev/null || true

# --network host so container can reach host's Python HTTP server via localhost
docker run -d --name subconverter --network host -v "${PWD}/config:/base/config" metacubex/subconverter:latest

sleep 3

LOCAL_URL="http://localhost:8080/merged_final.txt"
ENCODED_URL=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$LOCAL_URL'))")

echo "Generating pure proxies list (Proxy Provider mode)..."
curl -sL "http://localhost:25500/sub?target=clash&list=true&url=$ENCODED_URL" -o docs/proxies.yaml
echo "docs/proxies.yaml generated."

echo "Generating monolithic configuration..."
curl -sL "http://localhost:25500/sub?target=clash&config=config/flclash.ini&url=$ENCODED_URL" -o docs/config_monolithic.yaml
echo "docs/config_monolithic.yaml generated."

GEOIP_DB="config/GeoLite2-Country.mmdb"
if [ ! -f "$GEOIP_DB" ]; then
    echo "Downloading GeoIP Country database..."
    curl -sL "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb" -o "$GEOIP_DB"
fi

echo "Fixing Subconverter YAML IPv6 unquoted formatting bug and purifying nodes..."
python3 scripts/purify.py docs/proxies.yaml "$GEOIP_DB"
python3 scripts/purify.py docs/config_monolithic.yaml "$GEOIP_DB"

echo "Cleaning up..."
kill "$HTTP_PID" 2>/dev/null || true
docker rm -f subconverter 2>/dev/null || true
rm -rf sub_tmp

echo "Conversion completed successfully!"
