# SecureNet IDS - Testing & Verification Guide

## Prerequisites

Before testing, ensure:

1. ✅ PostgreSQL is running
2. ✅ Backend virtual environment is set up
3. ✅ Database migrations are applied
4. ✅ ML models exist in `F:\all_10_csv_manual`
5. ✅ Npcap is installed (for Scapy)
6. ✅ Running PowerShell as **Administrator**

## Quick Start

### Option 1: Automated Startup

```powershell
# Run as Administrator!
.\START_SECURENET.ps1
```

This script:
- Checks all prerequisites
- Starts PostgreSQL (if not running)
- Starts backend on port 8000
- Starts frontend on port 5173
- Shows real-time status

### Option 2: Manual Startup

**Terminal 1 - Backend:**
```powershell
# Run PowerShell as Administrator!
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```powershell
cd "SecureNet (2)\SecureNet\frontend"
npm run dev
```

## Verification Tests

### Test 1: Backend Health Check

```powershell
curl http://localhost:8000/health
```

**Expected Output:**
```json
{
  "status": "ok",
  "database": "connected",
  "ml": "available",
  "version": "1.0.0"
}
```

✅ **Pass Criteria:** Status is "ok", database is "connected"

### Test 2: ML Models Loaded

**API Call:**
```
GET http://localhost:8000/api/model/info
```

**Expected Output:**
```json
{
  "isolationForest": {
    "status": "loaded",
    "featureCount": 71,
    "nEstimators": 100,
    "contamination": 0.05
  },
  "xgboost": {
    "status": "loaded",
    "n_classes": 14,
    "supportedAttackClasses": [
      "Bot",
      "Brute Force -Web",
      "Brute Force -XSS",
      "DDOS attack-HOIC",
      "DDOS attack-LOIC-UDP",
      "DDoS attacks-LOIC-HTTP",
      "DoS attacks-GoldenEye",
      "DoS attacks-Hulk",
      "DoS attacks-SlowHTTPTest",
      "DoS attacks-Slowloris",
      "FTP-BruteForce",
      "SQL Injection",
      "SSH-Bruteforce"
    ]
  }
}
```

✅ **Pass Criteria:** Both models show "loaded" status, 71 features, 14 attack classes

### Test 3: User Authentication

**Step 1: Register**
```
POST http://localhost:8000/api/auth/signup
Content-Type: application/json

{
  "fullName": "Test Admin",
  "email": "admin@test.com",
  "password": "Test1234",
  "confirmPassword": "Test1234"
}
```

**Expected:** OTP code logged to backend console

**Step 2: Get OTP from console**
Look for log line:
```
INFO - [DEV] OTP for admin@test.com: 123456
```

**Step 3: Verify OTP**
```
POST http://localhost:8000/api/auth/otp/verify
Content-Type: application/json

{
  "email": "admin@test.com",
  "otp": "123456"
}
```

**Expected:** JWT tokens returned, account activated

✅ **Pass Criteria:** Login successful, tokens received

### Test 4: IDS Status (Before Start)

**API Call:**
```
GET http://localhost:8000/api/ids/status
Authorization: Bearer {your_token}
```

**Expected Output:**
```json
{
  "enabled": false,
  "mode": "monitor",
  "mlLoaded": true,
  "packetsProcessed": 0,
  "flowsAnalyzed": 0,
  "anomaliesDetected": 0,
  "attacksDetected": 0
}
```

✅ **Pass Criteria:** `enabled: false`, `mlLoaded: true`

### Test 5: Start IDS

**API Call:**
```
POST http://localhost:8000/api/ids/control
Authorization: Bearer {your_token}
Content-Type: application/json

{
  "enabled": true,
  "mode": "monitor"
}
```

**Expected Output:**
```json
{
  "enabled": true,
  "mode": "monitor",
  "mlLoaded": true,
  "packetsProcessed": 0,
  "flowsAnalyzed": 0,
  "anomaliesDetected": 0,
  "attacksDetected": 0
}
```

**Backend Console:**
```
INFO - Starting IDS...
INFO - Network monitor started
INFO - ✓ IDS started successfully
```

✅ **Pass Criteria:** `enabled: true`, no errors in console

### Test 6: Generate Network Traffic

Open multiple terminal windows and generate traffic:

**Terminal 1: ICMP (Normal)**
```powershell
ping 8.8.8.8 -t
```

**Terminal 2: HTTP (Normal)**
```powershell
# Browse websites or:
curl https://www.google.com
curl https://www.github.com
```

**Terminal 3: Large Download (Might trigger anomaly)**
```powershell
# Download a large file
Invoke-WebRequest -Uri "http://ipv4.download.thinkbroadband.com/100MB.zip" -OutFile test.zip
```

**Terminal 4: Port Scan (Should trigger anomaly)**
```powershell
# If nmap is installed:
nmap -p 1-1000 localhost

