#!/usr/bin/env python3
"""Query the status and result of an async request from IKAS Trigger."""

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


def main():
    parser = argparse.ArgumentParser(description="IKAS Trigger - Query async request result")
    parser.add_argument("--url", help="Trigger server base URL")
    parser.add_argument("--api-key", dest="api_key", required=True, help="API Key for authentication")
    parser.add_argument("--request-id", dest="request_id", required=True, help="Request ID to query")

    args = parser.parse_args()

    base_url = resolve_base_url(args.url)
    endpoint = f"{base_url}/api/requests/{args.request_id}"

    headers = {"X-Api-Key": args.api_key}

    resp = requests.get(endpoint, headers=headers, timeout=30)
    try:
        data = resp.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        print(f"HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code >= 400:
        sys.exit(1)


if __name__ == "__main__":
    main()
