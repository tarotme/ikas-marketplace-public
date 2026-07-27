---
description: Git 提交工作流强制标准 / Mandatory PR workflow
alwaysApply: true
---

# Git 工作流 / Git Workflow

## 强制标准 / Mandatory Rule

所有代码变更必须通过 Pull Request 合并到 main 分支，禁止直接推送 main。
All code changes MUST be merged into main via Pull Request. Direct push to main is forbidden.

流程 / Process：
1. 从 main 创建功能分支 / Create a feature branch from main
2. 在功能分支上提交改动 / Commit changes on the feature branch
3. 推送分支并创建 PR / Push branch and create a PR
4. 经用户确认后合并 / Merge after user confirmation

唯一例外：初始化空 repo 的第一次提交。
Only exception: the first commit when initializing an empty repo.

## 发版提交不豁免 / Release Commits Are Not Exempt

只改版本号的 `release: <version>` 提交同样是代码变更，必须走 `release/<version>` 分支加 PR。
A `release: <version>` commit that only bumps the version is still a code change; it MUST go
through a `release/<version>` branch and a PR.

```bash
git checkout -b release/<version>
git add package.json package-lock.json
git commit -m "release: <version>"
git push -u origin HEAD
gh pr create --title "release: <version>" --body "Version bump for <version>."
gh pr merge release/<version> --merge --delete-branch
git checkout main && git pull origin main
```

## 只有 tag 可以直接推送 / Only Tags May Be Pushed Directly

tag 不修改 main 分支，可以直接推送。打 tag 前先确保 PR 已合并、本地 main 已更新。
Tags do not modify main, so they may be pushed directly. Make sure the PR is merged and local
main is up to date first.

```bash
git checkout main && git pull origin main
git tag <version>
git push origin <version>
```

**禁止 `git push origin main --tags`**——它会把 main 一起推上去，等同于直推 main。
**Never use `git push origin main --tags`** — it pushes main along with the tags, which is a
direct push to main.
