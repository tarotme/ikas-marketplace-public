# slack-reply / Slack 回复

Send messages, thread replies, update messages, and download files via Slack API.

通过 Slack API 发送消息、线程回复、更新消息、下载文件。

## Trigger / 触发词

`slack`, `reply`, `回复`, `send message`, `发消息`

## Prerequisites / 前置条件

- Python dependencies / Python 依赖: `pip install slack-sdk requests`
- Workspace `.credentials/` directory must contain a decrypted `slack-bot` type credential JSON file (managed by IKAS Workspace Manager)

工作区 `.credentials/` 目录中必须包含一个 `type: "slack-bot"` 且含 `bot_token` 字段的凭证文件（由 IKAS Workspace Manager 管理）。

- Bot must have scopes / Bot 需要以下权限: `chat:write`, `files:read`, `files:write`

## Script / 脚本

`scripts/slack_reply.py` (relative to this skill directory)

## Commands / 命令

### Send a message to a channel / 发送消息到频道

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py send --channel C12345 --text "Hello"
```

### Send a DM to a user by User ID / 通过 User ID 发送 DM

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py dm --user U01GSENE599 --text "Hello"
```

This command automatically calls `conversations.open` to obtain the DM channel, then sends the message. No Channel ID needed.

此命令自动调用 `conversations.open` 获取 DM 频道，然后发送消息。无需 Channel ID。

### Reply in a thread / 线程回复

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py reply --channel C12345 --thread-ts 1234567890.123456 --text "Reply text"
```

### Reply in a thread and broadcast to channel / 线程回复并广播到频道

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py reply --channel C12345 --thread-ts 1234567890.123456 --text "Important reply" --broadcast
```

### Update an existing message / 更新已有消息

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py update --channel C12345 --ts 1234567890.123456 --text "Updated content"
```

### Send a message with files / 发送消息并附带文件

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py send --channel C12345 --text "See attached" \
  --files "/path/to/image.png"
```

### Send multiple files / 发送多个文件

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py send --channel C12345 --text "Reports attached" \
  --files "/path/to/report.pdf,/path/to/chart.png"
```

### Reply in a thread with files / 线程回复并附带文件

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py reply --channel C12345 --thread-ts 1234567890.123456 \
  --text "Here is the screenshot" --files "/path/to/screenshot.png"
```

### DM a user with files / 发送带文件的 DM

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py dm --user U01GSENE599 --text "File for you" \
  --files "/path/to/document.pdf"
```

### Download a file (e.g., voice clip) / 下载文件（如语音片段）

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py download --url "https://files.slack.com/files-pri/..." --output /tmp/audio.mp4
```

### With buttons (simplified) / 使用按钮（简化模式）

The `--buttons` parameter takes a simplified JSON array. Each button needs `text` and `action_id`, with optional `style` and `value`. Use `--color` to wrap buttons in a colored sidebar card.

`--buttons` 参数接受简化的 JSON 数组。每个按钮需要 `text` 和 `action_id`，可选 `style` 和 `value`。使用 `--color` 将按钮包裹在彩色侧边栏卡片中。

```bash
# Buttons with colored sidebar
python3 .cursor/skills/slack-reply/scripts/slack_reply.py dm --user U01GSENE599 --text "请审批" \
  --buttons '[{"text":"Approve","action_id":"approve_001","style":"primary","value":"yes"},{"text":"Deny","action_id":"deny_001","style":"danger","value":"no"}]' \
  --color "#2eb886"

# Buttons without sidebar (plain actions block)
python3 .cursor/skills/slack-reply/scripts/slack_reply.py dm --user U01GSENE599 --text "请选择" \
  --buttons '[{"text":"Option A","action_id":"opt_a","value":"a"},{"text":"Option B","action_id":"opt_b","value":"b"}]'
```

Button JSON format / 按钮 JSON 格式：

```json
[
  {
    "text": "Button label",
    "action_id": "unique_action_id",
    "style": "primary",
    "value": "payload_value"
  }
]
```

