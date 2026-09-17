/**
 * SecureNet — ProtectionTab
 *
 * Settings tab for auto-block configuration.
 * 
 * Note: Protection mode is automatically enabled when IDS is ON.
 * This tab only configures auto-blocking behavior.
 */

import { useCallback, useEffect, useState } from 'react';
import { useAsyncData } from '../../hooks/useAsyncData';
import { useToast } from '../common/Toast';
import { getProtectionSettings, updateProtectionSettings } from '../../services/settingsService';
import type { ProtectionSettings } from '../../types/settings.types';
import { SettingsSection } from './SettingsSection';
import { SettingsField } from './SettingsField';
import { SaveBar } from './SaveBar';
import { LoadingState } from '../common/LoadingState';
import { ErrorState } from '../common/ErrorState';
import styles from './TabShared.module.css';

export function ProtectionTab() {
  const { showToast } = useToast();
  const { data, isLoading, isError, refetch } = useAsyncData(
    useCallback(() => getProtectionSettings(), [])
  );

  const [local, setLocal] = useState<ProtectionSettings | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (data) {
      setLocal(data);
      setIsDirty(false);
    }
  }, [data]);

  function update<K extends keyof ProtectionSettings>(key: K, value: ProtectionSettings[K]) {
    setLocal((prev) => prev ? { ...prev, [key]: value } : prev);
    setIsDirty(true);
  }

  async function handleSave() {
    if (!local) return;
    setIsSaving(true);
    try {
      await updateProtectionSettings(local);
      setIsDirty(false);
      showToast({ message: 'Protection settings saved.', variant: 'success' });
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

  if (isLoading) return <LoadingState message="Loading protection settings…" />;
  if (isError || !local) {
    return (
      <ErrorState
        title="Settings unavailable"
        message="Protection settings could not be loaded. The backend API is not yet connected."
        onRetry={refetch}
      />
    );
  }

  return (
    <div className={styles.tabContent}>
      <SettingsSection
        title="Protection Configuration"
        description="Configure automatic threat blocking behavior. Protection is automatically active when IDS is ON."
      >
        <SettingsField
          id="prot-notify-block"
          label="Notify on Block"
          hint="Send a notification whenever a flow is blocked."
          type="toggle"
          checked={local.notifyOnBlock}
          onChange={(v) => update('notifyOnBlock', v)}
        />
      </SettingsSection>

      <SettingsSection
        title="Auto-Block"
        description="Automatically block source IPs based on detection severity."
      >
        <SettingsField
          id="prot-autoblock"
          label="Enable Auto-Block"
          hint="Automatically block IPs that trigger high-severity detections."
          type="toggle"
          checked={local.autoBlock}
          onChange={(v) => update('autoBlock', v)}
        />
        <SettingsField
          id="prot-block-duration"
          label="Block Duration (seconds)"
          hint="How long an IP remains blocked before it is automatically unblocked."
          type="number"
          value={local.blockDurationSeconds}
          onChange={(v) => update('blockDurationSeconds', parseInt(v, 10) || 0)}
          min={1}
          disabled={!local.autoBlock}
        />
        <SettingsField
          id="prot-max-blocked"
          label="Max Blocked IPs"
          hint="Maximum number of IPs that can be blocked simultaneously."
          type="number"
          value={local.maxBlockedIps}
          onChange={(v) => update('maxBlockedIps', parseInt(v, 10) || 0)}
          min={1}
          disabled={!local.autoBlock}
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
