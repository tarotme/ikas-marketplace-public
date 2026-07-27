---
description: 禁止在仓库写入服务器 IP/用户名/密码；部署前向用户询问 / Forbid embedding server IP, username, or password in the repo
alwaysApply: true
---

# 禁止写入服务器凭据 / No Server Credentials in Repo

## 规则 / Rule

**禁止**在本工作区任意仓库中写入、提交或固化以下信息：

- 服务器 IP 地址（公网或内网）
- SSH / 部署用的用户名
- SSH / 部署用的密码

Do **not** write, commit, or hardcode in any repository under this workspace:

- Server IP addresses (public or private)
- SSH / deploy usernames
- SSH / deploy passwords

## 正确做法 / Correct practice

1. 文档与 Skill 中只使用占位符：`<user>`、`<host>`、`<password>`（或密钥路径）。
2. 需要 SSH / 部署 / scp 时，**必须先向用户询问**主机、用户名、密码（或密钥），会话内使用，**不要**写回规则、skill、脚本或 README。
3. 官网等可用**域名**说明（如 `ikas.tarotme.net`），不要写对应 IP。
4. UI placeholder、示例配置使用虚构值（如 `host.example`、`proxy.example`），不要用真实内网 IP。
5. 工作区 `.credentials/` 仅用于已登记的第三方凭据 ID，**不是**存放服务器 SSH 密码的地方；也不要在 rules 里抄写其内容。

Use placeholders only (`<user>`, `<host>`, `<password>` or key path). Ask the user before every SSH/deploy/scp. Prefer domains over IPs. Use fictional example hosts in UI/docs. Do not copy SSH passwords into rules/skills.

## 例外 / Exceptions

- `127.0.0.1` / `0.0.0.0` / 文档中的 RFC1918 **网段示例**（如 `10.0.0.0/8`）用于本机监听或代理 bypass，不算服务器登录凭据。
- 程序代码里对用户输入字段名为 `password` / `username` 的 API 字段定义，不算违规。

`127.0.0.1`, `0.0.0.0`, and RFC1918 **CIDR examples** for listen/bypass are OK. API field names like `password` in source code are OK.
