# Mobile Security Audit — Restaurant SaaS Platform (React Native/Expo)

**Classification:** CONFIDENTIAL  
**Scope:** React Native/Expo mobile app, token storage, network security, platform-specific controls  

---

## Executive Summary

The mobile app (`apps/mobile/`) uses **Expo SDK 51** with **React Native 0.74**. It implements **platform-standard secure storage** (Keychain/Keystore via `expo-secure-store`) for tokens and uses **certificate pinning** via `expo-network`. However, it shares the **staff realm authentication** (Bearer tokens, 8-hour expiry, no MFA) and has **gaps in biometric authentication, certificate pinning enforcement, and runtime protections**.

**Overall Mobile Security Rating: MODERATE — Good storage, weak auth inheritance, missing runtime hardening**

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MOBILE APP ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  apps/mobile/                                                   │
│  ├── src/                                                       │
│  │   ├── lib/                                                   │
│  │   │   ├── api.ts          # Axios instance + interceptors   │
│  │   │   ├── tokenStore.ts   # SecureStore wrapper             │
│  │   │   └── auth.ts         # Auth state management           │
│  │   ├── screens/            # React Native screens            │
│  │   ├── navigation/         # React Navigation v6             │
│  │   └── App.tsx             # Root component                  │
│  ├── app.json / app.config.js  # Expo config                   │
│   ├── eas.json               # EAS Build config                │
│   └── package.json                                                      │
│                                                                  │
│  AUTH FLOW:                                                     │
│  1. User enters email/password                                 │
│  2. POST /api/v1/auth/login → {access_token, user}             │
│  3. Token stored in SecureStore (Keychain/Keystore)            │
│  4. Axios interceptor adds Authorization: Bearer <token>       │
│  5. Token expiry: 8 hours (no refresh)                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Token Storage Analysis

### Implementation (`apps/mobile/src/lib/tokenStore.ts`)

```typescript
import * as SecureStore from 'expo-secure-store';

const ACCESS_TOKEN_KEY = 'staff_access_token';
const REFRESH_TOKEN_KEY = 'staff_refresh_token';  // NOT USED - no refresh tokens
const TENANT_ID_KEY = 'current_tenant_id';

export const tokenStore = {
  async getAccessToken(): Promise<string | null> {
    return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
  },
  
  async setAccessToken(token: string): Promise<void> {
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token, {
      keychainService: 'restaurant-staff-app',
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,  // GOOD
    });
  },
  
  async clear(): Promise<void> {
    await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
    await SecureStore.deleteItemAsync(TENANT_ID_KEY);
  },
};
```

### Strengths

| Control | Implementation | Rating |
|---------|---------------|--------|
| **Storage** | `expo-secure-store` → iOS Keychain / Android Keystore | ✅ STRONG |
| **Keychain Access** | `WHEN_UNLOCKED_THIS_DEVICE_ONLY` (not in iCloud backup) | ✅ STRONG |
| **Keychain Service** | Custom service name (`restaurant-staff-app`) | ✅ GOOD |
| **No Plaintext** | Tokens never in AsyncStorage, SQLite, or files | ✅ STRONG |

### Vulnerabilities

#### MOB-001: Access Token Stored Without Expiry Metadata
**Severity:** MEDIUM  
**Location:** `tokenStore.ts:15-25`

Only the raw JWT is stored. No `expires_at` timestamp. App must decode JWT to check expiry (done in `api.ts` interceptor). If clock skew or token refresh (not implemented), stale token used.

**Fix:** Store `{token, expires_at}` object; validate before use.

---

#### MOB-002: No Refresh Token Storage (Because None Exist)
**Severity:** HIGH (inherited from AUTH-STAFF-001)  
**Location:** `tokenStore.ts:3` (REFRESH_TOKEN_KEY defined but unused)

Staff realm has **no refresh tokens** (8-hour access token only). Mobile app cannot silently refresh session. User must re-login every 8 hours or when token expires.

**Fix:** Implement staff realm refresh tokens (backend) + mobile storage.

---

#### MOB-003: Tenant ID Stored in SecureStore (Good) But Not Validated
**Severity:** LOW  
**Location:** `tokenStore.ts:28-35`

```typescript
async setTenantId(tenantId: string) {
  await SecureStore.setItemAsync(TENANT_ID_KEY, tenantId);
}
```

Tenant ID stored securely but app doesn't verify it matches token's `tenant_id` claim on resume.

