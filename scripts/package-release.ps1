# 生成交付包（银河麒麟 V10 部署包）
#
# 产物：<repo>/../dist-release/truck-bank-deploy-<yyyyMMdd>/
#       <repo>/../dist-release/truck-bank-deploy-<yyyyMMdd>.zip
#
# 排除项：开发期产物（.venv / node_modules / logs / build / 缓存）、
#         .git 与 .runtime（体积）、达梦相关文件（按交付决定不纳入）、
#         本地开发脚本（依赖 .runtime，目标机不存在）。
#
# 用法：pwsh -File scripts/package-release.ps1
#      pwsh -File scripts/package-release.ps1 -SkipZip    # 只生成目录

param(
    [switch]$SkipZip
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$releaseRoot = Join-Path (Split-Path -Parent $projectRoot) 'dist-release'
$stamp = Get-Date -Format 'yyyyMMdd'
$pkgName = "truck-bank-deploy-$stamp"
$stage = Join-Path $releaseRoot $pkgName

Write-Host "==> 项目根: $projectRoot"
Write-Host "==> 输出到: $releaseRoot"

if (Test-Path -LiteralPath $stage) {
    Remove-Item -LiteralPath $stage -Recurse -Force
}
New-Item -ItemType Directory -Path $stage -Force | Out-Null

# robocopy 返回码 0-7 均为成功，8 及以上才是错误
function Invoke-Copy {
    param([string]$Source, [string]$Dest, [string[]]$Xd, [string[]]$Xf)

    if (-not (Test-Path -LiteralPath $Source)) {
        Write-Host "    跳过（不存在）: $Source"
        return
    }
    $args = @($Source, $Dest, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:1', '/W:1')
    if ($Xd -and $Xd.Count -gt 0) { $args += '/XD'; $args += $Xd }
    if ($Xf -and $Xf.Count -gt 0) { $args += '/XF'; $args += $Xf }

    & robocopy @args | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy 失败（退出码 $LASTEXITCODE）: $Source"
    }
    $global:LASTEXITCODE = 0
}

# ---------------------------------------------------------------- 后端源码
Write-Host '==> 复制后端源码'
Invoke-Copy -Source (Join-Path $projectRoot 'ruoyi-fastapi-backend') `
    -Dest (Join-Path $stage 'ruoyi-fastapi-backend') `
    -Xd @('.venv', 'logs', 'build', '__pycache__', '.pytest_cache', '.ruff_cache',
          'vf_admin', 'ruoyi_fastapi_backend_cli.egg-info') `
    -Xf @('backend-dev.pid', '.env.dm',
          'dm_dialect_check.py', 'dm_sync_check.py', 'dm_ddl_apply_check.py')

# ---------------------------------------------------------------- 前端源码
Write-Host '==> 复制前端源码（含已构建的 dist）'
Invoke-Copy -Source (Join-Path $projectRoot 'ruoyi-fastapi-frontend') `
    -Dest (Join-Path $stage 'ruoyi-fastapi-frontend') `
    -Xd @('node_modules', '.npm-cache', '__pycache__') `
    -Xf @('agent_vite.log', 'vite-dev.pid')

# ------------------------------------------------------------ 配置与编排
Write-Host '==> 复制编排文件与配置模板'
$rootFiles = @(
    '部署指南.md', 'README.md', 'CHANGELOG.md', 'LICENSE', '.env.deploy.example',
    'docker-compose.backend-only.yml', 'docker-compose.kylin.yml',
    'docker-compose.my.yml', 'docker-compose.pg.yml'
)
foreach ($f in $rootFiles) {
    $src = Join-Path $projectRoot $f
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination (Join-Path $stage $f) -Force
    } else {
        Write-Host "    缺失（请检查）: $f" -ForegroundColor Yellow
    }
}

# ------------------------------------------------------- 数据库初始化脚本
Write-Host '==> 复制数据库初始化脚本'
Invoke-Copy -Source (Join-Path $projectRoot 'deploy') -Dest (Join-Path $stage 'deploy')

# -------------------------------------------------------------- 交付脚本
Write-Host '==> 复制交付脚本'
New-Item -ItemType Directory -Path (Join-Path $stage 'scripts') -Force | Out-Null
foreach ($f in @('prepare-docker-init.ps1', 'export-offline-bundle.sh')) {
    $src = Join-Path $projectRoot "scripts/$f"
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination (Join-Path $stage "scripts/$f") -Force
    }
}

