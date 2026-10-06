/**
 * SecureNet — verdict wording
 *
 * The model's job is to say whether traffic is normal or abnormal. Which attack it
 * might be is only stage 2's guess, so it is always shown as a "possible attack".
 */

import type { AttackGuess, SecurityEvent } from '../types/security.types';

export const ABNORMAL_TRAFFIC = 'Abnormal traffic detected';
export const NORMAL_TRAFFIC = 'Normal traffic';

const BENIGN = new Set(['benign', 'normal']);

export function percent(p: number, digits = 0): string {
  return `${(p * 100).toFixed(digits)}%`;
}

/** Guesses worth showing (≥ 0.5 %), most likely first. */
export function guessesOf(event: Pick<SecurityEvent, 'attackGuesses'>): AttackGuess[] {
  return [...(event.attackGuesses ?? [])]
    .filter((g) => typeof g.probability === 'number' && g.probability >= 0.005)
    .sort((a, b) => b.probability - a.probability);
}

/** The model's best guess of which attack it might be, e.g. "DDoS (97%)". */
export function possibleAttack(
  event: Pick<SecurityEvent, 'attackType' | 'confidence' | 'attackGuesses'>,
): string {
  if (event.attackType) {
    return event.confidence != null ? `${event.attackType} (${percent(event.confidence)})` : event.attackType;
  }
  const guess = guessesOf(event).find((g) => !BENIGN.has(g.label.toLowerCase()));
  return guess ? `${guess.label} (${percent(guess.probability)}, unsure)` : 'Unknown';
}

/** Name shown for a stage-2 class in the guess table. */
export function guessLabel(label: string): string {
  return BENIGN.has(label.toLowerCase()) ? 'Benign — not an attack' : label;
}
