#!/usr/bin/env python3
"""
Read Slack thread messages (full conversation context).

Usage:
    python3 slack_thread_read.py --channel C12345 --thread-ts 1234567890.123456
    python3 slack_thread_read.py --channel C12345 --thread-ts 1234567890.123456 --json
    python3 slack_thread_read.py --channel C12345 --thread-ts 1234567890.123456 --limit 10
    python3 slack_thread_read.py --channel C12345 --thread-ts 1234567890.123456 --exclude-bots

Token resolution:
    Reads decrypted slack-bot credential from <workspace>/.credentials/ directory.

Required scopes: channels:history, groups:history, im:history, mpim:history
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

_user_cache = {}


def _resolve_token():
    cred_dir = Path(os.getcwd()) / ".credentials"
    if not cred_dir.is_dir():
        print(f"Error: .credentials/ directory not found in workspace root: {cred_dir}", file=sys.stderr)
        sys.exit(1)

    for f in cred_dir.glob("*.json"):
        try:
            with open(f) as fh:
                data = json.load(fh)
            if data.get("type") == "slack-bot" and "bot_token" in data:
                return data["bot_token"]
        except (json.JSONDecodeError, KeyError, OSError):
            continue

    print("Error: no slack-bot credential found in .credentials/", file=sys.stderr)
    sys.exit(1)


def load_client():
    return WebClient(token=_resolve_token())


def get_user_name(client, user_id):
    if not user_id:
        return "unknown"
    if user_id in _user_cache:
        return _user_cache[user_id]
    try:
        resp = client.users_info(user=user_id)
        profile = resp["user"]["profile"]
        name = profile.get("display_name") or profile.get("real_name") or user_id
        _user_cache[user_id] = name
        return name
    except SlackApiError:
        _user_cache[user_id] = user_id
        return user_id


def fetch_thread(channel, thread_ts, limit=None, exclude_bots=False):
    client = load_client()
    messages = []
    cursor = None

    try:
        while True:
            kwargs = {
                "channel": channel,
                "ts": thread_ts,
                "limit": min(limit or 200, 200),
            }
            if cursor:
                kwargs["cursor"] = cursor

            resp = client.conversations_replies(**kwargs)

            for msg in resp["messages"]:
                if exclude_bots and msg.get("bot_id"):
                    continue
                messages.append({
                    "ts": msg["ts"],
                    "user_id": msg.get("user", ""),
                    "user_name": get_user_name(client, msg.get("user")),
                    "text": msg.get("text", ""),
                    "time": datetime.fromtimestamp(float(msg["ts"])).strftime(
                        "%Y-%m-%d %H:%M:%S"),
                    "is_parent": msg["ts"] == thread_ts,
                    "files": [
                        {
                            "name": f.get("name", ""),
                            "mimetype": f.get("mimetype", ""),
                            "url": f.get("url_private_download", ""),
                        }
                        for f in msg.get("files", [])
                    ],
                })

                if limit and len(messages) >= limit:
                    return messages

            if not resp.get("has_more"):
                break
            cursor = resp["response_metadata"].get("next_cursor")
            if not cursor:
                break

    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}", file=sys.stderr)
        sys.exit(1)

    return messages


def format_text(messages):
    lines = []
    for msg in messages:
        prefix = "[parent]" if msg["is_parent"] else "[reply]"
        header = f"{prefix} {msg['user_name']} ({msg['time']})"
        lines.append(header)
        lines.append(msg["text"])
        if msg["files"]:
            for f in msg["files"]:
                lines.append(f"  [file] {f['name']} ({f['mimetype']})")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Read Slack thread messages")
    parser.add_argument("--channel", required=True,
                        help="Channel ID (C.../D.../G...)")
    parser.add_argument("--thread-ts", required=True,
                        help="Parent message timestamp of the thread")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max number of messages to fetch")
    parser.add_argument("--exclude-bots", action="store_true",
                        help="Exclude bot messages (included by default)")
    parser.add_argument("--json", action="store_true", dest="output_json",
                        help="Output as JSON instead of text")

    args = parser.parse_args()

    messages = fetch_thread(args.channel, args.thread_ts,
                            args.limit, args.exclude_bots)

    if args.output_json:
        print(json.dumps(messages, ensure_ascii=False, indent=2))
    else:
        print(format_text(messages))


if __name__ == "__main__":
    main()