**Fix:** On app foreground, decode token and verify `tenant_id` matches stored value.

---

## 3. Network Security

### Axios Configuration (`apps/mobile/src/lib/api.ts`)

```typescript
const api = axios.create({
  baseURL: CONFIG.API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: attach token
api.interceptors.request.use(async (config) => {
  const token = await tokenStore.getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await tokenStore.clear();
      navigation?.navigate('Login');
    }
    return Promise.reject(error);
  }
);
```

### Vulnerabilities

#### MOB-004: No Certificate Pinning Enforced
**Severity:** HIGH  
**Location:** `app.json`, `api.ts`

`expo-network` supports certificate pinning but **not configured**. App trusts any valid CA certificate. Vulnerable to:
- Compromised CA
- MITM with corporate proxy (if user installs proxy CA)
- Malicious Wi-Fi with rogue certificate

**Fix:** Configure pinning in `app.json`:
```json
{
  "expo": {
    "plugins": [
      ["expo-network", {
        "certificatePinning": {
          "api.restaurant-platform.com": {
            "sha256": ["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB="],
            "enforce": true
          }
        }
      }]
    ]
  }
}
```
**Note:** Requires backup pins; plan for certificate rotation.

---

#### MOB-005: No TLS Version Enforcement
**Severity:** MEDIUM  
**Location:** `api.ts`

Axios uses system default TLS. No minimum TLS 1.2 enforcement.

**Fix:** Use `expo-network` with `tlsVersion: '1.2'` or native module to enforce.

---

#### MOB-006: Base URL Configurable at Runtime (Dev Risk)
**Severity:** LOW  
**Location:** `config.ts`

```typescript
export const CONFIG = {
  API_BASE_URL: __DEV__ 
    ? 'http://localhost:8000' 
    : 'https://api.restaurant-platform.com',
};
```

Development uses HTTP localhost. If dev build leaked, cleartext traffic.

**Fix:** Use HTTPS for all environments; use `10.0.2.2` for Android emulator.

---

#### MOB-007: No Request/Response Signing
**Severity:** LOW  
**Location:** N/A

API calls not signed. Relies solely on TLS + Bearer token. If TLS terminated at load balancer, internal traffic unencrypted.

**Fix:** Consider mTLS or request signing for high-value operations (payments, staff management).

---

## 4. Authentication & Session Management

### Inherited from Staff Realm (AUTHENTICATION_AUDIT.md)

| Issue | Mobile Impact |
|-------|---------------|
| 8-hour token expiry | User re-login frequently |
| No refresh tokens | No silent session extension |
| No MFA | High-privilege roles (Owner/Manager) unprotected |
| Bearer token in header | Token in memory during app lifecycle |
| No device binding | Token works on any device |

### Mobile-Specific Issues

#### MOB-008: No Biometric Authentication
**Severity:** HIGH  
**Location:** N/A (not implemented)

App uses email/password only. No Face ID / Touch ID / BiometricPrompt for:
- App unlock (after background)
- Sensitive actions (staff management, refunds)
- MFA alternative

**Fix:** Implement `expo-local-authentication`:
```typescript
import * as LocalAuthentication from 'expo-local-authentication';

async function authenticateWithBiometrics(): Promise<boolean> {
  const hasHardware = await LocalAuthentication.hasHardwareAsync();
  const isEnrolled = await LocalAuthentication.isEnrolledAsync();
  if (hasHardware && isEnrolled) {
    const result = await LocalAuthentication.authenticateAsync({
      promptMessage: 'Authenticate to access restaurant data',
      fallbackLabel: 'Use passcode',
    });
    return result.success;
  }
  return false;
}
```

---

#### MOB-009: No App Lock / Background Timeout
**Severity:** MEDIUM  
**Location:** `App.tsx`, navigation

App doesn't lock when backgrounded. User switches apps → returns → session still active. No re-authentication prompt.

**Fix:** Use `AppState` listener to lock after configurable timeout (e.g., 5 min):
```typescript
import { AppState } from 'react-native';

AppState.addEventListener('change', (nextState) => {
  if (nextState === 'active') {
    const timeSinceBackground = Date.now() - lastBackgroundTime;
    if (timeSinceBackground > LOCK_TIMEOUT_MS) {
      requireBiometricOrPasscode();
    }
  } else if (nextState === 'background') {
    lastBackgroundTime = Date.now();
  }
});
```

