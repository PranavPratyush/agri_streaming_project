/**
 * Frontend API Client interacting exclusively with AgriKafka-Agent Backend API.
 * Never connects directly to databases, Kafka, Chroma, or model providers.
 */

import {
  AdvisoryProposal,
  AgentHandoffSummary,
  CandidateAlert,
  CitationReference,
  FarmerFeedbackPayload,
  FieldProfile,
  FieldStatus,
  FieldTrends,
  HumanDecisionPayload,
  InvestigationSummary,
  ObservationRecord,
  SensorFreshness,
  StateTimelineEvent,
} from '../types/api';

const API_BASE_URL = '/api/v1';

// Default mock fixtures for offline demonstration when backend container is disconnected
const MOCK_FIELDS: FieldProfile[] = [
  {
    field_id: 'field-kolar-001',
    name: 'Kolar North Parcel - Finger Millet Demonstration',
    latitude: 13.1333,
    longitude: 78.1333,
    elevation_m: 822.0,
    crop_name: 'finger_millet',
    variety: 'GPU-28',
    sowing_date: '2026-07-15',
    expected_harvest_date: '2026-11-20',
    current_growth_stage: 'flowering',
    soil_type: 'red_sandy_loam',
    soil_texture: 'sandy_clay_loam',
    field_capacity: 0.22,
    wilting_point: 0.10,
    root_zone_depth_m: 0.50,
    irrigation_type: 'rainfed',
    is_active: true,
    metadata: { taluk: 'Kolar', zone: 'Karnataka Zone 5' },
  },
  {
    field_id: 'field-demo-parcel',
    name: 'Sarvamangalam Weather Station Field',
    latitude: 12.0000,
    longitude: 79.8000,
    elevation_m: 45.0,
    crop_name: 'finger_millet',
    variety: 'GPU-28',
    sowing_date: '2026-08-01',
    expected_harvest_date: '2026-12-05',
    current_growth_stage: 'vegetative',
    soil_type: 'red_sandy_loam',
    soil_texture: 'sandy_clay_loam',
    field_capacity: 0.22,
    wilting_point: 0.10,
    root_zone_depth_m: 0.40,
    irrigation_type: 'protective_drip',
    is_active: true,
    metadata: { station: 'openSenseMap_Sarvamangalam' },
  },
];

export class ApiService {
  private activeFarmerId: string = 'field-kolar-001';
  private userRole: string = 'farmer';

  constructor() {
    const saved = localStorage.getItem('agrikafka_active_field');
    if (saved) {
      this.activeFarmerId = saved;
    }
  }

  public setFarmerContext(fieldId: string, role: string = 'farmer') {
    this.activeFarmerId = fieldId;
    this.userRole = role;
    localStorage.setItem('agrikafka_active_field', fieldId);
    localStorage.setItem('agrikafka_user_role', role);
  }

  public getActiveFieldId(): string {
    return this.activeFarmerId;
  }

  private getHeaders(): HeadersInit {
    return {
      'Content-Type': 'application/json',
      'X-User-Role': this.userRole,
      'X-User-ID': `farmer-${this.activeFarmerId}`,
      'X-Farmer-ID': this.activeFarmerId,
    };
  }

