$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Test-Path ".env")) {
    Write-Host "Chua tim thay file .env." -ForegroundColor Yellow
    Write-Host "Hay chay: Copy-Item .env.example .env" -ForegroundColor Yellow
    Write-Host "Sau do dien EXTERNAL_API_KEY that vao file .env." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path ".venv")) {
    Write-Host "Dang tao Python virtual environment..."
    python -m venv .venv
}

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Khong tim thay Python trong .venv."
}

Write-Host "Dang cai dat/cap nhat dependencies..."
& $python -m pip install -r requirements.txt

Write-Host "Khoi dong Local AI API Service..."
& $python -m uvicorn app.main:app `
    --host 127.0.0.1 `
    --port 8010 `
    --reload
