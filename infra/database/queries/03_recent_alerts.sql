-- Query 3: Recent Crop Stress Candidate Alerts (Last 72 Hours)
-- Lists unhandled or high-severity alerts with calculated stress scores and suppression details.

SELECT 
    ca.alert_id,
    ca.field_id,
    ca.event_time,
    ca.alert_type,
    ca.severity,
    ca.status,
    ca.composite_stress_index,
    ca.fao56_depletion_fraction,
    ca.blast_risk_score,
    ca.thermal_stress_score,
    ca.sensor_health_state,
    ca.uncertainty_score,
    ca.contributing_features,
    ca.suppression_reason,
    ir.investigation_id IS NOT NULL AS has_investigation,
    rec.approval_status AS recommendation_status
FROM crop_candidate_alerts ca
LEFT JOIN investigation_reports ir ON ca.alert_id = ir.alert_id
LEFT JOIN farmer_recommendations rec ON ca.alert_id = rec.alert_id
WHERE ca.event_time >= NOW() - INTERVAL '72 hours'
ORDER BY ca.event_time DESC;

