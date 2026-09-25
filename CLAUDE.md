# CLAUDE.md — SecureNet (Behavioural IDS)

> **Maintenance rule (from the project owner):** update this file **every time** work is done on the project —
> record the work in the [Change Log](#10-change-log) and keep the [Issues register](#8-issues-register) current.
>
> **Install rule (from the project owner):** anything downloaded/installed (Node.js, Python packages, caches, tools)
> goes on the **F: drive**, never C: — see [§5](#5-how-to-run-windows).

---

## 1. What this project is

**SecureNet** (the dashboard is called **SENTRY** in the paper) is a **Behavioural-Based Network Intrusion Detection
System**, a final-year project by B. Samiksha, Shraddha V T, Shreshta S S and Siddhi Shetty (Dept. of CSE — IoT &
Cybersecurity with Blockchain, Mangalore Institute of Technology and Engineering; guide Dr. Shivananda V. Seeri).
The conference paper is `conference_paper_no_results_conclusion (2).pdf`.

| Aspect | Design (paper) | Status in code |
|---|---|---|
| Stage 1 | **Isolation Forest** scores each flow; score > threshold θ ⇒ suspicious | ✅ `app/ml/detector.py` (optional model) |
| Stage 2 | **XGBoost** classifies flagged flows into CICIDS2018 attack categories | ✅ `app/ml/detector.py` (optional model) |
| Dataset | CICIDS2018 flow records (CICFlowMeter features) | ✅ 71 features, same order as `backend/models/feature_columns.pkl` |
| Live capture | Scapy + psutil → flow features, same scaler/encoder as training | ✅ `network_monitor.py` + `features.py` (needs Npcap on Windows) |
| Modes | OFF / **Detection** / **Protection** (auto-block with netsh / iptables) | ⚙️ Owner's choice: IDS is simply **ON / OFF** (ON = detect + alert + email). `/ids/control` always runs `monitor`; blocking code kept but unused |
| Storage | PostgreSQL: score, category, top features, action | ✅ `security_events` (+ `contributing_features`) |
| API | FastAPI REST + WebSocket live stream | ✅ `/api/*`, `/ws/live` (token-authenticated) |
| UI | React + TypeScript dashboard, live score graph, alerts, report history | ✅ dark + warm **peach** light theme (Settings → Preferences); plain-language copy for common users |
| Alerts | Desktop + email notifications | ✅ in-app pop-ups, bell, sound, desktop; batched alert email to every registered user **from the admin Gmail with the incident report (.txt) attached**; daily reports on the Reports page |

**Models are optional and currently NOT loaded** (owner's decision: "either Isolation Forest or XGBoost or both",
to be enabled later). With no model the IDS still captures and counts traffic but scores nothing; the UI says so.

### Algorithm 1 (paper) — implemented in `IDSService.process_flow` + `Detector.analyze`
```
features ← feature_source(F)                # FlowRecord.features (71 CICIDS2018 columns, µs units)
scaled   ← Scaler.transform(features)       # if scaler.pkl present and its width matches
score    ← IsolationForest.score(scaled)    # anomaly score = -score_samples(x) ∈ (0,1]
if score > θ:                               # θ = Settings → Detection → Anomaly Threshold
    category    ← XGBoost.predict(scaled)   # if XGBoost loaded and stage 2 enabled
    topFeatures ← ExplainTop(scaled)        # |z-score| × XGBoost importance, top 5
    StoreAlert(...) ; if M == protect: BlockOrFlag(src IP) ; PushToWebSocket(alert)
```
XGBoost-only mode: every flow is classified; non-benign with confidence ≥ stage-2 threshold ⇒ alert,
anomaly score = 1 − P(benign).

---

## 2. Repository layout

```
SecureNet (3)/                               ← git root (github.com/samiksha99004/SecureNet-3-)
├── CLAUDE.md                                ← this file
├── START_SECURENET.bat                      ← double-click launcher: backend (:8000) + Vite (:5173), waits for /health, opens browser
├── START_SECURENET.ps1                      ← launcher logic (checks venv/Node/.env, skips busy ports, waits for /health)
├── SETUP.bat / SETUP.ps1                    ← one-time setup on ANY PC: venv (rebuilt if copied), Node (downloaded if
│                                              missing), npm install, .env + Neon + email + Npcap checks
├── scripts/securenet-env.ps1                ← shared helpers: tool/cache dirs (F: or .local), find Node/Python
├── .local/                                  ← tools/caches on PCs without an F: drive (gitignored)
├── docs/archive/                            ← old AI-generated status reports (historical, NOT accurate)
├── backend/                                 ← FastAPI service (Python 3.13 venv in backend\venv)
│   ├── app/
│   │   ├── main.py                          ← lifespan, uniform errors, routers, /ws/live, optional SPA serving
│   │   ├── core/config.py                   ← settings (.env resolved relative to backend/)
│   │   ├── core/security.py                 ← PBKDF2 hashing (+legacy bcrypt verify), typed JWTs
│   │   ├── db/base.py                       ← async engine (asyncpg; aiosqlite for tests)
│   │   ├── models/                          ← ORM (portable sqlalchemy.Uuid; enums stored by NAME)
│   │   ├── schemas/base.py                  ← CamelModel: snake_case attrs ↔ camelCase JSON, UTC "Z" datetimes
│   │   ├── schemas/*.py                     ← auth, common, security, settings, report, model
│   │   ├── api/dependencies.py              ← get_current_user, require_operator (admin|analyst), require_admin
│   │   ├── api/routes/                      ← auth, dashboard, events, ids, model, reports, settings_routes, health
│   │   ├── services/event_query.py          ← shared filters / safe sort map for events, export, reports
│   │   ├── services/exporters.py            ← CSV / JSON / PDF (reportlab)
│   │   ├── services/notifier.py             ← alert e-mails: batching, filters, recipients, digest
│   │   ├── api/routes/notifications.py      ← GET feed, GET status, POST test-email
│   │   ├── ml/features.py                   ← CICIDS2018 flow features (Flow, FlowRecord, FEATURE_COLUMNS)
│   │   ├── ml/network_monitor.py            ← Scapy AsyncSniffer → finished flows (FIN/RST/idle/active timeout)
│   │   ├── ml/detector.py                   ← optional IF / XGBoost loader + Algorithm 1 scoring
│   │   ├── ml/protection.py                 ← FirewallBlocker (netsh / iptables, expiry, safety list)
│   │   ├── ml/ids_service.py                ← live loop: queue → detect → store → block → notify → WS
│   │   ├── websocket/manager.py             ← broadcast live_score / alert / system_status
│   │   └── utils/                           ← logger, email (threaded SMTP), timeutil (naive-UTC helpers)
│   ├── models/*.pkl                         ← IF + XGBoost artifacts (gitignored; not loaded by default)
│   ├── tests/                               ← pytest suite (SQLite temp DB — never touches Neon)
│   ├── scripts/legacy/                      ← archived ad-hoc scripts (do not run; see README there)
│   ├── create_admin_user.py                 ← create/promote an admin (password prompted)
│   ├── setup.ps1                            ← compatibility wrapper → root SETUP.ps1
│   ├── scripts/check_setup.py               ← SETUP's read-only check: .env, Neon connection, email status
│   ├── requirements.txt / requirements-ml.txt
│   └── .env (gitignored, Neon URL + JWT secret) / .env.example
└── SecureNet (2)/SecureNet/
    ├── package.json, electron/main.js       ← Electron shell (backend serves built SPA on :8000)
    └── frontend/                            ← React 19 + TS + Vite 8 + Recharts + react-router 7
        ├── .env                             ← VITE_API_BASE_URL / VITE_WS_URL (localhost:8000)
        └── src/
            ├── styles/globals.css           ← DARK THEME tokens (single source of colours)
            ├── services/apiClient.ts        ← fetch wrapper: token refresh, uniform errors, auth downloads
            ├── services/*.ts                ← auth, dashboard, events, ids, model, reports, settings, websocket
            ├── contexts/AuthContext.tsx     ← session state, completeLogin, canOperate, expiry handling
            ├── components/common/ErrorBoundary.tsx ← root error screen (never a blank page); wraps <App/> in main.tsx
            ├── contexts/NotificationContext.tsx ← alert feed, unread state, pop-ups, sound, desktop notifications
            ├── components/notifications/    ← AlertPopups (on-screen alert cards), NotificationBell (top bar)
            ├── utils/alertChannels.ts       ← desktop Notification API + Web Audio alert tone
            ├── hooks/                       ← useAsyncData, useLiveMonitoring/useWebSocketMessage
            ├── pages/, components/          ← Dashboard, History, Reports, Settings, Account, Support, auth pages
            └── types/, utils/               ← camelCase API contracts, format/errors helpers, storage.ts (safe web storage)
```

## 3. Runtime architecture

```
Scapy sniff thread ─▶ NetworkMonitor (flows) ─▶ FlowRecord ─call_soon_threadsafe─▶ asyncio.Queue
                                                                                      │
IDSService._worker ◀──────────────────────────────────────────────────────────────────┘
   ├─ whitelist (IP / CIDR / port / protocol from DB)
   ├─ Detector.analyze  (asyncio.to_thread; returns None when no model is loaded)
   ├─ live_score → WebSocket (throttled for benign flows)
   └─ alert: SecurityEvent → DB, FirewallBlocker (protect mode + auto-block severities),
             alert → WebSocket, notifier.enqueue(event)
AlertNotifier (asyncio task): waits ALERT_EMAIL_BATCH_SECONDS after the first alert, filters by
   Settings → Notifications (high / medium / blocked), emails ALL active registered users + optional
   extra address (one email per recipient, one SMTP session), hourly-granularity digest if enabled.
Frontend: NotificationProvider (inside BrowserRouter) listens to WS `alert` → pop-up card (AlertPopups),
   bell feed + unread badge (NotificationBell, read state per user in localStorage), alert tone,
   desktop notification when the tab is not focused; "View incident" → /history?event=<id> opens the drawer.
   Dashboard polls every 15 s + refreshes on `alert` / `system_status` WS messages.
```

**API** (all under `/api` except `/health`, `/ws/live`):
`auth/{signup,otp/verify,signup/complete,login,otp/resend,password/forgot,password/verify,password/reset,profile/change,profile/confirm,refresh,logout,me,change-password}` ·
`events` (list, `export?format=csv|pdf|json`, `{id}`, `{id}/resolve`, `{id}/false-positive`) ·
`dashboard/{summary,host-status,protocol-distribution,top-sources}` · `ids/{status,control}` ·
`model/{info,feature-importance,reload}` · `reports/daily?tzOffset=` (days with attacks) + `reports/daily/{YYYY-MM-DD}/download?format=txt|csv|pdf&tzOffset=` (UI) — old generate/list/download/delete endpoints still exist but the UI no longer uses them ·
`settings` (all, detection, protection, notifications, system, whitelist CRUD) ·
`notifications` (feed, `status`, `test-email`) · `support/contact` (public: website, phone, email — falls back to the
first `ADMIN_EMAILS` — and admin office address; edited in Settings → System → Contact details) · `support/message`
(signed-in; {subject 3–150, message 10–5000} → emailed to the contact email with Reply-To = the user, copy to the user;
1 per minute / 10 per day per user, in-memory limiter).
Errors are always `{status, code, message, details?}`.

**Registration (3 steps)**: `POST /auth/signup` {fullName, email, phoneNumber} → 6-digit code emailed (real SMTP only) →
`POST /auth/otp/verify` {email, otp} → 15-min `setupToken` (JWT type `signup`, never an access token) →
`POST /auth/signup/complete` {setupToken, password, confirmPassword} → account ACTIVE + signed in. Afterwards: email + password.
UI: `/signup` → `/otp-verify` → `/create-password` → `/dashboard`. Phone stored normalised (`+?` 7–15 digits) in `users.phone_number`.

**Forgot password (3 steps)**: `/forgot-password` → `POST /auth/password/forgot` {email} (generic answer; code only for
ACTIVE accounts; 60 s cooldown while a code is outstanding) → `POST /auth/password/verify` {email, otp} → `resetToken`
(JWT type `reset`, 15 min, bound to the current password hash ⇒ single use) → `POST /auth/password/reset` → login page
shows "Your password has been changed". All codes are emailed from the admin Gmail (`SMTP_USER`).

**Profile changes**: `POST /auth/profile/change` {fullName?, phoneNumber?, email?} → only differing fields; a code is
emailed (to the NEW email when it changes; taken emails refused) + a 15-min `changeToken` (JWT type `profile` holding
the changes) → `POST /auth/profile/confirm` {changeToken, otp} applies them (old address notified on email change).
UI: Account → *Edit Details*.

**Attack emails**: every active non-admin user (+ Settings extra address) gets the normal alert; every admin gets
`[SecureNet Admin] …` with *who turned the IDS on* (`IDSService.started_by`, set in `/ids/control`), the monitored
computer, all registered users (name, email, phone, role) and full event details; both carry the incident report.

**Rate limits (issue #7)**: per account (login lockout, 5 tries per code, 60 s resend) **plus per network address**
(`app/utils/ratelimit.py`, in memory): 20 failed sign-ins / 15 min, 30 wrong codes / 15 min, 15 code emails / 15 min,
20 support messages / day. Support messages are stored in `support_messages` and their per-user limit (1/min,
10/day) is counted from the database, so restarts don't reset it.

**Roles (two)**: **Admin** — `ADMIN_EMAILS` (in `.env`: `samiksha99004@gmail.com`) register as `admin`; everyone else is a
**SecureNet User** (stored as `viewer`; legacy `analyst` is treated the same). Without `ADMIN_EMAILS` the first account to
complete registration becomes admin. Permissions: any signed-in user may turn the IDS ON/OFF (`/ids/control` uses
`get_current_user`); every settings write, whitelist change, model reload and event resolve/false-positive needs
`require_admin` (403 "Only the SecureNet admin can do this."). Frontend: `useAuth().isAdmin`, labels via `utils/roles.ts`.
`admin`/`analyst` can control the IDS, change settings/whitelist and resolve events; `viewer` is read-only;
only `admin` can reload models. Promote with `python create_admin_user.py user@example.com`.

## 4. Conventions & gotchas

- **Wire format is camelCase**; Python schemas are snake_case via `CamelModel` (alias generator). Never add
  `Field(alias=...)` by hand. Requests accept both cases.
- **Datetimes**: DB stores naive UTC; use `app.utils.timeutil` (`utcnow`, `parse_iso_utc`, `to_iso_z`).
  Responses use the `UtcDatetime` type so the browser gets a trailing `Z`.
- DB enums are stored by **name** (`HIGH`, `PROTECT`); `users.failed_login_attempts` is a legacy VARCHAR column
  mapped to int by `IntStoredAsString` (no migration needed).
- Anything blocking (sklearn/XGBoost, SMTP, subprocess, file writes) must go through `asyncio.to_thread`.
- The capture thread must never touch the DB/WebSocket directly — only enqueue via `_enqueue_from_thread`.
- Frontend colours come **only** from CSS variables in `styles/globals.css` (dark theme). Old token names
  (`--color-white` = card surface, `--color-peach-lightest` = page bg, `--color-peach-dark` = primary) are kept
  so components didn't need renaming; `--color-on-accent` is the text colour on accent/severity fills.
- Show real API errors with `errorMessage(err, fallback)`; never hard-code "backend not connected".
- Tests: `backend\venv\Scripts\python.exe -m pytest` (from `backend/`). They set env vars before importing the app
  and use a temp SQLite DB. Don't add tests that hit the real `.env` database.
- Don't print or commit `backend/.env` (Neon credentials, JWT secret).

## 5. How to run (Windows)

Tooling lives on F: (owner's rule): **Node.js 24 LTS** at `F:\tools\node`, caches in `F:\dev-cache`
(`pip`, `npm`, `tmp`), backend venv `backend\venv` (Python 3.13). The scripts find tools on their own
(`scripts/securenet-env.ps1`): F: when the PC has that drive, otherwise `<project>\.local` (gitignored);
override with `SECURENET_TOOLS_DIR`.

```text
one-time on any PC:  double-click SETUP.bat   (add -WithML from PowerShell: .\SETUP.ps1 -WithML)
every time:          double-click START_SECURENET.bat  (right-click → Run as administrator for live capture/blocking)
                     → backend http://127.0.0.1:8000 + UI http://localhost:5173, browser opens when both are healthy
```
- **Moving to another PC** (verified 2026-09-25 on a fresh copy with no venv/node_modules/Node):
  1. Copy the project folder (or `git clone`) **and copy `backend\.env`** — it is gitignored (Neon URL, JWT secret,
     SMTP). Without it SETUP stops with a clear message.
  2. Needs Windows + Python 3.11–3.14 (python.org) + internet. Node.js is downloaded by SETUP if missing
     (SHA-256 checked). A venv copied from another PC is detected as broken and rebuilt.
  3. SETUP checks the `.env`, connects to Neon, reports email status and whether Npcap is installed.
  4. Live capture on the new PC needs Npcap + Administrator, as here.
- **Database is always the cloud Neon PostgreSQL.** `config.py` refuses SQLite / localhost `DATABASE_URL`
  (only the tests set `ALLOW_LOCAL_DATABASE=true`). A missing/incomplete `.env` gives a readable startup error.
- **Emails are never faked**: no console printing of OTP codes/alerts. With `EMAIL_ENABLED=false` or placeholder
  SMTP values, sign-up returns 503 "Email delivery is not set up…" and nothing is created. Accounts can still be
  made without email via `python create_admin_user.py you@gmail.com "Name"` (from `backend/`).
- **Alert emails**: in `backend/.env` set `EMAIL_ENABLED=true`, `SMTP_USER=<gmail address>`,
  `SMTP_PASSWORD=<Gmail App Password>` (`SMTP_FROM_EMAIL` defaults to `SMTP_USER`); restart; then
  *Settings → Notifications*: turn on "Send Email Alerts" and click **Send test email**.
  Recipients = every active registered user (+ optional extra address). **Configured 2026-09-25**: Gmail
  `samiksha99004@gmail.com` with an App Password (in `.env` only); a real test email was sent successfully.
- **Live capture on Windows requires [Npcap](https://npcap.com)** (system driver, installs to C: by design) and an
  Administrator backend. Without it, turning the IDS on returns a clear 503 message. Npcap is **not installed** yet.
- Enable models later: put the `.pkl` files in `backend/models/`, `.\setup.ps1 -WithML`, then set
  `ML_AUTOLOAD=true` in `.env` **or** click *Settings → Model → Load / reload models* (admin).
- Electron: `npm run build:frontend` then `npm start` in `SecureNet (2)\SecureNet` (backend serves the SPA on :8000).

## 6. Verification status (2026-09-25)
- Session 18: backend **83/83 pytest** (+ `tests/test_profile_and_limits.py`: name/phone change needs code, wrong
  code, reuse, email change → code to new address + old notified + sign-in with new email, rules (nothing to change,
  taken email, bad phone/name, signed-out), token bound to one user; network limits for failed sign-ins across
  accounts, code emails, wrong codes; notifier test now checks user mail vs admin mail with users + event details;
  support test checks stored messages and that the limit survives a limiter reset). Chrome harness run 15/15: Edit
  Details (disabled until changed, code sent to masked address, wrong code refused, name/phone updated in sidebar +
  profile, email change → code to new address, sign in with new email), attack → user email to the user and
  `[SecureNet Admin]` email to samiksha99004@gmail.com listing both users and full event details, both with the
  report. Neon migrated to `d5f9a3c7e2b8`. Admin account created and sign-in verified on the real server.
- **Full QA pass (session 17)** — backend **76/76 pytest** (+17 in `tests/test_qa_auth.py`: right OTP; wrong OTP counts
  down 4…0 then the code is dead; **late OTP (11 min) rejected, 9 min still valid**; reused OTP rejected; OTP format;
  resend cooldown + old code invalidated; expired setup token; setup token can't take over an active account; login
  right/wrong/unknown (same message), case-insensitive email, unfinished registration can't log in, lockout + unlock;
  expired / tampered / foreign-secret / reset tokens and deleted-user tokens rejected; change password; late reset
  code; hostile search/sort/pageSize inputs). **Live API matrix** on the harness: 154 requests (every route ×
  anonymous/user/admin, empty + valid bodies) — 0 server errors, uniform `{status,code,message}`, anonymous blocked,
  user blocked from admin writes, CORS only for localhost:5173, API docs hidden. **WebSocket**: no/bad token refused,
  valid token gets status/pong/live_score/alert. **Neon (read-only)**: migration head `c4e8f2a6b1d7`, every table /
  column / nullability / index matches the models, 1 user (Samarth, viewer), 0 events, no stale OTPs, 1 row per
  settings table. **Browser (Chrome) E2E**: 41 checks — 40 pass after the fix below, 1 test artefact; 0 browser
  errors; phone width no overflow. **Frontend**: tsc clean, oxlint 0 errors, build OK, `npm audit` 0 vulnerabilities,
  no secrets in the bundle. **Email**: Gmail SMTP login accepted (235). **Performance**: Neon us-east-2 ≈ 305 ms per
  round trip → requests were 2.5–3.3 s; after removing pool pre-ping (+ recycle 240 s) warm requests 0.6–0.7 s.
- Session 16: backend **59/59 pytest** (+ support message test: sign-in required, validation, admin recipient +
  Reply-To user, subject newline stripped, name/phone included, HTML escaped, user copy, 1/minute limit, delivery
  failure → plain 503, nothing counted). Chrome harness run: "From" line, empty-form message, send → success banner,
  second send blocked "Please wait 58 seconds", captured mails: admin (reply-to user) + user copy; no page errors.
  Real Gmail send of a clearly-labelled test message rendered by the same code: delivered.
- Session 12: backend **58/58 pytest** (+ `tests/test_support.py`: fallback email, admin edits (website gets https://),
  public read, clearing a field, validation, users can't edit). Chrome harness run: peach theme applied (page bg
  #fbeee4), admin saved contact details → Support "Contact us" shows website/email/office for every user, Account
  page without the old note, **no technical words on any page** (dashboard, history, reports, account, support,
  login, user dashboard/settings/support), no page errors. Neon migrated to `c4e8f2a6b1d7`. tsc/oxlint (0 errors)/
  build clean. Contact phone/website/office not filled in yet (owner to provide; admin can enter them).
- Session 11: backend **57/57 pytest** (+ `test_securenet_user_can_switch_ids_but_nothing_else`: user starts the IDS,
  gets 403 on detection/notification/whitelist/model/resolve; legacy analyst = user). Chrome run on the SQLite harness:
  sign-in panel in plain language; SecureNet User → label "SecureNet User", ON/OFF enabled (backend accepted, replied
  "needs Npcap"), dashboard shows "Detection: Not set up yet" + friendly note (no tool names), Settings = Preferences
  only, Account shows "SecureNet User"; Support = About SecureNet + How to use SecureNet + "SecureNet version 1.0.0", no
  technical terms, no contact form; admin → "Admin", all 6 tabs. tsc/oxlint (0 errors)/build clean. Real app relaunched.
- Session 10: backend **56/56 pytest** (+ `tests/test_daily_reports.py`: empty list, local-day grouping (IST vs UTC),
  txt/csv/pdf downloads, 404/422, viewers can download, IDS forced to monitor; notifier tests: report attached,
  every severity emailed by default, subject names the most severe attack). Real Gmail send **with a .txt
  attachment** delivered. Chrome run on a SQLite harness (attacks injected through the real IDS pipeline, emails
  captured): dashboard ON/OFF only, no CPU/Memory, no Blocked card; Reports empty → 3 attacks → one day box
  (High 1/Medium 1/Low 1) → .txt downloaded with all 3; admin tabs = Preferences, Detection, Email Alerts,
  Whitelist, Model, System; viewer tabs = Preferences only, IDS power disabled with note; light theme applied and
  kept after reload; alert email captured with `SecureNet-incident-report-*.txt`; no page errors. Neon migrated to
  `b7d2e4f1a9c3` (alert_on_low; email on for all severities; protection mode MONITOR). tsc/oxlint (0 errors, 6
  advisory)/build clean.
- 3-step OTP registration (session 7): backend **45/45 pytest** (full flow: details → wrong code → right code →
  setup token rejected as access token → weak/mismatched password → create → token not reusable → email can't
  re-register → login with email + password; bad phone rejected; access token can't complete sign-up).
  Chrome run against a throw-away SQLite harness (codes captured, Neon untouched): bad phone message, code page,
  wrong code message, password page, mismatch message, account created → dashboard "Live", Account shows phone,
  sign out → sign in with email + password OK, no page errors. Neon migrated to `a1c4e7b9d2f0` (phone column).
- Session 9: backend **50/50 pytest** (+5 in `tests/test_password_reset.py`: full forgot flow incl. wrong code,
  reset token single-use and not an access token, old password rejected; unknown email generic + nothing sent;
  pending account can't reset; resend cooldown; `ADMIN_EMAILS` roles). Chrome run on a SQLite harness with
  `ADMIN_EMAILS=samiksha99004@gmail.com`: login page shows "Visit our website" + "Forgot password?" (university and
  administrator texts gone); Samiksha registers → Admin, empty dashboard (0s, NORMAL, no fake IPs), History 0 events;
  another user → Viewer; forgot password: wrong code rejected, new password saved, notice shown, old password
  rejected, new one signs in; no page errors. Real backend restarted; `/auth/password/forgot` live.
- Neon after session 9: **0 users, 0 events, 0 OTPs** (fake events + Samiksha's first account deleted after backup to
  `F:\SecureNet-backupake-events-20260925-155536.json` / `samiksha-account-20260925-155536.json`).
- Portability / real-data session (6): backend **42/42 pytest** (+10 in `tests/test_real_services.py`: local DB
  refused, cloud DB accepted, sender defaults to SMTP user, placeholder SMTP detected, disabled email raises,
  sign-up refused without email and nothing half-created). Fresh-PC simulation: project copied without
  venv/node_modules, no Node on PATH → SETUP rebuilt venv, downloaded Node 24.21.0, npm install, Neon connected,
  email reported off; START launched it; first load in Chrome showed the sign-up form (Vite's first-start reload
  handled). tsc clean, oxlint 0 errors (8 advisory), vite build OK. Test admin account created and signed in
  through the UI in Chrome → dashboard, data in ~0.3 s, WebSocket "Live", no page errors.
- (Session 7) The test admin `samiksha99004@gmail.com` was later **deleted** at the owner's request (their browser
  login failed; they chose the OTP sign-up instead). Neon has **0 users** — the first completed sign-up becomes admin. The 3 seeded `@securenet.com` demo accounts were
  deleted (backup: `F:\SecureNet-backup\demo-users-20260925-005609.json`). The 10 simulator events were kept
  (owner's choice).
- UI checks now use **Chrome** (`C:\Program Files\Google\Chrome\Application\chrome.exe`) via puppeteer-core in
  `F:\dev-cache\ui-check`: Edge 153 (auto-updated mid-session) exits immediately when driven by puppeteer.
- Blank-page fixes (session 5): headless Edge scenarios all render (no blank, no page errors): fresh profile,
  old-version session (migrated away), snake_case user, corrupt user JSON, storage blocked, backend unreachable,
  malformed/`null` API bodies, simulated component crash (error screen), main script failing to load (boot
  fallback). Real Neon data (3 users, 10 legacy events) replayed through every page + all 6 settings tabs +
  incident drawer + bell: no errors. Every GET endpoint returns 200 on the real DB (read-only check).
- Notification system: backend tests (batching, filters, recipients, HTML escaping, IDS→notifier, feed, status,
  test-email) pass; live browser run through a scratch harness (real server + real IDS pipeline with a fake
  detector, SQLite): 3 alerts → 3 pop-up cards, bell "3 unread" (cleared on open), "View incident" opened the
  drawer, one batched email to both registered users with the high + medium alerts (low filtered). No console errors.
- Backend: **32/32 pytest** pass (26 + 6 notification tests) (auth flow, OTP resend, lockout, refresh-token type check, settings persistence,
  RBAC, whitelist, events sort/pagination/date filters, export CSV/PDF, reports CSV/JSON/PDF + download,
  dashboard, IDS pipeline with fake detector, protection blocking path, WS auth).
- End-to-end against a live uvicorn + SQLite: **24/24** checks (SPA serving, signup→OTP→login, WS auth/ping,
  IDS control error, settings, whitelist, reports, export, refresh).
- Startup + `/health` against the real Neon DB: OK (read-only check).
- Frontend: `tsc -b` clean, `vite build` OK, oxlint 0 errors (8 advisory `set-state-in-effect` warnings — form
  tabs copy server data into local edit state; harmless). Dark theme checked with headless Edge screenshots
  (login, dashboard, history, settings, reports) — no browser console errors.

---

## 7. Severity legend
**Critical** – app cannot run / core feature broken · **High** – major feature wrong or insecure ·
**Medium** – incorrect behaviour · **Low** – hygiene.

## 8. Issues register

### Fixed on 2026-09-24 (session 2)
| ID | Issue (from the audit) | Fix |
|---|---|---|
| C1 | Active loader pointed at non-existent `F:\ML-NIDS-main` | RF/autoencoder ensemble removed; `detector.py` loads optional IF/XGBoost from `ML_MODELS_DIR` (relative to backend) |
| C2 | `torch` import broke backend boot | torch no longer used; ML libs optional (`requirements-ml.txt`), imported lazily |
| C3 | Paper models ignored; health/model routes used an uninitialised loader | Single detector used everywhere; health = DB status; model info reflects detector |
| C4 | IDS only ran a fake traffic simulator | Simulators deleted; IDS uses real Scapy capture or reports a clear capture error |
| C5 | UUID→str validation 500s (reports, whitelist) | `IdStr` type converts UUIDs |
| C6 | snake_case JSON vs camelCase frontend (pagination, settings, reports) | `CamelModel` base for all schemas |
| C7 | Settings saves silently dropped | snake_case attrs ⇒ `setattr` hits real columns; tested |
| C8 | OTP verify/resend 500 after a resend | Old OTPs invalidated, `limit(1)` queries; tested |
| C9 | Deps uninstallable on Python 3.13/3.14; no venv | New version ranges, venv on F:, setup script |
| H1 | Detector singleton rebound after import | One module-level `Detector`, loaded in place |
| H2 | Simulator wrong indices/units | Simulator removed |
| H3 | Scaler never applied; NaN into IF; `abs()` scores; fixed contamination gate | Algorithm 1 scaling, `nan_to_num`, `-score_samples`, configurable θ |
| H4 | Extractor re-scored each packet, unit mix, zeroed features, races | Emit once per finished flow; µs units; PSH/header/window/act-data features; packet timestamps; locking; AsyncSniffer stop |
| H5 | `asyncio.run` in capture thread | Thread → `call_soon_threadsafe` → queue → async worker |
| H6 | Fake/unsafe blocking | `FirewallBlocker`: netsh/iptables, expiry, dedupe, max, protected addresses, unblock on stop |
| H7 | Mode forced to protect | OFF/Detection/Protection selectable (dashboard + settings) |
| H8 | Settings/whitelist never reached IDS | `reload_config()` on start and on every settings/whitelist change |
| H9 | Refresh token usable as access token; no refresh | Typed tokens, `/auth/refresh`, silent refresh in apiClient |
| H10 | Unauthenticated WebSocket | `?token=` required (1008 close otherwise); default host 127.0.0.1 |
| H11 | RBAC inconsistent, no admin path | First user admin; operator/admin dependencies; UI respects roles |
| H12 | Error messages lost in UI | Uniform `{status,code,message}`; client also reads `detail` |
| H13 | OTP success bounced to login | `completeLogin` in AuthContext; pending email kept in sessionStorage |
| H14 | tz-aware vs naive datetime 500s | `parse_iso_utc`; responses end in `Z` |
| H15 | Reports never generated | CSV/JSON/PDF generation, authenticated download, file cleanup |
| H16 | Missing endpoints called by UI | Added export/download/feature-importance; removed forgot/reset/Google UI |
| M1–M9, M11, M13 | Dashboard zeros when off, not real-time, chart only attacks, metric semantics, sort map, flicker/stale data, blocking calls, auth hardening, task refs, tests, explainability | Fixed (see Change Log) |
| M10 | Electron build broken | Backend serves SPA; venv python; reuse running backend; no missing icon |
| B1 | **Blank page** when the browser held a session saved by the old app version (snake_case `full_name` → `user.fullName.charAt` threw in TopBar; no error boundary ⇒ React unmounted everything) | One-time session-format migration (`sn_session_format`), stored user validated/normalised, TopBar defensive, root `ErrorBoundary` |
| B2 | Blank page if the browser blocks site storage (every `localStorage` access throws on first render) | `utils/storage.ts` safe helpers used everywhere |
| B3 | Page blank while Google Fonts is slow/blocked (render-blocking stylesheet) | Fonts load non-blocking (`media=print` swap); system-font fallback |
| B4 | Empty `<div id="root">` ⇒ nothing visible if the bundle fails to load | Boot placeholder + failure message with the reason in `index.html` |
| B5 | Servers started by Claude died with its tool shell | `START_SECURENET.bat` (launch via Explorer / double-click), skips ports already in use, waits for `/health` |
| P1 | Project did not work on another PC: hard-coded `F:\tools\node` / `F:\dev-cache`, venv tied to this PC's Python, no Node install path, missing `.env` crashed with a traceback | `SETUP.bat` + `scripts/securenet-env.ps1` (F: or `.local`, Node download, venv rebuild, checks); readable `.env` errors |
| P2 | Fake emails: OTP codes / alerts "sent" by printing to the console; sender `securenet@example.com` | Real SMTP only; disabled/placeholder credentials ⇒ clear 503 on sign-up, errors in notifier status; sender = SMTP user |
| P3 | A local database (SQLite / localhost Postgres) was accepted | Refused at startup; cloud Neon only (tests opt in with `ALLOW_LOCAL_DATABASE`) |
| P4 | Seeded demo accounts `admin@/analyst@/viewer@securenet.com` (domain not owned — alert emails would reach strangers) | Deleted from Neon after backup |
| O11 | High | SMTP not configured → no codes/alerts could be emailed | **Fixed (session 8):** Gmail SMTP set in `.env`, real test email delivered |
| P6 | Fake simulator events shown as real incidents (Top Sources, "Current status: DDOS", detection reasons) | Deleted from Neon (backup kept); dashboard now empty until real traffic |
| P7 | No password reset ("ask an administrator") | `/forgot-password`: email → code → new password |
| P8 | Admin = whoever registered first | `ADMIN_EMAILS` decides admins; others are normal users |
| P9 | IDS offered Detection/Protection modes; owner wants ON/OFF | Mode selector, mode badges/filter, Protection tab and Blocked KPI/IP stat removed; backend always `monitor` |
| P10 | Host card showed CPU/Memory (not wanted) | Removed |
| P11 | Every user saw admin settings | Settings: Preferences (theme, notifications, sound, desktop) for all; admin tabs only for admin/analyst |
| P12 | Alert email had no report; low severity never emailed; email alerts off in DB | `.txt` incident report attached; `alert_on_low`; all severities on (migration) |
| P13 | Reports page was a manual generator | Automatic daily report boxes with .txt/.csv/.pdf download; empty until an attack |
| P14 | Three roles (admin/analyst/viewer) and users could not switch the IDS | Two roles: Admin + SecureNet User; users may switch ON/OFF only; everything else admin-only |
| P15 | Support page exposed models/tools/pipeline, had a dead contact form; three different version numbers | Plain-language About + How to use + single version 1.0.0 (package.json → `__APP_VERSION__`, backend default 1.0.0); sign-in panel and user-facing detector text de-technicalised |
| P16 | Technical wording shown to users ("backend API", "Cannot reach the SecureNet backend", ".env/SMTP" in sign-up errors, Npcap/"restart the backend") | Plain-language messages in UI and server responses; technical reasons only in logs / admin tabs |
| P17 | Light theme was a cool grey-blue | Warm peach / skin palette (cream cards, peach background, terracotta accent, brown text); theme button "Peach" |
| P18 | No way to contact the team | Support → Contact us (website, phone, email, admin office) editable by the admin; sign-in "Visit our website" uses the same website |
| P19 | No way for users to write to the team | Support → "Send us a message" (emailed to the contact/admin email, Reply-To the user, copy to user, anti-spam limit) |
| Q1 | SecureNet Users saw greyed-out *Mark Resolved / False Positive* with an outdated "admin and analyst" note | Actions section hidden unless admin (`IncidentDetailsDrawer`) |
| Q2 | Every request took 2.5–3.3 s (pool pre-ping = extra 300 ms round trip to the US database) | `pool_pre_ping=False`, `pool_recycle=240` for Postgres → 0.6–0.7 s warm |
| Q3 | High → fixed | No Admin account in Neon | Created `samiksha99004@gmail.com` (Samiksha Jain, 9482046521, admin); password given to the owner in chat |
| Q7 | Low → fixed | Limits only per account; support limit reset on restart | Per-network-address limits + support messages stored in the database |
| P20 | Users could not change their details | Account → Edit Details with an emailed code per change (email change verified on the new address) |
| P21 | One alert email for everybody | Normal alert for users, detailed admin copy (who turned the IDS on, computer, registered users, full event) |
| P5 | First start on a fresh install could show the boot error while Vite prepared dependencies | `index.html` retries once automatically before reporting |
| M14 | No alert notifications | Full notification system (pop-ups, bell feed, sound, desktop, batched emails to registered users, digest, test email) |
| L1–L4, L6, L7, L9 | Deprecations, no-op middleware, unused deps, stats, clutter, LIKE escaping, unverified build | Fixed / archived |
| new | Undefined CSS variables (`--color-bg-elevated`, `--text-*`, `--max-content-width`) broke IDS widget/page widths | Defined in globals.css |
| new | Detection/Protection settings tabs were hidden; unused fields shown | Tabs restored; sensitivity preset sets θ; unused fields removed |
| new | Null attack type shown as green "Normal"; History severity cards always "—" | "Unclassified"; real counts |

### Still open
| ID | Severity | Issue | Notes / next step |
|---|---|---|---|
| O1 | High | **Npcap not installed** → live capture unavailable on this PC. Installer **downloaded to `F:\tools\installers\npcap-1.89.exe`** (signature valid, Nmap Software LLC; SHA-256 8AED85E9…05CC) | Owner runs it (admin prompt; tick *WinPcap API-compatible Mode*; the driver itself goes into Windows by design), then starts SecureNet as Administrator |
| O2 | Medium | Models not loaded (by owner's choice) — compatibility of the `.pkl` files with current scikit-learn/XGBoost unverified; unknown whether IF was trained on scaled data | When enabling: install the training-time versions, `POST /api/model/reload`, check logs |
| O3 | Low | Protection (auto-block) mode is disabled by the owner (IDS is ON/OFF only); firewall code untested with admin rights | Re-enable only if the owner asks |
| O4 | Medium | Paper's reported metrics (78.58% → 99.98%) not reproducible from the repo (notebook/dataset in `F:\all_10_csv_manual`) | Add training notebook + evaluation script to repo |
| O5 | Low | Tokens in localStorage; logout doesn't revoke refresh tokens server-side | Consider httpOnly cookies / token denylist |
| O15 | Low | Support messages are not stored (email only) and the rate limit resets on restart. Contact details: email `samiksha99004@gmail.com`, phone `1234567898`, office `MITE, Mangalore`; website blank (owner's choice) | Add a message form that emails the admin; admin fills Contact details |
| Q4 | Medium | Database far away (Neon us-east-2, ~305 ms round trip from India): first request after idle ~3 s, warm ~0.6 s | Move the Neon project to ap-southeast-1 (Singapore) for ~4× faster responses |
| Q5 | Low | Legacy "generate report" endpoints (`POST/GET/DELETE /api/reports…`) still callable by any signed-in user although the UI no longer uses them (they write files to disk) | Remove them (daily reports replace them) |
| Q6 | Low | OTP codes stored in plain text in `otps` (valid 10 min, 5 tries) | Store a hash of the code |
| Q8 | Low | "Send verification code" waits ~4 s for Gmail | Acceptable; could send in background (loses error reporting) |
| Q9 | Info | Starlette TestClient deprecation warning in tests; Windows asyncio "connection reset" log line when a browser closes abruptly | Cosmetic |
| S1 | **Critical** | The Neon DB password (and the old JWT secret) were committed in two status notes and were **public on GitHub** from commit "updating" until 2026-09-25. History was rewritten and force-pushed without them, and the JWT secret was rotated, but anyone who copied the repo earlier still has the password | **Owner: reset the Neon role password now** and update `DATABASE_URL` in `backend/.env`; GitHub may keep cached copies of old commits for a while (contact GitHub support to purge if needed) |
| O12 | Low | Notification read-state is per browser (localStorage), not synced across devices; digest timer resets on backend restart | Add a `notification_reads` table if needed |
| O7 | Low | Electron package doesn't bundle Python; `npm start` from source only | Document or add PyInstaller build |
| O8 | Low | `detection_settings.min_flows_for_analysis` / `analysis_interval_ms` columns unused (hidden in UI) | Drop in a future migration |
| O9 | Low | Leftover untracked `backend/securenet.db` (kept by owner's choice; unused — local DBs are refused); old `backend/.env` has unused keys (ignored) | Safe to delete/clean manually |
| O10 | Low | 8 advisory oxlint `set-state-in-effect` warnings | Refactor tabs to keyed form components if desired |

## 9. Suggested next steps
1. Install Npcap, run `START_SECURENET.bat` as Administrator, switch IDS on, confirm packets/flows counters move.
2. Load models (§5), confirm `detector` shows `isolation_forest+xgboost`, watch live scores; tune θ in Settings.
3. **Change the Neon database password** (Neon console → Roles → neondb_owner → Reset password) and put the new
   connection string in `backend/.env` — the old one was public on GitHub until 2026-09-25 (see S1).

---

## 10. Change Log
| Date | Work done |
|---|---|
| 2026-09-24 (1) | Created CLAUDE.md. Read-only audit vs. the paper; logged 9 critical / 16 high / 14 medium / 9 low issues. No code changed. |
| 2026-09-24 (2) | **Toolchain on F:** Node.js v24.21.0 LTS → `F:\tools\node` (SHA-256 verified); caches in `F:\dev-cache`; backend venv (Python 3.13) in `backend\venv`; `puppeteer-core` for UI checks in `F:\dev-cache\ui-check`. **Backend rebuilt around Algorithm 1:** new `features.py`, `network_monitor.py`, `detector.py` (optional IF/XGBoost, nothing loaded by default), `protection.py`, `ids_service.py`; removed ensemble/torch pipeline and traffic simulators; CamelModel schemas; uniform errors; lifespan startup; typed JWT + refresh endpoint; OTP/lockout/first-admin auth fixes; RBAC; settings live-reload into IDS; whitelist validation; events sort map + export; reports generation/download; dashboard semantics; token-authenticated WebSocket; threaded SMTP + alert emails; portable `Uuid`; tz helpers; new requirements; pytest suite (26 tests) on SQLite; legacy scripts → `backend/scripts/legacy`, old status docs → `docs/archive`. **Frontend:** full **dark theme** (tokens, all CSS modules, charts, favicon, index.html); apiClient refresh/errors/downloads; AuthContext `completeLogin`/`canOperate`/expiry; OTP flow fix; IDS widget with Detection/Protection modes and capture/model status; live chart of all scores with alert markers and real θ; dashboard live refresh; desktop + toast alerts; Detection/Protection settings tabs restored; model reload button; history counts; real error messages everywhere. **Electron:** backend serves built SPA, uses venv, reuses running backend. Verified: pytest 26/26, E2E 24/24, Neon health OK, tsc/build clean, screenshots. Not committed. |
| 2026-09-25 (3) | **Notification system.** Backend: `services/notifier.py` (batched alert e-mails to all active registered users + optional extra address, severity/block filters, digest, HTML-escaped dark-branded template), `routes/notifications.py` (feed, status, test-email), generic multi-recipient `send_email` + `email_delivery_status`, IDS alert payload enriched and routed to the notifier, notifier started/stopped in lifespan, new config `ALERT_EMAIL_BATCH_SECONDS`, `ALERT_EMAIL_MAX_EVENTS`, `DASHBOARD_URL`; 6 new tests (32 total). Frontend: `NotificationContext` (feed, unread per user, pop-ups, sound, desktop), `AlertPopups` + `NotificationBell` (top bar), `/history?event=` deep link opens the incident, Notifications settings tab rebuilt (delivery status, recipients, test email, browser alert toggles); removed `useAlertNotifications`; z-index layering fixed (top bar 35 > pop-ups 30 < drawers/modals). Verified with tests + headless-Edge harness run. Not committed. |
| 2026-09-25 (4) | Launched the app for the owner with `START_SECURENET.ps1` (non-admin): `/health` OK against Neon (`database: connected`, `detector: none`, `ids: stopped`), Vite on :5173 returned 200. No code changes. Owner then saw a **blank page**: both servers had been started from Claude's tool shell and were killed when that shell's job ended (not an app bug). Relaunched them detached (`Win32_Process.Create`, each in its own "SecureNet Backend"/"SecureNet Frontend" cmd window); headless Edge confirmed the dark login page renders with no console errors. Running the script from the owner's own PowerShell is unaffected. |
| 2026-09-25 (5) | **Blank page fixed + full retest.** Root cause: an old-version session saved in the owner's browser crashed TopBar and there was no error boundary (B1). Also hardened: blocked storage (B2), render-blocking Google Fonts (B3), empty root when the bundle fails (B4). New `utils/storage.ts`, `components/common/ErrorBoundary.*`, session-format migration in `apiClient.ts`, `normaliseUser` in `authService.ts`, boot fallback in `index.html`; new `START_SECURENET.bat` launcher (B5). Verified: tsc clean, oxlint 0 errors (8 advisory), vite build OK, pytest 32/32, headless-Edge scenario suite + real-data replay of every page (§6). App launched via the .bat through Explorer; servers confirmed still running minutes later. Not committed. |
| 2026-09-25 (6) | **Portable, cloud-only, no fake emails + test account.** Owner asked: works on another device, DB not local, no fake emails/values. Deleted the 3 seeded `@securenet.com` demo users from Neon (backup in `F:\SecureNet-backup`); events + `securenet.db` kept by choice. `config.py`: local DB refused (`ALLOW_LOCAL_DATABASE` for tests), `SMTP_FROM_EMAIL` defaults to `SMTP_USER`, readable `.env` errors. `utils/email.py`: no console fallback, placeholder credentials detected; sign-up/resend return a clear 503 when email is not set up. New `SETUP.bat`/`SETUP.ps1`, `scripts/securenet-env.ps1`, `backend/scripts/check_setup.py`; `START_SECURENET.ps1` rewritten (checks, busy ports, health wait), `.bat` wraps it; `backend/setup.ps1` delegates; `.local/` gitignored; `index.html` boot retry; UI/README/.env.example wording. New `tests/test_real_services.py` (42/42). Verified with a fresh-PC copy (SETUP downloaded Node, rebuilt venv, START + first load OK), then deleted the copy (it held a copy of `.env`). Created test admin `samiksha99004@gmail.com` and signed in through the UI in Chrome. UI checks moved from Edge to Chrome (Edge 153 won't run under puppeteer). App relaunched via Explorer. Not committed. |
| 2026-09-25 (7) | **OTP registration as the owner described:** full name + email + phone → code emailed → enter code → create password → account created & signed in; next time email + password. Backend: `SignupRequest` (name/email/phone, phone normalised), `OtpVerifyResponse` returns `setupToken`, new `POST /auth/signup/complete`, `SIGNUP_TOKEN_TYPE` in `security.py`, admin role decided at completion, OTP email explains next step, `users.phone_number` + Alembic migration `a1c4e7b9d2f0` applied to Neon. Frontend: new `SignupForm` (step 1), `OtpForm` → `/create-password`, new `CreatePasswordForm`/`CreatePasswordPage`, `isValidPhone`, `completeSignup` in authService, phone on Account card. Tests updated + 3 new (45/45); tsc/oxlint/build clean; Chrome end-to-end run on a SQLite harness. Deleted the test admin account (owner's choice; Neon now 0 users). Real backend restarted with the new code. Still needs the owner's Gmail + App Password (O11) for codes to arrive. Not committed. |
| 2026-09-25 (8) | **Email switched on.** Owner supplied Gmail `samiksha99004@gmail.com` + App Password: written to `backend/.env` (`EMAIL_ENABLED=true`, SMTP user/password/from; previous `.env` backed up to `F:\SecureNet-backupackend.env.before-smtp`). `email_delivery_status()` = enabled; real test email sent through smtp.gmail.com OK; backend restarted via the launcher. Sign-up codes and alert emails now really arrive. Not committed. |
| 2026-09-25 (9) | **No fake data, forgot password, admin by email, website link.** Deleted the 10 simulator events + event features + OTPs and the just-created `samiksha99004@gmail.com` account (backups in `F:\SecureNet-backup`); Neon empty. Backend: `ADMIN_EMAILS` setting (+ `.env` = samiksha99004@gmail.com, `.env.example`), `_role_for_new_account`, shared `_consume_otp` / `_check_resend_cooldown` (cooldown only while a code is outstanding), `POST /auth/password/{forgot,verify,reset}`, `RESET_TOKEN_TYPE` + `create_reset_token` bound to `password_fingerprint`, `send_password_reset_email` (shared `_send_code` template); tests isolate from real `.env` (ADMIN_EMAILS/SMTP blanked). Frontend: `ForgotPasswordForm`/`ForgotPasswordPage` (`/forgot-password`), login "Forgot password?" link + success notice (dead "not verified" branch removed), AuthLayout footer "Visit our website" (`VITE_WEBSITE_URL`, empty for now). 50/50 pytest, tsc/oxlint/build clean, Chrome harness run. Real backend restarted. Not committed. |
| 2026-09-25 (10) | **ON/OFF IDS, user settings + theme, attack emails with report, daily reports.** Frontend: IDS widget ON/OFF only (no mode selector, no Blocked IPs), Blocked KPI removed (4-column KPI grid), Host Status without CPU/Memory, mode badges/filter + `ModeBadge` removed; Settings split (`PreferencesTab` for everyone: Dark/Light theme via `utils/theme.ts` + `data-theme` tokens in globals.css + early apply in index.html, notifications on/off (also gates desktop), sound + test, desktop permission; admin: Detection, Email Alerts (Low toggle replaces Blocked), Whitelist, Model, System; Protection tab deleted); Reports page rewritten (`DailyReportCard`, empty state, live refresh on alerts; old generate/table/summary components deleted). Backend: `utils/email.py` attachments (`Attachment`, multipart/mixed); `services/incident_report.py` (text report, local-time helpers); notifier attaches the report, local times, most-severe subject, email-all defaults; `alert_on_low` + migration `b7d2e4f1a9c3` (applied to Neon); `/reports/daily` + download; `/ids/control` always monitor. Tests 56/56; real Gmail attachment test; Chrome harness run; real app relaunched via the launcher. Neon: 1 user (Samarth Jain, viewer), 0 events. Not committed. |
| 2026-09-25 (11) | **Two roles + plain-language Support.** Backend: `require_operator` removed; settings/whitelist/events resolve → `require_admin` with message "Only the SecureNet admin can do this."; `/ids/control` open to every signed-in user; `APP_VERSION` default 1.0.0; new permission test (57/57). Frontend: `utils/roles.ts` (`isAdminRole`, `roleLabel` → Admin / SecureNet User) used in Sidebar, Account cards; AuthContext `canOperate` → `isAdmin`; IDS power button enabled for all users, user-facing detector/note text without tool names; Support page rewritten (`AboutCard`, new `GuideCard`, version line from `__APP_VERSION__` defined in `vite.config.ts` + `src/globals.d.ts`; `SupportInfoCard`/`ContactForm` deleted); frontend package version 0.0.0 → 1.0.0; sign-in left panel bullets in plain language. Chrome harness run; real app relaunched. Not committed. |
| 2026-09-25 (12) | **Peach theme, plain language, Contact us.** Light tokens in `globals.css` → warm peach/skin palette (+ `index.html`, `theme.ts` meta colour, Preferences label "Peach"). Removed technical wording from all user-visible text (ChangePasswordCard note deleted; load errors, network error, generic HTTP error, live-feed/host/summary texts; server: 500 messages, sign-up email failure, capture-unavailable). Contact details: 4 nullable `system_settings` columns + migration `c4e8f2a6b1d7` (applied to Neon), `SystemSettingsUpdate` validation, public `GET /api/support/contact` (admin-email fallback), System tab "Contact Details" section, Support `ContactCard`, AuthLayout website link from contact details. Tests 58/58; Chrome harness run; real app relaunched. Saved memory `plain-language-ui`. Not committed. |
| 2026-09-25 (13) | Contact us set as the owner asked: `system_settings.contact_email = samiksha99004@gmail.com`, phone / office location / website blank. `/api/support/contact` verified. No code changes. |
| 2026-09-25 (14) | Owner asked to run the app: both servers were down (windows closed); started with `START_SECURENET.bat` via Explorer — `/health` OK (Neon connected), UI on :5173, browser opened by the launcher. No code changes. |
| 2026-09-25 (15) | Contact us updated as the owner asked: phone `1234567898`, location `MITE, Mangalore`, email `samiksha99004@gmail.com` (website still blank); values passed through the same validation as the admin screen. App had stopped again (windows closed) — relaunched with the launcher; `/api/support/contact` verified. No code changes. |
| 2026-09-25 (16) | **Send us a message.** Backend: `send_email(..., reply_to=)` + `Reply-To` header; `SupportMessageRequest`; `POST /api/support/message` in `routes/support.py` (recipient = contact email or first admin email, Reply-To = user, copy to user, plain-language errors, per-user limiter); `tests/test_support.py` extended (59/59). Frontend: `sendSupportMessage`, new `MessageCard` (From line, subject, message + counter, validation, success banner, "Send another message"), Support page second row = Contact us + Send us a message (contact rows single column). Chrome harness run + real Gmail test. Real app relaunched. Not committed. |
| 2026-09-25 (17) | **Full QA pass** (owner request: frontend, database, API, backend; login, right/wrong/late OTP, email). Added `tests/test_qa_auth.py` (17 tests, 76/76 total); live API matrix (154 requests), WebSocket auth check, read-only Neon schema/data audit, 41-check Chrome E2E (harness gained a test-only `/__test/age-otp` hook), frontend tsc/lint/build/npm-audit/secret scan, Gmail SMTP login check, latency analysis. Fixed Q1 (user-visible admin actions) and Q2 (latency: pool pre-ping removed, recycle 240 s). Logged Q3–Q9. Real app relaunched. Not committed. |
| 2026-09-25 (18) | **Admin account, profile changes with OTP, admin alert email, Npcap download, issue #7.** Created admin Samiksha Jain (samiksha99004@gmail.com, 9482046521) in Neon. Backend: `PROFILE_TOKEN_TYPE` + `create_profile_token`, `ProfileChange*` schemas, `/auth/profile/change` + `/auth/profile/confirm`, `send_profile_change_email`; notifier `split_recipients`, `render_admin_email`, `fetch_events`/`report_attachment`, `IDSService.started_by`; `app/utils/ratelimit.py` wired into login/signup/resend/forgot/verify/profile/support; `SupportMessage` model + migration `d5f9a3c7e2b8` (applied); tests 83/83. Frontend: `EditProfileCard` (Account page), `requestProfileChange`/`confirmProfileChange`, guide text. Npcap 1.89 installer downloaded to `F:\tools\installers` (not installed). Chrome harness 15/15. Real app relaunched. Not committed. |
| 2026-09-25 (19) | **Published to GitHub** (`samiksha99004/SecureNet-3-`, public). Pre-push scan found the real Neon DB password + old JWT secret in `docs/archive/FIXED_AND_READY.md` and `NEON_POSTGRESQL_MIGRATION_COMPLETE.md` (already public since commit "updating"). With the owner's approval: git bundle backup (`F:\SecureNet-backup\securenet-git-before-rewrite.bundle`), JWT secret rotated in `backend/.env` (old .env backed up), docs redacted, work committed in 5 grouped commits (repo tidy, backend, frontend, tooling, docs), history rewritten with `git-filter-repo --replace-text` (installed in the F: venv) — 0 secret hits across all commits/6,902 objects — then force-pushed `main`. Verified no private files (.env, venv, node_modules, dist, *.db, *.pkl) are tracked; pytest 83/83 after the rewrite. Owner must still reset the Neon password (S1). |
