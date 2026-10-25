import { Ionicons } from "@expo/vector-icons";
import { Redirect } from "expo-router";
import { Tabs } from "expo-router/js-tabs";

import { useAuth } from "@/lib/auth";
import { useTheme } from "@/theme/context";
import { text } from "@/theme/tokens";

/**
 * Waiter station. Guarded by capability, not role name: anyone who can create
 * orders may work the floor.
 */
export default function WaiterLayout() {
  const { has } = useAuth();
  const theme = useTheme();
  const c = theme.color;

  if (!has("orders.create")) return <Redirect href="/" />;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: c.primary,
        tabBarInactiveTintColor: c.muted,
        tabBarStyle: {
          backgroundColor: c.surface,
          borderTopColor: c.line,
          borderTopWidth: 1,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Tables",
          tabBarIcon: ({ color }) => <Ionicons name="grid-outline" size={22} color={String(color)} />,
        }}
      />
      <Tabs.Screen
        name="requests"
        options={{
          title: "Requests",
          tabBarIcon: ({ color }) => (
            <Ionicons name="notifications-outline" size={22} color={String(color)} />
          ),
        }}
      />
      <Tabs.Screen
        name="account"
        options={{
          title: "Account",
          tabBarIcon: ({ color }) => <Ionicons name="person-outline" size={22} color={String(color)} />,
        }}
      />
    </Tabs>
  );
}
