-- Use these as approved starting queries, not free-form LLM SQL.
-- Revenue here means gross sold item value (before order-level discounts / shipping),
-- restricted to orders not cancelled, not necessarily net recognized revenue.
SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price_inr),2) AS gross_item_sales_inr
FROM order_items oi JOIN orders o ON o.order_id=oi.order_id
JOIN products p ON p.product_id=oi.product_id
WHERE o.status <> 'cancelled' AND o.order_date >= '2026-09-01' AND o.order_date < '2026-10-01'
GROUP BY p.category ORDER BY gross_item_sales_inr DESC LIMIT 5;

-- Available-to-sell stock per product
SELECT p.product_id,p.name,SUM(i.on_hand-i.reserved) AS available_units
FROM products p JOIN inventory i ON i.product_id=p.product_id
GROUP BY p.product_id,p.name ORDER BY available_units ASC LIMIT 20;

-- Customer-scoped order: :authenticated_customer_id must come from verified backend auth.
SELECT o.order_id,o.status,s.tracking_number,s.estimated_delivery_at,s.delivered_at
FROM orders o LEFT JOIN shipments s ON s.order_id=o.order_id
WHERE o.order_id=:order_id AND o.customer_id=:authenticated_customer_id LIMIT 1;
