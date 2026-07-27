#!/usr/bin/env python3
"""
Pull latest code for all git repositories under the workspace root.

Usage:
    python3 git_pull_repos.py
    python3 git_pull_repos.py --repo my-repo
    python3 git_pull_repos.py --branch main

Credential resolution:
    Reads decrypted ghc credential from <cwd>/.credentials/ directory.
    {"id": "...", "type": "ghc", "token": "ghp_..."}

Discovers directories (or symlinks) under <cwd> that contain a .git directory.
Dot-directories such as .credentials and .cursor are skipped.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def load_token():
    cred_dir = Path(os.getcwd()) / ".credentials"
    if not cred_dir.is_dir():
        print(f"Error: .credentials/ directory not found in workspace root: {cred_dir}", file=sys.stderr)
        sys.exit(1)

    for f in cred_dir.glob("*.json"):
        try:
            with open(f) as fh:
                data = json.load(fh)
            if data.get("type") == "ghc" and "token" in data:
                return data["token"]
        except (json.JSONDecodeError, KeyError, OSError):
            continue

    print("Error: no ghc credential found in .credentials/", file=sys.stderr)
    sys.exit(1)


def remote_to_slug(remote_url):
    """Extract org/repo slug from a GitHub remote URL."""
    url = remote_url.strip()
    # Strip credentials from https://user:token@host/...
    url = re.sub(r"https?://[^@]+@", "https://", url)
    url = re.sub(r"^git@", "https://", url)
    url = url.replace("github.com:", "github.com/")
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not match:
        return None
    return f"{match.group(1)}/{match.group(2)}"


def get_origin_url(repo_path):
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def discover_repos():
    """Return {dir_name: github_slug} for git repos under cwd."""
    cwd = Path(os.getcwd())
    repos = {}
    for entry in sorted(cwd.iterdir()):
        if entry.name.startswith("."):
            continue
        real_path = entry.resolve()
        if not (real_path / ".git").exists():
            continue
        remote = get_origin_url(real_path)
        if not remote:
            print(f"  SKIP [{entry.name}] - no origin remote", file=sys.stderr)
            continue
        slug = remote_to_slug(remote)
        if not slug:
            print(f"  SKIP [{entry.name}] - not a GitHub remote: {remote}", file=sys.stderr)
            continue
        repos[entry.name] = slug
    return repos


def pull_repo(name, slug, token, branch=None):
    repo_path = os.path.join(os.getcwd(), name)
    if not os.path.exists(repo_path):
        print(f"  SKIP - path not found: {repo_path}")
        return False

    real_path = os.path.realpath(repo_path)
    auth_url = f"https://x-access-token:{token}@github.com/{slug}.git"

    cmd = ["git", "pull", auth_url]
    if branch:
        cmd.append(branch)

    result = subprocess.run(cmd, cwd=real_path, capture_output=True, text=True)

    if result.returncode == 0:
        output = result.stdout.strip() or "up to date"
        print(f"  OK - {output.splitlines()[0]}")
        return True
    else:
        error = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown error"
        print(f"  FAILED - {error}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Pull latest code for workspace repos")
    parser.add_argument("--repo", default=None,
                        help="Pull a specific repo directory only / 仅拉取指定仓库目录")
    parser.add_argument("--branch", default=None,
                        help="Branch to pull (default: current branch's upstream) / 拉取的分支")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON / JSON 格式输出")
    args = parser.parse_args()

    token = load_token()
    repos = discover_repos()

    if not repos:
        print("Error: no git repositories found under workspace root", file=sys.stderr)
        sys.exit(1)

    if args.repo:
        if args.repo not in repos:
            print(f"Error: repo not found or not a GitHub git repo: {args.repo}", file=sys.stderr)
            print(f"Available: {', '.join(repos.keys())}", file=sys.stderr)
            sys.exit(1)
        targets = {args.repo: repos[args.repo]}
    else:
        targets = repos

    results = {}

    for name, slug in targets.items():
        print(f"[{name}]")
        success = pull_repo(name, slug, token, branch=args.branch)
        results[name] = "ok" if success else "failed"

    if args.json:
        print(json.dumps(results, indent=2))

    if any(v == "failed" for v in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
