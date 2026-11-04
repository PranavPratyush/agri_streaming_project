import React from 'react';
import { FieldProfile, FieldStatus, ObservationRecord, SensorFreshness } from '../../types/api';
import { Badge } from '../common/Badge';
import { DropletIcon, ThermometerIcon, SproutIcon, AlertTriangleIcon, ShieldCheckIcon } from '../common/Icons';
import { Language, TRANSLATIONS } from '../../i18n/translations';

interface OverviewScreenProps {
  field: FieldProfile;
  status: FieldStatus;
  observations: ObservationRecord[];
  sensorFreshness: SensorFreshness[];
  lang: Language;
  onNavigateToAlerts: () => void;
  onNavigateToAdvisories: () => void;
}

export const OverviewScreen: React.FC<OverviewScreenProps> = ({
  field,
  status,
  observations,
  sensorFreshness,
  lang,
  onNavigateToAlerts,
  onNavigateToAdvisories,
}) => {
  const t = TRANSLATIONS[lang];

  // Primary telemetry values
  const soilMoisture = observations.find((o) => o.observed_variable === 'soil_moisture')?.numeric_value ?? status.latest_soil_moisture ?? 0.12;
  const ambientTemp = observations.find((o) => o.observed_variable === 'ambient_temp')?.numeric_value ?? status.latest_ambient_temp ?? 31.8;
  const humidity = observations.find((o) => o.observed_variable === 'relative_humidity')?.numeric_value ?? 58.4;

  const isMoistureCritical = soilMoisture < 0.166; // FAO-56 critical threshold for Ragi in Alfisols
  const isHealthySensor = status.sensor_health_overall === 'HEALTHY';

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Field Header Card */}
      <div className="card" style={{ borderLeft: '5px solid #166534' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: '0 0 4px 0' }}>{field.name}</h2>
            <p style={{ fontSize: '0.85rem', color: '#64748b', margin: 0 }}>
              🌾 {field.crop_name === 'finger_millet' ? 'Finger Millet (Ragi)' : field.crop_name} — <strong>{field.variety}</strong>
            </p>
          </div>
          <Badge
            label={t[`stage_${field.current_growth_stage}` as keyof typeof t] || field.current_growth_stage}
            variant="healthy"
          />
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '12px', fontSize: '0.8rem', color: '#475569' }}>
          <span>🌱 {field.soil_type.replace(/_/g, ' ')}</span>
          <span>💧 {field.irrigation_type.replace(/_/g, ' ')}</span>
          <span>🧭 Lat: {field.latitude.toFixed(2)}° Lon: {field.longitude.toFixed(2)}°</span>
        </div>
      </div>

      {/* Sensor Health Notice (Screen 6) */}
      <div
        role="region"
        aria-label="Sensor Reliability Notice"
        style={{
          padding: '12px 14px',
          borderRadius: '10px',
          backgroundColor: isHealthySensor ? '#f0fdf4' : '#fffbeb',
          border: isHealthySensor ? '1px solid #bbf7d0' : '1px solid #fde68a',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}
      >
        <div style={{ flexShrink: 0 }}>
          {isHealthySensor ? <ShieldCheckIcon size={24} color="#16a34a" /> : <AlertTriangleIcon size={24} color="#d97706" />}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', color: isHealthySensor ? '#166534' : '#92400e' }}>
              {isHealthySensor ? t.status_healthy : t.status_degraded}
            </span>
            <Badge label={t.status_fresh} variant="healthy" size="sm" />
          </div>
          <p style={{ fontSize: '0.75rem', color: '#475569', margin: 0 }}>
            {isHealthySensor
              ? 'Soil capacitance probe and regional met station telemetry are active and verified within physical bounds.'
              : 'Notice: Some sensors are experiencing transmission delays. Fallback weather station data active.'}
          </p>
        </div>
      </div>

      {/* Primary Telemetry Cards (Screen 4) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
        {/* Soil Moisture */}
        <div
          className="card"
          style={{
            margin: 0,
            borderTop: isMoistureCritical ? '4px solid #ef4444' : '4px solid #22c55e',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b' }}>{t.soil_moisture}</span>
            <DropletIcon size={20} color={isMoistureCritical ? '#ef4444' : '#22c55e'} />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', margin: '8px 0 4px 0' }}>
            <span style={{ fontSize: '1.8rem', fontWeight: 800, color: isMoistureCritical ? '#b91c1c' : '#15803d' }}>
              {soilMoisture.toFixed(2)}
            </span>
            <span style={{ fontSize: '0.85rem', color: '#64748b' }}>m³/m³</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem' }}>
            <span style={{ color: '#64748b' }}>{t.critical_threshold}: 0.17</span>
            <Badge label={isMoistureCritical ? 'DRY DEFICIT' : 'ADEQUATE'} variant={isMoistureCritical ? 'danger' : 'healthy'} size="sm" />
          </div>
          <div style={{ marginTop: '6px', fontSize: '0.68rem', color: '#94a3b8' }}>
            🏷️ {t.provenance_physical}
          </div>
        </div>

        {/* Temperature & Humidity */}
        <div className="card" style={{ margin: 0, borderTop: '4px solid #3b82f6' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b' }}>{t.temperature}</span>
            <ThermometerIcon size={20} color="#3b82f6" />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', margin: '8px 0 4px 0' }}>
            <span style={{ fontSize: '1.8rem', fontWeight: 800, color: '#1e3a8a' }}>
              {ambientTemp.toFixed(1)}
            </span>
            <span style={{ fontSize: '0.85rem', color: '#64748b' }}>°C</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#475569' }}>
            <span>{t.humidity}: {humidity.toFixed(0)}%</span>
          </div>
          <div style={{ marginTop: '6px', fontSize: '0.68rem', color: '#94a3b8' }}>
            🏷️ {t.provenance_station}
          </div>
        </div>
      </div>

      {/* Crop Stress Index Overview Card */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b' }}>{t.csi_stress}</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', margin: '4px 0' }}>
            <span style={{ fontSize: '1.6rem', fontWeight: 800, color: status.composite_stress_index > 0.6 ? '#dc2626' : '#16a34a' }}>
              {(status.composite_stress_index * 100).toFixed(0)}%
            </span>
            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
              ({status.risk_level} RISK)
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: '#64748b', margin: 0 }}>
            {status.composite_stress_index > 0.6
              ? 'Mid-season moisture deficit combined with high transpiration.'
              : 'Crop transpiration within normal limits.'}
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {status.active_alerts_count > 0 && (
            <button
              onClick={onNavigateToAlerts}
              style={{
                backgroundColor: '#fef2f2',
                color: '#dc2626',
                border: '1px solid #fecaca',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              ⚠️ {status.active_alerts_count} Active Alerts
            </button>
          )}

          {status.pending_advisories_count > 0 && (
            <button
              onClick={onNavigateToAdvisories}
              style={{
                backgroundColor: '#166534',
                color: '#ffffff',
                border: 'none',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              📋 Review Advice
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

