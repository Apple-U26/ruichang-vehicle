param(
  [switch]$NoBrowser,
  [switch]$Lan
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'
$logsDir = Join-Path $root 'logs'
$venvDir = Join-Path $backendDir '.venv'
$venvPy = Join-Path $venvDir 'Scripts\python.exe'
$pidFile = Join-Path $root '.backend.pid'
$hostAddress = if ($Lan) { '0.0.0.0' } else { '127.0.0.1' }

if (-not (Test-Path -LiteralPath $logsDir)) {
  New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

function Select-BasePython {
  $candidates = @(
    @{ Command = 'py'; VersionArgs = @('-3.12') },
    @{ Command = 'py'; VersionArgs = @('-3.13') },
    @{ Command = 'py'; VersionArgs = @('-3.14') },
    @{ Command = 'python'; VersionArgs = @() }
  )

  foreach ($candidate in $candidates) {
    $testArgs = @($candidate.VersionArgs) + @('-c', 'import sys')
    try {
      & $candidate.Command @testArgs 2>$null | Out-Null
      if ($LASTEXITCODE -eq 0) {
        return $candidate
      }
    } catch {
      # try next candidate
    }
  }

  throw '未找到可用的 Python。请安装 Python 3.12 或 3.13 后重试。'
}

function Test-Venv {
  if (-not (Test-Path -LiteralPath $venvPy)) {
    return $false
  }
  try {
    & $venvPy -c 'import sys' 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

function Test-Dependencies {
  try {
    & $venvPy -c 'import fastapi, sqlalchemy, openpyxl, pydantic, pymysql, jwt' 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

if (-not (Test-Venv)) {
  Write-Host '正在创建 Python 虚拟环境...'
  $basePython = Select-BasePython

  if (Test-Path -LiteralPath $venvDir) {
    $oldVenv = Join-Path $backendDir ('.venv-broken-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    Move-Item -LiteralPath $venvDir -Destination $oldVenv
  }

  $versionArgs = $basePython.VersionArgs
  & $basePython.Command @versionArgs -m venv $venvDir
  if ($LASTEXITCODE -ne 0) {
    throw '创建 Python 虚拟环境失败。'
  }
}

if (-not (Test-Dependencies)) {
  Write-Host '正在安装后端依赖，请稍候...'
  & $venvPy -m pip install -r (Join-Path $backendDir 'requirements.txt') --disable-pip-version-check
  if ($LASTEXITCODE -ne 0) {
    throw '后端依赖安装失败，请检查网络后重试。'
  }
}

Write-Host '正在初始化数据库...'
Push-Location -LiteralPath $backendDir
try {
  & $venvPy -m app.seed
  if ($LASTEXITCODE -ne 0) {
    throw '数据库初始化失败。'
  }
} finally {
  Pop-Location
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendDir 'node_modules'))) {
  Write-Host '正在安装前端依赖，请稍候...'
  Push-Location -LiteralPath $frontendDir
  try {
    & npm install
    if ($LASTEXITCODE -ne 0) {
      throw '前端依赖安装失败。'
    }
  } finally {
    Pop-Location
  }
}

Write-Host '正在构建前端页面...'
Push-Location -LiteralPath $frontendDir
try {
  & npm run build
  if ($LASTEXITCODE -ne 0) {
    throw '前端构建失败。'
  }
} finally {
  Pop-Location
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
  $outLog = Join-Path $logsDir 'backend-out.log'
  $errLog = Join-Path $logsDir 'backend-error.log'
  $uvicornArgs = @('-m', 'uvicorn', 'app.main:app', '--host', $hostAddress, '--port', '8000')
  $process = Start-Process -FilePath $venvPy -ArgumentList $uvicornArgs -WorkingDirectory $backendDir -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
  Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii

  $deadline = (Get-Date).AddSeconds(60)
  $ready = $false
  while ((Get-Date) -lt $deadline) {
    if (Test-Health) {
      $ready = $true
      break
    }
    if ($process.HasExited) {
      break
    }
    Start-Sleep -Milliseconds 800
  }

  if (-not $ready) {
    Write-Host '后端启动失败，最近错误日志：'
    if (Test-Path -LiteralPath $errLog) {
      Get-Content -LiteralPath $errLog -Tail 30
    }
    throw '后端启动超时。'
  }
}

if (-not $NoBrowser) {
  Start-Process 'http://127.0.0.1:8000'
}

Write-Host ''
Write-Host '系统已启动：http://127.0.0.1:8000'
Write-Host '管理员：admin / Admin@123456'
Write-Host '演示账号：vehicle_manager / project_manager / finance / driver，密码同为 Admin@123456'
if ($Lan) {
  $lanOutput = ipconfig | Out-String
  $lanMatches = [regex]::Matches($lanOutput, 'IPv4[^\d]*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)')
  $lanIp = $null
  foreach ($match in $lanMatches) {
    $ip = $match.Groups[1].Value
    if ($ip -notlike '169.254.*') {
      $lanIp = $ip
      break
    }
  }
  if ($lanIp) {
    Write-Host "手机访问地址：http://${lanIp}:8000（需与电脑在同一网络）"
  } else {
    Write-Host '手机访问地址：http://<电脑局域网IP>:8000（需与电脑在同一网络）'
  }
}
Write-Host '如需停止服务，请运行 stop.bat。'
