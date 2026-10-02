from __future__ import annotations

import pandas as pd
import streamlit as st

from careops.infrastructure.ai import AIConfigurationError
from frontend.runtime import get_service, runtime_pills
from frontend.ui import (
    empty_state,
    member_snapshot,
    page_header,
    render_result,
    run_plan,
    section,
)

SCOPE_KEY = "scope_select"
MEMBER_KEY = "member_select"
FOCUS_KEY = "focus_text"
FRESH_KEY = "fresh_run"


def _keep_a_scope() -> None:
    """A segmented control can be de-selected by clicking it again; always keep one active."""
    if st.session_state.get(SCOPE_KEY) is None:
        st.session_state[SCOPE_KEY] = st.session_state.get("_last_scope", "overall")
    st.session_state["_last_scope"] = st.session_state[SCOPE_KEY]


def _member_label(population: pd.DataFrame, member_id: str) -> str:
    row = population.loc[population["patient_id"].astype(str).eq(str(member_id))].iloc[0]
    diagnosis = str(row.get("diagnosis") or "").strip()
    return f"{row['patient_name']}  ·  {member_id}" + (f"  ·  {diagnosis}" if diagnosis else "")


def _saved_for(service, member_id: str, scope: str):
    try:
        return service.find_saved(member_id, scope)
    except Exception:  # noqa: BLE001 - a hint only; never block the page
        return None


def page() -> None:
    service = get_service()
    policy = service.rules()
    population = service.population()
    members = population["patient_id"].astype(str).tolist()

    page_header(
        "Home",
        "Choose a member and a review type, then run CareOps. Rules establish the findings; "
        "AI writes the assessment from them.",
        runtime_pills(service),
    )
    if not members:
        st.error("No members are available in the configured data set.")
        return

    scopes = policy["scopes"]
    st.session_state.setdefault("results", {})

    with st.container(key="run_panel"):
        form, snapshot = st.columns([1.55, 1], gap="large")
        with form:
            member_id = st.selectbox(
                "Member",
                members,
                format_func=lambda value: _member_label(population, value),
                key=MEMBER_KEY,
            )
            scope = (
                st.segmented_control(
                    "Review type",
                    options=list(scopes),
                    format_func=lambda key: scopes[key].get("short_name") or scopes[key]["name"],
                    default="overall",
                    key=SCOPE_KEY,
                    on_change=_keep_a_scope,
                )
                or "overall"
            )
            scope_def = scopes[scope]
            st.markdown(
                f"<div class='field-hint'><b>{scope_def['name']}.</b> {scope_def['description']}</div>",
                unsafe_allow_html=True,
            )
            run_plan(scope_def, policy)
            focus = st.text_input(
                "Focus (optional)",
                placeholder="e.g. Prioritise the most important near-term follow-up",
                max_chars=700,
                key=FOCUS_KEY,
            )
            fresh = st.toggle(
                "Fresh run",
                value=False,
                key=FRESH_KEY,
                help="Off: if this member already has a saved result for this review (and their "
                "data and the policy are unchanged), that result is loaded and no AI is called. "
                "On: always run a new assessment.",
            )
            saved = _saved_for(service, member_id, scope)
            if saved is not None and not fresh and not focus.strip():
                st.caption(
                    f"A saved result from {saved.created_at.strftime('%d %b %Y, %H:%M UTC')} is "
                    "available. Run CareOps will load it. Turn on Fresh run to re-run instead."
                )
            else:
                st.caption(
                    "Run CareOps will generate a new assessment using the current data and policy."
                )
            run = st.button("Run CareOps", type="primary", use_container_width=True)
        with snapshot:
            member_snapshot(service.member_record(member_id))

    results: dict = st.session_state["results"]
    key = (member_id, scope)

    if run:
        try:
            with st.spinner(
                "Loading or preparing the assessment…"
                if not fresh
                else (
                    "Supervisor is selecting capabilities and preparing the assessment…"
                    if scope_def["mode"] == "overall"
                    else f"Running the {scope_def['name'].lower()}…"
                )
            ):
                results[key] = service.assess(
                    member_id, scope=scope, instruction=focus, fresh=fresh
                )
        except AIConfigurationError as exc:
            st.error("The AI service is not configured for this environment.")
            st.info(f"{exc} Check LLM_PROVIDER, LLM_MODEL and the matching API key in .env.")
        except Exception as exc:  # noqa: BLE001 - surface any failure to the operator
            st.error(f"The assessment could not be completed: {exc}")

    result = results.get(key)
    if result is None:
        empty_state(
            "No assessment yet",
            "Select a member and review type above, then choose Run CareOps. The result will appear here.",
        )
        return

    section("Assessment result")
    contract, reused = result
    render_result(contract, service.member_record(contract.member_id), policy, reused=reused)
