# jira-comment / Jira 评论管理

Add, list, edit, and delete comments on Jira tickets via Jira Cloud REST API v3. Supports posting on behalf of another user.

通过 Jira Cloud REST API v3 对 Jira Ticket 进行评论的增删改查。支持代发评论（在正文中标注实际发言人）。

## Trigger / 触发词

`jira评论`, `jira comment`, `添加评论`, `jira留言`

## Prerequisites / 前置条件

- Python 3.6+ (standard library only, no external dependencies)
- Workspace `.credentials/` directory must contain a `type: "atlassian"` credential JSON file

工作区 `.credentials/` 目录中必须包含一个 `type: "atlassian"` 的凭证 JSON 文件。通过 `auth_mode` 区分两种认证模式：

**Classic — 个人 API Token (auth_mode="classic"):**
```json
{
  "type": "atlassian",
  "email": "you@example.com",
  "token": "ATATT3xFfGF0...",
  "auth_mode": "classic",
  "domain": "your-domain.atlassian.net",
  "base_url": "https://your-domain.atlassian.net"
}
```

**Scoped — Service Account (auth_mode="scoped"):**
```json
{
  "type": "atlassian",
  "email": "sa@serviceaccount.atlassian.com",
  "token": "ATATT3xFfGF0...",
  "auth_mode": "scoped",
  "cloud_id": "ef72da96-...",
  "base_url": "https://api.atlassian.com/ex/jira/<cloud-id>"
}
```

`base_url` 可省略（scoped 模式从 `cloud_id` 自动推导，classic 模式从 `domain` 推导）。`--base-url` CLI 参数可覆盖。

## Script / 脚本

`scripts/jira_comment.py` (relative to this skill directory)

## Commands / 命令

### Add a comment / 添加评论

```bash
python3 .cursor/skills/jira-comment/scripts/jira_comment.py add \
  --ticket PROJ-123 --body "This is fixed in commit abc123"
```

Read comment from stdin (for multi-line Markdown content):

```bash
cat <<'EOF' | python3 .cursor/skills/jira-comment/scripts/jira_comment.py add \
  --ticket PROJ-123 --body -
## Summary

- Fixed login timeout
- Added tests
EOF
```

### Add a comment on behalf of someone / 代发评论

```bash
python3 .cursor/skills/jira-comment/scripts/jira_comment.py add \
  --ticket PROJ-123 --body "I've reviewed the PR, looks good" \
  --on-behalf-of "Alice Wang"
```

Jira API does not allow changing the comment author. This option prepends a header line to the comment body indicating the actual author.

Jira API 不允许修改评论的 author。此选项会在评论正文前添加一行标注实际发言人。

Output in Jira will look like:

```
[On behalf of Alice Wang]
I've reviewed the PR, looks good
```

### List comments / 查看评论列表

```bash
python3 .cursor/skills/jira-comment/scripts/jira_comment.py list --ticket PROJ-123
```

### List with limit / 限制评论数量

```bash
python3 .cursor/skills/jira-comment/scripts/jira_comment.py list --ticket PROJ-123 --limit 5
```

### Edit a comment / 编辑评论

```bash
python3 .cursor/skills/jira-comment/scripts/jira_comment.py edit \
  --ticket PROJ-123 --comment-id 10234 --body "Updated comment text"
```

### Delete a comment / 删除评论

```bash
python3 .cursor/skills/jira-comment/scripts/jira_comment.py delete \
  --ticket PROJ-123 --comment-id 10234
```

### Select a specific credential / 选择指定凭证

```bash
python3 .cursor/skills/jira-comment/scripts/jira_comment.py --credential Jira-MyOwn add \
  --ticket PROJ-123 --body "My comment"
```

## Parameters / 参数

