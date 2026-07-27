#!/usr/bin/env python3
"""
Add, list, edit, and delete comments on Jira tickets via REST API v3.

Usage:
    python3 jira_comment.py add --ticket PROJ-123 --body "Fixed in abc123"
    python3 jira_comment.py add --ticket PROJ-123 --body "LGTM" --on-behalf-of "Alice"
    python3 jira_comment.py list --ticket PROJ-123
    python3 jira_comment.py edit --ticket PROJ-123 --comment-id 10234 --body "Updated"
    python3 jira_comment.py delete --ticket PROJ-123 --comment-id 10234

Token is read from the credential JSON file in <workspace>/.credentials/ (token field).
Credential file: type="atlassian" JSON in .credentials/ with auth_mode "classic" or "scoped".
Authentication: Basic Auth (email:token) for Jira Cloud.
"""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

_cli_base_url = None
_cli_credential_id = None

_ATLASSIAN_API_BASE = "https://api.atlassian.com/ex/jira"


# ---------------------------------------------------------------------------
# Credential resolution
# ---------------------------------------------------------------------------

def _resolve_credential():
    cred_dir = Path(os.getcwd()) / ".credentials"
    if not cred_dir.is_dir():
        print(
            f"Error: .credentials/ directory not found in workspace root: {cred_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    candidates = []
    for f in cred_dir.glob("*.json"):
        try:
            with open(f) as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue

        cred_type = data.get("type", "")
        if cred_type not in ("jira", "atlassian"):
            continue
        if not data.get("email"):
            continue
        candidates.append((f, data))

    if not candidates:
        print(
            "Error: no Atlassian credential found in .credentials/\n"
            'Expected a JSON file with type="atlassian", email, and auth_mode ("classic" or "scoped").',
            file=sys.stderr,
        )
        sys.exit(1)

    if _cli_credential_id:
        matched = [
            (f, d) for f, d in candidates
            if d.get("id") == _cli_credential_id or f.stem == _cli_credential_id
        ]
        if not matched:
            available = [d.get("id", f.stem) for f, d in candidates]
            print(
                f"Error: credential '{_cli_credential_id}' not found.\n"
                f"Available: {', '.join(available)}",
                file=sys.stderr,
            )
            sys.exit(1)
        candidates = matched

    if len(candidates) > 1 and not _cli_credential_id:
        ids = [d.get("id", f.stem) for f, d in candidates]
        print(
            f"Warning: multiple Jira credentials found: {', '.join(ids)}\n"
            f"Using '{ids[0]}'. Specify --credential <id> to choose another.",
            file=sys.stderr,
        )

    f, data = candidates[0]
    email = data["email"]

    token = data.get("token") or data.get("api_token")
    if not token:
        print(
            f"Error: no token found in credential {data.get('id', f.name)}.",
            file=sys.stderr,
        )
        sys.exit(1)

    base_url = _cli_base_url or data.get("base_url")
    if not base_url:
        cloud_id = data.get("cloud_id")
        domain = data.get("domain")
        if cloud_id:
            base_url = f"{_ATLASSIAN_API_BASE}/{cloud_id}"
        elif domain:
            base_url = f"https://{domain}"
        else:
            print(
                f"Error: credential {data.get('id', f.name)} has no base_url, cloud_id, or domain.\n"
                "Provide --base-url <URL>, or add base_url/cloud_id/domain to the credential file.",
                file=sys.stderr,
            )
            sys.exit(1)

    is_service_account = (
        "serviceaccount" in email.lower()
        or data.get("auth_mode") == "scoped"
    )

    return {
        "id": data.get("id", f.stem),
        "email": email,
        "api_token": token,
        "base_url": base_url.rstrip("/"),
        "is_service_account": is_service_account,
    }


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _api_request(base_url, email, api_token, method, path, params=None, body=None):
    url = base_url.rstrip("/") + path
    if params:
        url += "?" + urlencode(params)

    cred = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {cred}",
        "Accept": "application/json",
    }

    data_bytes = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data_bytes = json.dumps(body).encode("utf-8")

    req = Request(url, data=data_bytes, headers=headers, method=method)

    try:
        with urlopen(req) as resp:
            raw = resp.read().decode()
            if not raw:
                return {}
            return json.loads(raw)
    except HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        try:
            detail = json.loads(err_body)
            msgs = detail.get("errorMessages", [])
            errs = detail.get("errors", {})
            parts = msgs + [f"{k}: {v}" for k, v in errs.items()]
            msg = "; ".join(parts) if parts else err_body
        except (json.JSONDecodeError, AttributeError):
            msg = err_body
        print(f"Jira API error ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)


class JiraClient:
    def __init__(self):
        cred = _resolve_credential()
        self.base_url = cred["base_url"]
        self.email = cred["email"]
        self.api_token = cred["api_token"]
        self.is_service_account = cred["is_service_account"]

    def get(self, path, params=None):
        return _api_request(self.base_url, self.email, self.api_token, "GET", path, params)

    def post(self, path, body=None, params=None):
        return _api_request(self.base_url, self.email, self.api_token, "POST", path, params, body)

    def put(self, path, body=None, params=None):
        return _api_request(self.base_url, self.email, self.api_token, "PUT", path, params, body)

    def delete(self, path, params=None):
        return _api_request(self.base_url, self.email, self.api_token, "DELETE", path, params)


# ---------------------------------------------------------------------------
# ADF helpers
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_ORDERED_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
_LINK_RE = re.compile(r"^\[([^\]]*)\]\(([^)]+)\)")


def _adf_text(text, marks=None):
    node = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def _with_mark(nodes, mark_type, attrs=None):
    mark = {"type": mark_type}
    if attrs:
        mark["attrs"] = attrs
    result = []
    for node in nodes:
        if node.get("type") != "text":
            result.append(node)
            continue
        marks = list(node.get("marks", []))
        marks.append(mark)
        updated = dict(node)
        updated["marks"] = marks
        result.append(updated)
    return result


def _parse_inline(text):
    """Parse inline Markdown into ADF text nodes."""
    if not text:
        return []

    nodes = []
    i = 0
    while i < len(text):
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                nodes.extend(_with_mark(_parse_inline(text[i + 2:end]), "strong"))
                i = end + 2
                continue

        if text[i] == "*" and not text.startswith("**", i):
            end = text.find("*", i + 1)
            if end != -1 and not text.startswith("**", end):
                nodes.extend(_with_mark(_parse_inline(text[i + 1:end]), "em"))
                i = end + 1
                continue

        if text[i] == "`":
            end = text.find("`", i + 1)
            if end != -1:
                nodes.append(_adf_text(text[i + 1:end], [{"type": "code"}]))
                i = end + 1
                continue

        if text[i] == "[":
            match = _LINK_RE.match(text[i:])
            if match:
                nodes.append(_adf_text(
                    match.group(1),
                    [{"type": "link", "attrs": {"href": match.group(2)}}],
                ))
                i += match.end()
                continue

        next_pos = len(text)
        for marker in ("**", "*", "`", "["):
            pos = text.find(marker, i)
            if pos != -1 and pos < next_pos:
                next_pos = pos

        chunk = text[i:next_pos] if next_pos > i else text[i:i + 1]
        if chunk:
            nodes.append(_adf_text(chunk))
        i = next_pos if next_pos > i else i + 1

    return nodes


def _adf_paragraph(text):
    return {"type": "paragraph", "content": _parse_inline(text)}


def _adf_list_item(text):
    return {
        "type": "listItem",
        "content": [_adf_paragraph(text)],
    }


def _is_block_start(line):
    if not line.strip():
        return False
    return (
        _HEADING_RE.match(line)
        or _BULLET_RE.match(line)
        or _ORDERED_RE.match(line)
    )


def _text_to_adf(text):
    """Convert Markdown-ish text to Atlassian Document Format (ADF)."""
    lines = text.split("\n")
    content = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            content.append({
                "type": "heading",
                "attrs": {"level": len(heading.group(1))},
                "content": _parse_inline(heading.group(2).strip()),
            })
            i += 1
            continue

        if _BULLET_RE.match(line):
            items = []
            while i < len(lines) and _BULLET_RE.match(lines[i]):
                item_text = _BULLET_RE.match(lines[i]).group(1)
                items.append(_adf_list_item(item_text))
                i += 1
            content.append({"type": "bulletList", "content": items})
            continue

        if _ORDERED_RE.match(line):
            items = []
            while i < len(lines) and _ORDERED_RE.match(lines[i]):
                item_text = _ORDERED_RE.match(lines[i]).group(1)
                items.append(_adf_list_item(item_text))
                i += 1
            content.append({"type": "orderedList", "content": items})
            continue

        paragraph_lines = []
        while i < len(lines) and lines[i].strip() and not _is_block_start(lines[i]):
            paragraph_lines.append(lines[i])
            i += 1

        if len(paragraph_lines) == 1:
            content.append(_adf_paragraph(paragraph_lines[0]))
        else:
            paragraph_content = []
            for idx, part in enumerate(paragraph_lines):
                if idx > 0:
                    paragraph_content.append({"type": "hardBreak"})
                paragraph_content.extend(_parse_inline(part))
            content.append({"type": "paragraph", "content": paragraph_content})

    if not content:
        content = [{"type": "paragraph", "content": []}]

    return {"type": "doc", "version": 1, "content": content}


def _text_to_adf_with_header(text, on_behalf_of):
    """Convert Markdown-ish text to ADF, prepending an italicized on-behalf-of header."""
    adf = _text_to_adf(text)
    adf["content"].insert(0, {
        "type": "paragraph",
        "content": [{
            "type": "text",
            "text": f"[On behalf of {on_behalf_of}]",
            "marks": [{"type": "em"}],
        }],
    })
    return adf


def _extract_adf_text(node):
    """Recursively extract plain text from Atlassian Document Format."""
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = []
    for child in node.get("content", []):
        parts.append(_extract_adf_text(child))
    joiner = "\n" if node.get("type") in ("doc", "paragraph", "bulletList", "orderedList", "listItem", "blockquote") else ""
    return joiner.join(parts)


def _read_stdin_content():
    if sys.stdin.isatty():
        print("Error: expected content from stdin (pipe or redirect)", file=sys.stderr)
        sys.exit(1)
    return sys.stdin.read()


def _resolve_text(value):
    """If value is '-', read from stdin; otherwise return as-is."""
    if value == "-":
        return _read_stdin_content()
    return value


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def _require_behalf_of(client, on_behalf_of):
    """If credential is a service account, --on-behalf-of is required."""
    if client.is_service_account and not on_behalf_of:
        print(
            "Error: current credential is a service account.\n"
            "Please provide --on-behalf-of <name> to identify the actual author.",
            file=sys.stderr,
        )
        sys.exit(1)


def cmd_add(args):
    client = JiraClient()
    ticket = args.ticket.strip()
    text = _resolve_text(args.body)
    _require_behalf_of(client, args.on_behalf_of)

    if args.on_behalf_of:
        adf = _text_to_adf_with_header(text, args.on_behalf_of)
    else:
        adf = _text_to_adf(text)

    body = {"body": adf}
    result = client.post(f"/rest/api/3/issue/{quote(ticket)}/comment", body)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        comment_id = result.get("id", "?")
        print(f"Comment added to {ticket} (id: {comment_id})")
        if args.on_behalf_of:
            print(f"  On behalf of: {args.on_behalf_of}")


def cmd_list(args):
    client = JiraClient()
    ticket = args.ticket.strip()

    data = client.get(f"/rest/api/3/issue/{quote(ticket)}/comment")
    comments = data.get("comments", [])

    if args.output_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not comments:
        print(f"No comments on {ticket}.")
        return

    if args.limit and args.limit < len(comments):
        comments = comments[-args.limit:]

    print(f"Comments on {ticket} ({data.get('total', len(comments))}):")
    for c in comments:
        cid = c.get("id", "?")
        author = c.get("author", {})
        name = author.get("displayName", "unknown")
        email = author.get("emailAddress", "")
        created = c.get("created", "")[:19].replace("T", " ")

        author_str = f"{name} ({email})" if email else name

        body_raw = c.get("body")
        body_text = _extract_adf_text(body_raw) if isinstance(body_raw, dict) else str(body_raw or "")

        print(f"  [{cid}] {created} | {author_str}")
        for line in body_text.splitlines():
            print(f"    {line}")


def cmd_edit(args):
    client = JiraClient()
    ticket = args.ticket.strip()
    comment_id = args.comment_id.strip()
    text = _resolve_text(args.body)
    _require_behalf_of(client, args.on_behalf_of)

    if args.on_behalf_of:
        adf = _text_to_adf_with_header(text, args.on_behalf_of)
    else:
        adf = _text_to_adf(text)

    body = {"body": adf}
    result = client.put(
        f"/rest/api/3/issue/{quote(ticket)}/comment/{quote(comment_id)}", body
    )

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Comment {comment_id} updated on {ticket}")


def cmd_delete(args):
    client = JiraClient()
    ticket = args.ticket.strip()
    comment_id = args.comment_id.strip()

    client.delete(f"/rest/api/3/issue/{quote(ticket)}/comment/{quote(comment_id)}")
    print(f"Comment {comment_id} deleted from {ticket}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global _cli_base_url, _cli_credential_id

    parser = argparse.ArgumentParser(description="Manage Jira ticket comments")
    parser.add_argument("--credential", default=None,
                        help="Credential ID to use (when multiple Jira credentials exist)")
    parser.add_argument("--base-url", default=None,
                        help="Jira Cloud base URL (overrides credential file)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = subparsers.add_parser("add", help="Add a comment to a ticket")
    p_add.add_argument("--ticket", required=True, help="Ticket key (e.g. PROJ-123)")
    p_add.add_argument("--body", required=True, help="Comment text, or '-' for stdin")
    p_add.add_argument("--on-behalf-of", default=None, help="Actual author name (prepended to body)")
    p_add.add_argument("--json", action="store_true", dest="output_json")

    # list
    p_list = subparsers.add_parser("list", help="List comments on a ticket")
    p_list.add_argument("--ticket", required=True, help="Ticket key")
    p_list.add_argument("--limit", type=int, default=None, help="Show last N comments")
    p_list.add_argument("--json", action="store_true", dest="output_json")

    # edit
    p_edit = subparsers.add_parser("edit", help="Edit an existing comment")
    p_edit.add_argument("--ticket", required=True, help="Ticket key")
    p_edit.add_argument("--comment-id", required=True, help="Comment ID to edit")
    p_edit.add_argument("--body", required=True, help="New comment text, or '-' for stdin")
    p_edit.add_argument("--on-behalf-of", default=None, help="Actual author name (prepended to body)")
    p_edit.add_argument("--json", action="store_true", dest="output_json")

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a comment")
    p_delete.add_argument("--ticket", required=True, help="Ticket key")
    p_delete.add_argument("--comment-id", required=True, help="Comment ID to delete")

    args = parser.parse_args()
    _cli_credential_id = args.credential
    _cli_base_url = args.base_url

    handlers = {
        "add": cmd_add,
        "list": cmd_list,
        "edit": cmd_edit,
        "delete": cmd_delete,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