  public async getFields(): Promise<FieldProfile[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/fields`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.items || data;
    } catch {
      return MOCK_FIELDS;
    }
  }

  public async getFieldProfile(fieldId: string): Promise<FieldProfile> {
    try {
      const res = await fetch(`${API_BASE_URL}/fields/${fieldId}`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return MOCK_FIELDS.find((f) => f.field_id === fieldId) || MOCK_FIELDS[0];
    }
  }

  public async updateFieldProfile(fieldId: string, updates: Partial<FieldProfile>): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE_URL}/fields/${fieldId}`, {
        method: 'PATCH',
        headers: this.getHeaders(),
        body: JSON.stringify(updates),
      });
      return res.ok;
    } catch {
      const idx = MOCK_FIELDS.findIndex((f) => f.field_id === fieldId);
      if (idx >= 0) {
        MOCK_FIELDS[idx] = { ...MOCK_FIELDS[idx], ...updates };
        return true;
      }
      return false;
    }
  }

  public async getFieldStatus(fieldId: string): Promise<FieldStatus> {
    try {
      const res = await fetch(`${API_BASE_URL}/fields/${fieldId}/status`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return {
        field_id: fieldId,
        crop_variety: 'GPU-28',
        growth_stage: 'flowering',
        composite_stress_index: 0.76,
        risk_level: 'HIGH',
        sensor_health_overall: 'HEALTHY',
        latest_soil_moisture: 0.12,
        latest_ambient_temp: 31.8,
        telemetry_latency_seconds: 18.4,
        active_alerts_count: 1,
        pending_advisories_count: 1,
        data_freshness_status: 'FRESH',
      };
    }
  }

  public async getObservations(fieldId: string): Promise<ObservationRecord[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/fields/${fieldId}/observations`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.items || data;
    } catch {
      return [
        {
          event_time: new Date().toISOString(),
          sensor_id: 'soil-probe-vh400-01',
          observed_variable: 'soil_moisture',
          numeric_value: 0.12,
          unit: 'm3/m3',
          provenance: 'physical_sensor',
          quality_flags: ['VALID_RANGE'],
        },
        {
          event_time: new Date().toISOString(),
          sensor_id: 'station-sarvamangalam-temp',
          observed_variable: 'ambient_temp',
          numeric_value: 31.8,
          unit: 'celsius',
          provenance: 'weather_station',
          quality_flags: ['VALID_RANGE'],
        },
        {
          event_time: new Date().toISOString(),
          sensor_id: 'station-sarvamangalam-rh',
          observed_variable: 'relative_humidity',
          numeric_value: 58.4,
          unit: 'percent',
          provenance: 'weather_station',
          quality_flags: ['VALID_RANGE'],
        },
      ];
    }
  }

  public async getTrends(fieldId: string): Promise<FieldTrends> {
    try {
      const res = await fetch(`${API_BASE_URL}/fields/${fieldId}/trends`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return {
        field_id: fieldId,
        window_hours: 24,
        soil_moisture_trend: 'DEPLETING',
        soil_moisture_mean: 0.13,
        soil_moisture_min: 0.11,
        soil_moisture_max: 0.16,
        ambient_temp_mean: 29.4,
        ambient_temp_max: 33.1,
        relative_humidity_mean: 58.2,
        observation_count: 96,
      };
    }
  }

  public async getSensorFreshness(): Promise<SensorFreshness[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/sensors/freshness`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return [
        {
          sensor_id: 'soil-probe-vh400-01',
          field_id: this.activeFarmerId,
          sensor_model: 'Capacitance-VH400',
          measured_variable: 'soil_moisture',
          unit: 'm3/m3',
          provenance_type: 'physical_sensor',
          last_event_time: new Date().toISOString(),
          last_value: 0.12,
          latency_seconds: 18.4,
          health_state: 'HEALTHY',
          reason_code: 'ALL_SENSORS_VALID',
        },
        {
          sensor_id: 'station-sarvamangalam-met',
          field_id: this.activeFarmerId,
          sensor_model: 'openSenseMap-Sarvamangalam',
          measured_variable: 'ambient_temp',
          unit: 'celsius',
          provenance_type: 'weather_station',
          last_event_time: new Date().toISOString(),
          last_value: 31.8,
          latency_seconds: 24.1,
          health_state: 'HEALTHY',
          reason_code: 'ALL_SENSORS_VALID',
        },
      ];
    }
  }

  public async getAlerts(fieldId?: string): Promise<CandidateAlert[]> {
    try {
      const query = fieldId ? `?field_id=${fieldId}` : '';
      const res = await fetch(`${API_BASE_URL}/alerts${query}`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.items || data;
    } catch {
      return [
        {
          alert_id: 'c1a4169f-48bd-494d-a2e0-32c3f2e9688a',
          field_id: fieldId || this.activeFarmerId,
          event_time: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
          alert_type: 'SOIL_MOISTURE_DEPLETION',
          severity: 'HIGH',
          status: 'CANDIDATE',
          composite_stress_index: 0.76,
          fao56_depletion_fraction: 0.65,
          blast_risk_score: 0.12,
          thermal_stress_score: 0.35,
          sensor_health_state: 'HEALTHY',
          uncertainty_score: 0.15,
          contributing_features: [
            { feature_name: 'soil_moisture_depletion', severity: 'HIGH' },
            { feature_name: 'thermal_drydown', severity: 'MEDIUM' },
          ],
          evidence: {
            observed_soil_moisture: 0.12,
            fao56_depletion_threshold: 0.166,
            deficit_fraction: 0.65,
            root_depth_cm: 50,
          },
        },
      ];
    }
  }

  public async getAdvisories(fieldId?: string): Promise<AdvisoryProposal[]> {
    try {
      const query = fieldId ? `?field_id=${fieldId}` : '';
      const res = await fetch(`${API_BASE_URL}/advisories${query}`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.items || data;
    } catch {
      return [
        {
          recommendation_id: 'rec-fao56-ragi-001',
          alert_id: 'c1a4169f-48bd-494d-a2e0-32c3f2e9688a',
          field_id: fieldId || this.activeFarmerId,
          investigation_id: 'run-kolar-inv-001',
          approval_status: 'PROPOSED',
          action_category: 'IRRIGATION',
          action_title: 'Apply 25mm Protective Irrigation to Avoid Flowering Yield Loss',
          action_body: 'Soil moisture is currently at 0.12 m³/m³, well below the critical FAO-56 depletion threshold (0.166 m³/m³) during the flowering stage. Apply 20–25mm of protective irrigation within 24 hours to prevent panicle blast susceptibility and grain abort.',
          urgency: 'HIGH',
          cited_evidence_ids: ['CIT-FAO56-001', 'CIT-ICAR-RAGI-001'],
          assumptions: [
            'Red sandy loam topsoil with 60cm effective rooting zone depth.',
            'Borewell or protective farm pond storage is accessible.',
          ],
          limitations: [
            'Irrigation recommendation assumes well-drained Alfisols without hardpan compaction.',
          ],
          confidence_score: 0.92,
          when_to_seek_expert: 'If standing water occurs or if water salinity is suspected above 2.0 dS/m.',
          next_step: 'Human agronomist or farmer confirmation before dispatch.',
          created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
        },
      ];
    }
  }

  public async getInvestigationSummary(runId: string): Promise<InvestigationSummary> {
    try {
      const res = await fetch(`${API_BASE_URL}/investigations/${runId}`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return {
        run_id: runId,
        alert_id: 'c1a4169f-48bd-494d-a2e0-32c3f2e9688a',
        field_id: this.activeFarmerId,
        current_state: 'awaiting_human_review',
        final_decision: 'AWAITING_HUMAN_REVIEW',
        revision_count: 0,
        max_revisions: 2,
        summary_title: 'Apply 25mm Protective Irrigation to Prevent Yield Loss',
        reliability_assessment: {
          is_trustworthy: true,
          health_state: 'HEALTHY',
          reason_code: 'ALL_SENSORS_VALID',
          summary: 'Ground capacitive probe and regional met station telemetry validated healthy without drift.',
        },
        risk_assessment: {
          severity: 'HIGH',
          category: 'SOIL_MOISTURE_DEPLETION',
          deterministic_csi: 0.76,
          hypothesis: 'Root-zone water depletion fraction p=0.65 exceeds critical ragi threshold.',
        },
        advisory_preview: {
          title: 'Apply 25mm Protective Irrigation to Avoid Flowering Yield Loss',
          category: 'IRRIGATION',
          urgency: 'HIGH',
          confidence: 0.92,
          citations: ['CIT-FAO56-001', 'CIT-ICAR-RAGI-001'],
          next_step: 'Awaiting farmer/agronomist confirmation.',
        },
        critic_verdict: 'APPROVED_FOR_HUMAN_REVIEW',
        safety_gate_passed: true,
        created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
        updated_at: new Date().toISOString(),
      };
    }
  }

  public async getInvestigationTimeline(runId: string): Promise<StateTimelineEvent[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/investigations/${runId}/timeline`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return [
        { transition_id: 1, from_state: 'received', to_state: 'checking_reliability', triggered_by: 'supervisor', timestamp: '12:00:00' },
        { transition_id: 2, from_state: 'checking_reliability', to_state: 'extracting_context', triggered_by: 'supervisor', timestamp: '12:00:01' },
        { transition_id: 3, from_state: 'extracting_context', to_state: 'analysing_risk', triggered_by: 'supervisor', timestamp: '12:00:02' },
        { transition_id: 4, from_state: 'analysing_risk', to_state: 'retrieving_knowledge', triggered_by: 'supervisor', timestamp: '12:00:03' },
        { transition_id: 5, from_state: 'retrieving_knowledge', to_state: 'synthesising_advisory', triggered_by: 'supervisor', timestamp: '12:00:04' },
        { transition_id: 6, from_state: 'synthesising_advisory', to_state: 'reviewing_critic', triggered_by: 'supervisor', timestamp: '12:00:05' },
        { transition_id: 7, from_state: 'reviewing_critic', to_state: 'awaiting_human_review', triggered_by: 'supervisor', reason: 'Critic approved proposal for human review', timestamp: '12:00:06' },
      ];
    }
  }

  public async getInvestigationMessages(runId: string): Promise<AgentHandoffSummary[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/investigations/${runId}/messages`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return [
        {
          message_id: 'msg-01',
          from_agent: 'sensor_reliability_agent',
          to_agent: 'supervisor',
          message_type: 'task_result',
          status: 'success',
          created_at: '12:00:01',
          concise_summary: 'Soil probe VH400 readings verified healthy. Z-score 0.2, zero flatline.',
          evidence_references: ['sensor-vh400-01'],
        },
        {
          message_id: 'msg-02',
          from_agent: 'crop_risk_analyst',
          to_agent: 'supervisor',
          message_type: 'task_result',
          status: 'success',
          created_at: '12:00:02',
          concise_summary: 'Severe moisture depletion detected during sensitive flowering growth stage.',
          evidence_references: ['csi:0.76'],
        },
        {
          message_id: 'msg-03',
          from_agent: 'agronomy_knowledge_agent',
          to_agent: 'supervisor',
          message_type: 'task_result',
          status: 'success',
          created_at: '12:00:03',
          concise_summary: 'Retrieved verified FAO-56 ragi crop coefficients and ICAR dryland protective irrigation protocols.',
          evidence_references: ['CIT-FAO56-001', 'CIT-ICAR-RAGI-001'],
        },
        {
          message_id: 'msg-04',
          from_agent: 'critic_safety_agent',
          to_agent: 'supervisor',
          message_type: 'task_result',
          status: 'success',
          created_at: '12:00:05',
          concise_summary: 'Safety review passed. No chemical dosages proposed. Physical actuation commands strictly absent.',
          evidence_references: ['gate:zero_actuation'],
        },
      ];
    }
  }

  public async getInvestigationCitations(runId: string): Promise<CitationReference[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/investigations/${runId}/citations`, { headers: this.getHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return [
        {
          citation_id: 'CIT-FAO56-001',
          source_id: 'FAO-56',
          document_title: 'Crop Evapotranspiration - Guidelines for Computing Crop Water Requirements',
          section_heading: 'Table 22: Small Grain Millets Depletion Threshold p=0.65',
          canonical_url: 'https://www.fao.org/3/x0490e/x0490e0b.htm',
          relevance_score: 0.94,
          excerpt: 'For finger millet (Eleusine coracana), depletion of total available soil water beyond fraction p = 0.65 during flowering leads to irreversible yield reduction.',
        },
        {
          citation_id: 'CIT-ICAR-RAGI-001',
          source_id: 'ICAR-CRIDA',
          document_title: 'Contingency Agricultural Planning for Kolar and Chikkaballapur Districts',
          section_heading: 'Protective Irrigation in Dryland Alfisols',
          canonical_url: 'https://icar.gov.in/content/contingency-plans-karnataka',
          relevance_score: 0.91,
          excerpt: 'During mid-season dry spells coinciding with flowering, application of 20-25 mm protective irrigation using farm pond or community borewell preserves grain formation.',
        },
      ];
    }
  }

  public async submitHumanDecision(runId: string, payload: HumanDecisionPayload): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE_URL}/investigations/${runId}/human-decision`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(payload),
      });
      return res.ok;
    } catch {
      return true; // Local optimistic UI update
    }
  }

  public async submitAdvisoryAction(recommendationId: string, payload: HumanDecisionPayload): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE_URL}/advisories/${recommendationId}/action`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(payload),
      });
      return res.ok;
    } catch {
      return true;
    }
  }

  public async submitFeedback(payload: FarmerFeedbackPayload): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE_URL}/feedback`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(payload),
      });
      return res.ok;
    } catch {
      return true;
    }
  }
}

export const api = new ApiService();

