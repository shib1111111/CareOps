from __future__ import annotations

import json

import streamlit as st

from frontend.runtime import get_service, runtime_pills
from frontend.ui import (
    callout,
    code,
    figure,
    flow,
    grid,
    json_block,
    page_header,
    section,
    table,
)


def page() -> None:
    """Render the CareOps documentation page."""
    service = get_service()
    policy = service.rules()

    page_header(
        "Documentation",
        (
            "Understand what CareOps does, why it matters, how a review moves from "
            "member information to an actionable decision, and how the platform can "
            "support people across care, navigation, operations, and leadership."
        ),
        runtime_pills(service),
    )

    overview, architecture, evidence, storage, api = st.tabs(
        [
            "Overview",
            "How CareOps Works",
            "Evidence & Policy",
            "Run Storage",
            "API",
        ]
    )

    with overview:
        _overview(policy)

    with architecture:
        _architecture(policy)

    with evidence:
        _evidence()

    with storage:
        _storage()

    with api:
        _api()


def _overview(policy: dict) -> None:
    """Business-first explanation of CareOps."""
    section(
        "CareOps at a glance",
        (
            "CareOps is a value-based AI decision-support platform that turns scattered "
            "member information into a clear, reviewable next step for the people responsible "
            "for care and operations."
        ),
        1,
    )

    callout(
        "The business idea",
        (
            "Important signals are often available in different places—clinical measurements, "
            "recent visits, utilization history, diagnoses, and other member information. "
            "The challenge is not simply finding the data; it is deciding what deserves attention "
            "now, why it matters, and what a human team should do next."
            "\n\n"
            "CareOps brings those signals together, applies configured decision rules, identifies "
            "meaningful patterns, and produces one structured assessment that a person can review "
            "and act on."
        ),
        "blue",
    )

    figure(
        "careops_business_architecture.svg",
        "Business architecture",
        "Member information → meaningful signals → decision → action → stakeholder hand-off",
        "CareOps business architecture",
    )

    section(
        "Why this matters",
        (
            "For a business audience, CareOps is not primarily about AI technology. "
            "It is about improving the journey from information to action."
        ),
        2,
    )

    grid(
        [
            (
                "Find what matters",
                "Reduce the time spent scanning large amounts of information by highlighting the signals that require attention.",
                "blue",
            ),
            (
                "Explain the decision",
                "Show the observations and evidence behind a recommendation instead of presenting a black-box result.",
                "green",
            ),
            (
                "Coordinate the next step",
                "Give each stakeholder the version of the decision that is relevant to their responsibility.",
                "violet",
            ),
            (
                "Create repeatable operations",
                "Turn a one-off review into a consistent process that can be repeated across members and review types.",
                "amber",
            ),
        ],
        cols=4,
    )

    section(
        "From reactive work to proactive action",
        (
            "Traditional operational reviews often begin with a queue, a spreadsheet, or a large "
            "set of records. A person then has to identify important cases, interpret the available "
            "information, decide what deserves escalation, and communicate the result."
            "\n\n"
            "CareOps moves that work into a repeatable decision-support flow. The system prepares "
            "the assessment first, while the human remains responsible for reviewing the result and "
            "deciding what should happen."
        ),
        3,
    )

    flow(
        [
            (
                "1. Understand the member",
                "Bring together the available clinical, utilization, and continuity context.",
            ),
            (
                "2. Detect meaningful signals",
                "Apply configured thresholds and evidence rules to identify relevant findings.",
            ),
            (
                "3. Connect the signals",
                "Recognize combinations of findings that may indicate a broader operational concern.",
            ),
            (
                "4. Prioritize",
                "Assign a deterministic priority based on the configured decision policy.",
            ),
            (
                "5. Explain the result",
                "Generate a concise assessment, rationale, next step, and stakeholder-specific views.",
            ),
            (
                "6. Enable human action",
                "Let the responsible team review, validate, and act on the assessment.",
            ),
        ]
    )

    section(
        "Who gets value from the same decision?",
        (
            "The underlying assessment stays consistent, but the way it is communicated changes "
            "depending on who needs it."
        ),
        4,
    )

    grid(
        [
            (
                "Member",
                (
                    "A simple explanation of what was identified, why it matters, "
                    "and what may happen next."
                ),
                "blue",
            ),
            (
                "Care team",
                (
                    "The supporting clinical and continuity context needed for "
                    "operational review and follow-up."
                ),
                "green",
            ),
            (
                "Navigator",
                (
                    "The pathway, eligibility, outreach, and coordination context "
                    "relevant to navigation workflows."
                ),
                "violet",
            ),
            (
                "Health plan / operations",
                (
                    "A concise view of priority, workflow relevance, supporting evidence, "
                    "and potential operational action."
                ),
                "amber",
            ),
        ],
        cols=4,
    )

    section(
        "What CareOps is not",
        None,
        5,
    )

    callout(
        "Decision support, not decision replacement",
        (
            "CareOps is designed to help people make better-informed operational decisions. "
            "It does not replace clinicians, care managers, navigators, or other accountable "
            "professionals. The platform identifies and explains signals; the responsible human "
            "decides what action is appropriate."
        ),
        "amber",
    )

    section(
        "Review types",
        (
            "Different workflows can enter CareOps through different review types. "
            "Each review has a defined purpose and produces its own saved result."
        ),
        6,
    )

    table(
        ["Review", "Route", "Agent", "AI calls", "Business purpose"],
        [
            (
                scope["name"],
                "Overall" if scope["mode"] == "overall" else "Focused",
                policy["agents"][scope["agent"]]["name"],
                "2 (route + write)" if scope["mode"] == "overall" else "1 (write)",
                _review_business_purpose(scope["mode"], scope["name"]),
            )
            for scope in policy["scopes"].values()
        ],
    )


