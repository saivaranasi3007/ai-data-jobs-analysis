-- Q5: Where is the hiring concentrated?
-- The source CSV doesn't include a company name, only company_size + industry,
-- so this answers "which industries and company sizes are hiring most" instead
-- of "top hiring companies". The substitution is documented in the README.
SELECT
    industry,
    company_size,
    COUNT(*) AS postings,
    ROUND(AVG(annual_salary_usd), 0) AS avg_salary
FROM jobs
GROUP BY industry, company_size
ORDER BY postings DESC
LIMIT 25;
