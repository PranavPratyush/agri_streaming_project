import React from 'react';
import { SproutIcon } from './Icons';
import { Language, TRANSLATIONS } from '../../i18n/translations';

interface HeaderProps {
  currentFieldId: string;
  onOpenFieldSelect: () => void;
  lang: Language;
  onToggleLang: () => void;
  isOnline: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentFieldId,
  onOpenFieldSelect,
  lang,
  onToggleLang,
  isOnline,
}) => {
  const t = TRANSLATIONS[lang];

  return (
    <header
      role="banner"
      style={{
        backgroundColor: '#166534',
        color: '#ffffff',
        padding: '12px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              backgroundColor: '#15803d',
              padding: '6px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <SproutIcon size={24} color="#86efac" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: '#ffffff' }}>
              {t.app_title}
            </h1>
            <p style={{ fontSize: '0.75rem', color: '#bbf7d0', margin: 0 }}>
              {t.app_subtitle}
            </p>
          </div>
        </div>

        <button
          onClick={onToggleLang}
          aria-label={`Switch language to ${t.switch_lang}`}
          style={{
            backgroundColor: '#14532d',
            color: '#fef08a',
            border: '1px solid #22c55e',
            borderRadius: '20px',
            padding: '6px 12px',
            fontSize: '0.85rem',
            fontWeight: 700,
            cursor: 'pointer',
            minHeight: '40px',
          }}
        >
          {t.switch_lang}
        </button>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#14532d',
          padding: '6px 12px',
          borderRadius: '8px',
          fontSize: '0.8rem',
        }}
      >
        <button
          onClick={onOpenFieldSelect}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            color: '#ffffff',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '32px',
          }}
          aria-label={`${t.active_parcel}: ${currentFieldId}. Click to switch field.`}
        >
          <span style={{ color: '#86efac' }}>📍 {t.active_parcel}:</span>
          <span style={{ textDecoration: 'underline' }}>{currentFieldId}</span>
        </button>

        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            color: isOnline ? '#86efac' : '#fca5a5',
            fontWeight: 600,
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: isOnline ? '#22c55e' : '#ef4444',
            }}
          />
          {isOnline ? t.online : t.offline}
        </span>
      </div>
    </header>
  );
};

