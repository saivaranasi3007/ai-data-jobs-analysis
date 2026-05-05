# AI & Data Jobs Market Analysis (2025-2026)

I wanted to know what the AI and data job market actually pays right now — not the breathless headlines, but the real numbers. What roles show up most often, what they pay across experience levels, how much of the work is genuinely remote, and which skills keep appearing in postings. So I took the Kaggle *AI Jobs Market 2025-2026 | Salaries* dataset and ran it end-to-end: inspect → clean → SQL → EDA → dashboard.

## Dataset

- **Source:** Kaggle, *AI Jobs Market 2025-2026 | Salaries*
- **Size:** 1,500 postings, 25 columns
- **Time range:** January 2025 – March 2026 (the data only records year + month, not full dates)
- **What's in it:** `job_title`, `job_category`, `experience_level` (four brackets) plus raw `years_of_experience`, `education_required`, `annual_salary_usd` + `salary_min_usd` / `salary_max_usd`, `city`, `country`, `remote_work` (Fully Remote / Hybrid / On-site), `company_size` (Startup 1-50 → Big Tech FAANG+), `industry`, pipe-separated `required_skills`, and a few engineered fields (`demand_score`, `ai_salary_premium_pct`, `is_llm_role`).

### What this dataset is not

Worth being upfront about. The file is unusually tidy: zero missing values, zero duplicate rows, exactly 25 canonical job titles with no spelling variants, and salary populated on every row. Real scraped job-board data never looks like this — this is almost certainly a curated or partly synthetic dataset, not raw postings. So everything here should be read as *"what a clean, opinionated snapshot of the AI labour market looks like"*, not as a ground-truth claim about hiring activity.

A few specific limits I worked around rather than hid:

- 288 of 1,500 rows (19%) have `annual_salary_usd` outside the `[salary_min_usd, salary_max_usd]` band that's reported on the same row. I left them untouched — silently re-clipping the number would distort the analysis — but flagged the inconsistency in the cleaning step.
- 58% of postings fall in January–March 2026. Any "trend over time" claim would be unreliable, so the dashboard treats the data as a snapshot rather than a time series.
- There's no company-*name* column, only `company_size` + `industry`. So the "top hiring companies" question became "top hiring industry × company-size combinations".
- There's no `employment_type` field. The SQL pack reuses that slot for an LLM-premium query the data actually supports.

## Key findings

1. Median total comp across all 1,500 roles is **$180,000**, with P10 / P90 at **$121k / $297k**. Even entry-level AI work in this dataset clears six figures — the bottom decile of the market starts above what general software roles paid in the same Kaggle release.
2. Stepping from Entry (0-2 yrs) to Lead (10+ yrs) raises median salary from **$145k to $238k — a 64% jump** — but most of that gain happens in the move from Mid to Senior ($176k → $214k), not Senior to Lead. The first six years compound faster than the next five.
3. Raw `years_of_experience` barely correlates with salary at all (Pearson **r = 0.08**). The bucketed `experience_level` field carries almost all the signal — meaning pay is set by tier, and adding a year inside the same tier is worth essentially nothing.
4. LLM-tagged roles command a real premium, but not a flat one. It's +7-10% at Entry/Mid, peaks at **+13.2% for Senior LLM Engineers** (~$227k median vs $200k for Senior non-LLM peers), then softens again at Lead. The market pays loudest to people who can build LLM systems but aren't yet running orgs.
5. Hybrid is the dominant arrangement at **45.7%** of postings; Fully Remote is only 29.7% — less than On-site (24.6%) plus a sliver of Hybrid combined. ML Engineer is the most remote-friendly title at 44% Fully Remote; AI Infrastructure Engineer is the least at 13%. Physical machines still anchor people to a building.

## Dashboard sections

The dashboard runs in Streamlit and is organised into five sections, each answering one question:

1. **Market Snapshot** — how big is the market and what's the headline mix of roles and industries?
2. **Salary Intelligence** — what do roles pay, and how does pay shift with experience and remote arrangement?
3. **Remote Work Trends** — how is the work split between Fully Remote / Hybrid / On-site, and which roles tilt which way?
4. **Skills in Demand** — which skills appear most often, and which ones correlate with higher pay?
5. **Role Explorer** — drill into any single job title and see its salary, experience mix, top locations, and hiring industries.

A sidebar with experience level, remote arrangement, and education filters narrows every chart on the page at once.

## Tech stack

- Python 3.11
- pandas, NumPy
- SQLite (stdlib `sqlite3`)
- Streamlit
- Plotly Express

## How to run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1. inspect, clean, run EDA, extract skills, write outputs into data/
python analysis.py

# 2. (optional) build the SQLite database and dump every query to stdout
python database.py

# 3. launch the dashboard
streamlit run dashboard/streamlit_app.py
```

## Project structure

```
.
├── analysis.py                  # cleaning + EDA + skill extraction pipeline
├── database.py                  # SQLite loader + query runner
├── requirements.txt
├── data/
│   ├── ai_jobs_market_2025_2026.csv   # raw input
│   ├── ai_jobs_cleaned.csv            # produced by analysis.py
│   ├── skills_frequency.csv           # top 30 skills + counts
│   ├── skills_salary.csv              # median salary by skill
│   ├── eda_findings.txt               # plain-text EDA summary
│   └── jobs.db                        # SQLite database (built on demand)
├── sql/
│   ├── 01_top_job_titles.sql
│   ├── 02_salary_by_title.sql
│   ├── 03_salary_by_experience.sql
│   ├── 04_remote_distribution.sql
│   ├── 05_top_industries.sql          # substitutes for "top companies"
│   ├── 06_country_distribution.sql
│   ├── 07_salary_by_company_size.sql
│   └── 08_llm_role_premium.sql        # substitutes for "employment types"
└── dashboard/
    └── streamlit_app.py
```

## What I learned

The biggest surprise wasn't a number, it was the dataset itself. Spending the first hour just *reading* the data — column counts, value distributions, internal consistency — saved me from writing a cleaning section full of theatre. Real scraped job postings would have had me reconciling "Sr. ML Eng" with "Senior Machine Learning Engineer" for a day; here I got to skip that and spend the time on real questions, but I had to be much more careful about overclaiming.

The years-vs-tier finding was the analytical surprise — that raw `years_of_experience` is almost uncorrelated with salary while the bucketed tier explains nearly all of it. It's probably an artefact of how the dataset is constructed, but it's a useful general reminder that bucketed features can quietly hide variance the eye expects to see, and that "compute every correlation" before trusting the obvious explanatory variable is rarely wasted effort.

If I were doing this again with a real source, two things would be worth the time: a free-text job description column so skill extraction means more than counting an enumerated list (right now "Python" is 942 mentions in clean tokens, which is tidy but tells me nothing about *which* Python work), and a true posting date so the year-and-month pile-up around early 2026 doesn't kill any chance of a real time-series view.
