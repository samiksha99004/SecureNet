# SecureNet IDS - Authentication Error Fix ✅

## Issue
Error message when trying to turn IDS ON:
```
Failed to start IDS — backend not connected
```

But backend logs show:
```
POST /api/ids/control HTTP/1.1" 401 Unauthorized
```

## Root Cause
The error message was misleading. The backend **IS** connected and working fine, but the frontend authentication token was missing or expired, causing **401 Unauthorized** responses.

## Why This Happens
- You need to be logged in to control IDS
- Authentication tokens can expire
- Browser refresh might clear session in some cases
- ADMIN or ANALYST role required for IDS control

## Solution Applied

### 1. Improved Error Messages
**File:** `frontend/src/components/dashboard/IDSControlWidget.tsx`

Now detects 401 errors and shows:
```
Session expired — please log in again
```

Instead of the misleading:
```
Failed to start IDS — backend not connected
```

### 2. Auto-Redirect on 401
**File:** `frontend/src/services/apiClient.ts`

When any API call gets 401:
- Clears stored tokens automatically
- Redirects to login page with `?expired=true` parameter
- Prevents further failed requests

### 3. Session Expired Notice
**File:** `frontend/src/pages/LoginPage.tsx`

Login page now shows a notice when redirected due to expired session:
```
Your session has expired. Please log in again.
```

## How to Fix When You See This Error

### Solution 1: Log In Again
1. Go to login page: http://localhost:5174/login
2. Login with your credentials:
   - Admin: admin@securenet.com / Admin@123456
   - Analyst: analyst@securenet.com / Analyst@123456
3. You'll be redirected to dashboard
4. Try turning IDS ON again

### Solution 2: Refresh and Login
1. Press F5 to refresh the page
2. If it redirects to login, enter your credentials
3. Dashboard will load
4. IDS control will work

## Testing

After applying the fix:

1. **Test expired session:**
   ```
   1. Login to dashboard
   2. Clear localStorage (F12 → Application → Local Storage → Clear)
   3. Try to turn IDS ON
   4. Should show: "Session expired — please log in again"
   5. Should auto-redirect to login after 2 seconds
   ```

2. **Test normal flow:**
   ```
   1. Login: admin@securenet.com / Admin@123456
   2. Navigate to dashboard
   3. Click IDS ON
   4. Should work correctly
   ```

3. **Test permission error:**
   ```
   1. Login as viewer: viewer@securenet.com / Viewer@123456
   2. Try to turn IDS ON
   3. Should show: "Failed to start IDS — ..." (403 Forbidden)
   ```

## Technical Details

### Before Fix
```typescript
catch (err) {
  showToast({
    message: `Failed to start IDS — backend not connected`,
    variant: 'error',
  });
}
```

### After Fix
```typescript
catch (err: any) {
  const isAuthError = err?.status === 401 || err?.code === 'UNAUTHORIZED';
  const message = isAuthError 
    ? 'Session expired — please log in again'
    : `Failed to start IDS — ${err?.message || 'backend not connected'}`;
  
  showToast({ message, variant: 'error' });
  
  if (isAuthError) {
    setTimeout(() => {
      window.location.href = '/login';
    }, 2000);
  }
}
```

### API Client 401 Handler
```typescript
if (!response.ok) {
  // Handle 401 Unauthorized - session expired
  if (response.status === 401 && !skipAuth) {
    // Clear stored tokens
    localStorage.removeItem('sn_access_token');
    localStorage.removeItem('sn_refresh_token');
    localStorage.removeItem('sn_user');
    
    // Redirect to login
    if (!window.location.pathname.includes('/login')) {
      window.location.href = '/login?expired=true';
    }
  }
  
  throw await parseErrorResponse(response);
}
```

## Files Modified

1. `frontend/src/components/dashboard/IDSControlWidget.tsx`
   - Improved error handling
   - Detects auth errors
   - Auto-redirects on session expiration

2. `frontend/src/services/apiClient.ts`
   - Global 401 handler
   - Automatic token cleanup
   - Login redirect with expired flag

3. `frontend/src/pages/LoginPage.tsx`
   - Session expired notice
   - Query parameter detection
   - User-friendly messaging

## Prevention

To avoid this issue in the future:

1. **Stay logged in:**
   - Access tokens last 60 minutes (configurable in backend/.env)
   - Refresh tokens last 7 days

2. **Auto-refresh implementation** (future enhancement):
   - Could add automatic token refresh before expiration
   - Use refresh token to get new access token
   - Seamless user experience

3. **Remember me option** (future enhancement):
   - Store tokens more persistently
   - Longer session duration

## Current Behavior

✅ **With valid session:**
- IDS ON/OFF works correctly
- All dashboard data loads
- Real-time monitoring active

❌ **Without valid session:**
- Error: "Session expired — please log in again"
- Auto-redirect to login page after 2 seconds
- Clear message on login page
- User logs in and continues working

---

**Status:** ✅ FIXED  
**Error Message:** Improved and accurate  
**User Experience:** Better with auto-redirect  
**Date:** September 13, 2026
