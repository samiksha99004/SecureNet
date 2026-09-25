/**
 * SecureNet — notification helpers
 */

import type { NotificationItem } from '../types/notifications.types';

/** Display title of an alert (null attack type = unclassified anomaly). */
export function titleOf(item: Pick<NotificationItem, 'attackType'>): string {
  return item.attackType ?? 'Unclassified anomaly';
}
