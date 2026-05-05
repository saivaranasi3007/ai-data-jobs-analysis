-- Q3: How much more do senior roles pay vs entry?
SELECT
    experience_level,
    ROUND(AVG(annual_salary_usd), 0) AS avg_salary,
    MIN(annual_salary_usd)            AS min_salary,
    MAX(annual_salary_usd)            AS max_salary,
    COUNT(*)                          AS n
FROM jobs
GROUP BY experience_level
ORDER BY avg_salary;
