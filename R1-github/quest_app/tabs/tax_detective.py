import streamlit as st
import tax_detective_db
import edu_db
from edu_db import load_progress
import ui_theme

# ── Shared layout helpers ────────────────────────────────────────────────────
# These accept a `practice` flag so both the real run and practice run can
# reuse the same HTML without duplicating full blocks.

def _case_card_html(case: dict, practice: bool = False) -> str:
    snap_rows = "".join([
        f'<div class="td-snap-row"><span>{r[0]}</span><b>{r[1]}</b></div>'
        for r in case["snapshot"]
    ])
    badge = (
        '<div style="font-size:10px; color:var(--q-accent); background:var(--q-accent-weak); '
        'border:1px solid var(--q-accent); padding:7px 10px; border-radius:8px; height:max-content; font-weight:700;">'
        '🕵️ Practice · no retry</div>'
        if practice else
        '<div style="font-size:10px; color:var(--q-accent); background:var(--q-accent-weak); '
        'border:1px solid var(--q-accent); padding:7px 10px; border-radius:8px; height:max-content; font-weight:700;">'
        '🔒 One decision · no retry</div>'
    )
    return f"""
<div class="td-case">
<div class="td-case-top">
<div>
<div class="td-case-id">{case['id']}</div>
<div class="td-case-title">{case['title']}</div>
</div>
{badge}
</div>
<div class="td-scenario">
<div class="td-person">
<div class="td-avatar">{case['avatar']}</div>
<p>{case['scenario']}</p>
</div>
<div class="td-snapshot">
<div class="td-snap-title">Case snapshot</div>
{snap_rows}
</div>
</div>
</div>
"""

def _result_panel_html(res: dict, practice: bool = False) -> str:
    is_correct = res["is_correct"]
    header_text = "Strong investigation." if is_correct else "Good attempt — here's the clue you missed."
    meta_text = (
        ("Practice hit! You got this one right." if is_correct else "Use the explanation to sharpen your approach.")
        if practice else
        ("You identified the key tax concept. +₹5,000 toward your potential reward." if is_correct else "Use the explanation to learn the rule.")
    )
    explanations_html = ""
    for n, exp in enumerate(res["all_explanations"]):
        is_good = (n == res["correct_index"])
        explanations_html += (
            f'<div class="td-why {"good" if is_good else "bad"}">'
            f'<b>Option {chr(65+n)} — {"Best choice" if is_good else "Why not"}:</b> {exp}</div>'
        )
    return f"""
<div class="td-result" style="background: var(--q-surface); border:1px solid var(--q-border); border-radius:18px; margin-top:20px;">
<div style="display:flex; gap:12px; align-items:center; margin-bottom:13px;">
<div style="width:38px; height:38px; border-radius:11px; display:grid; place-items:center; font-weight:900; background:{'var(--q-pos-weak)' if is_correct else 'var(--q-neg-weak)'}; color:{'var(--q-pos)' if is_correct else 'var(--q-neg)'};">
{('✓' if is_correct else '!')}
</div>
<div>
<h2 style="font-size:15px; margin:0 0 3px; color:var(--q-text);">{header_text}</h2>
<div style="font-size:10px; color:var(--q-text-3);">{meta_text}</div>
</div>
</div>
<div class="td-explain">
<div style="font-size:8px; letter-spacing:1.2px; color:var(--q-accent); font-weight:900; margin-bottom:6px;">CASE ANALYSIS</div>
<b>Why your choice {'works' if is_correct else "isn't the strongest"}:</b> {res['explanation']}
<div class="td-takeaway"><b>Key takeaway:</b> {res['takeaway']}</div>
</div>
<div style="margin-top:10px; display:grid; gap:7px;">
{explanations_html}
</div>
</div>
"""

# ── Interactive Option Card component ──────────────────────────────────────

def render_option_cards(choices: list, btn_key_prefix: str) -> int | None:
    """Render answer-option cards using Streamlit columns and native buttons.

    Each card contains:
      - small uppercase label (OPTION A / B / C)
      - bold title
      - muted description
      - a native full-width Streamlit button

    Returns:
        int index of clicked option (0, 1, 2) or None if no button was clicked.
    """
    cols = st.columns(len(choices), gap="medium")
    clicked_idx = None
    for i, (col, ch) in enumerate(zip(cols, choices)):
        letter = chr(65 + i)
        with col:
            with st.container(border=True):
                st.html(f"""
<div class="td-oc-card">
  <div class="td-oc-label">OPTION {letter}</div>
  <div class="td-oc-title">{ch['t']}</div>
  <div class="td-oc-desc">{ch['d']}</div>
</div>
""")
                if st.button(f"Select Option {letter}", key=f"{btn_key_prefix}_{i}", use_container_width=True):
                    clicked_idx = i
    return clicked_idx

