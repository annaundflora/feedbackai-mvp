# FeedbackAI Backend Launcher (PowerShell)
# Startet den FastAPI Server mit Validierung

param(
    [int]$Port = 8000,
    [switch]$NoReload
)

# Farben
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Warning { Write-Host "⚠️  $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "❌ $args" -ForegroundColor Red }
function Write-Info { Write-Host "→ $args" -ForegroundColor Cyan }

# Banner
Write-Host ""
Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Blue
Write-Host "║   FeedbackAI Backend Launcher          ║" -ForegroundColor Blue
Write-Host "║   FastAPI + LangGraph + Supabase       ║" -ForegroundColor Blue
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Blue
Write-Host ""

# Prüfe ob backend/ Verzeichnis existiert
if (-not (Test-Path "backend\app")) {
    Write-Error "Fehler: Muss aus dem Projekt-Root ausgeführt werden!"
    Write-Info "Wechsle ins Projekt-Root-Verzeichnis (wo backend/ Ordner ist)"
    exit 1
}

# Wechsle ins backend Verzeichnis
Set-Location backend
Write-Info "Wechsle in backend/ Verzeichnis"
Write-Host ""

# Prüfe .env
if (-not (Test-Path ".env")) {
    Write-Error ".env Datei nicht gefunden!"
    Write-Warning "Kopiere .env.example nach .env und fülle die Werte aus"
    Write-Host ""
    Write-Host "Erforderliche Variablen:" -ForegroundColor Yellow
    Write-Host "  - OPENROUTER_API_KEY"
    Write-Host "  - SUPABASE_URL"
    Write-Host "  - SUPABASE_KEY"
    exit 1
}

# Lade .env und prüfe kritische Variablen
$envContent = Get-Content .env
$envVars = @{}
foreach ($line in $envContent) {
    if ($line -match "^\s*([^#][^=]+)=(.*)$") {
        $envVars[$matches[1].Trim()] = $matches[2].Trim()
    }
}

$required = @("OPENROUTER_API_KEY", "SUPABASE_URL", "SUPABASE_KEY")
$missing = @()

foreach ($var in $required) {
    if (-not $envVars.ContainsKey($var) -or [string]::IsNullOrWhiteSpace($envVars[$var])) {
        $missing += $var
    }
}

if ($missing.Count -gt 0) {
    Write-Warning "Folgende ENV-Variablen sind nicht gesetzt:"
    foreach ($var in $missing) {
        Write-Host "   - $var"
    }
    Write-Host ""

    $response = Read-Host "Trotzdem starten? (y/n)"
    if ($response -ne "y") {
        exit 1
    }
}

Write-Success ".env Datei gefunden und validiert"

# Prüfe Python/uvicorn
try {
    $null = python -c "import uvicorn" 2>$null
    Write-Success "uvicorn gefunden"
} catch {
    Write-Error "uvicorn nicht installiert!"
    Write-Warning "Führe aus: pip install -r requirements.txt"
    exit 1
}

# Migration Hinweis
Write-Host ""
Write-Warning "📋 Supabase Migration:"
Write-Host "   Stelle sicher, dass die Migration ausgeführt wurde:"
Write-Info "Supabase Dashboard → SQL Editor → backend/migrations/001_create_interviews.sql"
Write-Host ""

# Server starten
Write-Host ""
Write-Host "🚀 Starte Backend Server..." -ForegroundColor Green -BackgroundColor Black
Write-Host ""
Write-Host "Server läuft auf: http://localhost:$Port" -ForegroundColor Cyan
Write-Host "Health Check:     http://localhost:$Port/health" -ForegroundColor Cyan
Write-Host "API Docs:         http://localhost:$Port/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Drücke CTRL+C zum Beenden" -ForegroundColor Yellow
Write-Host "─" * 50
Write-Host ""

$reloadFlag = if ($NoReload) { "" } else { "--reload" }

try {
    python -m uvicorn app.main:app --host 0.0.0.0 --port $Port $reloadFlag
} catch {
    Write-Host ""
    Write-Error "Fehler beim Starten: $_"
    exit 1
} finally {
    Write-Host ""
    Write-Success "Server gestoppt"
}
