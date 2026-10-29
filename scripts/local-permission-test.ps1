$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$mysql = Join-Path $projectRoot '.runtime\mysql\mysql-8.0.42-winx64\bin\mysql.exe'
$redisCli = Join-Path $projectRoot '.runtime\redis\Redis-8.0.2-Windows-x64-msys2\redis-cli.exe'
$mysqlArgs = @(
    '--host=127.0.0.1', '--port=3306', '--user=root', '--password=mysqlroot',
    '--database=truck_bank', '--default-character-set=utf8mb4'
)
$captchaKey = 'sys_config:sys.account.captchaEnabled'
$originalCaptchaValue = & $redisCli -p 6379 -n 2 GET $captchaKey

function Invoke-Login([string]$UserName) {
    $response = Invoke-RestMethod `
        -Uri 'http://127.0.0.1:9099/login' `
        -Method Post `
        -Body @{ username = $UserName; password = 'admin123' }
    if ($response.code -ne 200 -or -not $response.token) {
        throw "Login failed for $UserName`: $($response.msg)"
    }
    return $response.token
}

function Get-Headers([string]$Token) {
    return @{ Authorization = "Bearer $Token" }
}

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) {
        throw $Message
    }
}

try {
    & $redisCli -p 6379 -n 2 SET $captchaKey false | Out-Null
    & $mysql @mysqlArgs --execute="DELETE FROM truck_vehicle WHERE remark='M5_PERMISSION_TEST'; INSERT INTO truck_vehicle (plate_no,plate_color,dept_id,vehicle_status,del_flag,create_by,remark) VALUES ('M5PERM-XP','yellow',9101,'normal','0','codex','M5_PERMISSION_TEST'),('M5PERM-GS','yellow',9102,'normal','0','codex','M5_PERMISSION_TEST');"

    $adminHeaders = Get-Headers (Invoke-Login 'admin')
    $squadHeaders = Get-Headers (Invoke-Login 'xiping_admin')
    $leaderHeaders = Get-Headers (Invoke-Login 'truck_leader')

    $adminRows = @((Invoke-RestMethod -Uri 'http://127.0.0.1:9099/truck/vehicle/list?pageNum=1&pageSize=10&plateNo=M5PERM' -Headers $adminHeaders).rows)
    $squadRows = @((Invoke-RestMethod -Uri 'http://127.0.0.1:9099/truck/vehicle/list?pageNum=1&pageSize=10&plateNo=M5PERM' -Headers $squadHeaders).rows)
    $leaderRows = @((Invoke-RestMethod -Uri 'http://127.0.0.1:9099/truck/vehicle/list?pageNum=1&pageSize=10&plateNo=M5PERM' -Headers $leaderHeaders).rows)

    Write-Output "Vehicle visibility: admin=$($adminRows.plateNo -join ','), squad=$($squadRows.plateNo -join ','), leader=$($leaderRows.plateNo -join ',')"

    Assert-True ($adminRows.Count -eq 2) 'Admin should see both permission test vehicles.'
    Assert-True ($squadRows.Count -eq 1 -and $squadRows[0].plateNo -eq 'M5PERM-XP') 'Squad admin data scope is incorrect.'
    Assert-True ($leaderRows.Count -eq 2) 'Leader should have full read data scope.'

    $squadRecalculate = Invoke-RestMethod -Uri 'http://127.0.0.1:9099/truck/warning/recalculate' -Method Post -Headers $squadHeaders
    Assert-True ($squadRecalculate.code -eq 200 -and $squadRecalculate.data.count -ge 1) 'Squad warning recalculation should process its test vehicle.'

    $warningState = @(& $mysql @mysqlArgs --batch --skip-column-names --execute="SELECT plate_no,COALESCE(warning_level,'NULL') FROM truck_vehicle WHERE remark='M5_PERMISSION_TEST' ORDER BY plate_no;")
    Assert-True ($warningState[0] -match '^M5PERM-GS\s+NULL$') 'Squad recalculation changed another squad vehicle.'
    Assert-True ($warningState[1] -match '^M5PERM-XP\s+level_one$') 'Squad vehicle warning was not recalculated.'

    $leaderRecalculate = Invoke-RestMethod -Uri 'http://127.0.0.1:9099/truck/warning/recalculate' -Method Post -Headers $leaderHeaders
    Assert-True ($leaderRecalculate.code -eq 403) 'Leader should not have warning recalculation permission.'

    Write-Output 'Permission regression passed: admin=2, squad=1, leader=2; write permissions are correct.'
}
finally {
    & $mysql @mysqlArgs --execute="DELETE FROM truck_vehicle WHERE remark='M5_PERMISSION_TEST';"
    if ($null -eq $originalCaptchaValue -or $originalCaptchaValue -eq '') {
        & $redisCli -p 6379 -n 2 DEL $captchaKey | Out-Null
    }
    else {
        & $redisCli -p 6379 -n 2 SET $captchaKey $originalCaptchaValue | Out-Null
    }
}
