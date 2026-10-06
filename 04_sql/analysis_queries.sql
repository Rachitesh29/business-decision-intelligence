-- ============================================================
-- BUSINESS DECISION INTELLIGENCE
-- SQL ANALYTICAL QUERIES
-- ============================================================


-- ============================================================
-- 1. ORDER STATUS DISTRIBUTION
-- ============================================================

SELECT
    order_status,
    COUNT(*) AS order_count
FROM orders
GROUP BY order_status
ORDER BY order_count DESC;


-- ============================================================
-- 2. TOP STATES BY ORDER COUNT
-- ============================================================

SELECT
    c.customer_state,
    COUNT(DISTINCT o.order_id) AS order_count
FROM orders AS o
JOIN customers AS c
    ON o.customer_id = c.customer_id
GROUP BY c.customer_state
ORDER BY order_count DESC
LIMIT 10;


-- ============================================================
-- 3. TOP PRODUCT CATEGORIES BY SALES
-- ============================================================

SELECT
    COALESCE(
        ct.product_category_name_english,
        p.product_category_name
    ) AS category,
    ROUND(SUM(oi.price), 2) AS sales_value
FROM order_items AS oi
JOIN products AS p
    ON oi.product_id = p.product_id
LEFT JOIN category_translation AS ct
    ON p.product_category_name = ct.product_category_name
GROUP BY category
ORDER BY sales_value DESC
LIMIT 10;


-- ============================================================
-- 4. TOP PRODUCT CATEGORIES BY UNITS SOLD
-- ============================================================

SELECT
    COALESCE(
        ct.product_category_name_english,
        p.product_category_name
    ) AS category,
    COUNT(*) AS items_sold
FROM order_items AS oi
JOIN products AS p
    ON oi.product_id = p.product_id
LEFT JOIN category_translation AS ct
    ON p.product_category_name = ct.product_category_name
GROUP BY category
ORDER BY items_sold DESC
LIMIT 10;


-- ============================================================
-- 5. MONTHLY ORDER VOLUME
-- ============================================================

SELECT
    strftime('%Y-%m', order_purchase_timestamp) AS month,
    COUNT(*) AS order_count
FROM orders
GROUP BY month
ORDER BY month;


-- ============================================================
-- 6. MONTHLY PAYMENT VALUE
-- ============================================================

SELECT
    strftime('%Y-%m', o.order_purchase_timestamp) AS month,
    ROUND(SUM(p.payment_value), 2) AS payment_value
FROM orders AS o
JOIN payments AS p
    ON o.order_id = p.order_id
GROUP BY month
ORDER BY month;


-- ============================================================
-- 7. AVERAGE ORDER VALUE
-- ============================================================

SELECT
    ROUND(
        SUM(payment_value) / COUNT(DISTINCT order_id),
        2
    ) AS average_order_value
FROM payments;


-- ============================================================
-- 8. CUSTOMER ORDER FREQUENCY
-- ============================================================

SELECT
    c.customer_unique_id,
    COUNT(DISTINCT o.order_id) AS order_count
FROM orders AS o
JOIN customers AS c
    ON o.customer_id = c.customer_id
GROUP BY c.customer_unique_id
ORDER BY order_count DESC;


-- ============================================================
-- 9. REPEAT CUSTOMER SUMMARY
-- ============================================================

WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS order_count
    FROM orders AS o
    JOIN customers AS c
        ON o.customer_id = c.customer_id
    GROUP BY c.customer_unique_id
)

SELECT
    CASE
        WHEN order_count = 1 THEN 'One-time'
        ELSE 'Repeat'
    END AS customer_type,
    COUNT(*) AS customers
FROM customer_orders
GROUP BY customer_type;


-- ============================================================
-- 10. DELIVERY PERFORMANCE
-- ============================================================

SELECT
    delivery_performance,
    COUNT(*) AS order_count
FROM orders
WHERE order_status = 'delivered'
GROUP BY delivery_performance
ORDER BY order_count DESC;