# ── Practice-mode state helpers ──────────────────────────────────────────────

def _practice_init():
    """Reset all practice-mode session state to start a fresh practice run."""
    st.session_state.td_practice_case_idx = 0
    st.session_state.td_practice_correct = 0
    st.session_state.td_practice_answers = {}   # case_id -> {chosen, is_correct}
    st.session_state.td_practice_result = None  # result dict for the current case
    st.session_state.td_practice_done = False

def _practice_active() -> bool:
    return st.session_state.get("td_practice_mode", False)

def _exit_practice():
    st.session_state.td_practice_mode = False
    st.session_state.td_practice_case_idx = 0
    st.session_state.td_practice_correct = 0
    st.session_state.td_practice_answers = {}
    st.session_state.td_practice_result = None
    st.session_state.td_practice_done = False

# ── Practice banner ──────────────────────────────────────────────────────────

PRACTICE_BANNER = """
<div style="display:flex; align-items:center; gap:8px; background:var(--q-surface-2); border:1px solid var(--q-border-2);
 border-radius:8px; padding:7px 14px; margin-bottom:16px; max-width:1120px; margin-left:auto; margin-right:auto;">
<span style="font-size:10px; font-weight:900; letter-spacing:1.2px; color:var(--q-accent); text-transform:uppercase;">
🕵️ Practice Mode</span>
<span style="font-size:10px; color:var(--q-text-3); margin-left:4px;">— no XP, no reward, nothing saved</span>
</div>
"""

# ── Shared page CSS ──────────────────────────────────────────────────────────

