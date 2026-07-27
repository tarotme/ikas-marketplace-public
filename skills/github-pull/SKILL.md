# github-pull / 拉取仓库代码

Pull the latest code for all git repositories under the workspace root using a GitHub credential from `<cwd>/.credentials/`.

使用 `<cwd>/.credentials/` 中的 GitHub 凭证，拉取工作区根目录下所有 git 仓库的最新代码。

## Trigger / 触发词

`pull`, `git pull`, `拉取代码`, `更新代码`, `sync repos`, `同步仓库`, `github-pull`

## Prerequisites / 前置条件

- Workspace `.credentials/` directory must contain a decrypted `ghc` type credential JSON file (managed by IKAS Workspace Manager)

工作区 `.credentials/` 目录中必须包含一个 `type: "ghc"` 且含 `token` 字段的凭证文件（由 IKAS Workspace Manager 管理）。

```json
{"id": "...", "type": "ghc", "token": "ghp_..."}
```

- Token must have access to the target repos / Token 需要对目标仓库有访问权限
- Workspace layout with repo directories (or symlinks) in cwd / 工作区 cwd 下有仓库目录（或软链接）

## Script / 脚本

`scripts/git_pull_repos.py` (relative to this skill directory)

The script discovers git repositories under `<cwd>` (directories or symlinks containing `.git`) and pulls each one. Dot-directories (e.g. `.credentials`, `.cursor`) are skipped.

脚本会自动发现 `<cwd>` 下的 git 仓库（含 `.git` 的目录或软链接）并逐一拉取。以点开头的目录（如 `.credentials`、`.cursor`）会被跳过。

## Usage / 使用方式

### Pull all repos / 拉取所有仓库

```bash
python3 .cursor/skills/marketplace/github-pull/scripts/git_pull_repos.py
```

### Pull a specific repo / 拉取指定仓库

```bash
python3 .cursor/skills/marketplace/github-pull/scripts/git_pull_repos.py --repo <repo-dir-name>
```

### Pull a specific branch / 拉取指定分支

```bash
python3 .cursor/skills/marketplace/github-pull/scripts/git_pull_repos.py --branch main
```

### JSON output / JSON 格式输出

```bash
python3 .cursor/skills/marketplace/github-pull/scripts/git_pull_repos.py --json
```

## When to Use / 何时使用

- At the start of a session, to sync workspace repositories / 会话开始时同步工作区仓库
- When remote repositories have been updated / 当远程仓库已更新时
- Before work that depends on the latest code in sibling repos / 在依赖同级仓库最新代码的工作之前
