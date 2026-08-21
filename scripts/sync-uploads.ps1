param(
  [string]$Server = 'ubuntu@ruichang.site',
  [string]$RemoteDir = '/home/ubuntu/ruichang-vehicle/backend/uploads'
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$localUploads = Join-Path $root 'backend\uploads'

if (-not (Test-Path -LiteralPath $localUploads)) {
  throw "未找到本地图片目录：$localUploads"
}

ssh $Server "mkdir -p $RemoteDir"

$files = Get-ChildItem -LiteralPath $localUploads -File
if (-not $files) {
  Write-Host '本地没有需要同步的图片。'
  exit 0
}

$count = 0
foreach ($file in $files) {
  scp -q $file.FullName "${Server}:$RemoteDir/"
  $count += 1
}

Write-Host "已同步 $count 个图片文件到 $Server : $RemoteDir"
