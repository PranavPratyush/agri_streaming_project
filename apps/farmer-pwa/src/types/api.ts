/**
 * TypeScript Data Models matching AgriKafka-Agent Backend API Contracts.
 */

export type UserRole = 'farmer' | 'agronomist' | 'admin';

export type GrowthStage = 
  | 'germination'
  | 'vegetative'
  | 'tillering'
  | 'flowering'
  | 'grain_filling'
  | 'maturity'
  | 'harvested';

export interface FieldProfile {
  field_id: string;
  name: string;
  latitude: number;
  longitude: number;
  elevation_m?: number;
  crop_name: string;
  variety: string;
  sowing_date?: string;
  expected_harvest_date?: string;
  current_growth_stage: GrowthStage;
  soil_type: string;
  soil_texture: string;
  field_capacity: number;
  wilting_point: number;
  root_zone_depth_m: number;
  irrigation_type: string;
  is_active: boolean;
  metadata?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface FieldStatus {
  field_id: string;
  crop_variety: string;
  growth_stage: string;
  composite_stress_index: number;
  risk_level: 'NORMAL' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  sensor_health_overall: 'HEALTHY' | 'DEGRADED' | 'SUSPECT' | 'FAULTY';
  latest_soil_moisture?: number;
  latest_ambient_temp?: number;
  telemetry_latency_seconds: number;
  active_alerts_count: number;
  pending_advisories_count: number;
  data_freshness_status: 'FRESH' | 'STALE' | 'DISCONNECTED';
}

export interface ObservationRecord {
  event_time: string;
  sensor_id: string;
  observed_variable: string;
  numeric_value: number;
  unit: string;
  provenance: 'physical_sensor' | 'weather_station' | 'satellite_model' | 'injected_scenario';
  quality_flags: string[];
}

export interface SensorFreshness {
  sensor_id: string;
  field_id: string;
  sensor_model: string;
  measured_variable: string;
  unit: string;
  provenance_type: string;
  last_event_time: string;
  last_value: number;
  latency_seconds: number;
  health_state: 'HEALTHY' | 'DEGRADED' | 'SUSPECT' | 'FAULTY';
  reason_code: string;
}

export interface FieldTrends {
  field_id: string;
  window_hours: number;
  soil_moisture_trend: 'STABLE' | 'DEPLETING' | 'RECHARGING' | 'CRITICAL_DEFICIT';
  soil_moisture_mean: number;
  soil_moisture_min: number;
  soil_moisture_max: number;
  ambient_temp_mean: number;
  ambient_temp_max: number;
  relative_humidity_mean: number;
  observation_count: number;
}

export interface CandidateAlert {
  alert_id: string;
  field_id: string;
  event_time: string;
  alert_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'CANDIDATE' | 'SUPPRESSED' | 'INVESTIGATING' | 'RESOLVED';
  composite_stress_index: number;
  fao56_depletion_fraction?: number;
  blast_risk_score?: number;
  thermal_stress_score?: number;
  sensor_health_state: string;
  uncertainty_score: number;
  contributing_features: Array<{ feature_name: string; severity: string }>;
  evidence: Record<string, any>;
  suppression_reason?: string | null;
}

export interface AgentHandoffSummary {
  message_id: string;
  from_agent: string;
  to_agent: string;
  message_type: string;
  status: string;
  created_at: string;
  concise_summary: string;
  evidence_references: string[];
}

export interface StateTimelineEvent {
  transition_id: number;
  from_state: string;
  to_state: string;
  triggered_by: string;
  reason?: string;
  timestamp: string;
}

export interface CitationReference {
  citation_id: string;
  source_id: string;
  document_title: string;
  section_heading: string;
  canonical_url?: string;
  relevance_score: number;
  excerpt: string;
}

export interface InvestigationSummary {
  run_id: string;
  alert_id: string;
  field_id: string;
  current_state: string;
  final_decision: string;
  revision_count: number;
  max_revisions: number;
  abstention_reason?: string | null;
  summary_title?: string;
  reliability_assessment?: {
    is_trustworthy: boolean;
    health_state: string;
    reason_code: string;
    summary: string;
  };
  risk_assessment?: {
    severity: string;
    category: string;
    deterministic_csi: number;
    hypothesis: string;
  };
  advisory_preview?: {
    title: string;
    category: string;
    urgency: string;
    confidence: number;
    citations: string[];
    next_step?: string;
  };
  critic_verdict?: string;
  safety_gate_passed?: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdvisoryProposal {
  recommendation_id: string;
  alert_id: string;
  field_id: string;
  investigation_id?: string;
  approval_status: 'PROPOSED' | 'APPROVED' | 'REJECTED' | 'SUPERSEDED' | 'AWAITING_REVIEW';
  action_category: 'IRRIGATION' | 'SOIL_CONSERVATION' | 'FIELD_INSPECTION' | 'MONITORING';
  action_title: string;
  action_body: string;
  urgency: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  cited_evidence_ids: string[];
  assumptions: string[];
  limitations: string[];
  confidence_score: number;
  when_to_seek_expert?: string;
  next_step?: string;
  expiry_time?: string;
  approved_by?: string;
  approved_at?: string;
  created_at: string;
}

export interface HumanDecisionPayload {
  action: 'APPROVE' | 'REJECT' | 'REQUEST_INSPECTION' | 'ACKNOWLEDGE';
  reviewer_id?: string;
  comments?: string;
  idempotency_key?: string;
}

export interface FarmerFeedbackPayload {
  recommendation_id: string;
  field_id: string;
  rating: number; // 1 to 5
  action_taken: boolean;
  observed_outcome?: string;
  feedback_comments?: string;
  idempotency_key?: string;
}

