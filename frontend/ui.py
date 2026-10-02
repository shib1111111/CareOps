"""Presentation components. All markup is built here so pages stay declarative."""

from __future__ import annotations

import base64
from collections.abc import Iterable, Sequence
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

from careops.contracts.api import build_api_response
from careops.contracts.decisions import CareOpsDecisionContract

ROOT_DIR = Path(__file__).resolve().parents[1]
DIAGRAM_DIR = ROOT_DIR / "assets" / "diagrams"

TONES = {"blue", "green", "violet", "amber"}


class Raw(str):
    """Trusted markup that must not be escaped (built only from code, never from data)."""


def code(text: str) -> Raw:
    return Raw(f"<code>{escape(text)}</code>")


def _cell(value: object) -> str:
    return str(value) if isinstance(value, Raw) else escape(str(value))


def md(markup: str) -> None:
    """Render trusted HTML. Lines are collapsed so Markdown never mistakes indentation for code."""
    flat = "".join(line.strip() for line in markup.strip().splitlines())
    st.markdown(flat, unsafe_allow_html=True)


# --------------------------------------------------------------------------------------
# Page structure
# --------------------------------------------------------------------------------------
def page_header(title: str, subtitle: str, meta: Iterable[tuple[str, str]] = ()) -> None:
    pills = "".join(
        f"<span class='pill pill-{tone}'><i></i>{escape(label)}</span>" for label, tone in meta
    )
    md(
        f"""
        <div class="page-head">
          <div>
            <div class="page-title" role="heading" aria-level="1">{escape(title)}</div>
            <div class="page-sub">{escape(subtitle)}</div>
          </div>
          <div class="page-meta">{pills}</div>
        </div>
        """
    )


def section(title: str, subtitle: str | None = None, num: int | str | None = None) -> None:
    badge = f"<span class='sec-num'>{escape(str(num))}</span>" if num is not None else ""
    sub = f"<div class='sec-sub'>{escape(subtitle)}</div>" if subtitle else ""
    md(f"<div class='sec'><div class='sec-title'>{badge}{escape(title)}</div>{sub}</div>")


def subhead(text: str) -> None:
    md(f"<div class='subhead'>{escape(text)}</div>")


def callout(title: str, body: str, tone: str = "blue") -> None:
    tone = tone if tone in TONES else "blue"
    md(
        f"<div class='callout c-{tone}'><div><strong>{escape(title)}</strong>"
        f"<span>{escape(body)}</span></div></div>"
    )


def footer(version: str) -> None:
    md(
        f"""
        <div class="footer">
          <div class="footer-row">
            <div><b>CareOps</b> &nbsp;·&nbsp; Evidence-backed member decision support</div>
            <div>Made by <b>Shib Kumar</b> &nbsp;·&nbsp; Proof of concept v{escape(version)}</div>
          </div>
          <div class="footer-note">Runs on sample data. Outputs support operational review and are
          not clinical advice.</div>
        </div>
        """
    )


# --------------------------------------------------------------------------------------
# Documentation building blocks
# --------------------------------------------------------------------------------------
def grid(cards: Sequence[tuple[Any, ...]], cols: int = 3) -> None:
    """Responsive card grid. Each card is (title, body) or (title, body, tone)."""
    cells = []
    for card in cards:
        title, body, *rest = card
        tone = rest[0] if rest and rest[0] in TONES else ""
        cells.append(
            f"<div class='gcard t-{tone}'><div class='gcard-title'>{escape(title)}</div>"
            f"<div class='gcard-body'>{_cell(body)}</div></div>"
        )
    md(f"<div class='grid g{cols}'>{''.join(cells)}</div>")


def flow(steps: Sequence[tuple[str, str]]) -> None:
    items = "".join(
        f"<div class='flow-step'><div class='n'>STEP {i}</div><div class='t'>{escape(t)}</div>"
        f"<div class='d'>{escape(d)}</div></div>"
        for i, (t, d) in enumerate(steps, start=1)
    )
    md(f"<div class='flow'>{items}</div>")


