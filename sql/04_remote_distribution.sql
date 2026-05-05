-- Q4: How is the work split across Fully Remote / Hybrid / On-site?
SELECT
    remote_work,
    COUNT(*)                                                AS postings,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM jobs), 1) AS pct_of_total,
    ROUND(AVG(annual_salary_usd), 0)                         AS avg_salary
FROM jobs
GROUP BY remote_work
ORDER BY postings DESC;
