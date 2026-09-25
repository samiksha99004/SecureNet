# SecureNet — Behavioural Network Intrusion Detection System

SecureNet watches the network traffic of a Windows PC, flags suspicious behaviour and warns its users with
on-screen alerts and emails that carry an incident report. Detection follows a two-stage design:
**Isolation Forest** finds unusual traffic flows, then **XGBoost** names the attack type (CICIDS2018 categories).

Final-year project: B. Samiksha, Shraddha V T, Shreshta S S and Siddhi Shetty. Dept. of CSE (IoT & Cybersecurity
with Blockchain), Mangalore Institute of Technology and Engineering. Guide: Dr. Shivananda V. Seeri.

## Folder layout

```
├── backend/     FastAPI service: live capture, detection, sign-in with emailed codes, alerts, reports (Python)
├── frontend/    SecureNet dashboard: React + TypeScript + Vite (dark and peach themes)
├── desktop/     Optional Electron shell that opens the dashboard as a desktop app
├── scripts/     Helpers shared by the setup and start scripts
├── docs/        Archived notes from earlier versions (historical only)
├── SETUP.bat            One-time setup on any Windows PC
├── START_SECURENET.bat  Starts the backend and the dashboard, then opens the browser
└── CLAUDE.md            Full technical guide, issue register and change log
```

## Getting started (Windows)

1. Install Python 3.11–3.14 from python.org. Node.js is downloaded by the setup if it is missing.
2. Put your `backend\.env` in place (database, sign-in secret and email settings). It is never committed;
   start from `backend\.env.example`.
3. Double-click **`SETUP.bat`** once.
4. Double-click **`START_SECURENET.bat`** every time. For live traffic capture, install
   [Npcap](https://npcap.com) and run it as Administrator.

The dashboard opens at <http://localhost:5173>, and the backend runs on <http://127.0.0.1:8000>.

## Tests

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest      # uses a temporary database, never the real one
cd ..\frontend
npm run build                            # type-check + production build
```

See [CLAUDE.md](CLAUDE.md) for the architecture, API, roles, email alerts and current status.
