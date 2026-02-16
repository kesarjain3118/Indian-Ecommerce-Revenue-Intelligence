-- ============================================================
-- SQL QUERY LIBRARY
-- Indian E-Commerce Analytics
-- ============================================================

-- Section 1: RFM ANALYSIS
-- ============================================================

-- 1.1 Calculate RFM Metrics for All Customers
SELECT 
    c.customer_id,
    c.city,
    c.state,
    c.acquisition_channel,
    DATEDIFF('2024-12-30', MAX(o.order_date)) AS recency_days,
    COUNT(DISTINCT o.order_id) AS frequency,
    SUM(oi.revenue) AS monetary_value
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id 
    AND o.order_status = 'Delivered'
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.city, c.state, c.acquisition_channel
ORDER BY monetary_value DESC;

-- 1.2 Customer Segmentation Based on RFM Scores
WITH rfm_calc AS (
    SELECT 
        customer_id,
        NTILE(5) OVER (ORDER BY recency_days ASC) AS R_score,
        NTILE(5) OVER (ORDER BY frequency DESC) AS F_score,
        NTILE(5) OVER (ORDER BY monetary_value DESC) AS M_score
    FROM (
        SELECT 
            c.customer_id,
            DATEDIFF('2024-12-30', MAX(o.order_date)) AS recency_days,
            COUNT(o.order_id) AS frequency,
            SUM(oi.revenue) AS monetary_value
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id 
            AND o.order_status = 'Delivered'
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY c.customer_id
    ) rfm
)
SELECT 
   customer_id,
    R_score,
    F_score,
    M_score,
    CASE 
        WHEN R_score >= 4 AND F_score >= 4 AND M_score >= 4 THEN 'Champions'
        WHEN F_score >= 4 THEN 'Loyal'
        WHEN R_score >= 4 AND F_score BETWEEN 2 AND 3 THEN 'Potential Loyalist'
        WHEN R_score >= 4 AND F_score = 1 THEN 'New Customers'
        WHEN R_score BETWEEN 2 AND 3 THEN 'Need Attention'
        WHEN R_score <= 2 AND F_score >= 3 THEN 'At Risk'
        WHEN R_score = 1 THEN 'Lost'
        ELSE 'Others'
    END AS segment
FROM rfm_calc;

-- ============================================================
-- Section 2: COHORT ANALYSIS
-- ============================================================

-- 2.1 Monthly Cohort Retention Rates
WITH cohort_data AS (
    SELECT 
        c.customer_id,
        DATE_FORMAT(c.signup_date, '%Y-%m') AS cohort_month,
        DATE_FORMAT(o.order_date, '%Y-%m') AS order_month,
        TIMESTAMPDIFF(MONTH, c.signup_date, o.order_date) AS cohort_index
    FROM customers c
    INNER JOIN orders o ON c.customer_id = o.customer_id
        AND o.order_status = 'Delivered'
),
cohort_size AS (
    SELECT 
        cohort_month,
        COUNT(DISTINCT customer_id) AS cohort_customers
    FROM cohort_data
    WHERE cohort_index = 0
    GROUP BY cohort_month
)
SELECT 
    cd.cohort_month,
    cd.cohort_index,
    COUNT(DISTINCT cd.customer_id) AS active_customers,
    cs.cohort_customers,
    (COUNT(DISTINCT cd.customer_id) * 100.0 / cs.cohort_customers) AS retention_rate
FROM cohort_data cd
INNER JOIN cohort_size cs ON cd.cohort_month = cs.cohort_month
GROUP BY cd.cohort_month, cd.cohort_index, cs.cohort_customers
ORDER BY cd.cohort_month, cd.cohort_index;

-- ============================================================
-- Section 3: CUSTOMER LIFETIME VALUE (CLV)
-- ============================================================

-- 3.1 Calculate Historical CLV for All Customers
SELECT 
    c.customer_id,
    c.acquisition_channel,
    c.state,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(oi.revenue) AS lifetime_value,
    AVG(oi.revenue) AS avg_order_value,
    DATEDIFF(MAX(o.order_date), MIN(o.order_date)) AS customer_lifetime_days
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
    AND o.order_status = 'Delivered'
INNER JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.acquisition_channel, c.state
ORDER BY lifetime_value DESC;

-- 3.2 CLV by Acquisition Channel
SELECT 
    c.acquisition_channel,
    COUNT(DISTINCT c.customer_id) AS total_customers,
    SUM(oi.revenue) AS total_revenue,
    AVG(oi.revenue) AS avg_clv,
    AVG(order_counts.order_count) AS avg_orders_per_customer
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
    AND o.order_status = 'Delivered'
INNER JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN (
    SELECT customer_id, COUNT(*) AS order_count
    FROM orders
    WHERE order_status = 'Delivered'
    GROUP BY customer_id
) order_counts ON c.customer_id = order_counts.customer_id
GROUP BY c.acquisition_channel
ORDER BY avg_clv DESC;

-- ============================================================
-- Section 4: PRODUCT AFFINITY
-- ============================================================

