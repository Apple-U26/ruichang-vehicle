$ErrorActionPreference = 'SilentlyContinue'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$tunnelPidFile = Join-Path $root '.tunnel.pid'

if (Test-Path -LiteralPath $tunnelPidFile) {
  $pidValue = Get-Content -LiteralPath $tunnelPidFile
  if ($pidValue) {
    Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
  }
  Remove-Item -LiteralPath $tunnelPidFile -Force -ErrorAction SilentlyContinue
}

Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" -ErrorAction SilentlyContinue |
  Where-Object {
    $_.CommandLine -like '*localhost.run*' -or
    $_.CommandLine -like '*serveo.net*'
  } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }

Write-Host '公网隧道已停止。'
