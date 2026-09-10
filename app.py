import json
import streamlit as st
from graph import build_graph

# ----------------------------------------------------------------------
# Page config + styling
# ----------------------------------------------------------------------
st.set_page_config(page_title="TruthSwarm", page_icon="🔎", layout="wide")

st.markdown("""
<style>
    /* ---- global ---- */
    .stApp { background: radial-gradient(1200px 600px at 20% -10%, #10203a 0%, #0a0e14 55%); }
    .block-container { padding-top: 2.5rem; }

    /* ---- animated gradient title ---- */
    @keyframes shimmer { 0%{background-position:0% 50%} 100%{background-position:200% 50%} }
    .main-title {
        font-size: 4.2rem; font-weight: 900; letter-spacing: -2px; line-height: 1.05;
        background: linear-gradient(90deg,#4fd1c5,#63b3ed,#9f7aea,#4fd1c5);
        background-size: 200% auto;
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        animation: shimmer 5s linear infinite; margin-bottom:.2rem;
    }
    .subtitle { color:#a0aec0; font-size:1.3rem; margin-top:0; font-weight:400; }
    .subtitle b { color:#4fd1c5; }

    /* ---- larger base text ---- */
    html, body, [class*="css"] { font-size: 17px; }
    .stTextArea textarea { font-size:1.15rem !important; line-height:1.6 !important; }
    .stTextArea textarea::placeholder { color:#5a6b82 !important; }

    /* ---- input glass card ---- */
    .stTextArea textarea {
        background:rgba(20,26,35,.7) !important; border:1px solid #2d3748 !important;
        border-radius:14px !important; backdrop-filter:blur(6px);
    }
    .stTextArea textarea:focus {
        border-color:#4fd1c5 !important; box-shadow:0 0 0 3px rgba(79,209,197,.15) !important;
    }

    /* ---- run button ---- */
    .stButton button {
        font-size:1.25rem !important; font-weight:800 !important; padding:.85rem !important;
        border-radius:14px !important; border:none !important;
        background:linear-gradient(90deg,#4fd1c5,#38b2ac) !important; color:#06231f !important;
        transition:transform .15s, box-shadow .2s !important;
    }
    .stButton button:hover {
        transform:translateY(-2px) !important;
        box-shadow:0 8px 24px rgba(79,209,197,.4) !important;
    }

    /* ---- how-it-works side steps ---- */
    .hiw-step {
        background:rgba(20,26,35,.6); border:1px solid #232d3b; border-radius:12px;
        padding:.8rem 1rem; margin:.5rem 0; font-size:1.05rem; color:#cbd5e0;
        transition:all .2s;
    }
    .hiw-step:hover { border-color:#4fd1c5; transform:translateX(4px); }
    .hiw-step b { color:#fff; }

    /* ---- agent pipeline chips ---- */
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.55} }
    .agent-chip {
        display:inline-block; padding:.7rem 1.3rem; margin:.35rem;
        border-radius:999px; border:1.5px solid #2d3748; color:#8b98a9;
        font-size:1.1rem; font-weight:600; transition:all .35s;
    }
    .agent-active {
        border-color:#4fd1c5; color:#4fd1c5; background:rgba(79,209,197,.1);
        box-shadow:0 0 18px rgba(79,209,197,.5); animation:pulse 1.2s ease-in-out infinite;
    }
    .agent-done { border-color:#48bb78; color:#48bb78; background:rgba(72,187,120,.1); }

    /* ---- claim cards ---- */
    @keyframes slideup { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:none} }
    .claim-card {
        border-radius:14px; padding:1.3rem 1.5rem; margin:.7rem 0;
        border-left:5px solid #4a5568; background:rgba(20,26,35,.75);
        border-top:1px solid #232d3b; border-right:1px solid #232d3b; border-bottom:1px solid #232d3b;
        animation:slideup .4s ease both; transition:transform .15s;
    }
    .claim-card:hover { transform:translateY(-3px); }
    .verdict-badge {
        display:inline-block; padding:.28rem .85rem; border-radius:7px;
        font-weight:800; font-size:.85rem; text-transform:uppercase; letter-spacing:.6px;
    }
    .claim-text { color:#f0f4f8; font-size:1.2rem; margin:.6rem 0; font-weight:600; }
    .claim-reason { color:#9fb0c3; font-size:1.02rem; line-height:1.5; }
    .src-link { color:#63b3ed; font-size:.95rem; text-decoration:none; margin-right:.4rem; }
    .src-link:hover { text-decoration:underline; }
</style>
""", unsafe_allow_html=True)

VERDICT_COLORS = {
    "True":         ("#48bb78", "rgba(72,187,120,.5)"),
    "False":        ("#f56565", "rgba(245,101,101,.5)"),
    "Misleading":   ("#ed8936", "rgba(237,137,54,.5)"),
    "Unverifiable": ("#a0aec0", "rgba(160,174,192,.5)"),
}

# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------
st.markdown('<p class="main-title">🔎 TruthSwarm</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Four AI agents fact-check any article in real time — '
            '<b>Reader → Detective → Judge → Editor</b>, on a 100% free stack.</p>',
            unsafe_allow_html=True)
