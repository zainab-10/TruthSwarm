import os, json, re, time
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from ddgs import DDGS
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.2)
# ---- shared state passed between agents ----
class State(TypedDict):
    article: str
    claims: List[str]
    evidence: dict          # claim -> list of {snippet, url}
    verdicts: dict          # claim -> {verdict, confidence, reason}
    report: str
    attempts: int           # retry counter for the loop


# ---- free web search, no API key ----
def web_search(query, k=5):
    try:
        with DDGS() as ddgs:
            return [{"snippet": r.get("body", ""), "url": r.get("href", "")}
                    for r in ddgs.text(query, max_results=k)]
    except Exception:
        time.sleep(1)                      # back off if rate-limited
        return []


# ---- robust helpers ---------------------------------------------------
def ask(prompt):
    """Call the model and ALWAYS return a plain string.
    Newer Gemini models can return content as a list of parts."""
    resp = llm.invoke(prompt)
    content = resp.content
    if isinstance(content, list):          # list of parts -> join the text
        parts = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict):
                parts.append(p.get("text", ""))
        return "".join(parts)
    return str(content)


def extract_json(text):
    """Pull the first JSON object/array out of a model reply,
    stripping ```json fences and any surrounding prose."""
    text = text.strip()
    # remove code fences if present
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    # find the first [...] or {...} block
    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if match:
        text = match.group(1)
    return json.loads(text)


# ---- 1. READER ----
def reader(state: State):
    out = ask("Extract every distinct, checkable factual claim from this "
              "text. Return ONLY a JSON array of strings, nothing else.\n\n"
              f"{state['article']}")
    try:
        claims = extract_json(out)
        if not isinstance(claims, list):
            claims = [str(claims)]
    except Exception:
        # fallback: split into sentences if the model didn't give JSON
        claims = [s.strip() for s in re.split(r"[.\n]", state["article"])
                  if len(s.strip()) > 10]
    return {"claims": claims, "evidence": {}, "attempts": 0}


# ---- 2. DETECTIVE ----
def detective(state: State):
    evidence = dict(state.get("evidence", {}))
    for claim in state["claims"]:
        if state["attempts"] == 0:
            q = claim
        else:
            q = ask(f"Rewrite this as a sharper web-search query, "
                    f"return only the query text:\n{claim}")
        evidence[claim] = web_search(q)
    return {"evidence": evidence, "attempts": state["attempts"] + 1}


# ---- 3. JUDGE ----
def judge(state: State):
    verdicts = {}
    for claim, ev in state["evidence"].items():
        out = ask(
            f"Claim: {claim}\nEvidence: {json.dumps(ev)}\n\n"
            f'Reply with ONLY a JSON object, no prose: '
            f'{{"verdict": one of ["True","False","Misleading","Unverifiable"], '
            f'"confidence": a number 0 to 1, "reason": "one short sentence"}}')
        try:
            v = extract_json(out)
        except Exception:
            v = {"verdict": "Unverifiable", "confidence": 0.0,
                 "reason": "Could not parse evidence."}
        # normalise types
        try:
            v["confidence"] = float(v.get("confidence", 0))
        except Exception:
            v["confidence"] = 0.0
        v.setdefault("verdict", "Unverifiable")
        v.setdefault("reason", "")
        verdicts[claim] = v
    return {"verdicts": verdicts}


# ---- the loop decision ----
def should_retry(state: State):
    weak = any(v["confidence"] < 0.5 for v in state["verdicts"].values())
    if weak and state["attempts"] < 3:      # cap retries at 3
        return "detective"
    return "editor"


# ---- 4. EDITOR ----
def editor(state: State):
    report = ask(
        "Write a concise fact-check report in markdown. Start with an overall "
        "trust score 0-100, then list each claim with its verdict, the reason, "
        "and its source URLs.\n\n"
        f"Verdicts: {json.dumps(state['verdicts'])}\n"
        f"Evidence: {json.dumps(state['evidence'])}")
    return {"report": report}


# ---- wire the graph ----
def build_graph():
    g = StateGraph(State)
    g.add_node("reader", reader)
    g.add_node("detective", detective)
    g.add_node("judge", judge)
    g.add_node("editor", editor)
    g.set_entry_point("reader")
    g.add_edge("reader", "detective")
    g.add_edge("detective", "judge")
    g.add_conditional_edges("judge", should_retry,
                            {"detective": "detective", "editor": "editor"})
    g.add_edge("editor", END)
    return g.compile()