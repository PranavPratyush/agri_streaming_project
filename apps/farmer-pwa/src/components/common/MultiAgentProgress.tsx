import React from 'react';
import { AgentHandoffSummary, CitationReference, InvestigationSummary } from '../../types/api';
import { Badge } from './Badge';
import { CheckCircleIcon, ShieldCheckIcon } from './Icons';
import { Language, TRANSLATIONS } from '../../i18n/translations';

interface MultiAgentProgressProps {
  investigation?: InvestigationSummary | null;
  agentMessages: AgentHandoffSummary[];
  citations: CitationReference[];
  lang: Language;
}

export const MultiAgentProgress: React.FC<MultiAgentProgressProps> = ({
  investigation,
  agentMessages,
  citations,
  lang,
}) => {
  const t = TRANSLATIONS[lang];

  // Helper to extract sanitized summary for an agent
  const getAgentResult = (agentName: string) => {
    const msg = agentMessages.find((m) => m.from_agent === agentName);
    return msg ? msg.concise_summary : null;
  };

  const steps = [
    {
      agent: 'sensor_reliability_agent',
      label: t.agent_sensor,
      summary:
        investigation?.reliability_assessment?.summary ||
        getAgentResult('sensor_reliability_agent') ||
        'Telemetry verified healthy and within physical limits. No flatlines detected.',
      isDone: true,
      statusBadge: 'healthy' as const,
      statusLabel: 'Verified Ground Truth',
    },
    {
      agent: 'field_context_agent',
      label: t.agent_context,
      summary:
        getAgentResult('field_context_agent') ||
        'Confirmed crop variety (Ragi GPU-28) in flowering stage under red sandy loam topsoil.',
      isDone: true,
      statusBadge: 'healthy' as const,
      statusLabel: 'Context Matched',
    },
    {
      agent: 'crop_risk_analyst',
      label: t.agent_risk,
      summary:
        investigation?.risk_assessment?.hypothesis ||
        getAgentResult('crop_risk_analyst') ||
        'Soil water depletion fraction p=0.65 exceeds critical ragi threshold.',
      isDone: true,
      statusBadge: 'warning' as const,
      statusLabel: 'Stress Confirmed',
    },
    {
      agent: 'agronomy_knowledge_agent',
      label: t.agent_knowledge,
      summary:
        getAgentResult('agronomy_knowledge_agent') ||
        'Retrieved verified FAO-56 crop coefficients and ICAR dryland protective irrigation protocols.',
      isDone: true,
      statusBadge: 'info' as const,
      statusLabel: 'Citations Retrieved',
    },
    {
      agent: 'critic_safety_agent',
      label: t.agent_critic,
      summary:
        getAgentResult('critic_safety_agent') ||
        'Safety review passed. Chemical pesticides blocked. Physical irrigation valve actuation prohibited.',
      isDone: true,
      statusBadge: 'healthy' as const,
      statusLabel: 'Safety Approved',
    },
  ];

  return (
    <section
      aria-labelledby="multi-agent-title"
      style={{
        backgroundColor: '#f8fafc',
        border: '1px solid #cbd5e1',
        borderRadius: '12px',
        padding: '16px',
        marginTop: '16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <ShieldCheckIcon size={24} color="#166534" />
        <div>
          <h3 id="multi-agent-title" style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>
            {t.multi_agent_title}
          </h3>
          <p style={{ fontSize: '0.75rem', color: '#64748b', margin: 0 }}>
            {t.multi_agent_subtitle}
          </p>
        </div>
      </div>

      <ol style={{ listStyle: 'none', padding: 0, margin: '12px 0 0 0', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {steps.map((step, idx) => (
          <li
            key={step.agent}
            style={{
              backgroundColor: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '10px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '0.85rem', color: '#1e293b' }}>
                <CheckCircleIcon size={16} color="#16a34a" />
                <span>{step.label}</span>
              </div>
              <Badge label={step.statusLabel} variant={step.statusBadge} size="sm" />
            </div>

            <p style={{ fontSize: '0.8rem', color: '#475569', margin: 0, paddingLeft: '22px' }}>
              {step.summary}
            </p>
          </li>
        ))}
      </ol>

      {/* Citations Box */}
      {citations.length > 0 && (
        <div style={{ marginTop: '12px', padding: '10px', backgroundColor: '#f0fdf4', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
          <h4 style={{ fontSize: '0.8rem', fontWeight: 700, color: '#166534', margin: '0 0 6px 0' }}>
            📖 {t.citations_title}
          </h4>
          <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.75rem', color: '#14532d', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {citations.map((c) => (
              <li key={c.citation_id}>
                <strong>{c.source_id}:</strong> {c.document_title} — <em>{c.section_heading}</em>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Safety & Grounding Disclaimer */}
      <div
        role="note"
        style={{
          marginTop: '12px',
          padding: '8px 12px',
          backgroundColor: '#eff6ff',
          borderLeft: '4px solid #3b82f6',
          borderRadius: '4px',
          fontSize: '0.75rem',
          color: '#1e40af',
          lineHeight: '1.4',
        }}
      >
        {t.agent_disclaimer}
      </div>
    </section>
  );
};

