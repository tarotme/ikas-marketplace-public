#!/usr/bin/env python3
"""
IKAS Trigger API Call — Invoke API-type triggers via webhook.

Usage:
  python3 trigger_api_call.py call --message <msg> [--trigger-name <name>] [--agent-name <name>]
  python3 trigger_api_call.py call --url <url> --key <key> --message <msg>
  python3 trigger_api_call.py agents [--trigger-name <name>]
  python3 trigger_api_call.py agents --url <url> --key <key>

Credential resolution (priority order):
  1. Explicit --url and --key flags
  2. Environment variables TRIGGER_URL and TRIGGER_API_KEY
  3. Auto-discover from <cwd>/.credentials/ directory
     (type: "ikas-trigger", or legacy custom with trigger_url + api_key fields)

When multiple trigger credentials exist, use --trigger-name to select one by memo or id.
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' package required. Install: pip install requests", file=sys.stderr)
    sys.exit(1)


def _find_trigger_credentials():
    """Search .credentials/ for trigger-related credentials."""
    cred_dir = Path(os.getcwd()) / ".credentials"
    if not cred_dir.is_dir():
        return []

    results = []
    for f in sorted(cred_dir.glob("*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
            has_fields = "api_key" in data and ("trigger_url" in data or "url" in data)
            is_typed = data.get("type") == "ikas-trigger"
            if is_typed or has_fields:
                if not has_fields:
                    continue
                results.append({
                    "id": data.get("id", f.stem),
                    "memo": data.get("memo", ""),
                    "type": data.get("type", ""),
                    "url": data.get("trigger_url") or data.get("url", ""),
                    "api_key": data["api_key"],
                })
        except (json.JSONDecodeError, OSError):
            continue

    # Prefer typed ikas-trigger credentials when sorting for display
    results.sort(key=lambda c: (0 if c.get("type") == "ikas-trigger" else 1, c["id"]))
    return results


def _resolve_trigger(args):
    """Resolve trigger URL and API key from args, env, or credentials."""
    url = getattr(args, "url", None)
    key = getattr(args, "key", None)

    if url and key:
        return url, key

    creds = _find_trigger_credentials()

    # If --key is provided without --url, find URL from credentials matching that key
    if key and not url:
        matched = [c for c in creds if c["api_key"] == key]
        if matched:
            return matched[0]["url"], key
        # Key provided but not found in credentials — need explicit URL
        env_url = os.environ.get("TRIGGER_URL", "")
        if env_url:
            return env_url, key
        print("Error: --key provided but no matching credential found and --url not specified", file=sys.stderr)
        sys.exit(1)

    env_url = os.environ.get("TRIGGER_URL", "")
    env_key = os.environ.get("TRIGGER_API_KEY", "")
    if env_url and env_key:
        return env_url, env_key

    if not creds:
        print("Error: No trigger credentials found. Provide --key, set TRIGGER_URL/TRIGGER_API_KEY env vars, "
              "or add an ikas-trigger credential (trigger_url + api_key) to .credentials/", file=sys.stderr)
        sys.exit(1)

    trigger_name = getattr(args, "trigger_name", None)
    if trigger_name:
        matched = [c for c in creds if trigger_name.lower() in c["memo"].lower() or trigger_name.lower() in c["id"].lower()]
        if not matched:
            print(f"Error: No trigger credential matching '{trigger_name}'. Available: {[c['id'] for c in creds]}", file=sys.stderr)
            sys.exit(1)
        cred = matched[0]
    elif len(creds) == 1:
        cred = creds[0]
    else:
        print(f"Error: Multiple trigger credentials found. Use --trigger-name or --key to select:", file=sys.stderr)
        for c in creds:
            print(f"  - {c['id']}: {c['memo']} ({c['url']})", file=sys.stderr)
        sys.exit(1)

    return cred["url"], cred["api_key"]


def cmd_call(args):
    url, key = _resolve_trigger(args)

    headers = {"X-API-Key": key, "Content-Type": "application/json"}
    body = {"message": args.message}
    if args.agent_name:
        body["agent_name"] = args.agent_name

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=300)
    except requests.RequestException as e:
        print(f"Error: Request failed — {e}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code == 401:
        print("Error: Invalid or missing API Key", file=sys.stderr)
        sys.exit(1)
    if resp.status_code == 400:
        try:
            data = resp.json()
            print(f"Error: Bad request — {data.get('error', resp.text)}", file=sys.stderr)
        except ValueError:
            print(f"Error: Bad request — {resp.text}", file=sys.stderr)
        sys.exit(1)

    try:
        result = resp.json()
    except ValueError:
        print(resp.text)
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_agents(args):
    url, key = _resolve_trigger(args)
    if not url.endswith("/agents"):
        url = url.rstrip("/") + "/agents"

    headers = {"X-API-Key": key}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        print(f"Error: Request failed — {e}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code == 401:
        print("Error: Invalid or missing API Key", file=sys.stderr)
        sys.exit(1)

    try:
        result = resp.json()
    except ValueError:
        print(resp.text)
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="IKAS Trigger API Call")
    sub = parser.add_subparsers(dest="command")

    p_call = sub.add_parser("call", help="Send a message to trigger webhook")
    p_call.add_argument("--url", help="Trigger webhook URL (or auto-discover from .credentials/)")
    p_call.add_argument("--key", help="API Key (or auto-discover from .credentials/)")
    p_call.add_argument("--trigger-name", help="Select trigger credential by name (when multiple exist)")
    p_call.add_argument("--message", "-m", required=True, help="Message content")
    p_call.add_argument("--agent-name", help="Dynamic agent name (thread mode)")

    p_agents = sub.add_parser("agents", help="List dynamic agents for a trigger")
    p_agents.add_argument("--url", help="Trigger hook/agents URL (or auto-discover)")
    p_agents.add_argument("--key", help="API Key (or auto-discover)")
    p_agents.add_argument("--trigger-name", help="Select trigger credential by name")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "call":
        cmd_call(args)
    elif args.command == "agents":
        cmd_agents(args)


if __name__ == "__main__":
    main()
