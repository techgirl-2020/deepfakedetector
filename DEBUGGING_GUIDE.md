# FakeSight Debugging & Verification Guide

## 🔧 CURRENT STATUS

### Backend ✅ WORKING
- Auth Service: http://localhost:8001 
- User Service: http://localhost:8002
- AI Service: http://localhost:8003
- All services returning correct responses

### Frontend 🔄 IN PROGRESS
- Docker container rebuilt with updated code
- NaN errors need investigation
- 401 auth errors may be browser cache

---

## 📝 STEP-BY-STEP VERIFICATION

### Step 1: Hard Refresh Browser
```
Chrome/Edge: Ctrl + Shift + R
Firefox: Ctrl + Shift + F5
Safari: Cmd + Shift + R
```
This clears the cache and forces fresh JS/CSS load.

### Step 2: Test Login
**URL**: http://localhost:3001/index.html

**Credentials:**
- Username: `testuser`
- Password: `TestPass123`

**What to check:**
1. ✓ Form accepts input
2. ✓ No "Invalid credentials" error
3. ✓ Redirects to dashboard.html
4. ✓ User name displays in sidebar

### Step 3: Monitor Console Errors
1. Open DevTools: `F12`
2. Go to **Console** tab
3. Look for any errors (red messages)
4. Check **Network** tab for failed requests

**If you see NaN error:**
```
Error: <circle> attribute cx: Expected length, "NaN"
```
- Click on the error
- Check the stack trace
- Note which line of code is failing

---

## 🐛 DEBUGGING NaN ERROR

### What causes NaN in SVG?
The error occurs when JavaScript tries to set SVG circle attributes with undefined/NaN values.

### How to Locate:
1. **Open DevTools** (F12)
2. **Go to Console tab**
3. **Type this to enable debug logging:**
```javascript
window.DEBUG = true;
localStorage.debug = '*';
```
4. **Refresh page**
5. **Look for console logs with NaN values**

### If Error Persists:
1. **Right-click** on the error in console
2. **Click "Show in Sources"**
3. This shows exactly which line of code is creating NaN
4. Take a screenshot

### Common NaN Sources:
```javascript
// ❌ BAD - results in NaN
const cx = undefined + 10;  // NaN
const cy = null * 2;         // NaN

// ✅ GOOD - defensive coding
const cx = (value || 0) + 10;
const cy = (value ?? 0) * 2;

// ✅ BEST - explicit validation
if (isNaN(cx) || isNaN(cy)) {
  console.error("Invalid coordinates:", cx, cy);
  return;
}
```

---

## ✅ TESTING CHECKLIST

### Login/Register
- [ ] Hard refresh page (cache cleared)
- [ ] Register new account works
- [ ] Login with testuser/TestPass123 works
- [ ] Redirects to dashboard
- [ ] No 401 errors in Network tab
- [ ] No red errors in Console tab

### Dashboard
- [ ] Page loads without errors
- [ ] Sidebar shows user name
- [ ] Overview section loads stats
- [ ] Navigation between sections works
- [ ] No NaN errors in console

### Detection (Optional)
- [ ] Can upload an image
- [ ] Can run detection
- [ ] Result displays without NaN errors
- [ ] Confidence score renders correctly

---

## 🔍 NETWORK TAB DEBUGGING

### To Check API Calls:
1. Open DevTools (F12)
2. Go to **Network** tab
3. Do login attempt
4. Look for requests to:
   - `localhost:8001/auth/login/`
   - `localhost:8001/auth/register/`

### Expected Responses:
- **Status 200 or 201** (success)
- **Status 401** (check credentials)
- **Status 0** (network blocked - likely CORS)

### If CORS error appears:
```
Access to XMLHttpRequest blocked by CORS policy
```
- This means backend isn't allowing requests
- Check auth-service settings.py for `CORS_ALLOW_ALL_ORIGINS = True`

---

## 🚀 QUICK FIX CHECKLIST

- [x] Fixed Docker-compose.yml YAML indentation
- [x] Updated register function with role field
- [x] Rebuilt frontend container
- [ ] Hard refresh browser
- [ ] Test login/register
- [ ] Document any remaining errors

---

## 📞 IF ISSUES PERSIST

Run these commands to collect debug info:

```powershell
# Check service health
docker compose ps

# View auth service logs
docker compose logs auth-service --tail 50

# View frontend logs
docker compose logs frontend --tail 50

# Test auth endpoint directly
$body = @{username="testuser";password="TestPass123"} | ConvertTo-Json
Invoke-WebRequest -Uri http://localhost:8001/auth/login/ `
  -Method POST -ContentType application/json -Body $body -UseBasicParsing
```

---

## 🎯 SUCCESS INDICATORS

✅ **All green when:**
1. No red errors in console
2. Login succeeds with correct credentials
3. Dashboard loads with user data
4. Can navigate between tabs
5. Detection section works (upload form responsive)
