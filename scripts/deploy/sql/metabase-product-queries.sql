-- ============================================================
-- Car Backend — Metabase product queries (PostgreSQL)
-- Paste into Metabase → New → SQL query
-- ============================================================

-- 1) New users per day
SELECT
  date_trunc('day', created_at AT TIME ZONE 'Asia/Tehran') AS day,
  COUNT(*) AS new_users
FROM users
WHERE is_active = true
GROUP BY 1
ORDER BY 1 DESC;

-- 2) Active purchase requests by car model
SELECT
  cm.name AS model_name,
  COUNT(*) AS active_requests
FROM purchase_requests pr
JOIN car_trims ct ON ct.id = pr.car_trim_id
JOIN car_models cm ON cm.id = ct.model_id
WHERE pr.is_active = true
GROUP BY cm.name
ORDER BY active_requests DESC;

-- 3) Best opportunities today (discount %)
SELECT
  o.created_at,
  o.discount_pct,
  o.discount_amount,
  o.score,
  o.deal_tag,
  l.title,
  l.price,
  l.production_year,
  l.kilometer,
  l.district,
  l.divar_url
FROM opportunities o
JOIN listings l ON l.id = o.listing_id
WHERE o.created_at >= CURRENT_DATE
ORDER BY o.discount_pct DESC
LIMIT 50;

-- 4) SMS delivery funnel
SELECT
  sms_status,
  COUNT(*) AS count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM opportunity_deliveries
GROUP BY sms_status
ORDER BY count DESC;

-- 5) Crawl health (last 7 days)
SELECT
  date_trunc('day', started_at AT TIME ZONE 'Asia/Tehran') AS day,
  status,
  COUNT(*) AS runs,
  SUM(posts_found) AS posts,
  SUM(opportunities_found) AS opportunities
FROM crawl_runs
WHERE started_at >= NOW() - INTERVAL '7 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- 6) Listing price vs market (latest market price per listing)
SELECT
  l.title,
  l.price AS divar_price,
  mp.price_down AS market_low,
  mp.price_up AS market_high,
  l.price - mp.price_down AS diff_vs_market_low,
  ROUND(100.0 * (mp.price_down - l.price) / NULLIF(mp.price_down, 0), 2) AS discount_pct,
  l.production_year,
  l.kilometer,
  l.divar_url
FROM listings l
JOIN LATERAL (
  SELECT price_down, price_up, price_mid
  FROM market_prices
  WHERE listing_id = l.id
  ORDER BY fetched_at DESC
  LIMIT 1
) mp ON true
WHERE l.is_active = true
ORDER BY discount_pct DESC NULLS LAST
LIMIT 100;

-- 7) Gateway clicks after SMS
SELECT
  date_trunc('day', gc.clicked_at AT TIME ZONE 'Asia/Tehran') AS day,
  COUNT(*) AS clicks,
  COUNT(DISTINCT d.user_id) AS unique_users
FROM gateway_clicks gc
JOIN opportunity_deliveries d ON d.id = gc.delivery_id
GROUP BY 1
ORDER BY 1 DESC;

-- 8) Top cities for purchase requests
SELECT
  city,
  COUNT(*) AS requests
FROM purchase_requests
WHERE is_active = true
GROUP BY city
ORDER BY requests DESC;

-- 9) Catalog: models with most purchase interest
SELECT
  cb.name AS brand,
  cm.name AS model,
  COUNT(pr.id) AS total_requests,
  COUNT(*) FILTER (WHERE pr.is_active) AS active_requests
FROM car_models cm
JOIN car_brands cb ON cb.id = cm.brand_id
LEFT JOIN car_trims ct ON ct.model_id = cm.id
LEFT JOIN purchase_requests pr ON pr.car_trim_id = ct.id
GROUP BY cb.name, cm.name
ORDER BY total_requests DESC;

-- 10) Average discount by deal tag
SELECT
  deal_tag,
  COUNT(*) AS opportunities,
  ROUND(AVG(discount_pct), 2) AS avg_discount_pct,
  ROUND(AVG(discount_amount), 0) AS avg_discount_amount
FROM opportunities
GROUP BY deal_tag
ORDER BY avg_discount_pct DESC;