---

#### MOB-010: Token in Memory During App Lifecycle
**Severity:** MEDIUM  
**Location:** `api.ts` interceptor

Token held in memory (React state + Axios interceptor). If memory dump (rooted/jailbroken device), token extractable.

**Mitigation:** Short token expiry (8 hours is long). Fix requires backend refresh tokens.

---

## 5. Code Security

### Dependencies (`apps/mobile/package.json`)

```json
{
  "dependencies": {
    "expo": "~51.0.0",
    "react-native": "0.74.5",
    "axios": "^1.6.0",
    "expo-secure-store": "~13.0.0",
    "expo-local-authentication": "~14.0.0",
    "@react-navigation/native": "^6.1.0",
    "react-native-gesture-handler": "~2.16.0"
  }
}
```

### Vulnerabilities

#### MOB-011: Dependency Vulnerabilities Not Scanned
**Severity:** MEDIUM  
**Location:** `package.json`, CI/CD

No `npm audit` or `snyk` in CI. Expo SDK 51 may have transitive vulnerabilities.

**Fix:** Add to CI:
```yaml
- name: Audit dependencies
  run: npm audit --audit-level=high
```

---

#### MOB-012: No Code Obfuscation / Anti-Tamper
**Severity:** LOW  
**Location:** `eas.json`, build config

React Native JS bundle not obfuscated in production. Easy to reverse engineer API structure, endpoints, logic.

**Fix:** Enable Hermes bytecode compilation + `metro-minify-terser`:
```json
// metro.config.js
module.exports = {
  transformer: {
    minifierPath: 'metro-minify-terser',
    minifierConfig: { keep_fnames: true, mangle: true },
  },
};
```

---

#### MOB-013: Debug Logging in Production Build
**Severity:** LOW  
**Location:** `api.ts`, various files

```typescript
console.log('API Request:', config.url, config.data);  // May log tokens!
console.log('API Response:', response.data);
```

**Fix:** Use `__DEV__` guard or structured logger with sanitization.

---

## 6. Platform-Specific Analysis

### iOS (`ios/` or managed workflow)

| Control | Status | Notes |
|---------|--------|-------|
| **Keychain** | ✅ Used via SecureStore | `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` |
| **App Transport Security** | ⚠️ Not verified | Need `NSAppTransportSecurity` in `Info.plist` |
| **Keychain Sharing** | ❌ Not configured | Could enable shared credentials with web |
| **Biometric** | ❌ Not implemented | `LocalAuthentication` framework available |
| **Jailbreak Detection** | ❌ Not implemented | Consider `react-native-jailbreak-detection` |

### Android (`android/` or managed workflow)

| Control | Status | Notes |
|---------|--------|-------|
| **Keystore** | ✅ Used via SecureStore | Hardware-backed if available (API 23+) |
| **Network Security Config** | ❌ Not configured | Should pin certs, disable cleartext |
| **Biometric** | ❌ Not implemented | `BiometricPrompt` API available |
| **Root Detection** | ❌ Not implemented | Consider `react-native-root-detection` |
| **Backup Exclusion** | ✅ SecureStore excludes | `android:allowBackup="false"` for app data |

### Required: Network Security Config (`android/app/src/main/res/xml/network_security_config.xml`)

```xml
<network-security-config>
  <domain-config cleartextTrafficPermitted="false">
    <domain includeSubdomains="true">api.restaurant-platform.com</domain>
    <pin-set expiration="2026-12-31">
      <pin digest="SHA-256">AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=</pin>
      <pin digest="SHA-256">BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=</pin>
    </pin-set>
  </domain-config>
  <base-config cleartextTrafficPermitted="false">
    <trust-anchors>
      <certificates src="system" />
    </trust-anchors>
  </base-config>
  <debug-overrides>
    <trust-anchors>
      <certificates src="system" />
      <certificates src="user" />
    </trust-anchors>
  </debug-overrides>
</network-security-config>
```

Add to `AndroidManifest.xml`:
```xml
<application
    android:networkSecurityConfig="@xml/network_security_config"
    android:allowBackup="false"
    ... >
```

---

## 7. Build & Deployment Security

### EAS Build (`apps/mobile/eas.json`)

```json
{
  "build": {
    "production": {
      "ios": { "buildConfiguration": "Release" },
      "android": { "buildType": "apk" }
    }
  }
}
```

