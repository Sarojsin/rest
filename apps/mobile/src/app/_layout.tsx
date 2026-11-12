import { Ionicons } from "@expo/vector-icons";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider } from "@/lib/auth";
import { AppLockWrapper } from "@/components/AppLockWrapper";
import { QueryProvider } from "@/lib/query";
import { ThemeProvider, useTheme } from "@/theme/context";
import {
  configureForegroundPresentation,
  setupAndroidChannel,
  setupNotificationListeners,
} from "@/lib/fcm";

// Configure the Android notification channel once (pop sound, high importance)
// and make sure FCM banners also show while the app is in the foreground.
configureForegroundPresentation();
setupAndroidChannel();

void SplashScreen.preventAutoHideAsync();

function RootNavigator() {
  const theme = useTheme();
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: theme.color.bg },
        animation: "fade",
      }}
    >
      <Stack.Screen name="index" />
      <Stack.Screen name="login" />
      <Stack.Screen name="(app)" />
    </Stack>
  );
}

export default function RootLayout() {
  // The icon font is the only custom asset in the app; loading it before the
  // first paint avoids a frame of missing glyphs on the kitchen board.
  const [fontsLoaded] = useFonts(Ionicons.font);

  useEffect(() => {
    if (fontsLoaded) void SplashScreen.hideAsync();
  }, [fontsLoaded]);

  // Listen for incoming FCM taps (navigates to the payload's route).
  useEffect(() => setupNotificationListeners(), []);

  if (!fontsLoaded) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryProvider>
          <AuthProvider>
            <ThemeProvider>
              <StatusBar style="dark" />
              <AppLockWrapper>
                <RootNavigator />
              </AppLockWrapper>
            </ThemeProvider>
          </AuthProvider>
        </QueryProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