def _review_business_purpose(mode: str, name: str) -> str:
    """Return a business-friendly explanation for a configured review."""
    normalized = name.lower()

    if mode == "overall":
        return (
            "Combines relevant capabilities to create one broad member assessment "
            "and determine the most important follow-up."
        )

    if "clinical" in normalized:
        return (
            "Focused review of clinical signals and condition-related observations "
            "that may require attention."
        )

    if "gap" in normalized:
        return (
            "Focused review of missed or delayed care, continuity issues, "
            "and follow-up opportunities."
        )

    if "utilization" in normalized:
        return (
            "Focused review of utilization patterns and signals that may influence "
            "care coordination or operational follow-up."
        )

    if "navigation" in normalized:
        return (
            "Focused review of navigation-relevant signals, pathways, and "
            "member support opportunities."
        )

    return "A focused assessment for a specific operational question or domain."


def _architecture(policy: dict) -> None:
    """Explain the operating model from business and technical perspectives."""
    section(
        "How CareOps works",
        (
            "The platform separates three responsibilities: understanding the available information, "
            "applying business rules, and communicating the result. This separation makes the process "
            "easier to understand, test, audit, and change."
        ),
        1,
    )

    figure(
        "careops_technical_architecture.svg",
        "CareOps operating model",
        (
            "Deterministic evaluation establishes the facts; AI converts those facts into "
            "clear communication and stakeholder-ready output."
        ),
        "CareOps technical architecture",
    )

    section(
        "What happens during a review?",
        (
            "A CareOps run follows a repeatable sequence. The exact capability selection may differ "
            "between an overall assessment and a focused review, but the core decision flow remains consistent."
        ),
        2,
    )

    table(
        ["Step", "What happens", "Role of AI", "Why it matters"],
        [
            (
                "1. Select capabilities",
                (
                    "An overall review selects from the configured capability set. "
                    "A focused review starts with its predefined capability."
                ),
                "Overall only",
                (
                    "The system determines which areas should contribute to the assessment "
                    "without changing the underlying business rules."
                ),
            ),
            (
                "2. Evaluate information",
                ("Python functions apply configured thresholds and rules to the member's records."),
                "No",
                ("Creates consistent, repeatable findings from the source information."),
            ),
            (
                "3. Match patterns",
                ("Configured combinations of findings are matched to an implication and pathway."),
                "No",
                ("Connects individual signals into a meaningful operational context."),
            ),
            (
                "4. Determine priority",
                (
                    "Priority is calculated from the configured decision tiers and relevant findings."
                ),
                "No",
                ("Keeps prioritization tied to explicit policy rather than generated language."),
            ),
            (
                "5. Write the assessment",
                (
                    "The model converts the structured findings and patterns into a summary, "
                    "actions, rationale, and stakeholder views."
                ),
                "Yes",
                ("Makes the result easier for people to understand and use."),
            ),
            (
                "6. Validate",
                ("The output is checked against the known evidence and allowed audiences."),
                "No",
                (
                    "Prevents the generated response from introducing unsupported evidence "
                    "or changing the system's calculated priority."
                ),
            ),
            (
                "7. Store",
                ("The completed assessment is saved under the agent and review that produced it."),
                "No",
                ("Allows the result to be retrieved, reviewed, and reused operationally."),
            ),
        ],
    )

    section(
        "Where AI adds value",
        ("CareOps deliberately gives different jobs to deterministic software and generative AI."),
        3,
    )

    grid(
        [
            (
                "Rules establish facts",
                (
                    "Thresholds, evidence mappings, priority tiers, and configured patterns "
                    "determine what the system has actually observed."
                ),
                "green",
            ),
            (
                "AI communicates meaning",
                (
                    "The model turns the structured findings into concise language, explanations, "
                    "actions, and audience-specific messages."
                ),
                "violet",
            ),
            (
                "Humans own the action",
                (
                    "Care teams, navigators, and operational users remain responsible for reviewing "
                    "the information and deciding what should happen."
                ),
                "blue",
            ),
        ],
        cols=3,
    )

    callout(
        "Why this separation is important",
        (
            "An AI-generated sentence should not be the source of truth for a calculated priority "
            "or an evidence identifier. CareOps therefore establishes the factual findings and "
            "decision priority before the model writes the narrative. This makes the output more "
            "transparent and easier to review."
        ),
        "green",
    )

    section(
        "Agents and capabilities",
        (
            "Agents represent responsibility areas, while capabilities represent the specific "
            "domains of analysis available to those agents."
        ),
        4,
    )

    table(
        ["Agent", "Role", "Business responsibility"],
        [
            (
                agent["name"],
                agent["role"],
                agent["purpose"],
            )
            for agent in policy["agents"].values()
        ],
    )

    st.write("")

    table(
        ["Capability", "Domain", "Execution", "What it contributes"],
        [
            (
                tool["name"],
                tool["domain"],
                tool["execution"],
                tool["purpose"],
            )
            for tool in policy["tools"].values()
        ],
    )

    section(
        "Independent reviews and reusable results",
        None,
        5,
    )

    callout(
        "A review is its own decision",
        (
            "A new focused review does not automatically depend on a previous overall review. "
            "Each review executes its configured capabilities against the member's current data "
            "and produces its own result."
            "\n\n"
            "At the same time, CareOps can reuse a previously saved assessment when the same review "
            "for the same member was already completed against unchanged data and policy. A Fresh Run "
            "option allows users to explicitly create a new assessment."
        ),
        "blue",
    )

    section(
        "Why this is useful operationally",
        (
            "This model supports both consistency and flexibility. Teams can standardize how important "
            "signals are evaluated while still creating different views for different workflows."
        ),
        6,
    )

    grid(
        [
            (
                "For operations",
                "A repeatable process reduces dependence on individual interpretation and manual triage.",
                "amber",
            ),
            (
                "For managers",
                "The resulting queue and summaries make it easier to understand where attention is being directed and why.",
                "blue",
            ),
            (
                "For analysts",
                "The underlying evidence and configuration remain visible rather than hidden behind generated text.",
                "green",
            ),
            (
                "For technology teams",
                "The separation of policy, execution, generation, validation, and storage makes the system modular.",
                "violet",
            ),
        ],
        cols=4,
    )


