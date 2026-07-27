# jira-ticket-modify / 修改 Jira Ticket

Create, update, assign, transition, and comment on Jira tickets via Jira Cloud REST API v3.

通过 Jira Cloud REST API v3 创建、修改、分配、状态变更和评论 Jira Ticket。

## Trigger / 触发词

`jira创建`, `jira修改`, `jira分配`, `创建工单`, `修改工单`, `jira create`, `jira update`, `jira assign`

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

- Generate API token at: https://id.atlassian.com/manage-profile/security/api-tokens

## Script / 脚本

`scripts/jira_ticket_modify.py` (relative to this skill directory)

## Commands / 命令

### Create a ticket / 创建 Ticket

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py create \
  --project PROJ --type Task --summary "Implement feature X"
```

With description and other fields:

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py create \
  --project PROJ --type Bug --summary "Login timeout" \
  --description "Users report timeout when logging in" \
  --priority High --labels "backend,urgent" --assignee "alice@example.com"
```

Read description from stdin (for multi-line Markdown content):

```bash
cat <<'EOF' | python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py create \
  --project PROJ --type Task --summary "My task" --description -
## Goal

Implement feature X.

- First step
- Second step
EOF
```

### Update ticket fields / 修改 Ticket 字段

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py update \
  --ticket PROJ-123 --summary "Updated title" --priority Medium
```

Update description from stdin:

```bash
echo "New description" | python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py update \
  --ticket PROJ-123 --description -
```

### Assign a ticket / 分配 Ticket

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py assign \
  --ticket PROJ-123 --assignee "alice@example.com"
```

Unassign:

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py assign \
  --ticket PROJ-123 --unassign
```

### Transition ticket status / 变更 Ticket 状态

List available transitions:

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py transition \
  --ticket PROJ-123 --list
```

Apply a transition:

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py transition \
  --ticket PROJ-123 --to "In Progress"
```

### Add labels / 添加标签

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py label \
  --ticket PROJ-123 --add "backend,urgent"
```

### Remove labels / 移除标签

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py label \
  --ticket PROJ-123 --remove "obsolete"
```

### Link to another ticket / 关联其他 Ticket

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py link \
  --ticket PROJ-123 --target PROJ-456
```

With specific link type:

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py link \
  --ticket PROJ-123 --target PROJ-456 --type "Blocks"
```

List available link types:

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py link \
  --ticket PROJ-123 --target PROJ-123 --list-types
```

### Add a web link / 添加 Web 链接

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py weblink \
  --ticket PROJ-123 --url "https://github.com/org/repo/pull/42" --title "Fix PR"
```

### Update sprint / 关联 Sprint

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py update \
  --ticket PROJ-123 --sprint 19999
```

Remove from sprint:

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py update \
  --ticket PROJ-123 --sprint none
```

### Update story points / 修改 Story Points

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py update \
  --ticket PROJ-123 --story-points 5
```

Fractional values are supported (e.g. `1.5`, `2.5`).

支持小数（如 `1.5`、`2.5`）。

**Important / 重要:** Many Jira sites (including Roblox) have **two** story-point fields. This skill writes to **both** so the board/UI and issue detail stay in sync:

许多 Jira 站点（含 Roblox）有**两个** Story Points 字段。本 skill 会**同时写入两者**，保证看板/UI 与详情页一致：

| Field Name / 字段名 | Default ID | Typical use / 典型用途 |
|---|---|---|
| Story Points | `customfield_10024` | Issue detail UI / board estimate column / 详情页与看板估算列 |
| Story point estimate | `customfield_10016` | Jira Software (GreenHopper) estimate / 敏捷估算字段 |

After setting points, verify the value appears in the UI (field `customfield_10024`). Writing only `customfield_10016` can look like "points not set".

设置后请在 UI 核对 `customfield_10024` 是否有值；只写 `customfield_10016` 时页面上可能仍显示为空。

### Select a specific credential / 选择指定凭证

```bash
python3 .cursor/skills/jira-ticket-modify/scripts/jira_ticket_modify.py --credential Jira-MyOwn create \
  --project PROJ --type Task --summary "My task"
```

## Parameters / 参数

### Global / 全局参数

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--credential` | No / 否 | Credential ID to use (when multiple exist) / 凭证 ID |
| `--base-url` | No / 否 | Jira base URL (overrides credential file) / 覆盖 base URL |

### create

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--project` | Yes / 是 | Project key (e.g. PROJ) / 项目键值 |
| `--type` | Yes / 是 | Issue type: Task, Bug, Story, Epic, etc. / 工单类型 |
| `--summary` | Yes / 是 | Issue title / 工单标题 |
| `--description` | No / 否 | Description Markdown text, or `-` to read from stdin / 描述（支持 Markdown），`-` 从 stdin 读取 |
| `--priority` | No / 否 | Priority: Highest, High, Medium, Low, Lowest / 优先级 |
| `--labels` | No / 否 | Comma-separated labels / 逗号分隔的标签 |
| `--assignee` | No / 否 | Assignee email or accountId / 负责人邮箱或 accountId |
| `--reporter` | No / 否 | Reporter email or accountId / 报告人邮箱或 accountId |
| `--parent` | No / 否 | Parent ticket key (for sub-tasks) / 父工单键值 |
| `--json` | No / 否 | Output raw JSON response / 输出原始 JSON |

