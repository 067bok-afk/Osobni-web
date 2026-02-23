# AI Avatar - Spuštění serveru
# Spusťte z této složky: .\run.ps1

Set-Location $PSScriptRoot

if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "Chyba: venv nenalezen. Spusťte: python -m venv venv" -ForegroundColor Red
    exit 1
}

& .\venv\Scripts\Activate.ps1
Write-Host "Server startuje na http://127.0.0.1:8001" -ForegroundColor Green
uvicorn main:app --reload --host 127.0.0.1 --port 8001
