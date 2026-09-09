/**
 * SecureNet — Support Page
 *
 * Sections:
 *  - About SecureNet (system description, version, pipeline summary)
 *  - Support & Documentation (backend status, env config guidance)
 *  - Contact form (explicitly marked as unavailable until backend endpoint exists)
 */

import { MainLayout } from '../components/layout/MainLayout';
import { PageHeader } from '../components/common/PageHeader';
import { AboutCard } from '../components/support/AboutCard';
import { SupportInfoCard } from '../components/support/SupportInfoCard';
import { ContactForm } from '../components/support/ContactForm';
import styles from './SupportPage.module.css';

export function SupportPage() {
  return (
    <MainLayout title="Support">
      <div className={styles.page}>
        <PageHeader
          title="Support"
          description="System information, integration guidance, and contact options."
        />

        <div className={styles.grid}>
          {/* Left column */}
          <div className={styles.left}>
            <AboutCard />
            <SupportInfoCard />
          </div>

          {/* Right column */}
          <div className={styles.right}>
            <ContactForm />
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
