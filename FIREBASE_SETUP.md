# Firebase Cloud Messaging (FCM) Setup

This project uses **Firebase for push notifications only**.

| Layer | Technology |
|---|---|
| Database | **Postgres** (all business data) |
| Authentication | **FastAPI backend** (existing email/password + JWT) |
| Push notifications | **Firebase Cloud Messaging** |

Firebase Authentication and Firestore are **not used** and must not be added
back without an explicit decision to migrate off Postgres.

---

## 1. What is already configured

### Android app

- Firebase project: `restaurant-94f9b`
- Android package: `com.restaurant.staff`
- `google-services.json` at:
  - `apps/mobile/google-services.json`
  - `apps/mobile/android/app/google-services.json`
- `apps/mobile/app.json`:
  ```json
  "android": {
    "googleServicesFile": "./google-services.json",
    "package": "com.restaurant.staff"
  }
  ```
- `apps/mobile/android/build.gradle`:
  ```groovy
  classpath 'com.google.gms:google-services:4.5.0'
  ```
- `apps/mobile/android/app/build.gradle`:
  ```groovy
  implementation(platform("com.google.firebase:firebase-bom:35.1.0"))
  implementation("com.google.firebase:firebase-messaging")
  implementation("com.google.firebase:firebase-analytics")
  ```
  and the plugin applied at the bottom of the file:
  ```groovy
  apply plugin: 'com.google.gms.google-services'
  ```

> Re-running `npx expo prebuild` regenerates `android/` and overwrites these
> edits. Re-apply them after any prebuild.

### Web

FCM for the website is now configured but needs your Firebase web config:

1. In Firebase Console → Project settings → General → Your apps, add a **Web app** (`</>` icon).
2. Copy the config object and replace the placeholders in:
   - `apps/web/public/firebase-messaging-sw.js` (background push handler)
   - `apps/web/src/lib/fcm.ts` (foreground push handler + token registration)
3. You also need the **VAPID key**: Firebase Console → Cloud Messaging → Web configuration → Generate key pair. Replace `__FIREBASE_WEB_VAPID_KEY__` in `apps/web/src/lib/fcm.ts`.
4. Install the dependency (already done): `npm install firebase` in `apps/web/`.
5. The site must run on **HTTPS** (or `localhost`) for the browser to grant notification permission and for the service worker to register.

The web app now:
- Registers its FCM token with `POST /api/v1/devices` after login (`platform: "web"`)
- Shows an in-app alert when a push arrives while the tab is open
- Handles background pushes via `firebase-messaging-sw.js` (system notification with pop sound)
- Clears the token on sign-out

---

## 2. Server: send notifications

The backend sends notifications with the Firebase Admin SDK.

1. Install (already installed in this venv):
   ```powershell
   E:\rest\backend\venv\Scripts\python.exe -m pip install firebase-admin
   ```
2. Download a service-account key:
   - https://console.firebase.google.com/project/restaurant-94f9b/settings/serviceaccounts/adminsdk
   - **Generate new private key** → save as `backend/firebase-service-account.json`
   - The file is git-ignored (`*service-account*.json`).
3. Send a message:
   ```python
   import firebase_admin
   from firebase_admin import credentials, messaging

   if not firebase_admin._apps:
       firebase_admin.initialize_app(
           credentials.Certificate("firebase-service-account.json")
       )

   messaging.send(
       messaging.Message(
           token=device_token,
           notification=messaging.Notification(
               title="New order",
               body="Table 4 placed an order",
           ),
           data={"order_id": str(order_id)},
       )
   )
   ```

Server-side pieces (all built):

- `device_tokens` table — migration `alembic/versions/pa0023_fcm_device_tokens.py` (applied)
- `POST /api/v1/devices` endpoint — registers/upserts a device token
- `GET /api/v1/devices` — lists a restaurant's device tokens
- `DELETE /api/v1/devices/{token}` — removes a device token
- `POST /api/v1/notifications/send` — sends an FCM notification to a restaurant's devices
- `POST /api/v1/notifications/process-outbox` — drains `outbox_events` as FCM pushes
- `app/modules/notifications/services/fcm.py` — Firebase Admin SDK sender with multicast + unregistered token pruning

To enable sending, set in `backend/.env`:
```
FIREBASE_CREDENTIALS_PATH=backend/firebase-service-account.json
FIREBASE_PROJECT_ID=restaurant-94f9b
```

### Outbox worker (background delivery)

The worker drains `outbox_events` and delivers them as FCM pushes. Run it as a
standalone process (recommended for production):

```powershell
cd E:\rest\backend
.\venv\Scripts\python.exe backend\\run_fcm_worker.py
```

Options:
- `--poll-interval`  Seconds between polls (default: 5)
- `--batch-size`     Max events per poll (default: 100)

To create an outbox event from your backend code:

```python
from app.modules.notifications.services import record_outbox
from uuid import uuid4

record_outbox(
    db,
    restaurant_id=restaurant_id,
    event_type="order.created",
    aggregate_type="order",
    aggregate_id=str(order_id),
    payload=json.dumps({
        "title": "New order",
        "body": "Table 4 placed an order",
        "data": {"order_id": str(order_id)},
    }),
)
```

The `payload` must contain `title` and `body`, plus optional `data` and either
`restaurant_id` (broadcast to all devices of that restaurant) or `tokens`
(explicit device list). Events are retried up to 5 times before being dropped.

**Dev convenience:** set `FCM_WORKER_ENABLED=true` in `backend/.env` to run the
worker as a background daemon thread inside the API process. For production, use
the standalone script as a separate process instead.

---

## 3. Mobile: receive notifications

The native Firebase SDK is linked (step 1), but the app does not register a
token yet. In an Expo dev build:

```powershell
cd E:\rest\apps\mobile
npx expo install expo-notifications expo-device
```

Then, after login:

1. Request permission.
2. Read the token:
   ```ts
   import * as Notifications from "expo-notifications";

   const token = (await Notifications.getDevicePushTokenAsync()).data;
   await api.post("/api/v1/devices", { token, platform: "android" });
   ```
3. Handle taps and foreground messages with
   `Notifications.addNotificationResponseReceivedListener`.

Expo Go cannot receive FCM messages — use a development build
(`npx expo run:android` or `eas build --profile development`).

---

## 4. Verify

```powershell
cd E:\rest\backend
.\venv\Scripts\python.exe -c "import firebase_admin; print(firebase_admin.__version__)"
```

Send a test message to a real token:

```python
from firebase_admin import messaging
print(messaging.send(messaging.Message(
    token="<device-token>",
    notification=messaging.Notification(title="Test", body="Hello from FCM"),
)))
```

A successful send prints a message name such as
`projects/restaurant-94f9b/messages/0:1234...`.

---

## 5. Notes

- `google-services.json` is a **client** config (not a secret) and is committed.
- `firebase-service-account.json` is a **server secret** and must never be
  committed.
- FCM does not store your data and does not replace Postgres.
- The `firebase` npm package was removed from both apps: React Native uses the
  native SDK through Expo, not the web JS SDK.
