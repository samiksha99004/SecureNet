# SecureNet IDS - Quick Start Guide

## 🚀 Start Application in 3 Steps

### Step 1: Backend is Already Running ✅
```
Backend: http://127.0.0.1:8000
Status: Operational
Database: Neon PostgreSQL (connected)
ML Models: Loaded
```

### Step 2: Start Frontend
```powershell
cd "F:\SecureNet (3)\SecureNet (2)\SecureNet\frontend"
npm run dev
```
**Frontend will be available at:** http://localhost:5173

### Step 3: Login
```
URL: http://localhost:5173
Email: admin@securenet.com
Password: Admin@123456
```

---

## 📊 What You'll See

### Dashboard
- **5 sample security events** already loaded
- Real-time statistics (when IDS is enabled)
- Attack type distribution charts
- Severity breakdowns

### Security Events
- SQL Injection attack (HIGH)
- DoS attacks-Slowloris (HIGH)
- SSH-Bruteforce (MEDIUM)
- Brute Force -Web (MEDIUM)
- Bot (LOW)

### Settings
- Detection settings (already configured)
- Protection mode (set to PROTECT)
- Notification preferences
- System configuration

---

## 🔧 Common Tasks

### Enable IDS Monitoring
1. Go to Dashboard
2. Toggle "IDS Status" switch to ON
3. System will start monitoring network traffic

### View Security Events
1. Click "History" in sidebar
2. Filter by severity, attack type, or date
3. Click event to see details

### Change Settings
1. Click "Settings" in sidebar
2. Modify detection sensitivity
3. Configure auto-blocking
4. Save changes

### Generate Report
1. Go to "Reports" page
2. Set date range
3. Click "Generate Report"
4. Download PDF

---

## 🧪 Test API Directly

### Health Check
```powershell
curl http://localhost:8000/health
```

### Login (get JWT token)
```powershell
curl -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@securenet.com","password":"Admin@123456"}'
```

### Get Security Events
```powershell
$token = "YOUR_JWT_TOKEN"
curl http://localhost:8000/api/events `
  -H "Authorization: Bearer $token"
```

---

## 📝 Test Accounts

| Role | Email | Password | What You Can Do |
|------|-------|----------|----------------|
| **Admin** | admin@securenet.com | Admin@123456 | Everything |
| **Analyst** | analyst@securenet.com | Analyst@123456 | View, analyze, control IDS |
| **Viewer** | viewer@securenet.com | Viewer@123456 | View only (read-only) |

---

## 🛠️ Troubleshooting

### Backend Not Responding
```powershell
# Check if running
curl http://localhost:8000/health

# If not, restart:
cd "F:\SecureNet (3)\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend Can't Connect
1. Check `.env` file has: `VITE_API_BASE_URL=http://localhost:8000/api`
2. Restart frontend: `npm run dev`
3. Clear browser cache

### Login Fails
- Check backend is running
- Verify database connection in backend logs
- Try password: `Admin@123456` (case-sensitive)

---

## 📂 Project Structure

```
F:\SecureNet (3)
├── backend/                    # FastAPI backend
│   ├── app/                   # Application code
│   ├── alembic/              # Database migrations
│   ├── .env                   # Configuration (Neon PostgreSQL)
│   └── requirements.txt       # Python dependencies
│
├── SecureNet (2)/SecureNet/frontend/  # React frontend
│   ├── src/                  # Source code
│   ├── dist/                 # Built files
│   ├── .env                   # Frontend config
│   └── package.json           # Node dependencies
│
└── models/                    # ML models (XGBoost, IF)
```

---

## ✅ System Status

- ✅ **Database:** Neon PostgreSQL (cloud)
- ✅ **Backend:** Running on port 8000
- ✅ **ML Models:** Loaded (71→72 features)
- ✅ **Sample Data:** 5 events + 3 test users
- ✅ **APIs:** All 16 endpoints operational
- ✅ **Frontend:** Built successfully

---

## 🎯 Quick Feature Test

1. **Login** → Use admin@securenet.com / Admin@123456
2. **Dashboard** → See 5 sample events, charts, statistics
3. **History** → View and filter security events
4. **Settings** → Modify detection/protection settings
5. **IDS Control** → Toggle monitoring ON/OFF (top-right)

---

## 📞 Need Help?

Check these files:
- `NEON_POSTGRESQL_MIGRATION_COMPLETE.md` - Full setup details
- Backend logs - Console where uvicorn is running
- Frontend logs - Browser DevTools Console

**Everything is ready to use! Just start the frontend and login.** 🚀
