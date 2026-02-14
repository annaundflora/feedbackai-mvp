#!/usr/bin/env python3
"""
Interaktives Manual Test Script für FeedbackAI Backend
"""
import requests
import json
import sys
from time import sleep

BASE_URL = "http://localhost:8000"
YELLOW = "\033[93m"
GREEN = "\033[92m"
BLUE = "\033[94m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text):
    """Druckt Header"""
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}{text}{RESET}")
    print(f"{BLUE}{BOLD}{'='*60}{RESET}\n")


def print_response(label, data):
    """Druckt formatierte Response"""
    print(f"{YELLOW}{label}:{RESET}")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print()


def test_health():
    """Test: Health Check"""
    print_header("TEST 1: Health Check")

    try:
        response = requests.get(f"{BASE_URL}/health")

        if response.status_code == 200:
            print(f"{GREEN}✅ Health Check erfolgreich{RESET}")
            print_response("Response", response.json())
            return True
        else:
            print(f"{RED}❌ Health Check fehlgeschlagen: {response.status_code}{RESET}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"{RED}❌ Kann keine Verbindung herstellen!{RESET}")
        print(f"{YELLOW}→ Stelle sicher, dass der Server läuft (python backend/start.py){RESET}")
        return False


def test_interview_flow():
    """Test: Kompletter Interview Flow"""
    print_header("TEST 2: Interview Flow")

    anonymous_id = input(f"{BOLD}Anonymous ID (Enter für 'test-user'): {RESET}").strip()
    if not anonymous_id:
        anonymous_id = "test-user"

    # Start Interview
    print(f"\n{BLUE}→ Starte Interview für '{anonymous_id}'...{RESET}")

    try:
        response = requests.post(
            f"{BASE_URL}/api/interview/start",
            json={"anonymous_id": anonymous_id},
            stream=True,
            timeout=30
        )

        if response.status_code != 200:
            print(f"{RED}❌ Start fehlgeschlagen: {response.status_code}{RESET}")
            print(response.text)
            return

        print(f"{GREEN}✅ Interview gestartet - SSE Stream:{RESET}\n")

        session_id = None
        full_response = ""

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')

                if line_str.startswith('data: '):
                    data_json = line_str[6:]

                    try:
                        event = json.loads(data_json)

                        if event.get('type') == 'text-delta':
                            # Zeige Chunks
                            chunk = event.get('content', '')
                            print(chunk, end='', flush=True)
                            full_response += chunk

                        elif event.get('type') == 'text-done':
                            print()  # Newline nach vollständiger Antwort

                        elif event.get('type') == 'metadata':
                            session_id = event.get('session_id')
                            print(f"\n{YELLOW}Session ID: {session_id}{RESET}\n")
                    except json.JSONDecodeError:
                        pass

        if not session_id:
            print(f"{RED}❌ Keine Session ID erhalten{RESET}")
            return

        print(f"\n{GREEN}✅ Opening-Frage erhalten{RESET}")

        # User Messages
        print(f"\n{BLUE}→ Sende nun Nachrichten (leer = Interview beenden){RESET}\n")

        message_count = 0
        while True:
            user_message = input(f"{BOLD}Du: {RESET}").strip()

            if not user_message:
                break

            # Send Message
            response = requests.post(
                f"{BASE_URL}/api/interview/message",
                json={"session_id": session_id, "message": user_message},
                stream=True,
                timeout=30
            )

            if response.status_code != 200:
                print(f"{RED}❌ Message fehlgeschlagen: {response.status_code}{RESET}")
                print(response.text)
                break

            print(f"{GREEN}AI: {RESET}", end='', flush=True)

            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')

                    if line_str.startswith('data: '):
                        data_json = line_str[6:]

                        try:
                            event = json.loads(data_json)

                            if event.get('type') == 'text-delta':
                                chunk = event.get('content', '')
                                print(chunk, end='', flush=True)

                            elif event.get('type') == 'text-done':
                                print()
                        except json.JSONDecodeError:
                            pass

            print()
            message_count += 1

        # End Interview
        print(f"\n{BLUE}→ Beende Interview...{RESET}")

        response = requests.post(
            f"{BASE_URL}/api/interview/end",
            json={"session_id": session_id},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n{GREEN}✅ Interview beendet{RESET}")
            print(f"\n{YELLOW}Summary:{RESET}")
            print(result.get('summary', 'Keine Summary'))
            print(f"\n{YELLOW}Nachrichten: {result.get('message_count')}{RESET}")
        else:
            print(f"{RED}❌ End fehlgeschlagen: {response.status_code}{RESET}")
            print(response.text)

    except requests.exceptions.Timeout:
        print(f"{RED}❌ Timeout - Server antwortet nicht{RESET}")
    except Exception as e:
        print(f"{RED}❌ Fehler: {e}{RESET}")


def test_summary_injection():
    """Test: Summary Injection"""
    print_header("TEST 3: Summary Injection (Vorherige Summaries)")

    anonymous_id = input(f"{BOLD}Anonymous ID (muss vorherige Interviews haben): {RESET}").strip()
    if not anonymous_id:
        print(f"{YELLOW}Test übersprungen{RESET}")
        return

    print(f"\n{BLUE}→ Starte Interview für '{anonymous_id}' (sollte vorherige Summaries laden)...{RESET}\n")

    try:
        response = requests.post(
            f"{BASE_URL}/api/interview/start",
            json={"anonymous_id": anonymous_id},
            stream=True,
            timeout=30
        )

        print(f"{GREEN}Opening-Frage:{RESET} ", end='')

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')

                if line_str.startswith('data: '):
                    try:
                        event = json.loads(line_str[6:])

                        if event.get('type') == 'text-delta':
                            print(event.get('content', ''), end='', flush=True)
                        elif event.get('type') == 'metadata':
                            session_id = event.get('session_id')

                            # Beende sofort wieder
                            print(f"\n\n{BLUE}→ Beende Test-Interview...{RESET}")
                            requests.post(
                                f"{BASE_URL}/api/interview/end",
                                json={"session_id": session_id}
                            )
                    except:
                        pass

        print(f"\n{GREEN}✅ Test abgeschlossen{RESET}")
        print(f"{YELLOW}→ Prüfe ob der AI-Kontext auf vorherige Gespräche Bezug nimmt{RESET}")

    except Exception as e:
        print(f"{RED}❌ Fehler: {e}{RESET}")


def main():
    """Hauptfunktion"""
    print(f"{BLUE}{BOLD}")
    print("╔════════════════════════════════════════════════════╗")
    print("║   FeedbackAI Backend - Manueller Test             ║")
    print("╚════════════════════════════════════════════════════╝")
    print(f"{RESET}\n")

    # Health Check
    if not test_health():
        sys.exit(1)

    input(f"{BOLD}Enter drücken um fortzufahren...{RESET}")

    # Interview Flow
    test_interview_flow()

    # Summary Injection (optional)
    cont = input(f"\n{BOLD}Summary Injection testen? (y/n): {RESET}").lower()
    if cont == 'y':
        test_summary_injection()

    print(f"\n{GREEN}{BOLD}✅ Tests abgeschlossen!{RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Test abgebrochen{RESET}")
