/**
 * SecureNet — ContactForm
 *
 * Support contact form.
 *
 * Because there is no backend contact endpoint in the current API
 * specification, this form clearly states that submission is
 * unavailable. It does NOT fake a successful submission or silently
 * discard the message.
 *
 * When a contact endpoint is added to the backend, wire it through
 * a new `contactService.sendMessage()` call and remove the notice.
 */

import { useState } from 'react';
import { MessageSquare } from 'lucide-react';
import { Card } from '../common/Card';
import { isValidEmail, isNonEmpty } from '../../utils/validation';
import styles from './ContactForm.module.css';

const TOPIC_OPTIONS = [
  { value: '',          label: 'Select a topic…' },
  { value: 'bug',       label: 'Bug report' },
  { value: 'feature',   label: 'Feature request' },
  { value: 'question',  label: 'General question' },
  { value: 'other',     label: 'Other' },
];

export function ContactForm() {
  const [name, setName]       = useState('');
  const [email, setEmail]     = useState('');
  const [topic, setTopic]     = useState('');
  const [message, setMessage] = useState('');
  const [errors, setErrors]   = useState<Record<string, string>>({});

  function validate(): boolean {
    const errs: Record<string, string> = {};
    if (!isNonEmpty(name))    errs.name    = 'Name is required.';
    if (!isValidEmail(email)) errs.email   = 'Enter a valid email address.';
    if (!topic)               errs.topic   = 'Please select a topic.';
    if (!isNonEmpty(message)) errs.message = 'Message is required.';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // Validate first so users see field-level errors,
    // but we never fake a submission — the unavailable notice
    // below the button makes that clear.
    validate();
  }

  return (
    <Card padding="lg">
      <div className={styles.header}>
        <MessageSquare size={16} className={styles.headerIcon} aria-hidden="true" />
        <h3 className={styles.heading}>Contact Support</h3>
      </div>

      {/* Unavailability notice — shown prominently, not hidden */}
      <div className={styles.unavailableNotice} role="note" aria-label="Submission unavailable">
        <p className={styles.noticeTitle}>Submission currently unavailable</p>
        <p className={styles.noticeBody}>
          The contact endpoint has not been implemented on the backend yet.
          Filling in this form will not send a message. Please contact your
          system administrator directly until this feature is connected.
        </p>
      </div>

      <form onSubmit={handleSubmit} className={styles.form} noValidate>
        <div className={styles.row2}>
          {/* Name */}
          <div className={styles.fieldGroup}>
            <label htmlFor="contact-name" className={styles.label}>Your Name</label>
            <input
              id="contact-name"
              type="text"
              className={styles.input}
              value={name}
              onChange={(e) => { setName(e.target.value); setErrors((p) => ({ ...p, name: '' })); }}
              placeholder="Full name"
              autoComplete="name"
            />
            {errors.name && <p className={styles.error}>{errors.name}</p>}
          </div>

          {/* Email */}
          <div className={styles.fieldGroup}>
            <label htmlFor="contact-email" className={styles.label}>Email Address</label>
            <input
              id="contact-email"
              type="email"
              className={styles.input}
              value={email}
              onChange={(e) => { setEmail(e.target.value); setErrors((p) => ({ ...p, email: '' })); }}
              placeholder="you@example.com"
              autoComplete="email"
            />
            {errors.email && <p className={styles.error}>{errors.email}</p>}
          </div>
        </div>

        {/* Topic */}
        <div className={styles.fieldGroup}>
          <label htmlFor="contact-topic" className={styles.label}>Topic</label>
          <select
            id="contact-topic"
            className={styles.select}
            value={topic}
            onChange={(e) => { setTopic(e.target.value); setErrors((p) => ({ ...p, topic: '' })); }}
          >
            {TOPIC_OPTIONS.map((o) => (
              <option key={o.value} value={o.value} disabled={o.value === ''}>
                {o.label}
              </option>
            ))}
          </select>
          {errors.topic && <p className={styles.error}>{errors.topic}</p>}
        </div>

        {/* Message */}
        <div className={styles.fieldGroup}>
          <label htmlFor="contact-message" className={styles.label}>Message</label>
          <textarea
            id="contact-message"
            className={styles.textarea}
            value={message}
            onChange={(e) => { setMessage(e.target.value); setErrors((p) => ({ ...p, message: '' })); }}
            rows={5}
            placeholder="Describe your issue or question…"
          />
          {errors.message && <p className={styles.error}>{errors.message}</p>}
        </div>

        <div className={styles.actions}>
          <button
            type="submit"
            className={styles.submitBtn}
            disabled
            aria-disabled="true"
            title="Contact submission is not yet available"
          >
            Send Message — Not Available
          </button>
        </div>
      </form>
    </Card>
  );
}
