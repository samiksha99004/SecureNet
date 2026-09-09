# CRITICAL FIXES REQUIRED BEFORE DEPLOYMENT

## 🔴 BLOCKER #1: Feature Extraction Broken

**File:** `backend/app/ml/network_monitor.py` lines 127-270  
**Problem:** Extracts 77 features, model expects 71  
**Impact:** ML predictions will be completely wrong

**Missing Features (3):**
- Protocol_0 (ICMP/Other one-hot)
- Protocol_6 (TCP one-hot)
- Protocol_17 (UDP one-hot)

**Extra Features (9):**
- Bwd PSH Flags
- Fwd URG Flags
- Bwd URG Flags
- Fwd/Bwd Byts/b Avg
- Fwd/Bwd Pkts/b Avg
- Fwd/Bwd Blk Rate Avg

**Order Mismatches:** 40 positions

**Fix:** Rewrite `extract_features()` to match exact order from `feature_columns.pkl`

---

## 🔴 BLOCKER #2: WebSocket Endpoint Missing

**Problem:** ConnectionManager exists but no FastAPI endpoint to accept connections  
**Impact:** Frontend cannot receive real-time updates

**Fix:** Add to `backend/app/main.py`:

```python
from app.websocket.manager import manager

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

---

## ⚠️ MINOR: Documentation References "78 Features"

**Files:**
- backend/app/ml/README.md:22
- backend/README.md:8
- backend/PROJECT_SUMMARY.md:70
- backend/IMPLEMENTATION_STATUS.md:140

**Fix:** Replace "78" with "71"

---

## ✅ VERIFIED WORKING

- Model loading from F:\all_10_csv_manual ✅
- 71 features → IF → 72 features (71+IF) → XGBoost ✅
- Threshold 0.3 ✅
- IDS pipeline logic ✅
- Single ON/OFF switch ✅
- Windows Firewall blocking ✅
- Database persistence ✅
- No fake data ✅
- No stale config paths ✅

---

## DEPLOYMENT CHECKLIST

- [ ] Fix feature extraction (CRITICAL)
- [ ] Add WebSocket endpoint (CRITICAL)
- [ ] Update documentation (minor)
- [ ] Run `python backend/audit_feature_extraction.py` → must show 0 errors
- [ ] Test IDS start/stop
- [ ] Test WebSocket connection
- [ ] Test with real network traffic
- [ ] Verify frontend displays detections

**DO NOT DEPLOY UNTIL BLOCKERS #1 AND #2 ARE FIXED**
