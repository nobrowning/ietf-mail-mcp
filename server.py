"""IETF Mail Archive MCP Server

Provides tools to browse and read emails from https://mailarchive.ietf.org
"""

import asyncio
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ietf-mail-archive")

BASE_URL = "https://mailarchive.ietf.org"
HEADERS = {
    "User-Agent": "IETF-Mail-Archive-MCP/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
PAGE_SIZE = 20
CONCURRENCY = 10  # max concurrent detail requests


def _parse_message_rows(soup: BeautifulSoup) -> list[dict]:
    """Parse .xtr rows into message dicts."""
    messages = []
    for row in soup.select(".xtr"):
        cells = row.select(".xtd")
        msg = {}
        for cell in cells:
            classes = cell.get("class", [])
            text = cell.get_text(strip=True)
            if any("subj-col" in c for c in classes):
                a = cell.select_one("a")
                msg["subject"] = a.get_text(strip=True) if a else text
            elif any("from-col" in c for c in classes):
                msg["from"] = text
            elif any("date-col" in c for c in classes):
                msg["date"] = text
            elif any("url-col" in c for c in classes):
                msg["url"] = text
            elif any("id-col" in c for c in classes):
                msg["id"] = text
            elif any("thread-col" in c for c in classes):
                msg["thread_id"] = text
        if msg.get("id"):
            messages.append(msg)
    return messages


def _filter_by_date(
    messages: list[dict], start_date: str | None, end_date: str | None
) -> list[dict]:
    """Filter messages by date range (YYYY-MM-DD)."""
    if not start_date and not end_date:
        return messages
    filtered = []
    for msg in messages:
        msg_date = msg.get("date", "")
        if not msg_date:
            continue
        if start_date and msg_date < start_date:
            continue
        if end_date and msg_date > end_date:
            continue
        filtered.append(msg)
    return filtered


async def _fetch_email_list(
    client: httpx.AsyncClient,
    list_name: str,
    days: int = 0,
    max_count: int = 200,
) -> list[dict]:
    """Fetch email list with pagination. Returns list of message dicts."""
    max_count = min(max_count, 500)

    effective_start = None
    if days > 0:
        effective_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/arch/browse/{list_name}/?"
    resp = await client.get(url)
    if resp.status_code != 200:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    all_messages = _parse_message_rows(soup)

    collected = len(all_messages)
    while True:
        if not effective_start and collected >= max_count:
            break
        if effective_start and all_messages:
            oldest_date = all_messages[-1].get("date", "")
            if oldest_date and oldest_date < effective_start:
                break
        if collected >= max_count + 200:
            break
        if not all_messages:
            break
        last_id = all_messages[-1].get("id")
        if not last_id:
            break

        next_count = collected + PAGE_SIZE
        ajax_url = (
            f"{BASE_URL}/arch/ajax/messages/?"
            f"qid=&referenceitem={next_count}"
            f"&browselist={list_name}"
            f"&referenceid={last_id}"
            f"&direction=next"
        )
        resp = await client.get(ajax_url)
        if resp.status_code != 200:
            break

        page_soup = BeautifulSoup(resp.text, "html.parser")
        new_messages = _parse_message_rows(page_soup)
        if not new_messages:
            break

        seen_ids = {m["id"] for m in all_messages}
        added = 0
        for msg in new_messages:
            if msg["id"] not in seen_ids:
                all_messages.append(msg)
                seen_ids.add(msg["id"])
                added += 1
        if added == 0:
            break
        collected = len(all_messages)

    filtered = _filter_by_date(all_messages, effective_start, None)
    return filtered[:max_count]


async def _fetch_email_detail(client: httpx.AsyncClient, msg_id: str) -> dict:
    """Fetch a single email's detail. Returns a dict."""
    ajax_url = f"{BASE_URL}/arch/ajax/msg/?id={msg_id}"
    resp = await client.get(ajax_url)
    if resp.status_code != 200:
        return {"msg_id": msg_id, "error": f"HTTP {resp.status_code}"}

    soup = BeautifulSoup(resp.text, "html.parser")

    h3 = soup.select_one("h3")
    subject = h3.get_text(strip=True) if h3 else "Unknown Subject"

    msg_info = soup.select_one("#msg-info")
    from_addr = ""
    date_str = ""
    if msg_info:
        info_text = msg_info.get_text(separator="\n", strip=True)
        info_lines = [l.strip() for l in info_text.split("\n") if l.strip()]
        if len(info_lines) >= 1:
            from_addr = info_lines[0]
        if len(info_lines) >= 2:
            date_str = info_lines[1]

    payload = soup.select_one(".msg-payload")
    body = payload.get_text(separator="\n").strip() if payload else ""

    thread_div = soup.select_one("#message-thread")
    thread = []
    if thread_div:
        for a in thread_div.select("a")[:10]:
            thread.append(a.get_text(strip=True))

    return {
        "msg_id": msg_id,
        "subject": subject,
        "from": from_addr,
        "date": date_str,
        "body": body,
        "thread": thread,
    }


def _format_detail(detail: dict) -> str:
    """Format a single email detail dict into readable text."""
    if "error" in detail:
        return f"[Message {detail['msg_id']}] Error: {detail['error']}"

    thread_str = ""
    if detail.get("thread"):
        thread_str = "\nThread:\n" + "\n".join(f"  - {t}" for t in detail["thread"])

    return (
        f"Subject: {detail['subject']}\n"
        f"From: {detail['from']}\n"
        f"Date: {detail['date']}\n"
        f"Message ID: {detail['msg_id']}\n"
        f"\n{detail['body']}"
        f"{thread_str}"
    )


# ---- MCP Tools ----


# @mcp.tool()
# async def list_emails(
#     list_name: str,
#     days: int = 0,
#     max_count: int = 200,
# ) -> str:
#     """List recent emails from an IETF mailing list."""
#     async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
#         result = await _fetch_email_list(client, list_name, days, max_count)
#     if not result:
#         return f"No emails found in list '{list_name}' for the given criteria."
#     date_hint = ""
#     if days > 0:
#         since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
#         date_hint = f" (last {days} days, since {since})"
#     lines = [f"Found {len(result)} emails in [{list_name}]{date_hint}:\n"]
#     for i, msg in enumerate(result, 1):
#         lines.append(
#             f"{i}. [{msg.get('date', '?')}] {msg.get('subject', '?')}\n"
#             f"   From: {msg.get('from', '?')} | ID: {msg.get('id', '?')}"
#         )
#     return "\n".join(lines)


# @mcp.tool()
# async def get_email_detail(msg_id: str) -> str:
#     """Get the detailed content of a specific email by its message ID."""
#     async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
#         detail = await _fetch_email_detail(client, msg_id)
#     return _format_detail(detail)


@mcp.tool()
async def fetch_all_email_details(
    list_name: str,
    days: int = 0,
    max_count: int = 50,
) -> str:
    """Fetch the full content of every email in a mailing list within the given range.

    This combines list_emails + get_email_detail: it first fetches the email list,
    then concurrently fetches the detail of each email and returns all of them.

    Args:
        list_name: Name of the mailing list (e.g. "agent2agent", "httpbis", "quic")
        days: Fetch emails from the last N days (e.g. 3 = last 3 days). 0 means no date filter.
        max_count: Maximum number of emails to fetch details for (default 50, max 100)
    """
    max_count = min(max_count, 100)

    async with httpx.AsyncClient(headers=HEADERS, timeout=60, follow_redirects=True) as client:
        # Step 1: Get the email list
        email_list = await _fetch_email_list(client, list_name, days, max_count)

        if not email_list:
            return f"No emails found in list '{list_name}' for the given criteria."

        # Step 2: Concurrently fetch all details with semaphore
        sem = asyncio.Semaphore(CONCURRENCY)

        async def _fetch_with_sem(msg_id: str) -> dict:
            async with sem:
                return await _fetch_email_detail(client, msg_id)

        tasks = [_fetch_with_sem(msg["id"]) for msg in email_list]
        details = await asyncio.gather(*tasks)

    # Step 3: Format output
    date_hint = ""
    if days > 0:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        date_hint = f" (last {days} days, since {since})"

    separator = "\n" + "=" * 60 + "\n"
    header = f"Fetched {len(details)} email details from [{list_name}]{date_hint}:\n"

    parts = [header]
    for i, detail in enumerate(details, 1):
        parts.append(f"[{i}/{len(details)}]\n{_format_detail(detail)}")

    return separator.join(parts)


if __name__ == "__main__":
    mcp.run(transport="stdio")
