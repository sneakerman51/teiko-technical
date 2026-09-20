"""Streamlit dashboard presenting the Part 2-4 analysis results."""

import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
import analysis
from db import DB_PATH, get_connection

#Cached loaders


@st.cache_data
def load_frequencies() -> pd.DataFrame:
    """Return per-sample cell population frequencies (Part 2)."""
    with get_connection() as conn:
        return analysis.get_cell_frequencies(conn)


@st.cache_data
def load_response_analysis() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return cohort and its test results (Part 3)."""
    with get_connection() as conn:
        return analysis.run_response_analysis(conn)


@st.cache_resource
def build_boxplots() -> Figure:
    """Build the responder vs non-responder boxplots once."""
    cohort, _ = load_response_analysis()
    return analysis.plot_boxplots(cohort)


@st.cache_data
def load_baseline_samples() -> pd.DataFrame:
    """Return melanoma, miraclib, PBMC samples (Part 4)."""
    with get_connection() as conn:
        return analysis.get_baseline_samples(conn)


@st.cache_data
def load_average_b_cell_count() -> float:
    """Return the mean B cell count for melanoma male responders at t=0."""
    with get_connection() as conn:
        return analysis.average_b_cell_count(conn)


# Tab renderers

def render_frequencies_tab() -> None:
    """Show the relative frequency of each population per sample."""
    st.subheader("Cell population relative frequencies")
    st.dataframe(load_frequencies(), hide_index=True)


def render_response_tab() -> None:
    """Show boxplots and statistics for responders vs non-responders."""
    _, results = load_response_analysis()
    st.subheader("Responders vs non-responders at time from treatment start = 0")
    st.caption(
        "Melanoma, miraclib, PBMC samples. "
        "Mann-Whitney U per population, Holm-corrected."
    )
    st.pyplot(build_boxplots())
    display = results.assign(significant=results["significant"].map({True: "Yes", False: "No"}))
    st.dataframe(display, hide_index=True)
    n_significant = int(results["significant"].sum())
    st.write(
        f"{n_significant} of {len(results)} populations differ "
        f"significantly after correction."
    )


def render_subset_tab() -> None:
    """Show counts for the subset and the B cell average."""
    samples = load_baseline_samples()
    st.subheader("Melanoma PBMC samples treated with miraclib at time from treatment start = 0")

    col_project, col_response, col_sex = st.columns(3)
    with col_project:
        st.markdown("**Samples per project**")
        st.dataframe(analysis.count_samples_by_project(samples), hide_index=True)
    with col_response:
        st.markdown("**Subjects by response**")
        st.dataframe(analysis.count_subjects_by_response(samples), hide_index=True)
    with col_sex:
        st.markdown("**Subjects by sex**")
        st.dataframe(analysis.count_subjects_by_sex(samples), hide_index=True)

    st.metric(
        "Mean B cell count: melanoma males, responders, time = 0",
        f"{load_average_b_cell_count():.2f}",
    )


def main() -> None:
    """Lay out the dashboard."""
    st.set_page_config(page_title="Cell Count Analysis", layout="wide")
    st.title("Cell Count Analysis")

    if not DB_PATH.exists():
        st.error(f"Database not found at {DB_PATH}. Run `make pipeline` first.")
        st.stop()

    tab_freq, tab_response, tab_subset = st.tabs(
        ["Part 2: Frequencies", "Part 3: Response analysis", "Part 4: Subset analysis"]
    )
    with tab_freq:
        render_frequencies_tab()
    with tab_response:
        render_response_tab()
    with tab_subset:
        render_subset_tab()


main()