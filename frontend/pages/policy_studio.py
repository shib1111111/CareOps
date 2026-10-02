from __future__ import annotations

import copy

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from frontend.runtime import clear_frontend_caches, get_service, runtime_pills
from frontend.ui import callout, grid, page_header, section, subhead, table

LIFECYCLES = ["Active", "Draft", "Retired"]


def page() -> None:
    service = get_service()
    policy = service.rules()

    page_header(
        "Policy Studio",
        "Maintain the thresholds, evidence definitions and pattern mappings that shape every assessment.",
        runtime_pills(service),
    )
    callout(
        "How the pieces fit",
        "Thresholds decide when a measurement becomes a finding. Evidence definitions describe what a "
        "finding means. Patterns connect combinations of findings to an operational pathway. "
        "Changes are validated before they are saved and apply to the next run.",
        "blue",
    )

    thresholds_tab, evidence_tab, patterns_tab, paths_tab = st.tabs(
        ["Thresholds", "Evidence", "Patterns", "Assessment paths"]
    )
    with thresholds_tab:
        _thresholds(service, policy)
    with evidence_tab:
        _evidence(service, policy)
    with patterns_tab:
        _patterns(service, policy)
    with paths_tab:
        _scopes(policy)

    section("Reset", "Restore the shipped example policy. This replaces every change made here.")
    if st.button("Restore example policy"):
        service.reset_rules()
        clear_frontend_caches()
        st.toast("Example policy restored.")
        st.rerun()


# ---------------------------------------------------------------------------- saving
def _explain(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{' → '.join(str(part) for part in err['loc'])}: {err['msg']}"
            for err in exc.errors()[:4]
        )
    return str(exc)


def _commit(service, policy: dict, updated: dict, message: str) -> None:
    updated["revision"] = int(policy.get("revision", 1)) + 1
    try:
        service.save_rules(updated)
    except (ValidationError, ValueError) as exc:
        st.error(f"Not saved. {_explain(exc)}")
        return
    clear_frontend_caches()
    st.toast(message)
    st.rerun()


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


