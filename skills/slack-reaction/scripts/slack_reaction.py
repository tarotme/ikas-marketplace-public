#!/usr/bin/env python3
"""
Add or remove emoji reactions on Slack messages.

Usage:
    python3 slack_reaction.py add --channel C12345 --ts 1234567890.123456 --emoji thumbsup
    python3 slack_reaction.py remove --channel C12345 --ts 1234567890.123456 --emoji thumbsup

Token resolution:
    Reads decrypted slack-bot credential from <workspace>/.credentials/ directory.

Required scopes: reactions:write
"""

import argparse
import json
import os
import sys
from pathlib import Path

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


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


def add_reaction(channel, ts, emoji):
    client = load_client()
    try:
        client.reactions_add(channel=channel, timestamp=ts, name=emoji)
        print(f":{emoji}:")
    except SlackApiError as e:
        if e.response["error"] == "already_reacted":
            print(f":{emoji}: (already reacted)")
        else:
            print(f"Slack API error: {e.response['error']}", file=sys.stderr)
            sys.exit(1)


def remove_reaction(channel, ts, emoji):
    client = load_client()
    try:
        client.reactions_remove(channel=channel, timestamp=ts, name=emoji)
        print(f"removed :{emoji}:")
    except SlackApiError as e:
        if e.response["error"] == "no_reaction":
            print(f":{emoji}: (no reaction to remove)")
        else:
            print(f"Slack API error: {e.response['error']}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Slack emoji reactions")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in [
        ("add", "Add a reaction to a message"),
        ("remove", "Remove a reaction from a message"),
    ]:
        p = subparsers.add_parser(name, help=help_text)
        p.add_argument("--channel", required=True, help="Channel ID")
        p.add_argument("--ts", required=True, help="Message timestamp")
        p.add_argument("--emoji", required=True,
                       help="Emoji name without colons (e.g. thumbsup, eyes, white_check_mark)")

    args = parser.parse_args()

    if args.command == "add":
        add_reaction(args.channel, args.ts, args.emoji)
    elif args.command == "remove":
        remove_reaction(args.channel, args.ts, args.emoji)


if __name__ == "__main__":
    main()
