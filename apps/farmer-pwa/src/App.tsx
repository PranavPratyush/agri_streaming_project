import React, { useEffect, useState } from 'react';
import {
  AdvisoryProposal,
  AgentHandoffSummary,
  CandidateAlert,
  CitationReference,
  FieldProfile,
  FieldStatus,
  FieldTrends,
  InvestigationSummary,
  ObservationRecord,
  SensorFreshness,
} from './types/api';
import { api } from './services/api';
import { Language } from './i18n/translations';
import { Header } from './components/common/Header';
import { Navbar, ScreenId } from './components/common/Navbar';
import { OverviewScreen } from './components/screens/OverviewScreen';
import { TrendsScreen } from './components/screens/TrendsScreen';
import { AlertsScreen } from './components/screens/AlertsScreen';
import { AdvisoriesScreen } from './components/screens/AdvisoriesScreen';
import { FieldsScreen } from './components/screens/FieldsScreen';
import { HistoryScreen } from './components/screens/HistoryScreen';
import { OnboardingScreen } from './components/screens/OnboardingScreen';

export const App: React.FC = () => {
  const [lang, setLang] = useState<Language>(() => {
    return (localStorage.getItem('agrikafka_lang') as Language) || 'en';
  });
  const [activeScreen, setActiveScreen] = useState<ScreenId>('overview');
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [isOnboarding, setIsOnboarding] = useState<boolean>(() => {
    return !localStorage.getItem('agrikafka_onboarding_done');
  });

  // State data
  const [fields, setFields] = useState<FieldProfile[]>([]);
  const [activeFieldId, setActiveFieldId] = useState<string>(() => api.getActiveFieldId());
  const [currentField, setCurrentField] = useState<FieldProfile | null>(null);
  const [fieldStatus, setFieldStatus] = useState<FieldStatus | null>(null);
  const [observations, setObservations] = useState<ObservationRecord[]>([]);
  const [sensorFreshness, setSensorFreshness] = useState<SensorFreshness[]>([]);
  const [trends, setTrends] = useState<FieldTrends | null>(null);
  const [alerts, setAlerts] = useState<CandidateAlert[]>([]);
  const [advisories, setAdvisories] = useState<AdvisoryProposal[]>([]);
  const [investigation, setInvestigation] = useState<InvestigationSummary | null>(null);
  const [agentMessages, setAgentMessages] = useState<AgentHandoffSummary[]>([]);
  const [citations, setCitations] = useState<CitationReference[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Monitor network status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Save language preference
  const toggleLanguage = () => {
    const nextLang = lang === 'en' ? 'kn' : 'en';
    setLang(nextLang);
    localStorage.setItem('agrikafka_lang', nextLang);
  };

  // Load field and streaming data
  const loadFieldData = async (fieldId: string) => {
    setIsLoading(true);
    try {
      const allFields = await api.getFields();
      setFields(allFields);

      const profile = await api.getFieldProfile(fieldId);
      setCurrentField(profile);

      const status = await api.getFieldStatus(fieldId);
      setFieldStatus(status);

      const obs = await api.getObservations(fieldId);
      setObservations(obs);

      const freshness = await api.getSensorFreshness();
      setSensorFreshness(freshness);

      const tr = await api.getTrends(fieldId);
      setTrends(tr);

      const alts = await api.getAlerts(fieldId);
      setAlerts(alts);

      const advs = await api.getAdvisories(fieldId);
      setAdvisories(advs);

      // Load multi-agent investigation details for active alert
      if (alts.length > 0) {
        const invSummary = await api.getInvestigationSummary('run-kolar-inv-001');
        setInvestigation(invSummary);

        const msgs = await api.getInvestigationMessages('run-kolar-inv-001');
        setAgentMessages(msgs);

        const cites = await api.getInvestigationCitations('run-kolar-inv-001');
        setCitations(cites);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadFieldData(activeFieldId);
  }, [activeFieldId]);

  const handleSelectField = (fieldId: string) => {
    setActiveFieldId(fieldId);
    api.setFarmerContext(fieldId);
    loadFieldData(fieldId);
    setActiveScreen('overview');
  };

  const handleSaveField = async (updated: Partial<FieldProfile>) => {
    if (currentField) {
      await api.updateFieldProfile(currentField.field_id, updated);
      await loadFieldData(currentField.field_id);
      return true;
    }
    return false;
  };

  const handleAdvisoryAction = async (
    recommendationId: string,
    action: 'APPROVE' | 'REJECT' | 'REQUEST_INSPECTION' | 'ACKNOWLEDGE',
    comments?: string
  ) => {
    const ok = await api.submitAdvisoryAction(recommendationId, {
      action,
      reviewer_id: `farmer-${activeFieldId}`,
      comments,
    });
    if (ok) {
      // Reload advisories to show updated state
      const updated = await api.getAdvisories(activeFieldId);
      setAdvisories(updated);
    }
    return ok;
  };

  const handleSubmitFeedback = async (
    recommendationId: string,
    rating: number,
    actionTaken: boolean,
    comments: string
  ) => {
    return await api.submitFeedback({
      recommendation_id: recommendationId,
      field_id: activeFieldId,
      rating,
      action_taken: actionTaken,
      feedback_comments: comments,
    });
  };

  const handleCompleteOnboarding = (fieldId: string, role: string) => {
    localStorage.setItem('agrikafka_onboarding_done', 'true');
    api.setFarmerContext(fieldId, role);
    setActiveFieldId(fieldId);
    setIsOnboarding(false);
    loadFieldData(fieldId);
  };

  if (isOnboarding) {
    return (
      <div className="app-container">
        <OnboardingScreen
          onCompleteOnboarding={handleCompleteOnboarding}
          lang={lang}
          onToggleLang={toggleLanguage}
        />
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Header */}
      <Header
        currentFieldId={currentField?.name || activeFieldId}
        onOpenFieldSelect={() => setActiveScreen('fields')}
        lang={lang}
        onToggleLang={toggleLanguage}
        isOnline={isOnline}
      />

      {/* Main Content Area */}
      <main id="main-content" tabIndex={-1} style={{ flex: 1, outline: 'none' }}>
        {activeScreen === 'overview' && currentField && fieldStatus && (
          <OverviewScreen
            field={currentField}
            status={fieldStatus}
            observations={observations}
            sensorFreshness={sensorFreshness}
            lang={lang}
            onNavigateToAlerts={() => setActiveScreen('alerts')}
            onNavigateToAdvisories={() => setActiveScreen('advisories')}
          />
        )}

        {activeScreen === 'trends' && currentField && trends && (
          <TrendsScreen field={currentField} trends={trends} lang={lang} />
        )}

        {activeScreen === 'alerts' && currentField && (
          <AlertsScreen
            field={currentField}
            alerts={alerts}
            investigation={investigation}
            agentMessages={agentMessages}
            citations={citations}
            lang={lang}
            onNavigateToAdvisories={() => setActiveScreen('advisories')}
          />
        )}

        {activeScreen === 'advisories' && currentField && (
          <AdvisoriesScreen
            field={currentField}
            advisories={advisories}
            onAction={handleAdvisoryAction}
            onSubmitFeedback={handleSubmitFeedback}
            lang={lang}
          />
        )}

        {activeScreen === 'fields' && (
          <FieldsScreen
            fields={fields}
            activeFieldId={activeFieldId}
            onSelectField={handleSelectField}
            onSaveField={handleSaveField}
            lang={lang}
          />
        )}

        {activeScreen === 'history' && currentField && (
          <HistoryScreen field={currentField} lang={lang} />
        )}
      </main>

      {/* Mobile-Friendly Navigation Bar */}
      <Navbar
        activeScreen={activeScreen}
        onSelectScreen={setActiveScreen}
        lang={lang}
        unreadAlertsCount={alerts.length}
        pendingAdvisoriesCount={advisories.filter((a) => a.approval_status === 'PROPOSED').length}
      />
    </div>
  );
};

