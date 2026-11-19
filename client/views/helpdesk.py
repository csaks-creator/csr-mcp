"""
IT Service Desk Assistant: a thin chat client.

It sends the user's message to the help desk Lambda and displays the reply. All logic
(invoke the harness, run the tool loop, build the reply) lives in the Lambda.

Configuration (environment variables):
    HELPDESK_LAMBDA_ARN  ARN of the help desk agent Lambda (required)
    HELPDESK_REGION      AWS region of that Lambda (default: us-east-1)
"""

import json
import os
import uuid

import boto3
import streamlit as st

REGION = os.environ.get("HELPDESK_REGION", "us-east-1")
LAMBDA_ARN = os.environ.get("HELPDESK_LAMBDA_ARN", "")


@st.cache_resource
def _lambda_client(region: str):
    return boto3.client("lambda", region_name=region)


def _get_session_id() -> str:
    """One harness session id per browser session, so the agent remembers
    earlier turns within this chat. Reset by 'Start new chat'."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = "ticket-session-" + uuid.uuid4().hex
    return st.session_state.session_id


def ask_agent(message: str) -> str:
    if not LAMBDA_ARN:
        raise RuntimeError("HELPDESK_LAMBDA_ARN is not set")
    resp = _lambda_client(REGION).invoke(
        FunctionName=LAMBDA_ARN,
        Payload=json.dumps(
            {
                "message": message,
                "session_id": _get_session_id(),  # same id across the whole chat
            }
        ).encode(),
    )
    data = json.loads(resp["Payload"].read() or b"{}")
    # Keep whatever session id the Lambda used (it echoes it back).
    if isinstance(data, dict) and data.get("session_id"):
        st.session_state.session_id = data["session_id"]
    return data.get("reply", str(data)) if isinstance(data, dict) else str(data)


# ---------------------------------------------------------------------------
# Sidebar: IT Help Desk panel
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="hd-head">
          <div class="hd-logo">🛟</div>
          <div><div class="hd-title">IT Help Desk</div><div class="hd-sub">We're here to help</div></div>
        </div>
        <a class="hd-card" href="tel:+18005551234">
          <div class="hd-ic">📞</div>
          <div><div class="hd-k">Call us</div><div class="hd-v">+1 (800) 555-1234</div>
          <div class="hd-note">Press 1 for urgent / outage</div></div>
        </a>
        <a class="hd-card" href="mailto:servicedesk@company.com">
          <div class="hd-ic">✉️</div>
          <div><div class="hd-k">Email</div><div class="hd-v">servicedesk@company.com</div>
          <div class="hd-note">Reply within 1 business hour</div></div>
        </a>
        <div class="hd-card">
          <div class="hd-ic">🕐</div>
          <div><div class="hd-k">Support hours</div><div class="hd-v">Mon–Fri · 8:00–20:00</div>
          <div class="hd-note">24/7 for Sev-1 incidents</div></div>
        </div>
        <div class="hd-card">
          <div class="hd-ic">🚨</div>
          <div><div class="hd-k">Security hotline</div><div class="hd-v">+1 (800) 555-0000</div>
          <div class="hd-note">Phishing · lost device · breach</div></div>
        </div>
        <div class="hd-sec">Self-service</div>
        <div class="hd-links">
          <a href="#">🔑 Reset your password</a>
          <a href="#">📶 VPN setup guide</a>
          <a href="#">🖨 Printer troubleshooting</a>
          <a href="#">🎫 View my tickets</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    if st.button("🔄 Start new chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = "ticket-session-" + uuid.uuid4().hex  # fresh harness session
        st.rerun()


# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <div class="logo">AC</div>
      <div>
        <div class="kick">Powered by Amazon Bedrock AgentCore · Harness</div>
        <h1>🎫 IT Service Desk Assistant</h1>
        <div class="sub">Search knowledge · guide troubleshooting · raise tickets</div>
      </div>
      <div class="badge">harness_ticket</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if not st.session_state.messages:
    st.markdown(
        """
        <div class="chips">
          <span>🔌 “Why can't I connect to the corporate VPN? It times out.”</span>
          <span>🔑 “I'm locked out of my account.”</span>
          <span>🖨 “Raise a Jira ticket for a broken printer in room 101.”</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

if prompt := st.chat_input("Describe your IT issue…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Working on it…"):
                reply = ask_agent(prompt)
        except Exception as e:  # missing config, credentials or Lambda errors surface in the chat
            st.error(f"Could not reach the help desk agent: {type(e).__name__}: {e}")
        else:
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