# Or use PowerShell:
1..100 | ForEach-Object {
    Test-NetConnection -ComputerName localhost -Port $_ -WarningAction SilentlyContinue
}
```

### Test 7: Monitor IDS Activity

**Check Status Periodically:**
```
GET http://localhost:8000/api/ids/status
```

**Expected:** Numbers increasing:
```json
{
  "packetsProcessed": 1523,
  "flowsAnalyzed": 45,
  "anomaliesDetected": 2,
  "attacksDetected": 1
}
```

✅ **Pass Criteria:** Packet counts increasing, flows being analyzed

### Test 8: Check Security Events

**API Call:**
```
GET http://localhost:8000/api/events?page=1&pageSize=20
Authorization: Bearer {your_token}
```

**Expected:** List of detected events (if any anomalies found):
```json
{
  "data": [
    {
      "id": "uuid",
      "timestamp": "2024-01-15T14:23:45.123Z",
      "sourceIp": "192.168.1.100",
      "sourcePort": 54321,
      "destinationIp": "8.8.8.8",
      "destinationPort": 80,
      "protocol": "TCP",
      "anomalyScore": 0.87,
      "severity": "high",
      "attackType": "DoS attacks-Hulk",
      "confidence": 0.92,
      "mode": "monitor",
      "state": "active",
      "actionTaken": "logged"
    }
  ],
  "total": 1,
  "page": 1,
  "pageSize": 20,
  "totalPages": 1
}
```

✅ **Pass Criteria:** Events appear in database with real data

### Test 9: Database Verification

**Connect to PostgreSQL:**
```powershell
psql -U securenet -d securenet
```

**Query Events:**
```sql
SELECT id, timestamp, source_ip, destination_ip, severity, attack_type, anomaly_score
FROM security_events
ORDER BY timestamp DESC
LIMIT 10;
```

**Query Event Count:**
```sql
SELECT 
  severity,
  COUNT(*) as count
FROM security_events
GROUP BY severity;
```

✅ **Pass Criteria:** Events stored in database with accurate data

### Test 10: Stop IDS

**API Call:**
```
POST http://localhost:8000/api/ids/control
Authorization: Bearer {your_token}
Content-Type: application/json

