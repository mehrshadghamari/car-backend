-- OPTIONAL: read-only PostgreSQL user for Metabase.
-- Default install uses the main app DB user (DB_USER in config.env).
-- Only run this when METABASE_USE_READONLY=true in config.env.
-- Replace YOUR_STRONG_PASSWORD before running.

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'metabase_readonly') THEN
    CREATE USER metabase_readonly WITH PASSWORD 'YOUR_STRONG_PASSWORD';
  ELSE
    ALTER USER metabase_readonly WITH PASSWORD 'YOUR_STRONG_PASSWORD';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE car_backend TO metabase_readonly;
GRANT USAGE ON SCHEMA public TO metabase_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO metabase_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO metabase_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO metabase_readonly;

-- Optional: friendly views for Metabase dashboards
CREATE OR REPLACE VIEW v_purchase_requests_detail AS
SELECT
  pr.id,
  pr.created_at,
  pr.is_active,
  pr.city,
  pr.color,
  pr.production_year_min,
  pr.production_year_max,
  pr.expires_at,
  u.phone AS user_phone,
  u.source_channel,
  cb.name AS brand_name,
  cm.name AS model_name,
  cy.title AS year_title,
  ct.name AS trim_name,
  pp.name AS pricing_platform
FROM purchase_requests pr
JOIN users u ON u.id = pr.user_id
JOIN car_trims ct ON ct.id = pr.car_trim_id
JOIN car_models cm ON cm.id = ct.model_id
JOIN car_brands cb ON cb.id = cm.brand_id
JOIN car_years cy ON cy.id = ct.year_id
LEFT JOIN pricing_platforms pp ON pp.id = pr.pricing_platform_id;

CREATE OR REPLACE VIEW v_opportunities_detail AS
SELECT
  o.id,
  o.created_at,
  o.status,
  o.deal_tag,
  o.listing_price,
  o.market_price_down,
  o.market_price_up,
  o.reference_price,
  o.discount_amount,
  o.discount_pct,
  o.score,
  l.title AS listing_title,
  l.price AS current_listing_price,
  l.kilometer,
  l.production_year,
  l.district,
  l.divar_url,
  u.phone AS user_phone,
  cm.name AS model_name,
  ct.name AS trim_name
FROM opportunities o
JOIN listings l ON l.id = o.listing_id
LEFT JOIN purchase_requests pr ON pr.id = o.purchase_request_id
LEFT JOIN users u ON u.id = pr.user_id
LEFT JOIN car_trims ct ON ct.id = pr.car_trim_id
LEFT JOIN car_models cm ON cm.id = ct.model_id;

CREATE OR REPLACE VIEW v_sms_deliveries AS
SELECT
  d.id,
  d.created_at,
  d.sms_status,
  d.sms_sent_at,
  d.sms_error,
  u.phone AS user_phone,
  o.discount_pct,
  o.discount_amount,
  o.score,
  l.title AS listing_title,
  l.divar_url
FROM opportunity_deliveries d
JOIN users u ON u.id = d.user_id
JOIN opportunities o ON o.id = d.opportunity_id
JOIN listings l ON l.id = o.listing_id;

CREATE OR REPLACE VIEW v_crawl_runs_daily AS
SELECT
  date_trunc('day', cr.started_at AT TIME ZONE 'UTC') AS run_day,
  cr.status,
  COUNT(*) AS run_count,
  SUM(cr.posts_found) AS total_posts,
  SUM(cr.opportunities_found) AS total_opportunities
FROM crawl_runs cr
GROUP BY 1, 2;

GRANT SELECT ON v_purchase_requests_detail TO metabase_readonly;
GRANT SELECT ON v_opportunities_detail TO metabase_readonly;
GRANT SELECT ON v_sms_deliveries TO metabase_readonly;
GRANT SELECT ON v_crawl_runs_daily TO metabase_readonly;
