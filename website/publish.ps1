# Publish this folder to the live SecureNet website:
#   https://samiksha99004.github.io/securenet-site/
# (public repository samiksha99004/securenet-site, GitHub Pages from its main branch).
# The SecureNet project repository itself is private, and GitHub's free plan only serves
# Pages from public repositories — so only these website files are published there.
#
# Usage (from the project folder):  powershell -ExecutionPolicy Bypass -File website\publish.ps1 ["What changed"]
# Needs git with access to the samiksha99004 GitHub account (the same login used to push SecureNet).

param([string]$Message = 'Update SecureNet website')
$ErrorActionPreference = 'Stop'

$site = $PSScriptRoot
$repo = 'https://github.com/samiksha99004/securenet-site.git'
$work = Join-Path (Split-Path -Parent $site) '.local\site-publish'   # .local is ignored by git

if (Test-Path $work) { Remove-Item -Recurse -Force $work }
New-Item -ItemType Directory -Force (Split-Path -Parent $work) | Out-Null

$ErrorActionPreference = 'Continue'   # git reports progress on stderr
git clone --quiet --depth 1 $repo $work
if ($LASTEXITCODE -ne 0) { Write-Host 'Could not download the website repository.' -ForegroundColor Red; exit 1 }
$ErrorActionPreference = 'Stop'

# replace everything except git's own folder with the current website files
Get-ChildItem $work -Force | Where-Object { $_.Name -ne '.git' } | Remove-Item -Recurse -Force
Get-ChildItem $site -Force | Where-Object { $_.Name -ne 'publish.ps1' } | Copy-Item -Destination $work -Recurse -Force
New-Item (Join-Path $work '.nojekyll') -ItemType File -Force | Out-Null   # serve the files exactly as they are

$ErrorActionPreference = 'Continue'
git -C $work add -A
if (-not (git -C $work status --porcelain)) {
    Write-Host 'The live website is already up to date.' -ForegroundColor Green
    exit 0
}
git -C $work -c user.name='samiksha99004' -c user.email='samiksha99004@users.noreply.github.com' commit --quiet -m $Message
git -C $work push --quiet origin HEAD:main
if ($LASTEXITCODE -ne 0) { Write-Host 'Publishing failed (see the message above).' -ForegroundColor Red; exit 1 }
Write-Host 'Published. The live website updates within a minute: https://samiksha99004.github.io/securenet-site/' -ForegroundColor Green
