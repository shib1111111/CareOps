from __future__ import annotations

PATIENT_COLUMNS = [
    "patient_id",
    "patient_name",
    "age",
    "gender",
    "diagnosis",
    "current_medication",
    "lab_test",
    "lab_value",
    "lab_unit",
    "last_visit_date",
    "next_scheduled_visit",
    "days_since_last_visit",
    "missed_last_appointment",
    "vitals_bp_systolic",
    "vitals_bp_diastolic",
    "vitals_heart_rate",
    "vitals_spo2",
    "notes",
]
DATE_COLUMNS = ["last_visit_date", "next_scheduled_visit"]
NUMERIC_COLUMNS = [
    "age",
    "lab_value",
    "days_since_last_visit",
    "vitals_bp_systolic",
    "vitals_bp_diastolic",
    "vitals_heart_rate",
    "vitals_spo2",
]
CLAIM_COLUMNS = [
    "claim_id",
    "patient_id",
    "service_date",
    "service_type",
    "place_of_service",
    "diagnosis_group",
    "claim_status",
    "allowed_amount",
    "paid_amount",
]
CLAIM_DATE_COLUMNS = ["service_date"]
CLAIM_NUMERIC_COLUMNS = ["allowed_amount", "paid_amount"]
ENROLLMENT_COLUMNS = [
    "patient_id",
    "member_plan_id",
    "plan_name",
    "product_type",
    "csnp_enrolled",
    "coverage_status",
    "coverage_start",
    "pcp_group",
    "benefit_variant",
]
