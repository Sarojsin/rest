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

/** Shown on the account screen so staff can report a misconfigured build. */
export const IS_DEV = __DEV__;