st.write("")

# ----------------------------------------------------------------------
# Input
# ----------------------------------------------------------------------
col_in, col_side = st.columns([2, 1], gap="large")
with col_in:
    article = st.text_area("Paste an article or claim to verify",
                           height=230, placeholder="e.g. The Great Wall of "
                           "China is visible from the Moon with the naked eye.")
    run = st.button("🚀  Run TruthSwarm", type="primary", use_container_width=True)
with col_side:
    st.markdown("#### How it works")
    st.markdown('<div class="hiw-step">📖 <b>Reader</b> pulls out checkable claims</div>'
                '<div class="hiw-step">🕵️ <b>Detective</b> searches the web for evidence</div>'
                '<div class="hiw-step">⚖️ <b>Judge</b> rules on each claim</div>'
                '<div class="hiw-step">✍️ <b>Editor</b> writes the trust report</div>',
                unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------
AGENTS = [("reader", "📖 Reader"), ("detective", "🕵️ Detective"),
          ("judge", "⚖️ Judge"), ("editor", "✍️ Editor")]

def render_pipeline(active=None, done=()):
    chips = ""
    for key, label in AGENTS:
        cls = "agent-chip"
        if key in done:      cls += " agent-done"
        elif key == active:  cls += " agent-active"
        chips += f'<span class="{cls}">{label}</span>'
    return f'<div style="margin:1.5rem 0;text-align:center">{chips}</div>'

if run and article.strip():
    graph = build_graph()
    pipe = st.empty()
    done, final = [], None

    for step in graph.stream({"article": article}):
        for node, state in step.items():
            pipe.markdown(render_pipeline(active=node, done=done),
                          unsafe_allow_html=True)
            if node not in done:
                done.append(node)
            final = state

    pipe.markdown(render_pipeline(done=[a[0] for a in AGENTS]),
                  unsafe_allow_html=True)
    st.divider()

    verdicts = final.get("verdicts", {})
    evidence = final.get("evidence", {})

    # ---- overall trust score ----
    if verdicts:
        score_map = {"True": 100, "Misleading": 45, "Unverifiable": 50, "False": 0}
        avg = sum(score_map.get(v.get("verdict", "Unverifiable"), 50)
                  for v in verdicts.values()) / len(verdicts)
        c1, c2 = st.columns([1, 2], gap="large")
        with c1:
            color = "#48bb78" if avg >= 66 else "#ed8936" if avg >= 33 else "#f56565"
            st.markdown(f'<div style="text-align:center;padding:1.5rem;border-radius:18px;'
                        f'background:rgba(20,26,35,.8);border:1px solid #2d3748;'
                        f'box-shadow:0 0 30px {color}22">'
                        f'<div style="color:#8b98a9;font-size:.95rem;text-transform:uppercase;'
                        f'letter-spacing:1.5px">Overall Trust Score</div>'
                        f'<div style="font-size:4.5rem;font-weight:900;color:{color};line-height:1.1">'
                        f'{int(avg)}<span style="font-size:1.6rem;color:#8b98a9">/100</span></div>'
                        f'</div>', unsafe_allow_html=True)
        with c2:
            counts = {}
            for v in verdicts.values():
                k = v.get("verdict", "Unverifiable")
                counts[k] = counts.get(k, 0) + 1
            st.markdown("##### Verdict breakdown")
            badges = ""
            for verd, n in counts.items():
                col = VERDICT_COLORS.get(verd, ("#a0aec0",))[0]
                badges += (f'<span class="verdict-badge" style="background:{col}22;'
                           f'color:{col};margin:.3rem;font-size:1rem">{verd}: {n}</span>')
            st.markdown(badges, unsafe_allow_html=True)
        st.write("")

    # ---- per-claim cards ----
    st.markdown("### 🧾 Claim-by-claim")
    for claim, v in verdicts.items():
        verd = v.get("verdict", "Unverifiable")
        col, glow = VERDICT_COLORS.get(verd, ("#a0aec0", "rgba(160,174,192,.5)"))
        conf = v.get("confidence", 0)
        srcs = evidence.get(claim, [])[:3]
        links = " ".join(f'<a class="src-link" href="{s["url"]}" '
                         f'target="_blank">🔗 source {i+1}</a>'
                         for i, s in enumerate(srcs)) or "<span style='color:#4a5568'>no sources</span>"
        st.markdown(
            f'<div class="claim-card" style="border-left-color:{col};box-shadow:0 4px 20px {glow}22">'
            f'<span class="verdict-badge" style="background:{col}22;color:{col}">{verd}</span>'
            f'<span style="color:#8b98a9;font-size:.9rem;margin-left:.7rem">'
            f'confidence {conf:.0%}</span>'
            f'<div class="claim-text">{claim}</div>'
            f'<div class="claim-reason">{v.get("reason","")}</div>'
            f'<div style="margin-top:.7rem">{links}</div>'
            f'</div>', unsafe_allow_html=True)

    # ---- full editor report ----
    with st.expander("📄 Full report (Editor)"):
        st.markdown(final.get("report", "*No report generated.*"))

elif run:
    st.warning("Paste some text first.")