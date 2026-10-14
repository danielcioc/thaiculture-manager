BEGIN;

INSERT INTO pricing_rules (rule_name, tour_id, rule_type, conditions, calculation, is_active)
SELECT
  v.rule_name,
  t.id,
  v.rule_type,
  v.conditions,
  v.calculation,
  TRUE
FROM (
  VALUES
  (
    'PRICE-WEB-006-V1',
    'WEB-006',
    'private_total',
    '{"tour_code":"WEB-006","currency":"THB","min_guests":1,"max_guests":4,"group_size_basis":"per_booking","confidence_status":"estimated","source_note":"Historical private booking, 2 guests, THB 6500 total"}'::jsonb,
    '{"selling_price_gross":6500.00,"vat_rate":0.07,"selling_price_net":6074.77,"direct_cost_total":null,"guide_cost":null,"vehicle_cost":null,"entrance_cost":null,"insurance_cost":null,"insurance_rule":"guests_plus_driver_plus_guide","includes":"Private evening Ayutthaya tour; inclusions pending standardization","excludes":"Pending review"}'::jsonb
  ),
  (
    'PRICE-WEB-007-V1',
    'WEB-007',
    'private_total',
    '{"tour_code":"WEB-007","currency":"THB","min_guests":4,"max_guests":4,"group_size_basis":"per_booking","confidence_status":"confirmed","source_note":"Private Ayutthaya Day Trip 2026-10-06, 4 guests, THB 11500 total"}'::jsonb,
    '{"selling_price_gross":11500.00,"vat_rate":0.07,"selling_price_net":10747.66,"direct_cost_total":6600.00,"guide_cost":2500.00,"vehicle_cost":3000.00,"entrance_cost":800.00,"insurance_cost":300.00,"insurance_rule":"4 guests + 1 driver + 1 guide","includes":"Driver, private premium van, fuel, tolls, parking, temple entrance fees, insurance and VAT","excludes":"Lunch, drinks, personal expenses and gratuities"}'::jsonb
  ),
  (
    'PRICE-WEB-021-V1',
    'WEB-021',
    'private_total',
    '{"tour_code":"WEB-021","currency":"THB","min_guests":5,"max_guests":5,"group_size_basis":"per_booking","confidence_status":"estimated","source_note":"Private tour 2026-02-19, 5 guests, THB 14000 total, supplier cost THB 6200"}'::jsonb,
    '{"selling_price_gross":14000.00,"vat_rate":0.07,"selling_price_net":13084.11,"direct_cost_total":6200.00,"insurance_rule":"guests_plus_driver_plus_guide","includes":"Vehicle, driver, fuel, tolls, parking, guide assistance, insurance, drinking water and hotel pickup/drop-off","excludes":"Entrance fees and meals"}'::jsonb
  ),
  (
    'PRICE-WEB-022-V1',
    'WEB-022',
    'private_total',
    '{"tour_code":"WEB-022","currency":"THB","min_guests":5,"max_guests":5,"group_size_basis":"per_booking","confidence_status":"estimated","source_note":"Private tour 2026-02-22, 5 guests, THB 8900 total, supplier cost THB 6550"}'::jsonb,
    '{"selling_price_gross":8900.00,"vat_rate":0.07,"selling_price_net":8317.76,"direct_cost_total":6550.00,"insurance_rule":"guests_plus_driver_plus_guide","includes":"4x4 safari vehicle with ranger, private van, driver, guide assistance, insurance, water and hotel transfers","excludes":"Entrance fees and meals"}'::jsonb
  ),
  (
    'PRICE-WEB-023-V1',
    'WEB-023',
    'private_total',
    '{"tour_code":"WEB-023","currency":"THB","min_guests":5,"max_guests":5,"group_size_basis":"per_booking","confidence_status":"estimated","source_note":"Private tour 2026-02-16, 5 guests, THB 8900 total, supplier cost THB 5000"}'::jsonb,
    '{"selling_price_gross":8900.00,"vat_rate":0.07,"selling_price_net":8317.76,"direct_cost_total":5000.00,"insurance_rule":"guests_plus_driver_plus_guide","includes":"Vehicle, driver, fuel, tolls, parking, guide assistance, insurance, drinking water and hotel pickup/drop-off","excludes":"Entrance fees and meals"}'::jsonb
  ),
  (
    'PRICE-WEB-027-V1',
    'WEB-027',
    'group_per_person',
    '{"tour_code":"WEB-027","currency":"THB","min_guests":1,"max_guests":1,"group_size_basis":"per_person","confidence_status":"estimated","source_note":"Group record 2026-03-03, THB 2880 per person reference"}'::jsonb,
    '{"selling_price_gross":2880.00,"vat_rate":0.07,"selling_price_net":2691.59,"direct_cost_total":null,"insurance_rule":"needs_review","includes":"Historical group price reference","excludes":"Pending structured inclusions/exclusions review"}'::jsonb
  ),
  (
    'PRICE-WEB-028-V1',
    'WEB-028',
    'group_per_person',
    '{"tour_code":"WEB-028","currency":"THB","min_guests":1,"max_guests":1,"group_size_basis":"per_person","confidence_status":"estimated","source_note":"Group record 2026-03-04, THB 3200 per person reference"}'::jsonb,
    '{"selling_price_gross":3200.00,"vat_rate":0.07,"selling_price_net":2990.65,"direct_cost_total":null,"insurance_rule":"needs_review","includes":"Historical group price reference","excludes":"Pending structured inclusions/exclusions review"}'::jsonb
  )
) AS v(rule_name, tour_code, rule_type, conditions, calculation)
JOIN tours t ON t.tour_code = v.tour_code
WHERE NOT EXISTS (
  SELECT 1
  FROM pricing_rules p
  WHERE p.rule_name = v.rule_name
);

COMMIT;
