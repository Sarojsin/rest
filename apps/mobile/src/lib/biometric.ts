import { useEffect, useRef, useState, useCallback } from "react";
import * as LocalAuthentication from "expo-local-authentication";
import { AppState, AppStateStatus } from "react-native";

// Use the actual types from expo-local-authentication
type BiometryType = LocalAuthentication.AuthenticationType | null;

export type BiometricAuthResult =
  | { success: true }
  | { success: false; error: string };

export type BiometricAvailability = {
  available: boolean;
  biometryType: BiometryType;
  error: string | null;
};

export function useBiometricAuth() {
  const [availability, setAvailability] = useState<BiometricAvailability>({
    available: false,
    biometryType: null,
    error: null,
  });
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    async function checkAvailability() {
      try {
        const hasHardware = await LocalAuthentication.hasHardwareAsync();
        const isEnrolled = await LocalAuthentication.isEnrolledAsync();
        const supportedTypes = await LocalAuthentication.supportedAuthenticationTypesAsync();

        if (hasHardware && isEnrolled && supportedTypes.length > 0) {
          const firstType = supportedTypes[0];
          setAvailability({
            available: true,
            biometryType: firstType ?? null,
            error: null,
          });
        } else {
          let error = "Biometric authentication not available";
          if (!hasHardware) error = "No biometric hardware detected";
          else if (!isEnrolled) error = "No biometric credentials enrolled";
          else error = "Biometric authentication not supported";

          setAvailability({
            available: false,
            biometryType: null,
            error,
          });
        }
      } catch (err) {
        setAvailability({
          available: false,
          biometryType: null,
          error: err instanceof Error ? err.message : "Unknown error",
        });
      } finally {
        setIsChecking(false);
      }
    }

    checkAvailability();
  }, []);

  const authenticate = useCallback(
    async (promptMessage = "Authenticate to access the app"): Promise<BiometricAuthResult> => {
      if (!availability.available) {
        return { success: false, error: availability.error || "Biometric not available" };
      }

      try {
        const result = await LocalAuthentication.authenticateAsync({
          promptMessage,
          fallbackLabel: "Use passcode",
          cancelLabel: "Cancel",
          disableDeviceFallback: false,
        });
        if (result.success) {
          return { success: true as const };
        }
        return { success: false as const, error: "Authentication failed" };
      } catch (err) {
        return {
          success: false as const,
          error: err instanceof Error ? err.message : "Authentication failed",
        };
      }
    },
    [availability.available, availability.error]
  );

  return {
    availability,
    isChecking,
    authenticate,
  };
}

const BACKGROUND_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

export function useAppLock(
  onLock: () => void,
  isEnabled: boolean = true
) {
  const [isLocked, setIsLocked] = useState(false);
  const backgroundTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const appStateRef = useRef<AppStateStatus>("active");
  const { authenticate } = useBiometricAuth();

  const clearTimer = useCallback(() => {
    if (backgroundTimerRef.current) {
      clearTimeout(backgroundTimerRef.current);
      backgroundTimerRef.current = null;
    }
  }, []);

  const lockApp = useCallback(() => {
    if (!isLocked) {
      setIsLocked(true);
      onLock();
    }
  }, [isLocked, onLock]);

  const unlockApp = useCallback(async () => {
    const result = await authenticate("Unlock Restaurant Staff");
    if (result.success) {
      setIsLocked(false);
    }
    return result;
  }, [authenticate]);

  useEffect(() => {
    if (!isEnabled) return;

    const handleAppStateChange = (nextAppState: AppStateStatus) => {
      if (
        appStateRef.current.match(/inactive|background/) &&
        nextAppState === "active"
      ) {
        // App coming to foreground - check if we should lock
        if (backgroundTimerRef.current) {
          // Timer was still running, app was in background briefly
          clearTimer();
        } else {
          // App was in background long enough - lock it
          lockApp();
        }
      } else if (nextAppState.match(/inactive|background/)) {
        // App going to background - start timer
        clearTimer();
        backgroundTimerRef.current = setTimeout(() => {
          backgroundTimerRef.current = null;
          // App has been in background for timeout period
          // Will lock when it comes to foreground
        }, BACKGROUND_TIMEOUT_MS);
      }
      appStateRef.current = nextAppState;
    };

    const subscription = AppState.addEventListener("change", handleAppStateChange);

    return () => {
      clearTimer();
      subscription.remove();
    };
  }, [isEnabled, lockApp, clearTimer]);

  return {
    isLocked,
    lockApp,
    unlockApp,
    availability: useBiometricAuth().availability,
  };
}