def _evidence() -> None:
    """Explain evidence, thresholds, and patterns in plain language."""
    section(
        "How CareOps decides what matters",
        (
            "CareOps uses several distinct policy concepts so that a business user can understand "
            "the difference between an observation, evidence, and an operational interpretation."
        ),
        1,
    )

    grid(
        [
            (
                "Threshold policy",
                (
                    "Defines when an observed value becomes meaningful enough to create a finding. "
                    "For example, a measurement above a configured cut-off can become a flagged signal."
                ),
                "blue",
            ),
            (
                "Evidence catalog",
                (
                    "Gives each finding a stable identity and meaning. This creates a consistent "
                    "language for the system and the people reviewing its output."
                ),
                "green",
            ),
            (
                "Evidence pattern",
                (
                    "Connects multiple findings into a broader interpretation, such as a clinical "
                    "concern combined with a continuity gap."
                ),
                "violet",
            ),
        ]
    )

    section(
        "From a single observation to a business-relevant signal",
        (
            "A single measurement rarely tells the complete story. CareOps therefore preserves the "
            "original observation and can also recognize when multiple findings together create a "
            "stronger operational signal."
        ),
        2,
    )

    callout(
        "Illustrative example",
        (
            "HbA1c 9.9 → CLN-001\n"
            "Systolic BP 174 → CLN-002\n"
            "251 days since last visit → GAP-001\n\n"
            "The configured pattern linking CLN-001 and GAP-001 can then identify a broader "
            "clinical concern associated with a continuity gap."
        ),
        "green",
    )

    section(
        "Why evidence IDs matter",
        (
            "Every finding has a stable identifier so that the system can consistently connect "
            "the observation, the rule that produced it, the explanation shown to a user, and "
            "the downstream action that references it."
        ),
        3,
    )

    table(
        ["Field", "What it means", "Why it matters"],
        [
            (
                code("evidence_id"),
                "Stable identifier in the ABC-123 format.",
                "Provides a consistent reference across assessments and actions.",
            ),
            (
                code("domain"),
                "Capability area that produced the finding.",
                "Shows where the observation came from.",
            ),
            (
                code("signal"),
                "What was actually observed.",
                "Keeps the assessment grounded in a concrete fact.",
            ),
            (
                code("value / unit"),
                "The observed member value and its unit.",
                "Makes the finding interpretable without returning to the source record.",
            ),
            (
                code("status"),
                "Flagged or informational.",
                "Distinguishes attention-worthy findings from contextual information.",
            ),
            (
                code("interpretation"),
                "Configured meaning displayed with the finding.",
                "Provides understandable context for the observation.",
            ),
        ],
    )

    section(
        "Policy changes versus new findings",
        None,
        4,
    )

    callout(
        "Adding evidence does not automatically create a finding",
        (
            "The evidence catalog defines what an Evidence ID means, but it does not decide "
            "when that evidence should appear. A threshold, rule, or capability mapping must "
            "also produce the Evidence ID."
        ),
        "amber",
    )

    section(
        "Why this structure helps non-technical users",
        ("The architecture keeps three questions separate:"),
        5,
    )

    grid(
        [
            (
                "What happened?",
                "The observation recorded in the member data.",
                "blue",
            ),
            (
                "Why is it important?",
                "The interpretation and pattern defined by business and domain policy.",
                "green",
            ),
            (
                "What should happen next?",
                "The operational action or follow-up generated for human review.",
                "violet",
            ),
        ],
        cols=3,
    )


