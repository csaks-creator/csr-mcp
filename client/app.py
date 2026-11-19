import streamlit as st
from theme import inject_theme

st.set_page_config(page_title="IT Service Desk — AgentCore", page_icon="🎫", layout="wide")
inject_theme()

pages = st.navigation(
    [
        st.Page("views/helpdesk.py", title="IT Service Desk", icon="🎫", default=True),
        st.Page("views/mcp_tools.py", title="MCP Tools", icon="🧰"),
    ]
)
pages.run()
