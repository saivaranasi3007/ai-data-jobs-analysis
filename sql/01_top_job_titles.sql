-- Q1: What roles are most in demand right now?
-- Counting raw postings is the simplest proxy for demand.
SELECT
    job_title,
    COUNT(*) AS posting_count
FROM jobs
GROUP BY job_title
ORDER BY posting_count DESC
LIMIT 15;