def _storage() -> None:
    """Explain persistence and reproducibility."""
    section(
        "Where assessments are stored",
        (
            "Every assessment becomes a reusable operational record rather than a temporary "
            "chat response. Results are organized by the agent responsible for the review."
        ),
        1,
    )

    st.code(
        "data/runs/\n"
        "├── careops_supervisor/       Overall Member Assessment\n"
        "├── clinical_specialist/      Clinical Review\n"
        "├── care_gap_specialist/      Care Gap Review\n"
        "├── utilization_specialist/   Utilization Review\n"
        "└── navigation_specialist/    Navigation Review\n"
        "      ├── runs.parquet\n"
        "      ├── findings.parquet\n"
        "      └── actions.parquet",
        language="text",
    )

    callout(
        "Why saved results matter",
        (
            "A saved assessment creates continuity between one review and the next. "
            "Users can retrieve what was already assessed, inspect the supporting findings, "
            "and avoid unnecessary repeat processing when the underlying inputs have not changed."
        ),
        "blue",
    )

    section(
        "What is stored?",
        (
            "CareOps keeps the decision itself separate from the individual findings that support it "
            "and the actions that result from it."
        ),
        2,
    )

    table(
        ["Table", "One row represents", "Key information", "Business meaning"],
        [
            (
                code("runs"),
                "A completed assessment",
                (
                    "run_id, agent_key, scope, member_id, priority, status, "
                    "flagged_count, llm_calls, duration_ms, created_at, contract_json"
                ),
                "The overall decision record.",
            ),
            (
                code("findings"),
                "One finding",
                ("run_id, evidence_id, domain, signal, value, unit, status"),
                "The facts and observations supporting the decision.",
            ),
            (
                code("actions"),
                "One recommended action",
                ("run_id, sequence, owner, action, evidence_refs"),
                "The practical follow-up associated with the assessment.",
            ),
        ],
    )

    section(
        "Consistency and validation",
        (
            "Stored results are validated before they are written. This makes the persisted data "
            "more reliable for dashboards, APIs, downstream analysis, and future database migration."
        ),
        3,
    )

    grid(
        [
            (
                "Structured row validation",
                ("Pydantic models validate RunRow, FindingRow, and ActionRow before storage."),
                "violet",
            ),
            (
                "Explicit data types",
                (
                    "Important categories use explicit pandas dtypes, including ordered priorities, "
                    "nullable counts, and UTC timestamps."
                ),
                "blue",
            ),
            (
                "Exact result retrieval",
                (
                    "The full contract is retained with the run, allowing an assessment to be restored "
                    "from its run ID."
                ),
                "green",
            ),
        ],
        cols=3,
    )

    section(
        "Current storage model",
        None,
        4,
    )

    callout(
        "POC architecture",
        (
            "File-backed Parquet storage is appropriate for the current single-process proof of concept. "
            "The storage interface is separated from the rest of the application so that a database-backed "
            "implementation can replace it later without changing the core assessment concept."
        ),
        "amber",
    )


