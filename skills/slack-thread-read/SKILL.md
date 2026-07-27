# slack-thread-read / 读取 Slack Thread 上下文

Read the full conversation context of a Slack thread, including the parent message and all replies.

读取 Slack thread 的完整对话上下文，包括父消息和所有回复。

## Trigger / 触发词

`thread`, `read thread`, `读取thread`, `thread上下文`, `对话上下文`, `thread context`

## Prerequisites / 前置条件

- Python dependency / Python 依赖: `pip install slack-sdk`
- Workspace `.credentials/` directory must contain a decrypted `slack-bot` type credential JSON file (managed by IKAS Workspace Manager)

工作区 `.credentials/` 目录中必须包含一个 `type: "slack-bot"` 且含 `bot_token` 字段的凭证文件（由 IKAS Workspace Manager 管理）。

- Bot must have scopes / Bot 需要以下权限: `channels:history`, `groups:history`, `im:history`, `mpim:history`

## Script / 脚本

`scripts/slack_thread_read.py` (relative to this skill directory)

## Commands / 命令

### Fetch all messages in a thread / 获取 thread 中所有消息

```bash
python3 .cursor/skills/slack-thread-read/scripts/slack_thread_read.py --channel C12345 --thread-ts 1234567890.123456
```

### Output as JSON / 以 JSON 格式输出

```bash
python3 .cursor/skills/slack-thread-read/scripts/slack_thread_read.py --channel C12345 --thread-ts 1234567890.123456 --json
```

### Limit number of messages / 限制消息数量

```bash
python3 .cursor/skills/slack-thread-read/scripts/slack_thread_read.py --channel C12345 --thread-ts 1234567890.123456 --limit 10
```

### Exclude bot messages / 排除 bot 消息

Bot messages are included by default. Use `--exclude-bots` to exclude them.

默认包含 bot 消息。使用 `--exclude-bots` 排除 bot 消息。

```bash
python3 .cursor/skills/slack-thread-read/scripts/slack_thread_read.py --channel C12345 --thread-ts 1234567890.123456 --exclude-bots
```

## Parameters / 参数

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--channel` | Yes / 是 | Channel ID (C.../D.../G...) / 频道 ID |
| `--thread-ts` | Yes / 是 | Parent message timestamp of the thread / Thread 父消息的时间戳 |
| `--limit` | No / 否 | Max number of messages to fetch / 最多获取的消息数 |
| `--exclude-bots` | No / 否 | Exclude bot messages (included by default) / 排除 bot 消息 |
| `--json` | No / 否 | Output as JSON instead of human-readable text / 以 JSON 输出 |

## Output Formats / 输出格式

### Text output (default) / 文本输出（默认）

```
[parent] Alice (2026-06-18 10:00:00)
Can you check the DNS record for example.com?

[reply] Bob (2026-06-18 10:00:15)
Looking into it now...

[reply] Alice (2026-06-18 10:01:00)
Thanks, also check the CLB config.
  [file] screenshot.png (image/png)
```

### JSON output (`--json`) / JSON 输出

```json
[
  {
    "ts": "1234567890.123456",
    "user_id": "U01GSENE599",
    "user_name": "Alice",
    "text": "Can you check the DNS record for example.com?",
    "time": "2026-06-18 10:00:00",
    "is_parent": true,
    "files": []
  }
]
```

## Use Cases / 使用场景

- Read conversation history before responding to a thread / 回复 thread 前读取对话历史
- Understand the full context of a request that spans multiple messages / 理解跨多条消息的请求的完整上下文
- Extract file attachments from a thread for further processing / 提取 thread 中的文件附件以供后续处理

## Notes / 注意事项

- User names are resolved via `users.info` API and cached in memory / 用户名通过 `users.info` API 解析并缓存
- Bot messages are included by default for complete context; use `--exclude-bots` to filter / 默认包含 bot 消息；用 `--exclude-bots` 过滤
- Pagination is handled automatically for threads with many messages / 自动处理分页
- The bot must be a member of the channel (or have appropriate scopes for DMs) to read messages / Bot 必须是频道成员才能读取消息
