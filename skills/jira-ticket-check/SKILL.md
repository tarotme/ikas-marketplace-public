# jira-ticket-check / 查询 Jira Ticket 与 Sprint

Query Jira tickets and sprint information via Jira Cloud REST API v3 using scoped token (email + API token).

通过 Jira Cloud REST API v3 查询 Jira ticket 和 Sprint 信息，使用 scoped token（email + API token）认证。

## Trigger / 触发词

`jira`, `ticket`, `sprint`, `工单`, `jira查询`

## Prerequisites / 前置条件

- Python 3.6+ (standard library only, no external dependencies)
- Workspace `.credentials/` directory must contain a Jira/Atlassian credential JSON file

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

`base_url` can be auto-derived from `cloud_id` (scoped) or `domain` (classic) if omitted. The `--base-url` CLI flag overrides all.

`base_url` 可省略（scoped 模式从 `cloud_id` 自动推导，classic 模式从 `domain` 推导）。`--base-url` CLI 参数可覆盖。

- Generate API token at: https://id.atlassian.com/manage-profile/security/api-tokens

## Script / 脚本

`scripts/jira_ticket_check.py` (relative to this skill directory)

## Commands / 命令

### Get a specific ticket / 查看指定 Ticket

```bash
python3 .cursor/skills/jira-ticket-check/scripts/jira_ticket_check.py get --ticket PROJ-123
```

Shows full detail: type, status, priority, assignee, sprint, description, latest comments.

显示完整详情：类型、状态、优先级、负责人、Sprint、描述、最近评论。

### Search tickets via JQL / 通过 JQL 搜索 Ticket

```bash
python3 .cursor/skills/jira-ticket-check/scripts/jira_ticket_check.py search --jql "project = PROJ AND status = 'In Progress'"
```

### Search with result limit / 限制搜索结果数量

```bash
python3 .cursor/skills/jira-ticket-check/scripts/jira_ticket_check.py search --jql "assignee = currentUser() ORDER BY updated DESC" --limit 10
```

### List sprint issues / 查看 Sprint 中的 Ticket

```bash
python3 .cursor/skills/jira-ticket-check/scripts/jira_ticket_check.py sprint --project PROJ
```

### List active sprint issues only / 仅查看活跃 Sprint

```bash
python3 .cursor/skills/jira-ticket-check/scripts/jira_ticket_check.py sprint --project PROJ --state active
```

### Select a specific credential / 选择指定凭证

When multiple Jira credentials exist in `.credentials/`, use `--credential` to select one by ID:

当 `.credentials/` 中有多个 Jira 凭证时，使用 `--credential` 按 ID 选择：

```bash
python3 .cursor/skills/jira-ticket-check/scripts/jira_ticket_check.py --credential Jira-Service-Account search --jql "project = PROJ"
```

### Override base URL / 覆盖 base URL

```bash
python3 .cursor/skills/jira-ticket-check/scripts/jira_ticket_check.py --base-url "https://api.atlassian.com/ex/jira/<cloud-id>" search --jql "project = PROJ"
```

### JSON output (available for all commands) / JSON 输出（所有命令均支持）

```bash
python3 .cursor/skills/jira-ticket-check/scripts/jira_ticket_check.py get --ticket PROJ-123 --json
```

## Parameters / 参数

### Global / 全局参数

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--credential` | No / 否 | Credential ID to use (when multiple exist) / 凭证 ID（多个凭证时选择） |
| `--base-url` | No / 否 | Jira base URL (overrides credential file) / 覆盖凭证文件中的 base URL |

### get

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--ticket` | Yes / 是 | Ticket key (e.g. PROJ-123) / Ticket 键值 |
| `--json` | No / 否 | Output raw JSON / 输出原始 JSON |

### search

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--jql` | Yes / 是 | JQL query string / JQL 查询语句 |
| `--limit` | No / 否 | Max results, default 20 / 最大结果数，默认 20 |
| `--json` | No / 否 | Output raw JSON / 输出原始 JSON |

### sprint

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--project` | Yes / 是 | Project key (e.g. PROJ) / 项目键值 |
| `--state` | No / 否 | Filter: `active`, `future`, or `closed` / 按状态过滤 |
| `--limit` | No / 否 | Max results, default 50 / 最大结果数，默认 50 |
| `--json` | No / 否 | Output raw JSON / 输出原始 JSON |

## Common JQL Examples / 常用 JQL 示例

