# Prepare the database init directories for Docker deployment (MySQL and PostgreSQL).
#
# Background: the official MySQL / PostgreSQL images execute every script under
# /docker-entrypoint-initdb.d in alphabetical order. The original compose files mounted
# only the base template, so all business data -- the Songyang brigade and its 6 squads,
# business dictionaries, truck menus, roles, acceptance accounts, warning rules,
# GA/T1400 config and the M13/M14 fixes -- was missing. The result was a deployment
# where login worked but no business menu appeared.
#
# This script copies every script in the correct order into
#   deploy/mysql-init/   (for docker-compose.my.yml)
#   deploy/pg-init/      (for docker-compose.pg.yml)
# with a numeric prefix so the execution order is deterministic.
#
# Usage (from the custom-project directory):
#   pwsh -File scripts/prepare-docker-init.ps1

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$sqlDir = Join-Path $projectRoot 'ruoyi-fastapi-backend/sql'

if (-not (Test-Path -LiteralPath $sqlDir)) {
    throw "SQL directory not found: $sqlDir"
}

# Order: base template -> business init -> m4..m14 increments.
# m6 removes the upstream demo accounts and organization, so it must run after 01/02.
# Note: the base template names are asymmetric (ruoyi-fastapi.sql vs ruoyi-fastapi-pg.sql),
# so the base file name is passed in explicitly.
function Get-InitSequence {
    param([string]$Suffix, [string]$BaseFile)
    $items = @(
        @{ Source = $BaseFile;                        Name = '01-base.sql' }
        @{ Source = "truck-platform-init$Suffix.sql"; Name = '02-truck-init.sql' }
    )
    foreach ($v in 4..14) {
        $items += @{
            Source = "truck-platform-m$v$Suffix.sql"
            Name   = ('03-m{0:d2}.sql' -f $v)
        }
    }
    return $items
}

$targets = @(
    @{ DirName = 'mysql-init'; Suffix = '.mysql'; BaseFile = 'ruoyi-fastapi.sql';    Label = 'MySQL' }
    @{ DirName = 'pg-init';    Suffix = '.pg';    BaseFile = 'ruoyi-fastapi-pg.sql'; Label = 'PostgreSQL' }
)

foreach ($target in $targets) {
    $dir = Join-Path $projectRoot "deploy/$($target.DirName)"
    if (Test-Path -LiteralPath $dir) {
        Remove-Item -LiteralPath $dir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $dir -Force | Out-Null

    $sequence = Get-InitSequence -Suffix $target.Suffix -BaseFile $target.BaseFile
    $copied = 0
    foreach ($item in $sequence) {
        $src = Join-Path $sqlDir $item.Source
        if (-not (Test-Path -LiteralPath $src)) {
            throw "Missing script: $($item.Source)"
        }
        Copy-Item -LiteralPath $src -Destination (Join-Path $dir $item.Name) -Force
        $copied++
    }

    Write-Host "[$($target.Label)] generated $copied init scripts -> deploy/$($target.DirName)/"
    Get-ChildItem -LiteralPath $dir -Filter '*.sql' |
        Sort-Object Name |
        ForEach-Object { Write-Host ("  {0}  ({1:N0} bytes)" -f $_.Name, $_.Length) }
}
Write-Host ''
Write-Host 'NOTE: the database image runs these scripts only when the data volume is empty.'
Write-Host 'To re-initialize MySQL: docker compose -f docker-compose.my.yml down -v'
Write-Host 'To re-initialize PG   : docker compose -f docker-compose.pg.yml down -v'
