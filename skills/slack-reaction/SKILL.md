# slack-reaction / Slack 表情回应

Add or remove emoji reactions on Slack messages. Use reactions instead of sending a message when a simple emoji response is sufficient.

在 Slack 消息上添加或移除表情回应。当简短的表情回应足够时，使用 reaction 代替发送一条只含表情的消息。

## Trigger / 触发词

`reaction`, `react`, `emoji`, `表情`, `回应`

## Prerequisites / 前置条件

- Python dependency / Python 依赖: `pip install slack-sdk`
- Workspace `.credentials/` directory must contain a decrypted `slack-bot` type credential JSON file (managed by IKAS Workspace Manager)

工作区 `.credentials/` 目录中必须包含一个 `type: "slack-bot"` 且含 `bot_token` 字段的凭证文件（由 IKAS Workspace Manager 管理）。

- Bot must have scope / Bot 需要权限: `reactions:write`

## Script / 脚本

`scripts/slack_reaction.py` (relative to this skill directory)

## Commands / 命令

### Add a reaction / 添加表情回应

```bash
python3 .cursor/skills/slack-reaction/scripts/slack_reaction.py add --channel C12345 --ts 1234567890.123456 --emoji thumbsup
```

### Remove a reaction / 移除表情回应

```bash
python3 .cursor/skills/slack-reaction/scripts/slack_reaction.py remove --channel C12345 --ts 1234567890.123456 --emoji thumbsup
```

## Parameters / 参数

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--channel` | Yes / 是 | Channel ID (C.../D.../G...) / 频道 ID |
| `--ts` | Yes / 是 | Message timestamp to react to / 要回应的消息时间戳 |
| `--emoji` | Yes / 是 | Emoji name without colons / 表情名称（不含冒号） |

## Common Emoji Names / 常用表情名称

| Emoji | Name | Use case / 用途 |
|---|---|---|
| 👍 | `thumbsup` | Acknowledged, agreed / 已收到、同意 |
| ✅ | `white_check_mark` | Done, completed / 完成 |
| 👀 | `eyes` | Looking into it / 正在查看 |
| 🎉 | `tada` | Celebration, success / 庆祝、成功 |
| ⏳ | `hourglass_flowing_sand` | Working on it, in progress / 处理中 |
| ❌ | `x` | Rejected, not possible / 拒绝、不可行 |
| 🔥 | `fire` | Urgent, critical / 紧急、严重 |
| 💯 | `100` | Fully agree, perfect / 完全同意、完美 |

## Notes / 注意事项

- Emoji names do NOT include colons — use `thumbsup` not `:thumbsup:` / 表情名称不含冒号
- Adding a reaction that already exists will not error (gracefully handled) / 添加已存在的 reaction 不会报错
- Removing a reaction that doesn't exist will not error (gracefully handled) / 移除不存在的 reaction 不会报错
- Custom workspace emojis are also supported — use the custom emoji name / 也支持工作区自定义表情