-- ============================================================
-- 11. AVERAGE DELIVERY TIME BY STATE
-- ============================================================

SELECT
    c.customer_state,
    COUNT(DISTINCT o.order_id) AS delivered_orders,
    ROUND(AVG(o.delivery_days), 2) AS average_delivery_days,
    ROUND(
        AVG(
            CASE
                WHEN o.delivery_performance = 'Late'
                THEN 1.0
                ELSE 0.0
            END
        ) * 100,
        2
    ) AS late_order_percentage
FROM orders AS o
JOIN customers AS c
    ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
HAVING delivered_orders >= 100
ORDER BY average_delivery_days DESC;


-- ============================================================
-- 12. REVIEW SCORE DISTRIBUTION
-- ============================================================

SELECT
    review_score,
    COUNT(*) AS review_count
FROM reviews
GROUP BY review_score
ORDER BY review_score;


-- ============================================================
-- 13. AVERAGE REVIEW SCORE
-- ============================================================

SELECT
    ROUND(AVG(review_score), 2) AS average_review_score
FROM reviews;


-- ============================================================
-- 14. REVIEW SCORE VS DELIVERY TIME
-- ============================================================

SELECT
    r.review_score,
    COUNT(*) AS review_count,
    ROUND(AVG(o.delivery_days), 2) AS average_delivery_days
FROM reviews AS r
JOIN orders AS o
    ON r.order_id = o.order_id
WHERE o.delivery_days IS NOT NULL
GROUP BY r.review_score
ORDER BY r.review_score;


-- ============================================================
-- 15. PAYMENT VALUE BY PAYMENT TYPE
-- ============================================================

SELECT
    payment_type,
    COUNT(*) AS payment_records,
    ROUND(SUM(payment_value), 2) AS total_payment_value,
    ROUND(AVG(payment_value), 2) AS average_payment_value
FROM payments
GROUP BY payment_type
ORDER BY total_payment_value DESC;


-- ============================================================
-- 16. INSTALLMENT ANALYSIS
-- ============================================================

SELECT
    payment_installments,
    COUNT(*) AS payment_records,
    ROUND(SUM(payment_value), 2) AS total_payment_value,
    ROUND(AVG(payment_value), 2) AS average_payment_value
FROM payments
GROUP BY payment_installments
ORDER BY payment_installments;


-- ============================================================
-- 17. SELLER PERFORMANCE
-- ============================================================

SELECT
    seller_id,
    COUNT(DISTINCT order_id) AS orders_handled,
    ROUND(SUM(price), 2) AS sales_value,
    ROUND(AVG(price), 2) AS average_item_price
FROM order_items
GROUP BY seller_id
ORDER BY sales_value DESC
LIMIT 10;


-- ============================================================
-- 18. PRODUCT CATEGORY AVERAGE PRICE
-- ============================================================

SELECT
    COALESCE(
        ct.product_category_name_english,
        p.product_category_name
    ) AS category,
    COUNT(*) AS items_sold,
    ROUND(SUM(oi.price), 2) AS sales_value,
    ROUND(AVG(oi.price), 2) AS average_item_price
FROM order_items AS oi
JOIN products AS p
    ON oi.product_id = p.product_id
LEFT JOIN category_translation AS ct
    ON p.product_category_name = ct.product_category_name
GROUP BY category
ORDER BY sales_value DESC;


-- ============================================================
-- 19. NON-DELIVERED ORDERS
-- ============================================================

SELECT
    order_status,
    COUNT(*) AS order_count
FROM orders
WHERE order_status != 'delivered'
GROUP BY order_status
ORDER BY order_count DESC;


-- ============================================================
-- 20. ORDERS WITH EXTREME DELIVERY TIMES
-- ============================================================

SELECT
    order_id,
    order_status,
    delivery_days,
    delivery_delay_days,
    delivery_performance
FROM orders
WHERE delivery_days > 60
ORDER BY delivery_days DESC;