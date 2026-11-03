-- Query 4: Full Alert Evidence Chain & Audit Trail
-- Links a candidate alert -> sensor health status -> agent investigation -> recommendation -> farmer feedback.
-- Parameter: :target_alert_id

SELECT 
    ca.alert_id,
    ca.field_id,
    ca.event_time AS alert_time,
    ca.alert_type,
    ca.severity AS alert_severity,
    ca.composite_stress_index,
    ca.uncertainty_score,
    ca.contributing_features,
    ca.evidence AS alert_evidence,
    
    -- Investigation Details
    ir.investigation_id,
    ir.agent_model,
    ir.investigation_summary,
    ir.corroborating_evidence,
    ir.conflicting_evidence,
    ir.confidence_score AS agent_confidence,
    
    -- Farmer Recommendation Details
    rec.recommendation_id,
    rec.action_category,
    rec.action_title,
    rec.action_body,
    rec.approval_status,
    rec.approved_by,
    rec.approved_at,
    
    -- Farmer Feedback Details
    fb.feedback_id,
    fb.farmer_id,
    fb.rating AS farmer_rating,
    fb.action_taken,
    fb.observed_outcome,
    fb.feedback_comments
FROM crop_candidate_alerts ca
LEFT JOIN investigation_reports ir ON ca.alert_id = ir.alert_id
LEFT JOIN farmer_recommendations rec ON ca.alert_id = rec.alert_id
LEFT JOIN human_feedback fb ON rec.recommendation_id = fb.recommendation_id
WHERE ca.alert_id = '00000000-0000-0000-0000-000000000000' -- Replace with specific UUID
ORDER BY ca.event_time DESC;

