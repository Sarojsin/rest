import { View } from "react-native";

import { Banner, Button, Screen, Subtitle, Title } from "@/components/ui";
import { space } from "@/theme/tokens";

/**
 * Shown when a stored token could not be verified because the API is
 * unreachable. The app deliberately refuses to render order or bill data it
 * cannot prove is current.
 */
export function ServerUnreachable({
  onRetry,
  onSignOut,
}: {
  onRetry: () => void;
  onSignOut: () => void;
}) {
  return (
    <Screen scroll={false}>
      <View style={{ flex: 1, justifyContent: "center", gap: space[4] }}>
        <Title>Cannot reach the server</Title>
        <Subtitle>
          Your session is stored, but the app will not show orders or bills it cannot verify.
          Check the connection and try again.
        </Subtitle>
        <Banner tone="warn" title="No connection">
          Ask a manager if the restaurant network is down.
        </Banner>
        <Button label="Try again" icon="refresh" onPress={onRetry} />
        <Button label="Sign out" variant="secondary" onPress={onSignOut} />
      </View>
    </Screen>
  );
}
