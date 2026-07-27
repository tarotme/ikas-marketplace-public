# engine-self-schedule / Engine 自调度定时消息

Schedule delayed messages to yourself via the IKAS Engine HTTP API. When the scheduled time arrives, the Engine sends the message back to you with context references so you can recall what you were doing.

通过 IKAS Engine HTTP API 为自己设置定时消息。到达指定时间后，Engine 会将消息发送回你，并附带上下文引用，以便你回忆当时的任务。

## Trigger / 触发词

`schedule`, `定时`, `timer`, `remind me`, `稍后检查`, `delayed`, `postpone`, `check later`, `每隔`, `every`, `periodic`, `reschedule`

## Prerequisites / 前置条件

- Environment variables set by the Engine / Engine 自动注入的环境变量:
  - `IKAS_AGENT_ID` — your agent ID / 你的 agent ID
  - `IKAS_ENGINE_URL` — Engine HTTP base URL (e.g. `http://localhost:60320`) / Engine HTTP 地址

These are automatically available when running inside an IKAS Engine (Cursor or Gemini). Authentication uses localhost verification — no token needed.

这些环境变量在 IKAS Engine（Cursor 或 Gemini）中运行时自动可用。认证使用本机地址验证，不需要 token。

## Script / 脚本

`scripts/engine_self_schedule.py` (relative to this skill directory)

## Commands / 命令

### Schedule a message / 设置定时消息

```bash
python3 .cursor/skills/engine-self-schedule/scripts/engine_self_schedule.py schedule \
  --message "Check if DNS changes have propagated" \
  --at "+30m"
```

The `--at` parameter accepts ISO 8601 timestamps or relative time:

`--at` 参数接受 ISO 8601 时间戳或相对时间：

- `2026-07-18T01:00:00+08:00` — absolute time / 绝对时间
- `+30m` — 30 minutes from now / 30 分钟后
- `+2h` — 2 hours from now / 2 小时后
- `+1d` — 1 day from now / 1 天后

### Recall a turn's context / 查看某轮对话的上下文

```bash
python3 .cursor/skills/engine-self-schedule/scripts/engine_self_schedule.py recall \
  --turn-id "turn_abc123"
```

This retrieves the transcript events for a specific turn, including user message, assistant response, and tool call summaries.

获取指定 turn 的 transcript 事件，包括用户消息、助手回复和工具调用摘要。

### List scheduled messages / 查看已设置的定时消息

```bash
python3 .cursor/skills/engine-self-schedule/scripts/engine_self_schedule.py list
```

### Cancel a scheduled message / 取消定时消息

```bash
python3 .cursor/skills/engine-self-schedule/scripts/engine_self_schedule.py cancel --id "msg-uuid"
```

### Reschedule / 重新定时

Cancel an existing scheduled message and create a new one:

取消已有定时消息并创建新的：

```bash
python3 .cursor/skills/engine-self-schedule/scripts/engine_self_schedule.py reschedule \
  --id "msg-uuid" \
  --message "Check DNS again" \
  --at "+10m"
```

## Periodic / Recurring Pattern / 周期性定时模式

The Engine does not have built-in recurring timers. To implement periodic checks (e.g. "check every 10 minutes"), use the **chain reschedule** pattern:

Engine 没有内置的周期性定时器。要实现周期性检查（如"每 10 分钟检查一次"），使用**链式重设**模式：

1. Schedule the first check: `schedule --message "Check result" --at "+10m"`
2. When the scheduled message fires, do your work
3. If not done, schedule the next check: `schedule --message "Check result again" --at "+10m"`
4. Repeat until the task is complete

**Example prompt from user / 用户 prompt 示例：**

> "请每 10 分钟检查一次 DNS 传播状态，直到全部生效为止"

**What you should do / 你应该做的：**

1. Run the initial check
2. If not fully propagated, use `schedule --at "+10m"` to set the next check
3. When triggered again, re-check and reschedule if needed
4. When fully propagated, do NOT reschedule — the chain ends naturally

## Parameters / 参数

| Parameter / 参数 | Command / 命令 | Required / 必填 | Description / 说明 |
|---|---|---|---|
| `--message`, `-m` | schedule, reschedule | Yes | Message to send at the scheduled time / 定时发送的消息内容 |
| `--at` | schedule, reschedule | Yes | ISO 8601 timestamp or relative time (+30m, +2h) / ISO 8601 时间戳或相对时间 |
| `--turn-id` | recall | Yes | Turn ID to look up / 要查询的 turn ID |
| `--id` | cancel, reschedule | Yes | Scheduled message ID to cancel / 要取消的定时消息 ID |

## Notes / 注意事项

- The Engine polls every 5 seconds, so message delivery has up to ~5s of jitter / Engine 每 5 秒轮询一次，消息投递精度约 ±5 秒
- Scheduled messages are persisted to disk — they survive Engine restarts / 定时消息持久化到磁盘，Engine 重启后不丢失
- Each agent can only schedule messages from localhost (enforced by IP check) / 每个 agent 只能从本机设置定时消息（通过 IP 校验）
- When a scheduled message fires, it includes the context turn ID — use `recall` to review what you were doing / 定时消息触发时包含上下文 turn ID，使用 `recall` 查看当时的对话记录
- Scheduled messages have highest priority — they are inserted at the front of the queue / 定时消息优先级最高，插入队列最前面
- For periodic tasks, always check if the task is complete before rescheduling to avoid infinite loops / 周期性任务中，务必先检查任务是否完成再重设定时，避免无限循环
