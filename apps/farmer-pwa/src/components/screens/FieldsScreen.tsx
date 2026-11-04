import React, { useState } from 'react';
import { FieldProfile, GrowthStage } from '../../types/api';
import { Badge } from '../common/Badge';
import { MapPinIcon, SproutIcon } from '../common/Icons';
import { Language, TRANSLATIONS } from '../../i18n/translations';

interface FieldsScreenProps {
  fields: FieldProfile[];
  activeFieldId: string;
  onSelectField: (fieldId: string) => void;
  onSaveField: (field: Partial<FieldProfile>) => Promise<boolean>;
  lang: Language;
}

export const FieldsScreen: React.FC<FieldsScreenProps> = ({
  fields,
  activeFieldId,
  onSelectField,
  onSaveField,
  lang,
}) => {
  const t = TRANSLATIONS[lang];
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editingField, setEditingField] = useState<Partial<FieldProfile>>({
    name: '',
    crop_name: 'finger_millet',
    variety: 'GPU-28',
    current_growth_stage: 'flowering',
    soil_type: 'red_sandy_loam',
    irrigation_type: 'rainfed',
    latitude: 13.13,
    longitude: 78.13,
  });

  const handleEditClick = (f: FieldProfile) => {
    setEditingField(f);
    setIsEditing(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSaveField(editingField);
    setIsEditing(false);
  };

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0 }}>{t.nav_fields}</h2>
          <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>
            Registered agricultural parcels and crop profiles
          </p>
        </div>

        <button
          onClick={() => {
            setEditingField({
              field_id: `field-kolar-${Date.now().toString().slice(-3)}`,
              name: 'New Kolar Parcel',
              crop_name: 'finger_millet',
              variety: 'GPU-28',
              current_growth_stage: 'vegetative',
              soil_type: 'red_sandy_loam',
              soil_texture: 'sandy_clay_loam',
              field_capacity: 0.22,
              wilting_point: 0.10,
              root_zone_depth_m: 0.50,
              irrigation_type: 'rainfed',
              latitude: 13.13,
              longitude: 78.13,
            });
            setIsEditing(true);
          }}
          style={{
            backgroundColor: '#166534',
            color: '#ffffff',
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '0.8rem',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          + {t.register_field}
        </button>
      </div>

      {/* Field List (Screen 2) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {fields.map((f) => {
          const isSelected = f.field_id === activeFieldId;
          return (
            <div
              key={f.field_id}
              className="card"
              style={{
                border: isSelected ? '2px solid #166534' : '1px solid #cbd5e1',
                backgroundColor: isSelected ? '#f0fdf4' : '#ffffff',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <SproutIcon size={20} color="#166534" />
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>
                      {f.name}
                    </h3>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    ID: <code>{f.field_id}</code>
                  </span>
                </div>
                <Badge
                  label={isSelected ? 'ACTIVE' : 'SELECT'}
                  variant={isSelected ? 'healthy' : 'neutral'}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px', fontSize: '0.8rem', color: '#475569' }}>
                <div>🌾 Crop: <strong>{f.variety} ({f.crop_name})</strong></div>
                <div>🌱 Stage: <strong>{f.current_growth_stage}</strong></div>
                <div>🟫 Soil: <strong>{f.soil_type.replace(/_/g, ' ')}</strong></div>
                <div>💧 Method: <strong>{f.irrigation_type.replace(/_/g, ' ')}</strong></div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <MapPinIcon size={14} /> Lat: {f.latitude.toFixed(3)}°, Lon: {f.longitude.toFixed(3)}°
                </span>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => handleEditClick(f)}
                    style={{
                      padding: '4px 10px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: '#166534',
                      border: '1px solid #bbf7d0',
                      borderRadius: '6px',
                      backgroundColor: '#ffffff',
                      cursor: 'pointer',
                    }}
                  >
                    Edit
                  </button>
                  {!isSelected && (
                    <button
                      onClick={() => onSelectField(f.field_id)}
                      style={{
                        padding: '4px 12px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        color: '#ffffff',
                        backgroundColor: '#166534',
                        borderRadius: '6px',
                        cursor: 'pointer',
                      }}
                    >
                      Switch To
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Field Profile Setup / Edit Modal (Screen 3) */}
      {isEditing && (
        <div
          role="dialog"
          aria-modal="true"
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
          <form
            onSubmit={handleFormSubmit}
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              padding: '20px',
              maxWidth: '480px',
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
              maxHeight: '90vh',
              overflowY: 'auto',
            }}
          >
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>
              {editingField.field_id ? t.edit_field : t.register_field}
            </h3>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                {t.field_name}
              </label>
              <input
                type="text"
                required
                value={editingField.name || ''}
                onChange={(e) => setEditingField({ ...editingField, name: e.target.value })}
                style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Crop Variety
                </label>
                <select
                  value={editingField.variety || 'GPU-28'}
                  onChange={(e) => setEditingField({ ...editingField, variety: e.target.value })}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                >
                  <option value="GPU-28">Finger Millet (GPU-28)</option>
                  <option value="ML-365">Finger Millet (ML-365)</option>
                  <option value="KMR-301">Finger Millet (KMR-301)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Growth Stage
                </label>
                <select
                  value={editingField.current_growth_stage || 'flowering'}
                  onChange={(e) => setEditingField({ ...editingField, current_growth_stage: e.target.value as GrowthStage })}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                >
                  <option value="germination">Germination</option>
                  <option value="vegetative">Vegetative</option>
                  <option value="tillering">Tillering</option>
                  <option value="flowering">Flowering</option>
                  <option value="grain_filling">Grain Filling</option>
                  <option value="maturity">Maturity</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  {t.soil_type}
                </label>
                <select
                  value={editingField.soil_type || 'red_sandy_loam'}
                  onChange={(e) => setEditingField({ ...editingField, soil_type: e.target.value })}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                >
                  <option value="red_sandy_loam">Red Sandy Loam (Alfisols)</option>
                  <option value="clay_loam">Clay Loam</option>
                  <option value="sandy_clay">Sandy Clay</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  {t.irrigation_method}
                </label>
                <select
                  value={editingField.irrigation_type || 'rainfed'}
                  onChange={(e) => setEditingField({ ...editingField, irrigation_type: e.target.value })}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                >
                  <option value="rainfed">Rainfed Dryland</option>
                  <option value="protective_drip">Protective Drip</option>
                  <option value="furrow">Furrow Irrigation</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '10px' }}>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                style={{ padding: '8px 14px', borderRadius: '6px', border: '1px solid #cbd5e1', cursor: 'pointer' }}
              >
                {t.cancel}
              </button>
              <button
                type="submit"
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  backgroundColor: '#166534',
                  color: '#ffffff',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {t.btn_save}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

