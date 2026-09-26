# Publish this folder to the SecureNet website on Cloudflare Pages:
#   https://securenet-ids.pages.dev/      (no personal name in the address)
#
# One-time: put your Cloudflare details in  <project>\.local\cloudflare.env  (that folder is never committed):
#   CLOUDFLARE_API_TOKEN=...   (My Profile > API Tokens > Create Token > "Cloudflare Pages: Edit")
#   CLOUDFLARE_ACCOUNT_ID=...  (Workers & Pages page, right-hand side "Account ID")
#
# Usage (from the project folder):  powershell -ExecutionPolicy Bypass -File website\publish-cloudflare.ps1
# Uses Cloudflare's own "wrangler" tool through npx (downloaded into the npm cache on first use).

param([string]$Project = 'securenet-ids')
$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts\securenet-env.ps1')

$envFile = Join-Path $RepoRoot '.local\cloudflare.env'
if (-not (Test-Path $envFile)) {
    Write-Host "Missing $envFile - create it with CLOUDFLARE_API_TOKEN=... and CLOUDFLARE_ACCOUNT_ID=... (see the top of this script)." -ForegroundColor Red
    exit 1
}
foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*(CLOUDFLARE_API_TOKEN|CLOUDFLARE_ACCOUNT_ID)\s*=\s*(\S+)\s*$') {
        Set-Item "env:$($Matches[1])" $Matches[2]
    }
}
if (-not $env:CLOUDFLARE_API_TOKEN -or -not $env:CLOUDFLARE_ACCOUNT_ID -or $env:CLOUDFLARE_API_TOKEN -like 'paste*') {
    Write-Host "Fill in CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in $envFile first." -ForegroundColor Red
    exit 1
}

$nodeDir = Find-SecureNetNode
if (-not $nodeDir) { Write-Host 'Node.js was not found - run SETUP.bat first.' -ForegroundColor Red; exit 1 }
Use-SecureNetCaches
$env:Path = "$nodeDir;$env:Path"
$env:WRANGLER_SEND_METRICS = 'false'

# upload only the website files (not the publish scripts)
$out = Join-Path $RepoRoot '.local\site-cloudflare'
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force $out | Out-Null
Get-ChildItem $PSScriptRoot -Force | Where-Object { $_.Name -notlike 'publish*' -and $_.Name -ne 'README.md' } | Copy-Item -Destination $out -Recurse -Force

$ErrorActionPreference = 'Continue'   # wrangler writes progress on stderr
# create the Pages project the first time (an "already exists" message afterwards is fine)
& npx --yes wrangler@4 pages project create $Project --production-branch main 2>&1 | Out-Host
& npx --yes wrangler@4 pages deploy $out --project-name $Project --branch main --commit-dirty=true 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Write-Host 'Publishing failed (see the messages above).' -ForegroundColor Red; exit 1 }
Write-Host "Published: https://$Project.pages.dev/" -ForegroundColor Green
