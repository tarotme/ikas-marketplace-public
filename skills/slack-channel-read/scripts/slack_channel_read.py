#!/usr/bin/env python3
"""
Read context messages around a specific message in a Slack channel.

Usage:
    python3 slack_channel_read.py --channel C12345 --ts 1234567890.123456
    python3 slack_channel_read.py --channel C12345 --ts 1234567890.123456 --before 10 --after 5
    python3 slack_channel_read.py --channel C12345 --ts 1234567890.123456 --json
    python3 slack_channel_read.py --channel C12345 --latest --limit 20

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
        print(
            f"Error: .credentials/ directory not found in workspace root: {cred_dir}",
            file=sys.stderr,
        )
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


def _parse_message(client, msg, target_ts=None):
    ts = msg["ts"]
    thread_info = None
    if msg.get("thread_ts") and msg.get("reply_count"):
        thread_info = {"reply_count": msg["reply_count"]}

    return {
        "ts": ts,
        "user_id": msg.get("user", ""),
        "user_name": get_user_name(client, msg.get("user")),
        "text": msg.get("text", ""),
        "time": datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S"),
        "is_target": ts == target_ts if target_ts else False,
        "thread": thread_info,
        "files": [
            {
                "name": f.get("name", ""),
                "mimetype": f.get("mimetype", ""),
                "url": f.get("url_private_download", ""),
            }
            for f in msg.get("files", [])
        ],
    }


def fetch_context(channel, target_ts, before=5, after=5, exclude_bots=False):
    """Fetch messages surrounding target_ts in a channel."""
    client = load_client()

    before_msgs = []
    after_msgs = []
    target_msg = None

    try:
        # conversations.history returns newest-first; latest=ts, inclusive=True
        # gives the target + older messages
        resp = client.conversations_history(
            channel=channel, latest=target_ts, inclusive=True, limit=before + 1
        )
        raw = resp["messages"]
        for m in raw:
            if exclude_bots and m.get("bot_id"):
                continue
            if m["ts"] == target_ts:
                target_msg = _parse_message(client, m, target_ts)
            else:
                before_msgs.append(_parse_message(client, m, target_ts))

        # If we didn't find the target in the first call (e.g. filtered by bot),
        # fetch it explicitly
        if target_msg is None and raw:
            for m in raw:
                if m["ts"] == target_ts:
                    target_msg = _parse_message(client, m, target_ts)
                    break

        if target_msg is None:
            print(
                f"Error: message with ts={target_ts} not found in channel {channel}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Fetch messages after the target (newer)
        resp = client.conversations_history(
            channel=channel, oldest=target_ts, inclusive=False, limit=after
        )
        for m in resp["messages"]:
            if exclude_bots and m.get("bot_id"):
                continue
            after_msgs.append(_parse_message(client, m, target_ts))

    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}", file=sys.stderr)
        sys.exit(1)

    # before_msgs are newest-first from API, reverse to chronological
    before_msgs.reverse()
    # after_msgs are also newest-first, reverse to chronological
    after_msgs.reverse()

    return before_msgs + [target_msg] + after_msgs


def fetch_latest(channel, limit=20, exclude_bots=False):
    """Fetch the latest N messages from a channel."""
    client = load_client()
    messages = []

    try:
        resp = client.conversations_history(channel=channel, limit=limit)
        for m in resp["messages"]:
            if exclude_bots and m.get("bot_id"):
                continue
            messages.append(_parse_message(client, m))

    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}", file=sys.stderr)
        sys.exit(1)

    messages.reverse()
    return messages


def format_text(messages):
    lines = []
    for msg in messages:
        marker = " >>>" if msg.get("is_target") else "    "
        thread_tag = ""
        if msg.get("thread") and msg["thread"].get("reply_count"):
            thread_tag = f" [thread: {msg['thread']['reply_count']} replies]"
        header = f"{marker} {msg['user_name']} ({msg['time']}){thread_tag}"
        lines.append(header)
        text_lines = msg["text"].splitlines() if msg["text"] else [""]
        for tl in text_lines:
            lines.append(f"     {tl}")
        if msg["files"]:
            for f in msg["files"]:
                lines.append(f"       [file] {f['name']} ({f['mimetype']})")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Read context messages around a specific message in a Slack channel"
    )
    parser.add_argument(
        "--channel", required=True, help="Channel ID (C.../D.../G...)"
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--ts", help="Target message timestamp to read context around"
    )
    mode.add_argument(
        "--latest",
        action="store_true",
        help="Fetch the latest messages from the channel",
    )

    parser.add_argument(
        "--before",
        type=int,
        default=5,
        help="Number of messages before the target (default: 5)",
    )
    parser.add_argument(
        "--after",
        type=int,
        default=5,
        help="Number of messages after the target (default: 5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of latest messages to fetch (for --latest, default: 20)",
    )
    parser.add_argument(
        "--exclude-bots",
        action="store_true",
        help="Exclude bot messages (included by default)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output as JSON instead of text",
    )

    args = parser.parse_args()

    if args.latest:
        messages = fetch_latest(args.channel, args.limit, args.exclude_bots)
    else:
        messages = fetch_context(
            args.channel, args.ts, args.before, args.after, args.exclude_bots
        )

    if not messages:
        print("No messages found.")
        return

    if args.output_json:
        print(json.dumps(messages, ensure_ascii=False, indent=2))
    else:
        print(format_text(messages))


if __name__ == "__main__":
    main()
