import subprocess
import sys
from pathlib import Path


MAC_USER = "Ashvath"
MAC_HOST = "100.79.123.44"
MAC_SCRIPTS_DIR = "/Users/Ashvath/Ashvath-private-cloud/scripts"

ALLOWED_SCRIPTS = {
    "remote-health-check.sh": "Run full remote health check",
    "view-logs.sh": "View recent safe service logs",
    "cloudctl.sh": "Run cloud control/status script",
    "emergency-restart.sh": "Restart predefined private cloud services"
}

MENU_COMMANDS = {
    "status": "remote-health-check.sh",
    "health": "remote-health-check.sh",
    "logs": "view-logs.sh",
    "cloudctl": "cloudctl.sh",
    "restart": "emergency-restart.sh"
}


def run_script_on_mac(script_name):
    if script_name not in ALLOWED_SCRIPTS:
        print(f"Blocked: script is not allowlisted: {script_name}")
        return 1

    remote_script_path = f"{MAC_SCRIPTS_DIR}/{script_name}"

    ssh_command = [
        "ssh",
        f"{MAC_USER}@{MAC_HOST}",
        f"bash {remote_script_path}"
    ]

    try:
        result = subprocess.run(
            ssh_command,
            text=True,
            timeout=45
        )

        return result.returncode

    except subprocess.TimeoutExpired:
        print("Error: SSH command timed out after 45 seconds.")
        return 1

    except KeyboardInterrupt:
        print("Cancelled by user.")
        return 1

    except Exception as error:
        print(f"Bridge error: {error}")
        return 1


def interactive_mode():
    print("=" * 40)
    print(" Vetri HomeLLM Bridge - PC Brain")
    print("=" * 40)
    print("Available commands:")

    for command in MENU_COMMANDS:
        print(f"- {command}")

    print("- exit")
    print()

    while True:
        user_command = input("Vetri > ").strip().lower()

        if user_command in ["exit", "quit"]:
            print("Exiting bridge.")
            break

        if user_command not in MENU_COMMANDS:
            print("Unknown command. Allowed commands only.")
            continue

        script_name = MENU_COMMANDS[user_command]

        print()
        print("Running on Mac server...")
        print()

        run_script_on_mac(script_name)
        print()


def main():
    if len(sys.argv) == 2:
        script_name = Path(sys.argv[1]).name
        exit_code = run_script_on_mac(script_name)
        sys.exit(exit_code)

    interactive_mode()


if __name__ == "__main__":
    main()