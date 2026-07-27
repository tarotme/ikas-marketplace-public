#!/usr/bin/env python3
"""
IKAS Engine Self-Schedule — Schedule delayed messages to yourself via Engine HTTP API.

Usage:
  python3 engine_self_schedule.py schedule --message <msg> --at <iso8601_or_relative>
  python3 engine_self_schedule.py recall --turn-id <turn_id>
  python3 engine_self_schedule.py list
  python3 engine_self_schedule.py cancel --id <msg_id>
  python3 engine_self_schedule.py reschedule --id <msg_id> --message <msg> --at <time>

Environment variables (set automatically by IKAS Engine):
  IKAS_AGENT_ID     — current agent ID
  IKAS_ENGINE_URL   — Engine HTTP base URL (e.g. http://localhost:60320)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def _get_env():
    agent_id = os.environ.get("IKAS_AGENT_ID", "")
    engine_url = os.environ.get("IKAS_ENGINE_URL", "")
    if not agent_id:
        print("Error: IKAS_AGENT_ID not set", file=sys.stderr)
        sys.exit(1)
    if not engine_url:
        print("Error: IKAS_ENGINE_URL not set", file=sys.stderr)
        sys.exit(1)
    return agent_id, engine_url.rstrip("/")


def _parse_time(at_str: str) -> str:
    """Parse ISO 8601 timestamp or relative time like +30m, +2h."""
    relative = re.match(r"^\+(\d+)([mhd])$", at_str.strip())
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        delta = {"m": timedelta(minutes=amount), "h": timedelta(hours=amount), "d": timedelta(days=amount)}[unit]
        dt = datetime.now(timezone.utc) + delta
        return dt.isoformat()
    try:
        dt = datetime.fromisoformat(at_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        print(f"Error: Invalid time format: {at_str}", file=sys.stderr)
        print("Use ISO 8601 (e.g. 2026-07-18T01:00:00+08:00) or relative (+30m, +2h, +1d)", file=sys.stderr)
        sys.exit(1)


def _api_request(url: str, method: str = "GET", data: dict = None) -> dict:
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        try:
            err_body = json.loads(e.read().decode())
            print(f"Error ({e.code}): {err_body.get('error', err_body)}", file=sys.stderr)
        except (ValueError, AttributeError):
            print(f"Error ({e.code}): {e.reason}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Error: Connection failed — {e.reason}", file=sys.stderr)
        sys.exit(1)


def cmd_schedule(args):
    agent_id, engine_url = _get_env()
    scheduled_at = _parse_time(args.at)
    url = f"{engine_url}/agents/{agent_id}/schedule"
    result = _api_request(url, "POST", {
        "message": args.message,
        "scheduled_at": scheduled_at,
    })
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_recall(args):
    agent_id, engine_url = _get_env()
    url = f"{engine_url}/agents/{agent_id}/turn/{args.turn_id}"
    result = _api_request(url)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_list(args):
    _, engine_url = _get_env()
    url = f"{engine_url}/scheduled-messages"
    result = _api_request(url)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_cancel(args):
    _, engine_url = _get_env()
    url = f"{engine_url}/scheduled-messages/{args.id}"
    result = _api_request(url, "DELETE")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_reschedule(args):
    """Cancel an existing message and schedule a new one."""
    _, engine_url = _get_env()
    # Cancel the old message
    cancel_url = f"{engine_url}/scheduled-messages/{args.id}"
    cancel_result = _api_request(cancel_url, "DELETE")
    print(f"Cancelled: {cancel_result.get('cancelled_id', args.id)}", file=sys.stderr)

    # Schedule the new one
    agent_id, engine_url = _get_env()
    scheduled_at = _parse_time(args.at)
    url = f"{engine_url}/agents/{agent_id}/schedule"
    result = _api_request(url, "POST", {
        "message": args.message,
        "scheduled_at": scheduled_at,
    })
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="IKAS Engine Self-Schedule")
    sub = parser.add_subparsers(dest="command")

    p_schedule = sub.add_parser("schedule", help="Schedule a delayed message to yourself")
    p_schedule.add_argument("--message", "-m", required=True, help="Message to send at the scheduled time")
    p_schedule.add_argument("--at", required=True, help="ISO 8601 timestamp or relative time (+30m, +2h, +1d)")

    p_recall = sub.add_parser("recall", help="Recall a specific turn's context")
    p_recall.add_argument("--turn-id", required=True, help="Turn ID to look up")

    sub.add_parser("list", help="List all pending scheduled messages")

    p_cancel = sub.add_parser("cancel", help="Cancel a scheduled message")
    p_cancel.add_argument("--id", required=True, help="Scheduled message ID to cancel")

    p_resched = sub.add_parser("reschedule", help="Cancel and reschedule a message")
    p_resched.add_argument("--id", required=True, help="Existing message ID to cancel")
    p_resched.add_argument("--message", "-m", required=True, help="New message content")
    p_resched.add_argument("--at", required=True, help="New time (ISO 8601 or relative)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmds = {"schedule": cmd_schedule, "recall": cmd_recall, "list": cmd_list, "cancel": cmd_cancel, "reschedule": cmd_reschedule}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
