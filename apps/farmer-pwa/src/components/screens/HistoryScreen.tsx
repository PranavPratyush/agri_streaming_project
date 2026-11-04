import React from 'react';
import { FieldProfile } from '../../types/api';
import { Badge } from '../common/Badge';
import { CheckCircleIcon, ShieldCheckIcon } from '../common/Icons';
import { Language, TRANSLATIONS } from '../../i18n/translations';

interface HistoryScreenProps {
  field: FieldProfile;
  lang: Language;
}

export const HistoryScreen: React.FC<HistoryScreenProps> = ({ field, lang }) => {
  const t = TRANSLATIONS[lang];

  // Verified chronological historical audit entries
  const historyEvents = [
    {
      id: 'hist-01',
      date: '2026-11-04 12:10:00',
      type: 'HUMAN_APPROVAL',
      title: 'Farmer Approved Protective Irrigation',
      description: 'Applied 25mm protective irrigation following soil moisture depletion alert.',
      status: 'APPROVED',
      badgeVariant: 'healthy' as const,
      actor: 'Farmer field-kolar-001',
    },
    {
      id: 'hist-02',
      date: '2026-11-04 12:05:04',
      type: 'INVESTIGATION_COMPLETED',
      title: 'Multi-Agent Investigation Validated',
      description: 'Sensor Reliability, Crop Risk Analyst, and Critic Safety Agent completed review. 2 ICAR/FAO citations attached.',
      status: 'AWAITING_REVIEW',
      badgeVariant: 'info' as const,
      actor: 'MultiAgentSupervisor',
    },
    {
      id: 'hist-03',
      date: '2026-11-04 11:55:00',
      type: 'ALERT_TRIGGERED',
      title: 'Soil Moisture Depletion Detected',
      description: 'Root-zone water fraction dropped to 0.12 m³/m³ (65% deficit during flowering).',
      status: 'TRIGGERED',
      badgeVariant: 'danger' as const,
      actor: 'Deterministic Risk Engine',
    },
    {
      id: 'hist-04',
      date: '2026-11-03 16:30:00',
      type: 'FEEDBACK_SUBMITTED',
      title: 'Farmer Feedback Recorded',
      description: 'Rating: 5/5 stars. "Soil moisture stabilized within 12 hours after irrigation."',
      status: 'HELPFUL',
      badgeVariant: 'healthy' as const,
      actor: 'Farmer field-kolar-001',
    },
    {
      id: 'hist-05',
      date: '2026-07-15 09:00:00',
      type: 'FIELD_REGISTERED',
      title: 'Parcel Registered for Monitoring',
      description: 'Finger Millet (Ragi GPU-28) sown in Red Sandy Loam Alfisols.',
      status: 'REGISTERED',
      badgeVariant: 'neutral' as const,
      actor: 'Agronomist KVK Kolar',
    },
  ];

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0 }}>{t.nav_history}</h2>
        <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>
          Chronological record of alerts, agent evaluations, human decisions, and field outcomes
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {historyEvents.map((event) => (
          <div
            key={event.id}
            className="card"
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>
                  {event.title}
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  🕒 {event.date} • Actor: <strong>{event.actor}</strong>
                </span>
              </div>
              <Badge label={event.status} variant={event.badgeVariant} size="sm" />
            </div>

            <p style={{ fontSize: '0.8rem', color: '#475569', margin: 0 }}>
              {event.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

