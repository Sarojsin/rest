import { Redirect } from "expo-router";
import { Text, View } from "react-native";

import { ServerUnreachable } from "@/components/SessionScreens";
import { Button, Loading, Screen, Subtitle, Title } from "@/components/ui";
import { homeRouteFor, useAuth } from "@/lib/auth";
import { useTheme } from "@/theme/context";
import { space, text } from "@/theme/tokens";

/**
 * Single entry point. Every branch ends in a redirect or an honest explanation
 * — there is no "signed in but nothing to show" dead end.
 */
export default function Index() {
  const { status, me, retryBootstrap, signOut } = useAuth();
  const theme = useTheme();
  const c = theme.color;

  if (status === "loading") {
    return (
      <Screen scroll={false}>
        <View style={{ flex: 1, justifyContent: "center" }}>
          <Loading label="Checking your session" />
        </View>
      </Screen>
    );
  }

  if (status === "offline") {
    return (
      <ServerUnreachable onRetry={retryBootstrap} onSignOut={() => void signOut()} />
    );
  }

  if (status === "anonymous" || !me) {
    return <Redirect href="/login" />;
  }

  const home = homeRouteFor(me.membership.permissions);
  if (home) return <Redirect href={home} />;

  return (
    <Screen scroll={false}>
      <View style={{ flex: 1, justifyContent: "center", gap: space[4], padding: space[4] }}>
        <Title>No station for this account</Title>
        <Subtitle>
          {me.display_name}, your role ({me.membership.role}) has no floor, kitchen, or cashier
          access. Ask an owner to review your permissions.
        </Subtitle>
        <View style={{ gap: space[2] }}>
          <Text style={{ fontSize: text.sm, color: c.muted }}>
            Your permissions: {me.membership.permissions.join(", ") || "none"}
          </Text>
        </View>
        <Button label="Sign out" variant="secondary" onPress={() => void signOut()} />
      </View>
    </Screen>
  );
}
