/**
 * Firebase Cloud Messaging (FCM) client for the website.
 *
 * Handles:
 *  - Initializing the Firebase messaging SDK
 *  - Requesting notification permission
 *  - Getting the FCM push token
 *  - Registering it with the backend (POST /api/v1/devices)
 *  - Listening to incoming messages (foreground)
 *  - Clearing the token on logout
 *
 * Works only on HTTPS (or localhost) and modern browsers where
 * Notification + PushManager are available.
 */

import { getApp, getApps, initializeApp } from "firebase/app";
import { deleteToken, getMessaging, getToken, onMessage } from "firebase/messaging";

import { apiFetch } from "./api";

const firebaseConfig = {
  apiKey: "AIzaSyB9C3JpTrdpzSBuVSX56yhY4FeP4F3scCw",
  authDomain: "restaurant-94f9b.firebaseapp.com",
  projectId: "restaurant-94f9b",
  storageBucket: "restaurant-94f9b.firebasestorage.app",
  messagingSenderId: "987351547926",
  appId: "1:987351547926:web:0bd64696d752ac2508b537",
};

const VAPID_KEY =
  "BFXRM_q56YhgpqPsYTTuY_zSdabz_Oc7buaBvRfxXDubCIwhB17Po_1Sa2zRfwchKRmV-FKUgn-Lmy6ml7Yq2h4";

const SW_PATH = "/firebase-messaging-sw.js";

type Messaging = ReturnType<typeof getMessaging>;

let messagingInstance: Messaging | null = null;
let swRegistration: ServiceWorkerRegistration | null = null;
/** Cached so logout can unregister even after permission changes. */
let cachedToken: string | null = null;

function firebaseApp() {
  return getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
}

function initMessaging(): Messaging {
  if (!messagingInstance) {
    messagingInstance = getMessaging(firebaseApp());
  }
  return messagingInstance;
}

async function registerServiceWorker(): Promise<ServiceWorkerRegistration> {
  if (swRegistration) return swRegistration;
  swRegistration = await navigator.serviceWorker.register(SW_PATH, { scope: "/" });
  return swRegistration;
}

function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

/**
 * Request notification permission (if needed) and return the FCM token.
 * Returns null on unsupported browsers or when permission is denied.
 */
export async function getPushToken(): Promise<string | null> {
  if (!pushSupported()) return null;

  try {
    const messaging = initMessaging();
    if (Notification.permission === "default") {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") return null;
    }
    if (Notification.permission !== "granted") return null;

    const registration = await registerServiceWorker();
    const token = await getToken(messaging, {
      vapidKey: VAPID_KEY,
      serviceWorkerRegistration: registration,
    });
    cachedToken = token ?? null;
    return cachedToken;
  } catch (err) {
    console.warn("[FCM] Could not get push token:", err);
    return null;
  }
}

/** Register the current browser's FCM token with the backend. */
export async function registerDeviceToken(): Promise<string | null> {
  const token = await getPushToken();
  if (!token) return null;

  try {
    await apiFetch("/api/v1/devices", {
      method: "POST",
      body: JSON.stringify({ token, platform: "web" }),
    });
    return token;
  } catch (err) {
    console.warn("[FCM] Could not register device token:", err);
    return null;
  }
}

/** Clear the device token from the backend and from Firebase (on sign-out). */
export async function unregisterDeviceToken(): Promise<void> {
  const token = cachedToken;
  if (token) {
    try {
      await apiFetch(`/api/v1/devices/${encodeURIComponent(token)}`, {
        method: "DELETE",
      });
    } catch {
      // Best effort — the row may already be gone.
    }
  }

  cachedToken = null;
  try {
    await deleteToken(initMessaging());
  } catch {
    // Ignore — nothing to delete.
  }
}

/** Whether the browser can receive web push at all. */
export function webPushSupported(): boolean {
  return pushSupported();
}

/** Current browser notification permission state. */
export function notificationPermission(): NotificationPermission | "unsupported" {
  if (!pushSupported()) return "unsupported";
  return Notification.permission;
}

/**
 * Set up a listener for foreground FCM messages (when the tab is open).
 * Returns an unsubscribe function.
 */
export function setupForegroundListener(
  onMessageReceived: (payload: {
    title: string;
    body: string;
    data?: Record<string, string>;
  }) => void
): (() => void) | null {
  if (!pushSupported()) return null;

  try {
    return onMessage(initMessaging(), (payload) => {
      const { title, body } = payload.notification ?? {};
      const data = (payload.data as Record<string, string> | undefined) ?? {};
      onMessageReceived({
        title: title ?? data.title ?? "New notification",
        body: body ?? data.body ?? "",
        data,
      });
    });
  } catch {
    return null;
  }
}
