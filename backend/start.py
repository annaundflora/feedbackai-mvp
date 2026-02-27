#!/usr/bin/env python3
"""
FeedbackAI Backend Launcher
Startet den FastAPI Server mit Validierung
"""
import os
import sys
import subprocess
from pathlib import Path

# ANSI Color Codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_banner():
    """Zeigt Banner an"""
    print(f"{BLUE}{BOLD}")
    print("╔════════════════════════════════════════╗")
    print("║   FeedbackAI Backend Launcher          ║")
    print("║   FastAPI + LangGraph + PostgreSQL      ║")
    print("╚════════════════════════════════════════╝")
    print(f"{RESET}\n")


def check_env_file():
    """Prüft ob .env existiert und kritische Variablen gesetzt sind"""
    env_path = Path(".env")

    if not env_path.exists():
        print(f"{RED}❌ Fehler: .env Datei nicht gefunden!{RESET}")
        print(f"{YELLOW}→ Kopiere .env.example nach .env und fülle die Werte aus{RESET}\n")
        print("  Erforderliche Variablen:")
        print("  - OPENROUTER_API_KEY")
        print("  - DATABASE_URL")
        return False

    # Lade .env
    env_vars = {}
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    # Prüfe kritische Variablen
    required = ["OPENROUTER_API_KEY", "DATABASE_URL"]
    missing = []

    for var in required:
        if var not in env_vars or not env_vars[var]:
            missing.append(var)

    if missing:
        print(f"{YELLOW}⚠️  Warnung: Folgende ENV-Variablen sind nicht gesetzt:{RESET}")
        for var in missing:
            print(f"   - {var}")
        print()

        response = input(f"{BOLD}Trotzdem starten? (y/n): {RESET}").lower()
        if response != "y":
            return False

    print(f"{GREEN}✅ .env Datei gefunden und validiert{RESET}")
    return True


def check_dependencies():
    """Prüft ob uvicorn installiert ist"""
    try:
        import uvicorn  # noqa: F401
        print(f"{GREEN}✅ uvicorn gefunden{RESET}")
        return True
    except ImportError:
        print(f"{RED}❌ uvicorn nicht installiert!{RESET}")
        print(f"{YELLOW}→ Führe aus: pip install -r requirements.txt{RESET}\n")
        return False


def show_migration_hint():
    """Zeigt Hinweis zur PostgreSQL Migration"""
    print(f"\n{YELLOW}📋 PostgreSQL Setup:{RESET}")
    print("   Stelle sicher, dass PostgreSQL läuft:")
    print(f"   {BLUE}→ docker-compose up -d{RESET}")
    print(f"   Schema wird automatisch beim ersten Start angelegt.")
    print()


def start_server(port=8000, reload=True):
    """Startet den FastAPI Server"""
    print(f"\n{GREEN}{BOLD}🚀 Starte Backend Server...{RESET}\n")
    print(f"{BLUE}Server läuft auf: http://localhost:{port}{RESET}")
    print(f"{BLUE}Health Check:     http://localhost:{port}/health{RESET}")
    print(f"{BLUE}API Docs:         http://localhost:{port}/docs{RESET}")
    print(f"\n{YELLOW}Drücke CTRL+C zum Beenden{RESET}\n")
    print("─" * 50)

    try:
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(port),
        ]

        if reload:
            cmd.append("--reload")

        subprocess.run(cmd)
    except KeyboardInterrupt:
        print(f"\n\n{GREEN}✅ Server gestoppt{RESET}")
    except Exception as e:
        print(f"\n{RED}❌ Fehler beim Starten: {e}{RESET}")
        sys.exit(1)


def main():
    """Hauptfunktion"""
    print_banner()

    # Wechsle ins backend Verzeichnis falls nötig
    if Path("backend").exists() and not Path("app").exists():
        os.chdir("backend")
        print(f"{BLUE}→ Wechsle in backend/ Verzeichnis{RESET}\n")

    # Validierung
    if not check_env_file():
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    show_migration_hint()

    # Port wählen
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"{RED}❌ Ungültiger Port: {sys.argv[1]}{RESET}")
            sys.exit(1)

    # Server starten
    start_server(port=port)


if __name__ == "__main__":
    main()
