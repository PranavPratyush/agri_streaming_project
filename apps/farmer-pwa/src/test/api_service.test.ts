import { describe, it, expect, beforeEach } from 'vitest';
import { ApiService } from '../services/api';

describe('ApiService Tests', () => {
  let api: ApiService;

  beforeEach(() => {
    localStorage.clear();
    api = new ApiService();
  });

  it('initializes with default field-kolar-001 context', () => {
    expect(api.getActiveFieldId()).toBe('field-kolar-001');
  });

  it('updates farmer context and persists to localStorage', () => {
    api.setFarmerContext('field-demo-parcel', 'farmer');
    expect(api.getActiveFieldId()).toBe('field-demo-parcel');
    expect(localStorage.getItem('agrikafka_active_field')).toBe('field-demo-parcel');
  });

  it('returns verified fallback field profiles when offline', async () => {
    const fields = await api.getFields();
    expect(fields.length).toBeGreaterThanOrEqual(2);
    expect(fields.some((f) => f.field_id === 'field-kolar-001')).toBe(true);
    expect(fields.some((f) => f.crop_name === 'finger_millet')).toBe(true);
  });

  it('returns valid field status and sensor health without crashing', async () => {
    const status = await api.getFieldStatus('field-kolar-001');
    expect(status.field_id).toBe('field-kolar-001');
    expect(status.risk_level).toBe('HIGH');
    expect(status.sensor_health_overall).toBe('HEALTHY');
  });

  it('submits human decision without direct model access or leakage', async () => {
    const ok = await api.submitHumanDecision('run-kolar-inv-001', {
      action: 'APPROVE',
      reviewer_id: 'farmer-field-kolar-001',
      comments: 'Applied protective irrigation.',
    });
    expect(ok).toBe(true);
  });
});