| Field / 字段 | Required / 必填 | Description / 说明 |
|---|---|---|
| `text` | Yes / 是 | Button display text / 按钮显示文字 |
| `action_id` | Yes / 是 | Unique ID for interaction callback / 交互回调的唯一标识 |
| `style` | No / 否 | `"primary"` (green) or `"danger"` (red), omit for gray / 绿色或红色，不填为灰色 |
| `value` | No / 否 | Payload sent back on click / 点击时回传的值 |

### With Block Kit blocks / 使用 Block Kit

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py send --channel C12345 --text "Fallback text" --blocks '[{"type":"section","text":{"type":"mrkdwn","text":"*Bold* message"}}]'
```

### With raw attachments / 使用原始 attachments

```bash
python3 .cursor/skills/slack-reply/scripts/slack_reply.py dm --user U01GSENE599 --text "Fallback" \
  --attachments '[{"color":"#2eb886","blocks":[{"type":"section","text":{"type":"mrkdwn","text":"*Title*\nSubtitle"}}]}]'
```

### Color and style reference / 颜色和样式参考

| Color / 颜色 | Hex | Use case / 用途 |
|---|---|---|
| Green / 绿色 | `#2eb886` | Success, approval / 成功、审批 |
| Red / 红色 | `#e01e5a` | Error, alert / 错误、告警 |
| Yellow / 黄色 | `#ecb22e` | Warning / 警告 |
| Blue / 蓝色 | `#36a64f` | Info / 信息 |
| Gray / 灰色 | `#dddddd` | Neutral / 中性 |

## Output / 输出

- `send`, `reply`, `update`, `dm` (text only): prints the message timestamp (`ts`) to stdout / 输出消息时间戳到标准输出
- `send`, `reply`, `dm` (with `--files`): prints `(file uploaded)` to stdout / 输出 `(file uploaded)`
- `download`: prints the local file path to stdout / 输出本地文件路径到标准输出

## Key Parameters / 关键参数

| Parameter / 参数 | Description / 说明 |
|---|---|
| `--user` | Slack User ID (U...) — for `dm` command only / 仅限 `dm` 命令 |
| `--channel` | Slack channel ID (C...) or DM ID (D...) / 频道 ID 或 DM ID |
| `--thread-ts` | Parent message timestamp for thread replies / 线程回复的父消息时间戳 |
| `--ts` | Message timestamp to update / 要更新的消息时间戳 |
| `--text` | Message text (supports Slack mrkdwn format) / 消息文本 |
| `--blocks` | JSON string of Block Kit blocks (optional) / Block Kit JSON（可选） |
| `--attachments` | JSON string of raw attachments (optional) / 原始 attachments JSON（可选） |
| `--buttons` | Simplified button JSON array (optional) / 简化按钮 JSON 数组（可选） |
| `--color` | Attachment sidebar color hex, used with `--buttons` (optional) / 侧边栏颜色（可选） |
| `--files` | Comma-separated file paths to upload (for `send`, `reply`, `dm`) / 逗号分隔的文件路径 |
| `--broadcast` | Also post thread reply to channel (flag) / 同时广播到频道 |

## Notes / 注意事项

- The bot must be invited to the channel before it can post / Bot 必须先被邀请到频道才能发送消息
- For public channels, if bot has `chat:write.public` scope, joining is not required / 公开频道有 `chat:write.public` 权限则无需加入
- The `download` command uses the bot token for authentication to access private Slack file URLs / `download` 命令使用 bot token 认证访问私有文件
- `--files` uses Slack's `files_upload_v2` API; the `--text` content becomes the `initial_comment` / `--files` 使用 `files_upload_v2` API，`--text` 内容作为初始评论
- When `--files` is used, `--blocks`, `--attachments`, and `--buttons` are ignored / 使用 `--files` 时，`--blocks`、`--attachments`、`--buttons` 不生效
- `update` command does not support `--files` (Slack API limitation) / `update` 命令不支持 `--files`
