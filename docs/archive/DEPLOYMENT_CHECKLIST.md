# SecureNet IDS - Deployment Checklist

## Pre-Deployment Setup

### System Requirements
- [ ] Windows 10/11 (64-bit)
- [ ] Python 3.10+ installed
- [ ] PostgreSQL 13+ installed and running
- [ ] Node.js 16+ installed
- [ ] Administrator privileges available
- [ ] Minimum 4GB RAM
- [ ] Minimum 10GB free disk space

### Software Installation
- [ ] Npcap installed (https://npcap.com/#download)
  - [ ] "WinPcap API-compatible Mode" enabled during install
  - [ ] System restarted after installation
- [ ] Python virtual environment created (`backend/venv`)
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Node modules installed (`npm install` in frontend directory)

### ML Models Verification
- [ ] `F:\all_10_csv_manual` directory exists
- [ ] `isolation_forest_model.pkl` present
- [ ] `xgboost_hybrid_model.pkl` present
- [ ] `xgboost_multiclass_model.pkl` present
- [ ] `label_encoder.pkl` present
- [ ] `feature_columns.pkl` present
- [ ] `xgboost_threshold.pkl` present
- [ ] `scaler.pkl` present (optional)

## Database Setup

### PostgreSQL Configuration
- [ ] PostgreSQL service running
- [ ] Database `securenet` created
- [ ] User `securenet` created with password
- [ ] User granted all privileges on database
- [ ] Connection test successful: `psql -U securenet -d securenet`

### Backend Database Setup
- [ ] `.env` file created from `.env.example`
- [ ] `DATABASE_URL` configured correctly
- [ ] Alembic migrations applied: `alembic upgrade head`
- [ ] Tables verified in PostgreSQL:
  ```sql
  SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
  ```
  Expected tables:
  - [ ] users
  - [ ] security_events
  - [ ] event_features
  - [ ] detection_settings
  - [ ] protection_settings
  - [ ] notification_settings
  - [ ] system_settings
  - [ ] whitelist_entries
  - [ ] otps
  - [ ] reports

## Backend Configuration

### Environment Variables (`.env`)
- [ ] `DATABASE_URL` - PostgreSQL connection string
- [ ] `JWT_SECRET` - Strong random string (min 32 chars)
- [ ] `CORS_ORIGINS` - Frontend URL (http://localhost:5173)
- [ ] `EMAIL_ENABLED` - false for development
- [ ] `DETECTION_ENABLED` - true
- [ ] `DETECTION_MODE` - monitor or protect
- [ ] All other required variables set

### Backend Verification
- [ ] Backend starts without errors: `uvicorn app.main:app --reload`
- [ ] Logs show: "✓ ML models loaded successfully"
- [ ] Logs show: "✓ IDS service initialized"
- [ ] Health check returns OK: `http://localhost:8000/health`
- [ ] API docs accessible: `http://localhost:8000/api/docs`

## Frontend Configuration

### Environment Variables (`.env.local`)
- [ ] `VITE_API_BASE_URL` - Backend API URL (http://localhost:8000/api)
- [ ] `VITE_WS_URL` - WebSocket URL (ws://localhost:8000/ws)

### Frontend Verification
- [ ] Frontend starts without errors: `npm run dev`
- [ ] Frontend accessible: `http://localhost:5173`
- [ ] No console errors in browser developer tools
- [ ] API calls successfully reach backend

## User Account Setup

### First User Registration
- [ ] Navigate to signup page
- [ ] Register admin account
- [ ] OTP received (check backend console if EMAIL_ENABLED=false)
- [ ] OTP verified successfully
- [ ] Login successful
- [ ] JWT token received and stored
- [ ] Dashboard accessible

### Role Verification
- [ ] User has appropriate role (admin/analyst for IDS control)
- [ ] Protected routes require authentication
- [ ] Unauthorized access blocked

## IDS Functionality Testing

### ML Models
- [ ] GET `/api/model/info` shows models as "loaded"
- [ ] 71 features listed
- [ ] 14 attack types listed
- [ ] No "not_loaded" status

### IDS Control
- [ ] GET `/api/ids/status` returns status
- [ ] Initially shows `enabled: false`
- [ ] Shows `mlLoaded: true`
- [ ] POST `/api/ids/control` with `{enabled: true}` starts IDS
- [ ] Backend logs show "✓ IDS started successfully"
- [ ] Status endpoint shows `enabled: true`

### Network Monitoring
- [ ] Packet counts increasing when IDS running
- [ ] Flow counts increasing
- [ ] No "permission denied" errors
- [ ] No "Scapy not available" errors

### Detection Testing
- [ ] Generate test traffic (ping, web browsing)
- [ ] Wait 30-60 seconds
- [ ] Check events: GET `/api/events`
- [ ] Verify events in database:
  ```sql
  SELECT COUNT(*) FROM security_events;
  ```
- [ ] Events show real data (no zeros or nulls where data should exist)

### Protection Testing (Optional)
- [ ] Set mode to "protect": `{enabled: true, mode: "protect"}`
- [ ] Generate suspicious traffic (port scan)
- [ ] High-severity events show `actionTaken: "blocked"`
- [ ] Firewall rule created (check with `netsh advfirewall firewall show rule name=all`)

### Whitelist Testing
- [ ] Add IP to whitelist: POST `/api/settings/whitelist`
- [ ] Generate traffic from whitelisted IP
- [ ] Verify no events created for whitelisted IP

## Integration Verification

### API Endpoints
- [ ] All auth endpoints working
- [ ] All event endpoints working
- [ ] All dashboard endpoints working
- [ ] All settings endpoints working
- [ ] All model endpoints working
- [ ] All report endpoints working
- [ ] All IDS endpoints working

### Database Persistence
- [ ] Users persisted
- [ ] Security events persisted
- [ ] Settings persisted
- [ ] Whitelist entries persisted
- [ ] Reports persisted
- [ ] OTPs persisted

### WebSocket (When Implemented)
- [ ] WebSocket connection established
- [ ] Live events broadcast to frontend
- [ ] Disconnection handled gracefully
- [ ] Reconnection works

## Performance Verification

### Resource Usage
- [ ] CPU usage acceptable (< 50% for low traffic)
- [ ] Memory usage acceptable (< 1GB)
- [ ] Disk I/O acceptable
- [ ] Network capture not dropping packets

### Response Times
- [ ] Health check < 100ms
- [ ] API endpoints < 500ms
- [ ] ML inference < 100ms per flow
- [ ] Database queries < 200ms

### Scalability
- [ ] System handles sustained traffic
- [ ] No memory leaks over time
- [ ] Database grows as expected
- [ ] No crash under load

## Security Verification

### Authentication
- [ ] JWT tokens expire correctly
- [ ] Expired tokens rejected
- [ ] Invalid tokens rejected
- [ ] Password hashing working (bcrypt)
- [ ] OTP expiration enforced
- [ ] OTP max attempts enforced

### Authorization
- [ ] Protected routes require auth
- [ ] Role-based access enforced
- [ ] Users cannot access unauthorized resources

### Data Protection
- [ ] No passwords in logs
- [ ] No secrets in frontend code
- [ ] HTTPS recommended for production
- [ ] Database credentials not exposed

## Production Readiness (Optional)

### Performance Optimization
- [ ] Database indexes optimized
- [ ] Query performance acceptable
- [ ] Caching implemented where needed
- [ ] Connection pooling configured

### Monitoring
- [ ] Logging configured appropriately
- [ ] Error tracking set up
- [ ] Performance monitoring enabled
- [ ] Alerting configured

### Backup & Recovery
- [ ] Database backup strategy defined
- [ ] Backup tested and verified
- [ ] Recovery procedure documented
- [ ] Disaster recovery plan in place

### Documentation
- [ ] User manual created
- [ ] API documentation complete
- [ ] Deployment guide written
- [ ] Troubleshooting guide available

## Common Issues Resolved

### Issue: "Scapy not available"
- [ ] Fixed by: `pip install scapy`

### Issue: "WinPcap error"
- [ ] Fixed by: Installing Npcap with WinPcap compatibility

### Issue: "Permission denied"
- [ ] Fixed by: Running as Administrator

### Issue: "ML models not loaded"
- [ ] Fixed by: Verifying file paths in `F:\all_10_csv_manual`

### Issue: "Database connection failed"
- [ ] Fixed by: Starting PostgreSQL and verifying DATABASE_URL

### Issue: "No packets captured"
- [ ] Fixed by: Checking network interface and permissions

### Issue: "Too many false positives"
- [ ] Fixed by: Adjusting threshold or adding to whitelist

## Sign-Off

### Development Team
- [ ] Backend implementation verified
- [ ] Frontend integration verified
- [ ] ML models verified
- [ ] Testing completed
- [ ] Documentation complete

### QA Team
- [ ] Functional testing passed
- [ ] Performance testing passed
- [ ] Security testing passed
- [ ] User acceptance testing passed

### Deployment Team
- [ ] Environment configured
- [ ] Dependencies installed
- [ ] Services running
- [ ] Monitoring active

### Final Approval
- [ ] All critical tests passed
- [ ] No blocking issues
- [ ] Documentation complete
- [ ] Ready for production (or next phase)

---

## Deployment Date: _______________

## Deployed By: _______________

## Notes:
```
[Add any deployment-specific notes here]
```

---

**Checklist Version:** 1.0  
**Last Updated:** January 2024  
**Next Review:** [Set date for next review]
