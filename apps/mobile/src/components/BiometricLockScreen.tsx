import { Ionicons } from "@expo/vector-icons";
import { useState } from "react";
import { View, Text, Platform } from "react-native";

import { Button, Screen } from "@/components/ui";
import { useBiometricAuth, type BiometricAuthResult } from "@/lib/biometric";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

type BiometricLockScreenProps = {
  onUnlock: () => void;
  title?: string;
  subtitle?: string;
};

export function BiometricLockScreen({
  onUnlock,
  title = "App Locked",
  subtitle = "Authenticate to continue",
}: BiometricLockScreenProps) {
  const { authenticate, availability } = useBiometricAuth();
  const theme = useTheme();
  const c = theme.color;
  const [authenticating, setAuthenticating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fallbackMode, setFallbackMode] = useState(false);

  const handleAuthenticate = async () => {
    setAuthenticating(true);
    setError(null);

    const result: BiometricAuthResult = await authenticate(
      fallbackMode ? undefined : "Unlock Restaurant Staff"
    );

    if (result.success) {
      onUnlock();
    } else {
      setError(result.error);
      if (!fallbackMode && availability.biometryType) {
        // Try fallback (device passcode)
        setFallbackMode(true);
      }
    }
    setAuthenticating(false);
  };

  const biometryLabels: Record<string, string> = {
    facial_recognition: "Face ID",
    fingerprint: "Touch ID",
    iris: "Iris Scanner",
    face_id: "Face ID",
    touch_id: "Touch ID",
  };

  const biometryName = availability.biometryType
    ? biometryLabels[String(availability.biometryType)] || "Biometrics"
    : "Biometrics";

  if (!availability.available) {
    return (
      <Screen>
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: space[4], gap: space[4] }}>
          <Ionicons name="lock-closed-outline" size={48} color={c.muted} />
          <Text style={{ fontSize: text.xl, fontWeight: "700", color: c.ink }}>
            {title}
          </Text>
          <Text style={{ fontSize: text.base, color: c.muted, textAlign: "center" }}>
            {subtitle}
          </Text>
          <Text style={{ fontSize: text.sm, color: c.muted, textAlign: "center", marginTop: space[2] }}>
            {availability.error || "Biometric authentication is not available on this device."}
          </Text>
          <Button
            label="Unlock with Passcode"
            onPress={handleAuthenticate}
            disabled={authenticating}
            loading={authenticating}
          />
        </View>
      </Screen>
    );
  }

  const getBiometryIcon = () => {
    const biometryTypeStr = availability.biometryType ? String(availability.biometryType) : "";
    switch (biometryTypeStr) {
      case "facial_recognition":
      case "face_id":
        return "face-id-outline";
      case "fingerprint":
      case "touch_id":
        return "finger-print-outline";
      default:
        return "lock-closed-outline";
    }
  };

  return (
    <Screen>
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: space[4], gap: space[5] }}>
        <View
          style={{
            width: 80,
            height: 80,
            borderRadius: radius.pill,
            backgroundColor: c.primarySoft,
            alignItems: "center",
            justifyContent: "center",
            marginBottom: space[2],
          }}
        >
          <Ionicons
            name={getBiometryIcon() as any}
            size={36}
            color={c.primary}
          />
        </View>

        <Text style={{ fontSize: text.xl, fontWeight: "700", color: c.ink }}>
          {title}
        </Text>
        <Text style={{ fontSize: text.base, color: c.muted, textAlign: "center" }}>
          {subtitle}
        </Text>

        {error ? (
          <View style={{ backgroundColor: c.dangerSoft, padding: space[3], borderRadius: radius.md, width: "100%" }}>
            <Text style={{ fontSize: text.sm, color: c.danger, textAlign: "center" }}>
              {error}
            </Text>
          </View>
        ) : null}

        <Button
          label={authenticating ? "Authenticating…" : `Unlock with ${biometryName}`}
          loading={authenticating}
          onPress={handleAuthenticate}
          disabled={authenticating}
        />

        <Text style={{ fontSize: text.xs, color: c.muted, textAlign: "center" }}>
          {fallbackMode ? "Using device passcode fallback" : `Or use your device passcode`}
        </Text>
      </View>
    </Screen>
  );
}