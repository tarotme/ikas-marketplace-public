# ikas-mp-request-result-post / 上报异步请求结果

Post execution results back to IKAS Trigger for an asynchronous API request.

将执行结果上报至 IKAS Trigger 的异步请求接口。

## Trigger / 触发词

`report result`, `post result`, `request result`, `上报结果`, `回写结果`, `异步结果`

## Prerequisites / 前置条件

- Python dependencies / Python 依赖: `pip install requests`
- The agent's prompt must contain `{{request_id}}` and `{{api_key}}` template variables (automatically injected by IKAS Trigger for API-type triggers)

Agent 的 prompt 中必须包含 `{{request_id}}` 和 `{{api_key}}` 模板变量（IKAS Trigger 在 API 类型触发器中自动注入）。

### Credential format / 凭证格式

No separate credential file needed — the `api_key` and `request_id` are injected into the prompt by IKAS Trigger.

不需要额外的凭证文件——`api_key` 和 `request_id` 由 IKAS Trigger 注入到 prompt 中。

## Script / 脚本

`scripts/request_result_post.py` (relative to this skill directory)

## Commands / 命令

### Post a successful result / 上报成功结果

```bash
python3 .cursor/skills/ikas-mp-request-result-post/scripts/request_result_post.py \
  --url http://<trigger-host>:60330 \
  --api-key <api_key> \
  --request-id <request_id> \
  --result "Task completed successfully. Output: ..."
```

### Post an error result / 上报错误结果

```bash
python3 .cursor/skills/ikas-mp-request-result-post/scripts/request_result_post.py \
  --url http://<trigger-host>:60330 \
  --api-key <api_key> \
  --request-id <request_id> \
  --status error \
  --error "Failed to process: timeout"
```

### Query request status / 查询请求状态

```bash
python3 .cursor/skills/ikas-mp-request-result-post/scripts/request_result_post.py query \
  --url http://<trigger-host>:60330 \
  --api-key <api_key> \
  --request-id <request_id>
```

## Parameters / 参数

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--url` | Yes | IKAS Trigger server base URL / 触发器服务器地址 |
| `--api-key` | Yes | API Key for authentication / 用于鉴权的 API Key |
| `--request-id` | Yes | Request ID to report result for / 要上报结果的请求 ID |
| `--result` | No | Result content (for success) / 结果内容（成功时） |
| `--status` | No | `completed` (default) or `error` / 状态 |
| `--error` | No | Error message (when status is error) / 错误信息 |

## URL Resolution / URL 解析

1. `--url` provided → use directly / 直接使用
2. Environment variable `TRIGGER_URL` / 环境变量
3. Auto-discover from `<cwd>/.credentials/*.json` — finds files containing `trigger_url` (or `url`) field / 自动从 .credentials/ 搜索

## Output / 输出

Prints the API response as JSON:

```json
{
  "ok": true,
  "request_id": "req_abc123def456",
  "status": "completed"
}
```

## Notes / 注意事项

- The `request_id` and `api_key` are provided in the agent's prompt template as `{{request_id}}` and `{{api_key}}` / 这两个值在 prompt 模板中以 `{{request_id}}` 和 `{{api_key}}` 形式提供
- Authentication requires both `api_key` and matching `request_id` / 鉴权需要 api_key 和 request_id 匹配
- Results are stored in memory with disk persistence; expired results (>24h) are automatically cleaned / 结果存在内存中并持久化到磁盘，超过 24 小时自动清理
- Default trigger port is 60330 / 默认触发器端口为 60330
