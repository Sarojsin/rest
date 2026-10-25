import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useMemo } from "react";
import { Text, View } from "react-native";

import { Badge, Banner, Card, EmptyState, Loading, Screen, Subtitle, Title } from "@/components/ui";
import { useTables } from "@/features/tables/api";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

/**
 * Cashier home. Only tables with an open dining session can be billed; the
 * bill itself is created on the checkout screen so this list stays cheap.
 */
export default function CashierHomeScreen() {
  const theme = useTheme();
  const c = theme.color;
  const tables = useTables();

  const openSessions = useMemo(
    () => (tables.data ?? []).filter((table) => Boolean(table.active_session_id)),
    [tables.data]
  );

  return (
    <Screen refreshing={tables.isRefetching} onRefresh={() => void tables.refetch()}>
      <View style={{ gap: space[4] }}>
        <View style={{ gap: space[1] }}>
          <Title>Checkout</Title>
          <Subtitle>
            Pick an open table to issue its bill and record payment. Totals always come from the
            server.
          </Subtitle>
        </View>

        {tables.isError ? (
          <Banner tone="danger" title="Could not load tables">
            {tables.error instanceof Error ? tables.error.message : "Check the connection."}
          </Banner>
        ) : null}

        {tables.isPending ? <Loading label="Loading open tables" /> : null}

        {!tables.isPending && openSessions.length === 0 && !tables.isError ? (
          <EmptyState icon="receipt-outline" title="No open sessions">
            A table appears here once staff accept a QR order or take an order at the table.
          </EmptyState>
        ) : null}

        {openSessions.map((table) => (
          <Card
            key={table.id}
            onPress={() => router.push(`/cashier/bill/${table.active_session_id}`)}
            accessibilityLabel={`Open checkout for ${table.display_name}`}
          >
            <View style={{ flexDirection: "row", alignItems: "center", gap: space[3] }}>
              <View
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: radius.md,
                  backgroundColor: c.primarySoft,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Ionicons name="receipt-outline" size={20} color={c.primary} />
              </View>
              <View style={{ flex: 1, gap: 2 }}>
                <Text style={{ fontSize: text.md, fontWeight: "800", color: c.ink }}>
                  {table.display_name}
                </Text>
                <Text style={{ fontSize: text.sm, color: c.muted }}>
                  {table.seating_capacity ? `${table.seating_capacity} seats · ` : ""}
                  Session open
                </Text>
              </View>
              <Badge status={table.occupancy} />
              <Ionicons name="chevron-forward" size={18} color={c.muted} />
            </View>
          </Card>
        ))}

        {openSessions.length > 0 ? (
          <Text style={{ fontSize: text.xs, color: c.muted }}>
            A bill can only be settled in full or in part with a recorded payment. Nothing is marked
            paid from this device alone.
          </Text>
        ) : null}
      </View>
    </Screen>
  );
}
