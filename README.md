# ietf-mail-mcp

An MCP (Model Context Protocol) server that fetches and reads emails from the [IETF Mail Archive](https://mailarchive.ietf.org). It allows AI assistants to browse any IETF mailing list and retrieve full email content with a single tool call.

## Tool

### `fetch_all_email_details`

Fetches the full content of emails from an IETF mailing list within a given time range.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `list_name` | `str` | required | Mailing list name (e.g. `agent2agent`, `httpbis`, `quic`) |
| `days` | `int` | `0` | Fetch emails from the last N days. `0` = no date filter |
| `max_count` | `int` | `50` | Maximum number of emails to fetch (max 100) |

**Returns:** Formatted text containing each email's subject, sender, date, full body, and thread context.

**Examples:**

```
# Last 3 days of the agent2agent list
fetch_all_email_details("agent2agent", days=3)

# Latest 10 emails from httpbis
fetch_all_email_details("httpbis", max_count=10)
```

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:nobrowning/ietf-mail-mcp.git
cd ietf-mail-mcp
uv sync
```

## Integration

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "ietf-mail": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/ietf-mail-mcp", "python", "server.py"]
    }
  }
}
```

**Config file locations:**

| Client | Path |
|--------|------|
| Claude Code | `~/.claude/settings.json` or `.claude/settings.json` |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Cursor | `.cursor/mcp.json` |
| VS Code (Copilot) | `.vscode/mcp.json` |

## How It Works

1. Fetches the mailing list page from `mailarchive.ietf.org`
2. Automatically paginates via the site's AJAX API until the date range is covered
3. Concurrently fetches full content for each email (10 parallel requests)
4. Returns all emails as formatted text

## Dependencies

- [mcp](https://pypi.org/project/mcp/) - Model Context Protocol SDK
- [httpx](https://pypi.org/project/httpx/) - Async HTTP client
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) - HTML parser

---

# ietf-mail-mcp

一个 MCP（模型上下文协议）服务器，用于从 [IETF 邮件归档](https://mailarchive.ietf.org) 抓取和阅读邮件。它允许 AI 助手通过一次工具调用浏览任意 IETF 邮件列表并获取完整邮件内容。

## 工具

### `fetch_all_email_details`

获取指定时间范围内 IETF 邮件列表中所有邮件的完整内容。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `list_name` | `str` | 必填 | 邮件列表名称（如 `agent2agent`、`httpbis`、`quic`） |
| `days` | `int` | `0` | 获取最近 N 天的邮件，`0` 表示不限时间 |
| `max_count` | `int` | `50` | 最大获取邮件数量（上限 100） |

**返回：** 格式化文本，包含每封邮件的主题、发件人、日期、完整正文和线程上下文。

**示例：**

```
# 获取 agent2agent 列表最近 3 天的邮件
fetch_all_email_details("agent2agent", days=3)

# 获取 httpbis 列表最新 10 封邮件
fetch_all_email_details("httpbis", max_count=10)
```

## 安装

需要 [uv](https://docs.astral.sh/uv/)。

```bash
git clone git@github.com:nobrowning/ietf-mail-mcp.git
cd ietf-mail-mcp
uv sync
```

## 集成配置

在 MCP 客户端配置中添加：

```json
{
  "mcpServers": {
    "ietf-mail": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/ietf-mail-mcp", "python", "server.py"]
    }
  }
}
```

**配置文件位置：**

| 客户端 | 路径 |
|--------|------|
| Claude Code | `~/.claude/settings.json` 或 `.claude/settings.json` |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Cursor | `.cursor/mcp.json` |
| VS Code (Copilot) | `.vscode/mcp.json` |

## 工作原理

1. 从 `mailarchive.ietf.org` 获取邮件列表页面
2. 通过站点的 AJAX API 自动翻页，直到覆盖指定的时间范围
3. 并发获取每封邮件的完整内容（10 个并行请求）
4. 以格式化文本返回所有邮件

## 依赖

- [mcp](https://pypi.org/project/mcp/) - 模型上下文协议 SDK
- [httpx](https://pypi.org/project/httpx/) - 异步 HTTP 客户端
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/) - HTML 解析器