# ------------------------------------------------------------------------ thresholds
def _thresholds(service, policy: dict) -> None:
    section("Thresholds", "Deterministic rules that promote a raw observation into a finding.")
    thresholds = copy.deepcopy(policy["threshold_policies"])

    def save(updated_thresholds: dict, message: str) -> None:
        updated = copy.deepcopy(policy)
        updated["threshold_policies"] = updated_thresholds
        _commit(service, policy, updated, message)

    subhead("Laboratory rules")
    lab_rows = [
        {
            "Measure": name,
            "Direction": rule["direction"],
            "Cutoff": rule["cutoff"],
            "Unit": rule["unit"],
            "Finding": rule["evidence_id"],
            "Meaning": rule["note"],
        }
        for name, rule in thresholds["labs"].items()
    ]
    edited = st.data_editor(
        pd.DataFrame(lab_rows),
        hide_index=True,
        width="stretch",
        num_rows="dynamic",
        column_config={
            "Direction": st.column_config.SelectboxColumn(options=["high", "low"], required=True),
            "Cutoff": st.column_config.NumberColumn(required=True),
            "Finding": st.column_config.TextColumn(disabled=True),
        },
        key="lab_rules_editor",
    )
    if st.button("Save laboratory rules", type="primary"):
        updated = copy.deepcopy(thresholds)
        labs: dict[str, dict] = {}
        for row in edited.to_dict("records"):
            name = str(row.get("Measure", "") or "").strip()
            if not name:
                continue
            labs[name] = {
                "direction": str(row.get("Direction") or "high"),
                "cutoff": float(row.get("Cutoff") or 0),
                "note": str(row.get("Meaning") or "Configured clinical threshold"),
                "unit": str(row.get("Unit") or ""),
                "evidence_id": str(thresholds["labs"].get(name, {}).get("evidence_id", "CLN-001")),
            }
        updated["labs"] = labs
        save(updated, "Laboratory rules saved.")

    subhead("Vital-sign rules")
    st.caption("For the “outside” operator enter the range as two values, for example 60, 100.")
    vital_rows = [
        {
            "Measure": name,
            "Field": rule["field"],
            "Operator": rule["operator"],
            "Cutoff": ", ".join(f"{v:g}" for v in rule["cutoff"])
            if isinstance(rule["cutoff"], list)
            else f"{rule['cutoff']:g}",
            "Unit": rule["unit"],
        }
        for name, rule in thresholds["vitals"]["checks"].items()
    ]
    edited_vitals = st.data_editor(
        pd.DataFrame(vital_rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Field": st.column_config.TextColumn(disabled=True),
            "Operator": st.column_config.SelectboxColumn(
                options=["gt", "lt", "outside"], required=True
            ),
        },
        key="vital_rules_editor",
    )
    if st.button("Save vital-sign rules", type="primary"):
        updated = copy.deepcopy(thresholds)
        checks: dict[str, dict] = {}
        for row in edited_vitals.to_dict("records"):
            name = str(row.get("Measure", "") or "").strip()
            if not name:
                continue
            original = thresholds["vitals"]["checks"].get(name, {})
            raw = str(row.get("Cutoff", "0"))
            try:
                values = [
                    float(part)
                    for part in raw.replace("[", "").replace("]", "").split(",")
                    if part.strip()
                ]
            except ValueError:
                st.error(f"Invalid cut-off for {name}: “{raw}”.")
                return
            operator = str(row.get("Operator") or "gt")
            if operator == "outside" and len(values) != 2:
                st.error(f"“Outside” for {name} needs two values, such as 60, 100.")
                return
            if operator != "outside" and len(values) != 1:
                st.error(f"{name} needs a single cut-off value.")
                return
            checks[name] = {
                "field": original.get("field", name),
                "label": original.get("label", name.replace("_", " ").title()),
                "operator": operator,
                "cutoff": values if operator == "outside" else values[0],
                "unit": str(row.get("Unit") or ""),
            }
        updated["vitals"]["checks"] = checks
        save(updated, "Vital-sign rules saved.")

    subhead("Care continuity and utilization")
    left, right = st.columns(2, gap="large")
    with left:
        overdue = st.number_input(
            "Overdue follow-up (days)",
            min_value=0,
            value=int(thresholds["care_gaps"]["overdue_days"]),
            step=1,
            key="overdue_days",
        )
        if st.button("Save care-gap threshold"):
            updated = copy.deepcopy(thresholds)
            updated["care_gaps"]["overdue_days"] = int(overdue)
            save(updated, "Care-gap threshold saved.")
    with right:
        ed_min = st.number_input(
            "Minimum recent ED visits",
            min_value=0,
            value=int(thresholds["utilization"]["ed_min_visits"]),
            step=1,
            key="ed_min",
        )
        inpatient_min = st.number_input(
            "Minimum recent inpatient admissions",
            min_value=0,
            value=int(thresholds["utilization"]["inpatient_min_admissions"]),
            step=1,
            key="ip_min",
        )
        if st.button("Save utilization thresholds"):
            updated = copy.deepcopy(thresholds)
            updated["utilization"]["ed_min_visits"] = int(ed_min)
            updated["utilization"]["inpatient_min_admissions"] = int(inpatient_min)
            save(updated, "Utilization thresholds saved.")


