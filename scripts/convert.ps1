# Create output directories
New-Item -ItemType Directory -Force -Path docs | Out-Null
New-Item -ItemType Directory -Force -Path sub_tmp | Out-Null

Write-Host "Reading source URLs..."
$sourceFile = "config/source.txt"
$urls = Get-Content $sourceFile | Where-Object { $_ -notmatch '^#' -and $_.Trim() -ne '' }

if ($urls.Count -eq 0) {
    Write-Error "No valid URLs found in config/source.txt"
    exit 1
}

Write-Host "Downloading and merging subscriptions..."
Remove-Item -Force -ErrorAction SilentlyContinue sub_tmp/merged.txt, sub_tmp/merged_final.txt

foreach ($u in $urls) {
    Write-Host "Fetching: $u"
    $content = Invoke-RestMethod -Uri $u
    Add-Content -Path sub_tmp/merged.txt -Value $content
}

# Check if merged.txt contains plaintext URIs like vless:// or trojan://
$mergedContent = Get-Content sub_tmp/merged.txt -Raw
if ($mergedContent -match "://") {
    Write-Host "Plaintext URIs detected! Base64 encoding for Subconverter compatibility..."
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($mergedContent)
    $base64 = [Convert]::ToBase64String($bytes)
    [IO.File]::WriteAllText("sub_tmp/merged_final.txt", $base64)
} else {
    Write-Host "No plaintext URIs detected, assuming it's already encoded or a standard config."
    Copy-Item sub_tmp/merged.txt sub_tmp/merged_final.txt
}

Write-Host "Starting local HTTP server to serve the merged subscription..."
# Start a simple Python HTTP server in background
$httpProcess = Start-Process python -ArgumentList "-m http.server 8080" -WorkingDirectory "sub_tmp" -NoNewWindow -PassThru

# Give it a second to start
Start-Sleep -Seconds 2

Write-Host "Starting Dockerized Subconverter..."
# Stop and remove existing container
docker rm -f subconverter 2>$null
# Start metacubex/subconverter with port mapping 25500:25500
docker run -d --name subconverter -p 25500:25500 -v "${PWD}/config:/base/config" metacubex/subconverter:latest

# Wait for subconverter to start
Start-Sleep -Seconds 3

# Point to host.docker.internal since container needs to access host python server
$localUrl = "http://host.docker.internal:8080/merged_final.txt"
$encodedUrl = [uri]::EscapeDataString($localUrl)

Write-Host "Generating pure proxies list (Proxy Provider mode)..."
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:25500/sub?target=clash&list=true&url=$encodedUrl" -UseBasicParsing
    [IO.File]::WriteAllText("docs/proxies.yaml", $resp.Content)
    Write-Host "docs/proxies.yaml generated."
} catch {
    Write-Error "Failed to fetch proxies.yaml from subconverter: $_"
    $httpProcess | Stop-Process -Force
    docker rm -f subconverter 2>$null
    exit 1
}

Write-Host "Generating monolithic configuration..."
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:25500/sub?target=clash&config=config/flclash.ini&url=$encodedUrl" -UseBasicParsing
    [IO.File]::WriteAllText("docs/config_monolithic.yaml", $resp.Content)
    Write-Host "docs/config_monolithic.yaml generated."
} catch {
    Write-Error "Failed to fetch config_monolithic.yaml from subconverter: $_"
    $httpProcess | Stop-Process -Force
    docker rm -f subconverter 2>$null
    exit 1
}

# Download GeoIP Country database
$geoipDb = "config/GeoLite2-Country.mmdb"
if (-not (Test-Path $geoipDb)) {
    Write-Host "Downloading GeoIP Country database..."
    Invoke-WebRequest -Uri "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb" -OutFile $geoipDb
}

Write-Host "Fixing Subconverter YAML IPv6 unquoted formatting bug and purifying nodes..."
python scripts/purify.py docs/proxies.yaml $geoipDb
python scripts/purify.py docs/config_monolithic.yaml $geoipDb

Write-Host "Cleaning up..."
$httpProcess | Stop-Process -Force
docker rm -f subconverter 2>$null
Remove-Item -Recurse -Force sub_tmp 2>$null

Write-Host "Conversion completed successfully!"
