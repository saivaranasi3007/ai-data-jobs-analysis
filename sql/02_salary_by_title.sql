-- Q2: Average and median salary by role.
-- SQLite has no native median, so we compute it in Python and only do
-- the AVG / MIN / MAX / COUNT here. The dashboard joins the median in.
SELECT
    job_title,
    ROUND(AVG(annual_salary_usd), 0) AS avg_salary,
    MIN(annual_salary_usd)            AS min_salary,
    MAX(annual_salary_usd)            AS max_salary,
    COUNT(*)                          AS n
FROM jobs
GROUP BY job_title
ORDER BY avg_salary DESC;
