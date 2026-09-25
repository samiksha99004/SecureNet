/**
 * SecureNet — Preferences tab (every user)
 *
 * Personal app settings, saved on this device immediately:
 *   theme (dark / light), notifications on/off, notification sound,
 *   desktop notifications. Attack emails go to every registered user.
 */

import { Moon, Sun } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useNotifications } from '../../contexts/NotificationContext';
import { playAlertSound } from '../../utils/alertChannels';
import { useTheme, type Theme } from '../../utils/theme';
import { SettingsSection } from './SettingsSection';
import { SettingsField } from './SettingsField';
import styles from './TabShared.module.css';
import local from './PreferencesTab.module.css';

const THEMES: { id: Theme; label: string; icon: typeof Moon }[] = [
  { id: 'dark', label: 'Dark', icon: Moon },
  { id: 'light', label: 'Peach', icon: Sun },
];

export function PreferencesTab() {
  const { user } = useAuth();
  const [theme, setTheme] = useTheme();
  const { prefs, setPrefs, desktopPermission, enableDesktopNotifications } = useNotifications();

  return (
    <div className={styles.tabContent}>
      <SettingsSection title="Appearance" description="Choose how SecureNet looks on this device.">
        <SettingsField id="pref-theme" label="Theme" hint="Dark, or the light peach theme." type="custom">
          <div className={local.themeGroup} role="radiogroup" aria-label="Theme">
            {THEMES.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                role="radio"
                aria-checked={theme === id}
                className={`${local.themeButton} ${theme === id ? local.themeActive : ''}`}
                onClick={() => setTheme(id)}
              >
                <Icon size={15} aria-hidden="true" />
                {label}
              </button>
            ))}
          </div>
        </SettingsField>
      </SettingsSection>

      <SettingsSection
        title="Notifications"
        description="How attack alerts reach you while SecureNet is open. Saved on this device."
      >
        <SettingsField
          id="pref-notifications"
          label="Notifications"
          hint="Show an alert on screen (and on the desktop when SecureNet is in the background) when an attack is detected."
          type="toggle"
          checked={prefs.popups}
          onChange={(v) => setPrefs({ popups: v })}
        />
        <SettingsField
          id="pref-sound"
          label="Notification Sound"
          hint="Play a tone for medium and high severity attacks."
          type="toggle"
          checked={prefs.sound}
          onChange={(v) => setPrefs({ sound: v })}
        />
        <SettingsField id="pref-sound-test" label="Test Sound" hint="Hear the alert tone." type="custom">
          <button type="button" className={local.button} onClick={() => playAlertSound('high')} disabled={!prefs.sound}>
            Play
          </button>
        </SettingsField>
        <SettingsField
          id="pref-desktop"
          label="Desktop Notifications"
          hint={
            desktopPermission === 'granted'
              ? 'Allowed by the browser.'
              : desktopPermission === 'denied'
              ? 'Blocked by the browser — allow notifications for this site in the browser settings.'
              : desktopPermission === 'unsupported'
              ? 'This browser does not support desktop notifications.'
              : 'Allow the browser to show SecureNet alerts on your desktop.'
          }
          type="custom"
        >
          <button
            type="button"
            className={local.button}
            onClick={() => void enableDesktopNotifications()}
            disabled={desktopPermission !== 'default'}
          >
            {desktopPermission === 'granted' ? 'Allowed' : 'Allow'}
          </button>
        </SettingsField>
      </SettingsSection>

      <SettingsSection
        title="Email Alerts"
        description="Every registered user is emailed when an attack is detected, with the incident report attached."
      >
        <p className={local.note}>
          Alerts are sent to <strong>{user?.email}</strong>.
        </p>
      </SettingsSection>
    </div>
  );
}