# ------------------------------------------------------------------ 文档
Write-Host '==> 复制文档'
Invoke-Copy -Source (Join-Path $projectRoot 'docs') -Dest (Join-Path $stage 'docs')

# --------------------------------------------------------------- 校验门禁
Write-Host ''
Write-Host '==> 交付前校验'

$problems = @()

# 1) 初始化脚本必须齐全（13 个）
$initDir = Join-Path $stage 'deploy/mysql-init'
$sqlCount = if (Test-Path $initDir) { (Get-ChildItem $initDir -Filter '*.sql').Count } else { 0 }
Write-Host "    mysql-init 脚本数: $sqlCount (期望 13)"
if ($sqlCount -ne 13) { $problems += "deploy/mysql-init 应为 13 个脚本，实际 $sqlCount" }

# 2) 不应含开发期产物
foreach ($bad in @('.venv', 'node_modules', '.npm-cache', 'logs', '__pycache__', '.runtime', '.git')) {
    $hit = Get-ChildItem -LiteralPath $stage -Recurse -Directory -Filter $bad -ErrorAction SilentlyContinue
    if ($hit) { $problems += "包含不应交付的目录: $bad（$(($hit | Measure-Object).Count) 处）" }
}

# 3) 不应含达梦文件
$dm = Get-ChildItem -LiteralPath $stage -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq '.env.dm' -or $_.Name -like 'dm_*.py' }
if ($dm) { $problems += "包含达梦相关文件: $(($dm | ForEach-Object { $_.Name }) -join ', ')" }

# 4) 前端 dist 的 API 前缀必须是 /docker-api
$distJs = Join-Path $stage 'ruoyi-fastapi-frontend/dist/static'
if (Test-Path $distJs) {
    $prefixes = @{}
    Get-ChildItem $distJs -Recurse -Include '*.js' -File -ErrorAction SilentlyContinue | ForEach-Object {
        $c = [System.IO.File]::ReadAllText($_.FullName)
        foreach ($m in [regex]::Matches($c, '["'']/(?:docker|dev|prod)-api["'']')) {
            $prefixes[$m.Value] = $true
        }
    }
    $found = ($prefixes.Keys | Sort-Object) -join ', '
    Write-Host "    dist API 前缀: $found"
    if ($prefixes.Keys -notcontains '"/docker-api"') {
        $problems += "前端 dist 的 API 前缀不是 /docker-api（实际: $found）"
    }
} else {
    $problems += '前端 dist 不存在（方案 A 需要）'
}

# 5) 关键文件存在性
foreach ($req in @(
    '部署指南.md', '.env.deploy.example', 'docker-compose.backend-only.yml',
    'docker-compose.kylin.yml', 'deploy/nginx/truck-bank.conf',
    'ruoyi-fastapi-backend/Dockerfile.kylin', 'ruoyi-fastapi-backend/requirements.txt'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $stage $req))) {
        $problems += "缺少关键文件: $req"
    }
}

# 6) 体积统计
$sizeMB = [math]::Round(((Get-ChildItem -LiteralPath $stage -Recurse -File |
    Measure-Object -Property Length -Sum).Sum / 1MB), 1)
$fileCount = (Get-ChildItem -LiteralPath $stage -Recurse -File | Measure-Object).Count
Write-Host "    包大小: $sizeMB MB / $fileCount 个文件"

if ($problems.Count -gt 0) {
    Write-Host ''
    Write-Host '!! 校验未通过：' -ForegroundColor Red
    $problems | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    throw '打包校验失败，请修复后重试'
}

Write-Host '    校验通过 ✓' -ForegroundColor Green

# ------------------------------------------------------------------- 压缩
$zipPath = Join-Path $releaseRoot "$pkgName.zip"
if (-not $SkipZip) {
    Write-Host ''
    Write-Host "==> 压缩为 $zipPath"
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zipPath -CompressionLevel Optimal
    $zipMB = [math]::Round(((Get-Item $zipPath).Length / 1MB), 1)
    Write-Host "    zip 大小: $zipMB MB"
}

Write-Host ''
Write-Host '=============================================='
Write-Host " 交付目录: $stage"
if (-not $SkipZip) { Write-Host " 交付压缩包: $zipPath" }
Write-Host '=============================================='