PAGE_CSS = """
<style>
.td-hero { max-width:1120px; margin: 38px auto 20px; display:flex; justify-content:space-between; align-items:flex-end; gap:25px; }
.td-eyebrow { font-size:10px; color:var(--q-accent); letter-spacing:1.5px; text-transform:uppercase; font-weight:900; margin-bottom:9px; }
.td-hero h1 { margin:0 0 8px; font-size:36px; letter-spacing:-1.5px; color:var(--q-text); }
.td-sub { font-size:14px; color:var(--q-text-2); line-height:1.65; max-width:700px; }
.td-reward { white-space:nowrap; background:var(--q-accent-weak); border:1px solid var(--q-accent); color:var(--q-accent); border-radius:11px; padding:10px 14px; font-size:11px; font-weight:800; }

.td-case {
    max-width: 1120px;
    margin: auto;
    background: var(--q-surface-2);
    border: 1px solid var(--q-accent);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 0 0 1px var(--q-accent), 0 10px 40px -6px var(--q-accent-weak), 0 25px 70px rgba(0,0,0,0.45);
    transition: box-shadow .3s var(--q-ease);
}
.td-case-top { padding:21px 25px; border-bottom:1px solid var(--q-border); display:flex; justify-content:space-between; align-items:center; gap:20px; }
.td-case-id { display:inline-block; font-size:10px; color:var(--q-accent); background:var(--q-accent-weak); border:1px solid var(--q-accent); padding:4px 9px; border-radius:6px; font-weight:800; letter-spacing:1px; }
.td-case-title { font-size:21px; font-weight:800; margin-top:5px; color:var(--q-text); }
.td-scenario { padding:23px 25px 18px; display:grid; grid-template-columns:1fr 240px; gap:25px; }
.td-person { display:flex; gap:13px; }
.td-avatar { width:45px; height:45px; border-radius:13px; background:var(--q-accent-weak); border:1px solid var(--q-accent); display:grid; place-items:center; font-weight:800; font-size:13px; flex:none; color:var(--q-accent); }
.td-scenario p { margin:0; color:var(--q-text-2); font-size:13px; line-height:1.75; }

.td-snapshot { background:var(--q-surface-2); border:1px solid var(--q-border); border-left:3px solid var(--q-accent); border-radius:12px; padding:14px; }
.td-snap-title { font-size:9px; color:var(--q-accent); font-weight:800; letter-spacing:1px; text-transform:uppercase; margin-bottom:8px; }
.td-snap-row { display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px solid var(--q-border); font-size:10px; }
.td-snap-row:last-child { border:0; }
.td-snap-row span { color:var(--q-text-3); }
.td-snap-row b { color:var(--q-text); }

/* ── Option Card Grid & Containers ── */
div[data-testid="stColumn"] div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--q-surface-2) !important;
    border: 1px solid var(--q-border-2) !important;
    border-radius: 16px !important;
    padding: 20px 18px !important;
    transition: border-color .22s var(--q-ease),
                box-shadow     .22s var(--q-ease),
                background     .22s var(--q-ease),
                transform      .22s var(--q-ease) !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
    height: 100% !important;
}

div[data-testid="stColumn"] div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: var(--q-accent) !important;
    box-shadow: 0 0 0 1px var(--q-accent),
                0 10px 32px -4px var(--q-accent-weak),
                0 0 24px -2px var(--q-accent-weak) !important;
    transform: translateY(-2px);
}

.td-oc-card {
    display: flex;
    flex-direction: column;
    min-height: 140px;
}

/* Option label — muted uppercase pill (like "PORTFOLIO" in badge cards) */
.td-oc-label {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: var(--q-text-3);
    margin-bottom: 8px;
}

/* Bold primary title */
.td-oc-title {
    font-size: 15px;
    font-weight: 700;
    color: var(--q-text);
    line-height: 1.4;
    margin-bottom: 8px;
}

/* Muted description — grows to fill available space, pushing button down */
.td-oc-desc {
    font-size: 12px;
    color: var(--q-text-2);
    line-height: 1.6;
    margin-bottom: 16px;
    flex: 1;
}

div[data-testid="stColumn"] div[data-testid="stVerticalBlockBorderWrapper"] button {
    border-radius: 9px !important;
    font-weight: 600 !important;
    transition: all .18s var(--q-ease) !important;
}

.td-result { padding:20px 25px 25px; border-top:1px solid var(--q-border); }
.td-explain { background:var(--q-surface-2); border:1px solid var(--q-border); border-radius:12px; padding:17px; font-size:11px; line-height:1.7; color:var(--q-text-2); margin-bottom:10px; }
.td-takeaway { margin-top:13px; padding-top:12px; border-top:1px solid var(--q-border); color:var(--q-text); }
.td-why { padding:10px 12px; border-radius:9px; border:1px solid var(--q-border); background:var(--q-surface-2); font-size:10px; line-height:1.55; color:var(--q-text-2); margin-bottom:7px; }
.td-why.good { border-color:var(--q-pos); background:var(--q-pos-weak); }
.td-why.bad { border-color:var(--q-neg); background:var(--q-neg-weak); }
.td-summary { max-width:1120px; margin:auto; background:var(--q-surface); border:1px solid var(--q-border); border-radius:18px; box-shadow:0 25px 70px rgba(0,0,0,0.45); padding:55px 30px; text-align:center; color:var(--q-text); }
.td-summary h2 { font-size:27px; margin:0 0 7px; color:var(--q-text); }
.td-summary p { color:var(--q-text-2); font-size:12px; line-height:1.6; }
.td-score { display:inline-flex; gap:18px; margin:18px 0; padding:13px 18px; background:var(--q-surface-2); border:1px solid var(--q-border); border-radius:12px; }
.td-claim { color:var(--q-pos); font-weight:850; font-size:13px; margin:5px 0 20px; }
.td-claim.fail { color:var(--q-neg); }
.td-coming { margin:25px auto 20px; max-width:600px; padding:18px; border:1px dashed var(--q-border-2); border-radius:12px; background:var(--q-surface-2); }
</style>
"""

# ── Practice-run renderer ────────────────────────────────────────────────────

def _render_practice(prog: dict):
    """Full practice-mode flow. Reads/writes only st.session_state — no edu_db writes."""
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
    st.markdown(PRACTICE_BANNER, unsafe_allow_html=True)

    wallet_bal = prog.get("virtual_balance", 0.0)
    st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; max-width:1120px; margin:auto; margin-bottom:4px;">
