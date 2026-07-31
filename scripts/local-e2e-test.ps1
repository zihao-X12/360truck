$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$testRoot = Join-Path $projectRoot 'ruoyi-fastapi-test'
$redisCli = Join-Path $projectRoot '.runtime\redis\Redis-8.0.2-Windows-x64-msys2\redis-cli.exe'
$testPython = Join-Path $testRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $redisCli)) {
    throw "Redis client is missing: $redisCli"
}
if (-not (Test-Path -LiteralPath $testPython)) {
    throw 'E2E virtual environment is missing. Create ruoyi-fastapi-test\.venv and install requirements first.'
}

$captchaKey = 'sys_config:sys.account.captchaEnabled'
$originalCaptchaValue = & $redisCli -p 6379 -n 2 GET $captchaKey

try {
    & $redisCli -p 6379 -n 2 SET $captchaKey false | Out-Null
    $env:TEST_FRONTEND_URL = 'http://127.0.0.1:5173'
    $env:TEST_BACKEND_URL = 'http://127.0.0.1:9099'
    $env:PYTHONPATH = $testRoot
    & $testPython -m pytest (Join-Path $testRoot 'truck') -v -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        throw "Truck E2E tests failed with exit code $LASTEXITCODE"
    }
}
finally {
    if ($null -eq $originalCaptchaValue -or $originalCaptchaValue -eq '') {
        & $redisCli -p 6379 -n 2 DEL $captchaKey | Out-Null
    }
    else {
        & $redisCli -p 6379 -n 2 SET $captchaKey $originalCaptchaValue | Out-Null
    }
}
