import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const ACCESS_TOKEN_KEY = "rest.access_token";
const REFRESH_TOKEN_KEY = "rest.refresh_token";

/**
 * Tokens live in Keychain/Keystore, never in AsyncStorage.
 *
 * `expo-secure-store` has no web implementation; the web target only exists for
 * local preview in a browser, so it falls back to localStorage there.
 */
export async function getAccessToken(): Promise<string | null> {
  if (Platform.OS === "web") {
    try {
      return globalThis.localStorage?.getItem(ACCESS_TOKEN_KEY) ?? null;
    } catch {
      return null;
    }
  }
  try {
    return await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
}

export async function getRefreshToken(): Promise<string | null> {
  if (Platform.OS === "web") {
    try {
      return globalThis.localStorage?.getItem(REFRESH_TOKEN_KEY) ?? null;
    } catch {
      return null;
    }
  }
  try {
    return await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export async function setTokens(accessToken: string | null, refreshToken: string | null): Promise<void> {
  if (Platform.OS === "web") {
    try {
      if (accessToken) globalThis.localStorage?.setItem(ACCESS_TOKEN_KEY, accessToken);
      else globalThis.localStorage?.removeItem(ACCESS_TOKEN_KEY);
      if (refreshToken) globalThis.localStorage?.setItem(REFRESH_TOKEN_KEY, refreshToken);
      else globalThis.localStorage?.removeItem(REFRESH_TOKEN_KEY);
    } catch {
      // Ignore storage failures in the preview target.
    }
    return;
  }
  if (accessToken) {
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  } else {
    await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  }
  if (refreshToken) {
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  } else {
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  }
}
