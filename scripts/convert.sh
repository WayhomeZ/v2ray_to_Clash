#!/bin/bash
set -e

# Create output directories
mkdir -p docs

echo "Reading source URLs..."
urls=""
while IFS= read -r line || [ -n "$line" ]; do
    # Trim whitespace
    line=$(echo "$line" | xargs)
    # Ignore empty lines and comments
    if [[ -n "$line" && ! "$line" =~ ^# ]]; then
        if [ -z "$urls" ]; then
            urls="$line"
        else
            urls="${urls}|${line}"
        fi
    fi
done < config/source.txt

if [ -z "$urls" ]; then
    echo "Error: No valid URLs found in config/source.txt"
    exit 1
fi

echo "Source URLs read successfully."

# URL-encode function using Python3
encoded_urls=$(python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))" "$urls")

echo "Starting Dockerized Subconverter..."
# Stop any existing container
docker rm -f subconverter 2>/dev/null || true

# Run Subconverter and mount the local config directory to /base/config
# Workaround for docker running in Windows GitHub Actions or Unix: $(pwd) works in git bash/WSL
docker run -d --name subconverter -p 25500:25500 -v "$(pwd)/config:/base/config" tindy2013/subconverter:latest

# Run healthcheck
bash ./scripts/healthcheck.sh

echo "Generating pure proxies list (Proxy Provider mode)..."
http_code=$(curl -s -w "%{http_code}" -o docs/proxies.yaml "http://localhost:25500/sub?target=clash&list=true&url=${encoded_urls}")
if [ "$http_code" != "200" ]; then
    echo "Error: Subconverter failed with HTTP code $http_code. Response body:"
    cat docs/proxies.yaml
    exit 1
fi
echo "docs/proxies.yaml generated."

echo "Generating monolithic configuration..."
http_code=$(curl -s -w "%{http_code}" -o docs/config_monolithic.yaml "http://localhost:25500/sub?target=clash&config=config/flclash.ini&url=${encoded_urls}")
if [ "$http_code" != "200" ]; then
    echo "Error: Subconverter monolithic failed with HTTP code $http_code. Response body:"
    cat docs/config_monolithic.yaml
    exit 1
fi
echo "docs/config_monolithic.yaml generated."

echo "Stopping Subconverter..."
docker stop subconverter
docker rm subconverter

echo "Conversion step completed."
