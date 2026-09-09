/**
 * SecureNet — NotificationsTab
 *
 * Settings tab for email notification configuration.
 */

import { useCallback, useEffect, useState } from 'react';
import { useAsyncData } from '../../hooks/useAsyncData';
import { useToast } from '../common/Toast';
import { getNotificationSettings, updateNotificationSettings } from '../../services/settingsService';
import type { NotificationSettings } from '../../types/settings.types';
import { SettingsSection } from './SettingsSection';
import { SettingsField } from './SettingsField';
import { SaveBar } from './SaveBar';
import { LoadingState } from '../common/LoadingState';
import { ErrorState } from '../common/ErrorState';
import styles from './TabShared.module.css';

export function NotificationsTab() {
  const { showToast } = useToast();
  const { data, isLoading, isError, refetch } = useAsyncData(
    useCallback(() => getNotificationSettings(), [])
  );

  const [local, setLocal] = useState<NotificationSettings | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (data) {
      setLocal(data);
      setIsDirty(false);
    }
  }, [data]);

  function update<K extends keyof NotificationSettings>(key: K, value: NotificationSettings[K]) {
    setLocal((prev) => prev ? { ...prev, [key]: value } : prev);
    setIsDirty(true);
  }

  async function handleSave() {
    if (!local) return;
    setIsSaving(true);
    try {
      await updateNotificationSettings(local);
      setIsDirty(false);
      showToast({ message: 'Notification settings saved.', variant: 'success' });
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

  if (isLoading) return <LoadingState message="Loading notification settings…" />;
  if (isError || !local) {
    return (
      <ErrorState
        title="Settings unavailable"
        message="Notification settings could not be loaded. The backend API is not yet connected."
        onRetry={refetch}
      />
    );
  }

  return (
    <div className={styles.tabContent}>
      <SettingsSection
        title="Email Notifications"
        description="Configure where alerts and digests are delivered."
      >
        <SettingsField
          id="notif-email-enabled"
          label="Enable Email Notifications"
          hint="Send alert emails when security events are detected."
          type="toggle"
          checked={local.emailEnabled}
          onChange={(v) => update('emailEnabled', v)}
        />
        <SettingsField
          id="notif-email-address"
          label="Notification Email"
          hint="Email address that will receive all security alerts."
          type="email"
          value={local.emailAddress ?? ''}
          onChange={(v) => update('emailAddress', v || null)}
          disabled={!local.emailEnabled}
          placeholder="analyst@example.com"
        />
      </SettingsSection>

      <SettingsSection
        title="Alert Triggers"
        description="Choose which event severities trigger an immediate alert email."
      >
        <SettingsField
          id="notif-high"
          label="Alert on High Severity"
          hint="Send an email for every high-severity detection."
          type="toggle"
          checked={local.alertOnHigh}
          onChange={(v) => update('alertOnHigh', v)}
          disabled={!local.emailEnabled}
        />
        <SettingsField
          id="notif-medium"
          label="Alert on Medium Severity"
          hint="Send an email for every medium-severity detection."
          type="toggle"
          checked={local.alertOnMedium}
          onChange={(v) => update('alertOnMedium', v)}
          disabled={!local.emailEnabled}
        />
        <SettingsField
          id="notif-block"
          label="Alert on Block Action"
          hint="Send an email whenever an IP is automatically blocked."
          type="toggle"
          checked={local.alertOnBlock}
          onChange={(v) => update('alertOnBlock', v)}
          disabled={!local.emailEnabled}
        />
      </SettingsSection>

      <SettingsSection
        title="Digest"
        description="Receive a periodic summary of recent security activity."
      >
        <SettingsField
          id="notif-digest"
          label="Enable Digest"
          hint="Send a periodic summary email instead of (or in addition to) instant alerts."
          type="toggle"
          checked={local.digestEnabled}
          onChange={(v) => update('digestEnabled', v)}
          disabled={!local.emailEnabled}
        />
        <SettingsField
          id="notif-digest-interval"
          label="Digest Interval (hours)"
          hint="How often the digest email is sent."
          type="number"
          value={local.digestIntervalHours}
          onChange={(v) => update('digestIntervalHours', parseInt(v, 10) || 24)}
          min={1}
          max={168}
          disabled={!local.digestEnabled || !local.emailEnabled}
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
