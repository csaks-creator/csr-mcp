import os
import socket

import pytest
from fastapi.testclient import TestClient

from app import nova_service, security
from app.main import app

AUTH = {"Authorization": "Bearer test-token"}
MCP_HEADERS = {**AUTH, "content-type": "application/json", "accept": "application/json, text/event-stream"}


class FakeResult:
    def __init__(self, response=None, parsed=None, matches=True):
        self.response, self.parsed_response, self.matches_schema = response, parsed, matches


class FakeNova:
    def __init__(self, **kwargs):
        assert os.path.isdir(kwargs["logs_directory"]), "NovaAct requires logs_directory to exist"
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def act(self, prompt, **kw):
        return FakeResult()

    def act_get(self, prompt, schema=None, **kw):
        if schema and "results" in schema.get("properties", {}):
            return FakeResult(parsed={"results": [{"title": "A"}, {"title": "B"}, {"title": "C"}]})
        return FakeResult(response="done", parsed={"price": 9.5})


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("MCP_API_TOKEN", "test-token")
    monkeypatch.setattr(nova_service, "NovaAct", FakeNova)
    monkeypatch.setattr(
        security.socket, "getaddrinfo", lambda host, *a, **k: [(socket.AF_INET, 0, 0, "", ("93.184.216.34", 0))]
    )


@pytest.fixture(scope="module")  # one event loop: the MCP session manager starts once per process
def client():
    with TestClient(app) as c:
        yield c


def test_health_is_open(client):
    assert client.get("/health").text == '"ok"'


def test_rest_requires_token(client):
    r = client.post("/search", json={"url": "https://example.com", "query": "x"})
    assert r.status_code == 401


def test_token_whitespace_is_ignored(client, monkeypatch):
    monkeypatch.setenv("MCP_API_TOKEN", "test-token\n")
    r = client.post("/search", headers={"Authorization": "Bearer test-token "}, json={"url": "https://example.com", "query": "x"})
    assert r.status_code == 200


def test_search_limits_results(client):
    r = client.post("/search", headers=AUTH, json={"url": "https://example.com", "query": "x", "max_results": 2})
    assert r.status_code == 200
    assert [x["title"] for x in r.json()["results"]] == ["A", "B"]


def test_extract_with_schema(client):
    body = {"url": "https://example.com", "instruction": "price", "json_schema": {"type": "object"}}
    assert client.post("/extract", headers=AUTH, json=body).json() == {"data": {"price": 9.5}}


def test_fill_form_does_not_submit_by_default(client):
    r = client.post("/fill_form", headers=AUTH, json={"url": "https://example.com", "fields": {"Name": "Ann"}})
    assert r.json() == {"submitted": False, "report": "done"}


@pytest.mark.parametrize("url", ["http://169.254.169.254/latest/meta-data", "http://127.0.0.1:8000", "file:///etc/passwd"])
def test_ssrf_blocked(client, monkeypatch, url):
    monkeypatch.undo()
    monkeypatch.setenv("MCP_API_TOKEN", "test-token")
    monkeypatch.setattr(nova_service, "NovaAct", FakeNova)
    r = client.post("/extract", headers=AUTH, json={"url": url, "instruction": "x"})
    assert r.status_code in (403, 422)


def test_mcp_lists_three_tools(client):
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}},
    }
    r = client.post("/mcp", headers=MCP_HEADERS, json=init)
    assert r.status_code == 200, r.text
    headers = dict(MCP_HEADERS)
    if "mcp-session-id" in r.headers:
        headers["mcp-session-id"] = r.headers["mcp-session-id"]
    client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    r = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    body = r.text
    for name in ("search_website", "extract_page_data", "fill_form"):
        assert name in body, body
    assert "health" not in body


def test_mcp_is_stateless(client):
    # No initialize and no session id: any task behind the load balancer must be able to serve the call.
    call = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "search_website",
            "arguments": {"url": "https://example.com", "query": "x", "max_results": 2},
        },
    }
    r = client.post("/mcp", headers=MCP_HEADERS, json=call)
    assert r.status_code == 200, r.text
    assert '"isError":false' in r.text.replace(" ", "")
    assert "mcp-session-id" not in r.headers


def test_mcp_rejects_missing_token(client):
    r = client.post("/mcp", headers={"content-type": "application/json", "accept": "application/json, text/event-stream"}, json={})
    assert r.status_code == 401
