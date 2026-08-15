$ErrorActionPreference = 'SilentlyContinue'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $root '.backend.pid'
$stopped = $false

if (Test-Path -LiteralPath $pidFile) {
  $processId = Get-Content -LiteralPath $pidFile
  if ($processId) {
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    $stopped = $true
  }
  Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

if (-not $stopped) {
  Get-Process -Name python -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Path -like 'E:\ruichang-vehicle\backend\.venv\*' -or
      $_.Path -like '*ruichang-vehicle\backend\.venv\*'
    } |
    Stop-Process -Force -ErrorAction SilentlyContinue
  $stopped = $true
}

if ($stopped) {
  Write-Host '后端服务已停止。'
} else {
  Write-Host '没有发现正在运行的后端服务。'
}
