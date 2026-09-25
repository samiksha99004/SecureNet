# SecureNet Backend-Frontend Integration Guide

Complete guide for integrating the SecureNet backend with the existing frontend.

## Prerequisites

✅ Backend running at `http://localhost:8000`  
✅ PostgreSQL database created and migrated  
✅ Frontend project located at `../SecureNet/frontend`

## Integration Steps

### Step 1: Backend Configuration

Edit `backend/.env`:

```env
# Backend URL (where FastAPI runs)
HOST=0.0.0.0
PORT=8000

# Frontend URL (for CORS)
CORS_ORIGINS=http://localhost:5173

# Database
DATABASE_URL=postgresql+asyncpg://securenet:password@localhost:5432/securenet

# JWT Secret (generate a strong random string)
JWT_SECRET=your-super-secret-key-min-32-characters-long

# Email (for OTP - set to false for development)
EMAIL_ENABLED=false
```

### Step 2: Frontend Configuration

Edit `frontend/.env.local`:

```env
# Backend API URL
VITE_API_BASE_URL=http://localhost:8000/api

# WebSocket URL (for live monitoring)
VITE_WS_URL=ws://localhost:8000/ws
```

### Step 3: Start Backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Output should show:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     SecureNet v1.0.0 starting up...
INFO:     Environment: production
INFO:     Debug mode: False
```

### Step 4: Start Frontend

```powershell
cd ..\SecureNet\frontend
npm run dev
```

Output should show:
```
VITE v4.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
```

### Step 5: Verify Integration

Open browser to: `http://localhost:5173`

## Testing the Integration

### Test 1: User Registration

1. Navigate to `/signup`
2. Fill in registration form:
   - Full Name: Test User
   - Email: test@example.com
   - Password: Test1234
3. Click "Sign Up"

**Expected**: 
- Success message
- OTP logged in backend console (if EMAIL_ENABLED=false)
- Redirected to OTP verification page

**Backend Logs**:
```
INFO - [DEV] OTP for test@example.com: 123456
INFO - User registered: test@example.com
```

### Test 2: OTP Verification

1. Check backend console for OTP code
2. Enter the 6-digit code
3. Click "Verify"

**Expected**:
- Account activated
- Auto-login with JWT tokens
- Redirected to dashboard

**Backend Logs**:
```
INFO - OTP verified for: test@example.com
```

### Test 3: Login

1. Navigate to `/login`
2. Enter credentials
3. Click "Login"

**Expected**:
- JWT tokens received
- User data stored
- Redirected to dashboard

### Test 4: Dashboard Data

Dashboard should load and display:
- ✅ Active Flows: 0 (no events yet)
- ✅ Anomalies Last Hour: 0
- ✅ High Severity Count: 0
- ✅ Average Anomaly Score: 0.0
- ✅ Severity Breakdown: All zeros
- ✅ Recent Events: Empty list
- ✅ Protocol Distribution: All zeros

**This is correct** - no fake data is generated.

### Test 5: Settings Pages

Navigate to each settings page:

1. `/settings/detection` - Should load default detection settings
2. `/settings/protection` - Should load default protection settings
3. `/settings/notifications` - Should load default notification settings
4. `/settings/system` - Should load default system settings

Try updating a setting and verify it persists.

### Test 6: Whitelist Management

1. Go to `/settings/whitelist`
2. Click "Add Entry"
3. Add a test IP: `192.168.1.100`
4. Verify it appears in the list
5. Delete it

**Expected**: 
- Entry persists in database
- Backend logs show creation/deletion

### Test 7: Account Settings

1. Go to `/account`
2. View profile information
3. Try changing password

**Expected**:
- User info displayed correctly
- Password change works (verify by logging out and back in)

### Test 8: Model Information

1. Go to `/model`

**Expected**:
- Isolation Forest: Status "not_loaded" (until models are added)
- XGBoost: Status "not_loaded"
- Feature Count: 78

## API Contract Verification

### Authentication Flow

```
POST /api/auth/signup
  → 200 OK: { "message": "Registration successful..." }

POST /api/auth/otp/verify
  → 200 OK: { 
      "verified": true, 
      "authResponse": {
        "user": { ... },
        "tokens": { ... }
      }
    }

POST /api/auth/login
  → 200 OK: { "user": { ... }, "tokens": { ... } }

GET /api/auth/me (with Bearer token)
  → 200 OK: { "id": "...", "email": "...", ... }
```

### Dashboard Flow

```
GET /api/dashboard/summary
  → 200 OK: {
      "activeFlows": 0,
      "anomaliesLastHour": 0,
      ...
    }

GET /api/dashboard/protocol-distribution
  → 200 OK: {
      "tcp": 0,
      "udp": 0,
      "icmp": 0,
      "other": 0,
      "totalFlows": 0
    }
```

### Events Flow

```
GET /api/events?page=1&pageSize=20
  → 200 OK: {
      "data": [],
      "total": 0,
      "page": 1,
      "pageSize": 20,
      "totalPages": 0
    }
```

## Common Issues & Solutions

### Issue: CORS Error

**Symptom**: 
```
Access to fetch at 'http://localhost:8000/api/...' from origin 'http://localhost:5173' 
has been blocked by CORS policy
```

**Solution**:
1. Check `CORS_ORIGINS` in backend `.env` includes `http://localhost:5173`
2. Restart backend server
3. Clear browser cache

