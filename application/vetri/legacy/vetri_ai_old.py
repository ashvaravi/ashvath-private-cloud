import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from time import time


BASE_DIR = Path(__file__).resolve().parent
ACTIONS_FILE = BASE_DIR / "vetri_actions.json"
LOG_DIR = BASE_DIR / "logs"
AUDIT_LOG = LOG_DIR / "audit.jsonl"
BRIDGE_FILE = BASE_DIR / "vetri_bridge.py"

last_execution_time = None


def load_actions():
    with open(ACTIONS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def write_audit_log(user_input, action_name, decision, details):
    LOG_DIR.mkdir(exist_ok=True)

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "input": user_input,
        "action": action_name,
        "decision": decision,
        "details": details
    }

    with open(AUDIT_LOG, "a", encoding="utf-8") as file:
        file.write(json.dumps(log_entry) + "\n")


def is_blocked(user_input, config):
    text = user_input.lower()

    for keyword in config.get("blocked_keywords", []):
        if keyword.lower() in text:
            return True, keyword

    return False, None


def match_action(user_input, config):
    text = user_input.lower()

    for action_name, action in config["actions"].items():
        if not action.get("allowed", False):
            continue

        for keyword in action.get("intent_keywords", []):
            if keyword.lower() in text:
                return action_name, action

        for pattern in action.get("intent_patterns", []):
            if re.search(pattern, text):
                return action_name, action

    return None, None


def confirm_action(action):
    confirmation_text = action.get("confirmation_text", "YES")

    print()
    print("This action requires confirmation.")
    print(f"Action: {action.get('description')}")
    print(f"Risk: {action.get('risk')}")
    print(f"Type exactly: {confirmation_text}")

    user_confirmation = input("> ").strip()

    return user_confirmation == confirmation_text


def execute_action(action_name, action):
    script_name = action["script"]

    if not BRIDGE_FILE.exists():
        return False, f"Bridge file not found: {BRIDGE_FILE}"

    command = [
        "python",
        str(BRIDGE_FILE),
        script_name
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode == 0:
            return True, output if output else "Command completed successfully."

        return False, error if error else output

    except subprocess.TimeoutExpired:
        return False, "Execution timed out after 20 seconds. Possible SSH hang."

    except Exception as error:
        return False, str(error)


def main():
    global last_execution_time

    config = load_actions()

    print("Vetri Skeleton Phase 1")
    print("Type your request. Example: check server status")
    print("Type 'exit' to quit.")
    print()

    while True:
        user_input = input("Vetri> ").strip()

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting Vetri.")
            break

        if not user_input:
            continue

        blocked, blocked_keyword = is_blocked(user_input, config)

        if blocked:
            message = f"Blocked because input contains unsafe keyword: {blocked_keyword}"
            print(message)
            write_audit_log(user_input, None, "blocked", message)
            continue

        action_name, action = match_action(user_input, config)

        if action is None:
            message = "No safe matching action found."
            print(message)
            write_audit_log(user_input, None, "rejected", message)
            continue

        risk = action.get("risk", "high")
        policy = config.get("risk_policy", {}).get(risk, "block")

        if policy == "block":
            message = f"Action blocked by risk policy. Risk: {risk}"
            print(message)
            write_audit_log(user_input, action_name, "blocked", message)
            continue

        if policy == "confirm" or action.get("requires_confirmation", False):
            confirmed = confirm_action(action)

            if not confirmed:
                message = "Confirmation failed. Action cancelled."
                print(message)
                write_audit_log(user_input, action_name, "cancelled", message)
                continue

        current_time = time()

        if last_execution_time and (current_time - last_execution_time < 3):
            message = "Command issued too quickly."
            print("Please wait before issuing another command.")
            write_audit_log(user_input, action_name, "rate_limited", message)
            continue

        print(f"Executing safe action: {action_name}")

        success, output = execute_action(action_name, action)
        last_execution_time = current_time

        if success:
            print()
            print(output)
            write_audit_log(user_input, action_name, "executed", output)
        else:
            print()
            print("Execution failed:")
            print(output)
            write_audit_log(user_input, action_name, "failed", output)


if __name__ == "__main__":
    main()