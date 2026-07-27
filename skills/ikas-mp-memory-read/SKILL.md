# ikas-mp-memory-read / 读取工作区记忆文件

Read markdown memory files from the workspace `memory/` directory.

读取工作区 `memory/` 目录中的 Markdown 记忆文件。

## Trigger / 触发词

`memory`, `read memory`, `读取记忆`, `记忆文件`, `recall`, `回忆`

## Prerequisites / 前置条件

- Python 3.6+ (standard library only, no external dependencies)
- A `memory/` directory must exist in the workspace root / 工作区根目录下必须存在 `memory/` 目录

## Script / 脚本

`scripts/memory_read.py` (relative to this skill directory)

## Commands / 命令

### List all memory files / 列出所有记忆文件

```bash
python3 .cursor/skills/ikas-mp-memory-read/scripts/memory_read.py list
```

### Read a specific memory file / 读取指定记忆文件

```bash
python3 .cursor/skills/ikas-mp-memory-read/scripts/memory_read.py read --file meeting-notes.md
```

The `.md` extension is optional — both `meeting-notes` and `meeting-notes.md` are accepted.

`.md` 扩展名可省略 — `meeting-notes` 和 `meeting-notes.md` 均可。

### Search memory files by keyword / 按关键词搜索记忆文件

```bash
python3 .cursor/skills/ikas-mp-memory-read/scripts/memory_read.py search --keyword "项目计划"
```

## Parameters / 参数

| Parameter / 参数 | Required / 必填 | Description / 说明 |
|---|---|---|
| `list` | — | Subcommand: list all .md files in memory/ / 子命令：列出 memory/ 下所有 .md 文件 |
| `read` | — | Subcommand: read a specific .md file / 子命令：读取指定 .md 文件 |
| `search` | — | Subcommand: search files containing keyword / 子命令：搜索包含关键词的文件 |
| `--file` | Yes (for `read`) | Filename to read (with or without .md) / 要读取的文件名 |
| `--keyword` | Yes (for `search`) | Keyword to search for / 搜索关键词 |

## Output Formats / 输出格式

### list output / 列表输出

```
memory/
  meeting-notes.md (1.2 KB, 2026-06-25 10:30:00)
  project-plan.md (3.4 KB, 2026-06-25 09:15:00)
  daily-log.md (0.8 KB, 2026-06-24 18:00:00)
3 file(s) found
```

### read output / 读取输出

```
--- meeting-notes.md (1.2 KB, 2026-06-25 10:30:00) ---
# Meeting Notes
...file content...
```

### search output / 搜索输出

```
meeting-notes.md: 2 match(es)
  L3: 讨论了项目计划的时间安排
  L15: 更新项目计划文档

project-plan.md: 1 match(es)
  L1: # 项目计划

2 file(s) matched
```

## Notes / 注意事项

- If `memory/` directory does not exist, the script exits with an error message and does not create it / 如果 `memory/` 目录不存在，脚本将报错退出，不会自动创建
- Only first-level `.md` files are listed and read; subdirectories are ignored / 仅列出和读取第一层 `.md` 文件，忽略子目录
- No external dependencies required — uses Python standard library only / 无需外部依赖，仅使用 Python 标准库
