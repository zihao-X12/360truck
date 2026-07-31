$ErrorActionPreference = 'SilentlyContinue'

$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot '.runtime'
$mysqlAdmin = 'R:\.runtime\mysql\mysql-8.0.42-winx64\bin\mysqladmin.exe'
$redisCli = Join-Path $runtimeRoot 'redis\Redis-8.0.2-Windows-x64-msys2\redis-cli.exe'

if (-not (Test-Path -LiteralPath 'R:\.runtime')) {
    & subst.exe R: $projectRoot
}

function Stop-PortProcess([int]$Port) {
    $pattern = ":$Port\s+.*LISTENING\s+(\d+)$"
    foreach ($line in & netstat.exe -ano -p TCP) {
        if ($line -match $pattern) {
            Stop-Process -Id ([int]$Matches[1]) -Force
        }
    }
}

Stop-PortProcess 5173
Stop-PortProcess 9099

foreach ($service in @('frontend', 'backend')) {
    $pidFile = Join-Path $runtimeRoot "$service.pid"
    if (Test-Path -LiteralPath $pidFile) {
        $servicePid = Get-Content -LiteralPath $pidFile
        Stop-Process -Id $servicePid -Force
        Remove-Item -LiteralPath $pidFile -Force
    }
}

if (Test-Path -LiteralPath $redisCli) {
    & $redisCli -p 6379 shutdown nosave | Out-Null
}

if (Test-Path -LiteralPath $mysqlAdmin) {
    & $mysqlAdmin -h 127.0.0.1 -P 3306 -u root -pmysqlroot shutdown | Out-Null
}

Write-Host 'Local development services stopped.'
