# ikas-mp-request-result-get / 查询异步请求结果

Query the status and result of an asynchronous API request from IKAS Trigger.

从 IKAS Trigger 查询异步 API 请求的状态和结果。

## Trigger / 触发词

`get result`, `query result`, `check request`, `request status`, `查询结果`, `获取结果`, `请求状态`

## Prerequisites / 前置条件

- Python dependencies / Python 依赖: `pip install requests`
- You need the `api_key` and `request_id` of the request to query

需要目标请求的 `api_key` 和 `request_id`。

### Credential format / 凭证格式

No separate credential file needed — provide `api_key` and `request_id` directly via command-line arguments.

不需要额外的凭证文件——通过命令行参数直接提供 `api_key` 和 `request_id`。

## Script / 脚本

`scripts/request_result_get.py` (relative to this skill directory)

## Commands / 命令

### Query request result / 查询请求结果

```bash
python3 .cursor/skills/ikas-mp-request-result-get/scripts/request_result_get.py \
  --url http://<trigger-host>:60360 \
  --api-key <api_key> \
  --request-id <request_id>
```

### Auto-discover URL from credentials / 自动发现 URL

```bash
python3 .cursor/skills/ikas-mp-request-result-get/scripts/request_result_get.py \
  --api-key <api_key> \
  --request-id <request_id>
```

## Parameters / 参数

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `--url` | No | IKAS Trigger server base URL / 触发器服务器地址（可自动发现） |
| `--api-key` | Yes | API Key for authentication / 用于鉴权的 API Key |
| `--request-id` | Yes | Request ID to query / 要查询的请求 ID |

## URL Resolution / URL 解析

1. `--url` provided → use directly / 直接使用
2. Environment variable `TRIGGER_URL` / 环境变量
3. Auto-discover from `<cwd>/.credentials/*.json` — finds files containing `trigger_url` (or `url`) field / 自动从 .credentials/ 搜索

## Output / 输出

Prints the request record as JSON:

```json
{
  "request_id": "req_abc123def456",
  "trigger_name": "My API Trigger",
  "status": "completed",
  "created_at": "2026-07-03T09:59:58.286Z",
  "completed_at": "2026-07-03T10:00:03.278Z",
  "result": "Hello World"
}
```

### Status values / 状态值

| Status | Description / 说明 |
|---|---|
| `pending` | Request created, agent not yet started / 请求已创建，agent 尚未开始 |
| `running` | Agent is processing / Agent 正在处理 |
| `completed` | Execution completed successfully / 执行成功完成 |
| `error` | Execution failed / 执行失败 |
| `timeout` | Request timed out (>24h) / 请求超时 |

## Notes / 注意事项

- Authentication requires `api_key` matching the one used when the request was created / 鉴权需要与创建请求时一致的 api_key
- Results expire after 24 hours / 结果在 24 小时后过期
- Default trigger port is 60360 / 默认触发器端口为 60360