### Global / 全局参数

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--credential` | No / 否 | Credential ID to use (when multiple exist) / 凭证 ID |
| `--base-url` | No / 否 | Jira base URL (overrides credential file) / 覆盖 base URL |

### add

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--ticket` | Yes / 是 | Ticket key (e.g. PROJ-123) / Ticket 键值 |
| `--body` | Yes / 是 | Comment Markdown text, or `-` to read from stdin / 评论内容（支持 Markdown），`-` 从 stdin 读取 |
| `--on-behalf-of` | No / 否 | Actual author name (prepended to comment body) / 实际发言人姓名（标注在评论正文中） |
| `--json` | No / 否 | Output raw JSON response / 输出原始 JSON |

### list

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--ticket` | Yes / 是 | Ticket key / Ticket 键值 |
| `--limit` | No / 否 | Max comments to show, default all / 最多显示条数，默认全部 |
| `--json` | No / 否 | Output raw JSON / 输出原始 JSON |

### edit

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--ticket` | Yes / 是 | Ticket key / Ticket 键值 |
| `--comment-id` | Yes / 是 | Comment ID to edit / 评论 ID |
| `--body` | Yes / 是 | New comment Markdown, or `-` for stdin / 新评论内容（支持 Markdown），`-` 从 stdin 读取 |
| `--on-behalf-of` | No / 否 | Actual author name / 实际发言人姓名 |
| `--json` | No / 否 | Output raw JSON / 输出原始 JSON |

### delete

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--ticket` | Yes / 是 | Ticket key / Ticket 键值 |
| `--comment-id` | Yes / 是 | Comment ID to delete / 评论 ID |

## Output Formats / 输出格式

### add (text)

```
Comment added to PROJ-123 (id: 10234)
  On behalf of: Alice Wang
```

### list (text)

```
Comments on PROJ-123 (3):
  [10230] 2026-07-01 10:00 | Alice (alice@example.com)
    Looking into the DB connection pool issue...
  [10232] 2026-07-02 14:00 | Bob (bob@example.com)
    [On behalf of Carol]
    I've reviewed the fix, LGTM
  [10234] 2026-07-05 16:00 | Alice (alice@example.com)
    Fixed in commit abc123
```

### edit (text)

```
Comment 10234 updated on PROJ-123
```

### delete (text)

```
Comment 10234 deleted from PROJ-123
```

## Credential Format / 凭证格式

Same as `jira-ticket-check`. Create a JSON file in `.credentials/`:

与 `jira-ticket-check` 相同，在 `.credentials/` 目录下创建 JSON 文件：

| Field / 字段 | Required / 必填 | Description / 说明 |
|---|---|---|
| `type` | Yes / 是 | Must be `"atlassian"` / 必须为 `"atlassian"` |
| `email` | Yes / 是 | Atlassian account email / Atlassian 账号邮箱 |
| `token` | Yes / 是 | Jira API token / Jira API 令牌 |
| `auth_mode` | Yes / 是 | `"classic"` or `"scoped"` / 认证模式 |
| `base_url` | No / 否 | Auto-derived from `cloud_id` or `domain` / 可自动推导 |
| `domain` | No / 否 | Jira site domain (classic mode) / classic 模式的域名 |
| `cloud_id` | No / 否 | Atlassian Cloud site ID (scoped mode) / scoped 模式的 Cloud ID |

## Notes / 注意事项

- No external dependencies — uses Python standard library (`urllib`) only / 无需外部依赖
- Uses REST API v3 only — compatible with scoped tokens / 仅使用 REST API v3
- Jira Cloud API does not allow changing comment author; `--on-behalf-of` adds a text header as a workaround / Jira Cloud API 不允许修改评论作者，`--on-behalf-of` 通过正文标注作为替代方案
- Comments use Atlassian Document Format (ADF); common Markdown syntax is converted automatically / 评论自动转换为 ADF，支持常见 Markdown 语法
- Supported Markdown in `--body`: headings (`#`–`######`), bullet lists (`-`/`*`), numbered lists (`1.`), **bold**, *italic*, `code`, and `[text](url)` links / `--body` 支持的 Markdown：标题、无序/有序列表、加粗、斜体、行内代码、链接
- Use `--body -` to read long content from stdin / 用 `-` 从 stdin 读取长文本
- Use `list` command to find comment IDs for `edit` and `delete` / 用 `list` 命令获取评论 ID 后再 `edit` 或 `delete`