<div style="font-size:12px; color:var(--q-text-3);">Tax Detective <span>›</span> <b style="color:var(--q-text);">Practice Run</b></div>
<div style="display:flex; gap:8px; align-items:center;">
<div style="display:flex; align-items:center; gap:9px; background:var(--q-surface-2); border:1px solid var(--q-border); border-radius:12px; padding:8px 13px;">
<div style="width:28px; height:28px; border-radius:8px; background:var(--q-pos-weak); color:var(--q-pos); display:grid; place-items:center; font-weight:800;">₹</div>
<div><small style="display:block; font-size:9px; color:var(--q-text-3);">VIRTUAL BALANCE</small><strong style="font-size:14px; color:var(--q-text);">₹{wallet_bal:,.0f}</strong></div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    # ── Practice summary screen ──────────────────────────────────────────────
    if st.session_state.get("td_practice_done", False):
        correct = st.session_state.get("td_practice_correct", 0)
        st.markdown(f"""
<div class="td-summary" style="border-color:var(--q-border-2);">
<div style="font-size:10px; font-weight:900; letter-spacing:1.2px; color:var(--q-accent); text-transform:uppercase; margin-bottom:16px;">🕵️ Practice Mode — No XP · No Reward</div>
<div style="font-size:40px; margin-bottom:10px;">{'✓' if correct >= 3 else '📋'}</div>
<h2>Practice complete.</h2>
<p>{'Great recall — you got the right answer on most cases.' if correct >= 3 else 'A few cases to review. Use the explanations to sharpen your approach.'}</p>
<div class="td-score"><strong>{correct}/4</strong><span>correct in this practice run</span></div>
<div style="font-size:11px; color:var(--q-text-3); margin:0 0 24px;">Practice runs are not graded and do not affect your balance or XP.</div>
</div>
""", unsafe_allow_html=True)

        st.write("")
        col_a, col_b, col_c = st.columns([1, 1, 1])
        with col_a:
            if st.button("← Back to Case Board", key="practice_back_summary", use_container_width=True):
                _exit_practice()
                st.rerun()
        with col_c:
            if st.button("🔄 Practice Again", key="practice_again", type="primary", use_container_width=True):
                _practice_init()
                st.rerun()
        return

    # ── Practice case flow ───────────────────────────────────────────────────
    cases = tax_detective_db.get_public_cases()
    full_cases = [tax_detective_db.get_case(i) for i in range(len(cases))]

    case_idx = st.session_state.get("td_practice_case_idx", 0)
    answers = st.session_state.get("td_practice_answers", {})
    correct_count = st.session_state.get("td_practice_correct", 0)
    total = len(cases)

    # Exit button — always visible during practice
    col_exit, _ = st.columns([1, 4])
    with col_exit:
        if st.button("← Exit Practice", key="practice_exit_top", use_container_width=True):
            _exit_practice()
            st.rerun()

    st.write("")

    # Progress
    answered = len(answers)
    display_idx = case_idx + 1
    st.progress(
        answered / total,
        text=f"PRACTICE · CASE {display_idx} OF {total} | {correct_count} correct"
    )

    case_pub = cases[case_idx]
    case_full = full_cases[case_idx]

    st.markdown(_case_card_html(case_pub, practice=True), unsafe_allow_html=True)
    st.write("")

    prac_result = st.session_state.get("td_practice_result")

    if prac_result is None:
        chosen_opt = render_option_cards(case_pub["choices"], f"pbtn_{case_idx}")
        if chosen_opt is not None:
            full_choices = case_full["choices"]
            chosen = full_choices[chosen_opt]
            is_correct = chosen.get("c", False)
            correct_index = next((n for n, c in enumerate(full_choices) if c.get("c")), -1)
            result = {
                "is_correct": is_correct,
                "correct_index": correct_index,
                "explanation": chosen.get("why", ""),
                "all_explanations": [c.get("why", "") for c in full_choices],
                "takeaway": case_full["takeaway"],
            }
            answers[case_pub["id"]] = {"chosen": chosen_opt, "is_correct": is_correct}
            if is_correct:
                st.session_state.td_practice_correct = correct_count + 1
            st.session_state.td_practice_answers = answers
            st.session_state.td_practice_result = result
            st.rerun()
    else:
        # Show result panel
        st.markdown(_result_panel_html(prac_result, practice=True), unsafe_allow_html=True)
        st.write("")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("← Exit Practice", key="practice_exit_result", use_container_width=True):
                _exit_practice()
                st.rerun()
        with col3:
            is_last = (case_idx >= total - 1)
            next_label = "See Practice Summary" if is_last else "Next Case →"
            if st.button(next_label, key="practice_next", type="primary", use_container_width=True):
                if is_last:
                    st.session_state.td_practice_done = True
                else:
                    st.session_state.td_practice_case_idx = case_idx + 1
                st.session_state.td_practice_result = None
                st.rerun()


# ── Closed-board screen ──────────────────────────────────────────────────────

def _render_closed_board(prog: dict):
    """Terminal state: user has already completed their one real run."""
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
    wallet_bal = prog.get("virtual_balance", 0.0)
    st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; max-width:1120px; margin:auto;">