| JQL | Description / 说明 |
|---|---|
| `project = PROJ` | All tickets in project / 项目所有工单 |
| `assignee = currentUser()` | My tickets / 我的工单 |
| `status = "In Progress"` | In-progress tickets / 进行中的工单 |
| `sprint in openSprints()` | Issues in active sprints / 活跃 Sprint 中的工单 |
| `updated >= -7d ORDER BY updated DESC` | Updated in last 7 days / 最近 7 天更新的工单 |
| `priority = High AND status != Done` | High priority & not done / 高优先级且未完成 |

## Output Formats / 输出格式

### get (text) / 获取详情

```
============================================================
  PROJ-123: Fix login timeout issue
============================================================
          Type: Bug
        Status: In Progress
      Priority: High
      Assignee: Alice
      Reporter: Bob
        Labels: backend, urgent
        Sprint: Sprint 23
       Created: 2026-07-01 10:00
       Updated: 2026-07-06 14:30
  Story Points: 3

  Description:
    Users report timeout when logging in...

  Comments (2):
    [2026-07-02 09:00] Alice: Looking into the DB connection pool...
    [2026-07-05 16:00] Bob: Any update on this?
```

### search (text) / 搜索列表

```
[PROJ-123] (Bug) Fix login timeout issue  [In Progress | High | Alice]
[PROJ-124] (Story) Add dark mode support  [Open | Medium | Carol]
[PROJ-125] (Task) Update CI pipeline  [Done | Low | Unassigned]

3 of 3 issue(s)
```

### sprint (text) / Sprint 分组

```
--- Sprint 23 [active] (3 issues) ---
  [PROJ-123] (Bug) Fix login timeout  [In Progress | High | Alice]
  [PROJ-124] (Story) Dark mode support  [Open | Medium | Carol]
  [PROJ-125] (Task) Update CI pipeline  [Submitted | Low | Bob]

1 sprint(s), 3 of 3 issue(s)
```

## Credential Format / 凭证格式

Create a JSON file in `.credentials/` (filename is arbitrary):

在 `.credentials/` 目录下创建 JSON 文件（文件名任意）：

| Field / 字段 | Required / 必填 | Description / 说明 |
|---|---|---|
| `type` | Yes / 是 | Must be `"atlassian"` / 必须为 `"atlassian"` |
| `email` | Yes / 是 | Atlassian account email / Atlassian 账号邮箱 |
| `token` | Yes / 是 | Jira API token / Jira API 令牌 |
| `auth_mode` | Yes / 是 | `"classic"` (personal token) or `"scoped"` (service account) / 认证模式 |
| `base_url` | No / 否 | Jira instance URL; auto-derived from `cloud_id` or `domain` / 可自动推导 |
| `domain` | No / 否 | Jira site domain, for classic mode (e.g. `your-domain.atlassian.net`) / classic 模式的站点域名 |
| `cloud_id` | No / 否 | Atlassian Cloud site ID, for scoped mode / scoped 模式的 Cloud ID |

## Notes / 注意事项

- No external dependencies — uses Python standard library (`urllib`) only / 无需外部依赖，仅使用 Python 标准库
- Uses REST API v3 only (no Agile API dependency) — compatible with scoped tokens / 仅使用 REST API v3（无 Agile API 依赖），兼容受限 scope 的 token
- Authentication uses HTTP Basic Auth (email:token), standard for Jira Cloud / 使用 HTTP Basic Auth 认证
- The `get` command shows the last 5 comments; use `--json` for full data / `get` 命令显示最近 5 条评论；用 `--json` 获取完整数据
- Description is extracted from Atlassian Document Format (ADF) to plain text / 描述从 ADF 格式提取为纯文本
- Sprint data is read from both the standard `sprint` field and `customfield_10020` / Sprint 数据同时从标准 `sprint` 字段和 `customfield_10020` 读取
- Story Points are read from `customfield_10024` (`Story Points`) first, then `customfield_10016` (`Story point estimate`) / Story Points 优先读 `customfield_10024`，其次 `customfield_10016`
- Service-account tokens: `assignee = currentUser()` does **not** match a human user; query by display name (e.g. `"Xin Feng"`) or accountId / 服务账号下 `currentUser()` 无效，请用显示名或 accountId 查询
- Active sprint dates (`startDate` / `endDate`) are on the sprint object inside `customfield_10020` / 活跃 Sprint 起止时间在 `customfield_10020` 的 sprint 对象上
- Sprint may remain `active` after its planned `endDate` until someone closes it on the board / Sprint 可能在计划结束日之后仍为 `active`，直到在看板上正式关闭