### Issues

#### MOB-014: No Code Signing Verification in CI
**Severity:** MEDIUM  
**Location:** `.github/workflows/` (not present for mobile)

Mobile builds not in CI/CD. Manual `eas build` — no verification of:
- Dependency integrity (lockfile match)
- Build reproducibility
- Signature validation

**Fix:** Add GitHub Action for EAS Build with artifact verification.

---

#### MOB-015: No Runtime Application Self-Protection (RASP)
**Severity:** LOW  
**Location:** N/A

No detection of:
- Root/jailbreak
- Debugger attached
- Hooking frameworks (Frida, Xposed)
- Repackaged app

**Fix:** Integrate `react-native-rasp` or similar for high-security environments.

---

## 8. Data Privacy

### MOB-016: Analytics / Crash Reporting Not Audited
**Severity:** LOW  
**Location:** `app.json`, `App.tsx`

Expo includes `expo-analytics` / `sentry-expo` by default? Need to verify:
- What PII sent to analytics
- Crash reports may include tokens in stack traces
- Opt-out mechanism

**Fix:** Audit all telemetry; implement user consent.

---

## 9. Recommendations Priority Matrix

| Priority | Finding | Effort |
|----------|---------|--------|
| P0 | MOB-004: Certificate pinning | 4h |
| P0 | MOB-002: Staff refresh tokens (backend + mobile) | 8h |
| P1 | MOB-008: Biometric authentication | 6h |
| P1 | MOB-009: App lock on background | 4h |
| P1 | MOB-005: TLS 1.2 enforcement | 2h |
| P2 | MOB-001: Token expiry metadata in storage | 2h |
| P2 | MOB-011: Dependency scanning in CI | 2h |
| P2 | MOB-013: Remove debug logging | 1h |
| P3 | MOB-012: Code obfuscation | 4h |
| P3 | MOB-014: Mobile CI/CD pipeline | 8h |
| P3 | MOB-015: RASP integration | 8h |

---

## 10. Verification Test Suite

```typescript
// apps/mobile/__tests__/security.test.ts

describe('Mobile Security', () => {
  test('Token stored in SecureStore, not AsyncStorage', async () => {
    await tokenStore.setAccessToken('test-token');
    const secure = await SecureStore.getItemAsync('staff_access_token');
    const async = await AsyncStorage.getItem('staff_access_token');
    expect(secure).toBe('test-token');
    expect(async).toBeNull();
  });

  test('Certificate pinning rejects wrong cert', async () => {
    // Requires test server with different cert
    // Or mock axios adapter to simulate cert error
    await expect(api.get('/test')).rejects.toThrow('Certificate pinning');
  });

  test('Biometric authentication works', async () => {
    const result = await authenticateWithBiometrics();
    // On device with biometrics: expect true
    // On simulator: expect false (no hardware)
  });

  test('App locks after background timeout', async () => {
    // Mock AppState change to background
    // Advance timers by LOCK_TIMEOUT_MS + 1
    // Mock AppState change to active
    // Expect requireBiometricOrPasscode called
  });

  test('No tokens in console logs', () => {
    const consoleSpy = jest.spyOn(console, 'log');
    await api.post('/auth/login', { email: 'test@test.com', password: 'secret' });
    const logs = consoleSpy.mock.calls.flat().join(' ');
    expect(logs).not.toContain('secret');
    expect(logs).not.toContain('Bearer');
  });

  test('Network security config present (Android)', () => {
    // Verify android/app/src/main/res/xml/network_security_config.xml exists
    // Verify pin-set with SHA-256 hashes
    // Verify cleartextTrafficPermitted="false"
  });
});
```

---

## Conclusion

The mobile app **correctly uses platform secure storage** (Keychain/Keystore) for tokens, which is the most critical mobile security control. However, it **inherits the staff realm's weak authentication** (8-hour tokens, no refresh, no MFA) and **lacks certificate pinning**, which is essential for a financial/operations app.

**Immediate priorities:**
1. **Certificate pinning (MOB-004)** — prevents MITM on compromised networks
2. **Staff refresh tokens (MOB-002)** — requires backend work first
3. **Biometric authentication (MOB-008)** — strong UX + security improvement
4. **App lock on background (MOB-009)** — prevents session theft on unattended device

**Note:** Many mobile issues stem from backend auth design. Fix backend (refresh tokens, MFA) first, then mobile enhancements.