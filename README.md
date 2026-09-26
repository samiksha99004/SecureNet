# SecureNet — Behavioural Network Intrusion Detection System

SecureNet watches the network traffic of a Windows computer, spots behaviour that looks like an attack and
warns you right away: a pop-up on the dashboard, a Windows notification, and an email with an incident
report attached. Every day that had attacks gets its own downloadable report.

**Website: [samiksha99004.github.io/securenet-site](https://samiksha99004.github.io/securenet-site/)**

Detection uses a two-stage machine-learning design from our research paper: an **Isolation Forest** flags
unusual traffic flows, then **XGBoost** names the attack type (categories from the CICIDS2018 dataset).

> Final-year project by **B. Samiksha, Shraddha V T, Shreshta S S and Siddhi Shetty**, Department of CSE
> (IoT & Cybersecurity with Blockchain), Mangalore Institute of Technology and Engineering.
> Guide: **Dr. Shivananda V. Seeri**.

---

## Contents

1. [Features](#features)
2. [How it works](#how-it-works)
3. [What you need](#what-you-need)
4. [Download](#1-download)
5. [Install and run](#2-first-time-setup)
6. [Using SecureNet](#using-securenet)
7. [Troubleshooting](#troubleshooting)
8. [Project structure](#project-structure)
9. [For developers](#for-developers)

---

## Features

- **Live monitoring**: turn the IDS **ON / OFF** from the dashboard; live score graph, traffic counters and
  a status card. While the IDS is **OFF** the dashboard shows no values at all (every card says
  *"IDS is off"*); past events stay available in History and Reports.
- **Instant alerts**: on-screen pop-ups, a notification bell, an alert sound and Windows desktop notifications
  — each can be switched on or off in *Settings → Preferences* (desktop notifications ask the browser for
  permission the first time).
- **Email alerts**: every registered user gets an email for each attack (grouped into one email when there
  are many), with the incident report attached. The admin gets a detailed copy. Each user can switch their
  own alert emails off and on again (*Settings → Preferences → Attack Alert Emails*).
- **Daily reports**: one box per day with attacks, downloadable as `.txt`, `.csv` or `.pdf`.
- **Incident history**: search, filter, sort and export every detected event.
- **Safe accounts**: every sign-up, **every sign-in**, every password change and every change to your
  personal details is confirmed with a **6-digit code sent to your email** (valid for 5 minutes).
  The email, *"[SecureNet] Sign-in verification code"*, shows the code in a **"Code requested"** panel
  with one box per digit and the whole code once more as plain text — double-click (or long-press on a
  phone) selects it. Email apps never run code, so no email can contain a working copy button; Gmail adds
  its own *Copy code* chip to verification-code emails like these.
  Repeated wrong passwords or codes are blocked.
- **Fast**: the dashboard answers from memory (about 0.1 s) and the cloud database is kept awake while
  SecureNet is in use, so pages don't wait for a far-away database.
- **Stays on**: if you shut down the computer while the IDS is ON, it turns itself back on when you
  start the computer again and shows *"SecureNet is on and is monitoring."*
- **Two roles**: the **Admin** configures detection, email alerts and the whitelist; every other account is a
  **SecureNet User** who can monitor, turn the IDS on/off and download reports.
- **Dark and light (peach) themes**, plain-language screens and a built-in *How to use* guide.

## How it works

```
 Network traffic ──► Packet capture (Scapy + Npcap) ──► traffic "flows" (71 CICIDS2018 features)
                                                            │
                                   Stage 1: Isolation Forest — is this flow unusual?
                                                            │ yes
                                   Stage 2: XGBoost — which attack is it?
                                                            │
      Stored in the database ──► live dashboard (WebSocket) ──► pop-up, desktop notice, email + report
```

| Part | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic, Scapy |
| Detection models | scikit-learn Isolation Forest, XGBoost (optional — see [Detection models](#detection-models-optional)) |
| Database | PostgreSQL in the cloud (a free [Neon](https://neon.tech) database works) |
| Dashboard | React 19 + TypeScript + Vite, Recharts |
| Email | Any SMTP account (Gmail with an App Password is the easiest) |

---

## What you need

| | Why |
|---|---|
| **Windows 10 or 11** | The setup and start scripts, desktop notifications and packet capture are for Windows. |
| **Python 3.11 – 3.14** from [python.org](https://www.python.org/downloads/) | Runs the backend. During installation tick **"Add python.exe to PATH"**. |
| **Internet connection** | To install packages and reach the cloud database. |
| **A free PostgreSQL database** at [neon.tech](https://neon.tech) | SecureNet stores accounts, events and settings there. Each installation uses **its own** database. |
| **A Gmail account with an App Password** | Sign-up / sign-in codes and alert emails are sent from it. |
| **[Npcap](https://npcap.com)** (only for live monitoring) | The Windows packet-capture driver. Everything else works without it. |

You do **not** need to install Node.js: the setup downloads it into the project folder if it is missing.

---

## 1. Download

**Option A — with Git**

```powershell
git clone https://github.com/samiksha99004/SecureNet.git
cd SecureNet
```

**Option B — without Git**: on the GitHub page click **Code → Download ZIP**, then right-click the ZIP →
**Extract All…** and open the extracted folder.

Put the folder anywhere you like (for example `Documents\SecureNet`). Spaces in the path are fine.

## 2. First-time setup

Double-click **`SETUP.bat`**.

On the very first run it creates your own settings file, **`backend\.env`**, with a fresh random secret
key, and stops so you can fill in three things (step 3). Nothing else on your computer is changed: Python
packages go into `backend\venv`, and Node.js (if you don't have it) plus download caches go into the
project's `.local` folder.

## 3. Fill in `backend\.env`

Open `backend\.env` in Notepad and set these values (leave the rest as they are):

**a) Your database — `DATABASE_URL`**

1. Sign up at [neon.tech](https://neon.tech) (free) and create a project.
2. Copy the connection string. It looks like `postgresql://user:password@ep-xyz.aws.neon.tech/neondb?sslmode=require`.
3. Change the beginning to **`postgresql+asyncpg://`** and the ending to **`?ssl=require`**:

```ini
DATABASE_URL=postgresql+asyncpg://user:password@ep-xyz.aws.neon.tech/neondb?ssl=require
```

The tables are created for you in step 4. Local databases (SQLite, `localhost`) are not accepted.

**b) Email — needed to sign up and sign in**

1. In your Google Account turn on **2-Step Verification**.
2. Open [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), create an App Password
   named "SecureNet" and copy the 16 characters.

```ini
EMAIL_ENABLED=true
SMTP_USER=your.address@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
```

**c) Who is the admin — `ADMIN_EMAILS`**

```ini
ADMIN_EMAILS=your.address@gmail.com
```

This account gets the admin settings when it registers. If you leave it empty, the first account you
create becomes the admin.

> `backend\.env` holds your database password and secrets. It is listed in `.gitignore`. **Never upload
> or share it.**

## 4. Run the setup again

Double-click **`SETUP.bat`** again. This time it:

- creates the Python environment and installs the backend packages,
- installs Node.js if needed, plus the dashboard packages,
- connects to your database and **creates (or updates) all tables**,
- tells you whether email works and whether Npcap is installed.

It ends with **"Setup complete"**. You can run `SETUP.bat` again at any time (for example after
downloading a newer version); it only changes what is needed.

## 5. Start SecureNet

Double-click **`START_SECURENET.bat`** every time you want to use SecureNet.

It starts the backend and the dashboard, each in its own window, waits until both are ready and opens
**http://localhost:5173** in your browser. Keep the two windows open; closing them stops SecureNet.

**It won't clash with your other apps.** SecureNet uses port **8000** (backend) and **5173** (dashboard).
If another program or website on your computer already uses one of them, the launcher picks the next
free port (8001…, 5174…), connects both parts to it and opens the right address. It remembers that
choice for next time.

For **live traffic monitoring**, install [Npcap](https://npcap.com) once (tick *"WinPcap API-compatible
Mode"*; leave *"Restrict Npcap driver's access to Administrators only"* unticked), then start SecureNet with
right-click → **Run as administrator**.

---

## Using SecureNet

1. **Create your account**: *Create account* → full name, email, phone → enter the code from your
   email → choose a password.
2. **Sign in**: email + password → enter the **sign-in code** from your email (it works for 5 minutes;
   *Resend code* is available after a minute).
3. **Turn the IDS on**: Dashboard → **ON**. Alerts appear as pop-ups, in the bell, as Windows
   notifications and by email. While the IDS is OFF the dashboard stays empty ("IDS is off") —
   nothing is being watched, so it shows no values.
4. **Look back** (works whether the IDS is on or off): *History* lists every incident; *Reports* has one
   downloadable report per day with attacks.
5. **Your account**: *Account* → change your name, phone, email or password (each confirmed with an
   emailed code). *Settings → Preferences*: theme, pop-ups, sound, desktop notifications on/off and
   attack alert emails on/off.
6. **Admin only**: *Settings* → Detection (sensitivity), Email Alerts (who gets what, test email),
   Whitelist (trusted addresses), Model, System (contact details shown on the Support page).
7. **Shutting down**: if the IDS is ON when you shut down, it turns itself back on after the next start
   and shows a desktop notice. Turn it OFF first if you don't want that.

### Detection models (optional)

Without models SecureNet still captures traffic and counts flows, but it does not score them (the
dashboard says so). To enable detection:

1. Put the trained files in `backend\models\`: `isolation_forest_model.pkl` (or `isolation_forest.pkl`),
   `xgboost_multiclass_model.pkl` (or `xgboost_model.pkl`), `scaler.pkl`, `label_encoder.pkl` and
   `feature_columns.pkl`. Either model on its own also works.
2. From PowerShell in the project folder run `.\SETUP.ps1 -WithML` (installs scikit-learn and XGBoost).
3. Set `ML_AUTOLOAD=true` in `backend\.env` and restart, or, as admin, click
   *Settings → Model → Load / reload models*.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| SETUP says **"backend\.env is missing"** / **"still the example value"** | Fill in `backend\.env` as in [step 3](#3-fill-in-backendenv), then run `SETUP.bat` again. |
| **"Python 3.11-3.14 was not found"** | Install Python from python.org with *"Add python.exe to PATH"* ticked, then run SETUP again. |
| **"Database: cannot connect"** | Check your internet connection and `DATABASE_URL` (it must start with `postgresql+asyncpg://` and end with `?ssl=require`). |
| **No code arrives** / *"SecureNet can't send emails yet"* | Check `EMAIL_ENABLED=true`, `SMTP_USER` and the 16-character App Password. Look in the spam folder. Restart SecureNet after editing `.env`. |
| **"The code has expired"** | Codes are valid for 5 minutes. Use *Resend code*. |
| **"Too many failed attempts"** | Wait the minutes shown, or use *Forgot password?* |
| **IDS says it can't start on this computer yet** | Install Npcap and start SecureNet with *Run as administrator*. |
| **"The Python environment … was copied from another PC"** | Run `SETUP.bat`; it rebuilds `backend\venv` for this computer. |
| **A port message** | Another program uses 8000 / 5173; SecureNet moved to the next free port automatically. Use the address the launcher prints. |
| **Blank page or "can't be reached"** | Make sure both SecureNet windows are open (or run `START_SECURENET.bat` again) and reload the page. |

---

## Project structure

```
SecureNet/
├── SETUP.bat / SETUP.ps1                 one-time setup (safe to re-run)
├── START_SECURENET.bat / .ps1            starts backend + dashboard, picks free ports, opens the browser
├── scripts/securenet-env.ps1             shared helpers (tool folders, Node/Python lookup, ports)
├── backend/                              FastAPI service (Python)
│   ├── app/api/routes/                   REST API: auth, dashboard, events, ids, reports, settings, support …
│   ├── app/ml/                           packet capture, flow features, detector, live IDS loop
│   ├── app/services/                     email alerts, reports, exports, IDS auto-start
│   ├── alembic/                          database migrations (run by SETUP)
│   ├── scripts/                          setup check, Windows start-up helper
│   ├── tests/                            automated tests (temporary database, never your real one)
│   └── .env.example                      template for your backend\.env
├── frontend/                             React + TypeScript dashboard (Vite)
├── desktop/                              optional Electron desktop shell
├── website/                              the public SecureNet website (HTML/CSS/JS) + publish.ps1
├── docs/                                 QA report and archived notes
└── CLAUDE.md                             full technical guide, issue register and change log
```

## Website

The public website lives in [`website/`](website/) — plain HTML, CSS and JavaScript with a sidebar like the
app: Download, About SecureNet, the two models, the app, a technology timeline, About us and Contact us. It is
served by GitHub Pages at **https://samiksha99004.github.io/securenet-site/** from the public repository
`samiksha99004/securenet-site`. After changing it, publish with
`powershell -ExecutionPolicy Bypass -File website\publish.ps1 "What changed"` (see `website/README.md`).

## For developers

```powershell
# backend tests (use a temporary database — never the one in backend\.env)
cd backend
.\venv\Scripts\python.exe -m pytest

# dashboard: type-check, lint and production build (Node from .local\tools\node or your own install)
cd ..\frontend
npm run lint
npm run build
```

- API: all routes are under `/api` (e.g. `/api/auth/login`, `/api/events`, `/api/reports/daily`), the live
  stream is the WebSocket `/ws/live`, and `/health` reports the backend state. Interactive API docs are at
  `/api/docs` when `DEBUG=true`.
- Architecture, API list, roles, security rules and the full change log: [CLAUDE.md](CLAUDE.md).
- Latest test report: [docs/QA_REPORT_2026-09-25.md](docs/QA_REPORT_2026-09-25.md).
