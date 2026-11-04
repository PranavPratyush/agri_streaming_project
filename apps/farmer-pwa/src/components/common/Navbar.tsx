import React from 'react';
import { AlertTriangleIcon, LayersIcon, SproutIcon, CompassIcon, ShieldCheckIcon } from './Icons';
import { Language, TRANSLATIONS } from '../../i18n/translations';

export type ScreenId = 'overview' | 'trends' | 'alerts' | 'advisories' | 'fields' | 'history';

interface NavbarProps {
  activeScreen: ScreenId;
  onSelectScreen: (screen: ScreenId) => void;
  lang: Language;
  unreadAlertsCount: number;
  pendingAdvisoriesCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeScreen,
  onSelectScreen,
  lang,
  unreadAlertsCount,
  pendingAdvisoriesCount,
}) => {
  const t = TRANSLATIONS[lang];

  const items: Array<{ id: ScreenId; label: string; icon: React.ReactNode; badgeCount?: number }> = [
    { id: 'overview', label: t.nav_overview, icon: <SproutIcon size={22} /> },
    { id: 'trends', label: t.nav_trends, icon: <CompassIcon size={22} /> },
    { id: 'alerts', label: t.nav_alerts, icon: <AlertTriangleIcon size={22} />, badgeCount: unreadAlertsCount },
    { id: 'advisories', label: t.nav_advisories, icon: <ShieldCheckIcon size={22} />, badgeCount: pendingAdvisoriesCount },
    { id: 'fields', label: t.nav_fields, icon: <LayersIcon size={22} /> },
  ];

  return (
    <nav
      role="navigation"
      aria-label="Main Farmer Navigation"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        maxWidth: '768px',
        margin: '0 auto',
        backgroundColor: '#ffffff',
        borderTop: '1px solid #e2e8f0',
        display: 'flex',
        justifyContent: 'space-around',
        alignItems: 'center',
        height: '64px',
        zIndex: 50,
        boxShadow: '0 -2px 6px rgba(0, 0, 0, 0.05)',
      }}
    >
      {items.map((item) => {
        const isActive = activeScreen === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onSelectScreen(item.id)}
            role="tab"
            aria-selected={isActive}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              minWidth: '48px',
              minHeight: '48px',
              color: isActive ? '#166534' : '#64748b',
              fontWeight: isActive ? 700 : 500,
              fontSize: '0.75rem',
              gap: '3px',
              position: 'relative',
              cursor: 'pointer',
              borderTop: isActive ? '3px solid #166534' : '3px solid transparent',
              background: 'none',
            }}
          >
            <div style={{ position: 'relative' }}>
              {item.icon}
              {!!item.badgeCount && item.badgeCount > 0 && (
                <span
                  style={{
                    position: 'absolute',
                    top: '-6px',
                    right: '-10px',
                    backgroundColor: '#ef4444',
                    color: '#ffffff',
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    borderRadius: '10px',
                    padding: '1px 5px',
                    lineHeight: '1',
                  }}
                  aria-label={`${item.badgeCount} notifications`}
                >
                  {item.badgeCount}
                </span>
              )}
            </div>
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
};