# -------------------------------------------------------------------------- evidence
def _evidence(service, policy: dict) -> None:
    section(
        "Evidence definitions",
        "Evidence IDs are stable. Edit the business meaning without changing the ID.",
    )
    catalog = policy["evidence_catalog"]
    chosen = st.selectbox(
        "Evidence definition",
        list(catalog),
        format_func=lambda key: f"{key}  ·  {catalog[key]['name']}",
        key="evidence_choice",
    )
    item = catalog[chosen]

    with st.form("evidence_form"):
        name = st.text_input("Name", value=item["name"])
        description = st.text_area("Business meaning", value=item["description"], height=100)
        lifecycle = st.selectbox(
            "Lifecycle",
            LIFECYCLES,
            index=LIFECYCLES.index(item["lifecycle"]) if item["lifecycle"] in LIFECYCLES else 0,
        )
        priority_relevant = st.checkbox(
            "Counts toward assessment priority", value=bool(item.get("priority_relevant", True))
        )
        save = st.form_submit_button("Save evidence definition", type="primary")

    if save:
        updated = copy.deepcopy(policy)
        updated["evidence_catalog"][chosen].update(
            {
                "name": name.strip(),
                "description": description.strip(),
                "lifecycle": lifecycle,
                "priority_relevant": priority_relevant,
            }
        )
        _commit(service, policy, updated, f"{chosen} saved.")

    subhead("All definitions")
    table(
        ["ID", "Name", "Domain", "Lifecycle", "Counts toward priority"],
        [
            (
                key,
                value["name"],
                value["domain"],
                value["lifecycle"],
                "Yes" if value.get("priority_relevant", True) else "No",
            )
            for key, value in catalog.items()
        ],
    )


# -------------------------------------------------------------------------- patterns
def _patterns(service, policy: dict) -> None:
    section(
        "Evidence patterns",
        "Map combinations of findings to an operational implication. No numerical weighting is involved.",
    )
    patterns = policy["decision_patterns"]
    key = st.selectbox(
        "Pattern", list(patterns), format_func=lambda k: patterns[k]["name"], key="pattern_choice"
    )
    pattern = patterns[key]

    with st.form("pattern_form"):
        name = st.text_input("Pattern name", value=pattern["name"])
        required_all = st.text_input(
            "All of these evidence IDs", value=", ".join(pattern.get("required_all", []))
        )
        required_any = st.text_input(
            "At least one of these evidence IDs", value=", ".join(pattern.get("required_any", []))
        )
        also_any = st.text_input(
            "Also one of these evidence IDs", value=", ".join(pattern.get("also_any", []))
        )
        diagnoses = st.text_input(
            "Diagnosis context (optional)", value=", ".join(pattern.get("diagnoses_any", []))
        )
        implication = st.text_area(
            "Operational implication", value=pattern["implication"], height=90
        )
        pathway = st.text_input("Suggested pathway", value=pattern["pathway"])
        workflows = st.text_input("Workflow flags", value=", ".join(pattern.get("workflows", [])))
        save = st.form_submit_button("Save pattern", type="primary")

    if save:
        updated = copy.deepcopy(policy)
        updated["decision_patterns"][key].update(
            {
                "name": name.strip(),
                "required_all": _csv(required_all),
                "required_any": _csv(required_any),
                "also_any": _csv(also_any),
                "diagnoses_any": _csv(diagnoses),
                "implication": implication.strip(),
                "pathway": pathway.strip(),
                "workflows": _csv(workflows),
            }
        )
        _commit(service, policy, updated, f"{name.strip()} saved.")

    subhead("All patterns")
    cards = []
    for value in patterns.values():
        needs = (
            value.get("required_all", [])
            + value.get("required_any", [])
            + value.get("also_any", [])
        )
        context = ", ".join(needs) or "Diagnosis context only"
        cards.append((value["name"], f"{value['implication']} Evidence: {context}.", "violet"))
    grid(cards, cols=2)


# ---------------------------------------------------------------------------- scopes
def _scopes(policy: dict) -> None:
    section(
        "Assessment paths",
        "Overall uses the Supervisor to select capabilities. Focused paths use their configured specialist agent.",
    )
    rows = [
        (
            scope["name"],
            "Overall" if scope["mode"] == "overall" else "Focused",
            policy["agents"][scope["agent"]]["name"],
            ", ".join(policy["tools"][tool]["name"] for tool in scope["tools"]),
            ", ".join(audience.replace("_", " ").title() for audience in scope["handoffs"]),
        )
        for scope in policy["scopes"].values()
    ]
    table(["Assessment", "Route", "Agent", "Capabilities", "Stakeholder views"], rows)
