param([ValidateSet("frontend","backend")][string]$Service = "frontend")
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
if ($Service -eq "backend") {
    & .venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8100 --reload
} else {
    & npm.cmd --prefix frontend run dev -- --port 3100
}

