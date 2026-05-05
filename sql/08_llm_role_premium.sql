-- Q8: Is there an "LLM premium"?
-- The source CSV doesn't carry an employment_type column (full-time / contract /
-- part-time), so instead of a low-value full-time-vs-contract count this query
-- answers a question that's actually present in the data: are LLM-tagged roles
-- paid differently from the rest, holding experience level fixed?
SELECT
    experience_level,
    SUM(CASE WHEN is_llm_role = 1 THEN 1 ELSE 0 END) AS llm_postings,
    SUM(CASE WHEN is_llm_role = 0 THEN 1 ELSE 0 END) AS non_llm_postings,
    ROUND(AVG(CASE WHEN is_llm_role = 1 THEN annual_salary_usd END), 0) AS llm_avg_salary,
    ROUND(AVG(CASE WHEN is_llm_role = 0 THEN annual_salary_usd END), 0) AS non_llm_avg_salary
FROM jobs
GROUP BY experience_level
ORDER BY
    CASE experience_level
        WHEN 'Entry (0-2 yrs)'   THEN 1
        WHEN 'Mid (3-5 yrs)'     THEN 2
        WHEN 'Senior (6-9 yrs)'  THEN 3
        WHEN 'Lead (10+ yrs)'    THEN 4
        ELSE 5
    END;
