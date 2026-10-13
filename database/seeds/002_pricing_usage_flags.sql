BEGIN;

UPDATE pricing_rules
SET calculation = calculation || jsonb_build_object(
  'pricing_use',
  CASE
    WHEN conditions->>'confidence_status' = 'confirmed'
      THEN 'approved_for_quote'
    ELSE 'reference_only'
  END,
  'cost_status',
  CASE
    WHEN calculation->>'direct_cost_total' IS NULL
      THEN 'incomplete'
    ELSE 'available'
  END,
  'requires_manual_review',
  CASE
    WHEN conditions->>'confidence_status' = 'confirmed'
     AND calculation->>'direct_cost_total' IS NOT NULL
      THEN false
    ELSE true
  END
)
WHERE is_active = true;

COMMIT;
