import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from '../components/common/Header';
import { Navbar } from '../components/common/Navbar';
import { Badge } from '../components/common/Badge';
import { MultiAgentProgress } from '../components/common/MultiAgentProgress';
import { OverviewScreen } from '../components/screens/OverviewScreen';
import { AdvisoriesScreen } from '../components/screens/AdvisoriesScreen';
import { FieldProfile, FieldStatus } from '../types/api';

const mockField: FieldProfile = {
  field_id: 'field-kolar-001',
  name: 'Kolar North Demonstration',
  latitude: 13.1333,
  longitude: 78.1333,
  crop_name: 'finger_millet',
  variety: 'GPU-28',
  current_growth_stage: 'flowering',
  soil_type: 'red_sandy_loam',
  soil_texture: 'sandy_clay_loam',
  field_capacity: 0.22,
  wilting_point: 0.10,
  root_zone_depth_m: 0.50,
  irrigation_type: 'rainfed',
  is_active: true,
};

const mockStatus: FieldStatus = {
  field_id: 'field-kolar-001',
  crop_variety: 'GPU-28',
  growth_stage: 'flowering',
  composite_stress_index: 0.76,
  risk_level: 'HIGH',
  sensor_health_overall: 'HEALTHY',
  latest_soil_moisture: 0.12,
  latest_ambient_temp: 31.8,
  telemetry_latency_seconds: 18.4,
  active_alerts_count: 1,
  pending_advisories_count: 1,
  data_freshness_status: 'FRESH',
};

