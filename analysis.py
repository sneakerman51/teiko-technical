"""
analysis.py
Implements parts 2, 3, and 4 of the analysis pipeline.

"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests


# Part 2


def get_cell_frequencies(conn: sqlite3.Connection) -> pd.DataFrame:
    """Return each sample's cell population count and relative frequency."""
    query = """
    SELECT "sample_id", "population", "count"
    FROM cell_counts
    """

    
    df = pd.read_sql_query(query, conn)
    df["total_count"] = df.groupby("sample_id")["count"].transform("sum")
    df["percentage"] = df["count"]/df["total_count"] * 100

    return df[["sample_id", "total_count", "population", "count", "percentage"]]


# Part 3

ALPHA = 0.05
CONDITION = "melanoma"
TREATMENT = "miraclib"
SAMPLE_TYPE = "PBMC"
RESPONDER = "yes"
NON_RESPONDER = "no"
CORRECTION_METHOD = "holm"
BASE_TIMEPOINT = 0
PANEL_WIDTH_IN = 3
PANEL_HEIGHT_IN = 4


def get_sample_metadata(conn: sqlite3.Connection) -> pd.DataFrame:
    """Return one row for each sample with subject attributes needed to filter."""
    query = """
    SELECT s."sample_id",
            s.subject_id,
            s.sample_type,
            s.time_from_treatment_start,
            sub.condition,
            sub.treatment,
            sub.response
    FROM samples AS s
    JOIN subjects AS sub ON s.subject_id = sub.subject_id
    """
    return pd.read_sql_query(query, conn)


def select_cohort(freq_df: pd.DataFrame, meta_df: pd.DataFrame, timepoint: int = BASE_TIMEPOINT) -> pd.DataFrame:
    """Keep melanoma, miraclib, and PBMC samples with a recorded response at a single timepoint."""
    merged = freq_df.merge(meta_df, on="sample_id", how="inner")
    is_target = (
        (merged["condition"] == CONDITION)
        & (merged["treatment"] == TREATMENT)
        & (merged["sample_type"] == SAMPLE_TYPE)
        & (merged["time_from_treatment_start"] == timepoint)
        & (merged["response"].isin([RESPONDER, NON_RESPONDER]))
    )
    return merged.loc[is_target]


def split_by_response(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Return (responder, non-responder) percentages from a cohort."""
    responders = df.loc[df["response"] == RESPONDER, "percentage"]
    non_responders = df.loc[df["response"] == NON_RESPONDER, "percentage"]
    return responders, non_responders


def compare_populations(cohort: pd.DataFrame) -> pd.DataFrame:
    """Run a Mann-Whitney U test per population, Holm-corrected across populations."""
    rows = []
    for population, group in cohort.groupby("population"):
        responders, non_responders = split_by_response(group)
        _, p_value = mannwhitneyu(responders, non_responders, alternative="two-sided")
        rows.append({
            "population": population,
            "n_responder": len(responders),
            "n_non_responder": len(non_responders),
            "median_responder": responders.median(),
            "median_non_responder": non_responders.median(),
            "p_value": p_value,
        })

    results = pd.DataFrame(rows)
    reject, p_adjusted, _, _ = multipletests(
        results["p_value"], alpha=ALPHA, method=CORRECTION_METHOD
    )
    results["p_adjusted"] = p_adjusted
    results["significant"] = reject
    return results


def plot_boxplots(cohort: pd.DataFrame) -> Figure:
    """Boxplots of relative frequency, responders vs non-responders, per population.

    The cohort must contain a single timepoint.
    """
    timepoints = cohort["time_from_treatment_start"].unique()
    if len(timepoints) != 1:
        raise ValueError(f"Expected one timepoint, found {len(timepoints)}")

    populations = sorted(cohort["population"].unique())
    fig, axes = plt.subplots(
        1, len(populations),
        figsize=(PANEL_WIDTH_IN * len(populations), PANEL_HEIGHT_IN),
    )

    for ax, population in zip(axes, populations):
        panel = cohort[cohort["population"] == population]
        responders, non_responders = split_by_response(panel)
        ax.boxplot([responders, non_responders], tick_labels=["Responders", "Non-responders"])
        ax.set_title(population)
        ax.set_ylabel("Relative frequency (%)")

    fig.suptitle(
        "Cell Population Frequencies: Responders vs Non-Responders\n"
        f"{CONDITION.title()}, {TREATMENT.title()}, {SAMPLE_TYPE} samples"
    )
    fig.tight_layout()
    return fig


def run_response_analysis(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return cohort and its cell population test results."""
    freq_df = get_cell_frequencies(conn)
    meta_df = get_sample_metadata(conn)
    cohort = select_cohort(freq_df, meta_df)
    return cohort, compare_populations(cohort)


# Part 4

def get_baseline_samples(
    conn: sqlite3.Connection,
    condition: str = CONDITION,
    treatment: str = TREATMENT,
    sample_type: str = SAMPLE_TYPE,
    timepoint: int = BASE_TIMEPOINT,
) -> pd.DataFrame:
    """Return one row for each sample matching the given filters."""
    query = """
    SELECT s.sample_id,
           s.subject_id,
           sub.project,
           sub.sex,
           sub.response
    FROM samples AS s
    JOIN subjects AS sub ON s.subject_id = sub.subject_id
    WHERE sub.condition = :condition
      AND sub.treatment = :treatment
      AND s.sample_type = :sample_type
      AND s.time_from_treatment_start = :timepoint
    """
    params = {
        "condition": condition,
        "treatment": treatment,
        "sample_type": sample_type,
        "timepoint": timepoint,
    }
    return pd.read_sql_query(query, conn, params=params)


def count_samples_by_project(samples: pd.DataFrame) -> pd.DataFrame:
    """Return the number of samples in each project."""
    return (
        samples.groupby("project")["sample_id"].nunique()
        .rename("n_samples")
        .reset_index()
    )


def count_subjects_by_response(samples: pd.DataFrame) -> pd.DataFrame:
    """Return the number of subjects in each response group."""
    return (
        samples.groupby("response")["subject_id"].nunique()
        .rename("n_subjects")
        .reset_index()
    )


def count_subjects_by_sex(samples: pd.DataFrame) -> pd.DataFrame:
    """Return the number of subjects of each sex."""
    return (
        samples.groupby("sex")["subject_id"].nunique()
        .rename("n_subjects")
        .reset_index()
    )


def average_b_cell_count(
    conn: sqlite3.Connection,
    condition: str = CONDITION,
    sex: str = "M",
    response: str = RESPONDER,
    timepoint: int = BASE_TIMEPOINT,
) -> float:
    """Return the mean B cell count across all sample and treatment types."""
    query = """
    SELECT AVG(c.count)
    FROM cell_counts AS c
    JOIN samples AS s ON s.sample_id = c.sample_id
    JOIN subjects AS sub ON sub.subject_id = s.subject_id
    WHERE c.population = 'b_cell'
      AND sub.condition = :condition
      AND sub.sex = :sex
      AND sub.response = :response
      AND s.time_from_treatment_start = :timepoint
    """
    params = {
        "condition": condition,
        "sex": sex,
        "response": response,
        "timepoint": timepoint,
    }
    (average,) = conn.execute(query, params).fetchone()
    return round(average, 2)
