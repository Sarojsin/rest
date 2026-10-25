import { Ionicons } from "@expo/vector-icons";
import { Redirect } from "expo-router";
import { Tabs } from "expo-router/js-tabs";

import { useAuth } from "@/lib/auth";
import { useTheme } from "@/theme/context";

/** Cashier station — gated on `bills.issue`. */
export default function CashierLayout() {
  const { has } = useAuth();
  const theme = useTheme();
  const c = theme.color;

  if (!has("bills.issue")) return <Redirect href="/" />;

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
          title: "Checkout",
          tabBarIcon: ({ color }) => <Ionicons name="card-outline" size={22} color={String(color)} />,
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
