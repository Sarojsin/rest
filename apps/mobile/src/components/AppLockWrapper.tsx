import { useEffect, useState } from "react";
import { View } from "react-native";

import { useAuth } from "@/lib/auth";
import { useAppLock } from "@/lib/biometric";
import { BiometricLockScreen } from "@/components/BiometricLockScreen";

export function AppLockWrapper({ children }: { children: React.ReactNode }) {
  const { status, signOut } = useAuth();
  const [showLockScreen, setShowLockScreen] = useState(false);

  const handleLock = () => {
    setShowLockScreen(true);
  };

  const handleUnlock = () => {
    setShowLockScreen(false);
  };

  // Only enable app lock for authenticated users
  const isEnabled = status === "authenticated";

  useAppLock(handleLock, isEnabled);

  if (showLockScreen) {
    return (
      <BiometricLockScreen
        onUnlock={handleUnlock}
        title="App Locked"
        subtitle="Authenticate to access Restaurant Staff"
      />
    );
  }

  return <View style={{ flex: 1 }}>{children}</View>;
}