{
  "enabled": false
}
```

**Expected:**
```json
{
  "enabled": false,
  "mode": "monitor",
  "mlLoaded": true
}
```

**Backend Console:**
```
INFO - Stopping IDS...
INFO - Network monitor stopped
INFO - ✓ IDS stopped successfully
```

✅ **Pass Criteria:** `enabled: false`, monitoring stops

### Test 11: Protection Mode Test

**Start IDS in Protect Mode:**
```
POST http://localhost:8000/api/ids/control
{
  "enabled": true,
  "mode": "protect"
}
```

**Generate Suspicious Traffic:**
```powershell
# Port scan (will likely be detected as anomaly)
1..100 | ForEach-Object {
    Test-NetConnection -ComputerName localhost -Port $_
}
```

**Check Events:**
```
GET http://localhost:8000/api/events
```

**Look for:**
- `actionTaken: "blocked"`
- `mode: "protect"`

**Verify Firewall Rule Created:**
```powershell
netsh advfirewall firewall show rule name=all | Select-String "SecureNet_Block"
```

✅ **Pass Criteria:** High-severity events show `actionTaken: "blocked"`

### Test 12: Whitelist Test

**Add IP to Whitelist:**
```
POST http://localhost:8000/api/settings/whitelist
{
  "type": "ip",
  "value": "192.168.1.100",
  "description": "Test whitelist"
}
```

**Generate Traffic from Whitelisted IP:**
(If you can spoof source IP or test from that machine)

**Check Events:**
```
GET http://localhost:8000/api/events
```

✅ **Pass Criteria:** No events from whitelisted IP

### Test 13: Dashboard Real-Time Updates

**Open Frontend:**
```
http://localhost:5173
```

**Login**

**Navigate to Dashboard**

**Start IDS via Frontend UI** (once implemented)

**Generate Traffic**

**Observe:**
- Packet count updates
- Flow count updates
- Real-time event cards appearing
- WebSocket status: Connected

✅ **Pass Criteria:** Dashboard updates without page refresh

## Expected Results

### Normal Traffic
- Most benign traffic: **NO EVENTS CREATED**
- Isolation Forest classifies as inlier (score > 0)
- No database entries
- No alerts

### Anomalous Traffic
- Unusual patterns detected
- Isolation Forest: Outlier (score < 0)
- XGBoost Binary: Attack probability > 0.3
- **Event created and stored**
- Dashboard shows alert

### Attack Types That May Be Detected
Based on your network and the trained models:
- **DoS patterns**: Repetitive requests, high packet rate
- **Port scans**: Sequential port connections
- **Brute force**: Failed login attempts
- **DDoS**: Distributed high-volume traffic

### What WON'T Be Detected
- **SSL/TLS encrypted content** (models work on flow statistics, not payload)
- **Slow, low-volume attacks** below detection threshold
- **New attack types** not in training data (will show "UNKNOWN ATTACK TYPE")

## Performance Benchmarks

### Expected Performance
- **Packet Processing:** 1000-5000 packets/sec (depends on CPU)
- **Flow Analysis:** 10-100 flows/sec
- **Detection Latency:** < 1 second per flow
- **Database Write:** < 100ms per event

### Resource Usage
- **CPU:** 20-40% (single core for packet capture)
- **Memory:** 500MB-1GB (depends on flow cache size)
- **Disk:** Minimal (only event storage)

## Troubleshooting

### Issue: "Scapy not available"
**Solution:**
```powershell
pip install scapy
```

### Issue: "WinPcap error"
**Solution:**
1. Download Npcap: https://npcap.com/#download
2. Install with "WinPcap API-compatible Mode" checked
3. Restart computer

### Issue: "Permission denied" for packet capture
**Solution:**
Run PowerShell as **Administrator**

### Issue: No packets being captured
**Solution:**
1. Check network interface: `Get-NetAdapter`
2. Ensure traffic is flowing
3. Check firewall isn't blocking Scapy

### Issue: Too many false positives
**Solution:**
1. Adjust threshold in `xgboost_threshold.pkl` (currently 0.3)
2. Retrain model on your specific network
3. Add legitimate sources to whitelist

### Issue: "ML models not loaded"
**Solution:**
1. Verify files exist in `F:\all_10_csv_manual`
2. Check file permissions
3. Review backend logs for specific error

### Issue: Events not appearing in database
**Solution:**
1. Check PostgreSQL is running
2. Verify DATABASE_URL in `.env`
3. Run migrations: `alembic upgrade head`
4. Check database connection: `psql -U securenet -d securenet`

## Success Criteria Checklist

- [ ] Backend starts without errors
- [ ] ML models loaded (status: "loaded")
- [ ] IDS can be started/stopped
- [ ] Packet capture is working (counts increasing)
- [ ] Flows are being analyzed
- [ ] Anomalies are detected (at least 1 test case)
- [ ] Security events created in database
- [ ] Events visible via API
- [ ] Events visible in frontend (when integrated)
- [ ] WebSocket broadcasting works
- [ ] Whitelist prevents false positives
- [ ] Protection mode blocks IPs (if enabled)
- [ ] All data is REAL (no fake/random values)

## Final Validation

Run this complete test sequence:

```powershell
# 1. Start system
.\START_SECURENET.ps1

# 2. Wait 10 seconds for initialization

# 3. Verify health
curl http://localhost:8000/health

# 4. Login and get token
# (Use Postman or similar)

# 5. Check IDS status
curl http://localhost:8000/api/ids/status -H "Authorization: Bearer YOUR_TOKEN"

# 6. Start IDS
curl -X POST http://localhost:8000/api/ids/control `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"enabled":true,"mode":"monitor"}'

# 7. Generate test traffic
ping 8.8.8.8 -n 100

# 8. Wait 30 seconds

# 9. Check events
curl http://localhost:8000/api/events -H "Authorization: Bearer YOUR_TOKEN"

# 10. Verify database
psql -U securenet -d securenet -c "SELECT COUNT(*) FROM security_events;"

# 11. Stop IDS
curl -X POST http://localhost:8000/api/ids/control `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"enabled":false}'
```

If all tests pass: **✅ SYSTEM IS OPERATIONAL**

If any tests fail: Review logs and see troubleshooting section.

---

**Remember:** This is a REAL IDS using REAL ML models on REAL network traffic.
All detections are based on trained models - not fake or simulated data.
