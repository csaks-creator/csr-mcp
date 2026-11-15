import fnmatch
import ipaddress
import os
import secrets
import socket
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from nova_act import GuardrailDecision, GuardrailInputState

_bearer = HTTPBearer(auto_error=False)


def verify_token(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> None:
    if os.environ.get("AUTH_DISABLED") == "1":
        return
    expected = os.environ.get("MCP_API_TOKEN")
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "MCP_API_TOKEN is not configured")
    if creds is None or not secrets.compare_digest(creds.credentials, expected):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid or missing bearer token", headers={"WWW-Authenticate": "Bearer"}
        )


def _allowed_domains() -> list[str]:
    return [d.strip().lower() for d in os.environ.get("ALLOWED_DOMAINS", "").split(",") if d.strip()]


def _host_allowed(hostname: str) -> bool:
    patterns = _allowed_domains()
    return not patterns or any(fnmatch.fnmatch(hostname.lower(), p) for p in patterns)


def _is_public_ip(addr: str) -> bool:
    try:
        return ipaddress.ip_address(addr).is_global
    except ValueError:
        return False


def validate_url(url: str) -> str:
    """Reject non-http(s) URLs and hosts that resolve to private, loopback or link-local addresses."""
    parsed = urlparse(url)
    host = parsed.hostname
    if parsed.scheme not in ("http", "https") or not host:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "url must be an absolute http(s) URL")
    if not _host_allowed(host):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"host '{host}' is not in ALLOWED_DOMAINS")
    try:
        addrs = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"cannot resolve host '{host}'")
    if not addrs or not all(_is_public_ip(a) for a in addrs):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"host '{host}' resolves to a non-public address")
    return url


def state_guardrail(state: GuardrailInputState) -> GuardrailDecision:
    """Keep the browser on allowed, public hosts for every navigation the agent attempts."""
    parsed = urlparse(state.browser_url)
    if parsed.scheme == "about":
        return GuardrailDecision.PASS
    host = parsed.hostname
    if parsed.scheme not in ("http", "https") or not host or host == "localhost":
        return GuardrailDecision.BLOCK
    try:
        if not ipaddress.ip_address(host).is_global:
            return GuardrailDecision.BLOCK
    except ValueError:
        pass
    return GuardrailDecision.PASS if _host_allowed(host) else GuardrailDecision.BLOCK
