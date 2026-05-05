-- Q7: Do bigger companies pay more?
SELECT
    company_size,
    COUNT(*) AS postings,
    ROUND(AVG(annual_salary_usd), 0) AS avg_salary,
    MIN(annual_salary_usd) AS min_salary,
    MAX(annual_salary_usd) AS max_salary
FROM jobs
GROUP BY company_size
ORDER BY avg_salary DESC;
