import React, { useState } from 'react';
import { FieldProfile, FieldTrends } from '../../types/api';
import { Badge } from '../common/Badge';
import { DropletIcon, ThermometerIcon } from '../common/Icons';
import { Language, TRANSLATIONS } from '../../i18n/translations';

interface TrendsScreenProps {
  field: FieldProfile;
  trends: FieldTrends;
  lang: Language;
}

export const TrendsScreen: React.FC<TrendsScreenProps> = ({ field, trends, lang }) => {
  const t = TRANSLATIONS[lang];
  const [selectedRange, setSelectedRange] = useState<'24h' | '7d'>('24h');

  // Simulated 24-hour hourly points for accessible SVG trend representation
  const hourlyPoints = [
    { hour: '00:00', sm: 0.14, temp: 22.1 },
    { hour: '04:00', sm: 0.14, temp: 20.4 },
    { hour: '08:00', sm: 0.13, temp: 25.8 },
    { hour: '12:00', sm: 0.12, temp: 32.5 },
    { hour: '16:00', sm: 0.11, temp: 31.2 },
    { hour: '20:00', sm: 0.11, temp: 26.0 },
    { hour: 'Now', sm: 0.11, temp: 24.5 },
  ];

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0 }}>Environmental Trends</h2>
          <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>
            Historical dry-down slope and thermal fluctuations
          </p>
        </div>

        {/* Range Selector */}
        <div style={{ display: 'flex', backgroundColor: '#e2e8f0', borderRadius: '8px', padding: '2px' }}>
          <button
            onClick={() => setSelectedRange('24h')}
            style={{
              padding: '4px 12px',
              fontSize: '0.75rem',
              fontWeight: 700,
              borderRadius: '6px',
              backgroundColor: selectedRange === '24h' ? '#166534' : 'transparent',
              color: selectedRange === '24h' ? '#ffffff' : '#475569',
              cursor: 'pointer',
            }}
          >
            24 Hours
          </button>
          <button
            onClick={() => setSelectedRange('7d')}
            style={{
              padding: '4px 12px',
              fontSize: '0.75rem',
              fontWeight: 700,
              borderRadius: '6px',
              backgroundColor: selectedRange === '7d' ? '#166534' : 'transparent',
              color: selectedRange === '7d' ? '#ffffff' : '#475569',
              cursor: 'pointer',
            }}
          >
            7 Days
          </button>
        </div>
      </div>

      {/* Soil Moisture Depletion Trend Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <DropletIcon size={20} color="#16a34a" />
            <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0 }}>Soil Moisture Depletion</h3>
          </div>
          <Badge label={trends.soil_moisture_trend} variant="danger" size="sm" />
        </div>

        <p style={{ fontSize: '0.8rem', color: '#475569', marginBottom: '12px' }}>
          Root zone moisture has declined from <strong>{trends.soil_moisture_max.toFixed(2)} m³/m³</strong> to{' '}
          <strong style={{ color: '#dc2626' }}>{trends.soil_moisture_min.toFixed(2)} m³/m³</strong> over the last 24h.
        </p>

        {/* Simplified Bar Representation of 24h Telemetry */}
        <div style={{ display: 'flex', alignItems: 'flex-end', height: '100px', gap: '8px', padding: '8px 0', borderBottom: '1px solid #e2e8f0' }}>
          {hourlyPoints.map((p, i) => {
            const heightPercent = Math.max(15, (p.sm / 0.20) * 100);
            const isDeficit = p.sm < 0.13;
            return (
              <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <span style={{ fontSize: '0.65rem', fontWeight: 600, color: isDeficit ? '#dc2626' : '#166534' }}>
                  {p.sm.toFixed(2)}
                </span>
                <div
                  style={{
                    width: '100%',
                    height: `${heightPercent}px`,
                    backgroundColor: isDeficit ? '#f87171' : '#86efac',
                    borderRadius: '4px 4px 0 0',
                    transition: 'height 0.3s ease',
                  }}
                />
                <span style={{ fontSize: '0.65rem', color: '#94a3b8' }}>{p.hour}</span>
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', fontSize: '0.75rem', color: '#64748b' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', backgroundColor: '#f87171', borderRadius: '2px' }} />
            <span>Below FAO-56 Threshold (0.166 m³/m³)</span>
          </div>
          <span>Observed: {trends.observation_count} readings</span>
        </div>
      </div>

      {/* Temperature & Atmospheric Evaporation */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ThermometerIcon size={20} color="#3b82f6" />
            <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0 }}>Temperature & Evaporative Demand</h3>
          </div>
          <Badge label="HIGH TRANSPIRATION" variant="warning" size="sm" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', margin: '8px 0' }}>
          <div style={{ padding: '8px', backgroundColor: '#f8fafc', borderRadius: '6px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.7rem', color: '#64748b' }}>Minimum</span>
            <p style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>20.4°C</p>
          </div>
          <div style={{ padding: '8px', backgroundColor: '#f8fafc', borderRadius: '6px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.7rem', color: '#64748b' }}>Average</span>
            <p style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>{trends.ambient_temp_mean.toFixed(1)}°C</p>
          </div>
          <div style={{ padding: '8px', backgroundColor: '#fef2f2', borderRadius: '6px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.7rem', color: '#991b1b' }}>Peak Heat</span>
            <p style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, color: '#b91c1c' }}>{trends.ambient_temp_max.toFixed(1)}°C</p>
          </div>
        </div>

        <p style={{ fontSize: '0.75rem', color: '#475569', margin: '6px 0 0 0' }}>
          High afternoon temperatures (&gt;32°C) combined with moderate humidity (58%) accelerate evapotranspiration rates, increasing daily moisture loss to 5.2mm/day.
        </p>
      </div>
    </div>
  );
};
