$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot '.runtime'
$backendRoot = Join-Path $projectRoot 'ruoyi-fastapi-backend'
$frontendRoot = Join-Path $projectRoot 'ruoyi-fastapi-frontend'

function Test-TcpPort([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync('127.0.0.1', $Port)
        return $task.Wait(1000) -and $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Start-HiddenProcess([string]$FilePath, [string]$Arguments, [string]$WorkingDirectory) {
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $Arguments
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $true
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    return [System.Diagnostics.Process]::Start($startInfo)
}

if (-not (Test-Path -LiteralPath 'R:\.runtime')) {
    & subst.exe R: $projectRoot
}

$mysqlHome = 'R:\.runtime\mysql\mysql-8.0.42-winx64'
$redisHome = Join-Path $runtimeRoot 'redis\Redis-8.0.2-Windows-x64-msys2'
$python = Join-Path $backendRoot '.venv\Scripts\python.exe'

foreach ($requiredPath in @(
    (Join-Path $mysqlHome 'bin\mysqld.exe'),
    (Join-Path $redisHome 'redis-server.exe'),
    $python,
    (Join-Path $frontendRoot 'node_modules')
)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Local dependency is missing: $requiredPath"
    }
}

if (-not (Test-TcpPort 3306)) {
    $mysql = Start-HiddenProcess `
        (Join-Path $mysqlHome 'bin\mysqld.exe') `
        '--defaults-file=R:\.runtime\mysql\my.ini' `
        $mysqlHome
    $mysql.Id | Set-Content -LiteralPath (Join-Path $runtimeRoot 'mysql.pid')
}

if (-not (Test-TcpPort 6379)) {
    $redis = Start-HiddenProcess `
        (Join-Path $redisHome 'redis-server.exe') `
        '--port 6379 --appendonly no' `
        $redisHome
    $redis.Id | Set-Content -LiteralPath (Join-Path $runtimeRoot 'redis.pid')
}

if (-not (Test-TcpPort 9099)) {
    $backend = Start-HiddenProcess `
        $python `
        '-m uvicorn server:create_app --factory --host 0.0.0.0 --port 9099 --root-path /dev-api' `
        $backendRoot
    $backend.Id | Set-Content -LiteralPath (Join-Path $runtimeRoot 'backend.pid')
}

if (-not (Test-TcpPort 5173)) {
    $frontend = Start-HiddenProcess `
        $env:ComSpec `
        '/c npm.cmd run dev -- --host 127.0.0.1 --port 5173 --open false' `
        $frontendRoot
    $frontend.Id | Set-Content -LiteralPath (Join-Path $runtimeRoot 'frontend.pid')
}

$deadline = [DateTime]::UtcNow.AddSeconds(30)
do {
    $ready = (Test-TcpPort 3306) -and (Test-TcpPort 6379) -and
        (Test-TcpPort 9099) -and (Test-TcpPort 5173)
    if (-not $ready) {
        Start-Sleep -Milliseconds 500
    }
} while (-not $ready -and [DateTime]::UtcNow -lt $deadline)

if (-not $ready) {
    throw 'Local development services did not become ready within 30 seconds.'
}

Write-Host 'Local development environment is ready:'
Write-Host '  Frontend: http://127.0.0.1:5173/'
Write-Host '  Backend:  http://127.0.0.1:9099/'
Write-Host '  MySQL:    127.0.0.1:3306'
Write-Host '  Redis:    127.0.0.1:6379'
