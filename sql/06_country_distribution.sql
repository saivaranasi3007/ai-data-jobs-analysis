-- Q6: Where in the world are these jobs?
-- 'Global' here is a real value in the source data — it tags fully-distributed
-- postings, not a missing country.
SELECT
    country,
    COUNT(*)                          AS postings,
    ROUND(AVG(annual_salary_usd), 0)  AS avg_salary,
    ROUND(
        100.0 * SUM(CASE WHEN remote_work = 'Fully Remote' THEN 1 ELSE 0 END)
              / COUNT(*),
        1
    ) AS pct_fully_remote
FROM jobs
GROUP BY country
ORDER BY postings DESC;
