import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import { Alert, View, Text } from "react-native";

import { Banner, Button, Card, KeyValue, Screen, SectionLabel, Subtitle, Title } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { API_BASE_URL, IS_DEV } from "@/lib/config";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

const CAPABILITY_LABELS: Record<string, string> = {
  "orders.create": "Take orders",
  "orders.read": "Read orders",
  "orders.confirm_qr": "Confirm QR orders",
  "orders.serve": "Serve ready food to guests",
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
  const { me, signOut, switchMembership } = useAuth();
  const theme = useTheme();
  const c = theme.color;
  const [busy, setBusy] = useState(false);

  if (!me) return null;

  const isManagerOrOwner = me.membership.permissions.includes("staff.manage") || me.membership.permissions.includes("menu.manage");
  const hasKitchen = me.membership.permissions.includes("kitchen.update");
  const hasCashier = me.membership.permissions.includes("bills.issue");

  const initials = me.display_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");

  return (
    <Screen testID="account-screen">
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

        {/* Membership / Branch Switcher */}
        {(me.memberships.length > 1 || (me.active_branch_id && me.memberships.length > 0)) ? (
          <View style={{ gap: space[2] }}>
            <SectionLabel>Restaurant & Branch</SectionLabel>
            <Card>
              <View style={{ gap: space[3] }}>
                <View>
                  <Text style={{ fontSize: text.xs, fontWeight: "700", color: c.muted }}>Current</Text>
                  <KeyValue label="Restaurant" value={me.membership.restaurant_name} />
                  <KeyValue label="Role" value={me.membership.role} />
                  {me.active_branch_id ? <KeyValue label="Branch" value={me.active_branch_id.slice(0, 8)} /> : null}
                </View>
                {me.memberships.length > 1 ? (
                  <View style={{ gap: space[2] }}>
                    <Text style={{ fontSize: text.xs, fontWeight: "700", color: c.muted }}>Switch Membership</Text>
                    {me.memberships
                      .filter((m) => m.id !== me.membership.id)
                      .map((membership) => (
                        <Button
                          key={membership.id}
                          label={`${membership.restaurant_name} · ${membership.role}`}
                          variant="secondary"
                          onPress={() => {
                            setBusy(true);
                            void switchMembership(membership.id)
                              .finally(() => setBusy(false));
                          }}
                          disabled={busy}
                        />
                      ))}
                  </View>
                ) : null}
                {me.membership.role === "owner" && me.memberships.length > 0 ? (
                  <View style={{ gap: space[2] }}>
                    <Text style={{ fontSize: text.xs, fontWeight: "700", color: c.muted }}>
                      Branch Scope (Owner only)
                    </Text>
                    <Button
                      label={me.active_branch_id ? `Branch: ${me.active_branch_id.slice(0, 8)}` : "All branches (organization-wide)"}
                      variant="secondary"
                      onPress={() => {
                        Alert.alert(
                          "Branch scope",
                          "Switching branch scope requires re-authentication. Sign out and sign in again to change branch context.",
                          [{ text: "OK" }]
                        );
                      }}
                    />
                  </View>
                ) : null}
              </View>
            </Card>
          </View>
        ) : null}

        {isManagerOrOwner ? (
          <View style={{ gap: space[2] }}>
            <SectionLabel>Switch station</SectionLabel>
            <Card>
              <View style={{ gap: space[2] }}>
                {hasKitchen ? (
                  <Button
                    label="Kitchen board"
                    variant="secondary"
                    icon="restaurant-outline"
                    onPress={() => router.replace("/kitchen")}
                  />
                ) : null}
                {hasCashier ? (
                  <Button
                    label="Cashier checkout"
                    variant="secondary"
                    icon="card-outline"
                    onPress={() => router.replace("/cashier")}
                  />
                ) : null}
                <Button
                  label="Floor / tables"
                  variant="secondary"
                  icon="grid-outline"
                  onPress={() => router.replace("/waiter")}
                />
              </View>
            </Card>
            <Text style={{ fontSize: text.xs, color: c.muted }}>
              Managers and owners can work any station. Tap to switch.
            </Text>
          </View>
        ) : null}

        <Button
          testID="sign-out-button"
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
