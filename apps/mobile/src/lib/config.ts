import { Platform } from "react-native";

/**
 * Where the FastAPI service lives.
 *
 * `EXPO_PUBLIC_API_URL` always wins (set it for a physical device on the LAN).
 * Otherwise:
 *  - Android emulator: 10.0.2.2 is the host machine's loopback.
 *  - iOS simulator / web preview: the host is reachable on localhost.
 */
function defaultBaseUrl(): string {
  if (Platform.OS === "android") return "http://10.0.2.2:8000";
  return "http://127.0.0.1:8000";
}

const configured = process.env.EXPO_PUBLIC_API_URL?.trim();

export const API_BASE_URL = (configured && configured.length > 0 ? configured : defaultBaseUrl()).replace(
  /\/+$/,
  ""
);

/**
 * A release build without an explicit `EXPO_PUBLIC_API_URL` would silently
 * target the developer's machine, which is never reachable in production.
 * Warn in dev; in release the URL must be baked in by the build pipeline.
 */
if (__DEV__ && !(configured && configured.length > 0)) {
  console.warn(
    "[config] EXPO_PUBLIC_API_URL is not set — falling back to the emulator default:",
    API_BASE_URL
  );
}

/** Shown on the account screen so staff can report a misconfigured build. */
export const IS_DEV = __DEV__;
