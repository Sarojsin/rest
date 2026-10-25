import { Redirect } from "expo-router";
import { View } from "react-native";

import { ServerUnreachable } from "@/components/SessionScreens";
import { Button, Loading, Screen, Subtitle, Title } from "@/components/ui";
import { homeRouteFor, useAuth } from "@/lib/auth";
import { space } from "@/theme/tokens";

/**
 * Single entry point. Every branch ends in a redirect or an honest explanation
 * — there is no "signed in but nothing to show" dead end.
 */
export default function Index() {
  const { status, me, retryBootstrap, signOut } = useAuth();

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
      <View style={{ flex: 1, justifyContent: "center", gap: space[4] }}>
        <Title>No station for this account</Title>
        <Subtitle>
          {me.display_name}, your role ({me.membership.role}) has no floor, kitchen, or cashier
          access. Ask an owner to review your permissions.
        </Subtitle>
        <Button label="Sign out" variant="secondary" onPress={() => void signOut()} />
      </View>
    </Screen>
  );
}
