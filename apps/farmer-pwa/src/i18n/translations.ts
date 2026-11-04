/**
 * Complete Bilingual Translations Dictionary (English & Kannada / ಕನ್ನಡ)
 * Specially designed for smallholder farmers in Karnataka Zone 5 (Kolar/Chikkaballapur).
 */

export type Language = 'en' | 'kn';

export const TRANSLATIONS = {
  en: {
    app_title: 'AgriKafka Farmer Advisory',
    app_subtitle: 'Real-Time Field Health & Decision Support',
    switch_lang: 'ಕನ್ನಡ',
    online: 'Online',
    offline: 'Offline (Cached)',
    welcome_farmer: 'Welcome, Farmer',
    active_parcel: 'Active Parcel',
    change_parcel: 'Switch Field',
    nav_fields: 'Fields',
    nav_overview: 'Overview',
    nav_trends: 'Trends',
    nav_alerts: 'Alerts',
    nav_advisories: 'Advisories',
    nav_history: 'History',
    
    // Status badges
    status_healthy: 'Healthy & Valid',
    status_degraded: 'Check Sensor',
    status_stale: 'Data Delayed',
    status_fresh: 'Fresh Live Data',
    provenance_physical: 'Ground Soil Probe',
    provenance_station: 'Regional Weather Station',
    provenance_model: 'Satellite / Model',
    
    // Growth stages
    stage_germination: 'Germination',
    stage_vegetative: 'Vegetative Growth',
    stage_tillering: 'Tillering',
    stage_flowering: 'Flowering Stage',
    stage_grain_filling: 'Grain Filling',
    stage_maturity: 'Maturity',
    stage_harvested: 'Harvested',

    // Telemetry labels
    soil_moisture: 'Soil Moisture',
    soil_moisture_sub: 'Root-Zone (0–50cm)',
    temperature: 'Air Temperature',
    humidity: 'Relative Humidity',
    csi_stress: 'Crop Stress Index',
    last_updated: 'Last Updated',
    critical_threshold: 'FAO-56 Dry Threshold',
    
    // Alerts & Evidence
    alert_inbox: 'Agricultural Risk Alerts',
    no_alerts: 'No active risk alerts. Field conditions are favorable.',
    severity_high: 'High Risk',
    severity_critical: 'Critical Alert',
    severity_medium: 'Moderate Risk',
    severity_low: 'Low Advisory',
    why_it_matters: 'Why This Matters for Your Crop',
    corroborating_evidence: 'Observed Field Evidence',

    // Multi-Agent Section
    multi_agent_title: 'Field Investigation Progress',
    multi_agent_subtitle: 'Assisting agents examine sensor trustworthiness and agronomic publications',
    agent_sensor: '1. Checking Measurement Reliability',
    agent_context: '2. Reviewing Field & Soil Context',
    agent_risk: '3. Analysing Crop Stress Severity',
    agent_knowledge: '4. Checking Agronomic References',
    agent_critic: '5. Reviewing Advisory for Safety',
    agent_disclaimer: 'Notice: Automated agents assist field investigations with scientific citations. They do not replace local agricultural expert judgement.',
    citations_title: 'Scientific Evidence References',

    // Advisory Card & Human Review
    advisory_title: 'Agronomic Recommendation',
    proposed_action: 'Recommended Action',
    urgency_label: 'Urgency Level',
    assumptions_label: 'Field Assumptions',
    limitations_label: 'Known Limitations',
    uncertainty_label: 'Confidence & Uncertainty',
    btn_approve: 'Approve & Apply Action',
    btn_reject: 'Reject / Not Feasible',
    btn_inspect: 'Request Inspection',
    btn_acknowledge: 'Acknowledge Notice',
    feedback_title: 'Did this action help your field?',
    feedback_outcome: 'Outcome Observed',
    feedback_comments: 'Optional Farmer Notes',
    btn_submit_feedback: 'Submit Field Feedback',
    action_recorded: 'Your decision has been recorded securely.',
    
    // Field Setup
    register_field: 'Register New Parcel',
    edit_field: 'Edit Field Details',
    field_name: 'Parcel Name',
    crop_variety: 'Crop & Variety',
    sowing_date: 'Sowing / Transplant Date',
    soil_type: 'Soil Type',
    irrigation_method: 'Irrigation Setup',
    btn_save: 'Save Profile',
    cancel: 'Cancel',
  },
  kn: {
    app_title: 'ಅಗ್ರಿಕಾಫ್ಕಾ ಕೃಷಿ ಸಲಹೆಗಾರ',
    app_subtitle: 'ನೈಜ-ಸಮಯದ ಬೆಳೆ ಸಂರಕ್ಷಣೆ ಮತ್ತು ಸಲಹಾ ಸೇವೆ',
    switch_lang: 'English',
    online: 'ಆನ್‌ಲೈನ್',
    offline: 'ಆಫ್‌ಲೈನ್ (ಸಂಗ್ರಹಿತ)',
    welcome_farmer: 'ಸ್ವಾಗತ, ರೈತ ಮಿತ್ರರೆ',
    active_parcel: 'ಪ್ರಸ್ತುತ ಜಮೀನು',
    change_parcel: 'ಜಮೀನು ಬದಲಾಯಿಸಿ',
    nav_fields: 'ಜಮೀನುಗಳು',
    nav_overview: 'ಪ್ರಸ್ತುತ ಸ್ಥಿತಿ',
    nav_trends: 'ಬದಲಾವಣೆ',
    nav_alerts: 'ಎಚ್ಚರಿಕೆಗಳು',
    nav_advisories: 'ಸಲಹೆಗಳು',
    nav_history: 'ಇತಿಹಾಸ',
    
    // Status badges
    status_healthy: 'ಉತ್ತಮ ಮತ್ತು ವಿಶ್ವಾಸಾರ್ಹ',
    status_degraded: 'ಸಂವೇದಕ ಪರೀಕ್ಷಿಸಿ',
    status_stale: 'ಮಾಹಿತಿ ವಿಳಂಬವಾಗಿದೆ',
    status_fresh: 'ತಾಜಾ ನೈಜ ಮಾಹಿತಿ',
    provenance_physical: 'ನೆಲದ ಮಣ್ಣಿನ ಸಂವೇದಕ',
    provenance_station: 'ಪ್ರಾದೇಶಿಕ ಹವಾಮಾನ ಕೇಂದ್ರ',
    provenance_model: 'ಉಪಗ್ರಹ / ಮಾದರಿ',
    
    // Growth stages
    stage_germination: 'ಮೊಳಕೆಯೊಡೆಯುವಿಕೆ',
    stage_vegetative: 'ಸಸ್ಯೀಯ ಬೆಳವಣಿಗೆ',
    stage_tillering: 'ಕವಲೊಡೆಯುವ ಹಂತ',
    stage_flowering: 'ಹೂಬಿಡುವ ಹಂತ',
    stage_grain_filling: 'ಕಾಳು ತುಂಬುವ ಹಂತ',
    stage_maturity: 'ಪಕ್ವತೆಯ ಹಂತ',
    stage_harvested: 'ಕಟಾವು ಮುಗಿದಿದೆ',

    // Telemetry labels
    soil_moisture: 'ಮಣ್ಣಿನ ತೇವಾಂಶ',
    soil_moisture_sub: 'ಬೇರಿನ ವಲಯ (0–50 ಸೆಂ.ಮೀ)',
    temperature: 'ಗಾಳಿಯ ತಾಪಮಾನ',
    humidity: 'ಸಾಪೇಕ್ಷ ಆರ್ದ್ರತೆ',
    csi_stress: 'ಬೆಳೆ ಒತ್ತಡದ ಸೂಚ್ಯಂಕ',
    last_updated: 'ಕೊನೆಯ ನವೀಕರಣ',
    critical_threshold: 'ಎಫ್‌ಎಒ-56 ಒಣ ಮಿತಿ',
    
    // Alerts & Evidence
    alert_inbox: 'ಕೃಷಿ ಅಪಾಯದ ಎಚ್ಚರಿಕೆಗಳು',
    no_alerts: 'ಯಾವುದೇ ಅಪಾಯದ ಎಚ್ಚರಿಕೆಗಳಿಲ್ಲ. ಬೆಳೆಯ ಪರಿಸ್ಥಿತಿ ಉತ್ತಮವಾಗಿದೆ.',
    severity_high: 'ಹೆಚ್ಚಿನ ಅಪಾಯ',
    severity_critical: 'ತೀವ್ರ ಎಚ್ಚರಿಕೆ',
    severity_medium: 'ಮಧ್ಯಮ ಅಪಾಯ',
    severity_low: 'ಸಾಮಾನ್ಯ ಸಲಹೆ',
    why_it_matters: 'ಇದು ನಿಮ್ಮ ಬೆಳೆಗೆ ಏಕೆ ಮುಖ್ಯ?',
    corroborating_evidence: 'ಕ್ಷೇತ್ರದಲ್ಲಿ ಕಂಡುಬಂದ ಸಾಕ್ಷ್ಯಗಳು',

    // Multi-Agent Section
    multi_agent_title: 'ಕ್ಷೇತ್ರ ತನಿಖೆಯ ಹಂತಗಳು',
    multi_agent_subtitle: 'ಸ್ವಾಯತ್ತ ಸಹಾಯಕರು ಸಂವೇದಕ ನಿಖರತೆ ಮತ್ತು ಕೃಷಿ ಗ್ರಂಥಗಳನ್ನು ಪರಿಶೀಲಿಸುತ್ತಾರೆ',
    agent_sensor: '೧. ಅಳತೆಯ ನಿಖರತೆ ಪರಿಶೀಲನೆ',
    agent_context: '೨. ಜಮೀನು ಮತ್ತು ಮಣ್ಣಿನ ಮಾಹಿತಿ ಪರಿಶೀಲನೆ',
    agent_risk: '೩. ಬೆಳೆ ಒತ್ತಡದ ಗಂಭೀರತೆ ವಿಶ್ಲೇಷಣೆ',
    agent_knowledge: '೪. ಅಧಿಕೃತ ಕೃಷಿ ಸಂಶೋಧನಾ ಸಾಹಿತ್ಯ ಪರಿಶೀಲನೆ',
    agent_critic: '೫. ಸಲಹೆಯ ಸುರಕ್ಷತೆಯ ಮರುಪರಿಶೀಲನೆ',
    agent_disclaimer: 'ಸೂಚನೆ: ಸ್ವಯಂಚಾಲಿತ ಸಹಾಯಕರು ವೈಜ್ಞಾನಿಕ ಆಧಾರಗಳೊಂದಿಗೆ ಸಲಹೆ ನೀಡಲು ನೆರವಾಗುತ್ತಾರೆ. ಇದು ಸ್ಥಳೀಯ ಕೃಷಿ ವಿಜ್ಞಾನಿಗಳ ತೀರ್ಪಿಗೆ ಬದಲಿಯಾಗಿರುವುದಿಲ್ಲ.',
    citations_title: 'ವೈಜ್ಞಾನಿಕ ಆಧಾರ ಉಲ್ಲೇಖಗಳು',

    // Advisory Card & Human Review
    advisory_title: 'ಕೃಷಿ ತಜ್ಞರ ಶಿಫಾರಸು',
    proposed_action: 'ಶಿಫಾರಸು ಮಾಡಿದ ಕ್ರಮ',
    urgency_label: 'ತುರ್ತು ಮಟ್ಟ',
    assumptions_label: 'ಕ್ಷೇತ್ರದ ಊಹೆಗಳು',
    limitations_label: 'ತಿಳಿದಿರುವ ಮಿತಿಗಳು',
    uncertainty_label: 'ವಿಶ್ವಾಸಾರ್ಹತೆ ಮತ್ತು ಅನಿಶ್ಚಿತತೆ',
    btn_approve: 'ಒಪ್ಪಿಕೊಳ್ಳಿ ಮತ್ತು ಅನ್ವಯಿಸಿ',
    btn_reject: 'ತಿರಸ್ಕರಿಸಿ / ಅಸಾಧ್ಯ',
    btn_inspect: 'ಕ್ಷೇತ್ರ ತಪಾಸಣೆ ಕೋರಿಕೆ',
    btn_acknowledge: 'ಸ್ವೀಕರಿಸಿ',
    feedback_title: 'ಈ ಕ್ರಮವು ನಿಮ್ಮ ಬೆಳೆಗೆ ಸಹಾಯವಾಯಿತೇ?',
    feedback_outcome: 'ಕಂಡುಬಂದ ಫಲಿತಾಂಶ',
    feedback_comments: 'ರೈತರ ಟಿಪ್ಪಣಿಗಳು',
    btn_submit_feedback: 'ಪ್ರತಿಕ್ರಿಯೆ ಸಲ್ಲಿಸಿ',
    action_recorded: 'ನಿಮ್ಮ ನಿರ್ಧಾರವನ್ನು ಯಶಸ್ವಿಯಾಗಿ ದಾಖಲಿಸಲಾಗಿದೆ.',
    
    // Field Setup
    register_field: 'ಹೊಸ ಜಮೀನು ನೋಂದಾಯಿಸಿ',
    edit_field: 'ಜಮೀನಿನ ವಿವರ ಬದಲಾಯಿಸಿ',
    field_name: 'ಜಮೀನಿನ ಹೆಸರು',
    crop_variety: 'ಬೆಳೆ ಮತ್ತು ತಳಿ',
    sowing_date: 'ಬಿತ್ತನೆ ದಿನಾಂಕ',
    soil_type: 'ಮಣ್ಣಿನ ವಿಧ',
    irrigation_method: 'ನೀರಾವರಿ ವ್ಯವಸ್ಥೆ',
    btn_save: 'ಉಳಿಸಿ',
    cancel: 'ರದ್ದುಮಾಡಿ',
  }
};