<div style="font-size:12px; color:var(--q-text-3);">Tax Detective <span>›</span> <b style="color:var(--q-text);">Case Files</b></div>
<div style="display:flex; align-items:center; gap:9px; background:var(--q-surface-2); border:1px solid var(--q-border); border-radius:12px; padding:8px 13px;">
<div style="width:28px; height:28px; border-radius:8px; background:var(--q-pos-weak); color:var(--q-pos); display:grid; place-items:center; font-weight:800;">₹</div>
<div><small style="display:block; font-size:9px; color:var(--q-text-3);">VIRTUAL BALANCE</small><strong style="font-size:14px; color:var(--q-text);">₹{wallet_bal:,.0f}</strong></div>
</div>
</div>
<div style="max-width:1120px; margin:40px auto 0; background:var(--q-surface); border:1px solid var(--q-border); border-radius:18px; box-shadow:0 25px 70px rgba(0,0,0,0.45); padding:50px 30px; text-align:center; color:var(--q-text);">
<div style="font-size:48px; margin-bottom:16px;">🔒</div>
<h2 style="font-size:24px; margin:0 0 10px; color:var(--q-text);">Case board closed</h2>
<p style="color:var(--q-text-2); font-size:13px; line-height:1.7; max-width:520px; margin:0 auto 28px;">You've already completed this investigation. Your run is on the record — no new graded attempts are available.</p>
<div style="display:inline-block; margin:0 auto 28px; padding:18px 24px; background:var(--q-surface-2); border:1px solid var(--q-border); border-radius:12px;">
<div style="font-size:9px; color:var(--q-text-3); letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Investigation status</div>
<div style="font-size:15px; font-weight:800; color:var(--q-pos);">✓ Completed</div>
</div>
<div style="margin:0 auto 28px; max-width:560px; padding:18px; border:1px dashed var(--q-border-2); border-radius:12px; background:var(--q-surface-2);">
<b style="color:var(--q-text);">🔒 New cases are coming soon</b>
<p style="margin:8px 0 0; font-size:11px; color:var(--q-text-3); line-height:1.6;">New tax scenarios, trickier clues and fresh investigations will be added to the Tax Detective case board. Check back later to take on the next set of cases.</p>
</div>
</div>
""", unsafe_allow_html=True)

    # Practice Mode opt-in — visually distinct from a primary CTA
    st.write("")
    col_l, col_c, col_r = st.columns([1.5, 1, 1.5])
    with col_c:
        st.markdown(
            "<div style='text-align:center; font-size:10px; color:var(--q-text-3); margin-bottom:6px;'>"
            "Want to review the cases?</div>",
            unsafe_allow_html=True
        )
        if st.button("🕵️ Enter Practice Mode", key="enter_practice", type="primary", use_container_width=True):
            st.session_state.td_practice_mode = True
            _practice_init()
            st.rerun()


# ── One-time real-run summary ────────────────────────────────────────────────

def _render_completed_summary(attempt: dict, prog: dict):
    """Show the one-time pass/fail summary right after finishing. No replay button."""
    passed = attempt["correct_count"] >= 3
    icon = "✓" if passed else "!"
    title = "Case file closed. You cracked it." if passed else "Investigation incomplete."
    sub = (
        "You completed all four investigations and reached the minimum score of 3/4."
        if passed else
        "You completed all four cases, but you needed at least 3 correct. Because the reward requires a 3/4 score, no reward is unlocked this run."
    )
    claim_class = "td-claim" if passed else "td-claim fail"
    claim_text = f"✦ Reward unlocked: ₹{attempt['reward_amount']:,.0f}" if passed else "Reward unlocked: ₹0"

    st.markdown(f"""
