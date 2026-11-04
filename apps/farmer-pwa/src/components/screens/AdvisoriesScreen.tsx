import React, { useState } from 'react';
import { AdvisoryProposal, FieldProfile } from '../../types/api';
import { Badge } from '../common/Badge';
import { CheckCircleIcon, DropletIcon, ShieldCheckIcon, XCircleIcon } from '../common/Icons';
import { Language, TRANSLATIONS } from '../../i18n/translations';

interface AdvisoriesScreenProps {
  field: FieldProfile;
  advisories: AdvisoryProposal[];
  onAction: (recommendationId: string, action: 'APPROVE' | 'REJECT' | 'REQUEST_INSPECTION' | 'ACKNOWLEDGE', comments?: string) => Promise<boolean>;
  onSubmitFeedback: (recommendationId: string, rating: number, actionTaken: boolean, comments: string) => Promise<boolean>;
  lang: Language;
}

export const AdvisoriesScreen: React.FC<AdvisoriesScreenProps> = ({
  field,
  advisories,
  onAction,
  onSubmitFeedback,
  lang,
}) => {
  const t = TRANSLATIONS[lang];
  const [actingId, setActingId] = useState<string | null>(null);
  const [feedbackModalRecId, setFeedbackModalRecId] = useState<string | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<number>(5);
  const [feedbackComments, setFeedbackComments] = useState<string>('');
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  const handleActionClick = async (recId: string, action: 'APPROVE' | 'REJECT' | 'REQUEST_INSPECTION' | 'ACKNOWLEDGE') => {
    setActingId(recId);
    try {
      const ok = await onAction(recId, action);
      if (ok) {
        setActionSuccessMsg(`${t.action_recorded} (${action})`);
        if (action === 'APPROVE') {
          setFeedbackModalRecId(recId);
        }
      }
    } finally {
      setActingId(null);
    }
  };

  const handleFeedbackSubmit = async () => {
    if (!feedbackModalRecId) return;
    await onSubmitFeedback(feedbackModalRecId, feedbackRating, true, feedbackComments);
    setFeedbackModalRecId(null);
    setFeedbackComments('');
  };

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0 }}>{t.advisory_title}</h2>
        <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>
          Validated agronomic next steps supported by scientific research
        </p>
      </div>

      {actionSuccessMsg && (
        <div
          role="status"
          style={{
            padding: '10px 14px',
            backgroundColor: '#f0fdf4',
            border: '1px solid #86efac',
            borderRadius: '8px',
            color: '#166534',
            fontSize: '0.85rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <CheckCircleIcon size={20} color="#16a34a" />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {advisories.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '32px 16px' }}>
          <ShieldCheckIcon size={40} color="#16a34a" />
          <p style={{ fontSize: '0.9rem', color: '#475569', marginTop: '8px' }}>
            No pending advisories. All management actions are up to date.
          </p>
        </div>
      ) : (
        advisories.map((adv) => {
          const isResolved = adv.approval_status === 'APPROVED' || adv.approval_status === 'REJECTED';
          return (
            <div
              key={adv.recommendation_id}
              className="card"
              style={{
                borderTop: '4px solid #166534',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <DropletIcon size={20} color="#16a34a" />
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: '#166534' }}>
                      {adv.action_title}
                    </h3>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    Category: {adv.action_category} • {t.urgency_label}: <strong>{adv.urgency}</strong>
                  </span>
                </div>
                <Badge
                  label={adv.approval_status}
                  variant={adv.approval_status === 'APPROVED' ? 'healthy' : adv.approval_status === 'PROPOSED' ? 'warning' : 'neutral'}
                />
              </div>

              {/* Action Body */}
              <p style={{ fontSize: '0.85rem', color: '#1e293b', lineHeight: '1.5', margin: 0 }}>
                {adv.action_body}
              </p>

              {/* Assumptions & Limitations Box */}
              <div style={{ backgroundColor: '#f8fafc', padding: '10px 12px', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '0.75rem' }}>
                <strong style={{ color: '#334155' }}>📋 {t.assumptions_label}:</strong>
                <ul style={{ margin: '4px 0 8px 16px', color: '#475569' }}>
                  {adv.assumptions.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>

                <strong style={{ color: '#334155' }}>⚠️ {t.limitations_label}:</strong>
                <ul style={{ margin: '4px 0 0 16px', color: '#475569' }}>
                  {adv.limitations.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>

              {/* Confidence & Uncertainty */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#64748b' }}>
                <span>🎯 {t.uncertainty_label}: {(adv.confidence_score * 100).toFixed(0)}% Match</span>
                <span>Ref: {adv.cited_evidence_ids.join(', ')}</span>
              </div>

              {/* Human Review Controls (Screen 9) */}
              {!isResolved && (
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '6px' }}>
                  <button
                    onClick={() => handleActionClick(adv.recommendation_id, 'APPROVE')}
                    disabled={actingId === adv.recommendation_id}
                    style={{
                      flex: 1,
                      backgroundColor: '#166534',
                      color: '#ffffff',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      minHeight: '44px',
                    }}
                  >
                    <CheckCircleIcon size={18} color="#ffffff" />
                    {t.btn_approve}
                  </button>

                  <button
                    onClick={() => handleActionClick(adv.recommendation_id, 'REJECT')}
                    disabled={actingId === adv.recommendation_id}
                    style={{
                      flex: 1,
                      backgroundColor: '#ffffff',
                      color: '#dc2626',
                      border: '1px solid #fca5a5',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      minHeight: '44px',
                    }}
                  >
                    <XCircleIcon size={18} color="#dc2626" />
                    {t.btn_reject}
                  </button>

                  <button
                    onClick={() => handleActionClick(adv.recommendation_id, 'REQUEST_INSPECTION')}
                    disabled={actingId === adv.recommendation_id}
                    style={{
                      padding: '10px 14px',
                      backgroundColor: '#f8fafc',
                      color: '#475569',
                      border: '1px solid #cbd5e1',
                      borderRadius: '8px',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      minHeight: '44px',
                    }}
                  >
                    {t.btn_inspect}
                  </button>
                </div>
              )}
            </div>
          );
        })
      )}

      {/* Farmer Feedback Modal (Outcome Loop) */}
      {feedbackModalRecId && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="feedback-dialog-title"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
            zIndex: 100,
          }}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              padding: '20px',
              maxWidth: '440px',
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
            }}
          >
            <h3 id="feedback-dialog-title" style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>
              {t.feedback_title}
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>
              Help improve future recommendations for dryland ragi by sharing your field observation.
            </p>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                Utility Rating (1 to 5 Stars)
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setFeedbackRating(star)}
                    style={{
                      fontSize: '1.4rem',
                      color: star <= feedbackRating ? '#eab308' : '#cbd5e1',
                      cursor: 'pointer',
                      padding: '4px',
                    }}
                    aria-label={`${star} star`}
                  >
                    ★
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                {t.feedback_comments}
              </label>
              <textarea
                value={feedbackComments}
                onChange={(e) => setFeedbackComments(e.target.value)}
                placeholder="e.g. Applied 25mm irrigation from farm pond. Soil recovered to 0.20 m³/m³."
                rows={3}
                style={{
                  width: '100%',
                  padding: '8px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '6px' }}>
              <button
                type="button"
                onClick={() => setFeedbackModalRecId(null)}
                style={{
                  padding: '8px 14px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  color: '#475569',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                Skip
              </button>
              <button
                type="button"
                onClick={handleFeedbackSubmit}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  backgroundColor: '#166534',
                  color: '#ffffff',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                {t.btn_submit_feedback}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

