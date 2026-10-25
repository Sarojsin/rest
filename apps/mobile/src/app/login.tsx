import { Ionicons } from "@expo/vector-icons";
import { Redirect, router } from "expo-router";
import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
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

const DEMO_ROLES = [
  { role: "Owner", email: "owner@harbor.example" },
  { role: "Manager", email: "manager@harbor.example" },
  { role: "Waiter", email: "waiter@harbor.example" },
  { role: "Kitchen", email: "kitchen@harbor.example" },
  { role: "Cashier", email: "cashier@harbor.example" },
] as const;

export default function LoginScreen() {
  const { status, me, signIn, sessionExpired } = useAuth();
  const theme = useTheme();
  const c = theme.color;

  const [email, setEmail] = useState("waiter@harbor.example");
  const [password, setPassword] = useState("HarborWaiter!1");
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
              <Text style={{ color: c.navInk, fontWeight: "800", fontSize: text.md }}>HT</Text>
            </View>
            <Text style={{ fontSize: text.xl, fontWeight: "800", color: c.ink }}>
              Harbor Table
            </Text>
            <Text style={{ fontSize: text.base, color: c.muted }}>
              Staff app for the floor, kitchen, and cashier.
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

          <View style={{ gap: space[3] }}>
            <Text style={{ fontSize: text.xs, color: c.muted }}>
              Demo accounts — tap to fill. Password pattern: Harbor&lt;Role&gt;!1
            </Text>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space[2] }}>
              {DEMO_ROLES.map((account) => (
                <Pressable
                  key={account.role}
                  accessibilityRole="button"
                  accessibilityLabel={`Fill ${account.role} demo account`}
                  onPress={() => {
                    setEmail(account.email);
                    setPassword(`Harbor${account.role}!1`);
                    setError(null);
                  }}
                  style={({ pressed }) => ({
                    flexDirection: "row",
                    alignItems: "center",
                    gap: 6,
                    paddingHorizontal: space[3],
                    paddingVertical: space[2],
                    borderRadius: radius.pill,
                    borderWidth: 1,
                    borderColor: c.lineStrong,
                    backgroundColor: pressed ? c.surface3 : c.surface,
                  })}
                >
                  <Ionicons name="person-outline" size={14} color={c.muted} />
                  <Text style={{ fontSize: text.sm, fontWeight: "600", color: c.ink }}>
                    {account.role}
                  </Text>
                </Pressable>
              ))}
            </View>
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
