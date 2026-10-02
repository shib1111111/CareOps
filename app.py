from __future__ import annotations

import sys
from pathlib import Path

# Let `streamlit run app.py` work from a plain checkout, with or without `pip install -e .`
_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import streamlit as st  # noqa: E402

from frontend.pages.assessments import page as assessments_page  # noqa: E402
from frontend.pages.data_explorer import page as data_page  # noqa: E402
from frontend.pages.documentation import page as documentation_page  # noqa: E402
from frontend.pages.policy_studio import page as policy_page  # noqa: E402
from frontend.runtime import LOGO, LOGO_MARK, VERSION, inject_css  # noqa: E402
from frontend.ui import footer  # noqa: E402

st.set_page_config(
    page_title="CareOps",
    page_icon=str(LOGO_MARK),
    layout="wide",
    initial_sidebar_state="expanded",
)
st.logo(str(LOGO), icon_image=str(LOGO_MARK), size="large")
inject_css()

navigation = st.navigation(
    [
        st.Page(
            assessments_page,
            title="Home",
            icon=":material/assignment:",
            default=True,
            url_path="assessments",
        ),
        st.Page(
            policy_page, title="Policy Studio", icon=":material/tune:", url_path="policy-studio"
        ),
        st.Page(
            documentation_page,
            title="Documentation",
            icon=":material/menu_book:",
            url_path="documentation",
        ),
        st.Page(data_page, title="Data Explorer", icon=":material/database:", url_path="data"),
    ],
    position="sidebar",
)

with st.sidebar:
    st.markdown(
        "<div class='side-note'><strong>Proof of concept</strong>"
        "Evidence-backed AI decision support for turning complex member data into clear, actionable decisions.</div>",
        unsafe_allow_html=True,
    )

navigation.run()
footer(VERSION)
