# CLAUDE.md

## 项目概述

ietf-mail-mcp 是一个 MCP（Model Context Protocol）服务器，用于从 IETF 邮件归档站点 (https://mailarchive.ietf.org) 抓取和阅读邮件。

## 语言要求

所有文档、代码注释和对话请使用中文。

## 技术栈

- Python 3.13+
- uv 管理依赖和虚拟环境
- httpx 异步 HTTP 请求
- beautifulsoup4 解析 HTML
- mcp SDK (FastMCP) 提供 MCP 工具

## 项目结构

```
├── server.py          # MCP 服务器，包含所有工具和内部函数
├── pyproject.toml     # 项目配置和依赖声明
├── uv.lock            # 依赖锁定文件
├── .python-version    # Python 版本约束
└── README.md          # 项目说明（中英双语）
```

## 核心架构

`server.py` 包含：

- **内部函数**（不暴露为 MCP 工具）：
  - `_parse_message_rows()` — 解析 HTML 中的 `.xtr` 行为邮件字典列表
  - `_filter_by_date()` — 按日期范围过滤邮件
  - `_fetch_email_list()` — 获取邮件列表，支持自动翻页
  - `_fetch_email_detail()` — 获取单封邮件的完整内容
  - `_format_detail()` — 格式化邮件详情为可读文本

- **MCP 工具**（暴露给 AI 助手调用）：
  - `fetch_all_email_details(list_name, days, max_count)` — 唯一对外工具，一次性获取邮件列表并并发抓取所有邮件详情

## IETF 邮件归档 API

该站点没有正式 JSON API，所有数据通过解析 HTML 获取：

- **首页**：`GET /arch/browse/{list_name}/?` 返回包含 `.xtr` 行的 HTML，每行有 `.xtd` 单元格（subject, from, date, url, id, thread_id）
- **翻页**：`GET /arch/ajax/messages/?qid=&referenceitem={count}&browselist={list_name}&referenceid={last_id}&direction=next` 返回下一批邮件的 HTML 片段
- **邮件详情**：`GET /arch/ajax/msg/?id={msg_id}` 返回包含 `h3`（主题）、`#msg-info`（发件人+日期）、`.msg-payload`（正文）、`#message-thread`（线程）的 HTML

## 常用命令

```bash
# 安装依赖
uv sync

# 运行 MCP 服务器
uv run python server.py

# 快速测试
uv run python -c "
import asyncio
from server import fetch_all_email_details
async def main():
    r = await fetch_all_email_details('agent2agent', days=3)
    print(r)
asyncio.run(main())
"
```

## 注意事项

- 邮件列表按日期降序排列，但同一天内的邮件 ID 不一定严格递减
- 翻页使用 `referenceid` 作为位置标记，不是数值边界
- 并发获取详情时使用信号量（CONCURRENCY=10）控制并发数，避免对服务器造成压力
- `max_count` 上限为 100，防止单次请求过多
