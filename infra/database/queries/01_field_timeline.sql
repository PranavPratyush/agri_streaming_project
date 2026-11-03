-- Query 1: Field 24-Hour Timeline
-- Retrieves time-series observations and derived window features for a target field.
-- Parameter: :field_id (e.g. 'field-kolar-ragi-01'), :start_time, :end_time

SELECT 
    o.event_time,
    o.ingestion_time,
    o.sensor_id,
    o.observed_variable,
    o.numeric_value,
    o.unit,
    o.provenance,
    o.quality_flags->>'validation_status' AS validation_status
FROM observations o
WHERE o.field_id = 'field-kolar-ragi-01'
  AND o.event_time >= NOW() - INTERVAL '24 hours'
ORDER BY o.event_time ASC;

