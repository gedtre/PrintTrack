param([switch]$Demo)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (Test-Path .env) { throw '.env jau yra. Esamas failas neperrasomas. / .env already exists.' }
function New-RandomHex {
    $bytes = New-Object byte[] 24
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}
$dbPassword = New-RandomHex
$adminPassword = New-RandomHex
$demoValue = if ($Demo) { 'true' } else { 'false' }
$project = if ($Demo) { 'printtrack-demo' } else { 'printtrack-local' }
$content = @"
POSTGRES_PASSWORD=$dbPassword
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$adminPassword
DEMO_MODE=$demoValue
COMPOSE_PROJECT_NAME=$project
HOST_BIND=127.0.0.1
APP_PORT=8080
COOKIE_SECURE=false
"@
[IO.File]::WriteAllText((Join-Path $PSScriptRoot '.env'), $content, (New-Object Text.UTF8Encoding($false)))
Write-Host '.env sukurtas tik vietiniam HTTP paleidimui. Slaptazodis: ADMIN_PASSWORD faile .env.'
Write-Host 'Prisijungimas: admin. Paleiskite: docker compose up --build -d'
Write-Host 'Adresas: http://localhost:8080. Si .env saugokite kaip slapta faila.'