-- 4.1 Find Frequently Bought Together Products
SELECT 
    oi1.product_id AS product_1,
    oi2.product_id AS product_2,
    COUNT(DISTINCT oi1.order_id) AS times_bought_together,
    COUNT(DISTINCT oi1.order_id) * 100.0 / (
        SELECT COUNT(DISTINCT order_id) 
        FROM order_items
    ) AS support_pct
FROM order_items oi1
INNER JOIN order_items oi2 
    ON oi1.order_id = oi2.order_id 
    AND oi1.product_id < oi2.product_id
GROUP BY oi1.product_id, oi2.product_id
HAVING COUNT(DISTINCT oi1.order_id) >= 2
ORDER BY times_bought_together DESC
LIMIT 20;

-- 4.2 Most Popular Product Combinations (3+ items)
SELECT 
    o.order_id,
    GROUP_CONCAT(oi.product_id ORDER BY oi.product_id SEPARATOR ', ') AS product_combo,
    COUNT(oi.product_id) AS items_in_order,
    SUM(oi.revenue) AS order_revenue
FROM orders o
INNER JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'Delivered'
GROUP BY o.order_id
HAVING COUNT(oi.product_id) >= 3
ORDER BY items_in_order DESC, order_revenue DESC
LIMIT 20;

-- ============================================================
-- Section 5: SEASONAL TRENDS
-- ============================================================

-- 5.1 Monthly Revenue and Order Trends
SELECT 
    DATE_FORMAT(o.order_date, '%Y-%m') AS year_month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(oi.revenue) AS total_revenue,
    AVG(oi.revenue) AS avg_order_value,
    COUNT(DISTINCT o.customer_id) AS unique_customers
FROM orders o
INNER JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'Delivered'
GROUP BY year_month
ORDER BY year_month;

-- 5.2 Year-over-Year Comparison
SELECT 
    YEAR(o.order_date) AS year,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(oi.revenue) AS total_revenue,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    SUM(oi.revenue) / COUNT(DISTINCT o.order_id) AS avg_order_value
FROM orders o
INNER JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'Delivered'
GROUP BY year
ORDER BY year;

-- 5.3 Day of Week Analysis
SELECT 
    DAYNAME(o.order_date) AS day_of_week,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(oi.revenue) AS total_revenue,
    AVG(oi.revenue) AS avg_order_value
FROM orders o
INNER JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'Delivered'
GROUP BY day_of_week, DAYOFWEEK(o.order_date)
ORDER BY DAYOFWEEK(o.order_date);

-- ============================================================
-- Section 6: CHURN PREDICTION DATA PREP
-- ============================================================

-- 6.1 Customer Churn Status (90-day threshold)
SELECT 
    c.customer_id,
    c.acquisition_channel,
    c.state,
    c.age,
    DATEDIFF('2024-12-30', MAX(o.order_date)) AS days_since_last_order,
    COUNT(o.order_id) AS total_orders,
    SUM(oi.revenue) AS total_revenue,
    CASE 
        WHEN DATEDIFF('2024-12-30', MAX(o.order_date)) > 90 THEN 1
        ELSE 0
    END AS is_churned
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
    AND o.order_status = 'Delivered'
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.acquisition_channel, c.state, c.age
HAVING COUNT(o.order_id) > 0;

-- 6.2 At-Risk High-Value Customers
SELECT 
    c.customer_id,
    c.acquisition_channel,
    DATEDIFF('2024-12-30', MAX(o.order_date)) AS days_since_last_order,
    COUNT(o.order_id) AS total_orders,
    SUM(oi.revenue) AS lifetime_value
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
    AND o.order_status = 'Delivered'
INNER JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.acquisition_channel
HAVING 
    DATEDIFF('2024-12-30', MAX(o.order_date)) BETWEEN 60 AND 120
    AND SUM(oi.revenue) > 100000
ORDER BY lifetime_value DESC;

-- ============================================================
-- Section 7: COMMON ANALYTICS VIEWS
-- ============================================================

-- 7.1 Create Customer Summary View
CREATE OR REPLACE VIEW customer_summary AS
SELECT 
    c.customer_id,
    c.signup_date,
    c.city,
    c.state,
    c.acquisition_channel,
    c.age,
    c.gender,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(oi.revenue) AS lifetime_value,
    AVG(oi.revenue) AS avg_order_value,
    MAX(o.order_date) AS last_order_date,
    DATEDIFF('2024-12-30', MAX(o.order_date)) AS days_since_last_order
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
    AND o.order_status = 'Delivered'
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.signup_date, c.city, c.state, 
         c.acquisition_channel, c.age, c.gender;

-- 7.2 Create Monthly Performance View
CREATE OR REPLACE VIEW monthly_performance AS
SELECT 
    DATE_FORMAT(o.order_date, '%Y-%m') AS year_month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    SUM(oi.revenue) AS total_revenue,
    SUM(oi.revenue - oi.cost) AS gross_profit,
    AVG(oi.revenue) AS avg_order_value
FROM orders o
INNER JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'Delivered'
GROUP BY year_month
ORDER BY year_month;

-- ============================================================
-- END OF SQL QUERY LIBRARY
-- ============================================================
