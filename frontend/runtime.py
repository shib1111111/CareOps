from __future__ import annotations

from pathlib import Path

import streamlit as st

from careops import __version__
from careops.application.service import CareOpsService

ROOT_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT_DIR / "assets"
LOGO = ASSETS_DIR / "logo.svg"
LOGO_MARK = ASSETS_DIR / "logo_mark.svg"
VERSION = __version__


def inject_css() -> None:
    css = (ASSETS_DIR / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_service() -> CareOpsService:
    return CareOpsService()


def clear_frontend_caches() -> None:
    get_service.clear()
    st.cache_data.clear()


def runtime_pills(service: CareOpsService) -> list[tuple[str, str]]:
    """Header status pills. The model in use is deliberately not shown."""
    return [(f"Policy rev {service.rules()['revision']}", "neutral")]
