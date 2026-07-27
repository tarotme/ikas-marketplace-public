#!/usr/bin/env python3
"""
Slack messaging script.
Sends messages, thread replies, updates existing messages, and downloads files.

Usage:
    python3 slack_reply.py send --channel C12345 --text "Hello"
    python3 slack_reply.py reply --channel C12345 --thread-ts 1234567890.123456 --text "Reply"
    python3 slack_reply.py update --channel C12345 --ts 1234567890.123456 --text "Updated"
    python3 slack_reply.py dm --user U01GSENE599 --text "Hello"
    python3 slack_reply.py download --url "https://files.slack.com/..." --output /tmp/audio.mp4

Token resolution:
    Reads decrypted slack-bot credential from <workspace>/.credentials/ directory.

Output: prints message ts (timestamp ID) to stdout on success.
On error: prints error message to stderr and exits with non-zero code.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
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


def _build_buttons_block(buttons_json):
    """Convert simplified button definitions into a Block Kit actions block."""
    buttons = json.loads(buttons_json)
    elements = []
    for btn in buttons:
        element = {
            "type": "button",
            "text": {"type": "plain_text", "text": btn["text"]},
            "action_id": btn["action_id"],
        }
        if "value" in btn:
            element["value"] = btn["value"]
        if "style" in btn:
            element["style"] = btn["style"]
        elements.append(element)
    return {"type": "actions", "elements": elements}


def _build_kwargs(text, blocks=None, attachments=None, buttons=None, color=None):
    kwargs = {"text": text}
    if blocks:
        kwargs["blocks"] = json.loads(blocks)
    if attachments:
        kwargs["attachments"] = json.loads(attachments)

    if buttons:
        actions_block = _build_buttons_block(buttons)
        if color:
            att = {"color": color, "blocks": [actions_block]}
            kwargs.setdefault("attachments", []).append(att)
        else:
            kwargs.setdefault("blocks", []).append(actions_block)

    return kwargs


def _upload_files(client, channel, file_paths, text=None, thread_ts=None):
    """Upload files to a channel, optionally with an initial comment and thread_ts."""
    file_uploads = []
    for fp in file_paths:
        p = Path(fp)
        if not p.is_file():
            print(f"Error: file not found: {fp}", file=sys.stderr)
            sys.exit(1)
        file_uploads.append({"file": str(p), "title": p.name})

    kwargs = {"channel": channel, "file_uploads": file_uploads}
    if text:
        kwargs["initial_comment"] = text
    if thread_ts:
        kwargs["thread_ts"] = thread_ts

    resp = client.files_upload_v2(**kwargs)
    files_info = resp.get("files", [])
    return files_info


def _parse_files(files_arg):
    """Parse comma-separated file paths, respecting quotes for paths with commas."""
    if not files_arg:
        return []
    return [f.strip() for f in files_arg.split(",") if f.strip()]


def send_message(channel, text, blocks=None, attachments=None,
                 buttons=None, color=None, files=None):
    client = load_client()
    try:
        file_paths = _parse_files(files)
        if file_paths:
            _upload_files(client, channel, file_paths, text=text)
            return "(file uploaded)"
        kwargs = {"channel": channel,
                  **_build_kwargs(text, blocks, attachments, buttons, color)}
        resp = client.chat_postMessage(**kwargs)
        return resp["ts"]
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}", file=sys.stderr)
        sys.exit(1)


def reply_in_thread(channel, thread_ts, text, blocks=None, attachments=None,
                    buttons=None, color=None, broadcast=False, files=None):
    client = load_client()
    try:
        file_paths = _parse_files(files)
        if file_paths:
            _upload_files(client, channel, file_paths, text=text, thread_ts=thread_ts)
            return "(file uploaded)"
        kwargs = {
            "channel": channel,
            "thread_ts": thread_ts,
            "reply_broadcast": broadcast,
            **_build_kwargs(text, blocks, attachments, buttons, color),
        }
        resp = client.chat_postMessage(**kwargs)
        return resp["ts"]
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}", file=sys.stderr)
        sys.exit(1)


def update_message(channel, ts, text, blocks=None, attachments=None,
                   buttons=None, color=None):
    client = load_client()
    try:
        kwargs = {"channel": channel, "ts": ts,
                  **_build_kwargs(text, blocks, attachments, buttons, color)}
        resp = client.chat_update(**kwargs)
        return resp["ts"]
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}", file=sys.stderr)
        sys.exit(1)


def dm_user(user_id, text, blocks=None, attachments=None,
            buttons=None, color=None, files=None):
    """Open (or reuse) a DM conversation with a user and send a message."""
    client = load_client()
    try:
        conv = client.conversations_open(users=[user_id])
        channel = conv["channel"]["id"]
        file_paths = _parse_files(files)
        if file_paths:
            _upload_files(client, channel, file_paths, text=text)
            return "(file uploaded)"
        kwargs = {"channel": channel,
                  **_build_kwargs(text, blocks, attachments, buttons, color)}
        resp = client.chat_postMessage(**kwargs)
        return resp["ts"]
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}", file=sys.stderr)
        sys.exit(1)


def download_file(url, output_path):
    token = _resolve_token()
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        return output_path
    except requests.RequestException as e:
        print(f"Download error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Slack messaging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, parser_kwargs, extra_args, has_files in [
        ("send", {"help": "Send a message to a channel"},
         [("--channel", {"required": True, "help": "Channel ID"})], True),
        ("reply", {"help": "Reply in a thread"},
         [("--channel", {"required": True, "help": "Channel ID"}),
          ("--thread-ts", {"required": True, "help": "Parent message timestamp"}),
          ("--broadcast", {"action": "store_true",
                           "help": "Also post reply to the channel"})], True),
        ("update", {"help": "Update an existing message"},
         [("--channel", {"required": True, "help": "Channel ID"}),
          ("--ts", {"required": True, "help": "Message timestamp to update"})], False),
        ("dm", {"help": "Send a DM to a user by User ID"},
         [("--user", {"required": True, "help": "Slack User ID (U...)"})], True),
    ]:
        p = subparsers.add_parser(name, **parser_kwargs)
        for arg_name, arg_kwargs in extra_args:
            p.add_argument(arg_name, **arg_kwargs)
        p.add_argument("--text", required=True, help="Message text")
        p.add_argument("--blocks", help="JSON string of Block Kit blocks")
        p.add_argument("--attachments", help="JSON string of attachments")
        p.add_argument("--buttons",
                       help='Simplified button JSON: [{"text":"OK","action_id":"ok","style":"primary","value":"yes"}]')
        p.add_argument("--color",
                       help="Attachment sidebar color hex (e.g. #2eb886), used with --buttons")
        if has_files:
            p.add_argument("--files",
                           help="Comma-separated file paths to upload (images, documents, etc.)")

    p_download = subparsers.add_parser("download", help="Download a file from Slack")
    p_download.add_argument("--url", required=True, help="File URL (url_private_download)")
    p_download.add_argument("--output", required=True, help="Local output path")

    args = parser.parse_args()

    if args.command == "send":
        ts = send_message(args.channel, args.text, args.blocks,
                          args.attachments, args.buttons, args.color,
                          args.files)
        print(ts)
    elif args.command == "reply":
        ts = reply_in_thread(args.channel, args.thread_ts, args.text,
                             args.blocks, args.attachments,
                             args.buttons, args.color, args.broadcast,
                             args.files)
        print(ts)
    elif args.command == "update":
        ts = update_message(args.channel, args.ts, args.text,
                            args.blocks, args.attachments,
                            args.buttons, args.color)
        print(ts)
    elif args.command == "dm":
        ts = dm_user(args.user, args.text, args.blocks,
                     args.attachments, args.buttons, args.color,
                     args.files)
        print(ts)
    elif args.command == "download":
        path = download_file(args.url, args.output)
        print(path)


if __name__ == "__main__":
    main()
