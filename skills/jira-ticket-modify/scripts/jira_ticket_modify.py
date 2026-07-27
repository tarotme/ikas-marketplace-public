#!/usr/bin/env python3
"""
Create, update, assign, transition, and comment on Jira tickets via REST API v3.

Usage:
    python3 jira_ticket_modify.py create --project PROJ --type Task --summary "Title"
    python3 jira_ticket_modify.py update --ticket PROJ-123 --summary "New title"
    python3 jira_ticket_modify.py assign --ticket PROJ-123 --assignee "user@example.com"
    python3 jira_ticket_modify.py transition --ticket PROJ-123 --to "In Progress"
    python3 jira_ticket_modify.py comment --ticket PROJ-123 --body "Fixed in abc123"
    python3 jira_ticket_modify.py label --ticket PROJ-123 --add "backend,urgent"

Token is read from the credential JSON file in <workspace>/.credentials/ (token field).

Credential file: type="atlassian" JSON in .credentials/ with auth_mode "classic" or "scoped".
Authentication: Basic Auth (email:token) for Jira Cloud.
Uses only REST API v3 (no Agile API dependency).
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
_SPRINT_FIELD = "customfield_10020"
# Jira often has TWO story-point fields. Writing only one makes points missing
# in the other view (board vs issue detail). Write both when present.
# - customfield_10024 = "Story Points" (usually issue UI / board estimate column)
# - customfield_10016 = "Story point estimate" (Jira Software / GreenHopper)
_STORY_POINTS_FIELDS = ("customfield_10024", "customfield_10016")
_STORY_POINTS_FIELD_NAMES = ("Story Points", "Story point estimate")


# ---------------------------------------------------------------------------
# Credential resolution (shared logic with jira-ticket-check)
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

    return {
        "id": data.get("id", f.stem),
        "email": email,
        "api_token": token,
        "base_url": base_url.rstrip("/"),
        "auth_mode": data.get("auth_mode", "classic"),
        "cloud_id": data.get("cloud_id"),
        "domain": data.get("domain"),
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
        self.domain = cred.get("domain")
        self._site_url = None

    def get(self, path, params=None):
        return _api_request(self.base_url, self.email, self.api_token, "GET", path, params)

    def post(self, path, body=None, params=None):
        return _api_request(self.base_url, self.email, self.api_token, "POST", path, params, body)

    def put(self, path, body=None, params=None):
        return _api_request(self.base_url, self.email, self.api_token, "PUT", path, params, body)

    def _resolve_site_url(self):
        if self._site_url:
            return self._site_url
        if self.domain:
            self._site_url = f"https://{self.domain}"
            return self._site_url
        try:
            info = self.get("/rest/api/3/serverInfo")
            self._site_url = info.get("baseUrl", "").rstrip("/")
        except SystemExit:
            self._site_url = self.base_url
        return self._site_url

    def browse_url(self, key):
        return f"{self._resolve_site_url()}/browse/{key}"


def _resolve_story_points_fields(client):
    """Return custom field IDs to write for story points.

    Discovers fields named "Story Points" / "Story point estimate" via
    /rest/api/3/field. Falls back to known default IDs. Returns a
    de-duplicated list so both UI and Agile estimate stay in sync.
    """
    discovered = []
    try:
        for f in client.get("/rest/api/3/field") or []:
            name = (f.get("name") or "").strip()
            if name in _STORY_POINTS_FIELD_NAMES:
                fid = f.get("id")
                if fid and fid not in discovered:
                    discovered.append(fid)
    except SystemExit:
        discovered = []

    if not discovered:
        return list(_STORY_POINTS_FIELDS)

    # Prefer canonical order (UI Story Points first), then any extras
    result = [fid for fid in _STORY_POINTS_FIELDS if fid in discovered]
    for fid in discovered:
        if fid not in result:
            result.append(fid)
    return result


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
# User lookup
# ---------------------------------------------------------------------------

def _resolve_user(client, user_input, ticket_key=None):
    """Resolve an email or display name to an accountId.
    If input looks like an accountId (no @ and long hex-like), return directly."""
    if not user_input:
        return None

    if len(user_input) > 20 and "@" not in user_input and " " not in user_input:
        return user_input

    if ticket_key:
        users = client.get(
            "/rest/api/3/user/assignable/search",
            {"query": user_input, "issueKey": ticket_key, "maxResults": 5},
        )
    else:
        users = client.get(
            "/rest/api/3/user/search",
            {"query": user_input, "maxResults": 5},
        )

    if not users:
        print(f"Error: no user found matching '{user_input}'", file=sys.stderr)
        sys.exit(1)

    exact = [u for u in users if u.get("emailAddress", "").lower() == user_input.lower()]
    if exact:
        return exact[0]["accountId"]

    return users[0]["accountId"]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_create(args):
    client = JiraClient()

    fields = {
        "project": {"key": args.project},
        "issuetype": {"name": args.type},
        "summary": args.summary,
    }

    if args.description:
        text = _resolve_text(args.description)
        fields["description"] = _text_to_adf(text)

    if args.priority:
        fields["priority"] = {"name": args.priority}

    if args.labels:
        fields["labels"] = [l.strip() for l in args.labels.split(",") if l.strip()]

    if args.assignee:
        account_id = _resolve_user(client, args.assignee)
        fields["assignee"] = {"accountId": account_id}

    if args.reporter:
        account_id = _resolve_user(client, args.reporter)
        fields["reporter"] = {"accountId": account_id}

    if args.parent:
        fields["parent"] = {"key": args.parent}

    body = {"fields": fields}
    result = client.post("/rest/api/3/issue", body)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        key = result.get("key", result.get("id", "?"))
        print(f"Created: {key} — {args.summary}")
        print(f"URL: {client.browse_url(key)}")


def cmd_update(args):
    client = JiraClient()
    ticket = args.ticket.strip()

    fields = {}
    updated = []

    if args.summary:
        fields["summary"] = args.summary
        updated.append(f'  summary: "{args.summary}"')

    if args.description:
        text = _resolve_text(args.description)
        fields["description"] = _text_to_adf(text)
        preview = text[:60].replace("\n", " ")
        updated.append(f'  description: "{preview}..."' if len(text) > 60 else f'  description: "{preview}"')

    if args.priority:
        fields["priority"] = {"name": args.priority}
        updated.append(f'  priority: "{args.priority}"')

    if args.labels is not None:
        labels = [l.strip() for l in args.labels.split(",") if l.strip()] if args.labels else []
        fields["labels"] = labels
        updated.append(f'  labels: {labels}')

    if args.assignee:
        account_id = _resolve_user(client, args.assignee, ticket)
        fields["assignee"] = {"accountId": account_id}
        updated.append(f'  assignee: "{args.assignee}"')

    if args.reporter:
        account_id = _resolve_user(client, args.reporter)
        fields["reporter"] = {"accountId": account_id}
        updated.append(f'  reporter: "{args.reporter}"')

    if args.sprint is not None:
        if args.sprint == "" or args.sprint.lower() == "none":
            fields[_SPRINT_FIELD] = None
            updated.append("  sprint: (removed)")
        else:
            try:
                sprint_id = int(args.sprint)
            except ValueError:
                print(f"Error: --sprint must be a numeric sprint ID, got '{args.sprint}'", file=sys.stderr)
                sys.exit(1)
            fields[_SPRINT_FIELD] = sprint_id
            updated.append(f"  sprint: {sprint_id}")

    if args.story_points is not None:
        if args.story_points == "" or args.story_points.lower() == "none":
            value = None
            updated.append("  story_points: (removed)")
        else:
            try:
                value = float(args.story_points)
            except ValueError:
                print(f"Error: --story-points must be numeric, got '{args.story_points}'", file=sys.stderr)
                sys.exit(1)
            updated.append(f"  story_points: {value}")
        # Write to ALL story-point fields so board UI and issue detail stay in sync
        for fid in _resolve_story_points_fields(client):
            fields[fid] = value
            updated.append(f"  {fid}: {value if value is not None else '(removed)'}")

    if not fields:
        print("Error: no fields to update. Provide at least one of: --summary, --description, --priority, --labels, --assignee, --reporter, --sprint, --story-points",
              file=sys.stderr)
        sys.exit(1)

    body = {"fields": fields}
    result = client.put(f"/rest/api/3/issue/{quote(ticket)}", body)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Updated: {ticket}")
        for line in updated:
            print(line)


def cmd_assign(args):
    client = JiraClient()
    ticket = args.ticket.strip()

    if args.unassign:
        body = {"accountId": None}
        client.put(f"/rest/api/3/issue/{quote(ticket)}/assignee", body)
        print(f"Unassigned: {ticket}")
    elif args.assignee:
        account_id = _resolve_user(client, args.assignee, ticket)
        body = {"accountId": account_id}
        client.put(f"/rest/api/3/issue/{quote(ticket)}/assignee", body)
        print(f"Assigned: {ticket} → {args.assignee}")
    else:
        print("Error: provide --assignee or --unassign", file=sys.stderr)
        sys.exit(1)


def cmd_transition(args):
    client = JiraClient()
    ticket = args.ticket.strip()

    transitions = client.get(f"/rest/api/3/issue/{quote(ticket)}/transitions")
    available = transitions.get("transitions", [])

    if args.list:
        issue = client.get(f"/rest/api/3/issue/{quote(ticket)}", {"fields": "status"})
        current = issue.get("fields", {}).get("status", {}).get("name", "?")

        if args.output_json:
            print(json.dumps({"current_status": current, "transitions": available}, ensure_ascii=False, indent=2))
            return

        print(f"Available transitions for {ticket} (current: {current}):")
        if not available:
            print("  (none)")
        for t in available:
            print(f"  [{t['id']}] {t['name']}")
        return

    if not args.to:
        print("Error: provide --to <status> or --list", file=sys.stderr)
        sys.exit(1)

    target = args.to.lower()
    match = None
    for t in available:
        if t["name"].lower() == target:
            match = t
            break
    if not match:
        for t in available:
            if target in t["name"].lower():
                match = t
                break

    if not match:
        names = [t["name"] for t in available]
        print(
            f"Error: transition '{args.to}' not found for {ticket}.\n"
            f"Available: {', '.join(names)}",
            file=sys.stderr,
        )
        sys.exit(1)

    body = {"transition": {"id": match["id"]}}
    client.post(f"/rest/api/3/issue/{quote(ticket)}/transitions", body)

    if args.output_json:
        print(json.dumps({"ticket": ticket, "transition": match["name"], "id": match["id"]}, ensure_ascii=False, indent=2))
    else:
        print(f"Transitioned: {ticket} → {match['name']}")


def cmd_label(args):
    client = JiraClient()
    ticket = args.ticket.strip()

    update_ops = []

    if args.add:
        for label in args.add.split(","):
            label = label.strip()
            if label:
                update_ops.append({"add": label})

    if args.remove:
        for label in args.remove.split(","):
            label = label.strip()
            if label:
                update_ops.append({"remove": label})

    if not update_ops:
        print("Error: provide --add and/or --remove", file=sys.stderr)
        sys.exit(1)

    body = {"update": {"labels": update_ops}}
    client.put(f"/rest/api/3/issue/{quote(ticket)}", body)

    issue = client.get(f"/rest/api/3/issue/{quote(ticket)}", {"fields": "labels"})
    current_labels = issue.get("fields", {}).get("labels", [])
    print(f"Labels updated on {ticket}: {', '.join(current_labels) if current_labels else '(none)'}")


def cmd_link(args):
    client = JiraClient()
    ticket = args.ticket.strip()
    target = args.target.strip()
    link_type = args.type or "Relates"

    if args.list_types:
        data = client.get("/rest/api/3/issueLinkType")
        types = data.get("issueLinkTypes", [])
        if args.output_json:
            print(json.dumps(types, ensure_ascii=False, indent=2))
        else:
            print("Available issue link types:")
            for t in types:
                print(f"  {t['name']}  (inward: {t['inward']}, outward: {t['outward']})")
        return

    body = {
        "type": {"name": link_type},
        "inwardIssue": {"key": target},
        "outwardIssue": {"key": ticket},
    }
    client.post("/rest/api/3/issueLink", body)
    print(f"Linked: {ticket} —[{link_type}]→ {target}")


def cmd_weblink(args):
    client = JiraClient()
    ticket = args.ticket.strip()

    obj = {"url": args.url}
    if args.title:
        obj["title"] = args.title

    body = {"object": obj}
    result = client.post(f"/rest/api/3/issue/{quote(ticket)}/remotelink", body)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        link_id = result.get("id", "?")
        title_str = f" ({args.title})" if args.title else ""
        print(f"Web link added to {ticket} (id: {link_id}){title_str}")
        print(f"  URL: {args.url}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global _cli_base_url, _cli_credential_id

    parser = argparse.ArgumentParser(description="Create and modify Jira tickets")
    parser.add_argument("--credential", default=None,
                        help="Credential ID to use (when multiple Jira credentials exist)")
    parser.add_argument("--base-url", default=None,
                        help="Jira Cloud base URL (overrides credential file)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = subparsers.add_parser("create", help="Create a new ticket")
    p_create.add_argument("--project", required=True, help="Project key (e.g. PROJ)")
    p_create.add_argument("--type", required=True, help="Issue type: Task, Bug, Story, Epic, etc.")
    p_create.add_argument("--summary", required=True, help="Issue title")
    p_create.add_argument("--description", default=None, help="Description text, or '-' for stdin")
    p_create.add_argument("--priority", default=None, help="Priority: Highest, High, Medium, Low, Lowest")
    p_create.add_argument("--labels", default=None, help="Comma-separated labels")
    p_create.add_argument("--assignee", default=None, help="Assignee email or accountId")
    p_create.add_argument("--reporter", default=None, help="Reporter email or accountId")
    p_create.add_argument("--parent", default=None, help="Parent ticket key (for sub-tasks)")
    p_create.add_argument("--json", action="store_true", dest="output_json")

    # update
    p_update = subparsers.add_parser("update", help="Update ticket fields")
    p_update.add_argument("--ticket", required=True, help="Ticket key (e.g. PROJ-123)")
    p_update.add_argument("--summary", default=None, help="New summary")
    p_update.add_argument("--description", default=None, help="New description, or '-' for stdin")
    p_update.add_argument("--priority", default=None, help="New priority")
    p_update.add_argument("--labels", default=None, help="Replace all labels (comma-separated)")
    p_update.add_argument("--assignee", default=None, help="New assignee email or accountId")
    p_update.add_argument("--reporter", default=None, help="New reporter email or accountId")
    p_update.add_argument("--sprint", default=None, help="Sprint ID to move issue to, or 'none' to remove")
    p_update.add_argument("--story-points", default=None, help="Story points (numeric), or 'none' to clear")
    p_update.add_argument("--json", action="store_true", dest="output_json")

    # assign
    p_assign = subparsers.add_parser("assign", help="Assign or unassign a ticket")
    p_assign.add_argument("--ticket", required=True, help="Ticket key")
    p_assign.add_argument("--assignee", default=None, help="Assignee email or accountId")
    p_assign.add_argument("--unassign", action="store_true", help="Remove assignee")

    # transition
    p_trans = subparsers.add_parser("transition", help="Change ticket status")
    p_trans.add_argument("--ticket", required=True, help="Ticket key")
    p_trans.add_argument("--list", action="store_true", help="List available transitions")
    p_trans.add_argument("--to", default=None, help="Target status name")
    p_trans.add_argument("--json", action="store_true", dest="output_json")

    # label
    p_label = subparsers.add_parser("label", help="Add or remove labels")
    p_label.add_argument("--ticket", required=True, help="Ticket key")
    p_label.add_argument("--add", default=None, help="Comma-separated labels to add")
    p_label.add_argument("--remove", default=None, help="Comma-separated labels to remove")

    # link
    p_link = subparsers.add_parser("link", help="Link two issues together")
    p_link.add_argument("--ticket", required=True, help="Source ticket key")
    p_link.add_argument("--target", required=True, help="Target ticket key to link to")
    p_link.add_argument("--type", default=None, help="Link type name (default: Relates)")
    p_link.add_argument("--list-types", action="store_true", help="List available link types")
    p_link.add_argument("--json", action="store_true", dest="output_json")

    # weblink
    p_weblink = subparsers.add_parser("weblink", help="Add a web link to a ticket")
    p_weblink.add_argument("--ticket", required=True, help="Ticket key")
    p_weblink.add_argument("--url", required=True, help="URL to link")
    p_weblink.add_argument("--title", default=None, help="Link title/description")
    p_weblink.add_argument("--json", action="store_true", dest="output_json")

    args = parser.parse_args()
    _cli_credential_id = args.credential
    _cli_base_url = args.base_url

    handlers = {
        "create": cmd_create,
        "update": cmd_update,
        "assign": cmd_assign,
        "transition": cmd_transition,
        "label": cmd_label,
        "link": cmd_link,
        "weblink": cmd_weblink,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
