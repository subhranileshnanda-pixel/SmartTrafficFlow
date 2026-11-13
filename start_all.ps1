# Starts the backend, simulation and dashboard, each in its own window.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $root "venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "Virtual environment not found at $py" -ForegroundColor Red
    exit 1
}

Write-Host "1/3 Starting backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='SmartFlow Backend'; cd '$root\backend'; & '$py' -m uvicorn main:app --port 8000"

# Wait until the backend answers (up to 30 seconds)
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 1 | Out-Null
        $ready = $true
        break
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $ready) {
    Write-Host "Backend did not start. Check the Backend window for errors." -ForegroundColor Red
    exit 1
}
Write-Host "    Backend is up." -ForegroundColor Green

Write-Host "2/3 Starting simulation..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='SmartFlow Simulation'; cd '$root'; & '$py' simulation\main.py"

Write-Host "3/3 Starting dashboard..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='SmartFlow Dashboard'; cd '$root\frontend'; npm run dev"

Start-Sleep -Seconds 5
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "SmartFlow is running." -ForegroundColor Green
Write-Host "  Dashboard : http://localhost:5173"
Write-Host "  API docs  : http://127.0.0.1:8000/docs"
Write-Host "  Health    : http://127.0.0.1:8000/api/health"