def _api() -> None:
    """Explain the public API in both business and technical terms."""
    section(
        "Public API",
        (
            "The API exposes CareOps as a reusable decision-support capability rather than limiting it "
            "to a single dashboard. Other applications can submit an assessment request and retrieve "
            "the completed decision through a consistent interface."
        ),
        1,
    )

    section(
        "What the API enables",
        (
            "A future workflow could trigger a CareOps assessment from a care-management application, "
            "operations portal, member workflow, batch process, or another enterprise system."
        ),
        2,
    )

    table(
        ["Method", "Path", "Purpose", "Business use"],
        [
            (
                "POST",
                code("/api/v1/assessments"),
                "Create an assessment",
                "Start a new overall or focused review for a member.",
            ),
            (
                "GET",
                code("/api/v1/assessments/{id}"),
                "Retrieve an assessment",
                "Open a previously completed decision and its supporting information.",
            ),
            (
                "GET",
                code("/health"),
                "Liveness",
                "Confirm that the service is running.",
            ),
            (
                "GET",
                code("/ready"),
                "Readiness",
                "Confirm that required data and policy configuration are available.",
            ),
        ],
    )

    json_block(
        "Request",
        (
            "The assessment type controls whether the request is overall or focused. "
            "The optional instruction can add contextual emphasis without replacing the "
            "configured decision policy."
        ),
        json.dumps(
            {
                "member": {"id": "P0001"},
                "assessment": {"type": "overall"},
                "options": {
                    "instruction": "Focus on the most important near-term follow-up.",
                    "fresh": False,
                },
            },
            indent=2,
        ),
    )

    section(
        "What comes back",
        (
            "The response is designed around the decision a user needs to consume, rather than "
            "exposing implementation details such as prompts or model configuration."
        ),
        3,
    )

    json_block(
        "Response (abridged)",
        "Illustrative response structure.",
        json.dumps(
            {
                "assessment": {
                    "id": "assessment-…",
                    "type": "overall",
                    "status": "ready",
                    "priority": "critical",
                },
                "member": {"id": "P0001"},
                "decision": {
                    "summary": "…",
                    "why_it_matters": "…",
                    "next_step": "…",
                },
                "findings": [
                    {
                        "evidence_id": "CLN-001",
                        "finding": "HbA1c above threshold",
                        "value": "9.9",
                        "unit": "%",
                        "meaning": "Poor glycemic control",
                    }
                ],
                "actions": [
                    {
                        "owner": "Care Team",
                        "action": "…",
                        "supported_by": ["CLN-001"],
                    }
                ],
                "handoffs": [
                    {
                        "audience": "care_team",
                        "message": "…",
                    }
                ],
            },
            indent=2,
        ),
    )

    section(
        "Business interpretation of the response",
        (
            "A consumer of the API does not need to understand the underlying agent architecture "
            "to benefit from the result."
        ),
        4,
    )

    grid(
        [
            (
                "Decision",
                "What was identified, the priority, and the current status.",
                "blue",
            ),
            (
                "Evidence",
                "The observable information that supports the assessment.",
                "green",
            ),
            (
                "Actions",
                "The practical next steps and responsible owner.",
                "violet",
            ),
            (
                "Handoffs",
                "Audience-specific communication for downstream teams or workflows.",
                "amber",
            ),
        ],
        cols=4,
    )

    callout(
        "Designed for integration",
        (
            "The API intentionally exposes the business decision contract rather than the internal "
            "implementation. This makes the same assessment pattern usable across dashboards, "
            "workflow tools, automation, or future enterprise applications."
        ),
        "green",
    )
