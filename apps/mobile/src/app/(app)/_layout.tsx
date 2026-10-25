import { Redirect, Stack } from "expo-router";
import { View } from "react-native";

import { ServerUnreachable } from "@/components/SessionScreens";
import { Loading } from "@/components/ui";
import { useAuth } from "@/lib/auth";

/**
 * Session gate for every signed-in route. Route visibility is a UX affordance
 * only — the API re-checks the membership on each request, so a revoked role
 * fails on the next call and this gate drops the session.
 */
export default function AppLayout() {
  const { status, retryBootstrap, signOut } = useAuth();

  if (status === "loading") {
    return (
      <View style={{ flex: 1, justifyContent: "center" }}>
        <Loading label="Checking your session" />
      </View>
    );
  }

  if (status === "offline") {
    return <ServerUnreachable onRetry={retryBootstrap} onSignOut={() => void signOut()} />;
  }

  if (status !== "authenticated") {
    return <Redirect href="/login" />;
  }

  return <Stack screenOptions={{ headerShown: false }} />;
}
