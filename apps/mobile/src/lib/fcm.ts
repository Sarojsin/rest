/**
 * Firebase Cloud Messaging (FCM) client for the mobile app.
 *
 * Handles:
 *  - Getting the device push token from Expo Notifications
 *  - Registering it with the backend (POST /api/v1/devices)
 *  - Listening to incoming notifications (foreground + taps)
 *  - Clearing the token on sign-out
 *
 * Works only on real devices / dev builds — Expo Go cannot receive FCM.
 */

import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { router } from "expo-router";
import { Platform } from "react-native";

import { api } from "./api";

type DeviceTokenIn = {
  token: string;
  platform: "android" | "ios" | "web";
};

/**
 * Android notification channel so the "pop" sound plays on incoming pushes.
 * The channel id is also sent by the backend in every FCM message, so both
 * sides must agree on this constant.
 */
export const ANDROID_CHANNEL_ID = "restaurant-staff";

/** Show FCM notifications while the app is in the foreground. */
export function configureForegroundPresentation() {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

export function setupAndroidChannel() {
  if (Platform.OS !== "android") return;
  void Notifications.setNotificationChannelAsync(ANDROID_CHANNEL_ID, {
    name: "Restaurant Staff",
    importance: Notifications.AndroidImportance.HIGH,
    vibrationPattern: [0, 250, 250, 250],
    lightColor: "#0F1B2D",
    sound: "default",
    bypassDnd: true,
  });
}

/** Cached so sign-out can unregister without re-prompting for permission. */
let cachedToken: string | null = null;

/**
 * Request notification permissions and return the FCM push token.
 * Returns null on simulators / Expo Go / when permission is denied.
 */
export async function getPushToken(): Promise<string | null> {
  if (!Device.isDevice) {
    // Simulators and Expo Go can't receive FCM.
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;
  if (finalStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }
  if (finalStatus !== "granted") {
    return null;
  }

  try {
    const token = (await Notifications.getDevicePushTokenAsync()).data;
    cachedToken = typeof token === "string" ? token : null;
    return cachedToken;
  } catch (err) {
    console.warn("[FCM] Could not get device push token:", err);
    return null;
  }
}

/** Platform string the backend expects ("android" | "ios" | "web"). */
export function pushPlatform(): "android" | "ios" | "web" {
  if (Platform.OS === "android") return "android";
  if (Platform.OS === "ios") return "ios";
  return "web";
}

/** Register the current device's FCM token with the backend. */
export async function registerDeviceToken(): Promise<string | null> {
  const token = await getPushToken();
  if (!token) return null;

  const payload: DeviceTokenIn = {
    token,
    platform: pushPlatform(),
  };

  try {
    await api("/api/v1/devices", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return token;
  } catch (err) {
    console.warn("[FCM] Could not register device token:", err);
    return null;
  }
}

/** Clear the device token from the backend (e.g. on sign-out). */
export async function unregisterDeviceToken(): Promise<void> {
  const token = cachedToken;
  if (!token) return;

  try {
    await api(`/api/v1/devices/${encodeURIComponent(token)}`, {
      method: "DELETE",
    });
  } catch {
    // Best effort — token may already be gone.
  }
  cachedToken = null;
}

function routeFromData(data: Record<string, unknown>): string {
  const route = data.route;
  if (typeof route === "string" && route.startsWith("/")) return route;
  return "/staff/tables";
}

/**
 * Set up listeners for incoming FCM messages.
 *
 * - Foreground: the handler above shows the banner and plays the sound.
 * - Tap: navigate to the screen named in the payload (route key).
 *
 * Returns a cleanup function that removes both listeners.
 */
export function setupNotificationListeners(): () => void {
  const response = Notifications.addNotificationResponseReceivedListener((event) => {
    const data = event.notification.request.content.data ?? {};
    router.push(routeFromData(data) as never);
  });

  return () => {
    response.remove();
  };
}
