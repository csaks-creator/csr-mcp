"""Smoke test for a deployed Nova Act MCP server. Needs only Python 3.9+ (standard library).

Usage:
    python scripts/smoke_test.py --url http://<host>/mcp --token <MCP_API_TOKEN>
    python scripts/smoke_test.py --url http://<host>/mcp --token <MCP_API_TOKEN> --call-tool

MCP_URL and MCP_API_TOKEN environment variables are used when the flags are omitted.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

EXPECTED_TOOLS = {"search_website", "extract_page_data", "fill_form"}


def post(url: str, body: dict, token: str | None, timeout: int) -> tuple[int, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def result_of(text: str) -> dict:
    # Responses are plain JSON, but tolerate an SSE "data:" line.
    for line in text.splitlines():
        if line.startswith("data:"):
            text = line[5:].strip()
            break
    return json.loads(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=os.environ.get("MCP_URL"), help="MCP endpoint, e.g. http://host/mcp")
    parser.add_argument("--token", default=os.environ.get("MCP_API_TOKEN"), help="Bearer token")
    parser.add_argument("--call-tool", action="store_true", help="Also run extract_page_data (uses Nova Act quota)")
    parser.add_argument("--target", default="https://example.com", help="Page used by --call-tool")
    args = parser.parse_args()
    if not args.url or not args.token:
        parser.error("--url and --token (or MCP_URL and MCP_API_TOKEN) are required")

    failures = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        failures += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{': ' + detail if detail and not ok else ''}")

    list_tools = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}

    status, body = post(args.url, list_tools, None, 30)
    check("rejects request without token (401)", status == 401, f"got {status}: {body[:200]}")

    status, body = post(args.url, list_tools, "wrong-token", 30)
    check("rejects wrong token (401)", status == 401, f"got {status}: {body[:200]}")

    status, body = post(args.url, list_tools, args.token, 30)
    check("accepts your token (200)", status == 200, f"got {status}: {body[:200]}")
    if status == 200:
        names = {t["name"] for t in result_of(body)["result"]["tools"]}
        check("lists expected tools", EXPECTED_TOOLS <= names, f"found {sorted(names)}")

    if args.call_tool:
        call = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "extract_page_data",
                "arguments": {"url": args.target, "instruction": "What is the main heading of the page?"},
            },
        }
        status, body = post(args.url, call, args.token, 600)
        ok = status == 200 and not result_of(body)["result"].get("isError")
        check("extract_page_data runs end to end", ok, f"got {status}: {body[:300]}")
        if ok:
            print(result_of(body)["result"]["content"][0]["text"])

    print("All checks passed" if not failures else f"{failures} check(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