### Issue: 401 Unauthorized

**Symptom**: Protected endpoints return 401 even after login

**Solution**:
1. Check browser localStorage for `sn_access_token`
2. Verify token is being sent in Authorization header
3. Check JWT_SECRET is consistent
4. Token may have expired - try logging in again

### Issue: 422 Validation Error

**Symptom**: API returns validation errors

**Solution**:
1. Check request payload matches schema
2. Verify camelCase field names in frontend
3. Check required fields are present
4. Verify data types match

### Issue: Empty Dashboard

**Symptom**: Dashboard shows all zeros

**Solution**:
This is **correct behavior** - no security events exist yet.

To populate with test data:
1. Manually insert events via SQL, or
2. Implement network capture module, or
3. Use API to create test events

### Issue: OTP Not Received

**Symptom**: No OTP code after signup

**Solution**:
1. Check backend console logs (development mode)
2. If EMAIL_ENABLED=false, OTP is logged to console
3. If EMAIL_ENABLED=true, check SMTP configuration
4. Look for: `[DEV] OTP for email@example.com: 123456`

## Database Inspection

### View Users

```sql
SELECT id, email, full_name, role, account_status, created_at 
FROM users;
```

### View Security Events

```sql
SELECT id, timestamp, source_ip, destination_ip, severity, attack_type 
FROM security_events 
ORDER BY timestamp DESC 
LIMIT 10;
```

### View Settings

```sql
SELECT * FROM detection_settings;
SELECT * FROM protection_settings;
SELECT * FROM notification_settings;
```

### View OTPs (Development)

```sql
SELECT email, otp_code, created_at, expires_at, is_used 
FROM otps 
ORDER BY created_at DESC;
```

## API Testing with cURL

### Register User

```powershell
curl -X POST http://localhost:8000/api/auth/signup `
  -H "Content-Type: application/json" `
  -d '{
    "fullName": "Test User",
    "email": "test@example.com",
    "password": "Test1234",
    "confirmPassword": "Test1234"
  }'
```

### Verify OTP

```powershell
curl -X POST http://localhost:8000/api/auth/otp/verify `
  -H "Content-Type: application/json" `
  -d '{
    "email": "test@example.com",
    "otp": "123456"
  }'
```

### Login

```powershell
curl -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{
    "email": "test@example.com",
    "password": "Test1234"
  }'
```

### Get Dashboard (with token)

```powershell
$token = "your_jwt_token_here"
curl -X GET http://localhost:8000/api/dashboard/summary `
  -H "Authorization: Bearer $token"
```

## Performance Verification

### Response Times (Expected)

- Authentication: < 200ms
- Dashboard summary: < 100ms (empty DB)
- Event list: < 50ms (empty DB)
- Settings read: < 50ms
- Health check: < 10ms

### Database Query Performance

```sql
-- Check for missing indexes
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public';

-- Check slow queries (enable logging)
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

## Security Verification

### JWT Token Inspection

Decode token at https://jwt.io/

Should contain:
```json
{
  "sub": "user-uuid",
  "exp": 1234567890,
  "iat": 1234567890,
  "type": "access"
}
```

### Password Security

```sql
-- Verify passwords are hashed
SELECT email, 
       length(password_hash) as hash_length,
       substring(password_hash from 1 for 7) as hash_prefix
FROM users;
```

Expected:
- Hash length: ~60 characters
- Prefix: `$2b$` (bcrypt)

## Next Integration Steps

### 1. Add Test Security Events

Create a script to insert sample events:

```python
from app.models.security_event import SecurityEvent, SeverityLevel, Protocol

event = SecurityEvent(
    source_ip="192.168.1.100",
    source_port=54321,
    destination_ip="10.0.0.50",
    destination_port=80,
    protocol=Protocol.TCP,
    anomaly_score=0.85,
    severity=SeverityLevel.HIGH,
    attack_type="Port Scan",
    confidence=0.92,
    # ... other fields
)
```

### 2. Integrate ML Models

See `app/ml/README.md` for ML integration guide.

### 3. Set up Network Capture

Implement network traffic capture and feature extraction.

### 4. Enable WebSocket

Implement WebSocket endpoint for real-time updates.

### 5. Configure Email

Set up SMTP for production OTP delivery.

## Monitoring Integration

### Application Logs

```powershell
# Watch logs in real-time
Get-Content backend/logs/securenet.log -Wait -Tail 50
```

### Database Monitoring

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Database size
SELECT pg_size_pretty(pg_database_size('securenet'));

-- Table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Success Criteria

✅ User registration works end-to-end  
✅ OTP verification completes successfully  
✅ Login returns JWT tokens  
✅ Protected routes require authentication  
✅ Dashboard loads without errors  
✅ Settings can be viewed and updated  
✅ Whitelist management works  
✅ All API responses match frontend contracts  
✅ No CORS errors  
✅ No console errors in frontend  
✅ Database persists all changes  

## Support

If you encounter issues not covered here:

1. Check backend logs for errors
2. Check browser console for frontend errors
3. Verify database connectivity
4. Verify environment configuration
5. Review `IMPLEMENTATION_STATUS.md` for feature status

---

**Integration Status**: ✅ Ready for frontend connection  
**Core APIs**: ✅ Fully implemented  
**Database**: ✅ Schema complete  
**Authentication**: ✅ Working  
**Next**: ML models + network capture
