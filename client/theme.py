import streamlit as st


def inject_theme() -> None:
    """Dark navy + teal theme shared by every page."""
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
