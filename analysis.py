"""
End-to-end cleaning + EDA pipeline for the AI & Data jobs dataset.

Run as a script: `python analysis.py`
Outputs:
  data/ai_jobs_cleaned.csv         - cleaned table the dashboard reads
  data/skills_frequency.csv        - top skills + counts
  data/eda_findings.txt            - plain-text summary of headline findings
"""

from __future__ import annotations

import os
import re
from collections import Counter

import numpy as np
import pandas as pd

RAW_PATH = "data/ai_jobs_market_2025_2026.csv"
CLEAN_PATH = "data/ai_jobs_cleaned.csv"
SKILLS_PATH = "data/skills_frequency.csv"
FINDINGS_PATH = "data/eda_findings.txt"


# ---------------------------------------------------------------------------
# 1. Inspect
# ---------------------------------------------------------------------------
def inspect(df: pd.DataFrame) -> None:
    print("=" * 70)
    print("STEP 1 — INSPECTION")
    print("=" * 70)
    print(f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
    print("\nColumns + dtypes:")
    for col, dt in df.dtypes.items():
        print(f"  {col:<24} {dt}")
    print(f"\nFull-row duplicates: {df.duplicated().sum()}")
    print("\nMissing values per column:")
    miss = df.isna().sum()
    miss = miss[miss > 0]
    if miss.empty:
        print("  (none — every column is fully populated)")
    else:
        print(miss.to_string())
    print("\nFirst 5 rows:")
    print(df.head().to_string())
    print()


# ---------------------------------------------------------------------------
# 2. Clean
# ---------------------------------------------------------------------------
def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    The raw file is already remarkably tidy: no missing values, no dupes,
    25 canonical job titles (no "Sr." vs "Senior" variants to merge), salary
    already numeric. The cleaning here is therefore defensive rather than
    heavy — but each decision is documented so the logic is auditable.
    """
    print("=" * 70)
    print("STEP 2 — CLEANING")
    print("=" * 70)
    out = df.copy()
    notes: list[str] = []

    # Strip whitespace on every string column. Cheap insurance against
    # invisible trailing spaces breaking groupby.
    str_cols = out.select_dtypes(include="object").columns
    for c in str_cols:
        out[c] = out[c].astype(str).str.strip()
    notes.append(f"Stripped whitespace on {len(str_cols)} string columns.")

    # Drop exact duplicate rows. None expected, but kept for reproducibility
    # if the upstream file is ever refreshed with new appends.
    before = len(out)
    out = out.drop_duplicates().reset_index(drop=True)
    notes.append(f"Dropped {before - len(out)} duplicate rows.")

    # Sanity-check the salary triplet. annual_salary_usd is supposed to sit
    # inside [salary_min_usd, salary_max_usd], but in this dataset it doesn't
    # always. We DO NOT mutate — we just flag, because changing the source
    # number would silently distort the analysis.
    out_of_band = (
        (out["annual_salary_usd"] < out["salary_min_usd"])
        | (out["annual_salary_usd"] > out["salary_max_usd"])
    ).sum()
    notes.append(
        f"{out_of_band} rows have annual_salary_usd outside [min,max]. "
        "Left as-is; flagged for awareness."
    )

    # Cast booleans-as-int flags into real booleans for cleaner groupbys.
    for flag in ["is_senior", "is_remote_friendly", "is_llm_role"]:
        out[flag] = out[flag].astype(bool)
    notes.append("Converted is_senior / is_remote_friendly / is_llm_role to bool.")

    # Build a posting_date for time-based plots. Day defaults to 1 because
    # the dataset only records year + month.
    out["posting_date"] = pd.to_datetime(
        dict(year=out["posting_year"], month=out["posting_month"], day=1)
    )
    notes.append("Built posting_date from posting_year + posting_month (day=1).")

    # Country has a "Global" entry — that's a label for fully-distributed
    # postings, not a missing value, so we keep it.

    print("\n".join(f"  - {n}" for n in notes))
    print(f"\nCleaned shape: {out.shape[0]:,} rows x {out.shape[1]} columns")
    return out


# ---------------------------------------------------------------------------
# 3. EDA
# ---------------------------------------------------------------------------
def eda(df: pd.DataFrame) -> dict:
    """Return a dict of headline findings used later for README + dashboard."""
    print("=" * 70)
    print("STEP 4 — EDA")
    print("=" * 70)

    findings: dict = {}

    # Distributions
    salary = df["annual_salary_usd"]
    findings["salary_median"] = float(salary.median())
    findings["salary_mean"] = float(salary.mean())
    findings["salary_p10"] = float(salary.quantile(0.10))
    findings["salary_p90"] = float(salary.quantile(0.90))

    # Salary by experience
    exp_order = ["Entry (0-2 yrs)", "Mid (3-5 yrs)", "Senior (6-9 yrs)", "Lead (10+ yrs)"]
    by_exp = (
        df.groupby("experience_level")["annual_salary_usd"]
        .agg(["median", "mean", "count"])
        .reindex(exp_order)
    )
    findings["by_experience"] = by_exp

    # Entry vs Lead gap
    entry_med = by_exp.loc["Entry (0-2 yrs)", "median"]
    lead_med = by_exp.loc["Lead (10+ yrs)", "median"]
    findings["entry_to_lead_pct"] = float((lead_med - entry_med) / entry_med * 100)

    # Roles with the widest salary range
    role_range = (
        df.groupby("job_title")["annual_salary_usd"]
        .agg(p10=lambda s: s.quantile(0.10), p90=lambda s: s.quantile(0.90), n="count")
    )
    role_range["spread"] = role_range["p90"] - role_range["p10"]
    findings["widest_spread_roles"] = role_range.sort_values("spread", ascending=False).head(5)

    # Remote-friendliness by role
    remote_share = (
        df.assign(is_full_remote=(df["remote_work"] == "Fully Remote"))
        .groupby("job_title")["is_full_remote"]
        .mean()
        .sort_values(ascending=False)
    )
    findings["most_remote_roles"] = remote_share.head(5)
    findings["least_remote_roles"] = remote_share.tail(5)

    # LLM premium — does is_llm_role == True pay more, controlling for
    # experience? Simple within-group median comparison.
    llm_premium = (
        df.groupby(["experience_level", "is_llm_role"])["annual_salary_usd"]
        .median()
        .unstack()
    )
    llm_premium.columns = ["non_llm_median", "llm_median"]
    llm_premium["delta_pct"] = (
        (llm_premium["llm_median"] - llm_premium["non_llm_median"])
        / llm_premium["non_llm_median"]
        * 100
    )
    findings["llm_premium_by_exp"] = llm_premium.reindex(exp_order)

    # Salary by remote arrangement
    findings["by_remote"] = (
        df.groupby("remote_work")["annual_salary_usd"]
        .agg(["median", "mean", "count"])
        .sort_values("median", ascending=False)
    )

    # Correlation: years_of_experience vs salary
    findings["corr_years_salary"] = float(
        df["years_of_experience"].corr(df["annual_salary_usd"])
    )

    # Demand vs salary — do the highest-paying roles also show high demand?
    role_summary = (
        df.groupby("job_title")
        .agg(median_salary=("annual_salary_usd", "median"),
             median_demand=("demand_score", "median"),
             n=("job_id", "count"))
    )
    findings["corr_demand_salary"] = float(
        role_summary["median_salary"].corr(role_summary["median_demand"])
    )

    # Top countries by share + median salary
    findings["by_country"] = (
        df.groupby("country")
        .agg(postings=("job_id", "count"),
             median_salary=("annual_salary_usd", "median"))
        .sort_values("postings", ascending=False)
    )

    # Print key numbers so a reader of stdout can sanity-check
    print(f"\nMedian salary overall: ${findings['salary_median']:,.0f}")
    print(f"P10 / P90 salary: ${findings['salary_p10']:,.0f} / ${findings['salary_p90']:,.0f}")
    print(f"Entry median:  ${entry_med:,.0f}")
    print(f"Lead median:   ${lead_med:,.0f}  ({findings['entry_to_lead_pct']:.1f}% above entry)")
    print(f"corr(years_of_exp, salary) = {findings['corr_years_salary']:.3f}")
    print(f"corr(role-median demand, role-median salary) = {findings['corr_demand_salary']:.3f}")
    print("\nLLM premium by experience level:")
    print(findings["llm_premium_by_exp"].round(1).to_string())
    print("\nMost-remote roles (share Fully Remote):")
    print(findings["most_remote_roles"].round(2).to_string())
    print("\nLeast-remote roles:")
    print(findings["least_remote_roles"].round(2).to_string())
    print("\nWidest salary spreads (P90 - P10):")
    print(findings["widest_spread_roles"].round(0).to_string())

    return findings


# ---------------------------------------------------------------------------
# 5. Skill extraction
# ---------------------------------------------------------------------------
def extract_skills(df: pd.DataFrame) -> pd.DataFrame:
    """Pipe-separated skills column. Tokenise, count, return top 30."""
    print("=" * 70)
    print("STEP 5 — SKILL EXTRACTION")
    print("=" * 70)
    if "required_skills" not in df.columns:
        print("  No skills column — skipping.")
        return pd.DataFrame(columns=["skill", "count"])

    counter: Counter = Counter()
    for raw in df["required_skills"].dropna():
        for token in str(raw).split("|"):
            t = token.strip()
            if t:
                counter[t] += 1

    skills = (
        pd.DataFrame(counter.most_common(), columns=["skill", "count"])
        .head(30)
        .reset_index(drop=True)
    )
    print(f"  Unique skills found: {len(counter)}")
    print(f"  Top 10:")
    print(skills.head(10).to_string(index=False))
    return skills


def skill_salary_correlation(df: pd.DataFrame, skills: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    For each top skill: median salary of postings that list it
    vs median salary of postings that don't. Useful for the dashboard.
    """
    if skills.empty:
        return pd.DataFrame()
    overall_median = df["annual_salary_usd"].median()
    rows = []
    for skill in skills["skill"].head(top_n):
        # Match the skill as a full pipe-delimited token to avoid e.g.
        # "SQL" matching "PostgreSQL".
        pattern = rf"(?:^|\|){re.escape(skill)}(?:\||$)"
        mask = df["required_skills"].fillna("").str.contains(pattern, regex=True)
        with_skill = df.loc[mask, "annual_salary_usd"]
        if len(with_skill) < 10:
            continue
        rows.append({
            "skill": skill,
            "n_postings": int(mask.sum()),
            "median_salary": float(with_skill.median()),
            "delta_vs_overall_pct": float((with_skill.median() - overall_median) / overall_median * 100),
        })
    return pd.DataFrame(rows).sort_values("median_salary", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def write_findings_file(findings: dict, skills: pd.DataFrame, skill_corr: pd.DataFrame) -> None:
    lines = ["AI & DATA JOBS — EDA FINDINGS", "=" * 40, ""]
    lines.append(f"Median annual salary (USD): ${findings['salary_median']:,.0f}")
    lines.append(f"P10 / P90: ${findings['salary_p10']:,.0f} / ${findings['salary_p90']:,.0f}")
    lines.append(f"Entry → Lead median jump: {findings['entry_to_lead_pct']:.1f}%")
    lines.append(f"corr(years_of_experience, salary): {findings['corr_years_salary']:.3f}")
    lines.append(f"corr(role demand, role salary): {findings['corr_demand_salary']:.3f}")
    lines.append("")
    lines.append("By experience level:")
    lines.append(findings["by_experience"].round(0).to_string())
    lines.append("")
    lines.append("LLM premium (within experience level, % above non-LLM):")
    lines.append(findings["llm_premium_by_exp"].round(1).to_string())
    lines.append("")
    lines.append("By remote arrangement:")
    lines.append(findings["by_remote"].round(0).to_string())
    lines.append("")
    lines.append("Top countries by posting count:")
    lines.append(findings["by_country"].round(0).to_string())
    lines.append("")
    lines.append("Top 15 skills:")
    lines.append(skills.head(15).to_string(index=False))
    lines.append("")
    if not skill_corr.empty:
        lines.append("Highest-paying skills (median salary among postings that list them):")
        lines.append(skill_corr.head(10).round(1).to_string(index=False))

    with open(FINDINGS_PATH, "w") as fh:
        fh.write("\n".join(lines))
    print(f"\nWrote {FINDINGS_PATH}")


def main() -> None:
    if not os.path.exists(RAW_PATH):
        raise SystemExit(f"Missing input file: {RAW_PATH}")

    df_raw = pd.read_csv(RAW_PATH)
    inspect(df_raw)

    df = clean(df_raw)
    df.to_csv(CLEAN_PATH, index=False)
    print(f"\nWrote {CLEAN_PATH}")

    findings = eda(df)
    skills = extract_skills(df)
    skills.to_csv(SKILLS_PATH, index=False)
    print(f"\nWrote {SKILLS_PATH}")

    skill_corr = skill_salary_correlation(df, skills)
    if not skill_corr.empty:
        skill_corr.to_csv("data/skills_salary.csv", index=False)
        print("Wrote data/skills_salary.csv")

    write_findings_file(findings, skills, skill_corr)


if __name__ == "__main__":
    main()
