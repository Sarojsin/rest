import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Banner, Button, Field } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { API_BASE_URL, IS_DEV } from "@/lib/config";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

export default function InvitationAcceptScreen() {
  const { completeMfa } = useAuth();
  const theme = useTheme();
  const c = theme.color;
  const { token } = useLocalSearchParams<{ token: string }>();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [validating, setValidating] = useState(true);
  const [invitationValid, setInvitationValid] = useState(false);
  const [restaurantName, setRestaurantName] = useState("");

  useEffect(() => {
    async function validateToken() {
      if (!token) {
        setError("Missing invitation token.");
        setValidating(false);
        return;
      }
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/invitations/validate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        const data = await response.json();
        if (data.valid) {
          setInvitationValid(true);
          setRestaurantName(data.restaurant_name || "your restaurant");
        } else {
          setError("This invitation link is invalid or has expired.");
        }
      } catch {
        setError("Could not verify invitation. Check your connection.");
      } finally {
        setValidating(false);
      }
    }
    validateToken();
  }, [token]);

  async function submit() {
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (!token) {
      setError("Missing invitation token.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/invitations/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new ApiError(response.status, errorData.code || "ERROR", errorData.detail || "Failed to accept invitation");
      }

      const data = await response.json();
      // Store tokens and redirect
      const { setTokens } = await import("@/lib/tokenStore");
      await setTokens(data.access_token, data.refresh_token);

      // Clear query cache and redirect
      const { queryClient } = await import("@/lib/query");
      queryClient.clear();

      const home = "/waiter"; // Default home for owner
      router.replace(home);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not accept invitation. Try again."
      );
    } finally {
      setBusy(false);
    }
  }

  if (validating) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: c.bg }} edges={["top", "left", "right"]}>
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: space[4] }}>
          <Ionicons name="hourglass-outline" size={48} color={c.primary} />
          <Text style={{ marginTop: space[3], fontSize: text.md, color: c.ink }}>
            Verifying invitation…
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!invitationValid) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: c.bg }} edges={["top", "left", "right"]}>
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: space[4] }}>
          <Ionicons name="alert-circle-outline" size={48} color={c.danger} />
          <Text style={{ marginTop: space[3], fontSize: text.md, fontWeight: "600", color: c.ink }}>
            Invalid Invitation
          </Text>
          <Text style={{ marginTop: space[2], fontSize: text.base, color: c.muted, textAlign: "center" }}>
            {error || "This invitation link is invalid or has expired."}
          </Text>
          <Button
            label="Go to Sign In"
            variant="secondary"
            onPress={() => router.replace("/login")}
          />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: c.bg }} edges={["top", "left", "right"]}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={{ flexGrow: 1, padding: space[4], gap: space[5] }}
          keyboardShouldPersistTaps="handled"
        >
          <View style={{ gap: space[1], marginTop: space[6] }}>
            <View
              style={{
                width: 44,
                height: 44,
                borderRadius: radius.md,
                backgroundColor: c.navBg,
                alignItems: "center",
                justifyContent: "center",
                marginBottom: space[3],
              }}
            >
              <Ionicons name="mail-open-outline" size={22} color={c.navInk} />
            </View>
            <Text style={{ fontSize: text.xl, fontWeight: "800", color: c.ink }}>
              Accept Invitation
            </Text>
            <Text style={{ fontSize: text.base, color: c.muted }}>
              You&apos;ve been invited to join <Text style={{ fontWeight: "600" }}>{restaurantName}</Text> as an Owner.
            </Text>
          </View>

          {error ? (
            <Banner tone="danger" title="Error">
              {error}
            </Banner>
          ) : null}

          <View
            style={{
              backgroundColor: c.surface,
              borderColor: c.line,
              borderWidth: 1,
              borderRadius: radius.lg,
              padding: space[4],
              gap: space[4],
            }}
          >
            <Field
              label="Create Password"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoCapitalize="none"
              autoComplete="new-password"
              textContentType="newPassword"
              returnKeyType="next"
              placeholder="At least 8 characters"
            />
            <Field
              label="Confirm Password"
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              secureTextEntry
              autoCapitalize="none"
              autoComplete="new-password"
              textContentType="newPassword"
              returnKeyType="go"
              onSubmitEditing={() => void submit()}
              placeholder="Confirm your password"
            />
            <Button
              label={busy ? "Accepting…" : "Accept Invitation"}
              loading={busy}
              onPress={() => void submit()}
            />
          </View>

          <Text
            style={{
              fontSize: text.xs,
              color: c.muted,
              textAlign: "center",
              marginTop: "auto",
            }}
          >
            By accepting, you agree to the Terms of Service and Privacy Policy.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}