import React, { useState } from 'react';
import {
  AgentHandoffSummary,
  CandidateAlert,
  CitationReference,
  FieldProfile,
  InvestigationSummary,
} from '../../types/api';
import { Badge } from '../common/Badge';
import { AlertTriangleIcon, DropletIcon, ShieldCheckIcon } from '../common/Icons';
import { MultiAgentProgress } from '../common/MultiAgentProgress';
import { Language, TRANSLATIONS } from '../../i18n/translations';

interface AlertsScreenProps {
  field: FieldProfile;
  alerts: CandidateAlert[];
  investigation: InvestigationSummary | null;
  agentMessages: AgentHandoffSummary[];
  citations: CitationReference[];
  lang: Language;
  onNavigateToAdvisories: () => void;
}

export const AlertsScreen: React.FC<AlertsScreenProps> = ({
  field,
  alerts,
  investigation,
  agentMessages,
  citations,
  lang,
  onNavigateToAdvisories,
}) => {
  const t = TRANSLATIONS[lang];
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(
    alerts.length > 0 ? alerts[0].alert_id : null
  );

  const selectedAlert = alerts.find((a) => a.alert_id === selectedAlertId) || alerts[0];

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0 }}>{t.alert_inbox}</h2>
        <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>
          Deterministic stress alerts and multi-agent investigations
        </p>
      </div>

      {alerts.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '32px 16px' }}>
          <ShieldCheckIcon size={40} color="#16a34a" />
          <p style={{ fontSize: '0.9rem', color: '#475569', marginTop: '8px' }}>{t.no_alerts}</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Alert Selector Tabs if multiple */}
          {alerts.length > 1 && (
            <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
              {alerts.map((alert) => (
                <button
                  key={alert.alert_id}
                  onClick={() => setSelectedAlertId(alert.alert_id)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '8px',
                    border: '1px solid',
                    borderColor: selectedAlertId === alert.alert_id ? '#166534' : '#cbd5e1',
                    backgroundColor: selectedAlertId === alert.alert_id ? '#f0fdf4' : '#ffffff',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {alert.alert_type.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          )}

          {/* Selected Alert Detail Card */}
          {selectedAlert && (
            <div className="card" style={{ borderLeft: '5px solid #dc2626' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertTriangleIcon size={20} color="#dc2626" />
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: '#991b1b' }}>
                      {selectedAlert.alert_type.replace(/_/g, ' ')}
                    </h3>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    {t.last_updated}: {new Date(selectedAlert.event_time).toLocaleTimeString()}
                  </span>
                </div>
                <Badge label={selectedAlert.severity} variant="danger" />
              </div>

              {/* Observed Physical Evidence */}
              <div style={{ marginTop: '14px', padding: '10px 12px', backgroundColor: '#fef2f2', borderRadius: '8px', border: '1px solid #fee2e2' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#991b1b' }}>
                  📊 {t.corroborating_evidence}
                </span>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', marginTop: '6px' }}>
                  <div style={{ fontSize: '0.75rem', color: '#7f1d1d' }}>
                    Current Moisture: <strong>0.12 m³/m³</strong>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#7f1d1d' }}>
                    FAO-56 Threshold: <strong>0.166 m³/m³</strong>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#7f1d1d' }}>
                    Deficit Fraction: <strong>65% Depletion</strong>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#7f1d1d' }}>
                    Sensor Reliability: <strong>100% (Healthy)</strong>
                  </div>
                </div>
              </div>

              {/* Why This Matters for the Farmer */}
              <div style={{ marginTop: '12px', fontSize: '0.8rem', color: '#334155', lineHeight: '1.4' }}>
                <strong style={{ color: '#0f172a' }}>🌱 {t.why_it_matters}:</strong>
                <p style={{ margin: '4px 0 0 0' }}>
                  Your finger millet (Ragi GPU-28) is currently in the <strong>flowering stage</strong>. Soil moisture depletion below 0.166 m³/m³ at this stage prevents proper pollination, leading to spikelet sterility and up to 35% grain yield loss if unaddressed within 48 hours.
                </p>
              </div>

              {/* Multi-Agent Transparency Section */}
              <MultiAgentProgress
                investigation={investigation}
                agentMessages={agentMessages}
                citations={citations}
                lang={lang}
              />

              {/* Quick Action Button to Advisories */}
              <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  onClick={onNavigateToAdvisories}
                  style={{
                    backgroundColor: '#166534',
                    color: '#ffffff',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontSize: '0.85rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <ShieldCheckIcon size={18} color="#ffffff" />
                  View Recommended Next Steps →
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