### update

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--ticket` | Yes / 是 | Ticket key (e.g. PROJ-123) / Ticket 键值 |
| `--summary` | No / 否 | New summary / 新标题 |
| `--description` | No / 否 | New description Markdown, or `-` for stdin / 新描述（支持 Markdown），`-` 从 stdin 读取 |
| `--priority` | No / 否 | New priority / 新优先级 |
| `--labels` | No / 否 | Replace labels (comma-separated) / 替换标签 |
| `--assignee` | No / 否 | New assignee email or accountId / 新负责人 |
| `--reporter` | No / 否 | New reporter email or accountId (requires "Modify Reporter" permission) / 新报告人（需要"修改报告人"权限） |
| `--sprint` | No / 否 | Sprint ID to move issue to, or `none` to remove / Sprint ID，`none` 移除 |
| `--story-points` | No / 否 | Story points (numeric, fractions OK), or `none` to clear — writes **all** Story Points fields / Story Points（支持小数），`none` 清除；会写入**全部** Story Points 字段 |
| `--json` | No / 否 | Output raw JSON response / 输出原始 JSON |

### assign

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--ticket` | Yes / 是 | Ticket key / Ticket 键值 |
| `--assignee` | No* | Assignee email or accountId / 负责人（与 --unassign 二选一） |
| `--unassign` | No* | Remove assignee / 取消分配 |

### transition

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--ticket` | Yes / 是 | Ticket key / Ticket 键值 |
| `--list` | No* | List available transitions / 列出可用状态变更 |
| `--to` | No* | Target status name / 目标状态名称（与 --list 二选一） |
| `--json` | No / 否 | Output raw JSON / 输出原始 JSON |

### label

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--ticket` | Yes / 是 | Ticket key / Ticket 键值 |
| `--add` | No* | Comma-separated labels to add / 逗号分隔，添加标签 |
| `--remove` | No* | Comma-separated labels to remove / 逗号分隔，移除标签 |

### link

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--ticket` | Yes / 是 | Source ticket key / 源 Ticket 键值 |
| `--target` | Yes / 是 | Target ticket key / 目标 Ticket 键值 |
| `--type` | No / 否 | Link type name, default "Relates" / 关联类型，默认 "Relates" |
| `--list-types` | No / 否 | List available link types / 列出可用关联类型 |
| `--json` | No / 否 | Output raw JSON / 输出原始 JSON |

### weblink

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--ticket` | Yes / 是 | Ticket key / Ticket 键值 |
| `--url` | Yes / 是 | URL to link / 要关联的 URL |
| `--title` | No / 否 | Link title / 链接标题 |
| `--json` | No / 否 | Output raw JSON / 输出原始 JSON |

## Output Formats / 输出格式

### create (text)

```
Created: PROJ-456 — Implement feature X
URL: https://your-domain.atlassian.net/browse/PROJ-456
```

### update (text)

```
Updated: PROJ-123
  summary: "Updated title"
  priority: "Medium"
```

### assign (text)

```
Assigned: PROJ-123 → Alice (alice@example.com)
```

### transition (--list)

```
Available transitions for PROJ-123 (current: Open):
  [11] In Progress
  [21] Done
  [31] Closed
```

### transition (--to)

```
Transitioned: PROJ-123 → In Progress
```

### label (text)

```
Labels updated on PROJ-123: backend, urgent
```

### link (text)

```
Linked: PROJ-123 —[Relates]→ PROJ-456
```

### weblink (text)

```
Web link added to PROJ-123 (id: 351240) (Fix PR)
  URL: https://github.com/org/repo/pull/42
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
- Authentication uses HTTP Basic Auth (email:token) / 使用 HTTP Basic Auth 认证
- Description uses Atlassian Document Format (ADF); common Markdown syntax is converted automatically / 描述自动转换为 ADF，支持常见 Markdown 语法
- Supported Markdown in `--description`: headings (`#`–`######`), bullet lists (`-`/`*`), numbered lists (`1.`), **bold**, *italic*, `code`, and `[text](url)` links / `--description` 支持的 Markdown：标题、无序/有序列表、加粗、斜体、行内代码、链接
- Assignee and reporter can be specified by email (auto-resolved to accountId) or accountId directly / 负责人和报告人可用邮箱或 accountId
- Use `--description -` to read long content from stdin / 用 `-` 从 stdin 读取长文本
- For comment operations, use the `jira-comment` skill / 评论相关操作请使用 `jira-comment` 技能
- `--story-points` writes to **both** `Story Points` and `Story point estimate` fields (auto-discovered by name, defaults `customfield_10024` + `customfield_10016`) / `--story-points` 同时写入两个 Story Points 相关字段（按名称自动发现，默认 `customfield_10024` + `customfield_10016`）
- Service-account tokens: `currentUser()` in JQL does **not** resolve to a human; use display name or accountId / 服务账号下 JQL 的 `currentUser()` 不会对到真人，请用显示名或 accountId
- Sprint ID for `--sprint` comes from issue sprint JSON (`customfield_10020[].id`), not the sprint name / `--sprint` 需要 Sprint 数字 ID（来自 `customfield_10020[].id`），不是 Sprint 名称
