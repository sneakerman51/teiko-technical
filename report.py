"""Run the Part 2-4 analysis and write the results to outputs/."""

import sqlite3
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure
import analysis
from db import DB_PATH, get_connection

OUTPUT_DIR = Path(__file__).parent / "outputs"
FIGURE_DPI = 150


def save_table(df: pd.DataFrame, filename: str, float_format: str | None = None) -> None:
    """Write a DataFrame to outputs/ as CSV."""
    path = OUTPUT_DIR / filename
    df.to_csv(path, index=False, float_format=float_format)
    print(f"Wrote {path}")


def save_figure(fig: Figure, filename: str) -> None:
    """Save a figure to outputs/ and release it."""
    path = OUTPUT_DIR / filename
    fig.savefig(path, dpi=FIGURE_DPI)
    plt.close(fig)
    print(f"Wrote {path}")


def write_frequencies(conn: sqlite3.Connection) -> None:
    """Part 2: per-sample relative frequency of each cell population."""
    save_table(analysis.get_cell_frequencies(conn), "part2_frequencies.csv")


def write_response_analysis(conn: sqlite3.Connection) -> None:
    """Part 3: responder vs non-responder stats and boxplots."""
    cohort, results = analysis.run_response_analysis(conn)
    save_table(results, "part3_response_stats.csv")
    save_figure(analysis.plot_boxplots(cohort), "part3_boxplots.png")


def write_subset_analysis(conn: sqlite3.Connection) -> None:
    """Part 4: sample subset counts and the B cell average."""
    samples = analysis.get_baseline_samples(conn)
    save_table(analysis.count_samples_by_project(samples), "part4_samples_by_project.csv")
    save_table(analysis.count_subjects_by_response(samples), "part4_subjects_by_response.csv")
    save_table(analysis.count_subjects_by_sex(samples), "part4_subjects_by_sex.csv")

    average = pd.DataFrame({"mean_b_cell_count": [analysis.average_b_cell_count(conn)]})
    save_table(average, "part4_avg_b_cell_count.csv", float_format="%.2f")


def main() -> None:
    """Run every analysis part with the pipeline's database."""
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found at {DB_PATH}. Run load_data.py first.")
    OUTPUT_DIR.mkdir(exist_ok=True)
    with get_connection() as conn:
        write_frequencies(conn)
        write_response_analysis(conn)
        write_subset_analysis(conn)


if __name__ == "__main__":
    main()