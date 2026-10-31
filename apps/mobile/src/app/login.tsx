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
import { homeRouteFor, useAuth } from "@/lib/auth";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

export default function LoginScreen() {
  const { status, me, signIn, sessionExpired } = useAuth();
  const theme = useTheme();
  const c = theme.color;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (status === "authenticated" && me) {
    const home = homeRouteFor(me.membership.permissions);
    if (home) return <Redirect href={home} />;
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const signedIn = await signIn(email, password);
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
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
