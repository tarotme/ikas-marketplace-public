# slack-channel-read / 读取 Slack Channel 上下文消息

Read context messages around a specific message in a Slack channel, or fetch the latest messages.

读取 Slack 频道中指定消息的上下文消息，或获取频道最新消息。

## Trigger / 触发词

`channel`, `read channel`, `channel context`, `频道消息`, `频道上下文`, `channel history`

## Prerequisites / 前置条件

- Python dependency / Python 依赖: `pip install slack-sdk`
- Workspace `.credentials/` directory must contain a decrypted `slack-bot` type credential JSON file (managed by IKAS Workspace Manager)

工作区 `.credentials/` 目录中必须包含一个 `type: "slack-bot"` 且含 `bot_token` 字段的凭证文件（由 IKAS Workspace Manager 管理）。

- Bot must have scopes / Bot 需要以下权限: `channels:history`, `groups:history`, `im:history`, `mpim:history`

## Script / 脚本

`scripts/slack_channel_read.py` (relative to this skill directory)

## Commands / 命令

### Read context around a message / 读取指定消息的上下文

```bash
python3 .cursor/skills/slack-channel-read/scripts/slack_channel_read.py --channel C12345 --ts 1234567890.123456
```

Default: 5 messages before and 5 messages after the target.

默认获取目标消息前后各 5 条消息。

### Customize context window / 自定义上下文窗口

```bash
python3 .cursor/skills/slack-channel-read/scripts/slack_channel_read.py --channel C12345 --ts 1234567890.123456 --before 10 --after 3
```

### Fetch latest messages / 获取频道最新消息

```bash
python3 .cursor/skills/slack-channel-read/scripts/slack_channel_read.py --channel C12345 --latest
```

### Fetch latest with custom limit / 获取指定数量的最新消息

```bash
python3 .cursor/skills/slack-channel-read/scripts/slack_channel_read.py --channel C12345 --latest --limit 50
```

### Output as JSON / 以 JSON 格式输出

```bash
python3 .cursor/skills/slack-channel-read/scripts/slack_channel_read.py --channel C12345 --ts 1234567890.123456 --json
```

### Exclude bot messages / 排除 bot 消息

```bash
python3 .cursor/skills/slack-channel-read/scripts/slack_channel_read.py --channel C12345 --ts 1234567890.123456 --exclude-bots
```

## Parameters / 参数

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--channel` | Yes / 是 | Channel ID (C.../D.../G...) / 频道 ID |
| `--ts` | One of `--ts` / `--latest` | Target message timestamp / 目标消息的时间戳 |
| `--latest` | One of `--ts` / `--latest` | Fetch latest messages instead / 获取最新消息 |
| `--before` | No / 否 | Messages before the target (default: 5, used with `--ts`) / 目标前的消息数 |
| `--after` | No / 否 | Messages after the target (default: 5, used with `--ts`) / 目标后的消息数 |
| `--limit` | No / 否 | Max messages to fetch (default: 20, used with `--latest`) / 最新消息数量 |
| `--exclude-bots` | No / 否 | Exclude bot messages / 排除 bot 消息 |
| `--json` | No / 否 | Output as JSON instead of text / 以 JSON 输出 |

## Output Formats / 输出格式

### Text output (default) / 文本输出（默认）

The target message is marked with `>>>`. Thread info is shown when a message has replies.

目标消息用 `>>>` 标记。有回复的消息会显示 thread 信息。

```
     Alice (2026-07-06 14:00:00)
     Anyone looked at the deployment issue?

     Bob (2026-07-06 14:01:00) [thread: 3 replies]
     Yes, I think it's a config problem.

 >>> Carol (2026-07-06 14:02:00)
     I just pushed a fix, can someone review?

     Alice (2026-07-06 14:03:00)
     Sure, I'll take a look.
```

### JSON output (`--json`) / JSON 输出

```json
[
  {
    "ts": "1234567890.123456",
    "user_id": "U01GSENE599",
    "user_name": "Alice",
    "text": "Anyone looked at the deployment issue?",
    "time": "2026-07-06 14:00:00",
    "is_target": false,
    "thread": null,
    "files": []
  },
  {
    "ts": "1234567891.123456",
    "user_id": "U02ABCDE123",
    "user_name": "Carol",
    "text": "I just pushed a fix, can someone review?",
    "time": "2026-07-06 14:02:00",
    "is_target": true,
    "thread": null,
    "files": []
  }
]
```

## Use Cases / 使用场景

- Understand the conversation context before/after a specific message / 了解某条消息前后的对话上下文
- Review what was discussed around a linked Slack message / 查看链接的 Slack 消息周围的讨论内容
- Catch up on the latest channel activity / 了解频道最新动态
- Combine with `slack-thread-read` to get both channel context and thread details / 结合 `slack-thread-read` 同时获取频道上下文和 thread 详情

## Notes / 注意事项

- `--ts` and `--latest` are mutually exclusive — use one or the other / `--ts` 和 `--latest` 互斥，只能选其一
- User names are resolved via `users.info` API and cached in memory / 用户名通过 `users.info` API 解析并缓存
- Bot messages are included by default for complete context; use `--exclude-bots` to filter / 默认包含 bot 消息；用 `--exclude-bots` 过滤
- The bot must be a member of the channel (or have appropriate scopes for DMs) to read messages / Bot 必须是频道成员才能读取消息
- Messages with threads show reply count; use `slack-thread-read` to fetch full thread content / 有 thread 的消息会显示回复数；用 `slack-thread-read` 获取完整 thread 内容
