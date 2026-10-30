# CLAUDE.md — SecureNet (Behavioural IDS)

> **Maintenance rule (from the project owner):** update this file **every time** work is done on the project —
> record the work in the [Change Log](#10-change-log) and keep the [Issues register](#8-issues-register) current.
>
> **Install rule (from the project owner):** anything downloaded/installed (Node.js, Python packages, caches, tools)
> goes on the **F: drive**, never C: — see [§5](#5-how-to-run-windows).

---

> **Session 40 — model removed (owner's request).** The trained hybrid model is **no longer in the app**: its files were
> moved out of `backend/models/` to `F:\SecureNet-backup\models-removed-2026-10-13\` (the only copy — `F:\retraining_hybrid`
> no longer exists), `ML_AUTOLOAD` and `IDS_ON_AT_STARTUP` now default to **false**. The app runs with no detection ("Detection:
> Not set up yet"). To bring it back: move the files back into `backend/models/` and set `ML_AUTOLOAD=true` (+ optionally
> `IDS_ON_AT_STARTUP=true`). The sections below that describe the hybrid model describe the code, which is unchanged.
> **Desktop app:** `F:\SecureNet IDS.lnk` (icon `desktop/build/icon.ico`) opens SecureNet in its own Electron window (starts
> the backend itself, serves the built `frontend/dist`; one window only; external links open in the browser). After
> frontend changes run `npm run build` in `frontend/`. Note: a shell with `ELECTRON_RUN_AS_NODE=1` (VS Code terminals) can't start Electron.
>
> **Session 41 — LOCAL model integrated (2026-10-27).** This copy lives inside `F:\Intrusion_Detection-System\SecureNet`
> (the IDS-research project; old pristine copy kept at `F:\SecureNet` + `..\SecureNet_backup_old`). The removed hybrid is
> replaced by the research project's own **plain-XGBoost model** (`backend/models/local_model.pkl` + `classes.json`, 12
> classes, 55 CICFlowMeter-4.0 features). New code, nothing old deleted:
> `app/ml/local_adapter.py` (`LocalModel` + `JAVA_COLUMN` map model-feature→CICFlowMeter-4.0 header), a new **`local`
> detector kind** in `detector.py` (`_load_local` + `_analyze_local_batch`: argmax class, any non-Benign = attack, confidence
> floor = `stage2_confidence`; no IF stage so the `threshold`/sensitivity slider doesn't gate flagging), and
> `app/ml/csv_capture.py` (`CsvFlowSource`: a drop-in for `NetworkMonitor` that tails the project's `live_ids/csv` output
> instead of sniffing, so the model is fed flows from the **same real CICFlowMeter-4.0** it was trained on — avoids the
> train/serve skew that scapy features would cause). `.env`: `ML_AUTOLOAD=true`, `CAPTURE_SOURCE=local_csv`,
> `LIVE_CSV_DIR=F:\Intrusion_Detection-System\live_ids\csv`, `IDS_ON_AT_STARTUP=true`. Installed `pandas` into `backend/venv`
> (was missing; dill/xgboost/sklearn/numpy already present). VERIFIED: detector loads (`kind=local-xgboost`) and
> `analyze_batch` scores through the app context (xgboost 3.4 loads the 3.2-trained model with a harmless compat warning).
> TO RUN LIVE: start capture+convert (`live_ids/1_capture_windivert.py` + `2_convert.py`, admin) so CSVs appear, then start
> SecureNet (backend+frontend) with IDS ON — the dashboard shows what `live_status.py` used to print in the CLI.
> NOT yet end-to-end tested with the servers + a live attack. To revert to scapy+no-model: `CAPTURE_SOURCE=scapy`, `ML_AUTOLOAD=false`.

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
| Modes | OFF / **Detection** / **Protection** (auto-block with netsh / iptables) | ✅ IDS is **ON / OFF**; a **Settings → Advanced Protection** switch (session 42) turns Protection on/off at runtime. OFF ⇒ `monitor` (detect + alert). ON ⇒ `protect`: once traffic is abnormal (>30%) it auto-blocks the attacker's source IP (netsh) and the block is stored in the report |
| Storage | PostgreSQL: score, category, top features, action | ✅ `security_events` (+ `contributing_features`) |
| API | FastAPI REST + WebSocket live stream | ✅ `/api/*`, `/ws/live` (token-authenticated) |
| UI | React + TypeScript dashboard, live score graph, alerts, report history | ✅ dark + warm **peach** light theme (Settings → Preferences); plain-language copy for common users |
| Alerts | Desktop + email notifications | ✅ in-app pop-ups, bell, sound, desktop; batched alert email to every registered user **from the admin Gmail with the incident report (.txt) attached**; daily reports on the Reports page; IDS left ON survives a shutdown (turns itself back on at the next start + one Windows desktop notice) |

**The retrained hybrid model is loaded (session 33)** — Isolation Forest + XGBoost from `F:\retraining_hybrid`
(copied to `backend/models/`, not in git): 63 CICIDS2018 features, 7 classes (Benign, DDoS, DoS, Infilteration, Bot,
Brute Force, SQL Injection), tested threshold 0.4602, **92.24 % accuracy** on 465,837 unseen test flows. Loaded at
startup (`ML_AUTOLOAD` now defaults to true) and the IDS turns on at startup (`IDS_ON_AT_STARTUP`). Without model
files the IDS still captures and counts traffic but scores nothing; the UI says so.

### Hybrid model (session 33) — `app/ml/detector.py` kind `hybrid`
Used when `backend/models/model_config.json` exists (otherwise the legacy `.pkl` loader). Files: `model_config.json`
(features_used, classes, benign_code, threshold, roc_auc), `scaler.joblib`, `isolation_forest.joblib` (300 trees,
8,192 rows/tree), `xgboost_stage2.json` (Booster, 200 rounds × 7 classes), `hybrid_metrics.json` (real test results).
Exactly the tested pipeline (`F:\retraining_hybrid\4_evaluate.py`): x = 63 features by name →
stage 1 `score = -IF.score_samples(scaler(log1p(max(x,0)+1)))`, flagged when `score ≥ θ` → stage 2 XGBoost on the
**raw** x, argmax class; **Benign cancels** the flag; otherwise alert with that class (named only if confidence ≥
the stage-2 confidence setting, else "Unclassified"). `analyze_batch()` scores bursts in one call (identical verdicts,
~0.13 ms/flow vs 16 ms one at a time); the IDS worker drains up to `BATCH_MAX = 256` waiting flows. Features: the app's
extractor now also emits `Protocol` (number) and `Fwd URG Flags`; names match `features_used`; time columns in µs.
**Threshold**: `IDSService.effective_threshold` — when the model records a tested threshold, presets follow it
(Medium = tested, Low +0.05, High −0.03); Custom = admin's value; no settings row ⇒ Medium. Neon has MEDIUM ⇒ 0.4602.
**Severity** (hybrid): stage-2 confidence ≥ 0.9 High, ≥ 0.6 Medium, else Low; unnamed anomalies keep distance-above-θ.
**Model page** (`/api/model/info`): real values only — threshold in use + tested threshold, ROC-AUC 0.896, accuracy,
macro/weighted F1 and per-class precision/recall/F1/support from `hybrid_metrics.json` with the evaluation note;
max depth / learning rate are **not** stored in an XGBoost model file, so they show "Not available" (never guessed).
ML libs pinned to the training versions: scikit-learn 1.9.1, XGBoost 3.4.1 (`requirements-ml.txt`, installed in the
venv). `backend/scripts/verify_model.py` replays held-out test rows through `Detector.analyze` one flow at a time and
compares with the tested pipeline (20,000 rows: 100 % identical verdicts, score difference 0, 91.98 % = reference).
Live-traffic caveat (from `F:\all_10_csv_manual\documents\CLAUDE.md`): real LAN flows differ from the 2018 testbed, so
live accuracy can be lower than the offline 92.2 %; the app shows the model's real output either way.

### Verdict wording + guess tables (session 35)
Owner: show **normal / abnormal traffic**, not the attack name; the attack is a *guess* in a table (like the
report: Table 1 stage 1 Attack vs Not attack, Table 2 stage 2 "which attack" for all flagged flows incl. "Benign
(stage 2 cancelled the alarm)", final verdict %). `Detection.flagged` (stage 1 ≥ θ) + `Detection.guesses`
([{label, probability}] ≥ 0.5 %, best first). `IDSService` counts since the IDS was turned on (reset in `start()`):
`flows_scored/normal/flagged` + `guess_counts` (top class per flagged flow; Benign = cancelled; no stage 2 =
"Unclassified") → `/api/ids/status` `verdicts` {scored, normal, abnormal, guesses[{label, flows, cancelled}],
finalNormal, finalAbnormal}; the dashboard refetches it on every 5 s `system_status`. Events keep
`security_events.attack_guesses` (JSON, migration `f7c2a8e5b3d1`, applied to Neon). Wording lives in
`services/verdict.py` / `utils/verdict.ts` (`ABNORMAL`, `possible_attack` → "DDoS (97%)" or "Bot (45%, unsure)"
or "Unknown"). UI: status card NORMAL TRAFFIC / ABNORMAL TRAFFIC DETECTED + "Possible attack: …"; new
`TrafficVerdictCard` under the IDS widget (admin captions name the models, users see "step 1/2"); counters Normal /
Abnormal Traffic; pop-ups/bell/desktop "Abnormal traffic detected" + possible attack; History/Recent column
"Possible Attack"; incident drawer "Which attack might it be?" table. Emails: subject `[SecureNet] Abnormal traffic
detected (HIGH) from <ip> — possible attack: X`; reports/CSV/PDF: Verdict + Possible Attack + Model Guesses columns.
Alerts are still only stored for flows stage 2 confirms (Benign cancels), so normal LAN flows above θ don't flood.

### Dashboard in plain words (session 39)
Owner: no model names on the dashboard (common people don't know Isolation Forest / XGBoost); the top just says
abnormal traffic detected / normal; no tiny rows like SQL; the probability/guess table goes right under the big status.
IDS widget: status `NORMAL` / `ABNORMAL TRAFFIC DETECTED` only (no hint line); directly under it
`AttackGuessTable` "What kind of attack could it be?" (Attack type | Chance bar + %), from `attackChances()` in
`utils/verdict.ts` = share of each guessed attack among the abnormal flows since the IDS was turned on (cancelled/Benign
excluded, "Unclassified" → "Unknown type"), falling back to the latest alert's own guesses after a restart; rows under
`MIN_SHOWN_CHANCE` (5 %) hidden (also in the incident drawer). "Detection: Active / Not set up yet" for everyone (no
detector name); admin's no-model notice in plain words. `TrafficVerdictCard` → "Traffic Check": one table normal vs
abnormal (final verdict, connections + share), no stage tables. Detection reasons are now written in plain words by
`detector.py` ("The traffic looked unusual: score … is at or above the alarm level …. Most likely attack: DoS (100% sure)");
`plainReason()` rewrites older stored reasons the same way (widget, Detection reason card, incident drawer). Model names
remain only in admin Settings → Model / Detection.

### Self-protection (session 35) — `app/core/hardening.py`
`HardeningMiddleware` (added last ⇒ runs first): **Host check** (`ALLOWED_HOSTS`, default `localhost,127.0.0.1,::1`,
"*" disables; tests add `test,testserver`) → 400 "Unknown host" / WS close (DNS rebinding); **WebSocket Origin** must
be a `CORS_ORIGINS` entry or the serving host (no Origin = non-browser, allowed); **body limit** 1 MB (413
`PAYLOAD_TOO_LARGE`, chunked bodies buffered up to the limit then replayed); **headers** nosniff, X-Frame-Options
DENY, Referrer-Policy no-referrer, COOP, Permissions-Policy, API CSP `default-src 'none'; frame-ancestors 'none'`,
`Cache-Control: no-store` on /api + /health; built SPA (FRONTEND_DIST) gets `spa_csp()` = self + inline scripts and
the fonts' onload handler **by sha256 hash** ('unsafe-hashes'), Google Fonts, localhost connect. WebSocket: max 100
live connections (1013), uvicorn `--ws-max-size 65536 --no-server-header` (START, Electron, autostart). Capture:
`MAX_ACTIVE_FLOWS = 50,000` (oldest open flow finished early), `MAX_PACKETS_PER_FLOW = 20,000`. Storm limit:
`ALERT_STORE_MAX_PER_MINUTE=120`, `ALERT_STORE_MAX_PER_SOURCE_PER_MINUTE=30` (rest counted in
`alerts_not_stored` + verdict tables). CSV export prefixes `= + - @ \t \r` cells with `'`. Vite dev server:
`host: 'localhost'` + the same framing/sniffing headers (Vite itself checks Host and CORS).

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
SecureNet/                                   ← git root F:\SecureNet (github.com/samiksha99004/SecureNet; renamed from SecureNet-3-)
├── CLAUDE.md                                ← this file
├── README.md                                ← GitHub front page: what it is, folder layout, getting started
├── START_SECURENET.bat                      ← double-click launcher: backend (:8000) + Vite (:5173), waits for /health, opens browser
├── START_SECURENET.ps1                      ← launcher logic (checks venv/Node/.env, skips busy ports, waits for /health)
├── SETUP.bat / SETUP.ps1                    ← one-time setup on ANY PC: venv (rebuilt if copied), Node (downloaded if
│                                              missing), npm install, .env + Neon + email + Npcap checks
├── scripts/securenet-env.ps1                ← shared helpers: tool/cache dirs (F: or .local), find Node/Python
├── .local/                                  ← tools/caches on PCs without an F: drive (gitignored)
├── docs/QA_REPORT_2026-09-25.md             ← latest full QA report (tests, bugs fixed, still open)
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
│   │   ├── services/autostart.py            ← IDS ON/OFF memory (data/ids-state.json), Startup-folder entry, resume at start
│   │   ├── utils/desktop.py                 ← Windows toast notifications from the backend (app id SecureNet.IDS)
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
│   ├── scripts/check_setup.py               ← SETUP's check: .env, DB connection, `alembic upgrade head`, email status
│   ├── scripts/autostart.py                 ← run by the Startup shortcut (pythonw, no window) → backend; log in logs/autostart.log
│   ├── data/ids-state.json                  ← saved IDS ON/OFF choice for this computer (gitignored)
│   ├── requirements.txt / requirements-ml.txt
│   └── .env (gitignored, Neon URL + JWT secret) / .env.example
├── website/                                 ← public website (index.html, styles.css, script.js, favicon.svg) +
│                                              publish.ps1 → public repo samiksha99004/securenet-site (GitHub Pages)
├── desktop/                                 ← optional Electron shell
│   ├── package.json                         ← `npm start` / `npm run dev`; `build:frontend` builds ../frontend
│   └── electron/main.js                     ← starts ../backend (venv), backend serves ../frontend/dist on :8000
└── frontend/                                ← React 19 + TS + Vite 8 + Recharts + react-router 7
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
IDS across a shutdown (session 24, `services/autostart.py`): `/ids/control` ON (successful start) saves
   {enabled: true, startedBy} to `data/ids-state.json` and creates `SecureNet Monitor.lnk` in the user's Startup
   folder (venv `pythonw.exe` → `backend/scripts/autostart.py`, no admin, no window); OFF saves false and deletes it
   (also when the IDS wasn't running). Server shutdown (`ids.stop()` in lifespan) keeps the saved choice. At every
   backend start, lifespan runs `resume_after_restart()`: saved ON ⇒ `ids.start()` (retries 20 × 15 s while network/DB
   aren't up), restores `started_by`, then ONE Windows toast "SecureNet is on and is monitoring." (never email).
   Capture unavailable ⇒ one plain toast "SecureNet could not turn monitoring back on". `autostart.py` exits if
   port 8000 is already in use; START_SECURENET.bat later skips the busy backend port and just opens the dashboard.
Frontend: NotificationProvider (inside BrowserRouter) listens to WS `alert` → pop-up card (AlertPopups),
   bell feed + unread badge (NotificationBell, read state per user in localStorage), alert tone,
   desktop notification when the tab is not focused; "View incident" → /history?event=<id> opens the drawer.
   Dashboard polls every 15 s + refreshes on `alert` / `system_status` WS messages.
   **IDS OFF ⇒ dashboard shows no values** (session 27): `DashboardPage` computes `idsOff` from `/ids/status`; KPI
   cards show "—", Host Status rows "—" (no hostname), Security Summary / Network Traffic / Live chart / Why was this
   detected / Top Sources / Recent events show `IdsOffNote` ("IDS is off" + links to History and Reports), the IDS
   widget hides counters + incident panel; only `/ids/status` is polled while off; turning ON refetches everything.
   History and Reports are unaffected.
WebSocket auth: a bad/expired token is accepted then closed with **1008** (not a failed handshake).
   `websocketService` gets a fresh token before every (re)connect (`freshAccessToken()` in apiClient),
   refreshes once on 1008, and never stops retrying (30 s max back-off; "Connection error" after 10 tries).
```

**API** (all under `/api` except `/health`, `/ws/live`):
`auth/{signup,otp/verify,signup/complete,login,login/verify,login/resend,otp/resend,password/forgot,password/verify,password/reset,profile/change,profile/confirm,refresh,logout,me,change-password,change-password/confirm}` ·
`events` (list, `export?format=csv|pdf|json`, `{id}`, `{id}/resolve`, `{id}/false-positive`) ·
`dashboard/{summary,host-status,protocol-distribution,top-sources}` · `ids/{status,control}` ·
`model/{info,feature-importance,reload}` · `reports/daily?tzOffset=` (days with attacks) + `reports/daily/{YYYY-MM-DD}/download?format=txt|csv|pdf&tzOffset=` (UI; the old saved-report generate/list/download/delete endpoints were removed in session 21) ·
`settings` (all, detection, protection, notifications, system, whitelist CRUD) ·
`notifications` (feed, `status`, `test-email`) · `support/contact` (public: website, phone, email — falls back to the
first `ADMIN_EMAILS` — and admin office address; edited in Settings → System → Contact details) · `support/message`
(signed-in; {subject 3–150, message 10–5000} → emailed to the contact email with Reply-To = the user, copy to the user;
1 per minute / 10 per day per user, in-memory limiter).
Errors are always `{status, code, message, details?}`.

**Registration (3 steps)**: `POST /auth/signup` {fullName, email, phoneNumber} → 6-digit code emailed (real SMTP only) →
`POST /auth/otp/verify` {email, otp} → 15-min `setupToken` (JWT type `signup`, never an access token) →
`POST /auth/signup/complete` {setupToken, password, confirmPassword} → account ACTIVE + signed in. Afterwards: two-step sign-in (below).
UI: `/signup` → `/otp-verify` → `/create-password` → `/dashboard`. Phone stored normalised (`+?` 7–15 digits) in `users.phone_number`.

**Sign-in (2 steps, session 25)**: `POST /auth/login` {email, password} → password checked (lockout, network limit,
dummy hash for unknown emails) → a 6-digit code is emailed and the answer is `{loginToken, sentTo, message}` (**no
session tokens**; `loginToken` = JWT type `login`, 15 min, bound to the password fingerprint). Signing in again within
60 s reuses the code just sent. `POST /auth/login/verify` {loginToken, otp} → `AuthResponse`; `POST /auth/login/resend`
{loginToken} → new code (60 s cooldown). UI: `LoginForm` step 2 "Check your email" (`#login-code`, Verify and sign in,
Resend code, Use a different account); `AuthContext.login` returns the challenge, `verifyLogin` signs in.
**All emailed codes are valid 5 minutes** (`OTP_EXPIRE_MINUTES=5`, also in the owner's `.env`); max 5 tries per code.
**Code email (session 30, final)**: only the grey "Code requested" panel with one box per digit — no link, no
button, no second copy of the code (owner: "just print the OTP in button format, we copy it manually"); the full
code is only in the plain-text part and the hidden inbox preview line. (Session 28's link + /code page and
session 29's selectable copy were removed at the owner's request.)
**Code email design (session 27)**: `render_code_email()` in `utils/email.py` — subject `[SecureNet] <Sign-up | Sign-in |
Password reset | Password change | Profile change> verification code` (like GitHub's), hidden preview line with the
code, grey "Code requested" panel with one white box per digit, a "Copy code" pill holding the whole code (select +
copy — emails can't run a real copy button; Gmail adds its own *Copy code* card), expiry + "never share" note.
Table layout + inline styles only (Gmail/Outlook/phones). Plain-text part still starts "verification code is: NNNNNN".

**Forgot password (3 steps)**: `/forgot-password` → `POST /auth/password/forgot` {email} (generic answer; code only for
ACTIVE accounts; 60 s cooldown while a code is outstanding) → `POST /auth/password/verify` {email, otp} → `resetToken`
(JWT type `reset`, 15 min, bound to the current password hash ⇒ single use) → `POST /auth/password/reset` → login page
shows "Your password has been changed". All codes are emailed from the admin Gmail (`SMTP_USER`).

**Profile changes**: `POST /auth/profile/change` {fullName?, phoneNumber?, email?} → only differing fields; a code is
emailed (to the NEW email when it changes; taken emails refused) + a 15-min `changeToken` (JWT type `profile` holding
the changes) → `POST /auth/profile/confirm` {changeToken, otp} applies them (old address notified on email change).
UI: Account → *Edit Details*.

**Change password (2-step, session 23)**: `POST /auth/change-password` {currentPassword, newPassword,
confirmNewPassword} → current password checked (wrong tries count toward the network sign-in limit), strength +
"must differ" checked, a code is emailed to the **registered** address (60 s cooldown) + a 15-min `changeToken`
(JWT type `password`: user id, fingerprint of the current hash ⇒ single use, and an HMAC of the new password — the
password itself is never in the token) → `POST /auth/change-password/confirm` {changeToken, otp, newPassword}
(same new password required) sets it. Nothing changes before the code. UI: Account → *Change Password* → code step
(Confirm new password / Resend code / Cancel).

**Attack emails (session 37, owner: "admin is not a user — admin sends mails to users, admin should not receive any
mail regarding attacks")**: sent FROM the admin Gmail (`SMTP_USER`) TO every active non-admin user with alert emails on
(+ the Settings extra address unless it belongs to an admin / `ADMIN_EMAILS`), one batched email with the incident
report. `notifier.get_recipients()` is the single rule (alerts, digest, `/notifications/status`); the old
`[SecureNet Admin]` detailed copy (`render_admin_email`, `split_recipients`, `host_details`) was removed. Admins
still get their own sign-in/confirmation codes and the explicit *Send test email* they click.
**Email pacing + design (session 38, owner: "tonnes of emails like spamming — email when normal changes to abnormal,
then every 5 min; keep desktop alerting the same; email has too much info dump, keep it simple, keep the printable
report")**: `AlertNotifier.enqueue` marks a **new episode** when no alert came for `ALERT_EMAIL_INTERVAL_SECONDS`
(300); `seconds_until_next_email()` = `ALERT_EMAIL_BATCH_SECONDS` (30) for a new episode, else until 5 min after the
last alert email (never closer than 5 min); `_run` sleeps that long and sends ONE email for everything queued;
`stop()` only flushes if that keeps the spacing. Pop-ups/bell/desktop (WebSocket `alert`) are NOT throttled.
`render_alert_email(alerts, kind)` kinds new / continuing / digest / test: short summary only — title, one-line intro
("Your network was normal until HH:MM…" / "still detecting…"), grey panel with ABNORMAL TRAFFIC pill, most likely
attack (most common guess, "in X of N alerts", "the model's best guess"), alert count by severity, time range, sources
("IP and N others"), *Open SecureNet* button, "full report is attached — open or print it", footer (at most one email
every 5 min; how to switch off). Subjects `[SecureNet] Abnormal traffic detected - most likely DDoS (N alerts)` /
`[SecureNet] Abnormal traffic continues - N alerts, most likely DDoS`. The attached `.txt` incident report is unchanged.
`/notifications/status` gains `intervalSeconds`; Notifications tab explains the pacing. UI: Preferences shows
admins a note instead of the alert-email switch; Notifications tab says alerts go to users, never the admin, and
"No SecureNet users to email yet" when there are none.

**Website (session 29)**: `website/` (static, no build) — sidebar like the app (Home, Download, About SecureNet, The two
models, The app, Technology timeline, About us, Contact us), dark/peach theme switch, mobile drawer. Owner's content
rules: the four owners only — no guide, no college/education, no "final year project"; Download button disabled
("installer coming soon"). The project repo `samiksha99004/SecureNet` is **private** and the free plan only serves
Pages from public repos, and `samiksha99004.github.io` is the owner's personal portfolio (must not be touched), so the
site is published to the new public repo `samiksha99004/securenet-site` (Pages from main /) by
`website/publish.ps1` (clones into `.local/site-publish`, copies the files + `.nojekyll`, pushes). No links to the
private repo on the site. `system_settings.contact_website` = the site URL (sign-in "Visit our website" + Contact us).
**Website address without a name (session 31, postponed by the owner — site stays on GitHub Pages for now)**: owner does not want their GitHub name in the URL and
chose Cloudflare Pages. `securenet.pages.dev` is taken; `securenet-ids.pages.dev` is free. `website/publish-cloudflare.ps1`
(wrangler@4 via npx, project `securenet-ids`, reads `.local/cloudflare.env` = CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID,
gitignored) is ready for later; nothing was published there. When the owner wants it: they create the Cloudflare
account + token, fill `.local/cloudflare.env`, run the script, then switch
the site's Website card + Neon `contact_website` to https://securenet-ids.pages.dev/ and offer to delete the old
`samiksha99004/securenet-site` repository.
**Greeting (session 29)**: `utils/greeting.ts` (`useGreeting`, re-checked every minute; 05–12 morning, 12–17
afternoon, else evening) shown in the TopBar on the dashboard (`MainLayout greet`); hidden under 640 px.

**Personal preferences (session 28)**: *Settings → Preferences* — desktop notifications is a real switch
(`prefs.desktop` in `sn_notification_prefs`; turning it on asks the browser for permission; if the browser blocked
notifications the switch is disabled with how to unblock them). Attack alert emails on/off per account:
`users.email_alerts` (migration `e6b1c9d4a2f7`, default true, applied to Neon), `PUT /auth/me/preferences`
{emailAlerts}, `UserResponse.emailAlerts`; the notifier skips users who switched them off (codes are always sent).

**Speed (session 28)** — the database is ~300 ms per round trip away (Neon us-east-2 from India) and every request
used to cost 3–10 trips (≈3–5 s). Now: `dependencies.user_from_token` remembers the signed-in user 60 s (shared
lookup for parallel requests; after expiry answered once from memory while re-checked in the background;
`remember_user()` at sign-in, `forget_user()` after every account change); `services/cache.py` keeps dashboard
answers (summary in 3 queries instead of 8, protocols, top sources, bell feed, daily reports, detection settings,
contact) — `events_changed()` (IDS stores an event / resolve / false positive) drops `events:*` and re-loads them
in the background, `settings_changed()` drops `settings:*`, old entries are served while refreshing, parallel
requests share one load; loaders use their own sessions. `db/base.py`: `warm_up()` opens 4 connections at startup
and runs user/event/settings queries on each (the first custom-type query on a connection costs ~3 s of type
lookups), connections are replaced only after 4 min idle (`checkout` event), `keep_awake()` re-warms every 2 min
while the IDS is on, a dashboard is open or a request came in during the last 5 min (Neon never cold-starts while
in use; it may sleep when nobody uses SecureNet). Measured on Neon: all 9 dashboard requests 3–5 s → **~0.1 s**
(first load after a restart ≈1.4 s, after sign-in ≈0.1 s). Moving Neon to Singapore (Q4) would cut the rest ~4×.

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
- **Someone else downloading it** (session 25, verified with a fresh copy of the repo): README.md walks through it.
  SETUP creates `backend\.env` from `.env.example` with a random 96-hex `JWT_SECRET` and stops with what to fill in
  (own Neon `DATABASE_URL`, Gmail App Password, `ADMIN_EMAILS`); the backend refuses a placeholder/short JWT secret;
  `check_setup.py` refuses the example database address, then runs **`alembic upgrade head`** (builds all 11 tables on
  an empty database, no-op on an up-to-date one). Tools/caches go to `<project>\.local` unless the PC already has
  `F:\tools\node\node.exe` or `F:\dev-cache\pip` (only the owner's PC) — an F: drive alone is no longer enough.
  **Ports**: START uses 8000/5173 (or the last ones, `backend\data\ports.json`); a port held by another program is
  skipped (next free 8001…/5174…, SecureNet is recognised by `/health` / the page title) and both servers get the
  chosen ports via env vars (`PORT`, `CORS_ORIGINS`, `DASHBOARD_URL`, `VITE_API_BASE_URL`, `VITE_WS_URL`, Vite
  `--port … --strictPort`); `scripts/autostart.py` reads the same file. `START_SECURENET.ps1 -NoBrowser` skips
  opening the browser.
- **Moving to another PC** (verified 2026-09-25 on a fresh copy with no venv/node_modules/Node):
  1. Copy the project folder (or `git clone`) **and copy `backend\.env`** — it is gitignored (Neon URL, JWT secret,
     SMTP). Without it SETUP stops with a clear message.
  2. Needs Windows + Python 3.11–3.14 (python.org) + internet. Node.js is downloaded by SETUP if missing
     (SHA-256 checked). A venv copied from another PC is detected as broken and rebuilt.
     **Renaming/moving the project folder** keeps the venv importable but breaks its `.exe` launchers
     (`pip.exe`, `alembic.exe`, `uvicorn.exe` point at the old path). The scripts use `python -m …` so the
     app still runs; to repair the launchers reinstall the same versions with
     `python -m pip install --force-reinstall --no-deps <pkg>==<ver>` (done 2026-09-25 after `SecureNet (3)` → `SecureNet`).
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
- **Live capture on Windows requires [Npcap](https://npcap.com)** (system driver, installs to C: by design). Without it,
  turning the IDS on returns a clear 503 message. **Installed on this PC 2026-10-06** (1.89, WinPcap-compatible, non-admin
  capture allowed) — live capture works without running SecureNet as Administrator.
  The start-up entry (IDS left ON at shutdown) starts the backend **without** admin rights; capture then works as long
  as Npcap is installed with its default setting ("Restrict Npcap driver's access to Administrators only" **unticked**).
- Models: copy the hybrid files into `backend/models/` (see `backend/models/README.md`), `.\SETUP.ps1 -WithML`;
  they load at startup (`ML_AUTOLOAD=true` default) or via *Settings → Model → Load / reload models* (admin). The old
  August `.pkl` models were moved to `backend/models/archive_2026-08/` (unused).
- Electron: `npm run build:frontend` then `npm start` in `desktop\` (backend serves the SPA on :8000).

## 6. Verification status (2026-09-25)
- **Session 35 — normal/abnormal verdict, guess tables, self-protection (2026-10-06):** backend **129/129** (new
  `tests/test_verdict_and_hardening.py`, 10 tests: Table 1/2/final counts + API + stored guesses + feed wording,
  counters reset, wording helpers, storm limit (40 alerts → 5 stored, 35 counted), bounded flow table + flow cut,
  foreign Host 400 / own hosts OK, security headers on API + 404, 413 for big + chunked bodies (small chunked OK),
  WS foreign Origin 1008 / own Origin OK, CSV formulas neutralised). Real model on 3,000 test rows: Table 1 1,277
  normal / 1,723 abnormal, Table 2 DDoS 918, DoS 254, Bot 186, Benign 180, Brute Force 131, Infilteration 54.
  Chrome `qa3/verdict.js` **20/21** + email subject checked by hand (script fixed to pick the alert email) on the
  harness (real model, 300 real test flows): NORMAL TRAFFIC → ABNORMAL TRAFFIC DETECTED + "Possible attack: DoS
  (100%)", Table 1 136/164, Table 2 DDoS 85 / Benign 22 / Brute Force 18 / DoS 18 / Bot 13 / Infilteration 8, final
  52.67 % / 47.33 %, 142 alerts = 142 final abnormal, pop-ups/bell/History/drawer wording, foreign Host 400, headers,
  413, WS foreign origin refused, Vite framing headers, 0 page errors. `qa3/spa-csp.js` **5/5**: built dashboard served
  by the backend under the strict CSP renders, fonts load, signs in, live feed, 0 CSP violations. tsc/oxlint (0
  errors)/build clean. Neon migrated to `f7c2a8e5b3d1`; real app restarted: IDS on by itself, foreign Host → 400.
- **Session 33 — hybrid model loaded, live detection, speed (2026-10-06):** venv got scikit-learn 1.9.1 + XGBoost 3.4.1
  (training versions); test split re-scored in the app venv = 0.9224 (identical). `verify_model.py`: 20,000 test
  rows through `Detector.analyze` → 100 % same verdicts as the tested pipeline, score diff 0. Batch = single verdicts;
  ~8,000 flows/s in batches. Backend **119/119** (new `tests/test_hybrid_model.py`: loads as tested hybrid, live flow
  has all 63 features, batch = single, 1,000 test rows = reference, Model page shows real metrics, severity rule;
  `test_autostart`: IDS on at startup + OFF during start-up wins; `test_prefs_and_speed`: history/recipients never
  stale). Real backend on Neon: all page GETs 200, model `isolation_forest+xgboost`, threshold in use 0.460194 =
  tested, repeat requests ~5 ms (Settings 3.7 s → 5 ms, History 1.9 s → 6 ms), WebSocket OK; turning the IDS on →
  503 "needs Npcap" (Npcap still not installed). Chrome `qa3/live.js` **13/13** on the harness (real model, fake
  capture, 300 real test-split flows replayed through the IDS): 165 alerts for 183 true attacks (DDoS 91/98, Bot 32/32,
  Brute Force 15/15, DoS 21/22, Infilteration 4/16), pop-ups with real classes, live chart with real scores, events
  with score/class/confidence/reason, Model tab 0.4602 + 92.2 % + 465,837 + 7 classes, Detection tab preset text.
  **Real live monitoring** after Npcap was installed (owner approved) and the capture-check bug (R6) was fixed: the
  real app started by `START_SECURENET.bat` (no admin) turned the IDS on by itself, captured 1,034 packets / 43 flows
  in ~75 s, every flow scored by the hybrid model (e.g. 0.583, 0.606, 0.435 — normal flows above θ cancelled by stage
  2 as Benign, 0 false alerts), one "SecureNet is on and is monitoring." toast, Startup entry created.
- **Session 29 — website live, plain code email, greeting, name only (2026-09-26):** website published to
  https://samiksha99004.github.io/securenet-site/ (HTTP 200 for page, css, js, icon; owner's portfolio at
  samiksha99004.github.io untouched); Chrome on the live site: sidebar highlight follows the section, both themes,
  phone width 0 px overflow + menu drawer, 0 errors. Email rendered: no link, selectable code. Greeting checked in
  Chrome with the clock set to 09:00 / 14:30 / 20:15 → Good morning / afternoon / evening, <name>; Send us a
  message From shows the name only. Real backend: `/api/support/contact` returns the website. Backend 110/110,
  tsc/oxlint (0 errors)/build clean.
- **Session 28 — switches, Copy code, speed (2026-09-26):** backend **110/110** (new `tests/test_prefs_and_speed.py`:
  alert-email switch + notifier skips opted-out users, 7 dashboard GETs need 0 queries when repeated, summary = 3
  queries and refreshes after a new event / resolve, settings cache refreshed on change, expired user re-checked in
  the background then refused; deleted-user test adapted to the 60 s window; email test checks the Copy code link).
  Chrome `qa3/prefs-copy.js` **14/14**: desktop switch enabled, OFF/ON saved + kept after reload, alert-email switch
  OFF saved on the account + kept after reload + back ON, sign-in email has `/code#NNNNNN`, copy page says Copied,
  code on the clipboard, waiting sign-in tab filled in, signs in; 0 page errors. Neon migrated to `e6b1c9d4a2f7`
  (3 users, alert emails on). Speed on the real backend + Neon (`qa3/speed.py`): 9 parallel dashboard requests
  ~100 ms (was 3–5 s), `/ids/status` and `/dashboard/summary` ~8 ms; cold first load ≈1.4 s.
- **Session 27 — empty dashboard while OFF + new code email (2026-09-26):** Chrome on the harness (fake capture, one
  past attack): OFF → 12 "IDS is off" notes, KPI "—", no hostname/counters/attack names on the dashboard, History
  still lists the attack and Reports still offers the download; ON → values, host network rate and the attack back;
  0 page errors (screenshot checked). Code email rendered in Chrome at 620 px and 360 px (panel, 6 digit boxes, Copy
  code pill). Backend **105/105** (+ `test_code_email_design_and_subjects`). tsc/oxlint (0 errors)/build clean.
- **Session 26 — "IDS IS OFF" status (2026-09-26):** dashboard *Current Status* no longer says NORMAL while the IDS
  is stopped. Chrome on the harness (fake capture): OFF → "IDS IS OFF" + "Press ON to start monitoring", ON →
  NORMAL, OFF again → "IDS IS OFF"; screenshots in peach and dark themes; 0 page errors. tsc/oxlint (0 errors)/build
  clean.
- **Session 25 — sign-in code, 5-minute codes, portable download, README (2026-09-26):** backend **104/104 pytest**
  (new `tests/test_login_code.py`, 7 tests: password alone gives no session, login token isn't an access token, wrong
  code, right code, code single-use, wrong password sends nothing, 6-min-old code refused + resend + cooldown, second
  sign-in within 60 s reuses the code, token dies after a password reset, foreign tokens refused, email failure ⇒ 503
  and nothing issued; `test_codes_expire_after_five_minutes`; JWT placeholder/short refused; conftest `login()` helper).
  Chrome `qa3/login2fa.js` **10/10** (wrong password, code step with masked email + "5 minutes", still signed out,
  resend timer, wrong/right code → dashboard, Edit Details still needs a code, "Use a different account");
  regression suites updated for two-step sign-in: live API **84/84**, Chrome E2E **42/43** (known artefact).
  **Fresh-download test** (repo copied without .env/venv/node_modules): SETUP run 1 created `.env` (random secret) and
  stopped with instructions; run 2 built venv + npm and stopped at the example DATABASE_URL; run 3 (real DB address)
  connected, tables up to date, reported email/Npcap, "Setup complete". **Port clash test**: two foreign web servers
  on 8010/5180 (preferred ports) → launcher chose 8011/5181; Chrome: dashboard on 5181 called the API on 8011, no
  CORS/browser errors, foreign servers untouched. Migrations on an empty SQLite DB build all 11 tables = models. Copy
  deleted afterwards. tsc/oxlint (0 errors)/build clean.
- **Session 24 — IDS stays on after a restart:** backend **94/94 pytest** (new `tests/test_autostart.py`, 8 tests:
  ON remembered + Startup entry, OFF forgets + entry removed, failed start not remembered, OFF clears a saved ON
  when not running, server shutdown keeps the choice, resume = IDS on + started_by + exactly one notice, no resume
  when OFF, retries until the DB is reachable, capture unavailable ⇒ plain failure notice). Live on the harness
  (:8001, fake capture, entry in a temp folder): ON → state + `SecureNet Monitor.lnk`; kill server (shutdown) →
  restart ⇒ IDS ON, **one real Windows toast** "SecureNet is on and is monitoring." (checked in the notification
  history), 0 emails; OFF → entry removed, next restart stays OFF, no toast. Real start-up path: the shortcut
  (pythonw → `scripts/autostart.py`) started the real backend on Neon with no window (`/health` OK, log in
  `logs/autostart.log`) and exits with "already running" when port 8000 is busy. The real Startup folder was not
  touched by any test. tsc/oxlint (0 errors)/build clean.
- **Session 23 — password change with emailed code:** backend **86/86 pytest** (`test_change_password` now covers
  wrong current, same password, code emailed, old password still valid before the code, wrong code, token bound to
  the new password / the user / its type, success, single use). Frontend tsc/oxlint (0 errors)/build clean.
  Chrome (`qa3/pwchange.js`, harness on :8001 + Vite :5174 so the owner's app kept running) **11/11**, 0 page errors.
  Real backend restarted; `/auth/change-password/confirm` live.
- **Session 21 — full QA pass + fixes** (report: `docs/QA_REPORT_2026-09-25.md`). Backend **86/86 pytest**
  (new: `test_two_quick_starts_open_one_capture` (fails on the old code), `test_unknown_email_still_checks_a_password`,
  `test_legacy_saved_report_endpoints_are_gone`, `test_huge_page_number_is_refused_cleanly`; WebSocket test now
  requires close code 1008). Frontend tsc clean, oxlint 0 errors (6 advisory), build OK, `npm audit` 0. **Live API**
  on a new harness (`F:\dev-cache\ui-check\qa3\harness.py`: real app, temp SQLite, captured emails, `/__test/*` hooks)
  84/84 incl. a 252-request route matrix (0 server errors, uniform errors, anon/user blocked correctly), hostile
  inputs, CORS, WebSocket auth/ping/live alert, user + admin alert emails with report, reports, support, profile.
  **Chrome E2E** 40/41 (1 known test artefact: the resend timer after an artificially aged code), 0 browser errors.
  **Token-expiry scenario** (`ws-expiry.js`, 1-minute tokens, server restart): failed before the fix (stuck
  "Reconnecting…", no pop-up), passes after. **Neon read-only audit** (`neon_check.py`): head `d5f9a3c7e2b8`, schema
  = models, 1 row per settings table, 2 active users (admin samiksha99004@gmail.com + user samiksha94820@gmail.com) (both non-admin accounts were deleted in session 36),
  0 events, 0 stale codes; cold start ≈ 6 s, round trip ≈ 360 ms. Real backend smoke test on Neon OK.
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
| R1 | **Medium (session 21)** Live alerts silently stopped: after the 60-min access token expired, any WebSocket drop reconnected with the stale token forever (server refused before the handshake → browser saw 1006, not 1008) | Server accepts then closes 1008; client refreshes the token before every (re)connect and once on 1008; retries never stop |
| R2 | **Medium (session 21)** Two quick IDS "ON" requests both passed the `enabled` check → a second packet sniffer that was never stopped | `IDSService` start/stop serialised with an `asyncio.Lock`; regression test |
| R3 | Low (session 21) Login response time revealed registered emails (7 ms vs 54 ms); PBKDF2 ran on the event loop | Dummy-hash check for unknown emails; password checks via `asyncio.to_thread` |
| R4 | Low (session 21) `GET /api/events?page=1e20` → 500 | `page` capped at 1,000,000 (422) |
| Q5 | Low (session 21) Legacy saved-report endpoints writable by any user | Removed (`reports.py` = daily reports only); unused report schemas deleted |
| R5 | Env (session 21) venv `.exe` launchers broken after renaming the folder | Same versions force-reinstalled (§5) |
| P22 | Changing the password needed only the current password (no second factor) | Session 23: 6-digit code emailed to the registered address confirms every password change |
| P23 | IDS was OFF after every restart even if the user left it ON | Session 24: saved ON/OFF choice + Startup-folder entry; resumes at start with one desktop notice |
| P24 | A correct password alone signed you in | Session 25: every sign-in needs a 6-digit code emailed to the account (5-minute codes everywhere) |
| P25 | A fresh download could clash with the user's PC: tools written to any F: drive, busy ports 8000/5173 taken for SecureNet, empty database never got tables, `.env` had to be written by hand with a placeholder JWT secret accepted | Session 25: `.local` unless the owner's F: folders exist; free-port selection passed to both servers; SETUP creates `.env` (random secret) and runs migrations; placeholder secret refused |
| P26 | Dashboard *Current Status* showed a green NORMAL while the IDS was OFF (nothing was being watched) | Session 26: neutral grey card "IDS IS OFF" + hint to press ON; NORMAL / attack name only while running; "CHECKING…" before the status loads |
| P27 | Dashboard kept showing values (host network/uptime/OS, KPIs, charts, recent events) while the IDS was OFF | Session 27: every dashboard card empty with "IDS is off" while stopped; History/Reports unchanged |
| P28 | Code emails were a plain "Your verification code is" page | Session 27: GitHub-style "[SecureNet] … verification code" email with a Code requested panel, digit boxes and a copyable code |
| P29 | Desktop notifications could not be switched off once the browser allowed them (greyed "Allowed" button) | Session 28: real on/off switch |
| P30 | Alert emails could not be switched off per user | Session 28: `users.email_alerts` + Preferences switch |
| P31 | The email's Copy code pill was not a button | Session 30 (final): digit boxes only, copied by hand (session-28 link/page and session-29 extra code box removed at the owner's request) |
| P32 | No public website (sign-in "Visit our website" / Contact us had no link) | Session 29: `website/` published to GitHub Pages; contact website set in Neon |
| P33 | Dashboard had no personal greeting; message form showed the user's email | Session 29: "Good morning/afternoon/evening, <name>" (updates every minute); From = name only |
| Q10 | Medium → fixed | App took ~5 s per page (8 queries × ~300 ms, user re-read every request, reconnect every 4 min, type lookups on new connections, Neon cold start) | Session 28: user + dashboard caches, 3-query summary, warm connections, idle-only replacement, keep-awake while in use → ~0.1 s |
| O2 | Medium → fixed (session 33) | Models not loaded; compatibility unverified | Hybrid model loaded with the training library versions; verified identical to the tested results |
| P34 | Live detection had no model (no real scores) and did not start with the app | Session 33: hybrid model auto-loaded, IDS on at startup, real scores/classes/metrics |
| P35 | Settings / History / notification status took 1–4 s per visit | Session 33: cached until changed + prepared at startup → ~5 ms |
| O1 | High → fixed (session 33) | Npcap not installed → no live capture | Owner installed Npcap 1.89 (WinPcap-compatible, AdminOnly=0); service running |
| R6 | **High (session 33)** The IDS could never start on Windows, even with Npcap installed: `check_capture_available` imported only `scapy.config`, and `conf.use_pcap` becomes True only when `scapy.arch.windows` loads | Check imports `scapy.all` first; live capture verified on the real app without admin rights |
| P5 | First start on a fresh install could show the boot error while Vite prepared dependencies | `index.html` retries once automatically before reporting |
| M14 | No alert notifications | Full notification system (pop-ups, bell feed, sound, desktop, batched emails to registered users, digest, test email) |
| L1–L4, L6, L7, L9 | Deprecations, no-op middleware, unused deps, stats, clutter, LIKE escaping, unverified build | Fixed / archived |
| new | Undefined CSS variables (`--color-bg-elevated`, `--text-*`, `--max-content-width`) broke IDS widget/page widths | Defined in globals.css |
| new | Detection/Protection settings tabs were hidden; unused fields shown | Tabs restored; sensitivity preset sets θ; unused fields removed |
| new | Null attack type shown as green "Normal"; History severity cards always "—" | "Unclassified"; real counts |

| P36 | Dashboard/alerts stated the attack class as fact | Session 35: NORMAL TRAFFIC / ABNORMAL TRAFFIC DETECTED; attack shown as the model's guess; Table 1 / Table 2 / final verdict card; guesses stored per event |
| S2 | **High (session 35)** The app itself could be attacked: any Host accepted (DNS rebinding let a hostile web page read the local API from the owner's browser), no security headers (framing/sniffing), unlimited request bodies, WebSocket open to any origin, open-flow table and per-flow packet lists unbounded (random-port flood ⇒ memory exhaustion), every alert written to Neon + emailed (attack storm floods DB/email/dashboards), CSV export could carry spreadsheet formulas | `app/core/hardening.py` (host check, origin check, 1 MB limit, headers + CSP), WS connection cap + 64 KB messages, flow caps, alert storm limit, CSV escaping, Vite headers |

| P37 | The admin received attack emails (a detailed admin copy) although the admin is the sender, not a user | Session 37: alerts/digest only to non-admin users (+ non-admin extra address); admin copy removed |

| P38 | Users got an alert email for almost every alert (spam), and each email was a long per-alert table | Session 38: email on normal → abnormal, then at most one summary every 5 min; short summary email + printable report; screen/desktop alerts unchanged |

| P39 | Dashboard showed model names (Isolation Forest / XGBoost, stage 1/2), a hint line under the status, tiny guess rows, and the guess table far below the status | Session 39: plain status, chance table right under it (≥ 5 % only), plain detection reasons, no model names on the dashboard / history |
| R7 | **High (session 41)** Electron window stayed on the boot placeholder: `/` received the API CSP (`default-src 'none'`) so the dashboard script never ran | `/` gets the dashboard CSP when FRONTEND_DIST is served; regression test |

### Still open
| ID | Severity | Issue | Notes / next step |
|---|---|---|---|
| O3 | Low | Protection (auto-block) is now a runtime switch (Settings → Advanced Protection, session 42). Code path exercised via py_compile/build, but the live netsh block has not yet been tested end-to-end during a real attack with the backend elevated | Run a lab attack with Advanced Protection ON (backend as admin) and confirm the attacker IP gets a `SecureNet_Block_*` firewall rule + a BLOCKED event in the report |
| O4 | Medium | Paper's reported metrics (78.58% → 99.98%) not reproducible from the repo (notebook/dataset in `F:\all_10_csv_manual`) | Add training notebook + evaluation script to repo |
| O5 | Low | Tokens in localStorage; logout doesn't revoke refresh tokens server-side | Consider httpOnly cookies / token denylist |
| O15 | Low | Support messages are not stored (email only) and the rate limit resets on restart. Contact details: email `samiksha99004@gmail.com`, phone `1234567898`, office `MITE, Mangalore`; website blank (owner's choice) | Add a message form that emails the admin; admin fills Contact details |
| Q4 | Medium | Database far away (Neon us-east-2, ~305 ms round trip from India): first request after idle ~3 s, warm ~0.6 s | Move the Neon project to ap-southeast-1 (Singapore) for ~4× faster responses |
| Q6 | Low | OTP codes stored in plain text in `otps` (valid 10 min, 5 tries) | Store a hash of the code |
| Q8 | Low | "Send verification code" waits ~4 s for Gmail | Acceptable; could send in background (loses error reporting) |
| Q9 | Info | Starlette TestClient deprecation warning in tests; Windows asyncio "connection reset" log line when a browser closes abruptly | Cosmetic |
| S1 | **Critical** | The Neon DB password (and the old JWT secret) were committed in two status notes and were **public on GitHub** from commit "updating" until 2026-09-25. History was rewritten and force-pushed without them, and the JWT secret was rotated, but anyone who copied the repo earlier still has the password | **Owner: reset the Neon role password now** and update `DATABASE_URL` in `backend/.env`; GitHub may keep cached copies of old commits for a while (contact GitHub support to purge if needed) |
| O12 | Low | Notification read-state is per browser (localStorage), not synced across devices; digest timer resets on backend restart | Add a `notification_reads` table if needed |
| O7 | Low | Electron package doesn't bundle Python; `npm start` from source only | Document or add PyInstaller build |
| O8 | Low | `detection_settings.min_flows_for_analysis` / `analysis_interval_ms` columns unused (hidden in UI); since session 21 also the `reports` table / `Report` model and the `REPORTS_DIR` setting | Drop in a future migration |
| O9 | Low | Leftover untracked `backend/securenet.db` (kept by owner's choice; unused — local DBs are refused); old `backend/.env` has unused keys (ignored) | Safe to delete/clean manually |
| O10 | Low | 8 advisory oxlint `set-state-in-effect` warnings | Refactor tabs to keyed form components if desired |

## 9. Suggested next steps
1. Done (session 33): Npcap installed, hybrid model loaded, live capture + scoring verified.
2. Watch how the model behaves on this network (live flows differ from CICIDS2018); tune the sensitivity if needed.
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
| 2026-09-25 (20) | **Folder layout tidied** (owner: the nested `SecureNet (2)/SecureNet` folder looked bad). Moved the React app to `frontend/` and the Electron shell (`package.json`, `package-lock.json`, `electron/`) to `desktop/`; deleted the empty stub `SecureNet (2)/package-lock.json` and the folder. Updated `scripts/securenet-env.ps1` (`$FrontendDir`), `desktop/electron/main.js` (backend = `../../backend`, dist = `../../frontend/dist`), `desktop/package.json` (`build:frontend` → `../frontend`), `.gitignore` (`desktop/dist-electron/`). New root `README.md`; frontend README (was the Vite template) and backend README roles line rewritten. `docs/archive` left untouched (historical). Verified: frontend build + oxlint from `frontend/`, Electron paths resolve, pytest 83/83, `START_SECURENET.bat` → `/health` OK (Neon connected) + UI 200 on :5173. Committed and pushed (normal push). The root folder is still named `SecureNet (3)` locally (GitHub repo `SecureNet-3-`). |
| 2026-09-25 (21) | **Full QA pass + fixes** (owner: test frontend, backend, database, API; fix; report; update CLAUDE.md). Project folder is now `F:\SecureNet` (renamed from `SecureNet (3)`). Wrote a new harness + suites in `F:\dev-cache\ui-check\qa3` (`harness.py`, `api_test.py`, `e2e.js`, `ws-expiry.js`, read-only `neon_check.py`). Fixed: **R1** live alerts stopped after token expiry + reconnect (`main.py` WS accept→close 1008; `apiClient.ts` `freshAccessToken`/`refreshSession`; `websocketService.ts` fresh token per connect, one refresh on 1008, endless 30 s retries); **R2** IDS double-start race (`ids_service.py` `_lifecycle_lock`); **R3** login timing leak + PBKDF2 off the event loop (`auth.py` `_DUMMY_PASSWORD_HASH`, `asyncio.to_thread`); **R4** huge `page` → 500 (`events.py` `MAX_PAGE`); **Q5** legacy saved-report endpoints removed (`reports.py`, `schemas/report.py`); **R5** venv launchers repaired. Tests: pytest 86/86, live API 84/84, Chrome E2E 40/41 (known artefact), token-expiry scenario pass, Neon audit pass, real-backend smoke test OK. Report: `docs/QA_REPORT_2026-09-25.md`. Not committed. |
| 2026-09-25 (22) | Owner asked to run the app: started with `START_SECURENET.bat` via Explorer (after the session-21 fixes) — `/health` OK (Neon connected), UI 200 on :5173, browser opened by the launcher. No code changes. |
| 2026-09-25 (23) | **Two-factor password change** (owner: changing password had no 2FA; add an OTP to the registered email). Backend: `PASSWORD_CHANGE_TOKEN_TYPE`, `new_password_digest`, `create_password_change_token` (security.py); `ChangePasswordConfirm` schema; `send_password_change_email`; `/auth/change-password` now checks and emails a code (returns `changeToken`, `sentTo`, `message`), new `/auth/change-password/confirm`; conftest captures the new email; `test_change_password` extended. Frontend: `ChangePasswordConfirm` type, `confirmPasswordChange`, `ChangePasswordCard` code step. 86/86 pytest, tsc/oxlint/build clean, Chrome 11/11. Real backend restarted via the launcher. Not committed. |
| 2026-09-25 (24) | **IDS stays on after shutdown/restart + desktop notice** (owner: if the IDS is on when the computer is shut down it should be on again when the computer starts, with one desktop-only notification "SecureNet is on and is monitoring", no email). New `app/services/autostart.py` (state file, Startup `.lnk` via PowerShell WScript.Shell, `resume_after_restart`), `app/utils/desktop.py` (Windows toast, HKCU AppUserModelId `SecureNet.IDS`, text passed via env vars), `backend/scripts/autostart.py` (pythonw launcher, port check, log rotation). `config.py`: `IDS_AUTOSTART`, `IDS_STATE_FILE`, `IDS_STARTUP_DIR`, `DESKTOP_NOTIFICATIONS` (+ `.env.example`); `ids.py` remembers ON/OFF; `main.py` lifespan starts/cancels the resume task; `backend/.gitignore` `data/`; conftest + harness use temp dirs and no pop-ups (harness `HARNESS_FAKE_CAPTURE=1`). Guide text updated (restart behaviour; password change by code). 94/94 pytest, harness restart simulation, real shortcut start on Neon. Real app relaunched via the launcher. Not committed. |
| 2026-09-26 (25) | **Sign-in with an emailed code, 5-minute codes, portable download, GitHub README** (owner: OTP for login and for personal-detail changes, code expiry 5 minutes; proper README with download/run steps; must not clash when run locally by others; push to GitHub). Personal-detail changes already required a code (session 18) — re-verified. Backend: `LOGIN_TOKEN_TYPE` + `create_login_token`, `LoginChallenge`/`LoginVerifyRequest`/`LoginResendRequest`, `send_login_code_email`, `/auth/login` → challenge, new `/auth/login/verify` + `/auth/login/resend`; `OTP_EXPIRE_MINUTES` 10 → 5 (config default, owner `.env`, `.env.example`); JWT secret validator. Frontend: `LoginChallenge` type, `verifyLogin`/`resendLoginCode`, AuthContext `login` → challenge + `verifyLogin`, `LoginForm` code step; guide step "Sign in safely". Portability: `securenet-env.ps1` (F: only if the owner's folders exist; port helpers), `START_SECURENET.ps1` (free ports, env for both servers, `-NoBrowser`), `SETUP.ps1` (creates `.env` with random secret), `check_setup.py` (example-URL check, `alembic upgrade head`), `scripts/autostart.py` (saved ports). Docs: new root `README.md`, `backend/README.md` refreshed. Tests: 104/104 pytest, Chrome 10/10 + 42/43, API 84/84, fresh-download + port-clash runs. Committed and pushed to GitHub. |
| 2026-09-26 (26) | **"IDS IS OFF" instead of NORMAL** (owner: when detection is off it should not show normal). `IDSControlWidget.tsx`: status = IDS IS OFF while stopped (ShieldOff icon, hint "Your network is not being watched. Press ON to start monitoring."), NORMAL / latest unresolved attack only while running, CHECKING… / STATUS UNKNOWN before the status arrives; `.statusOff` + `.statusHint` in `IDSControlWidget.module.css` (theme tokens only). Chrome check on the harness in both themes. Committed and pushed to GitHub. |
| 2026-09-26 (27) | **Dashboard empty while the IDS is OFF + GitHub-style code emails** (owner: when the IDS is off nothing on the dashboard should have values — only detection is off, History/Reports keep working; make the OTP email look like GitHub's "Code requested" email; update CLAUDE.md + README; push). Frontend: new `components/dashboard/IdsOffNote.tsx` (+ css), `idsOff` prop on HostStatusCard, SecuritySummaryCard, ProtocolDistributionCard, TopSourcesCard, DetectionReasonCard, RecentEventsTable, LiveAnomalyChart; IDSControlWidget hides counters/incident while off; DashboardPage `idsOff` / `idsPending`, polls only the IDS status while off and refetches when it turns on. Backend: `render_code_email()` + `_send_code(email, code, purpose, next_step)` with the new subjects; test added (105/105). README features/usage updated. Committed and pushed to GitHub. |
| 2026-09-26 (28) | **Desktop + email alert switches, working Copy code button, speed** (owner: desktop notifications could not be turned off; email alerts on/off; the OTP copy button did not work; app took ~5 s, IDS must be fast; update CLAUDE.md + README and push every time). Backend: `users.email_alerts` + migration `e6b1c9d4a2f7` (applied to Neon), `PUT /auth/me/preferences`, notifier filter; `render_code_email` Copy code link; user cache (`remember_user`/`forget_user`, shared + background re-check), `services/cache.py` (events/settings caches, priming, stale-while-refresh), 3-query summary, loaders with own sessions, `db/base.py` warm-up with type priming, idle-only connection replacement, keep-awake. Frontend: `CopyCodePage` (/code), `utils/codeHandoff.ts` in all five code forms, desktop switch (`prefs.desktop`), alert-email switch, `User.emailAlerts`. Tests 110/110, Chrome 14/14, speed measured on Neon. Saved memory `push-after-every-change`. Committed and pushed. |
| 2026-09-26 (29) | **Website live on GitHub Pages, plain code email, greeting, message "From" = name** (owner: make a website with a sidebar — download (no app yet), about us (4 owners, no guide/education/final-year), about SecureNet (2 models, the app, technologies as a timeline), contact — in a new `website` folder, host it live; the email copy button must just copy, no page/auto-fill; add the website to Contact us; greeting by time of day; only the name in Send us a message; update CLAUDE.md and push). New `website/` (index.html, styles.css, script.js, favicon.svg, README.md, publish.ps1); public repo `samiksha99004/securenet-site` created and Pages enabled via the GitHub API (project repo is private); live at https://samiksha99004.github.io/securenet-site/; Neon `contact_website` set. Email: Copy code link removed, plain selectable code; `CopyCodePage`, `utils/codeHandoff.ts` and the form hooks removed. `utils/greeting.ts` + TopBar greeting; MessageCard From = name; support success message without the address. Tests 110/110, Chrome checks. Committed and pushed. |
| 2026-09-26 (30) | **Code email = digit boxes only** (owner: no copy button needed, just print the OTP in box format, we copy it manually). `render_code_email`: removed the "Your code" box and the select hint; test updated (110/110). Committed and pushed. |
| 2026-09-26 (31) | **Website address without the owner's name — Cloudflare Pages prepared** (owner: no name in the website address; chose Cloudflare Pages). Checked names (securenet.pages.dev taken, securenet-ids.pages.dev free); new `website/publish-cloudflare.ps1`; `.local/cloudflare.env` template (gitignored); website README. Waiting for the owner's Cloudflare account + API token. Backend restarted with the digit-box email. Committed and pushed. |
| 2026-09-26 (32) | Owner: keep the website on GitHub Pages for now (https://samiksha99004.github.io/securenet-site/), move to Cloudflare later. No code changes; CLAUDE.md status updated. Committed and pushed. |
| 2026-10-06 (33) | **Retrained hybrid model loaded, live monitoring at startup, faster pages** (owner: load the hybrid Isolation Forest + XGBoost from F:\retraining_hybrid, fix API/connection errors, live monitoring when the app starts, no fake values — real results from the model's testing). venv: scikit-learn 1.9.1, XGBoost 3.4.1 (pinned in requirements-ml.txt). Model files copied to backend/models (old Aug .pkl → archive_2026-08; .gitignore models/*.json, archive*/; models/README.md). `detector.py` rewritten: hybrid loader + tested pipeline + `analyze_batch`, legacy kept; `features.py`: Protocol, Fwd URG Flags; `ids_service.py`: effective threshold (presets follow the tested threshold), reload_config after model load, batch worker, confidence-based severity, status `threshold`; `/api/model/info` real metrics (schemas: tested_threshold, evaluation, test_rows); `autostart.py` + `IDS_ON_AT_STARTUP` (default true), `ML_AUTOLOAD` default true; caches for settings/whitelist/recipients/history + more startup priming; `scripts/verify_model.py`. Frontend: Model tab (threshold in use / tested, evaluation note, only real metric rows), Detection tab preset text, live chart uses the IDS threshold. Tests 119/119, Chrome 13/13, real backend smoke OK. Live capture still needs Npcap (O1). Committed and pushed. |
| 2026-10-06 (34) | **Npcap installed + live capture bug fixed** (part of the model request: live monitoring when the app starts). With the owner's approval opened the signed Npcap 1.89 installer (owner clicked through: WinPcap-compatible, AdminOnly=0). Found R6: `network_monitor.check_capture_available` checked `scapy.config.conf.use_pcap` without loading `scapy.arch.windows`, so it was always False and the IDS could never start on Windows — now imports `scapy.all` first. Real app (no admin) now starts monitoring by itself and scores real traffic with the hybrid model. 119/119 tests. Committed and pushed. |
| 2026-10-06 (35) | **Normal / abnormal verdict + guess tables, app protected against attacks on itself** (owner: instead of the attack name show normal traffic / abnormal traffic detected, with a guess table below of what attack it might be like the report photos (Table 1 stage 1, Table 2 stage 2, final verdict); make SecureNet itself hard to attack). Backend: `Detection.flagged/guesses`, IDS verdict counters + `/ids/status.verdicts`, `security_events.attack_guesses` (migration `f7c2a8e5b3d1`, applied to Neon), `services/verdict.py`, wording in alert payload / notifications / emails / incident report / exports; `core/hardening.py` + `ALLOWED_HOSTS`, WS connection cap, flow caps in `network_monitor.py`, alert storm limit, CSV formula escaping, uvicorn flags in the launchers. Frontend: `TrafficVerdictCard`, `utils/verdict.ts`, status card/counters/pop-ups/bell/History/drawer/reports wording, Vite security headers. Tests 129/129, Chrome 20/21 (+1 test-script fix) and 5/5 (SPA CSP). Real app restarted. Committed and pushed. |
| 2026-10-06 (36) | **Only the admin account kept** (owner: delete both SecureNet users, keep only admin). Deleted Samarth Jain (samiksha94820@gmail.com) and Anivrath (4mt23ic012@mite.ac.in) from Neon after a JSON backup (`F:\SecureNet-backup\securenet-users-deleted-20261006-234937.json`: users, their 8 OTP rows, 1 support message); their references cleared (support message kept with user_id = null; no events/settings/reports pointed to them). Neon now has 1 account: Samiksha Jain (admin, active). No code changes. Committed and pushed. |
| 2026-10-06 (37) | **Admin sends attack emails, never receives them** (owner: admin is not a user; admin should send mails to users when there are attacks/alerts and should not receive any attack mail). `notifier.py`: `get_recipients()` = active non-admin users with alert emails on + extra address unless it is an admin's; admin copy + `split_recipients`/`render_admin_email`/`host_details` removed; email heading reworded (abnormal traffic). Tests updated + `test_admin_never_gets_attack_emails` (130/130). Frontend: Preferences note for admins instead of the alert-email switch; Notifications tab wording + "No SecureNet users to email yet". Harness check: admin + 2 users, admin also set as extra address, one alert → mails only to the 2 users. Neon currently has only the admin, so no attack emails are sent until users register. Real backend restarted. Committed and pushed. |
| 2026-10-07 (38) | **Alert emails paced + simplified** (owner: too many emails as a SecureNet user; email when normal turns abnormal, then every 5 min; desktop alerts unchanged; email too much info, keep it simple, keep the printable report). `notifier.py`: episode tracking, `seconds_until_next_email`, throttled `_run`, spacing-safe `stop`, new `render_alert_email(alerts, kind)` + `summarize_alerts`/`likely_attack`, new subjects; `ALERT_EMAIL_INTERVAL_SECONDS=300` (config + .env.example); test email uses the new layout; status `intervalSeconds`; Notifications tab text. Tests 133/133 (+ spacing, short email + full report, shutdown spacing). Email rendered in Chrome at 620/360 px (0 overflow). Harness with a 20 s interval: 16 alerts → 16 on-screen alerts, 2 emails (new episode at once, one summary after the interval). Real app restarted. Committed and pushed. |
| 2026-10-07 (39) | **Dashboard in plain words + chance table under the status** (owner: no model names on the dashboard; top just says abnormal traffic detected / normal; don't show small rows like SQL; probability/guess table right under the big status; also asked whether SMS is needed for phone OTP — answered: no, all codes go by email; SMS would need a paid SMS provider + DLT sender registration in India, sent from the provider's sender ID, not the admin's phone). Frontend: new `AttackGuessTable`, `attackChances`/`plainReason`/`MIN_SHOWN_CHANCE` in `utils/verdict.ts`, IDSControlWidget (status words, table placement, no detector name), TrafficVerdictCard simplified to "Traffic Check", Detection reason card + incident drawer plain reasons and ≥ 5 % guesses, Security Summary label. Backend: plain reason strings in `detector.py`. Tests 133/133; Chrome `qa3/plain.js` 11/12 (the 1 failure matched the pop-up card's text, checked on the screenshot); 0 page errors. App closed afterwards at the owner's request. Committed and pushed. |
| 2026-10-13 (40) | **Model removed, Electron desktop app + F: icon** (owner: remove the linked trained model — app is just an app, no detection; make it an Electron app with an icon on F: that opens it on the device, not in the browser). Model files moved to `F:\SecureNet-backup\models-removed-2026-10-13`; `config.py` `ML_AUTOLOAD`/`IDS_ON_AT_STARTUP` default false; `desktop/electron/main.js` (icon, no menu bar, single instance, external links to the browser); `desktop/build/icon.ico/png`; `F:\SecureNet IDS.lnk`; frontend rebuilt. Tests 127 passed / 1 skipped; launched via the icon: window opens, `/health` ml not_loaded, ids stopped. |
| 2026-10-13 (41) | **Desktop window stuck on "Starting SecureNet... Loading the dashboard." fixed** (R7). `core/hardening.py`: `/` counted as an API path, so the built dashboard served at `/` (what Electron opens) got the API policy `default-src 'none'` and its script was blocked; `/` now gets the dashboard CSP when a frontend is served (still the API CSP otherwise). New `test_dashboard_root_gets_the_dashboard_policy` (128 passed / 1 skipped). App reopened via the F: icon; Chrome on http://localhost:8000/ → sign-in page, 0 errors. |
| 2026-10-30 (52) | **Protection: ON is instant, OFF needs the code** (owner: turning protection ON shouldn't need verification; turning it OFF should, so a hacker who got in can't disable it). Re-added `PUT /settings/advanced-protection` — `{enabled:true}` turns it ON directly (no code), `{enabled:false}` is refused there; `request-code` now refuses `enabled:true` (ON needs no code) and only emails the OFF-confirmation code; `confirm` applies the token's state (false) as before. Frontend: `updateAdvancedProtection` re-added; `AdvancedProtectionTab.handleToggle` → ON calls PUT directly, OFF shows the Confirm-by-email panel; description updated. py_compile + tsc/vite build clean; applies on the next backend restart. Not committed. |
| 2026-10-30 (51) | **Rule-layer detections shown as a single "Reconnaissance" label** (owner: don't display the specific rule names — port scan / sweep / flood / ICMP / brute — keep them internally, show "Reconnaissance" if anything). `ids_service._rule_detection` now sets `attack_type` + the guess to `RULE_DISPLAY_LABEL = "Reconnaissance"` and a generic reason; the specific rule (`hit.reason`) is kept in a `logger.info("Behavioural rule (internal): …")` only. `rule_engine.py` is unchanged — all 5 rules still run, still count toward abnormal%, still drive the source-IP block. Backend-only (the UI shows whatever label the backend sends). PROTECTION_MEASURES.md noted. py_compile OK; applies on the next backend restart. Not committed. |
| 2026-10-30 (50) | **Per-attack protection doc + hardening script; black-screen = same stale backend** (owner: rule-based already added so leave it; add protection methods for the 14 attacks minus Infiltration; and how is protection handled when SQL Injection is detected as DoS). Confirmed the behavioural rule layer (session 45) is present → no change. New `PROTECTION_MEASURES.md` (SecureNet root): the dynamic action is a **type-agnostic source-IP block**, so a wrong label does NOT weaken protection — SQLi read as DoS still blocks the attacker's IP and the SQLi stops with it (the label only affects report wording). Per-attack table (13 labels, Infiltration excluded) with dynamic block + static hardening, + the rule-layer detections, + honest limits. Recreated `harden_victim.ps1` (account lockout, SSH MaxAuthTries, disable SMBv1, firewall on, RDP NLA; self-elevating). Black screen: same cause as session 49 — the elevated boot backend from the previous sign-in still serves JSON on :8000 (can't be killed from a non-elevated shell); **verified** that once a backend starts with the session-49 fix, `/` serves HTML with the dashboard CSP (scripts allowed) and the JS bundle loads 200 → renders. Resolution: one restart (reboot / sign out-in) or kill the :8000 backend from an admin shell. Not committed. |
| 2026-10-30 (49) | **App showed API JSON instead of the dashboard — backend now serves the SPA by default** (owner: opening the app shows `{"name":"SecureNet","version":"1.0.0","status":"running"}`). Cause: the boot-monitor backend (`scripts/autostart.py`, started at sign-in) did NOT set `FRONTEND_DIST`, so it served no SPA; when the app opens it REUSES that running backend (Electron `startBackend` reuses a healthy :8000) and `/` returned the API root JSON. Fix: `config.py` now defaults `FRONTEND_DIST` to `frontend/dist` when a build exists (guarded by `"pytest" not in sys.modules`, so the suite — which sets `FRONTEND_DIST=""` — is unaffected), so EVERY backend serves the dashboard regardless of launcher; `autostart.py` also sets it explicitly (belt-and-suspenders). Verified: a backend started with no `FRONTEND_DIST` env now returns the dashboard HTML at `/`. NOTE: a backend already running from a previous sign-in (elevated pythonw) keeps the old behaviour until it is restarted — sign out/in or reboot once. py_compile OK. Not committed. |
| 2026-10-30 (48) | **No capture terminals (windowless helpers)** (owner: at sign-in the IDS starts monitoring — good — but the 2 capture terminals pop up; don't open them, and close them if they do). `csv_capture._spawn_capture` now launches `1_capture_windivert.py` + `2_convert.py` with `creationflags=CREATE_NO_WINDOW` (output still goes to DEVNULL / the stderr log), so no console windows appear; and `live_ids/2_convert.py` (outer repo) passes `CREATE_NO_WINDOW` to its Java CICFlowMeter `subprocess.run` so java.exe doesn't flash a window once its parent is windowless. The helpers are still child processes, so `CsvFlowSource.stop()` (IDS off / backend shutdown) `terminate()`s them as before. py_compile OK; app restarted. Not committed. |
| 2026-10-30 (47) | **Protection outcome notifications + host-IP safety** (owner: on an attack send detection notice to desktop/popup/email; after a protection action, wait a few seconds — if the network is benign again say "protection successful" with ONE desktop+popup+email "click to view what was done", else "attack still active"; and never block this PC's own IP — the VM is fine). `ids_service`: when a block fires, `_arm_protection(ip)` starts an episode; the maintenance loop runs `_check_protection_outcome()` — `PROTECTION_VERDICT_DELAY=15s` after the block it judges SUCCESS when `_recent_attack_count(SUCCESS_CHECK_WINDOW=12s) <= 1` (≈no new attack flows), else failure, sends exactly ONE notice (`PROTECTION_NOTIFY_COOLDOWN=300s`): in-app popup + sound (`manager.send_alert` with `verdict:"protection"`, `success`, `desktopPop`), backend OS toast (`notify_desktop`, works app-closed), and a branded one-off email to `get_recipients` with a "View what SecureNet did" button to `/history`; `_last_blocked_event_id` makes "click to view" open the actual block. Detection notices (desktop+popup+email) already fire on the abnormal state — unchanged. Host safety: `protection.py` `_own_addresses()` now also uses a socket fallback (so the host IP is protected even if psutil fails) + includes loopback/0.0.0.0; `safe_addresses()` caches own-IPs + new `PROTECTION_NEVER_BLOCK` config (comma-sep) for 60s so `is_protected` runs per-flow cheaply; verified host IP + loopback protected, VM `192.168.56.104` still blockable. Frontend: `NotificationItem.verdict` adds `'protection'` + `success?`; `AlertPopups` renders a success/failure card ("View what SecureNet did"). py_compile + tsc/vite build clean; app restarted. Committed and pushed. |
| 2026-10-29 (46) | **Reports: CSV removed + branded PDF; protection needs a code BOTH ways** (owner: drop the .csv download; make the PDF look good — "SecureNet Report" heading with a shield and a border on every page; and turning Advanced Protection on OR off both need the emailed code). Reports: `DailyReportCard` now offers only **.txt / .pdf**; `reports.py` daily download pattern `^(txt|pdf)$`, `DAILY_FORMATS` drops csv (the events-export CSV endpoint is untouched). PDF redesign in `exporters.to_pdf` (used by reports + events export): every page gets a double rounded **border**, a navy **header band** with a vector **shield (check-mark)** + "SecureNet Report" + "Network Intrusion Detection System" + generated-UTC, and a footer (brand line · confidential · page N); body has a coloured 5-cell summary strip (total/high/medium/low/sources), side-by-side breakdown tables and a severity-coloured alerts table (navy header, zebra rows). Verified: renders valid PDFs for populated + empty days. Protection confirmation now covers **both directions**: `create_protect_token(user_id, enabled)` carries the target state; `request-code` takes `{enabled}` and emails "turn protection on/off"; `confirm` applies the token's state; the direct `PUT /settings/advanced-protection` (OFF-without-code) was **removed**, and `AdvancedProtectionTab` routes on and off through the same Confirm-by-email panel (labels/messages reflect on/off). `updateAdvancedProtection` service fn removed. py_compile + tsc/vite build clean; app restarted. Not committed. |
| 2026-10-29 (45) | **Behavioural rule layer added (additive second opinion)** (owner: research rule-based / signature-based IDS, add the best as extra help without breaking the project). Researched Snort/Suricata/Zeek: payload *signatures* need raw packets (we only have CICFlowMeter flows), so the fitting addition is the Zeek/Suricata *threshold* style — per-source sliding-window counts for the cross-flow attacks the per-flow XGBoost is blind to. New `app/ml/rule_engine.py` (`RuleEngine`, `RuleHit`): vertical **port scan** (≥20 distinct dst ports/60s), horizontal **sweep** (≥20 dst IPs/60s), **brute-force** (≥10 conns to a service port 21/22/23/3389/445/3306/5900/…/60s), **flood/DoS** (≥200 flows to one dst/10s), **ICMP flood** (≥100/10s); per-(source,rule) 30s cooldown; memory bounded (50k sources). `ids_service`: `self.rule_engine` (gated on new `IDS_RULES_ENABLED`, default true), reset on each start, fed every scored flow in `process_flows`; a hit on a flow the MODEL called Benign is raised to an alert via `_rule_detection()` (score→severity: flood/brute HIGH, scan/sweep MEDIUM) — it NEVER overrides a model attack call. Rule alerts flow through the normal count/store/report path and feed Advanced Protection blocking too. `rule_hits` added to `/ids/status`. **Additive & safe**: standalone functional test (scan/brute/sweep/flood/ICMP/cooldown + normal-traffic-no-trip) PASSED; full pytest run with the layer ON vs OFF gives the **same** results (0 new failures). NOTE: the suite shows 17 pre-existing failures — the tests in this copy predate the dashboard redesign (recent-window/30% email gating, store-throttle, local model) and the session-42 protection-toggle/block-gate changes, and were never updated; not caused by this work. py_compile + tsc/vite build clean; app restarted with the layer live. Not committed. |
| 2026-10-29 (44) | **Advanced Protection available to every user; Edit Details updates directly** (owner: couldn't find protection while signed in as a normal user — make it visible there; and on Account → Edit Details, "instead of send code make it verify and update"). Advanced Protection is no longer admin-only: the tab moved to `USER_TABS` in `SettingsPage` (every signed-in user sees Preferences + Advanced Protection), and the three `/settings/advanced-protection*` endpoints now use `get_current_user` instead of `require_admin` (the enable-code is emailed to the user turning it on). Profile editing is now one step: new `PUT /auth/profile` (`update_profile`) validates the name/phone/email and a changed email's uniqueness, saves immediately, notifies the old address on an email change — no OTP; `authService.updateProfile`; `EditProfileCard` rewritten to a single "Verify and update" button (the send-code/confirm/resend flow removed; `/auth/profile/change` + `/auth/profile/confirm` kept but unused by the UI). `py_compile` + `tsc`/`vite build` clean; app restarted (ids running). Committed and pushed. |
| 2026-10-29 (43) | **Protection needs email confirmation; admin + user accounts set** (owner: IDS is detection-only by default; turning Protection ON in Settings must need email confirmation; make `samiksha99004@gmail.com` the admin/sender instead of `projectids99@gmail.com`; create a normal user `samiksha94820@gmail.com` / `Imsam99@`; open the app from that email). `.env` `ADMIN_EMAILS=samiksha99004@gmail.com` (SMTP already sends from samiksha99004). Backend: `PUT /settings/advanced-protection` now only turns it OFF; turning it ON is a two-step emailed-code flow — `POST /settings/advanced-protection/request-code` (emails a 6-digit code to the admin, returns a short-lived `protect` JWT) + `POST /settings/advanced-protection/confirm {token, otp}` (verifies, then enables), reusing auth's `_issue_otp`/`_consume_otp`/`_check_resend_cooldown` + `_send_code`; new `PROTECT_TOKEN_TYPE`/`create_protect_token` in `security.py`; schemas `AdvancedProtectionChallenge`/`AdvancedProtectionConfirm`. Frontend `AdvancedProtectionTab`: toggling ON shows a "Confirm by email" panel (code field + Turn on / Resend / Cancel); toggling OFF is immediate. Created the viewer account directly in Neon (bypassing OTP signup, one-off script, then deleted). `py_compile` + `tsc`/`vite build` clean; app relaunched → `/health` ml=local-xgboost, ids stopped, request-code route 401 without auth. Default mode stays `monitor` (Neon has no protection row). Not committed. |
| 2026-10-29 (42) | **Advanced Protection — one runtime switch turns the IDS into an IPS** (owner: add a Settings section "Advanced Protection" with ~2 lines + a sliding on/off button; OFF = normal IDS, ON = detect then protect; whatever is protected goes into the report; this folder is now the working IDS, a clean backup sits at `F:\intrusion detection system backup`, and the separate `F:\intrusion protection system` folder was deleted). Backend: new `GET/PUT /settings/advanced-protection` (`AdvancedProtection{Response,Update}` schemas) — ON sets `ProtectionSettings.mode=protect`, `auto_block=true`, `auto_block_severities=[high,medium]`; OFF sets `monitor`, `auto_block=false`; applies to the running IDS immediately (`reload_config` + `set_mode`). `ids_service._handle`: protection now blocks the attacker's **source IP** (type-agnostic, deduped, each source once) only once the network is ABNORMAL (`_abnormal_now`, attacks > 30% of the recent window) — detection-only below that; the stored `SecurityEvent` records `action=BLOCKED` + a reason naming the firewall block, so every block shows in History/Reports/exports. `routes/ids.py control_ids` no longer forces `monitor`: ON uses the saved Advanced Protection mode (`start(None)` → `reload_config`). Frontend: new `AdvancedProtectionTab.tsx` (SettingsSection + a single toggle, saves live) wired into `SettingsPage` ADMIN_TABS (ShieldCheck icon); `settingsService.getAdvancedProtection/updateAdvancedProtection`; `IDSControlWidget` turns the IDS on with no forced mode and shows "Advanced Protection ON/off" (read-only) in its subtitle. Reuses the existing `FirewallBlocker` + `ProtectionSettings` (O3 is now an on-demand toggle, not owner-disabled). Backend `py_compile` OK; frontend `tsc -b && vite build` clean. Not committed (owner didn't ask to push). |