def table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{_cell(c)}</td>" for c in row) + "</tr>" for row in rows)
    md(
        f"<div class='tbl-wrap'><table class='tbl'><thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )


def figure(filename: str, title: str, caption: str, alt: str) -> None:
    encoded = base64.b64encode((DIAGRAM_DIR / filename).read_bytes()).decode("ascii")
    md(
        f"""
        <div class="figure">
          <div class="figure-bar"><b>{escape(title)}</b><span>{escape(caption)}</span></div>
          <div class="figure-body"><img src="data:image/svg+xml;base64,{encoded}" alt="{escape(alt)}"></div>
        </div>
        """
    )


def json_block(title: str, description: str, payload: str) -> None:
    subhead(title)
    st.caption(description)
    st.code(payload, language="json")


def kpis(items: Sequence[tuple[str, object, str]]) -> None:
    cells = "".join(
        f"<div class='kpi'><div class='l'>{escape(label)}</div><div class='v'>{escape(str(value))}</div>"
        f"<div class='n'>{escape(note)}</div></div>"
        for label, value, note in items
    )
    md(f"<div class='kpis'>{cells}</div>")


# --------------------------------------------------------------------------------------
# Assessments workspace
# --------------------------------------------------------------------------------------
def member_snapshot(record: dict[str, Any]) -> None:
    name = _display(record.get("patient_name"))
    initials = "".join(part[:1] for part in name.split()[:2]).upper() or "M"
    bp = f"{_num(record.get('vitals_bp_systolic'))}/{_num(record.get('vitals_bp_diastolic'))} mmHg"
    lab = (
        f"{_display(record.get('lab_test'))} {_num(record.get('lab_value'))} "
        f"{_display(record.get('lab_unit'), '')}"
    ).strip()
    rows = [
        ("Diagnosis", _display(record.get("diagnosis"))),
        ("Latest lab", lab),
        ("Blood pressure", bp),
        ("Last visit", f"{_num(record.get('days_since_last_visit'))} days ago"),
        ("Missed last appointment", _display(record.get("missed_last_appointment"))),
    ]
    body = "".join(
        f"<div class='mrow'><span>{escape(k)}</span><b>{escape(v)}</b></div>" for k, v in rows
    )
    meta = (
        f"{_num(record.get('age'))} yrs · {_display(record.get('gender'))} · "
        f"{record.get('patient_id', '')}"
    )
    md(
        f"""
        <div class="member">
          <div class="member-head">
            <div class="avatar">{escape(initials)}</div>
            <div>
              <div class="member-name">{escape(name)}</div>
              <div class="member-meta">{escape(meta)}</div>
            </div>
          </div>
          <div class="member-rows">{body}</div>
        </div>
        """
    )


def run_plan(scope: dict[str, Any], policy: dict[str, Any]) -> None:
    """Show exactly what will execute for the selected review, and where AI is involved."""
    tools = policy["tools"]
    names = [tools[t]["name"].removesuffix(" capability") for t in scope["tools"] if t in tools]
    steps: list[tuple[str, str]] = []
    if scope["mode"] == "overall":
        steps.append(("ai", "Supervisor selects capabilities"))
        steps.append(("det", "Evaluate selected capabilities"))
        calls = 2
    else:
        steps.append(("det", f"Evaluate: {', '.join(names)}"))
        calls = 1
    steps += [
        ("det", "Match patterns · calculate priority"),
        ("ai", "Write the assessment"),
        ("chk", "Validate"),
    ]
    chips = "<span class='plan-arrow'>→</span>".join(
        f"<span class='plan-step {kind}'>{escape(label)}</span>" for kind, label in steps
    )
    note = f"{calls} AI call{'s' if calls > 1 else ''} per fresh run. "
    md(f"<div class='plan'>{chips}</div><div class='plan-note'>{escape(note)}</div>")


def empty_state(title: str, body: str) -> None:
    md(f"<div class='empty'><strong>{escape(title)}</strong><span>{escape(body)}</span></div>")


_PRIORITY_CLASS = {"Critical": "critical", "High": "high", "Medium": "medium", "Low": "low"}
_STATUS_PILL = {
    "READY": ("Validated", "green"),
    "REVIEW": ("Needs review", "amber"),
    "BLOCKED": ("Not released", "red"),
}


def render_result(
    contract: CareOpsDecisionContract,
    member: dict[str, Any],
    policy: dict[str, Any],
    reused: bool = False,
) -> None:
    scope_def = policy["scopes"].get(contract.scope, {})
    scope_name = scope_def.get("name", contract.scope.replace("_", " ").title())
    blocked = contract.status == "BLOCKED"
    tone = "blocked" if blocked else _PRIORITY_CLASS.get(contract.priority, "medium")
    prio_label = "Priority not released" if blocked else f"{contract.priority} priority"
    status_label, status_tone = _STATUS_PILL[contract.status]
    ex = contract.execution

    source = "Saved result (no new run)" if reused else "Fresh run"
    source_tone = "blue" if reused else "green"
    stamp = contract.created_at.strftime("%d %b %Y, %H:%M UTC")
    summary = (
        "The written assessment did not pass validation and has been withheld. "
        "The findings below remain valid."
        if blocked
        else contract.summary
    )
    member_name = _display(member.get("patient_name"))
    md(
        f"""
        <div class="result p-{tone}">
          <div class="result-top">
            <span class="prio prio-{tone}"><i></i>{escape(prio_label)}</span>
            <span class="pill pill-{status_tone}"><i></i>{escape(status_label)}</span>
            <span class="pill pill-violet"><i></i>{escape(scope_name)}</span>
            <span class="pill pill-{source_tone}"><i></i>{escape(source)}</span>
          </div>
          <div class="result-summary">{escape(summary)}</div>
          <div class="result-meta">
            <span>Member <b>{escape(member_name)} ({escape(contract.member_id)})</b></span>
            <span>Agent <b>{escape(ex.agent_name)}</b></span>
            <span>Completed <b>{escape(stamp)}</b></span>
            <span>Duration <b>{ex.duration_ms / 1000:.1f} s</b></span>
          </div>
        </div>
        """
    )

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        if not blocked:
            section("Why it matters")
            md(f"<div class='panel'><p>{escape(contract.why_it_matters)}</p></div>")
        section("Findings", "Only findings that crossed a configured threshold are listed.")
        _findings(contract)
        if contract.patterns:
            section(
                "Matched evidence patterns",
                "Configured combinations that shaped the recommendation.",
            )
            _patterns(contract)
    with right:
        if blocked:
            section("Validation")
            md(
                "<div class='panel warn'><p><strong>Withheld.</strong> The model output referenced "
                "evidence or audiences that are not part of this run. Re-run the assessment.</p></div>"
            )
        else:
            section("Recommended next step")
            md(
                f"<div class='panel next'><div class='lbl'>Next step</div>"
                f"<p>{escape(contract.next_step)}</p></div>"
            )
            section("Actions")
            _actions(contract)

    if contract.handoffs and not blocked:
        _handoffs(contract)

    section("Run record")
    with st.expander("Run details"):
        _run_details(contract, policy)
    st.download_button(
        "Download API response (JSON)",
        data=build_api_response(contract).model_dump_json(indent=2),
        file_name=f"{contract.decision_id}.json",
        mime="application/json",
    )


def _findings(contract: CareOpsDecisionContract) -> None:
    if not contract.flagged:
        empty_state(
            "No findings above configured thresholds",
            "The current policy did not promote a finding for this review.",
        )
        return
    rows = []
    for item in contract.flagged:
        unit = f" {item.unit}" if item.unit and item.unit != "mixed" else ""
        rows.append(
            f"<div class='finding'><div class='idc'><span class='idchip'>{escape(item.evidence_id)}</span></div>"
            f"<div class='head'><span class='sig'>{escape(item.signal)}</span>"
            f"<span class='val'>{escape(item.value)}{escape(unit)}</span></div>"
            f"<div class='why'>{escape(item.interpretation)}</div></div>"
        )
    md(f"<div class='list-card'>{''.join(rows)}</div>")


def _patterns(contract: CareOpsDecisionContract) -> None:
    rows = "".join(
        f"<div class='finding'><div class='idc'><span class='idchip'>PATTERN</span></div>"
        f"<div class='head'><span class='sig'>{escape(p.name)}</span>"
        f"<span class='ownerchip'>{escape(p.pathway)}</span></div>"
        f"<div class='why'>{escape(p.implication)}</div></div>"
        for p in contract.patterns
    )
    md(f"<div class='list-card'>{rows}</div>")


def _actions(contract: CareOpsDecisionContract) -> None:
    rows = "".join(
        f"<div class='action'><div class='num'>{a.sequence}</div>"
        f"<div class='what'>{escape(a.action)}</div>"
        f"<div class='note'>{escape(a.rationale)}</div>"
        f"<div class='who'><span class='ownerchip'>{escape(a.owner)}</span> "
        + "".join(f"<span class='idchip'>{escape(ref)}</span> " for ref in a.evidence_refs)
        + "</div></div>"
        for a in sorted(contract.actions, key=lambda item: item.sequence)
    )
    md(f"<div class='list-card'>{rows}</div>")


def _handoffs(contract: CareOpsDecisionContract) -> None:
    section(
        "Stakeholder views",
        "The same decision, written for each audience enabled for this review.",
    )
    labels = [audience.replace("_", " ").title() for audience in contract.handoffs]
    for tab, message in zip(st.tabs(labels), contract.handoffs.values(), strict=True):
        with tab:
            md(f"<div class='view'>{escape(message)}</div>")


def _run_details(contract: CareOpsDecisionContract, policy: dict[str, Any]) -> None:
    ex = contract.execution
    tools = policy.get("tools", {})
    capabilities = ", ".join(tools.get(t, {}).get("name", t) for t in contract.evaluated_tools)
    route = (
        "Overall: Supervisor selected the capabilities"
        if ex.route == "overall"
        else "Focused: capabilities fixed by the review configuration (no routing call)"
    )
    pairs = [
        ("Run ID", contract.decision_id),
        ("Agent", f"{ex.agent_name} ({ex.agent_key})"),
        ("Route", route),
        ("Routing reason", ex.routing_reason or "Not applicable"),
        ("Capabilities run", capabilities or "None"),
        ("Data fingerprint", contract.context_fingerprint),
        ("Policy fingerprint", contract.policy_fingerprint),
        ("Stored under", f"data/runs/{ex.agent_key}/"),
    ]
    items = "".join(f"<dt>{escape(k)}</dt><dd>{escape(v)}</dd>" for k, v in pairs)
    md(f"<dl class='kv'>{items}</dl>")
    st.caption(
        "Fingerprints are hashes of the member's records and of the policy at run time, "
        "so a stored result can be tied to the exact inputs that produced it."
    )


# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------
def _display(value: object, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return fallback if not text or text.lower() in {"nan", "nat", "none", "<na>"} else text


def _num(value: object) -> str:
    text = _display(value, "n/a")
    try:
        number = float(text)
    except ValueError:
        return text
    return f"{number:g}"
