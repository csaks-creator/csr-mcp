import asyncio
import json
import os
from datetime import timedelta

import streamlit as st
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

REQUEST_TIMEOUT = 600  # Nova Act tasks can run for minutes
CONNECT_TIMEOUT = 15  # fail fast when the server is unreachable


async def _run(url: str, token: str, fn):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(
        url, headers=headers, timeout=CONNECT_TIMEOUT, sse_read_timeout=REQUEST_TIMEOUT
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await fn(session)


def _describe(error: BaseException) -> str:
    while isinstance(error, BaseExceptionGroup) and error.exceptions:
        error = error.exceptions[0]
    return f"{type(error).__name__}: {error}"


def _field_type(prop: dict) -> str:
    if "type" in prop:
        return prop["type"]
    for option in prop.get("anyOf", []):
        if option.get("type") != "null":
            return option.get("type", "string")
    return "string"


def _render_field(name: str, prop: dict, required: bool):
    label = f"{prop.get('title', name)}{' *' if required else ''}"
    help_text = prop.get("description")
    default = prop.get("default")
    kind = _field_type(prop)
    if kind == "boolean":
        return st.checkbox(label, value=bool(default), help=help_text, key=name)
    if kind in ("integer", "number"):
        cast = int if kind == "integer" else float
        bounds = {k: cast(prop[j]) for k, j in (("min_value", "minimum"), ("max_value", "maximum")) if j in prop}
        value = st.number_input(
            label,
            value=cast(default) if default is not None else (cast(0) if required else None),
            step=cast(1) if kind == "integer" else 0.1,
            help=help_text,
            key=name,
            **bounds,
        )
        return None if value is None else cast(value)
    if kind in ("object", "array"):
        text = st.text_area(
            f"{label} (JSON)", value=json.dumps(default) if default is not None else "", help=help_text, key=name
        )
        return json.loads(text) if text.strip() else None
    text = st.text_input(label, value=default or "", help=help_text, key=name)
    return text or None


st.title("Nova Act MCP Client")

with st.sidebar:
    server_url = st.text_input("MCP server URL", os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp"))
    env_token = os.environ.get("MCP_API_TOKEN", "").strip()
    override = st.text_input(
        "Bearer token override (optional)" if env_token else "Bearer token", type="password"
    ).strip()
    token = override or env_token
    st.caption(
        f"Token source: {'sidebar' if override else 'environment' if env_token else 'none'}, length {len(token)}"
    )
    if st.button("Refresh tools") or "tools" not in st.session_state:
        try:
            with st.spinner(f"Connecting to {server_url}..."):
                result = asyncio.run(_run(server_url, token, lambda s: s.list_tools()))
            st.session_state.tools = {t.name: t for t in result.tools}
            st.session_state.pop("error", None)
        except Exception as e:  # network and protocol errors surface in the UI
            st.session_state.tools = {}
            st.session_state.error = _describe(e)

if "error" in st.session_state:
    st.error(f"Could not list tools from {server_url}\n\n{st.session_state.error}")

tools = st.session_state.get("tools", {})
if tools:
    st.sidebar.success(f"{len(tools)} tools available")
    name = st.selectbox("Tool", list(tools))
    tool = tools[name]
    st.caption(tool.description or "")
    schema = tool.inputSchema or {}
    required = set(schema.get("required", []))

    with st.form(f"form-{name}"):
        args = {}
        for field, prop in schema.get("properties", {}).items():
            try:
                value = _render_field(f"{name}.{field}", prop, field in required)
            except json.JSONDecodeError:
                st.warning(f"{field}: invalid JSON")
                value = None
            if value is not None:
                args[field] = value
        submitted = st.form_submit_button("Run tool")

    if submitted:
        with st.spinner("Running... browser tasks can take a few minutes"):
            try:
                result = asyncio.run(
                    _run(
                        server_url,
                        token,
                        lambda s: s.call_tool(name, args, read_timeout_seconds=timedelta(seconds=REQUEST_TIMEOUT)),
                    )
                )
            except Exception as e:
                st.error(_describe(e))
            else:
                (st.error if result.isError else st.success)("Tool returned an error" if result.isError else "Done")
                for block in result.content:
                    text = getattr(block, "text", None)
                    if text is None:
                        st.write(block)
                        continue
                    try:
                        st.json(json.loads(text))
                    except ValueError:
                        st.text(text)
