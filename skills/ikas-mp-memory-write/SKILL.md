# ikas-mp-memory-write / 写入工作区记忆文件

Create and write markdown memory files in the workspace `memory/` directory.

在工作区 `memory/` 目录中创建和写入 Markdown 记忆文件。

## Trigger / 触发词

`write memory`, `save memory`, `记忆`, `保存记忆`, `写入记忆`, `remember`, `记住`

## Prerequisites / 前置条件

- Python 3.6+ (standard library only, no external dependencies)
- A `memory/` directory must exist in the workspace root / 工作区根目录下必须存在 `memory/` 目录

## Script / 脚本

`scripts/memory_write.py` (relative to this skill directory)

## Commands / 命令

### Create a new memory file / 创建新的记忆文件

```bash
python3 .cursor/skills/ikas-mp-memory-write/scripts/memory_write.py create --file meeting-notes.md --content "# Meeting Notes"
```

Fails if the file already exists. Use `write` to overwrite.

如果文件已存在则失败。使用 `write` 覆盖写入。

### Write (overwrite) a memory file / 覆盖写入记忆文件

```bash
python3 .cursor/skills/ikas-mp-memory-write/scripts/memory_write.py write --file meeting-notes.md --content "# Updated Notes\n\nNew content here."
```

Creates the file if it does not exist; overwrites if it does.

文件不存在则创建，已存在则覆盖。

### Append to a memory file / 追加写入记忆文件

```bash
python3 .cursor/skills/ikas-mp-memory-write/scripts/memory_write.py append --file daily-log.md --content "\n## 2026-06-25\n\n- Completed task A"
```

Appends content to the end of an existing file.

向现有文件末尾追加内容。

### Delete a memory file / 删除记忆文件

```bash
python3 .cursor/skills/ikas-mp-memory-write/scripts/memory_write.py delete --file old-notes.md
```

### Read content from stdin / 从标准输入读取内容

When `--content` is not provided, content is read from stdin. Useful for writing multi-line content.

当未提供 `--content` 时，从标准输入读取内容。适合写入多行内容。

```bash
cat draft.md | python3 .cursor/skills/ikas-mp-memory-write/scripts/memory_write.py write --file meeting-notes.md
```

## Parameters / 参数

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `create` | — | Subcommand: create a new file (fails if exists) / 子命令：创建新文件（已存在则失败） |
| `write` | — | Subcommand: write/overwrite a file / 子命令：覆盖写入文件 |
| `append` | — | Subcommand: append to an existing file / 子命令：追加写入文件 |
| `delete` | — | Subcommand: delete a file / 子命令：删除文件 |
| `--file` | Yes / 是 | Filename (with or without .md) / 文件名（可省略 .md） |
| `--content` | No / 否 | Content to write; reads from stdin if omitted / 写入内容；省略时从标准输入读取 |

## Notes / 注意事项

- If `memory/` directory does not exist, the script exits with an error message and does not create it / 如果 `memory/` 目录不存在，脚本将报错退出，不会自动创建
- Only first-level `.md` files are operated on; nested paths in `--file` are rejected / 仅操作第一层 `.md` 文件，`--file` 中的嵌套路径会被拒绝
- The `.md` extension is auto-appended if omitted / 如果省略 `.md` 扩展名会自动补上
- `\n` in `--content` is interpreted as a newline / `--content` 中的 `\n` 会被解释为换行符
- No external dependencies required — uses Python standard library only / 无需外部依赖，仅使用 Python 标准库
