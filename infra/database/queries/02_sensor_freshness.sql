-- Query 2: Sensor Freshness & Health Dashboard
-- Computes the latest observation time, elapsed latency, and forensic status for each sensor.

SELECT 
    sm.sensor_id,
    sm.field_id,
    sm.sensor_model,
    sm.measured_variable,
    sm.unit,
    sm.provenance_type,
    latest_obs.last_event_time,
    latest_obs.last_value,
    ROUND(EXTRACT(EPOCH FROM (NOW() - latest_obs.last_event_time))::numeric, 1) AS freshness_latency_seconds,
    COALESCE(latest_health.health_state, 'UNKNOWN') AS current_health_state,
    COALESCE(latest_health.reason_code, 'NO_DATA') AS health_reason_code
FROM sensor_metadata sm
LEFT JOIN LATERAL (
    SELECT o.event_time AS last_event_time, o.numeric_value AS last_value
    FROM observations o
    WHERE o.sensor_id = sm.sensor_id
    ORDER BY o.event_time DESC
    LIMIT 1
) latest_obs ON TRUE
LEFT JOIN LATERAL (
    SELECT sh.health_state, sh.reason_code
    FROM sensor_health_events sh
    WHERE sh.sensor_id = sm.sensor_id
    ORDER BY sh.event_time DESC
    LIMIT 1
) latest_health ON TRUE
WHERE sm.is_active = TRUE
ORDER BY freshness_latency_seconds ASC NULLS LAST;

