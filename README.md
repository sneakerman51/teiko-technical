# Teiko Technical: Immune Cell Population Analysis

Analysis pipeline and interactive dashboard for immune cell population frequencies across patient samples in a clinical trial of the drug candidate miraclib. The project loads `cell-count.csv` into SQLite, computes relative cell population frequencies, tests whether they differ between responders and non-responders, and summarizes a baseline melanoma subset.

**Dashboard:** http://localhost:8501 (available after running `make dashboard`)

## Quick start (GitHub Codespaces)

Place `cell-count.csv` (exact filename) in the repository root, then run:

```bash
make setup       # install dependencies from requirements.txt
make pipeline    # build cell_count.db and write results to outputs/
make dashboard   # start the Streamlit dashboard (run pipeline first)
```

The dashboard runs on port 8501. In Codespaces, open the forwarded port from the Ports tab.

## Outputs

`make pipeline` runs `load_data.py` (creates the database) and then `report.py` (writes to `outputs/`):

| Part | Output | Contents |
|------|--------|----------|
| 2 | `part2_frequencies.csv` | Per sample and population: `sample_id`, `total_count`, `population`, `count`, `percentage` |
| 3 | `part3_response_stats.csv` | Medians, sample sizes, raw and Holm-adjusted p-values, significance flag per population |
| 3 | `part3_boxplots.png` | Responders vs non-responders, one panel per population |
| 4 | `part4_*.csv` | Sample counts by project, subject counts by response and sex, and the B cell average |

`analysis.py` holds all analysis logic, `report.py` and `dashboard.py` present it, and `db.py` and `load_data.py` handle the database.

## Database schema

```
subjects (subject_id PK, project, condition, age, sex, treatment, response)
samples  (sample_id PK, subject_id FK -> subjects, sample_type, time_from_treatment_start)
cell_counts (sample_id FK -> samples, population, count)   PK (sample_id, population)
```

- Subject-level attributes repeat across every sample from the same subject in the CSV, so storing them once in `subjects` removes that redundancy.
- `cell_counts` is long format, so adding a new population is a new row, not a schema change, and per-population queries are simple.
- The composite primary key prevents duplicate counts, and foreign keys are enforced with `PRAGMA foreign_keys = ON`.
- Scaling: New projects, subjects, and populations add rows, not schema changes. For larger data, add indexes on samples.subject_id and the cohort filter columns, and move to a server database if concurrent writes are needed.

## Statistical method (Part 3)

The cohort is melanoma patients treated with miraclib, PBMC samples only, at time from treatment start = 0, with a recorded response. Each population is compared with a two-sided Mann-Whitney U test, and p-values are Holm-adjusted across the five populations (alpha = 0.05).

Mann-Whitney U is used instead of a t-test because relative frequencies are bounded percentages that may not be normally distributed, and the groups are small. Holm controls the family-wise error rate across the five populations and is uniformly more powerful than Bonferroni. Restricting to time = 0 keeps each subject to a single sample, so the observations are independent, and it compares baseline frequencies as a predictor of later response.

## Results

- **Significant populations after correction:** None. All five Holm-adjusted p-values are 1.0 (smallest raw p-value: monocytes, 0.21), and the medians differ by less than 1 percentage point in every population.
- **Interpretation and caveats:** Baseline (time = 0) relative frequencies do not distinguish responders (n = 331) from non-responders (n = 325), so they are not useful predictors of miraclib response on their own. This tests baseline frequencies only, not changes over time, and it does not rule out effects in other cell populations or timepoints.
- **Part 4 summary:** 656 baseline samples: 384 from prj1 and 272 from prj3. Subjects: 331 responders and 325 non-responders; 344 male and 312 female.
- **Mean B cell count (melanoma males, responders, time = 0):** 10206.15