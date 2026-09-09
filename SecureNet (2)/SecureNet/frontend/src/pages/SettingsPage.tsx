/**
 * IDS Application — Settings Page
 *
 * Settings tabs:
 *   Notifications — email alert configuration
 *   Whitelist     — trusted IP / CIDR / port / protocol entries
 *   Model         — ML model information (read-only)
 *   System        — data retention, timezone, debug
 *
 * Note: Detection and Protection modes are removed.
 * IDS has only ONE control: ON/OFF (see Dashboard).
 * When ON, detection and protection are both automatically active.
 */

import { Bell, List, Cpu, Server } from 'lucide-react';
import { MainLayout } from '../components/layout/MainLayout';
import { PageHeader } from '../components/common/PageHeader';
import { SettingsLayout, type SettingsTab } from '../components/settings/SettingsLayout';
import { NotificationsTab } from '../components/settings/NotificationsTab';
import { WhitelistTab }    from '../components/settings/WhitelistTab';
import { ModelTab }        from '../components/settings/ModelTab';
import { SystemTab }       from '../components/settings/SystemTab';
import { useLocalStorage } from '../hooks/useLocalStorage';
import styles from './SettingsPage.module.css';

const TABS: SettingsTab[] = [
  { id: 'notifications', label: 'Notifications', icon: <Bell   size={15} /> },
  { id: 'whitelist',     label: 'Whitelist',     icon: <List   size={15} /> },
  { id: 'model',         label: 'Model',         icon: <Cpu    size={15} /> },
  { id: 'system',        label: 'System',        icon: <Server size={15} /> },
];

export function SettingsPage() {
  const [activeTab, setActiveTab] = useLocalStorage<string>(
    'sn_settings_tab',
    'notifications'
  );

  function renderTab() {
    switch (activeTab) {
      case 'notifications': return <NotificationsTab />;
      case 'whitelist':     return <WhitelistTab />;
      case 'model':         return <ModelTab />;
      case 'system':        return <SystemTab />;
      default:              return <NotificationsTab />;
    }
  }

  return (
    <MainLayout title="Settings">
      <div className={styles.page}>
        <PageHeader
          title="Settings"
          description="Configure notifications, whitelist, and system behavior. IDS control (ON/OFF) is on the Dashboard."
        />

        <SettingsLayout
          tabs={TABS}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        >
          {renderTab()}
        </SettingsLayout>
      </div>
    </MainLayout>
  );
}
