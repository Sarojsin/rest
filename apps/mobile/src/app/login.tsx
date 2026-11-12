import { Ionicons } from "@expo/vector-icons";
import { Redirect, router } from "expo-router";
import { useState } from "react";
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
import { homeRouteFor, useAuth } from "@/lib/auth";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

export default function LoginScreen() {
  const { status, me, signIn, completeMfa, sessionExpired, mfaChallenge } = useAuth();
  const theme = useTheme();
  const c = theme.color;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Handle MFA challenge screen
  if (status === "mfa_required" && mfaChallenge) {
    return <MfaChallengeScreen mfaToken={mfaChallenge.mfa_token} />;
  }

  if (status === "authenticated" && me) {
    const home = homeRouteFor(me.membership.permissions);
    if (home) return <Redirect href={home} />;
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const signedIn = await signIn(email, password);
      if ("mfaRequired" in signedIn) {
        // MFA required - screen will switch to MFA challenge via status
        return;
      }
      const home = homeRouteFor(signedIn.membership.permissions);
      if (home) router.replace(home);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not reach the server. Check the connection and try again."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView
      testID="login-screen"
      style={{ flex: 1, backgroundColor: c.bg }}
      edges={["top", "left", "right"]}
    >
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
              <Ionicons name="restaurant-outline" size={22} color={c.navInk} />
            </View>
            <Text style={{ fontSize: text.xl, fontWeight: "800", color: c.ink }}>
              Staff sign in
            </Text>
            <Text style={{ fontSize: text.base, color: c.muted }}>
              Use the account your restaurant created for you.
            </Text>
          </View>

          {sessionExpired && !error ? (
            <Banner tone="warn" title="Session ended">
              Your session expired or was revoked. Sign in again to continue.
            </Banner>
          ) : null}

          {error ? (
            <Banner tone="danger" title="Sign-in failed">
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
              testID="email-input"
              label="Email"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              autoComplete="username"
              textContentType="username"
              returnKeyType="next"
            />
            <Field
              testID="password-input"
              label="Password"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoCapitalize="none"
              autoComplete="current-password"
              textContentType="password"
              returnKeyType="go"
              onSubmitEditing={() => void submit()}
            />
            <Button
              testID="login-button"
              label={busy ? "Signing in…" : "Sign in"}
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
            Guests never need an account — they scan the table QR code.
          </Text>
          {IS_DEV ? (
            <View
              style={{
                backgroundColor: c.surface,
                borderColor: c.line,
                borderWidth: 1,
                borderRadius: radius.md,
                padding: space[3],
                gap: space[1],
              }}
            >
              <Text style={{ fontSize: text.xs, fontWeight: "700", color: c.ink }}>
                Test accounts (dev only):
              </Text>
              <Text style={{ fontSize: text.xs, color: c.muted }}>
                owner@harbor.example / HarborOwner!1
              </Text>
              <Text style={{ fontSize: text.xs, color: c.muted }}>
                manager@harbor.example / HarborManager!1
              </Text>
              <Text style={{ fontSize: text.xs, color: c.muted }}>
                waiter@harbor.example / HarborWaiter!1
              </Text>
              <Text style={{ fontSize: text.xs, color: c.muted }}>
                kitchen@harbor.example / HarborKitchen!1
              </Text>
              <Text style={{ fontSize: text.xs, color: c.muted }}>
                cashier@harbor.example / HarborCashier!1
              </Text>
            </View>
          ) : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}


function MfaChallengeScreen({ mfaToken }: { mfaToken: string }) {
  const { completeMfa } = useAuth();
  const theme = useTheme();
  const c = theme.color;
  const [mfaCode, setMfaCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showRecovery, setShowRecovery] = useState(false);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const signedIn = await completeMfa(
        mfaToken,
        mfaCode || undefined,
        showRecovery ? recoveryCode : undefined
      );
      const home = homeRouteFor(signedIn.membership.permissions);
      if (home) router.replace(home);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Invalid code. Try again."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView
      testID="mfa-screen"
      style={{ flex: 1, backgroundColor: c.bg }}
      edges={["top", "left", "right"]}
    >
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
              <Ionicons name="shield-checkmark-outline" size={22} color={c.navInk} />
            </View>
            <Text style={{ fontSize: text.xl, fontWeight: "800", color: c.ink }}>
              Two-Factor Authentication
            </Text>
            <Text style={{ fontSize: text.base, color: c.muted }}>
              Enter the 6-digit code from your authenticator app.
            </Text>
          </View>

          {error ? (
            <Banner tone="danger" title="Verification failed">
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
              testID="mfa-input"
              label={showRecovery ? "Recovery Code" : "Authenticator Code"}
              value={showRecovery ? recoveryCode : mfaCode}
              onChangeText={showRecovery ? setRecoveryCode : setMfaCode}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="number-pad"
              textContentType="oneTimeCode"
              returnKeyType="go"
              onSubmitEditing={() => void submit()}
              placeholder={showRecovery ? "XXXX-XXXX" : "123456"}
            />
            <Button
              testID="mfa-verify-button"
              label={busy ? "Verifying…" : "Verify"}
              loading={busy}
              onPress={() => void submit()}
            />
            <Button
              variant="secondary"
              label={showRecovery ? "Use authenticator code" : "Use recovery code"}
              onPress={() => {
                setShowRecovery(!showRecovery);
                setMfaCode("");
                setRecoveryCode("");
              }}
            />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
