$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location -LiteralPath $root

git add -A

$status = git status --porcelain
if ($status) {
  $message = "同步更新 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
  git commit -m $message
}

git push origin main

Write-Host ''
Write-Host '已推送到 GitHub main 分支。'
Write-Host '服务器上执行：'
Write-Host 'cd /home/ubuntu/ruichang-vehicle && bash scripts/server-deploy.sh'
