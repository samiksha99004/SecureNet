/**
 * SecureNet — Account Page
 *
 * Displays the authenticated user's profile, account metadata,
 * and security settings (password change).
 *
 * All data comes from AuthContext — no fabricated values.
 * Password change is hidden for Google OAuth users.
 */

import { MainLayout } from '../components/layout/MainLayout';
import { PageHeader } from '../components/common/PageHeader';
import { ProfileCard } from '../components/account/ProfileCard';
import { AccountInfoCard } from '../components/account/AccountInfoCard';
import { ChangePasswordCard } from '../components/account/ChangePasswordCard';
import { useAuth } from '../contexts/AuthContext';
import { LoadingState } from '../components/common/LoadingState';
import styles from './AccountPage.module.css';

export function AccountPage() {
  const { user, status } = useAuth();

  if (status === 'loading' || status === 'idle') {
    return (
      <MainLayout title="Account">
        <LoadingState message="Loading account…" />
      </MainLayout>
    );
  }

  if (!user) {
    return (
      <MainLayout title="Account">
        <div className={styles.page}>
          <PageHeader title="Account" />
          <p className={styles.unavailable}>Account information not available.</p>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout title="Account">
      <div className={styles.page}>
        <PageHeader
          title="Account"
          description="View your profile, account details, and security settings."
        />

        {/* Profile summary */}
        <ProfileCard user={user} />

        {/* Two-column grid on wide screens */}
        <div className={styles.grid}>
          <AccountInfoCard user={user} />
          <ChangePasswordCard user={user} />
        </div>
      </div>
    </MainLayout>
  );
}
