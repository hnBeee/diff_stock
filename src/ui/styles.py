"""CSS — clean, unik, responsif, light & dark."""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

.block-container {
    padding-top: 1.1rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 1.2rem !important;
    padding-right: 1.2rem !important;
    max-width: 1120px;
}

/* Sidebar toggle always visible */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    z-index: 999999 !important;
    background: #0f766e !important;
    color: #fff !important;
    border-radius: 0 10px 10px 0 !important;
    width: 34px !important;
    height: 42px !important;
    box-shadow: 2px 2px 10px rgba(0,0,0,0.15) !important;
}
[data-testid="collapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] svg {
    fill: #fff !important;
}

header[data-testid="stHeader"] { background: transparent !important; }

/* Header */
.main-header {
    background: linear-gradient(135deg, #134e4a 0%, #0f766e 45%, #14b8a6 100%);
    border-radius: 18px;
    padding: 1.4rem 1.6rem 1.35rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 8px 28px rgba(15, 118, 110, 0.28);
    position: relative;
    overflow: hidden;
}
.main-header::after {
    content: "";
    position: absolute;
    right: -40px; top: -40px;
    width: 140px; height: 140px;
    background: rgba(255,255,255,0.08);
    border-radius: 50%;
}
.header-badge {
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    background: rgba(255,255,255,0.18);
    color: #ecfdf5;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    margin-bottom: 0.45rem;
}
.main-header h1 {
    margin: 0;
    font-size: 1.55rem;
    font-weight: 700;
    color: #fff !important;
    letter-spacing: -0.03em;
}
.main-header p {
    margin: 0.35rem 0 0;
    color: rgba(255,255,255,0.88) !important;
    font-size: 0.92rem;
}

/* Metric cards */
.metric-card {
    background: var(--card-bg, #fff);
    border: 1px solid var(--card-border, #e2e8f0);
    border-radius: 14px;
    padding: 0.95rem 1rem;
    text-align: center;
    height: 100%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.07);
}
.metric-card .label {
    font-size: 0.75rem;
    font-weight: 500;
    color: #64748b;
    margin-bottom: 0.25rem;
}
.metric-card .value {
    font-size: 1.22rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.02em;
}
.metric-card .value.positive { color: #059669; }
.metric-card .value.negative { color: #dc2626; }
.metric-card .value.neutral  { color: #0f766e; }

.section-title {
    font-size: 1.05rem;
    font-weight: 650;
    color: #0f172a;
    margin: 0.6rem 0 0.7rem;
    padding-left: 0.55rem;
    border-left: 3px solid #14b8a6;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #f8fafc !important;
    border-right: 1px solid #e2e8f0;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] .stMarkdown {
    color: #1e293b !important;
}
[data-testid="stSidebar"] .stTextInput input {
    background: #fff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 9px !important;
}
[data-testid="stSidebar"] div.stButton > button {
    background: #fff !important;
    color: #0f172a !important;
    border: 1.5px solid #94a3b8 !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] div.stButton > button:hover {
    background: #0f766e !important;
    color: #fff !important;
    border-color: #0f766e !important;
}

/* Buttons */
div.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    transition: all 0.14s ease !important;
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0f766e, #14b8a6) !important;
    border: none !important;
    color: #fff !important;
}
div.stButton > button[kind="primary"]:hover {
    filter: brightness(1.08);
    box-shadow: 0 4px 14px rgba(15, 118, 110, 0.35) !important;
    transform: translateY(-1px);
}
div.stButton > button:not([kind="primary"]) {
    background: #f8fafc !important;
    color: #0f172a !important;
    border: 1.5px solid #94a3b8 !important;
}
div.stButton > button:not([kind="primary"]):hover {
    background: #0f766e !important;
    color: #fff !important;
    border-color: #0f766e !important;
}

div.stDownloadButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    background: #f0fdfa !important;
    border: 1.5px solid #5eead4 !important;
    color: #0f766e !important;
}
div.stDownloadButton > button:hover {
    background: #0f766e !important;
    color: #fff !important;
    border-color: #0f766e !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #f1f5f9;
    padding: 5px;
    border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: #fff !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.stTextArea textarea {
    border-radius: 10px !important;
    border: 1px solid #cbd5e1 !important;
    font-size: 0.88rem !important;
}
.stTextArea textarea:focus {
    border-color: #0f766e !important;
    box-shadow: 0 0 0 2px rgba(15, 118, 110, 0.18) !important;
}

[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* Dark */
[data-theme="dark"] .metric-card,
.stApp[data-theme="dark"] .metric-card {
    background: #1e293b;
    border-color: #334155;
}
[data-theme="dark"] .metric-card .label { color: #94a3b8; }
[data-theme="dark"] .metric-card .value { color: #f1f5f9; }
[data-theme="dark"] .section-title { color: #f1f5f9; }

[data-theme="dark"] [data-testid="stSidebar"],
.stApp[data-theme="dark"] [data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right-color: #1e293b;
}
[data-theme="dark"] [data-testid="stSidebar"] label,
[data-theme="dark"] [data-testid="stSidebar"] p,
[data-theme="dark"] [data-testid="stSidebar"] span {
    color: #e2e8f0 !important;
}
[data-theme="dark"] [data-testid="stSidebar"] .stTextInput input {
    background: #1e293b !important;
    color: #f1f5f9 !important;
    border-color: #334155 !important;
}
[data-theme="dark"] div.stButton > button:not([kind="primary"]),
.stApp[data-theme="dark"] div.stButton > button:not([kind="primary"]) {
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border-color: #64748b !important;
}
[data-theme="dark"] div.stButton > button:not([kind="primary"]):hover,
.stApp[data-theme="dark"] div.stButton > button:not([kind="primary"]):hover {
    background: #0f766e !important;
    color: #fff !important;
}
[data-theme="dark"] .stTabs [data-baseweb="tab-list"] { background: #1e293b; }
[data-theme="dark"] .stTabs [aria-selected="true"] { background: #334155 !important; }

@media (max-width: 768px) {
    .main-header h1 { font-size: 1.28rem; }
    .metric-card .value { font-size: 1.08rem; }
    .block-container {
        padding-left: 0.65rem !important;
        padding-right: 0.65rem !important;
    }
}

footer { visibility: hidden; }
</style>
"""
