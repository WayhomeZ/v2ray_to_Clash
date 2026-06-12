#!/bin/bash
set -e

TEMPLATE="config/config_template.yaml"
OUTPUT="docs/config.yaml"

OWNER="${GITHUB_REPOSITORY_OWNER:-$(git config --get remote.origin.url | sed -n 's/.*github.com[\/:]\([^\/]*\)\/.*/\1/p')}"
REPO="${GITHUB_REPOSITORY#*/}"
if [ -z "$REPO" ]; then
    REPO="$(git config --get remote.origin.url | sed -n 's/.*\/\([^\/]*\)\.git/\1/p')"
fi

if [ -z "$OWNER" ] || [ -z "$REPO" ]; then
    echo "Error: Could not determine owner/repo"
    exit 1
fi

echo "Generating Proxy-Provider config for $OWNER/$REPO..."
sed "s/<owner>/$OWNER/g; s/<repo>/$REPO/g" "$TEMPLATE" > "$OUTPUT"
echo "docs/config.yaml generated."
