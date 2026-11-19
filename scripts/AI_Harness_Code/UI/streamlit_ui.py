"""
IT Service Desk Assistant — thin Streamlit client with the dark theme.

The app does NO processing: it sends the user's message to the har_invo Lambda
and displays the reply. All logic (invoke harness, tool loop, build reply) is in
the Lambda.

Run:
    pip install streamlit boto3
    streamlit run streamlit_harness_ticket.py
"""

import json
import uuid
import boto3
import streamlit as st

# Change Region and Lambda ARN Details
REGION = "us-east-1"
LAMBDA_ARN = "arn:aws:lambda:us-east-1:196715057542:function:invoke_it_helpdesk_agent"

st.set_page_config(page_title="IT Service Desk — AgentCore", page_icon="🎫", layout="wide")


# ---------------------------------------------------------------------------
# Theme — dark navy + teal (matches the slide deck)
# ---------------------------------------------------------------------------
def inject_theme():
    st.markdown(
        """
        <style>
        :root {
            --bg:#0b1020; --panel:#16203f; --panel2:#1d2b52; --ink:#eaf0ff;
            --muted:#9fb0d6; --accent:#4f8cff; --accent2:#22d3ee; --good:#34d399;
            --line:rgba(255,255,255,0.10);
        }
        .stApp {
            background:
                radial-gradient(1200px 800px at 15% -10%, #1b2a55 0%, transparent 55%),
                radial-gradient(1000px 700px at 100% 0%, #0e2a3a 0%, transparent 50%),
                var(--bg);
            color: var(--ink);
        }
        #MainMenu, header[data-testid="stHeader"], footer { visibility: hidden; }
        .block-container { padding-top: 1.4rem; max-width: 1100px; }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--panel), #0e1730);
            border-right: 1px solid var(--line);
        }
        section[data-testid="stSidebar"] * { color: var(--ink); }

        /* Hero header */
        .hero {
            background: linear-gradient(135deg, #16234a 0%, #0f2740 100%);
            border: 1px solid var(--line); border-radius: 18px;
            padding: 22px 26px; margin-bottom: 18px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.45);
            display: flex; align-items: center; gap: 18px;
        }
        .hero .logo {
            width: 64px; height: 64px; border-radius: 16px; flex: none;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            display: grid; place-items: center; font-weight: 800; font-size: 1.3rem;
            color: #06122c;
        }
        .hero .kick { color: var(--accent2); font-size: .62rem; letter-spacing: .16em;
            text-transform: uppercase; font-weight: 600; margin-bottom: 4px; opacity: .9; }
        .hero h1 { color: var(--ink); font-size: 2.6rem; margin: 0; line-height: 1.05;
            letter-spacing: -0.02em; font-weight: 800; }
        .hero .sub { color: var(--muted); font-size: .95rem; margin-top: 6px; }
        .hero .badge { margin-left: auto; align-self: flex-start; color: var(--good);
            border: 1px solid rgba(52,211,153,.4); background: rgba(52,211,153,.1);
            padding: 5px 13px; border-radius: 999px; font-size: .78rem; font-weight: 600; }

        /* Chat bubbles (native chat_message, forced light text) */
        div[data-testid="stChatMessage"] { background: transparent !important; border: none; }
        div[data-testid="stChatMessageContent"] {
            background: linear-gradient(180deg, var(--panel), var(--panel2));
            border: 1px solid var(--line); border-radius: 14px; padding: 12px 16px;
        }
        div[data-testid="stChatMessage"], div[data-testid="stChatMessage"] *,
        div[data-testid="stChatMessageContent"], div[data-testid="stChatMessageContent"] * {
            color: var(--ink) !important;
        }

        /* Chat input — dark bg + light text */
        div[data-testid="stChatInput"],
        div[data-testid="stChatInput"] > div,
        div[data-testid="stChatInput"] div[data-baseweb="textarea"],
        div[data-testid="stChatInput"] div[data-baseweb="base-input"] {
            background: var(--panel2) !important; border-color: var(--line) !important;
            border-radius: 14px;
        }
        div[data-testid="stChatInput"] textarea {
            background: var(--panel2) !important;
            color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important;
        }
        div[data-testid="stChatInput"] textarea::placeholder {
            color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important; opacity: 1;
        }
        div[data-testid="stChatInput"] button svg { fill: var(--accent2) !important; }

        /* Starter chips */
        .chips { display: flex; gap: 10px; flex-wrap: wrap; margin: 2px 0 14px; }
        .chips span { padding: 7px 14px; border-radius: 999px; border: 1px solid var(--line);
            background: var(--panel); color: var(--muted); font-size: .85rem; }

        /* Help desk sidebar panel */
        .hd-head { display: flex; align-items: center; gap: 12px; margin: 2px 0 16px; }
        .hd-logo { width: 42px; height: 42px; border-radius: 12px; flex: none;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            display: grid; place-items: center; font-size: 1.25rem; }
        .hd-title { color: var(--ink); font-weight: 800; font-size: 1.15rem; line-height: 1.1; }
        .hd-sub { color: var(--muted); font-size: .8rem; }
        .hd-card { display: flex; gap: 12px; align-items: flex-start;
            background: linear-gradient(180deg, var(--panel), var(--panel2));
            border: 1px solid var(--line); border-radius: 12px;
            padding: 12px 14px; margin-bottom: 10px; text-decoration: none; }
        .hd-ic { font-size: 1.3rem; line-height: 1.4; flex: none; }
        .hd-k { color: var(--muted); font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; }
        .hd-v { color: var(--ink); font-weight: 700; font-size: .98rem; }
        .hd-note { color: var(--muted); font-size: .76rem; margin-top: 2px; }
        .hd-sec { color: var(--accent2); font-size: .72rem; letter-spacing: .14em;
            text-transform: uppercase; font-weight: 700; margin: 6px 0 8px; }
        .hd-links { display: flex; flex-direction: column; gap: 6px; }
        .hd-links a { color: var(--ink); text-decoration: none; font-size: .9rem;
            padding: 8px 12px; border-radius: 10px; border: 1px solid var(--line); background: var(--panel); }
        .hd-links a:hover { border-color: rgba(34,211,238,.5); color: var(--accent2); }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_theme()


# ---------------------------------------------------------------------------
# Lambda call (all processing happens there)
# ---------------------------------------------------------------------------
lambda_client = st.cache_resource(lambda: boto3.client("lambda", region_name=REGION))()


def _get_session_id() -> str:
    """One harness session id per browser session, so the agent remembers
    earlier turns within this chat. Reset by 'Start new chat'."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = "ticket-session-" + uuid.uuid4().hex
    return st.session_state.session_id


def ask_agent(message: str) -> str:
    resp = lambda_client.invoke(
        FunctionName=LAMBDA_ARN,
        Payload=json.dumps({
            "message": message,
            "session_id": _get_session_id(),  # same id across the whole chat
        }).encode(),
    )
    data = json.loads(resp["Payload"].read() or b"{}")
    # Keep whatever session id the Lambda used (it echoes it back).
    if isinstance(data, dict) and data.get("session_id"):
        st.session_state.session_id = data["session_id"]
    return data.get("reply", str(data)) if isinstance(data, dict) else str(data)


# ---------------------------------------------------------------------------
# Sidebar — IT Help Desk panel
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
        with st.spinner("Working on it…"):
            reply = ask_agent(prompt)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
