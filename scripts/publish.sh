#!/bin/bash
set -e

# Load .env file if it exists for local testing
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Fallback values
owner=${GITHUB_REPOSITORY_OWNER:-"username"}
repo_full=${GITHUB_REPOSITORY:-"username/repo"}

# Extract owner and repo
owner_lower=$(echo "$owner" | tr '[:upper:]' '[:lower:]')
repo=$(echo "$repo_full" | cut -d'/' -f2)

echo "Publishing for Owner: ${owner_lower}, Repo: ${repo}"

mkdir -p docs

# Replace placeholders in template and save to docs/config.yaml
sed "s|<owner>|${owner_lower}|g; s|<repo>|${repo}|g" config/config_template.yaml > docs/config.yaml

echo "Dynamic config.yaml successfully generated."
