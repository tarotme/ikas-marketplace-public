#!/usr/bin/env python3
"""Post execution results back to IKAS Trigger async request endpoint."""

import argparse
import json
import os
import sys
import glob

try:
    import requests
except ImportError:
    print("Error: 'requests' package not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)


def discover_trigger_url(cwd: str) -> str | None:
    """Auto-discover trigger URL from .credentials/ directory."""
    creds_dir = os.path.join(cwd, ".credentials")
    if not os.path.isdir(creds_dir):
        return None
    for f in glob.glob(os.path.join(creds_dir, "*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
            url = data.get("trigger_url") or data.get("url")
            if url:
                return url.rstrip("/").rsplit("/api", 1)[0]
        except (json.JSONDecodeError, IOError):
            continue
    return None


def resolve_base_url(args_url: str | None) -> str:
    """Resolve base URL from args, env, or credential discovery."""
    if args_url:
        return args_url.rstrip("/")
    env_url = os.environ.get("TRIGGER_URL")
    if env_url:
        return env_url.rstrip("/").rsplit("/api", 1)[0]
    discovered = discover_trigger_url(os.getcwd())
    if discovered:
        return discovered
    print("Error: Cannot determine trigger URL. Use --url, set TRIGGER_URL, or place credentials in .credentials/", file=sys.stderr)
    sys.exit(1)


def cmd_post(args):
    """Post result to the request endpoint."""
    base_url = resolve_base_url(args.url)
    endpoint = f"{base_url}/api/requests/{args.request_id}/result"

    payload = {}
    if args.result:
        payload["result"] = args.result
    if args.status:
        payload["status"] = args.status
    if args.error:
        payload["error"] = args.error
        if not args.status:
            payload["status"] = "error"

    headers = {"Content-Type": "application/json"}
    if args.api_key:
        headers["X-Api-Key"] = args.api_key
    else:
        payload["api_key"] = args.api_key or ""

    resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
    try:
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(f"HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code >= 400:
        sys.exit(1)


def cmd_query(args):
    """Query request status."""
    base_url = resolve_base_url(args.url)
    endpoint = f"{base_url}/api/requests/{args.request_id}"

    headers = {}
    params = {}
    if args.api_key:
        headers["X-Api-Key"] = args.api_key
    else:
        params["api_key"] = args.api_key or ""

    resp = requests.get(endpoint, headers=headers, params=params, timeout=30)
    try:
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(f"HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code >= 400:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="IKAS Trigger - Post request result")
    subparsers = parser.add_subparsers(dest="command")

    # Default command (post)
    parser.add_argument("--url", help="Trigger server base URL")
    parser.add_argument("--api-key", dest="api_key", help="API Key for authentication")
    parser.add_argument("--request-id", dest="request_id", help="Request ID")
    parser.add_argument("--result", help="Result content")
    parser.add_argument("--status", choices=["completed", "error"], default="completed", help="Result status")
    parser.add_argument("--error", help="Error message")

    # Query subcommand
    query_parser = subparsers.add_parser("query", help="Query request status")
    query_parser.add_argument("--url", help="Trigger server base URL")
    query_parser.add_argument("--api-key", dest="api_key", help="API Key for authentication")
    query_parser.add_argument("--request-id", dest="request_id", help="Request ID")

    args = parser.parse_args()

    if args.command == "query":
        if not args.request_id:
            print("Error: --request-id is required", file=sys.stderr)
            sys.exit(1)
        cmd_query(args)
    else:
        if not args.request_id:
            print("Error: --request-id is required", file=sys.stderr)
            sys.exit(1)
        cmd_post(args)


if __name__ == "__main__":
    main()
