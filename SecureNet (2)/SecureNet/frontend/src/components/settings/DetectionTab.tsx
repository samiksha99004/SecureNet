/**
 * SecureNet — DetectionTab
 *
 * Settings tab for anomaly detection configuration.
 * Loads current settings from the backend; saves via PUT.
 * Shows "Not available" for all fields when backend is not connected.
 */

import { useCallback, useEffect, useState } from 'react';
import { useAsyncData } from '../../hooks/useAsyncData';
import { useToast } from '../common/Toast';
import { getDetectionSettings, updateDetectionSettings } from '../../services/settingsService';
import type { DetectionSettings } from '../../types/settings.types';
import { SettingsSection } from './SettingsSection';
import { SettingsField } from './SettingsField';
import { SaveBar } from './SaveBar';
import { LoadingState } from '../common/LoadingState';
import { ErrorState } from '../common/ErrorState';
import styles from './TabShared.module.css';

export function DetectionTab() {
  const { showToast } = useToast();
  const { data, isLoading, isError, refetch } = useAsyncData(
    useCallback(() => getDetectionSettings(), [])
  );

  const [local, setLocal] = useState<DetectionSettings | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (data) {
      setLocal(data);
      setIsDirty(false);
    }
  }, [data]);

  function update<K extends keyof DetectionSettings>(key: K, value: DetectionSettings[K]) {
    setLocal((prev) => prev ? { ...prev, [key]: value } : prev);
    setIsDirty(true);
  }

  async function handleSave() {
    if (!local) return;
    setIsSaving(true);
    try {
      await updateDetectionSettings(local);
      setIsDirty(false);
      showToast({ message: 'Detection settings saved.', variant: 'success' });
      void refetch();
    } catch {
      showToast({ message: 'Could not save — backend not connected.', variant: 'error' });
    } finally {
      setIsSaving(false);
    }
  }

  function handleDiscard() {
    if (data) {
      setLocal(data);
      setIsDirty(false);
    }
  }

  if (isLoading) return <LoadingState message="Loading detection settings…" />;
  if (isError || !local) {
    return (
      <ErrorState
        title="Settings unavailable"
        message="Detection settings could not be loaded. The backend API is not yet connected."
        onRetry={refetch}
      />
    );
  }

  return (
    <div className={styles.tabContent}>
      <SettingsSection
        title="Anomaly Detection"
        description="Control the Isolation Forest stage-1 detection pipeline."
      >
        <SettingsField
          id="det-enabled"
          label="Enable Detection"
          hint="Pause or resume the anomaly detection engine."
          type="toggle"
          checked={local.enabled}
          onChange={(v) => update('enabled', v)}
        />
        <SettingsField
          id="det-sensitivity"
          label="Sensitivity Preset"
          hint="Adjusts threshold and analysis interval as a bundle."
          type="select"
          value={local.sensitivity}
          onChange={(v) => update('sensitivity', v as DetectionSettings['sensitivity'])}
          options={[
            { value: 'low',    label: 'Low — fewer alerts' },
            { value: 'medium', label: 'Medium — balanced' },
            { value: 'high',   label: 'High — maximum sensitivity' },
            { value: 'custom', label: 'Custom' },
          ]}
        />
        <SettingsField
          id="det-threshold"
          label="Anomaly Threshold"
          hint="Flows with a score above this value are flagged (0.0 – 1.0)."
          type="number"
          value={local.anomalyThreshold}
          onChange={(v) => update('anomalyThreshold', parseFloat(v) || 0)}
          min={0}
          max={1}
          step={0.01}
        />
        <SettingsField
          id="det-min-flows"
          label="Min Flows for Analysis"
          hint="Minimum number of flows required before a detection pass runs."
          type="number"
          value={local.minFlowsForAnalysis}
          onChange={(v) => update('minFlowsForAnalysis', parseInt(v, 10) || 0)}
          min={1}
        />
        <SettingsField
          id="det-interval"
          label="Analysis Interval (ms)"
          hint="How frequently the model runs a detection pass."
          type="number"
          value={local.analysisIntervalMs}
          onChange={(v) => update('analysisIntervalMs', parseInt(v, 10) || 0)}
          min={100}
          step={100}
        />
      </SettingsSection>

      <SettingsSection
        title="Stage 2 — XGBoost Classification"
        description="Control the attack-classification pipeline that runs after stage-1 flags a flow."
      >
        <SettingsField
          id="det-stage2"
          label="Enable XGBoost Stage 2"
          hint="When enabled, flagged flows are classified into attack categories."
          type="toggle"
          checked={local.stage2Enabled}
          onChange={(v) => update('stage2Enabled', v)}
        />
        <SettingsField
          id="det-stage2-confidence"
          label="Stage 2 Confidence Threshold"
          hint="Minimum XGBoost confidence to accept a classification (0.0 – 1.0)."
          type="number"
          value={local.stage2ConfidenceThreshold}
          onChange={(v) => update('stage2ConfidenceThreshold', parseFloat(v) || 0)}
          min={0}
          max={1}
          step={0.01}
          disabled={!local.stage2Enabled}
        />
      </SettingsSection>

      <SaveBar
        isDirty={isDirty}
        isSaving={isSaving}
        onSave={handleSave}
        onDiscard={handleDiscard}
      />
    </div>
  );
}
