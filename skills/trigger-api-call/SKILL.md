# trigger-api-call / 调用 IKAS Trigger API 触发器

Call IKAS Trigger's API-type webhook endpoint to dispatch messages to agents.

调用 IKAS Trigger 的 API 类型 webhook 端点，将消息分发给 agent 执行。

## Trigger / 触发词

`trigger`, `api hook`, `webhook`, `触发器`, `调用触发器`, `dispatch`

## Prerequisites / 前置条件

- Python dependencies / Python 依赖: `pip install requests`
- Workspace `.credentials/` directory must contain an `ikas-trigger` credential (or legacy `custom` with the same fields) with `trigger_url` (or `url`) and `api_key`

工作区 `.credentials/` 目录中必须包含 `ikas-trigger` 类型凭证（或带相同字段的旧版 `custom` 凭证），需含 `trigger_url`（或 `url`）和 `api_key`（由 IKAS Workspace Manager 管理）。

### Credential format / 凭证格式

```json
{
  "id": "my-trigger",
  "type": "ikas-trigger",
  "memo": "Production API Trigger",
  "trigger_url": "http://trigger.example:60360/api/hook",
  "api_key": "your-api-key-here"
}
```

In Workspace Manager UI, enter only the base URL (e.g. `http://trigger.example:60360`); `/api/hook` is appended automatically and stored in the credential.

在 Workspace Manager UI 中只需填写 Base URL（如 `http://trigger.example:60360`），系统会自动补全并写入 `/api/hook`。

Legacy `custom` credentials with the same fields remain supported.

旧版 `custom` 类型（含相同字段）仍可兼容使用。

## Script / 脚本

`scripts/trigger_api_call.py` (relative to this skill directory)

## Commands / 命令

### Send a message (auto-discover credentials) / 发送消息（自动发现凭证）

```bash
python3 .cursor/skills/trigger-api-call/scripts/trigger_api_call.py call --message "Your message here"
```

### Select a specific trigger (when multiple credentials exist) / 选择特定触发器

```bash
python3 .cursor/skills/trigger-api-call/scripts/trigger_api_call.py call --trigger-name "my-trigger" --message "Hello"
```

### Send to a dynamic agent (thread mode) / 发送到动态 agent

```bash
python3 .cursor/skills/trigger-api-call/scripts/trigger_api_call.py call --message "Process this" --agent-name "customer-123"
```

### List dynamic agents / 列出动态 agent

```bash
python3 .cursor/skills/trigger-api-call/scripts/trigger_api_call.py agents
```

### Explicit URL and key (override credential discovery) / 手动指定

```bash
python3 .cursor/skills/trigger-api-call/scripts/trigger_api_call.py call \
  --url http://<trigger-host>:60360/api/hook \
  --key <api-key> \
  --message "Hello"
```

## Parameters / 参数

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--message`, `-m` | Yes | Message content to send / 要发送的消息内容 |
| `--trigger-name` | No | Select credential by id or memo match / 通过 id 或 memo 匹配选择凭证 |
| `--agent-name` | No | Dynamic agent name (for thread_agent mode) / 动态 agent 名称 |
| `--url` | No | Trigger webhook URL (overrides auto-discovery) / 覆盖自动发现 |
| `--key` | No | API Key — selects the trigger; URL auto-resolved from credentials / 指定 API Key，URL 从凭证中自动解析 |

## Credential Resolution / 凭证解析优先级

1. `--url` + `--key` both provided → use directly / 两者都指定则直接使用
2. `--key` only → find matching credential by api_key, get URL from it / 仅指定 key 则按 key 匹配凭证获取 URL
3. Environment variables `TRIGGER_URL` + `TRIGGER_API_KEY` / 环境变量
4. Auto-discover from `<cwd>/.credentials/*.json` — prefers `type: "ikas-trigger"`, also accepts files with both `trigger_url` (or `url`) and `api_key` / 自动从 .credentials/ 搜索

## Output / 输出

Prints the trigger execution result as JSON:

输出触发器执行结果（JSON 格式）：

```json
{
  "trigger_name": "my-api-trigger",
  "trigger_type": "api",
  "agent_name": "my-agent",
  "result": "success",
  "duration_ms": 1234,
  "prompt_summary": "..."
}
```

Result values / 结果值:
- `success` — Agent executed successfully / Agent 执行成功
- `queued` — Request queued (agent busy) / 请求已排队
- `error` — Execution failed / Agent 执行失败
- `skipped_busy` — Agent busy, skipped / Agent 忙碌，已跳过
- `skipped_paused` — Agent paused / Agent 已暂停

## Notes / 注意事项

- The API Key is unique per trigger — each credential corresponds to one trigger / 每个凭证对应一个触发器
- The trigger's prompt template uses `{{message}}` placeholder — your `--message` content replaces it / 触发器 prompt 模板中的 `{{message}}` 会被替换
- Other template variables: `{{datetime}}` (current time UTC+8), `{{trigger_name}}` / 其他模板变量
- Default trigger port is often `60360` (check your Trigger Admin) / 常见端口为 60360，以实际 Admin 配置为准
- For dynamic agent mode, `--agent-name` is required; each unique name creates/reuses a separate agent instance / 动态 agent 模式需要 agent-name
- When multiple trigger credentials exist in `.credentials/`, use `--trigger-name` to select / 多个凭证时用 --trigger-name 选择
