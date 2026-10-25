import { Ionicons } from "@expo/vector-icons";
import { useState } from "react";
import { View, Text } from "react-native";

import { Banner, Button, Card, KeyValue, Screen, SectionLabel, Subtitle, Title } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { API_BASE_URL, IS_DEV } from "@/lib/config";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

const CAPABILITY_LABELS: Record<string, string> = {
  "orders.create": "Take orders",
  "orders.read": "Read orders",
  "orders.confirm_qr": "Confirm QR orders",
  "kitchen.read": "Read kitchen tickets",
  "kitchen.update": "Move kitchen items",
  "tables.manage": "Manage tables",
  "bills.issue": "Issue bills",
  "payments.record": "Record payments",
  "reports.read": "Read reports",
  "menu.manage": "Manage menu",
  "settings.manage": "Manage settings",
  "staff.manage": "Manage staff",
};

function label(permission: string): string {
  return CAPABILITY_LABELS[permission] ?? permission;
}

export function AccountScreen() {
  const { me, signOut } = useAuth();
  const theme = useTheme();
  const c = theme.color;
  const [busy, setBusy] = useState(false);

  if (!me) return null;

  const initials = me.display_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");

  return (
    <Screen>
      <View style={{ gap: space[5] }}>
        <View>
          <Title>Account</Title>
          <Subtitle>Signed in as {me.membership.role}.</Subtitle>
        </View>

        <Card>
          <View style={{ flexDirection: "row", alignItems: "center", gap: space[3] }}>
            <View
              style={{
                width: 48,
                height: 48,
                borderRadius: radius.pill,
                backgroundColor: c.primarySoft,
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Text style={{ fontSize: text.md, fontWeight: "800", color: c.primary }}>
                {initials || "?"}
              </Text>
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={{ fontSize: text.md, fontWeight: "700", color: c.ink }}>
                {me.display_name}
              </Text>
              <Text style={{ fontSize: text.sm, color: c.muted }}>{me.email}</Text>
            </View>
          </View>
          <View style={{ height: 1, backgroundColor: c.line }} />
          <KeyValue label="Restaurant" value={me.membership.restaurant_name} />
          <KeyValue label="Role" value={me.membership.role} />
        </Card>

        <View style={{ gap: space[2] }}>
          <SectionLabel>What this account can do</SectionLabel>
          <Card>
            {me.membership.permissions.length === 0 ? (
              <Subtitle>No permissions are assigned to this role.</Subtitle>
            ) : (
              me.membership.permissions.map((permission) => (
                <View
                  key={permission}
                  style={{ flexDirection: "row", alignItems: "center", gap: space[3] }}
                >
                  <Ionicons name="checkmark-circle" size={18} color={c.success} />
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: text.base, color: c.ink }}>{label(permission)}</Text>
                    <Text style={{ fontSize: text.xs, color: c.muted }}>{permission}</Text>
                  </View>
                </View>
              ))
            )}
          </Card>
          <Text style={{ fontSize: text.xs, color: c.muted }}>
            The API re-checks these on every request. If a manager changes your role, this screen
            updates on the next refresh.
          </Text>
        </View>

        <View style={{ gap: space[2] }}>
          <SectionLabel>Session</SectionLabel>
          <Card>
            <KeyValue label="Token lifetime" value="One shift (8 hours)" />
            <KeyValue label="Stored in" value="Device keychain / keystore" />
            {IS_DEV ? <KeyValue label="API" value={API_BASE_URL} /> : null}
          </Card>
        </View>

        {me.membership.permissions.includes("reports.read") ? (
          <Banner tone="info" title="Reports live on the web">
            Sales reports, menu management, and payment settings are in the staff website. This app
            covers the floor, kitchen, and cashier.
          </Banner>
        ) : null}

        <Button
          label={busy ? "Signing out…" : "Sign out"}
          variant="secondary"
          icon="log-out-outline"
          loading={busy}
          onPress={() => {
            setBusy(true);
            void signOut().finally(() => setBusy(false));
          }}
          accessibilityHint="Clears the session and cached order data from this device"
        />
        <Text style={{ fontSize: text.xs, color: c.muted, textAlign: "center" }}>
          Signing out removes cached orders and bills from this device.
        </Text>
      </View>
    </Screen>
  );
}
