from __future__ import annotations

import pandas as pd
import streamlit as st

from frontend.runtime import get_service, runtime_pills
from frontend.ui import empty_state, kpis, page_header, section

_RUN_COLUMNS = [
    "created_at",
    "agent_name",
    "scope",
    "member_id",
    "priority",
    "status",
    "flagged_count",
    "llm_calls",
    "duration_ms",
    "summary",
]


def _height(rows: int, cap: int = 360) -> int:
    return min(cap, 38 + 35 * max(rows, 1))


_RUN_CONFIG = {
    "created_at": st.column_config.DatetimeColumn(
        "Completed", format="DD MMM YYYY, HH:mm", width="medium"
    ),
    "agent_name": st.column_config.TextColumn("Agent", width="medium"),
    "scope": st.column_config.TextColumn("Review", width="small"),
    "member_id": st.column_config.TextColumn("Member", width="small"),
    "priority": st.column_config.TextColumn("Priority", width="small"),
    "status": st.column_config.TextColumn("Status", width="small"),
    "flagged_count": st.column_config.NumberColumn("Findings", width="small"),
    "llm_calls": st.column_config.NumberColumn("AI calls", width="small"),
    "duration_ms": st.column_config.NumberColumn("ms", width="small"),
    "summary": st.column_config.TextColumn("Summary", width="large"),
}


def page() -> None:
    service = get_service()
    patients = service.population()
    claims = service.claims()
    enrollment = service.enrollment()

    page_header(
        "Data Explorer",
        "Inspect the records CareOps reads, and the runs it has saved. Each run reads the current files.",
        runtime_pills(service),
    )
    kpis(
        [
            ("Members", len(patients), "Records in patients.csv"),
            ("Claims", len(claims), "Utilization history"),
            ("Enrollment", len(enrollment), "Plan context rows"),
        ]
    )

    members_tab, claims_tab, enrollment_tab, runs_tab = st.tabs(
        ["Members", "Claims", "Enrollment", "Saved runs"]
    )

    with members_tab:
        section("Member records", "The clinical and continuity fields assessments are built from.")
        query = st.text_input(
            "Search", placeholder="Name, member ID or diagnosis", key="member_search"
        )
        view = patients
        if query.strip():
            needle = query.strip().lower()
            mask = pd.Series(False, index=patients.index)
            for column in ("patient_id", "patient_name", "diagnosis"):
                mask |= (
                    patients[column]
                    .astype(str)
                    .str.lower()
                    .str.contains(needle, regex=False, na=False)
                )
            view = patients.loc[mask]
        st.caption(f"{len(view)} of {len(patients)} members")
        st.dataframe(view, hide_index=True, width="stretch", height=420)

    with claims_tab:
        section(
            "Claims", "Source for the utilization capability (emergency and inpatient activity)."
        )
        st.dataframe(claims, hide_index=True, width="stretch", height=420)

    with enrollment_tab:
        section("Enrollment", "Plan context made available to reviews that require it.")
        st.dataframe(enrollment, hide_index=True, width="stretch", height=420)

    with runs_tab:
        _saved_runs(service)


def _saved_runs(service) -> None:
    policy = service.rules()
    agents = {key: value["name"] for key, value in policy["agents"].items()}

    section(
        "Saved runs",
        "Every run is stored under the agent that produced it. A new run never uses another run's results as input.",
    )
    choice = st.selectbox(
        "Agent",
        ["all", *agents],
        format_func=lambda key: "All agents" if key == "all" else agents[key],
        key="runs_agent",
    )
    frames = service.saved_runs(None if choice == "all" else choice)
    runs = frames.runs

    if runs.empty:
        empty_state(
            "No saved runs yet",
            "Run an assessment from the Assessments page and it will be listed here.",
        )
        return

    last = runs["created_at"].max().strftime("%d %b %Y, %H:%M UTC")
    kpis(
        [
            ("Runs saved", len(runs), "For the selected agent filter"),
            ("Agents used", runs["agent_key"].nunique(), f"of {len(agents)} configured"),
            ("Latest run", last, "Most recent completion"),
        ]
    )

    runs_view, findings_view, actions_view = st.tabs(["Runs", "Findings", "Actions"])
    with runs_view:
        st.dataframe(
            runs[_RUN_COLUMNS],
            hide_index=True,
            width="stretch",
            column_config=_RUN_CONFIG,
            height=_height(len(runs)),
        )
        st.download_button(
            "Download runs (CSV)",
            runs.drop(columns=["contract_json"]).to_csv(index=False),
            file_name="careops_runs.csv",
            mime="text/csv",
        )
    with findings_view:
        st.caption("One row per finding, linked to its run by run_id.")
        st.dataframe(
            frames.findings, hide_index=True, width="stretch", height=_height(len(frames.findings))
        )
    with actions_view:
        st.caption("One row per recommended action, linked to its run by run_id.")
        st.dataframe(
            frames.actions, hide_index=True, width="stretch", height=_height(len(frames.actions))
        )
