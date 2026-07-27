#!/usr/bin/env python3
"""
Query Jira tickets and sprints via Jira Cloud REST API v3.

Usage:
    python3 jira_ticket_check.py get --ticket PROJ-123
    python3 jira_ticket_check.py search --jql "project = PROJ AND status = Open"
    python3 jira_ticket_check.py sprint --project PROJ
    python3 jira_ticket_check.py sprint --project PROJ --state active

Token is read from the credential JSON file in <workspace>/.credentials/ (token field).

Credential file: type="atlassian" JSON in .credentials/ with auth_mode "classic" or "scoped".
    Supports auth_mode="scoped" (cloud_id + base_url, token via env var)
    and classic mode (email + api_token/token + base_url in one file).

Authentication: Basic Auth (email:token) for Jira Cloud.
Uses only REST API v3 (no Agile API dependency).
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

_cli_base_url = None
_cli_credential_id = None

_ATLASSIAN_API_BASE = "https://api.atlassian.com/ex/jira"



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

    # Filter by --credential if specified
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
    }


def _api_request(base_url, email, api_token, path, params=None):
    url = base_url.rstrip("/") + path
    if params:
        url += "?" + urlencode(params)

    cred = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    req = Request(url, headers={
        "Authorization": f"Basic {cred}",
        "Accept": "application/json",
    })

    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            detail = json.loads(body)
            msgs = detail.get("errorMessages", [])
            errs = detail.get("errors", {})
            parts = msgs + [f"{k}: {v}" for k, v in errs.items()]
            msg = "; ".join(parts) if parts else body
        except (json.JSONDecodeError, AttributeError):
            msg = body
        print(f"Jira API error ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)


class JiraClient:
    def __init__(self):
        cred = _resolve_credential()
        self.base_url = cred["base_url"]
        self.email = cred["email"]
        self.api_token = cred["api_token"]

    def api(self, path, params=None):
        return _api_request(self.base_url, self.email, self.api_token, path, params)

    def search(self, jql, max_results=50, fields=None):
        params = {"jql": jql, "maxResults": max_results}
        if fields:
            params["fields"] = fields
        return self.api("/rest/api/3/search/jql", params)


_SPRINT_CUSTOM_FIELD = "customfield_10020"
# Roblox/Jira Software: board/UI usually shows "Story Points" (10024);
# "Story point estimate" (10016) is the GreenHopper field. Read both.
_STORY_POINTS_FIELDS = ("customfield_10024", "customfield_10016")

_SUMMARY_FIELDS = ",".join([
    "summary", "status", "priority", "assignee", "issuetype",
    "reporter", "labels", "created", "updated", "sprint",
    _SPRINT_CUSTOM_FIELD, "duedate",
] + list(_STORY_POINTS_FIELDS))

_DETAIL_FIELDS = _SUMMARY_FIELDS + ",description,comment"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_sprint_info(fields):
    """Extract the active/most-recent sprint from issue fields.
    Checks both the standard 'sprint' field and the common custom field."""
    sprint = fields.get("sprint")
    if sprint:
        return sprint
    cf = fields.get(_SPRINT_CUSTOM_FIELD)
    if isinstance(cf, list) and cf:
        active = [s for s in cf if s.get("state") == "active"]
        return active[0] if active else cf[-1]
    if isinstance(cf, dict):
        return cf
    return None


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _format_issue_summary(issue):
    fields = issue.get("fields", {})
    key = issue.get("key", issue.get("id", "?"))
    summary = fields.get("summary", "")
    status = fields.get("status", {}).get("name", "") if fields.get("status") else ""
    priority = fields.get("priority", {}).get("name", "") if fields.get("priority") else ""
    assignee = fields.get("assignee")
    assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"
    issue_type = fields.get("issuetype", {}).get("name", "") if fields.get("issuetype") else ""

    parts = [f"[{key}]"]
    if issue_type:
        parts.append(f"({issue_type})")
    parts.append(summary)
    tags = []
    if status:
        tags.append(status)
    if priority:
        tags.append(priority)
    tags.append(assignee_name)
    parts.append(f"  [{' | '.join(tags)}]")

    return " ".join(parts)


def _format_issue_detail(issue):
    fields = issue.get("fields", {})
    key = issue.get("key", issue.get("id", "?"))
    lines = [f"{'=' * 60}", f"  {key}: {fields.get('summary', '')}"]
    lines.append(f"{'=' * 60}")

    def _field(label, value):
        if value:
            lines.append(f"  {label:>14}: {value}")

    _field("Type", fields.get("issuetype", {}).get("name") if fields.get("issuetype") else None)
    _field("Status", fields.get("status", {}).get("name") if fields.get("status") else None)
    _field("Priority", fields.get("priority", {}).get("name") if fields.get("priority") else None)

    assignee = fields.get("assignee")
    _field("Assignee", assignee.get("displayName") if assignee else "Unassigned")

    reporter = fields.get("reporter")
    _field("Reporter", reporter.get("displayName") if reporter else None)

    if fields.get("labels"):
        _field("Labels", ", ".join(fields["labels"]))

    sprint_info = _get_sprint_info(fields)
    if sprint_info:
        _field("Sprint", sprint_info.get("name", ""))

    _field("Created", fields.get("created", "")[:19].replace("T", " "))
    _field("Updated", fields.get("updated", "")[:19].replace("T", " "))

    if fields.get("duedate"):
        _field("Due Date", fields["duedate"])

    story_points = fields.get("story_points")
    if story_points is None:
        for fid in _STORY_POINTS_FIELDS:
            if fields.get(fid) is not None:
                story_points = fields[fid]
                break
    if story_points is not None:
        _field("Story Points", str(story_points))

    desc = fields.get("description")
    if desc:
        lines.append("")
        lines.append("  Description:")
        desc_text = _extract_adf_text(desc) if isinstance(desc, dict) else str(desc)
        for dl in desc_text.splitlines():
            lines.append(f"    {dl}")

    comments = fields.get("comment", {}).get("comments", [])
    if comments:
        lines.append("")
        lines.append(f"  Comments ({len(comments)}):")
        for c in comments[-5:]:
            author = c.get("author", {}).get("displayName", "unknown")
            created = c.get("created", "")[:19].replace("T", " ")
            body = _extract_adf_text(c.get("body", "")) if isinstance(c.get("body"), dict) else str(c.get("body", ""))
            body_preview = body.replace("\n", " ")
            if len(body_preview) > 120:
                body_preview = body_preview[:117] + "..."
            lines.append(f"    [{created}] {author}: {body_preview}")

    lines.append("")
    return "\n".join(lines)


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


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_get(args):
    client = JiraClient()
    ticket = args.ticket.strip()
    data = client.api(f"/rest/api/3/issue/{quote(ticket)}", {"expand": "renderedFields"})

    if args.output_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(_format_issue_detail(data))


def cmd_search(args):
    client = JiraClient()
    data = client.search(args.jql, args.limit, _SUMMARY_FIELDS)

    total = data.get("total", len(data.get("issues", [])))
    issues = data.get("issues", [])

    if args.output_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not issues:
        print("No issues found.")
        return

    for issue in issues:
        print(_format_issue_summary(issue))
    shown = len(issues)
    suffix = "" if data.get("isLast", True) else " (more available)"
    print(f"\n{shown} of {total} issue(s){suffix}")


def cmd_sprint(args):
    client = JiraClient()

    state_map = {
        "active": "openSprints()",
        "future": "futureSprints()",
        "closed": "closedSprints()",
    }

    if args.state:
        sprint_filter = f"sprint in {state_map[args.state]}"
    else:
        sprint_filter = "sprint is not EMPTY"

    jql = f"project = {args.project} AND {sprint_filter} ORDER BY sprint ASC, status ASC"
    data = client.search(jql, args.limit, _SUMMARY_FIELDS)
    issues = data.get("issues", [])

    if args.output_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not issues:
        state_label = f" ({args.state})" if args.state else ""
        print(f"No sprint issues found for {args.project}{state_label}.")
        return

    sprints = {}
    for issue in issues:
        fields = issue.get("fields", {})
        sprint_info = _get_sprint_info(fields)
        sprint_name = sprint_info.get("name", "Unknown Sprint") if sprint_info else "No Sprint"
        sprint_state = sprint_info.get("state", "") if sprint_info else ""
        sprint_key = (sprint_name, sprint_state)
        sprints.setdefault(sprint_key, []).append(issue)

    for (name, state), group in sprints.items():
        state_tag = f" [{state}]" if state else ""
        print(f"\n--- {name}{state_tag} ({len(group)} issues) ---")
        for issue in group:
            print(f"  {_format_issue_summary(issue)}")

    total = data.get("total", len(issues))
    shown = len(issues)
    suffix = "" if data.get("isLast", True) else " (more available)"
    print(f"\n{len(sprints)} sprint(s), {shown} of {total} issue(s){suffix}")


def main():
    global _cli_base_url, _cli_credential_id

    parser = argparse.ArgumentParser(
        description="Query Jira tickets and sprints"
    )
    parser.add_argument("--credential", default=None,
                        help="Credential ID to use (when multiple Jira credentials exist)")
    parser.add_argument("--base-url", default=None,
                        help="Jira Cloud base URL (overrides credential file)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # get
    p_get = subparsers.add_parser("get", help="Get a specific ticket by key")
    p_get.add_argument("--ticket", required=True, help="Ticket key (e.g. PROJ-123)")
    p_get.add_argument("--json", action="store_true", dest="output_json")

    # search
    p_search = subparsers.add_parser("search", help="Search issues via JQL")
    p_search.add_argument("--jql", required=True, help="JQL query string")
    p_search.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    p_search.add_argument("--json", action="store_true", dest="output_json")

    # sprint
    p_sprint = subparsers.add_parser("sprint", help="List issues grouped by sprint")
    p_sprint.add_argument("--project", required=True, help="Project key (e.g. PROJ)")
    p_sprint.add_argument("--state", choices=["active", "future", "closed"],
                          help="Filter: active, future, or closed sprints")
    p_sprint.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")
    p_sprint.add_argument("--json", action="store_true", dest="output_json")

    args = parser.parse_args()
    _cli_credential_id = args.credential
    _cli_base_url = args.base_url

    handlers = {
        "get": cmd_get,
        "search": cmd_search,
        "sprint": cmd_sprint,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
