param(
  [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logsDir = Join-Path $root 'logs'
$tunnelPidFile = Join-Path $root '.tunnel.pid'
$publicUrlFile = Join-Path $root 'public-url.txt'
$sshPath = 'C:\Windows\System32\OpenSSH\ssh.exe'

if (-not (Test-Path -LiteralPath $logsDir)) {
  New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

function Test-Health {
  try {
    $response = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
    return $response.status -eq 'ok'
  } catch {
    return $false
  }
}

if (-not (Test-Health)) {
  Write-Host '正在启动后端服务...'
  & (Join-Path $root 'start.ps1') -Lan -NoBrowser
  if ($LASTEXITCODE -ne 0) {
    throw '后端启动失败，请先运行 start.bat 查看错误。'
  }
}

if (Test-Path -LiteralPath $tunnelPidFile) {
  $oldPid = Get-Content -LiteralPath $tunnelPidFile
  Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
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

$outLog = Join-Path $logsDir 'public-tunnel.log'
$errLog = Join-Path $logsDir 'public-tunnel-error.log'
$tunnelArgs = @(
  '-o', 'StrictHostKeyChecking=no',
  '-o', 'ServerAliveInterval=60',
  '-o', 'ExitOnForwardFailure=yes',
  '-R', '80:127.0.0.1:8000',
  'nokey@localhost.run'
)

$tunnelProcess = Start-Process -FilePath $sshPath -ArgumentList $tunnelArgs -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
Set-Content -LiteralPath $tunnelPidFile -Value $tunnelProcess.Id -Encoding ascii

$publicUrl = $null
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Milliseconds 750
  if (Test-Path -LiteralPath $outLog) {
    $logText = Get-Content -LiteralPath $outLog -Raw -ErrorAction SilentlyContinue
    if ($logText -match 'https://[a-z0-9]+\.lhr\.life') {
      $publicUrl = $matches[0]
      break
    }
  }
  if ($tunnelProcess.HasExited) {
    break
  }
}

if (-not $publicUrl) {
  Write-Host '公网隧道启动失败，最近日志：'
  if (Test-Path -LiteralPath $errLog) {
    Get-Content -LiteralPath $errLog -Tail 20
  }
  throw '公网隧道启动超时。'
}

Set-Content -LiteralPath $publicUrlFile -Value $publicUrl -Encoding ascii

Write-Host ''
Write-Host "公网地址：$publicUrl"
Write-Host "手机访问：$publicUrl/mobile"
Write-Host '该地址为临时地址，电脑重启或隧道断开后会变化。'
Write-Host '停止公网访问请运行 stop-public.bat。'

if (-not $NoBrowser) {
  Start-Process $publicUrl
}
