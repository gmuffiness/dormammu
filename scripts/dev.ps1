# ESE Development — start backend + frontend in one command (Windows)
# Usage: .\scripts\dev.ps1

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Check .env
if (-not (Test-Path "$ProjectDir\.env")) {
    if (Test-Path "$ProjectDir\.env.example") {
        Copy-Item "$ProjectDir\.env.example" "$ProjectDir\.env"
        Write-Host "[ESE] Created .env from .env.example - edit it to add your OPENAI_API_KEY"
    } else {
        Write-Host "[ESE] Warning: No .env file found. LLM features will use fallback mode."
    }
}

Write-Host ""
Write-Host "  ESE - Emergent Simulation Engine"
Write-Host "  Backend:  http://localhost:8000"
Write-Host "  Frontend: http://localhost:5173"
Write-Host ""

# Start backend
$backend = Start-Process -PassThru -NoNewWindow python -ArgumentList "-m", "ese.api.server" -WorkingDirectory $ProjectDir

# Start frontend
$frontend = Start-Process -PassThru -NoNewWindow npm -ArgumentList "run", "dev" -WorkingDirectory "$ProjectDir\frontend"

Write-Host "[ESE] Press Ctrl+C to stop..."

try {
    Wait-Process -Id $backend.Id, $frontend.Id
} finally {
    Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -ErrorAction SilentlyContinue
    Write-Host "[ESE] Stopped."
}
