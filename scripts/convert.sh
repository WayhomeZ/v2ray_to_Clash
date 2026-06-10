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

# URL-encode function using bash
urlencode() {
    local string="${1}"
    local strlen=${#string}
    local encoded=""
    local pos c o
    for (( pos=0 ; pos<strlen ; pos++ )); do
        c=${string:$pos:1}
        case "$c" in
            [-_.~a-zA-Z0-9] ) o="${c}" ;;
            * )               printf -v o '%%%02x' "'$c"
        esac
        encoded="${encoded}${o}"
    done
    echo "${encoded}"
}

encoded_urls=$(urlencode "$urls")

echo "Starting Dockerized Subconverter..."
# Stop any existing container
docker rm -f subconverter 2>/dev/null || true

# Run Subconverter and mount the local config directory to /base/config
# Workaround for docker running in Windows GitHub Actions or Unix: $(pwd) works in git bash/WSL
docker run -d --name subconverter -p 25500:25500 -v "$(pwd)/config:/base/config" tindy2013/subconverter:latest

# Run healthcheck
bash ./scripts/healthcheck.sh

echo "Generating pure proxies list (Proxy Provider mode)..."
curl -s -S -f -o docs/proxies.yaml "http://localhost:25500/sub?target=clashmeta&list=true&url=${encoded_urls}"
echo "docs/proxies.yaml generated."

echo "Generating monolithic configuration..."
curl -s -S -f -o docs/config_monolithic.yaml "http://localhost:25500/sub?target=clashmeta&config=config/flclash.ini&url=${encoded_urls}"
echo "docs/config_monolithic.yaml generated."

echo "Stopping Subconverter..."
docker stop subconverter
docker rm subconverter

echo "Conversion step completed."
