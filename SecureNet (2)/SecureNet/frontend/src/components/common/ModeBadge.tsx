/**
 * SecureNet — ModeBadge Component
 *
 * Displays the detection mode: Monitor or Protect.
 */

import type { DetectionMode } from '../../types/security.types';
import { cn } from '../../utils/cn';
import styles from './ModeBadge.module.css';

interface ModeBadgeProps {
  mode: DetectionMode;
  className?: string;
}

export function ModeBadge({ mode, className }: ModeBadgeProps) {
  return (
    <span
      className={cn(styles.badge, styles[mode], className)}
      aria-label={`Mode: ${mode === 'monitor' ? 'Monitor' : 'Protect'}`}
    >
      {mode === 'monitor' ? 'Monitor' : 'Protect'}
    </span>
  );
}