describe('Header & Navigation Component Tests', () => {
  it('renders application title, active parcel, and toggles language to Kannada', () => {
    const toggleLang = vi.fn();
    const { rerender } = render(
      <Header
        currentFieldId="Kolar North Parcel"
        onOpenFieldSelect={vi.fn()}
        lang="en"
        onToggleLang={toggleLang}
        isOnline={true}
      />
    );

    expect(screen.getByText('AgriKafka Farmer Advisory')).toBeInTheDocument();
    expect(screen.getByText('Kolar North Parcel')).toBeInTheDocument();
    expect(screen.getByText('Online')).toBeInTheDocument();

    const switchBtn = screen.getByRole('button', { name: /switch language to ಕನ್ನಡ/i });
    fireEvent.click(switchBtn);
    expect(toggleLang).toHaveBeenCalledTimes(1);

    // Re-render in Kannada
    rerender(
      <Header
        currentFieldId="Kolar North Parcel"
        onOpenFieldSelect={vi.fn()}
        lang="kn"
        onToggleLang={toggleLang}
        isOnline={true}
      />
    );
    expect(screen.getByText('ಅಗ್ರಿಕಾಫ್ಕಾ ಕೃಷಿ ಸಲಹೆಗಾರ')).toBeInTheDocument();
    expect(screen.getByText('ಆನ್‌ಲೈನ್')).toBeInTheDocument();
  });

  it('renders mobile navbar tabs with active state and notification badges', () => {
    const selectScreen = vi.fn();
    render(
      <Navbar
        activeScreen="overview"
        onSelectScreen={selectScreen}
        lang="en"
        unreadAlertsCount={2}
        pendingAdvisoriesCount={1}
      />
    );

    expect(screen.getByRole('tab', { name: /overview/i })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();

    const alertsTab = screen.getByRole('tab', { name: /alerts/i });
    fireEvent.click(alertsTab);
    expect(selectScreen).toHaveBeenCalledWith('alerts');
  });
});

describe('Field Overview Screen Tests', () => {
  it('displays real-time telemetry with explicit units and FAO-56 threshold deficit', () => {
    render(
      <OverviewScreen
        field={mockField}
        status={mockStatus}
        observations={[
          { event_time: '', sensor_id: 's1', observed_variable: 'soil_moisture', numeric_value: 0.12, unit: 'm3/m3', provenance: 'physical_sensor', quality_flags: [] },
          { event_time: '', sensor_id: 's2', observed_variable: 'ambient_temp', numeric_value: 31.8, unit: 'celsius', provenance: 'weather_station', quality_flags: [] },
        ]}
        sensorFreshness={[]}
        lang="en"
        onNavigateToAlerts={vi.fn()}
        onNavigateToAdvisories={vi.fn()}
      />
    );

    expect(screen.getByText('Kolar North Demonstration')).toBeInTheDocument();
    expect(screen.getByText('0.12')).toBeInTheDocument();
    expect(screen.getByText('m³/m³')).toBeInTheDocument();
    expect(screen.getByText('DRY DEFICIT')).toBeInTheDocument();
    expect(screen.getByText(/Ground Soil Probe/i)).toBeInTheDocument();
    expect(screen.getByText('31.8')).toBeInTheDocument();
    expect(screen.getByText('°C')).toBeInTheDocument();
  });
});

describe('Multi-Agent Investigation Progress Component Tests', () => {
  it('renders all 5 milestones truthfully without leaking raw prompts or secrets', () => {
    const mockMessages = [
      {
        message_id: 'm1',
        from_agent: 'sensor_reliability_agent',
        to_agent: 'supervisor',
        message_type: 'task_result',
        status: 'success',
        created_at: '12:00',
        concise_summary: 'Soil probe VH400 readings verified healthy. Z-score 0.2.',
        evidence_references: [],
      },
      {
        message_id: 'm2',
        from_agent: 'critic_safety_agent',
        to_agent: 'supervisor',
        message_type: 'task_result',
        status: 'success',
        created_at: '12:02',
        concise_summary: 'Safety review passed. Chemical pesticides blocked. Physical actuation absent.',
        evidence_references: [],
      },
    ];

    const mockCitations = [
      {
        citation_id: 'CIT-FAO56-001',
        source_id: 'FAO-56',
        document_title: 'Crop Evapotranspiration',
        section_heading: 'Table 22: Millet Depletion',
        relevance_score: 0.95,
        excerpt: 'FAO-56 water requirements.',
      },
    ];

    render(
      <MultiAgentProgress
        investigation={null}
        agentMessages={mockMessages}
        citations={mockCitations}
        lang="en"
      />
    );

    // Milestones check
    expect(screen.getByText('1. Checking Measurement Reliability')).toBeInTheDocument();
    expect(screen.getByText('2. Reviewing Field & Soil Context')).toBeInTheDocument();
    expect(screen.getByText('3. Analysing Crop Stress Severity')).toBeInTheDocument();
    expect(screen.getByText('4. Checking Agronomic References')).toBeInTheDocument();
    expect(screen.getByText('5. Reviewing Advisory for Safety')).toBeInTheDocument();

    // Verifies citations and safety notice
    expect(screen.getByText(/Scientific Evidence References/i)).toBeInTheDocument();
    expect(screen.getByText(/FAO-56:/i)).toBeInTheDocument();
    expect(screen.getByRole('note')).toHaveTextContent(/do not replace local agricultural expert judgement/i);

    // Verifies no prompt or raw internal token leakage
    expect(screen.queryByText(/SYSTEM PROMPT/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/chain_of_thought/i)).not.toBeInTheDocument();
  });
});

describe('Advisory & Human Review Screen Tests', () => {
  it('renders advisory cards with human review action buttons and assumptions', () => {
    const handleAction = vi.fn().mockResolvedValue(true);
    const mockAdvisory = {
      recommendation_id: 'rec-01',
      alert_id: 'alt-01',
      field_id: 'field-kolar-001',
      approval_status: 'PROPOSED' as const,
      action_category: 'IRRIGATION' as const,
      action_title: 'Apply 25mm Protective Irrigation',
      action_body: 'Water level below threshold. Apply 20-25mm protective irrigation.',
      urgency: 'HIGH' as const,
      cited_evidence_ids: ['CIT-FAO56-001'],
      assumptions: ['Red sandy loam soil with 60cm root zone'],
      limitations: ['Assumes farm pond storage accessible'],
      confidence_score: 0.92,
      created_at: new Date().toISOString(),
    };

    render(
      <AdvisoriesScreen
        field={mockField}
        advisories={[mockAdvisory]}
        onAction={handleAction}
        onSubmitFeedback={vi.fn().mockResolvedValue(true)}
        lang="en"
      />
    );

    expect(screen.getByText('Apply 25mm Protective Irrigation')).toBeInTheDocument();
    expect(screen.getByText(/Red sandy loam soil with 60cm root zone/i)).toBeInTheDocument();

    const approveBtn = screen.getByRole('button', { name: /approve & apply action/i });
    const rejectBtn = screen.getByRole('button', { name: /reject \/ not feasible/i });
    expect(approveBtn).toBeInTheDocument();
    expect(rejectBtn).toBeInTheDocument();

    fireEvent.click(approveBtn);
    expect(handleAction).toHaveBeenCalledWith('rec-01', 'APPROVE');
  });
});