<div class="td-summary">
<div style="font-size:40px; margin-bottom:10px;">{icon}</div>
<h2>{title}</h2>
<p>{sub}</p>
<div class="td-score"><strong>{attempt['correct_count']}/4</strong><span>cases solved correctly</span></div>
<div class="{claim_class}">{claim_text}</div>
<div class="td-coming"><b>🔒 More cases are coming soon</b><p style="margin:6px 0 0; font-size:10px; color:var(--q-text-3);">New tax scenarios, trickier clues and fresh investigations will be added to the Tax Detective case board.</p></div>
</div>
""", unsafe_allow_html=True)


# ── Main entry point ─────────────────────────────────────────────────────────

def render(user_info: dict):
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    prog = load_progress()

    # ── EARLY EXIT: user has already completed their one real run ────────────
    if tax_detective_db.has_completed_run():
        if _practice_active():
            _render_practice(prog)
            return

        att = st.session_state.get("td_attempt")
        if att and att.get("status") == "completed":
            _render_completed_summary(att, prog)
            return

        _render_closed_board(prog)
        return

    # ── First-run only: load/initialise graded attempt ───────────────────────
    if "td_attempt" not in st.session_state:
        st.session_state.td_attempt = tax_detective_db.get_current_attempt()
        st.session_state.td_result = None

    attempt = st.session_state.td_attempt

    # ── Header ───────────────────────────────────────────────────────────────
    wallet_bal = prog.get("virtual_balance", 0.0)
    st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; max-width:1120px; margin:auto;">
<div style="font-size:12px; color:var(--q-text-3);">Tax Detective <span>›</span> <b style="color:var(--q-text);">Case Files</b></div>
<div style="display:flex; align-items:center; gap:9px; background:var(--q-surface-2); border:1px solid var(--q-border); border-radius:12px; padding:8px 13px;">
<div style="width:28px; height:28px; border-radius:8px; background:var(--q-pos-weak); color:var(--q-pos); display:grid; place-items:center; font-weight:800;">₹</div>
<div><small style="display:block; font-size:9px; color:var(--q-text-3);">VIRTUAL BALANCE</small><strong style="font-size:14px; color:var(--q-text);">₹{wallet_bal:,.0f}</strong></div>
</div>
</div>
<div class="td-hero">
<div>
<div class="td-eyebrow">Tax Detective · Mini-Game</div>
<h1>Find the tax clue. Solve the case.</h1>
<div class="td-sub">You've learned the concepts. Now apply them to real-world situations. Attempt all four cases, review the reasoning behind every decision, and answer all four cases. Score <b>3 out of 4 or better</b> to unlock your reward.</div>
</div>
<div class="td-reward">✦ 3/4 to unlock your reward</div>
</div>
""", unsafe_allow_html=True)

    if attempt["status"] == "completed":
        _render_completed_summary(attempt, prog)
        return

    # ── In-progress graded case flow ─────────────────────────────────────────
    cases = tax_detective_db.get_public_cases()
    answered_ids = list(attempt["answers"].keys())

    if st.session_state.td_result:
        current_case_idx = len(answered_ids) - 1
    else:
        current_case_idx = len(answered_ids)

    if current_case_idx >= len(cases):
        if st.button("Submit Final Report & Claim Reward", type="primary", use_container_width=True):
            try:
                res = tax_detective_db.finish_attempt()
                if not _practice_active():
                    if res["correct_count"] >= 3:
                        for _ in range(res["correct_count"]):
                            edu_db.award_xp(75, 'tax_case_solved')
                    if res["correct_count"] == 4:
                        edu_db.award_xp(25, 'perfect_score_bonus')
                st.session_state.td_attempt = res
                st.session_state.td_result = None
                st.rerun()
            except Exception as e:
                st.error(str(e))
        return

    case = cases[current_case_idx]
    attempted = len(answered_ids)
    total = len(cases)
    st.progress(attempted / total, text=f"CASE {current_case_idx+1} OF {total} | {attempt['correct_count']} correct · {total - attempted} to go")

    st.markdown(_case_card_html(case, practice=False), unsafe_allow_html=True)
    st.write("")

    if not st.session_state.td_result:
        chosen_opt = render_option_cards(case["choices"], f"btn_{current_case_idx}")
        if chosen_opt is not None:
            res = tax_detective_db.answer_case(current_case_idx, chosen_opt)
            st.session_state.td_attempt = tax_detective_db.get_current_attempt()
            st.session_state.td_result = res
            st.rerun()
    else:
        st.markdown(_result_panel_html(st.session_state.td_result, practice=False), unsafe_allow_html=True)
        st.write("")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col3:
            label = "Next Case →" if current_case_idx < total - 1 else "Finish & See Final Result"
            if st.button(label, type="primary", use_container_width=True):
                if current_case_idx == total - 1:
                    finished = tax_detective_db.finish_attempt()
                    if not _practice_active():
                        if finished["correct_count"] >= 3:
                            for _ in range(finished["correct_count"]):
                                edu_db.award_xp(75, 'tax_case_solved')
                        if finished["correct_count"] == 4:
                            edu_db.award_xp(25, 'perfect_score_bonus')
                    st.session_state.td_attempt = finished
                st.session_state.td_result = None
                st.rerun()
