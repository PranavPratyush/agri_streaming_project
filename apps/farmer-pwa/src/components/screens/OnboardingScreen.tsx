import React, { useState } from 'react';
import { SproutIcon, ShieldCheckIcon } from '../common/Icons';
import { Language, TRANSLATIONS } from '../../i18n/translations';

interface OnboardingScreenProps {
  onCompleteOnboarding: (fieldId: string, role: string) => void;
  lang: Language;
  onToggleLang: () => void;
}

export const OnboardingScreen: React.FC<OnboardingScreenProps> = ({
  onCompleteOnboarding,
  lang,
  onToggleLang,
}) => {
  const t = TRANSLATIONS[lang];
  const [selectedField, setSelectedField] = useState<string>('field-kolar-001');
  const [role, setRole] = useState<string>('farmer');

  return (
    <div
      role="region"
      aria-labelledby="onboarding-welcome"
      style={{
        padding: '24px 16px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '80vh',
        gap: '20px',
      }}
    >
      <div
        style={{
          backgroundColor: '#166534',
          width: '64px',
          height: '64px',
          borderRadius: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 12px rgba(22, 101, 52, 0.3)',
        }}
      >
        <SproutIcon size={36} color="#86efac" />
      </div>

      <div style={{ textAlign: 'center' }}>
        <h2 id="onboarding-welcome" style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', margin: '0 0 6px 0' }}>
          {t.app_title}
        </h2>
        <p style={{ fontSize: '0.9rem', color: '#64748b', margin: 0, maxWidth: '340px' }}>
          {t.app_subtitle}
        </p>
      </div>

      {/* Language Switcher */}
      <button
        onClick={onToggleLang}
        style={{
          padding: '6px 14px',
          backgroundColor: '#f0fdf4',
          color: '#166534',
          border: '1px solid #bbf7d0',
          borderRadius: '20px',
          fontSize: '0.85rem',
          fontWeight: 700,
          cursor: 'pointer',
        }}
      >
        🌐 Switch to {t.switch_lang}
      </button>

      {/* Selection Card */}
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '380px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}
      >
        <div>
          <label style={{ fontSize: '0.85rem', fontWeight: 700, color: '#334155', display: 'block', marginBottom: '6px' }}>
            Select Field Parcel
          </label>
          <select
            value={selectedField}
            onChange={(e) => setSelectedField(e.target.value)}
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              fontSize: '0.9rem',
              backgroundColor: '#ffffff',
            }}
          >
            <option value="field-kolar-001">Kolar North Parcel (Finger Millet GPU-28)</option>
            <option value="field-demo-parcel">Sarvamangalam Test Farm (Live Met Station)</option>
          </select>
        </div>

        <div>
          <label style={{ fontSize: '0.85rem', fontWeight: 700, color: '#334155', display: 'block', marginBottom: '6px' }}>
            Sign-in Persona
          </label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              onClick={() => setRole('farmer')}
              style={{
                flex: 1,
                padding: '8px',
                borderRadius: '6px',
                fontSize: '0.85rem',
                fontWeight: 700,
                border: '1px solid',
                borderColor: role === 'farmer' ? '#166534' : '#cbd5e1',
                backgroundColor: role === 'farmer' ? '#f0fdf4' : '#ffffff',
                color: role === 'farmer' ? '#166534' : '#64748b',
                cursor: 'pointer',
              }}
            >
              👨‍🌾 Farmer
            </button>
            <button
              type="button"
              onClick={() => setRole('agronomist')}
              style={{
                flex: 1,
                padding: '8px',
                borderRadius: '6px',
                fontSize: '0.85rem',
                fontWeight: 700,
                border: '1px solid',
                borderColor: role === 'agronomist' ? '#166534' : '#cbd5e1',
                backgroundColor: role === 'agronomist' ? '#f0fdf4' : '#ffffff',
                color: role === 'agronomist' ? '#166534' : '#64748b',
                cursor: 'pointer',
              }}
            >
              🧑‍🔬 Agronomist
            </button>
          </div>
        </div>

        {/* Core Principles Guarantee */}
        <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', flexDirection: 'column', gap: '4px', borderTop: '1px solid #f1f5f9', paddingTop: '10px' }}>
          <div>✓ Ground soil sensors and live openSenseMap weather telemetry.</div>
          <div>✓ Multi-agent safety review citing verified FAO & ICAR publications.</div>
          <div>✓ Zero autonomous hardware actuation: Human decision is required.</div>
        </div>

        <button
          onClick={() => onCompleteOnboarding(selectedField, role)}
          style={{
            backgroundColor: '#166534',
            color: '#ffffff',
            padding: '12px',
            borderRadius: '8px',
            fontSize: '0.95rem',
            fontWeight: 700,
            cursor: 'pointer',
            minHeight: '48px',
            marginTop: '6px',
          }}
        >
          Enter Field Workbench →
        </button>
      </div>
    </div>
  );
};

