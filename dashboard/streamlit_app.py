"""
Streamlit dashboard for the AI & Data jobs analysis.

Run from the project root:
    streamlit run dashboard/streamlit_app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Make sibling modules importable when Streamlit launches this file directly.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from database import build_database, run_query  # noqa: E402

CLEAN_PATH = "data/ai_jobs_cleaned.csv"
SKILLS_PATH = "data/skills_frequency.csv"
SKILLS_SALARY_PATH = "data/skills_salary.csv"

EXP_ORDER = ["Entry (0-2 yrs)", "Mid (3-5 yrs)", "Senior (6-9 yrs)", "Lead (10+ yrs)"]
REMOTE_ORDER = ["Fully Remote", "Hybrid", "On-site"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not os.path.exists(CLEAN_PATH):
        st.error(
            "Cleaned data not found. Run `python analysis.py` from the project "
            "root before starting the dashboard."
        )
        st.stop()
    df = pd.read_csv(CLEAN_PATH, parse_dates=["posting_date"])
    skills = pd.read_csv(SKILLS_PATH) if os.path.exists(SKILLS_PATH) else pd.DataFrame()
    skill_corr = (
        pd.read_csv(SKILLS_SALARY_PATH) if os.path.exists(SKILLS_SALARY_PATH) else pd.DataFrame()
    )
    return df, skills, skill_corr


def apply_filters(df: pd.DataFrame, exp: list, remote: list, edu: list) -> pd.DataFrame:
    """The sidebar drives every chart in the page."""
    out = df
    if exp:
        out = out[out["experience_level"].isin(exp)]
    if remote:
        out = out[out["remote_work"].isin(remote)]
    if edu:
        out = out[out["education_required"].isin(edu)]
    return out


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------
def usd(value: float) -> str:
    return f"${value:,.0f}"


def empty_warning(filtered: pd.DataFrame) -> bool:
    if filtered.empty:
        st.warning("No postings match the current filters. Loosen the sidebar to see charts.")
        return True
    return False


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
def section_market_snapshot(df: pd.DataFrame) -> None:
    st.subheader("1. Market Snapshot")
    st.caption("How big is the dataset, where is the work, and what shape do postings come in?")

    if empty_warning(df):
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Postings", f"{len(df):,}")
    c2.metric("Distinct roles", df["job_title"].nunique())
    c3.metric("Countries", df["country"].nunique())
    date_min = df["posting_date"].min().strftime("%b %Y")
    date_max = df["posting_date"].max().strftime("%b %Y")
    c4.metric("Date range", f"{date_min} → {date_max}")

    left, right = st.columns([1.2, 1])

    with left:
        top_titles = (
            df["job_title"].value_counts().head(10).rename_axis("job_title").reset_index(name="postings")
        )
        fig = px.bar(
            top_titles.sort_values("postings"),
            x="postings",
            y="job_title",
            orientation="h",
            text="postings",
        )
        fig.update_layout(
            title="Top 10 job titles by posting count",
            xaxis_title="Postings",
            yaxis_title="",
            margin=dict(l=10, r=10, t=50, b=10),
            height=420,
        )
        st.plotly_chart(fig, width="stretch")

    with right:
        # The source CSV doesn't carry an employment_type column. Industry mix
        # is the closest signal of "what kind of work is being posted", so
        # the donut shows that instead.
        ind = (
            df["industry"].value_counts().rename_axis("industry").reset_index(name="postings")
        )
        fig = px.pie(ind, names="industry", values="postings", hole=0.55)
        fig.update_layout(
            title="Postings by industry",
            margin=dict(l=10, r=10, t=50, b=10),
            height=420,
            legend=dict(font=dict(size=11)),
        )
        fig.update_traces(textinfo="percent")
        st.plotly_chart(fig, width="stretch")


def section_salary_intelligence(df: pd.DataFrame) -> None:
    st.subheader("2. Salary Intelligence")
    st.caption(
        "Annual salaries are reported in USD across all countries. Salary is dense — every "
        "posting has one — so unlike many public job datasets there are no gaps to apologise for."
    )

    if empty_warning(df):
        return

    # Top 15 by avg salary
    top_pay = (
        df.groupby("job_title")["annual_salary_usd"]
        .agg(avg="mean", n="count")
        .sort_values("avg", ascending=False)
        .head(15)
        .reset_index()
    )
    fig = px.bar(
        top_pay.sort_values("avg"),
        x="avg",
        y="job_title",
        orientation="h",
        text=top_pay.sort_values("avg")["avg"].map(lambda v: f"${v/1000:.0f}k"),
        hover_data={"n": True, "avg": ":.0f"},
    )
    fig.update_layout(
        title="Top 15 highest-paying roles (mean annual salary, USD)",
        xaxis_title="Average salary (USD)",
        yaxis_title="",
        margin=dict(l=10, r=10, t=50, b=10),
        height=520,
    )
    st.plotly_chart(fig, width="stretch")

    # Box plot by experience level
    fig = px.box(
        df,
        x="experience_level",
        y="annual_salary_usd",
        category_orders={"experience_level": EXP_ORDER},
        points=False,
    )
    fig.update_layout(
        title="Salary distribution by experience level",
        xaxis_title="",
        yaxis_title="Annual salary (USD)",
        margin=dict(l=10, r=10, t=50, b=10),
        height=420,
    )
    st.plotly_chart(fig, width="stretch")

    # Salary vs remote arrangement
    by_remote = (
        df.groupby("remote_work")["annual_salary_usd"]
        .agg(median="median", mean="mean", n="count")
        .reindex([r for r in REMOTE_ORDER if r in df["remote_work"].unique()])
        .reset_index()
    )
    fig = px.bar(
        by_remote,
        x="remote_work",
        y="median",
        text=by_remote["median"].map(lambda v: f"${v/1000:.0f}k"),
        hover_data={"n": True, "mean": ":.0f"},
    )
    fig.update_layout(
        title="Median salary by remote arrangement",
        xaxis_title="",
        yaxis_title="Median annual salary (USD)",
        margin=dict(l=10, r=10, t=50, b=10),
        height=380,
    )
    st.plotly_chart(fig, width="stretch")


def section_remote_trends(df: pd.DataFrame) -> None:
    st.subheader("3. Remote Work Trends")
    st.caption("Remote, hybrid, on-site — and which roles tilt which way.")

    if empty_warning(df):
        return

    overall = (
        df["remote_work"].value_counts().rename_axis("remote_work").reset_index(name="postings")
    )
    overall["pct"] = overall["postings"] / overall["postings"].sum() * 100

    fig = px.bar(
        overall,
        x="remote_work",
        y="pct",
        text=overall["pct"].map(lambda v: f"{v:.1f}%"),
        category_orders={"remote_work": REMOTE_ORDER},
    )
    fig.update_layout(
        title="Overall split: Fully Remote vs Hybrid vs On-site",
        xaxis_title="",
        yaxis_title="% of postings",
        margin=dict(l=10, r=10, t=50, b=10),
        height=360,
    )
    st.plotly_chart(fig, width="stretch")

    # By role: stacked share. Use job_category to keep the chart readable.
    cat_remote = (
        df.groupby(["job_category", "remote_work"])
        .size()
        .rename("postings")
        .reset_index()
    )
    cat_totals = cat_remote.groupby("job_category")["postings"].transform("sum")
    cat_remote["pct"] = cat_remote["postings"] / cat_totals * 100

    fig = px.bar(
        cat_remote,
        x="pct",
        y="job_category",
        color="remote_work",
        orientation="h",
        category_orders={"remote_work": REMOTE_ORDER},
    )
    fig.update_layout(
        title="Remote mix by job category (% of postings in each row)",
        xaxis_title="% of postings",
        yaxis_title="",
        margin=dict(l=10, r=10, t=50, b=10),
        height=460,
        barmode="stack",
    )
    st.plotly_chart(fig, width="stretch")

    # Most/least remote-friendly individual titles
    role_remote = (
        df.assign(is_full_remote=(df["remote_work"] == "Fully Remote"))
        .groupby("job_title")
        .agg(pct_remote=("is_full_remote", "mean"), n=("job_id", "count"))
        .reset_index()
    )
    role_remote = role_remote[role_remote["n"] >= 20]  # avoid noise
    role_remote["pct_remote"] *= 100
    top10 = role_remote.sort_values("pct_remote", ascending=False).head(10)

    fig = px.bar(
        top10.sort_values("pct_remote"),
        x="pct_remote",
        y="job_title",
        orientation="h",
        text=top10.sort_values("pct_remote")["pct_remote"].map(lambda v: f"{v:.0f}%"),
    )
    fig.update_layout(
        title="Most remote-friendly job titles (≥ 20 postings)",
        xaxis_title="% Fully Remote",
        yaxis_title="",
        margin=dict(l=10, r=10, t=50, b=10),
        height=420,
    )
    st.plotly_chart(fig, width="stretch")


def section_skills(df: pd.DataFrame, skills: pd.DataFrame, skill_corr: pd.DataFrame) -> None:
    st.subheader("4. Skills in Demand")

    if skills.empty:
        st.info("No skills data available — the cleaning step didn't produce a skills file.")
        return

    st.caption(
        "Skills are extracted from the pipe-separated `required_skills` field. The sidebar "
        "filter does not narrow this section because skills are computed once over the full corpus."
    )

    fig = px.bar(
        skills.sort_values("count"),
        x="count",
        y="skill",
        orientation="h",
        text="count",
    )
    fig.update_layout(
        title=f"Top {len(skills)} skills by mention count",
        xaxis_title="Postings mentioning the skill",
        yaxis_title="",
        margin=dict(l=10, r=10, t=50, b=10),
        height=720,
    )
    st.plotly_chart(fig, width="stretch")

    if not skill_corr.empty:
        fig = px.bar(
            skill_corr.sort_values("median_salary"),
            x="median_salary",
            y="skill",
            orientation="h",
            text=skill_corr.sort_values("median_salary")["median_salary"].map(
                lambda v: f"${v/1000:.0f}k"
            ),
            hover_data={"n_postings": True, "delta_vs_overall_pct": ":.1f"},
        )
        fig.update_layout(
            title="Median salary among postings that list each skill",
            xaxis_title="Median salary (USD)",
            yaxis_title="",
            margin=dict(l=10, r=10, t=50, b=10),
            height=600,
        )
        st.plotly_chart(fig, width="stretch")


def section_role_explorer(df: pd.DataFrame) -> None:
    st.subheader("5. Role Explorer")
    st.caption("Pick a role; everything below recomputes for it alone.")

    if empty_warning(df):
        return

    role = st.selectbox(
        "Role",
        sorted(df["job_title"].unique()),
        index=0,
    )
    sub = df[df["job_title"] == role]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Postings", f"{len(sub):,}")
    c2.metric("Avg salary", usd(sub["annual_salary_usd"].mean()))
    c3.metric("Median salary", usd(sub["annual_salary_usd"].median()))
    pct_remote = (sub["remote_work"] == "Fully Remote").mean() * 100
    c4.metric("Fully remote", f"{pct_remote:.0f}%")

    left, right = st.columns(2)
    with left:
        exp_dist = (
            sub["experience_level"]
            .value_counts()
            .rename_axis("experience_level")
            .reset_index(name="postings")
        )
        exp_dist["experience_level"] = pd.Categorical(
            exp_dist["experience_level"], EXP_ORDER, ordered=True
        )
        exp_dist = exp_dist.sort_values("experience_level")
        fig = px.bar(exp_dist, x="experience_level", y="postings", text="postings")
        fig.update_layout(
            title="Experience-level mix",
            xaxis_title="",
            yaxis_title="",
            margin=dict(l=10, r=10, t=50, b=10),
            height=380,
        )
        st.plotly_chart(fig, width="stretch")

    with right:
        top_industries = (
            sub.groupby(["industry", "company_size"])
            .size()
            .rename("postings")
            .reset_index()
            .sort_values("postings", ascending=False)
            .head(10)
        )
        top_industries["label"] = top_industries["industry"] + " · " + top_industries["company_size"]
        fig = px.bar(
            top_industries.sort_values("postings"),
            x="postings",
            y="label",
            orientation="h",
            text="postings",
        )
        fig.update_layout(
            title="Top hiring industry × company size",
            xaxis_title="",
            yaxis_title="",
            margin=dict(l=10, r=10, t=50, b=10),
            height=380,
        )
        st.plotly_chart(fig, width="stretch")

    top_locations = (
        sub.groupby(["city", "country"])
        .size()
        .rename("postings")
        .reset_index()
        .sort_values("postings", ascending=False)
        .head(10)
    )
    top_locations["label"] = top_locations["city"] + ", " + top_locations["country"]
    fig = px.bar(
        top_locations.sort_values("postings"),
        x="postings",
        y="label",
        orientation="h",
        text="postings",
    )
    fig.update_layout(
        title="Top locations for this role",
        xaxis_title="",
        yaxis_title="",
        margin=dict(l=10, r=10, t=50, b=10),
        height=420,
    )
    st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="AI & Data Jobs Market — 2025-2026",
        layout="wide",
    )

    df, skills, skill_corr = load_data()

    st.title("AI & Data Jobs Market — 2025-2026")
    st.write(
        "1,500 AI and data postings from the 2025-2026 Kaggle dataset, cleaned and queried "
        "end-to-end. Pick filters in the sidebar to narrow every chart on the page."
    )

    # Sidebar filters
    st.sidebar.header("Filters")
    exp = st.sidebar.multiselect(
        "Experience level",
        options=[e for e in EXP_ORDER if e in df["experience_level"].unique()],
        default=[],
        help="Leave empty to include all levels.",
    )
    remote = st.sidebar.multiselect(
        "Remote arrangement",
        options=[r for r in REMOTE_ORDER if r in df["remote_work"].unique()],
        default=[],
    )
    edu = st.sidebar.multiselect(
        "Education required",
        options=sorted(df["education_required"].unique()),
        default=[],
    )

    filtered = apply_filters(df, exp, remote, edu)
    st.sidebar.caption(f"Showing **{len(filtered):,}** of {len(df):,} postings.")
    st.sidebar.divider()
    st.sidebar.markdown(
        "**Sections**\n\n"
        "1. Market Snapshot\n"
        "2. Salary Intelligence\n"
        "3. Remote Work Trends\n"
        "4. Skills in Demand\n"
        "5. Role Explorer"
    )

    section_market_snapshot(filtered)
    st.divider()
    section_salary_intelligence(filtered)
    st.divider()
    section_remote_trends(filtered)
    st.divider()
    section_skills(filtered, skills, skill_corr)
    st.divider()
    section_role_explorer(filtered)


if __name__ == "__main__":
    main()
